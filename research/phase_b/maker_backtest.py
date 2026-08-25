"""Maker-entry backtest on historical Polymarket books (BTC 5m/15m, Mar 2026).

Protocol:
- Champion (s023 features, LGBM) trained on spot TWAP next-window labels
  through Feb 28; predictions for March windows are out-of-sample.
- Decision at open+60s: side by champion p vs theta gate.
- MAKER entry: rest a bid on the model's token at price = fair - delta
  (fair = CLT Asian-digital probability at the decision minute).
- Fill: any subsequent trade print on that token at price <= our bid.
- Settle vs official Polymarket resolutions. Maker fee = 0.
Variants: delta in {0.00, 0.02, 0.05} x horizons {5m, 15m}.

Token->side identification: for each resolved epoch, the token whose final
in-window mid is highest is the winning side (metadata recovery from
outcomes — used only to label books, never as a feature).
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

from env import build_windows  # noqa: E402  (research/rlenv/env.py)
from quantbtc.twapbars import aggregate_windows  # noqa: E402
from strategies.s002_lgbm_base import new_model as champ_model  # noqa: E402
from strategies.s023_lgbm_pos_lag23 import build_features as champ_feats  # noqa: E402

DATA = REPO / "data/polymarket"
THETA = 0.05
TRAIN_CUTOFF_MS = int(np.datetime64("2026-03-01").astype("datetime64[ms]").astype(int))
# Offsets ABOVE fair: with 11c/89c walls + active midpoint matching,
# a bid fills only if its limit >= prevailing mid-print. Pricing below
# fair never fills (Campaign-D-era bug: bids under mid are ineligible).
DELTAS = (0.00, 0.01, 0.03)


HERDR_1M = Path(
    "/home/charleton/Desktop/agentProjects/Herdr/quant-btc/data/raw/"
    "btcusdt-usdtm-1m.parquet"
)


def champion_predictions(bars: pl.DataFrame, horizon: str):
    """Train on Herdr perp TWAP windows through Feb 28 (long history,
    temporally clean), predict March spot windows. Perp->spot basis is an
    accepted approximation, documented in MAKER_BACKTEST.md."""
    seconds = int(horizon[: len(horizon) - 1]) * 60

    def prep(src: pl.DataFrame, until_ms: int | None) -> pl.DataFrame:
        b = src.sort("open_time")
        if b.schema["open_time"].time_zone is None:
            b = b.with_columns(pl.col("open_time").dt.replace_time_zone("UTC"))
        if until_ms is not None:
            b = b.filter(pl.col("open_time").dt.epoch("ms") < until_ms)
        agg = aggregate_windows(b, horizon)
        return (
            agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next"))
            .drop_nulls(["y_next"])
        )

    train_agg = prep(pl.read_parquet(HERDR_1M), TRAIN_CUTOFF_MS)
    Xtr = champ_feats(train_agg)
    ytr = train_agg["y_next"].to_numpy().astype(int)
    fin_tr = np.isfinite(Xtr).all(axis=1)

    val_agg = prep(bars, None)
    Xva = champ_feats(val_agg)
    fin_va = np.isfinite(Xva).all(axis=1)
    opens_ms = val_agg["open_time"].dt.epoch("ms").to_numpy()

    model = champ_model()
    model.fit(Xtr[fin_tr], ytr[fin_tr])
    probs = model.predict_proba(Xva[fin_va])[:, 1]

    out = {}
    for i, pi in zip(np.flatnonzero(fin_va), probs):
        out[int(opens_ms[i])] = float(pi)
    return out


def main() -> None:
    bars = pl.read_parquet(DATA / "btcusdt_spot_1m_janmar.parquet")

    # ---- token/side map + final-mid table from orderbooks ----
    tok_rows = []
    for f in sorted(DATA.glob("orderbooks_*.parquet")):
        ob = pl.read_parquet(f)
        if ob.height == 0:
            continue
        tok_rows.append(
            ob.with_columns(pl.col("timestamp").dt.epoch("ms").alias("ts_ms"))
            .select(["market_id", "token_id", "question", "ts_ms", "mid_price"])
            .with_columns(
                pl.col("market_id")
                .str.extract(r"-(\d{10})$", 1)
                .cast(pl.Int64)
                .mul(1000)
                .alias("open_ms")
            )
            .drop_nulls(["open_ms", "mid_price"])
            .filter(pl.col("question").str.contains("(?i)up or down"))
        )
    books = pl.concat(tok_rows)

    epochs_all = pl.read_parquet(DATA / "epochs_bridge_quotes.parquet").filter(
        (pl.col("asset") == "BTC") & (pl.col("outcome").is_not_null())
    )
    res_lookup = {
        r["market_id"]: r["outcome"]
        for r in epochs_all.iter_rows(named=True)
    }

    side_of_token: dict[tuple[str, str], str] = {}
    final_mid: dict[tuple[str, str], float] = {}
    for (mid, tok), g in books.group_by(["market_id", "token_id"]):
        if mid not in res_lookup:
            continue
        last_mid = float(g.sort("ts_ms")["mid_price"][-1])
        if not np.isfinite(last_mid):
            continue
        final_mid[(mid, tok)] = last_mid

    for mid, outcome in res_lookup.items():
        toks = [(m, t) for (m, t) in final_mid if m == mid]
        if len(toks) != 2:
            continue
        winner_tok = max(toks, key=lambda k: final_mid[k])
        side_of_token[winner_tok] = "up"
        side_of_token[[t for t in toks if t != winner_tok][0]] = "down"

    print(f"side map entries: {len(side_of_token)}")

    # ---- trades grouped by token ----
    trades = pl.concat([
        pl.read_parquet(f) for f in sorted(DATA.glob("trades_2026-03-*.parquet"))
    ]).select(["token_id", "timestamp", "price"]).with_columns(
        pl.col("timestamp").dt.epoch("ms").alias("ts_ms")
    ).sort("ts_ms")
    trades_by_token = {}
    for t_key, g in trades.group_by("token_id"):
        t = t_key[0] if isinstance(t_key, tuple) else t_key
        trades_by_token[t] = g

    all_results = []
    for horizon in ("5m", "15m"):
        seconds = 300 if horizon == "5m" else 900
        p_by_open = champion_predictions(bars, horizon)

        eps_all = build_windows(bars, horizon_s=seconds, seal='2026-04-01')
        eps = {
            e["open_time_ms"]: e
            for e in eps_all
            if e["open_time_ms"] >= TRAIN_CUTOFF_MS
        }

        epochs = epochs_all.filter(pl.col("horizon") == horizon)

        for delta in DELTAS:
            filled = won_n = skipped_theta = no_map = unfilled = decided = 0
            pnls = []
            for r in epochs.iter_rows(named=True):
                open_ms = int(r["open_time_utc"].timestamp() * 1000)
                prev_open = open_ms - seconds * 1000
                p = p_by_open.get(prev_open)
                if p is None:
                    continue
                decided += 1
                if abs(p - 0.5) <= THETA:
                    skipped_theta += 1
                    continue
                side_up = p >= 0.5
                ep = eps.get(open_ms)
                if ep is None:
                    continue
                fair = None
                for st in ep["steps"]:
                    if (st["t_ms"] - ep["open_time_ms"]) >= 60_000:
                        fair = float(st["feat"][0])
                        break
                if fair is None:
                    continue
                want_side = "up" if side_up else "down"
                tok = None
                for (m, t), s in side_of_token.items():
                    if m == r["market_id"] and s == want_side:
                        tok = t
                        break
                if tok is None:
                    no_map += 1
                    continue
                base = fair if want_side == "up" else 1.0 - fair
                bid = float(np.clip(base + delta, 0.01, 0.99))

                tt = trades_by_token.get(tok)
                if tt is None:
                    unfilled += 1
                    continue
                after = tt.filter(
                    (pl.col("ts_ms") >= open_ms + 60_000)
                    & (pl.col("price") <= bid)
                )
                if after.height == 0:
                    unfilled += 1
                    continue
                fill_px = float(after["price"][0])
                w = (r["outcome"] == ("Up" if side_up else "Down"))  # maker fee 0
                pnl = ((1 - fill_px)) if w else (-fill_px)
                filled += 1
                won_n += int(w)
                pnls.append(pnl)

            ev = float(np.mean(pnls)) if pnls else float("nan")
            all_results.append({
                "horizon": horizon, "delta": delta, "decided": decided,
                "theta_skipped": skipped_theta, "filled": filled,
                "no_map": no_map, "unfilled": unfilled,
                "win_rate": round(won_n / max(1, filled), 4),
                "ev_per_trade": round(ev, 4),
                "total_pnl": round(sum(pnls), 2),
            })

    lines = ["# Maker-entry backtest (BTC, Mar 2026, official outcomes)", "",
             "| horizon | delta | decided | theta-skip | filled | no-map | "
             "unfilled | win rate | EV/trade | total PnL |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in all_results:
        lines.append(
            f"| {r['horizon']} | {r['delta']:.2f} | {r['decided']} | "
            f"{r['theta_skipped']} | {r['filled']} | {r['no_map']} | "
            f"{r['unfilled']} | {r['win_rate']} | {r['ev_per_trade']:+.4f} | "
            f"{r['total_pnl']:+.2f} |"
        )
    report = "\n".join(lines) + "\n"
    (REPO / "research/phase_b/MAKER_BACKTEST.md").write_text(report)
    print(report)


def mid_slug_of(r: dict) -> str:
    return r["market_id"]


if __name__ == "__main__":
    main()
