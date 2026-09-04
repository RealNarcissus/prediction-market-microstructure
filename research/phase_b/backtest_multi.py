"""Multi-month x multi-asset maker-entry backtest (Option-1 hardening).

Data sources:
- Features/training: Binance Vision + REST spot 1m klines (data/klines),
  Aug-2025 -> present, per asset.
- Epochs/outcomes: BrockMisner/polymarket-btc-updown `markets` subset
  (resolution: 1=Up, 0=Down, -1=unknown).
- Quote series for fill simulation: updown `prices` subset
  (per-market up_price/down_price through the active window).

Protocol per asset x horizon:
  - Train champion on windows [2025-09 .. 2025-12] (TWAP next-labels).
  - Predict every later window (Jan..Aug 2026) — out-of-sample year.
  - Decision at open+60s: side by |p-0.5|>theta; rest maker bid at fair-delta
    (fair = CLT Asian prob at decision minute); fill when the market's own
    price for that side <= bid; settle vs official resolution; maker fee 0.

Outputs: EV/win-rate/fill tables by month x asset x horizon -> MAKER_BACKTEST_MULTI.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))
sys.path.insert(0, str(REPO / "research" / "rlenv"))

from env import build_windows  # noqa: E402
from quantbtc.twapbars import aggregate_windows  # noqa: E402
from strategies.s002_lgbm_base import new_model as champ_model  # noqa: E402
from strategies.s023_lgbm_pos_lag23 import build_features as champ_feats  # noqa: E402

KLINES = REPO / "data/klines"
UPDOWN_DATA = REPO / "data/polymarket/updown"
UPDOWN = REPO / "data/polymarket/updown"
ASSETS = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"}
TFS = {"5-minute": "5m", "15-minute": "15m"}
THETA = 0.05
TRAIN_END = np.datetime64("2026-01-01")
DELTAS = (0.00, 0.02)


def champ_predictions_for_year(symbol: str, horizon_str: str):
    """Train Sep-Dec 2025, predict all of 2026. Returns {open_ms: p}."""
    seconds = int(horizon_str[: len(horizon_str) - 1]) * 60

    def prep(src: pl.DataFrame, until_ms: int | None, since_ms: int | None):
        b = src.sort("open_time")
        if until_ms is not None:
            b = b.filter(pl.col("open_time").dt.epoch("ms") < until_ms)
        if since_ms is not None:
            b = b.filter(pl.col("open_time").dt.epoch("ms") >= since_ms)
        agg = aggregate_windows(b, horizon_str)
        return (
            agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next"))
            .drop_nulls(["y_next"])
        )

    bars = pl.read_parquet(KLINES / f"{symbol}_1m.parquet").with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
    )
    cut = int(TRAIN_END.astype("datetime64[ms]").astype(int))
    tr_agg = prep(bars, cut, None)
    Xtr = champ_feats(tr_agg)
    ytr = tr_agg["y_next"].to_numpy().astype(int)
    fin_tr = np.isfinite(Xtr).all(axis=1)

    val_agg = prep(bars, None, cut)
    Xva = champ_feats(val_agg)
    fin_va = np.isfinite(Xva).all(axis=1)
    opens = val_agg["open_time"].dt.epoch("ms").to_numpy()[fin_va]

    model = champ_model()
    model.fit(Xtr[fin_tr], ytr[fin_tr])
    probs = model.predict_proba(Xva[fin_va])[:, 1]
    col1 = list(model.classes_).index(1)
    opens_f = val_agg["open_time"].dt.epoch("ms").to_numpy()[fin_va]
    probs_f = model.predict_proba(Xva[fin_va])
    return {int(o): float(pv[col1]) for o, pv in zip(opens_f, probs_f)}


def main() -> None:
    markets = pl.read_parquet(UPDOWN / "markets.parquet").filter(
        pl.col("crypto").is_in(list(set(ASSETS.values())))
        & pl.col("timeframe").is_in(list(TFS.keys()))
        & pl.col("resolution").is_in([0, 1])
    )
    print(f"resolved epochs available: {markets.height}")

    all_rows = []
    for symbol, asset in ASSETS.items():
        for tf_file, hz in TFS.items():
            seconds = int(hz[: len(hz) - 1]) * 60
            prices = pl.read_parquet(
                UPDOWN / f"prices_{asset}_{tf_file}.parquet"
            )
            p_by_open = champ_predictions_for_year(symbol, hz)
            bars_dt = pl.read_parquet(KLINES / f"{symbol}_1m.parquet").with_columns(
                pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
            )
            eps = {
                e["open_time_ms"]: e
                for e in build_windows(bars_dt, horizon_s=seconds, seal="2099-01-01")
            }
            mtf = markets.filter(
                (pl.col("crypto") == asset) & (pl.col("timeframe") == tf_file)
            )
            # start_ts = market CREATION time; the slug suffix is the epoch
            # window start (RECON finding) — never use start_ts for timing
            for r in mtf.iter_rows(named=True):
                import re as _re

                mm = _re.search(r"-(\d{10})$", r["slug"])
                if not mm:
                    continue
                open_ms = int(mm.group(1)) * 1000
                prev_open = open_ms - seconds * 1000
                p = p_by_open.get(prev_open)
                if p is None or abs(p - 0.5) <= THETA:
                    continue
                ep = eps.get(open_ms)
                if ep is None:
                    continue
                fair = next(
                    (
                        float(st["feat"][0])
                        for st in ep["steps"]
                        if (st["t_ms"] - open_ms) >= 60_000
                    ),
                    None,
                )
                if fair is None:
                    continue
                side_up = p >= 0.5
                base = fair if side_up else 1.0 - fair
                won = (r["resolution"] == 1) == side_up
                for delta in DELTAS:
                    bid = float(np.clip(base - delta, 0.01, 0.99))
                    # fill proxy: market price of our side crossed our bid
                    pr = prices.filter(pl.col("market_id") == r["market_id"])
                    side_prices = pr["up_price"] if side_up else pr["down_price"]
                    after = [
                        float(x)
                        for x in side_prices.to_list()
                        if x is not None and x <= bid
                    ]
                    if not after:
                        continue
                    w = won
                    pnl = ((1 - bid)) if w else (-bid)
                    all_rows.append({
                        "month": datetime_month(open_ms),
                        "asset": asset, "horizon": hz, "delta": delta,
                        "filled": True, "win": bool(w),
                        "pnl": pnl, "bid": bid,
                    })
        print(f"{asset} done")

    df = pl.DataFrame(all_rows)
    if not df.is_empty():
        cache = REPO / "data/polymarket/maker_fills_multi.parquet"
        df.write_parquet(cache)
    if df.is_empty():
        print("no fills simulated — investigate")
        return
    summary = (
        df.group_by(["month", "asset", "horizon", "delta"])
        .agg(
            pl.len().alias("fills"),
            pl.col("win").mean().alias("win_rate"),
            pl.col("pnl").mean().alias("ev_per_trade"),
            pl.col("pnl").sum().alias("total_pnl"),
        )
        .sort(["month", "asset", "horizon", "delta"])
    )
    lines = [
        "# Maker-entry backtest MULTI (official outcomes, real quote fills)", "",
        "| month | asset | hz | delta | fills | win | EV/trade | PnL |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in summary.iter_rows(named=True):
        lines.append(
            f"| {r['month']} | {r['asset']} | {r['horizon']} | "
            f"{r['delta']:.2f} | {r['fills']} | {r['win_rate']:.1%} | "
            f"{r['ev_per_trade']:+.4f} | {r['total_pnl']:+.2f} |"
        )
    totals = df.group_by("delta").agg(
        pl.len().alias("n_fills"),
        pl.col("win").mean().alias("win_rate_avg"),
        pl.col("pnl").mean().alias("ev_avg"),
        pl.col("pnl").sum().alias("total_pnl_sum"),
    )
    lines += ["", "**By delta (all months/assets/horizons):**"]
    for r in totals.sort("delta").iter_rows(named=True):
        lines.append(
            f"- delta {r['delta']:.2f}: fills {r['n_fills']}, "
            f"win {r['win_rate_avg']:.1%}, EV {r['ev_avg']:+.4f}, "
            f"total PnL {r['total_pnl_sum']:+.2f}"
        )
    out_md = REPO / "research/phase_b/MAKER_BACKTEST_MULTI.md"
    Path(out_md).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-14:]))
    print(f"wrote {out_md}")


def datetime_month(ms: int) -> str:
    import datetime as dt

    return dt.datetime.fromtimestamp(ms / 1000, tz=dt.timezone.utc).strftime("%Y-%m")


if __name__ == "__main__":
    main()
