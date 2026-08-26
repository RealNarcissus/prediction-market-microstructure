"""Confidence-gate sweep using only the updown dataset (self-contained)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))

from quantbtc.twapbars import aggregate_windows  # noqa: E402
from strategies.s002_lgbm_base import new_model as champ_model  # noqa: E402
from strategies.s023_lgbm_pos_lag23 import build_features as champ_feats  # noqa: E402

UPDOWN = REPO / "data/polymarket/updown"
KLINES = REPO / "data/klines"
ASSETS = {"BTCUSDT": "BTC", "ETHUSDT": "ETH", "SOLUSDT": "SOL"}
TFS = {"5-minute": "5m", "15-minute": "15m"}
THETAS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
TRAIN_CUTOFF_MS = int(np.datetime64("2026-03-01").astype("datetime64[ms]").astype(int))


def champ_predictions(klines_path: Path, horizon_str: str):
    seconds = int(horizon_str[: len(horizon_str) - 1]) * 60
    bars = pl.read_parquet(klines_path).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
    )
    agg = aggregate_windows(bars, horizon_str)
    agg = agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next")).drop_nulls(["y_next"])
    X = champ_feats(agg)
    y = agg["y_next"].to_numpy().astype(int)
    fin = np.isfinite(X).all(axis=1)
    opens = agg["open_time"].dt.epoch("ms").to_numpy()
    model = champ_model()
    model.fit(X[fin & (opens < TRAIN_CUTOFF_MS)], y[fin & (opens < TRAIN_CUTOFF_MS)])
    probs = model.predict_proba(X)[:, list(model.classes_).index(1)]
    return {int(o): float(p) for o, p in zip(opens[fin], probs[fin])}


def main() -> None:
    markets = pl.read_parquet(UPDOWN / "markets.parquet").filter(
        pl.col("crypto").is_in(list(set(ASSETS.values())))
        & pl.col("timeframe").is_in(list(TFS.keys()))
        & pl.col("resolution").is_in([0, 1])
    )
    print(f"resolved epochs: {markets.height}")

    all_rows = []
    for symbol, asset in ASSETS.items():
        klines = KLINES / f"{symbol}_1m.parquet"
        if not klines.exists():
            continue
        for tf_file, hz in TFS.items():
            seconds = 300 if hz == "5m" else 900
            p_by_open = champ_predictions(klines, hz)

            mtf = markets.filter(
                (pl.col("crypto") == asset) & (pl.col("timeframe") == tf_file)
            ).with_columns(
                (pl.col("start_ts") * 1000).alias("open_ms")
            )
            pr_file = UPDOWN / f"prices_{asset}_{tf_file}.parquet"
            all_prices = (
                pl.read_parquet(pr_file).with_columns(
                    pl.col("timestamp").dt.epoch("ms").alias("ts_ms")
                )
                if pr_file.exists()
                else None
            )

            for r in mtf.iter_rows(named=True):
                open_ms = r["open_ms"]
                prev_open = open_ms - seconds * 1000
                p = p_by_open.get(prev_open)
                if p is None:
                    continue
                won_up = r["resolution"] == 1
                side_up = p >= 0.5
                won = won_up == side_up
                col = "up_price" if side_up else "down_price"

                # entry price from the prices subset
                entry_px = None
                month = ""
                if all_prices is not None:
                    sub = all_prices.filter(
                        (pl.col("market_id") == mid)
                        & (pl.col("ts_ms") >= open_ms + 60_000)
                    ).sort("ts_ms")
                    vals = [float(x) for x in sub[col].to_list() if x is not None and float(x) > 0.01]
                    if vals:
                        entry_px = vals[0]
                    month = sub["ts_ms"][0] if sub.height else ""

                if entry_px is None:
                    continue
                fee = 0.07 * entry_px * (1 - entry_px)
                pnl = ((1 - entry_px) - fee) if won else (-entry_px - fee)

                month_s = datetime_month(open_ms)
                for theta in THETAS:
                    if abs(p - 0.5) > theta:
                        all_rows.append({
                            "theta": theta, "month": month_s,
                            "asset": asset, "horizon": hz,
                            "won": won, "pnl": pnl, "p": p, "entry": entry_px,
                        })

    df = pl.DataFrame(all_rows)
    print(f"\ndecided+priced epochs at theta=0.05: {df.filter(pl.col('theta')==0.05).height}")

    lines = ["| theta | month | asset | hz | fills | win | EV/trade |", "|---|---|---|---|---|---|---|"]
    summary = (
        df.group_by(["theta", "month", "asset", "horizon"])
        .agg(pl.len().alias("n"), pl.col("won").mean(), pl.col("pnl").mean())
        .sort(["theta", "month", "asset", "horizon"])
    )
    for r in summary.iter_rows(named=True):
        lines.append(f"| {r['theta']:.2f} | {r['month']} | {r['asset']} | {r['horizon']} | {r['n']} | {r['won']:.1%} | {r['pnl']:+.4f} |")
    print("\n".join(lines))

    print("\n=== AGGREGATE BY THETA ===")
    agg_t = df.group_by("theta").agg(
        pl.len().alias("fills"), pl.col("won").mean(),
        pl.col("pnl").mean().alias("ev"), pl.col("pnl").sum().alias("tot")
    ).sort("theta")
    for r in agg_t.iter_rows(named=True):
        marker = " ←" if r["ev"] > 0 and r["theta"] >= 0.08 else ""
        print(f"theta={r['theta']:.2f}: fills={r['fills']}, win={r['won']:.1%}, EV/trade={r['ev']:+.4f}, total={r['tot']:+.2f}{marker}")

    out_md = REPO / "research/phase_b/CONF_GATE_SWEEP.md"
    Path(out_md).write_text("\n".join(lines) + "\n")
    print(f"wrote {out_md}")


def datetime_month(ms: int) -> str:
    import datetime as dt2
    return dt2.datetime.fromtimestamp(ms / 1000, tz=dt2.timezone.utc).strftime("%Y-%m")


if __name__ == "__main__":
    main()
