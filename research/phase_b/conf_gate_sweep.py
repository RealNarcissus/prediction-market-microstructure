"""Simple conf-gate sweep using bridge quotes + champion predictions."""
import re, sys
from pathlib import Path
import numpy as np, polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "research"))
from quantbtc.twapbars import aggregate_windows
from strategies.s002_lgbm_base import new_model as cm
from strategies.s023_lgbm_pos_lag23 import build_features as cf

KL = REPO / "data/klines"
HERDR = Path("/home/charleton/Desktop/agentProjects/Herdr/quant-btc/data/raw/btcusdt-usdtm-1m.parquet")
THETAS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]
CUT = int(np.datetime64("2026-03-01").astype("datetime64[ms]").astype(int))

results = []
for symbol, asset in [("BTCUSDT","BTC"),("ETHUSDT","ETH"),("SOLUSDT","SOL")]:
    kl_path = KL / f"{symbol}_1m.parquet"
    bars = pl.read_parquet(str(kl_path)).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms","UTC")))

    for tf_file, hz, sec in [("5-minute","5m",300), ("15-minute","15m",900)]:
        agg = aggregate_windows(bars, hz)
        agg = agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next")).drop_nulls(["y_next"])
        X = cf(agg); y = agg["y_next"].to_numpy().astype(int)
        fin = np.isfinite(X).all(axis=1)
        opens = agg["open_time"].dt.epoch("ms").to_numpy()
        m = cm(); m.fit(X[fin & (opens<CUT)], y[fin & (opens<CUT)])
        probs = m.predict_proba(X)[:, list(m.classes_).index(1)]

        # load polymarket epochs with outcomes AND quotes
        epath = REPO / "data/polymarket/epochs_bridge_quotes.parquet"
        epochs = pl.read_parquet(str(epath)).filter(
            (pl.col("asset")==asset) & (pl.col("horizon")==hz)
            & pl.col("outcome").is_not_null() & pl.col("entry_ask_up").is_not_null())

        n_match = 0
        for r in epochs.iter_rows(named=True):
            slug = r["market_id"]
            mm = re.search(r"-(\d{10})$", slug)
            if not mm:
                # try matching by open time from bridge
                oms = int(r["open_time_utc"].timestamp()*1000)
                p = next((pv for o,pv in ((o2,pv2) for o2,pv2 in
                    zip(opens[fin], probs[fin]) if abs(o2-oms) < 60_000)), None)
                if p is None: continue
                n_match += 1
            else:
                prev_open = int(mm.group(1))*1000 - sec*1000
                pidx = np.searchsorted(np.sort(opens[fin]), prev_open)
                sorted_opens = np.sort(opens[fin])
                if pidx < len(sorted_opens) and sorted_opens[pidx] == prev_open:
                    orig_idx = np.flatnonzero(fin & (opens==sorted_opens[pidx]))[0]
                    p = float(probs[orig_idx])
                else:
                    continue
                n_match += 1

            if p is None: continue
            won_up = r["outcome"] == "Up"
            side_up = p >= 0.5
            won = won_up == side_up

            # entry: use whichever ask is lower (our model picks side)
            entry = r["entry_ask_up"] if side_up else r["entry_ask_down"]
            if entry is None or entry <= 0.01 or entry >= 0.99:
                entry = 0.50

            fee = 0.07 * entry * (1 - entry)
            pnl = ((1 - entry) - fee) if won else (-entry - fee)

            for theta in THETAS:
                if abs(p - 0.5) > theta:
                    results.append({"theta":theta, "asset":asset,
                        "hz":hz, "won":won, "pnl":pnl})

        print(f"  {asset} {hz}: {n_match} matched")

df = pl.DataFrame(results)
print(f"\ntotal rows across all theta levels: {df.height}")
if df.is_empty():
    print("no results"); sys.exit()

print("\n=== EV BY CONFIDENCE THRESHOLD ===")
agg_t = df.group_by("theta").agg(
    pl.len().alias("n"), pl.col("won").mean().alias("wr"),
    pl.col("pnl").mean().alias("ev"), pl.col("pnl").sum().alias("tot")
).sort("theta")

lines = ["| theta | fills | win | EV/trade | total PnL |", "|---|---|---|---|---|"]
for r in agg_t.iter_rows(named=True):
    marker = " <- POSITIVE" if r["ev"] > 0 and r["theta"] >= 0.08 else ""
    print(f"theta={r['theta']:.2f}: n={r['n']}, win={r['wr']:.1%}, EV={r['ev']:+.4f}{marker}")
    lines.append(f"| {r['theta']:.2f} | {r['n']} | {r['wr']:.1%} | {r['ev']:+.4f} | {r['tot']:+.2f} |")

out = Path(__file__).resolve().parents[1] / "CONF_GATE_SWEEP.md"
Path(out).write_text("\n".join(lines) + "\n")
print(f"wrote {out}")
