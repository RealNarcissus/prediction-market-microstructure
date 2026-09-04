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

for symbol, asset in [("BTCUSDT","BTC"), ("ETHUSDT","ETH"), ("SOLUSDT","SOL")]:
    bars = pl.read_parquet(str(KL / f"{symbol}_1m.parquet")).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms","UTC")))

    for tf_file, hz, sec in [("5-minute","5m",300), ("15-minute","15m",900)]:
        mk = pl.read_parquet(str(UPD / "markets.parquet")).filter(
            (pl.col("crypto")==asset) & (pl.col("timeframe")==tf_file)
            & pl.col("resolution").is_in([0,1])
        ).with_columns(
            ((pl.col("end_ts") - sec) * 1000).alias("open_ms")
        )
        if mk.height < 20:
            print(f"{asset} {hz}: skip ({mk.height})"); continue

        agg = aggregate_windows(bars, hz)
        X_all = cf(agg)
        opens_all = [int(float(o)) for o in agg["open_time"].dt.epoch("ms").to_list()]
        open_to_idx = {o: i for i, o in enumerate(opens_all)}

        y_official, idx_matched = [], []
        for r in mk.iter_rows(named=True):
            key = int(r["open_ms"])
            if key in open_to_idx and r["resolution"] in (0,1):
                idx_matched.append(open_to_idx[key])
                y_official.append(r["resolution"])

        if len(idx_matched) < 30:
            print(f"{asset} {hz}: only {len(idx_matched)} matched"); continue

        cut_i = int(len(idx_matched)*0.7)
        tr_i = idx_matched[:cut_i]
        ev_i = idx_matched[cut_i:]
        X_tr = X_all[tr_i]; y_tr = np.array([y_official[idx_matched.index(i)] for i in tr_i])
        
        m = cm()
        m.fit(X_tr, y_tr)
        probs_ev = m.predict_proba(X_all[ev_i])[:, list(m.classes_).index(1)]
        y_ev = [y_official[idx_matched.index(i)] for i in ev_i]
        correct = sum(1 for p,o in zip(probs_ev, y_ev) if (p>=0.5)==(o==1))
        acc = correct/max(1,len(ev_outcomes if 'ev_outcomes' in dir() else ev_i))

        print(f"{asset} {hz}: train={cut_i} eval={len(ev_i)} | official acc={acc:.1%}")

print("\nDone")
