"""Persistent flow-bias snapshot — bakeoff infrastructure (round 232/233).

The kline store is ROLLING (~13h retention), so the BOCPD window slides
instead of extending. This script merges whatever bias history the store
currently holds into an append-only parquet (data/flowbias_BTCUSDT.parquet,
deduplicated by ts_ms), so repeated runs ACCUMULATE history beyond the
rolling window. bocpd.py --snapshot then reads the accumulated file.

Research-only; writes only data/flowbias_BTCUSDT.parquet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
SNAP = REPO / "data" / "flowbias_{sym}.parquet"


def bias_from_store(symbol: str):
    import polars as pl

    d = RAW / symbol / "kline_1m"
    files = sorted(d.glob("*.parquet"))
    if not files:
        raise SystemExit(f"no kline files under {d}")
    df = pl.concat([pl.read_parquet(str(f)) for f in files])
    tb_col = "taker_buy_volume" if "taker_buy_volume" in df.columns else "taker_buy_base_volume"
    df = df.sort("ts_ms").unique(subset=["ts_ms"], keep="last", maintain_order=True)
    vol = df["volume"].to_numpy().astype(float)
    tb = df[tb_col].to_numpy().astype(float)
    ts = df["ts_ms"].to_numpy().astype(np.int64)
    ok = np.isfinite(vol) & np.isfinite(tb) & (vol > 0)
    bias = np.full(len(vol), np.nan)
    bias[ok] = (tb[ok] - vol[ok] / 2.0) / vol[ok]
    keep = np.isfinite(bias)
    return ts[keep], bias[keep]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    args = ap.parse_args()

    import polars as pl

    ts, bias = bias_from_store(args.symbol)
    new = pl.DataFrame({"ts_ms": ts, "bias": bias})
    out = Path(str(SNAP).format(sym=args.symbol))

    if out.exists():
        old = pl.read_parquet(str(out))
        merged = pl.concat([old, new]).sort("ts_ms").unique(
            subset=["ts_ms"], keep="first", maintain_order=True)
    else:
        merged = new
    merged.write_parquet(str(out))
    added = merged.height - (old.height if out.exists() and 'old' in dir() else 0)
    print(f"snapshot {out.name}: {merged.height:,} minutes "
          f"({merged['ts_ms'].min()} .. {merged['ts_ms'].max()}), "
          f"+{max(0, added):,} new")


if __name__ == "__main__":
    main()
