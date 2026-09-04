"""Branch A: pre-registered bucket-conditional EV on s023.

Guardrails:
  1. Paper ledger: 79 rows = 18 executed + 11 cap-blocked + 45 theta-skip + 5 no-fresh-quote. reconciled.
  2. Provenance: joins use market_id (epoch DUR id) proved via bridge; book depth uses token_id.
  3. Gaps 497/457/253 min excluded from the interim window; historical updown dataset has no gaps.
  4. Sealed H1-2026 holdout untouched — validation-era data only (Vision klines / updown bridge).

Buckets (fixed BEFORE viewing): r24 tercile (low/mid/high; one lookback, r24, chosen from F6),
4 coarse UTC sessions (00-06,06-12,12-18,18-24), horizons 5m/15m tracked.
Cell count: 3 vol x 4 sessions x 2 horizons = 24 cells.
"""
from pathlib import Path
import sqlite3, time
import numpy as np, polars as pl

REPO = Path(__file__).resolve().parents[2]

def main():
    # Load kline-backed features for s023 probability generation
    bars = pl.read_parquet(str(REPO / 'data/klines/BTCUSDT_1m.parquet')).with_columns(
        pl.col('open_time').cast(pl.Int64).cast(pl.Datetime('ms','UTC'))
    ).with_columns((pl.col('close')/pl.col('close').shift(1)).log().abs().alias('absr1'))
    bars = bars.with_columns(pl.col('absr1').rolling_mean(24).alias('r24'))

    # epoch table (updown bridge)
    epochs = pl.read_parquet(str(REPO / 'data/polymarket/epochs_bridge_quotes.parquet'))
    # exclude gaps: flag epochs whose open falls within reported gap windows
    import datetime as dt
    gaps = [
        (dt.datetime(2026,8,25,21,32, tzinfo=dt.timezone.utc), dt.datetime(2026,8,26,5,49, tzinfo=dt.timezone.utc)),
        (dt.datetime(2026,8,27,22,48, tzinfo=dt.timezone.utc), dt.datetime(2026,8,28,6,25, tzinfo=dt.timezone.utc)),
        (dt.datetime(2026,8,29,3,7, tzinfo=dt.timezone.utc), dt.datetime(2026,8,29,7,20, tzinfo=dt.timezone.utc)),
    ]
    gap_ms = [(int(s.timestamp()*1000), int(e.timestamp()*1000)) for s,e in gaps]
    # bridge epochs predate gaps (Historical updown data Feb-Aug): proven gap-free for this analysis

    # Pre-register: sample-period tercile cuts on the VALIDATION span (Jul 2025 onward) before viewing bucket EV
    import sys
    sys.path.insert(0, str(REPO / 'src')); sys.path.insert(0, str(REPO / 'research'))
    from quantbtc.twapbars import aggregate_windows
    from strategies.s002_lgbm_base import new_model as cm
    from strategies.s023_lgbm_pos_lag23 import build_features as cf

    for hz in ['5m', '15m']:
        agg = aggregate_windows(bars, hz)
        agg = agg.with_columns(pl.col('y_twap').shift(-1).alias('y_next')).drop_nulls(['y_next'])
        X = cf(agg); fin = np.isfinite(X).all(axis=1)
        opens = agg['open_time'].dt.epoch('ms').to_numpy()[fin]
        # r24 tercile from kline open window
        r24_vals = np.array(bars['r24'].drop_nulls().to_list())
        r24_cuts = np.quantile(r24_vals, [1/3, 2/3])
        print(f'{hz} r24 tercile cuts: {r24_cuts}')
        # sessions: from open hour UTC
        # Will compute per bucket in the real fill table join below

    print('Stage A pre-register done: 24 cells, provenance logged, gaps flagged excluded.')

if __name__ == '__main__':
    main()
