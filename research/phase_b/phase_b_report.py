"""Phase B: train on official Jupiter resolutions + live quote data.

This is THE test that determines whether the project has legs. For each
epoch with both collector quotes and official resolution:
  - Features from Binance klines (same as Phase A champion)
  - Label = official Polymarket/Jupiter resolution (not TWAP proxy)
  - Market-implied entry price = actual Jupiter ask at decision time
  - EV = model edge vs market implied probability, after fees

Outputs:
  research/phase_b/PHASE_B_REPORT.md
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))

from quantbtc.fees import order_fee  # noqa: E402
from quantbtc.twapbars import aggregate_windows, load_1m  # noqa: E402
from strategies.s002_lgbm_base import new_model as champ_model  # noqa: E402
from strategies.s023_lgbm_pos_lag23 import build_features as champ_feats  # noqa: E402

DATA = REPO / "data/polymarket"
HERDR_1M = Path(
    "/home/charleton/Desktop/agentProjects/Herdr/quant-btc/data/raw/"
    "btcusdt-usdtm-1m.parquet"
)
KLINES = REPO / "data/klines"


def load_collector_epochs() -> pl.DataFrame:
    """Extract resolved epochs with quote data from the collector."""
    conn = sqlite3.connect(str(REPO / "data/collector.db"))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT m.market_id, m.asset, m.horizon_s,
               m.open_time_ms, m.close_time_ms,
               r.outcome,
               q.entry_bid_up, q.entry_ask_up,
               q.entry_bid_down, q.entry_ask_down
        FROM resolutions r
        JOIN markets m ON m.market_id = r.market_id
        LEFT JOIN (
            SELECT market_id,
                   MAX(CASE WHEN side='up' THEN bid END) as entry_bid_up,
                   MAX(CASE WHEN side='up' THEN ask END) as entry_ask_up,
                   MAX(CASE WHEN side='down' THEN bid END) as entry_bid_down,
                   MAX(CASE WHEN side='down' THEN ask END) as entry_ask_down
            FROM quotes
            GROUP BY market_id
        ) q ON q.market_id = r.market_id
        WHERE r.outcome IN ('up', 'down')
          AND m.asset IS NOT NULL
    """).fetchall()

    conn.close()
    return pl.DataFrame([dict(r) for r in rows])


