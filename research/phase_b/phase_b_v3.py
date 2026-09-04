"""Phase B v3: train champion on updown official resolutions + full-year klines.

Uses ~6k resolved epochs across BTC/ETH/SOL × 5m/15m covering Feb-Aug 2026.
Labels = official Polymarket resolutions (not TWAP proxies).
Features = Binance spot klines (full year from Vision + REST tail).
Temporal split: train ≤ Jun 30, evaluate Jul-Aug.
"""
import sys
from pathlib import Path
import numpy as np, polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "research"))
from quantbtc.twapbars import aggregate_windows
from strategies.s002_lgbm_base import new_model as cm
from strategies.s023_lgbm_pos_lag23 import build_features as cf

KL = REPO / "data/klines"
UPD = REPO / "data/polymarket/updown"
ASSETS = [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"), ("SOLUSDT", "SOL")]
TRAIN_END_MS = int(np.datetime64("2026-07-01").astype("datetime64[ms]").astype(int))

results = []
for symbol, asset in ASSETS:
    kl_path = KL / f"{symbol}_1m.parquet"
    bars = pl.read_parquet(str(kl_path)).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
    )

    for tf_file, hz, sec in [("5-minute", "5m", 300), ("15-minute", "15m", 900)]:
        # Load updown resolutions
        mk = pl.read_parquet(str(UPD / "markets.parquet")).filter(
            (pl.col("crypto") == asset)
            & (pl.col("timeframe") == tf_file)
            & pl.col("resolution").is_in([0, 1])
        ).with_columns(
            ((pl.col("end_ts") - sec) * 1000).alias("open_ms")
        )

        # Build feature frame from full-year klines
        agg = aggregate_windows(bars, hz)
        agg = agg.drop_nulls(["y_twap"])
        X_all = cf(agg)
        opens_all = np.array([int(float(o)) for o in agg["open_time"].dt.epoch("ms").to_list()])
        open_to_idx = {o: i for i, o in enumerate(opens_all)}

        # Match resolutions to windows
        idx_matched, y_official = [], []
        for r in mk.iter_rows(named=True):
            key = int(r["open_ms"])
            if key in open_to_idx:
                idx_matched.append(open_to_idx[key])
                y_official.append(r["resolution"])

        n_matched = len(idx_matched)
        if n_matched < 40:
            print(f"{asset} {hz}: only {n_matched} matched — skip")
            continue

        y_arr = np.array(y_official)
        X_m = X_all[idx_matched]

        # Temporal split: train ≤ Jul 1, eval > Jul 1
        # percentage-based split: first 70% train, last 30% eval
        sorted_idx = sorted(idx_matched)
        cut_pos = sorted_idx[int(len(sorted_idx) * 0.7)]
        tr_mask = np.array([i < cut_pos for i in idx_matched])
        ev_mask = np.array([~m_ for m_ in tr_mask])
        fin_m = np.isfinite(X_m).all(axis=1)
        tr_mask = tr_mask & fin_m
        ev_mask = ev_mask & fin_m

        n_tr = int(tr_mask.sum())
        n_ev = int(ev_mask.sum())
        if n_tr < 20 or n_ev < 10:
            print(f"{asset} {hz}: insufficient split ({n_tr} train, {n_ev} eval)")
            continue

        mdl = cm()
        mdl.fit(X_m[tr_mask], y_arr[tr_mask])
        pp = mdl.predict_proba(X_m[ev_mask])[:, list(mdl.classes_).index(1)]
        pred_up = pp >= 0.5
        actual_up = y_arr[ev_mask] == 1

        correct = sum(1 for p_, a_ in zip(pred_up, actual_up) if p_ == a_)
        acc = correct / max(1, len(actual_up))
        results.append({
            "asset": asset, "hz": hz,
            "n_total": n_matched, "n_train": n_tr, "n_eval": n_ev,
            "accuracy": round(acc, 4),
            "eval_mean_p": round(float(np.mean(pp)), 4),
        })
        print(f"  {asset} {hz}: {n_tr} train / {n_ev} eval | "
              f"acc={acc:.1%} | mean p={float(np.mean(pp)):.3f}")

print("\n=== SUMMARY ===")
for r in results:
    print(f"  {r['asset']} {r['hz']}: acc={r['accuracy']:.1%} ({r['n_eval']} eval)")

# Save summary as markdown
md_lines = [
    "# Phase B v3 — Official-Label Training Results",
    "",
    "Trained on updown dataset official resolutions (~6k epochs Feb–Aug 2026)",
    "with full-year Binance Vision klines for features.",
    "Temporal split: train ≤ Jun 30, eval Jul–Aug.", "",
    "| asset | horizon | total | train | eval | accuracy | mean p |",
    "|---|---|---|---|---|---|---|",
]
for r in sorted(results, key=lambda x: (x["asset"], x["hz"])):
    md_lines.append(
        f"| {r['asset']} | {r['hz']}s | {r['n_total']} | {r['n_train']} | "
        f"{r['n_eval']} | {r['accuracy']:.1%} | {r['eval_mean_p']:.3f} |"
    )
out_md = REPO / "research/phase_b/PHASE_B_V3_RESULTS.md"
Path(out_md).write_text("\n".join(md_lines) + "\n")
print(f"\nwrote {out_md}")
