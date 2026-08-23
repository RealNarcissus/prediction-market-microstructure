"""Aggregate 1m bars into non-overlapping 5m/15m windows with BOTH labels:

- endpoint label: last 1m close of the window vs strike (classic)
- TWAP label (proxy for Jupiter's Chainlink TWAP resolution):
  mean of 1m closes in the window vs the window's first 1m open

Jupiter resolves "Up" iff the Chainlink TWAP over the window is >= the price
at window start. The 1m-close mean is the best proxy available from exchange
data; divergence vs the true oracle is measured separately against live
resolutions (docs/RECON.md open question 1).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

AGG_MIN = {"5m": 5, "15m": 15}


def aggregate_windows(
    bars_1m: pl.DataFrame, horizon: str
) -> pl.DataFrame:
    """1m bars -> non-overlapping windows aligned to clock boundaries.

    Returns one row per window with OHLCV aggregates, twap (mean of 1m
    closes), strike (first 1m open), and both labels.
    """
    m = AGG_MIN[horizon]
    df = bars_1m.with_columns(
        (pl.col("open_time").dt.truncate(f"{m}m")).alias("win")
    )
    agg = df.group_by("win").agg(
        pl.col("open").first().alias("open"),
        pl.col("high").max().alias("high"),
        pl.col("low").min().alias("low"),
        pl.col("close").last().alias("close"),
        pl.col("volume").sum().alias("volume"),
        pl.col("taker_buy_base_volume").sum().alias("taker_buy_base_volume"),
        pl.col("count").sum().alias("count"),
        pl.col("close").mean().alias("twap"),
    )
    # only keep complete windows (full m minutes of 1m bars)
    counts = df.group_by("win").len().select(["win", "len"])
    agg = agg.join(counts, on="win").filter(pl.col("len") == m).drop("len")
    agg = agg.with_columns(pl.col("open").alias("strike"))
    agg = agg.with_columns(
        (pl.col("twap") >= pl.col("strike")).cast(pl.Int8).alias("y_twap"),
        (pl.col("close") >= pl.col("strike")).cast(pl.Int8).alias("y_end"),
    ).sort("win")
    return agg.rename({"win": "open_time"})


def load_1m(parquet_path: str | Path) -> pl.DataFrame:
    df = pl.read_parquet(parquet_path).sort("open_time")
    if df.schema["open_time"].time_zone is None:
        df = df.with_columns(pl.col("open_time").dt.replace_time_zone("UTC"))
    return df


def label_disagreement(agg: pl.DataFrame) -> float:
    """Fraction of windows where endpoint and TWAP labels differ — the gap
    between what Phase A modeled and what Jupiter actually pays on."""
    return float((agg["y_twap"] != agg["y_end"]).mean())