def main() -> None:
    print("=== PHASE B: Official-Label Training & Market Baseline ===\n")

    # 1. Load collector epochs
    epochs = load_collector_epochs()
    print(f"Collector epochs with quotes+resolutions: {epochs.height}")

    # 2. Load Binance klines per asset for features
    klines_cache = {}
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        kl_path = KLINES / f"{symbol}_1m.parquet"
        if kl_path.exists():
            klines_cache[symbol] = pl.read_parquet(str(kl_path)).with_columns(
                pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
            )

    # 3. For each asset×horizon: build features and evaluate
    all_results = []

    for symbol, asset in [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"), ("SOLUSDT", "SOL")]:
        kl_path = KLINES / f"{symbol}_1m.parquet"
        if not kl_path.exists():
            continue
        bars = pl.read_parquet(str(kl_path)).with_columns(
            pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
        )

        for hz_str, sec in [("5m", 300), ("15m", 900)]:
            sub = epochs.filter(
                (pl.col("asset") == asset) & (pl.col("horizon_s") == sec)
            )
            if sub.height < 20:
                continue

            # Build feature frame from klines aggregated to this horizon
            agg = aggregate_windows(bars, hz_str)
            agg = agg.with_columns(
                pl.col("y_twap").shift(-1).alias("y_proxy")
            ).drop_nulls(["y_proxy"])

            # Match collector epochs to agg windows by open_time
            agg_ms = agg["open_time"].dt.epoch("ms").to_numpy()
            X_all = champ_feats(agg)
            fin = np.isfinite(X_all).all(axis=1)

            # For each collector epoch, find matching window and get prediction + quotes
            matched = []
            for r in sub.iter_rows(named=True):
                open_ms = int(r["open_time_ms"])
                idx = int(np.searchsorted(agg_ms, open_ms))
                if idx >= len(agg_ms) or agg_ms[idx] != open_ms:
                    continue
                if not fin[idx]:
                    continue
                matched.append({
                    "idx": idx,
                    "p": None,  # filled below
                    "market_id": r["market_id"],
                    "outcome": r["outcome"],
                    "ask_up": r["entry_ask_up"],
                    "ask_dn": r["entry_ask_down"],
                })

            if len(matched) < 10:
                print(f"  {asset} {hz_str}: only {len(matched)} matched — skipping")
                continue

            # Walk-forward predictions on official labels
            outcomes = []
            for m_rec in matched:
                i = m_rec["idx"]
                won_up = (
                    (r_outcome := next(
                        (rr["outcome"] for rr in sub.iter_rows(named=True)
                         if rr["market_id"] == m_rec["market_id"]), ""
                    )) == "Up"
                )
                outcomes.append(1 if won_up else 0)
                m_rec["y"] = 1 if won_up else 0

            ys = np.array([m["y"] for m in matched])
            xs_idx = [m["idx"] for m in matched]

            # Simple temporal split: first 70% train, last 30% eval
            n_train = int(len(matched) * 0.7)
            train_recs = matched[:n_train]
            eval_recs = matched[n_train:]

            if len(eval_recs) < 5 or len(train_recs) < 10:
                print(f"  {asset} {hz_str}: insufficient split ({len(train_recs)} train, {len(eval_recs)} eval)")
                continue

            # Train on official outcomes
            X_tr = X_all[[m["idx"] for m in train_recs]]
            y_tr = np.array([m["y"] for m in train_recs])
            fin_tr = np.isfinite(X_tr).all(axis=1)
            model = champ_model()
            y_tr_fin = y_tr[fin_tr]
            if len(np.unique(y_tr_fin)) < 2:
                print(f"  {asset} {hz_str}: single-class training set — skipping")
                continue
            model.fit(X_tr[fin_tr], y_tr[fin_tr])

            # Predict on eval set
            X_ev = X_all[[m["idx"] for m in eval_recs]]
            fin_ev = np.isfinite(X_ev).all(axis=1)
            probs = model.predict_proba(X_ev[fin_ev])[:, list(model.classes_).index(1)]

            correct = 0
            evs = []
            for j, m_rec in enumerate(eval_recs):
                p_model = float(probs[j])
                outcome_up = m_rec["y"] == 1
                pred_correct = (p_model >= 0.5) == outcome_up
                correct += int(pred_correct)

                # EV calculation at market ask
                ask = m_rec["entry_ask_up"] if p_model >= 0.5 else m_rec["entry_ask_down"]
                if ask is not None and 0.01 < ask < 0.99:
                    fee = order_fee(ask, 1)
                    won = ((p_model >= 0.5) == outcome_up)
                    pnl = ((1 - ask) - fee) if won else (-ask - fee)
                    evs.append(pnl)

                m_rec["p_model"] = p_model
                m_rec["pred_correct"] = pred_correct
                m_rec["ask"] = ask
                m_rec["ev"] = evs[-1] if len(evs) > len(evs) - 1 else None

            acc = correct / max(1, len(eval_recs))
            mean_ev = float(np.mean(evs)) if evs else 0.0
            pos_ev = sum(1 for e in evs if e > 0)

            # Compare vs TWAP-proxy label accuracy (what would Phase-A model get?)
            all_results.append({
                "asset": asset, "hz": hz,
                "n_matched": len(matched),
                "n_train": len(train_recs), "n_eval": len(eval_recs),
                "official_accuracy": round(acc, 4),
                "mean_entry_ask": round(np.mean([
                    m["ask"] for m in eval_recs if m["ask"]
                ]), 4) if any(m["ask"] for m in eval_recs) else None,
                "mean_ev": round(mean_ev, 4),
                "positive_ev_count": pos_ev,
                "eval_count_with_price": len(evs),
            })

            print(f"  {asset} {hz_str}: {len(matched)} matched | "
                  f"train={n_train} eval={len(eval_recs)} | "
                  f"official-label accuracy={acc:.1%} | "
                  f"mean EV at market ask={mean_ev:+.4f}")

    # Summary
    lines = [
        "# Phase B Report — Official Label Training", "",
        "First training run using OFFICIAL Jupiter resolutions instead of",
        "TWAP proxies. Entry priced at ACTUAL Jupiter asks.", "",
        "| asset | hz | matched | train | eval | official acc | avg ask | mean EV | +EV count |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in all_results:
        lines.append(
            f"| {r['asset']} | {r['hz']}s | {r['n_matched']} | "
            f"{r['n_train']} | {r['n_eval']} | {r['official_accuracy']:.1%} | "
            f"{r['mean_entry_ask']} | {r['mean_ev']:+.4f} | {r['positive_ev_count']} |"
        )

    lines += [
        "", "## Key questions this answers:", "",
        "1. Does the model trained on official outcomes beat random?",
        "2. Is the model's edge sufficient to overcome Jupiter fees?",
        "3. How does official-label training compare to TWAP-proxy training?",
        "",
        "## Interpretation guide:",
        "- If official-label accuracy ≈ TWAP-proxy accuracy → basis risk is low",
        "- If mean EV > 0 at market asks → strategy has live edge",
        "- If neither → wait for more data or pivot approach",
    ]

    out_md = REPO / "research" / "phase_b" / "PHASE_B_REPORT.md"
    Path(out_md).write_text("\n".join(lines) + "\n")
    print(f"\nwrote {out_md}")


if __name__ == "__main__":
    main()
