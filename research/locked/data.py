"""Data loading and labels — ported verbatim from the Herdr EXPERIMENT-001
semantics (src/data.py of the prior attempt).

Label for bar i uses bar i+1's open->close move (y[i] = 1 if C[i+1] > O[i+1]);
features for bar i use information up to bar i's close only. No lookahead.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

MAX_LOOKBACK = 10
BASE_FEATURES = (1, 2, 3, 5, 10)


def load_bars(parquet_path: str | Path) -> pl.DataFrame:
    df = pl.read_parquet(parquet_path).sort("open_time")
    if df.schema["open_time"].time_zone is None:
        df = df.with_columns(pl.col("open_time").dt.replace_time_zone("UTC"))
    required = {"open_time", "open", "close", "volume", "taker_buy_base_volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing columns {missing} in {parquet_path}")
    return df


def compute_labels(df: pl.DataFrame) -> pl.DataFrame:
    """Attach target_y (next bar open->close direction) and target_z (log move).

    The final bar has no next bar and is dropped, along with the warmup rows
    needed by trailing features (MAX_LOOKBACK).
    """
    o = df["open"].to_numpy()
    c = df["close"].to_numpy()
    y = np.where(c[1:] > o[1:], 1.0, 0.0)
    z = np.log(c[1:] / o[1:])
    out = df.slice(0, len(df) - 1).with_columns(
        pl.Series("target_y", y), pl.Series("target_z", z)
    )
    return out.slice(MAX_LOOKBACK)  # drop feature warmup rows


def base_trailing_returns(df: pl.DataFrame) -> np.ndarray:
    """f_k = ln(close_t / close_{t-k}) for k in BASE_FEATURES -> (n, 5)."""
    c = df["close"]
    cols = [(c / c.shift(k)).log().alias(f"f_{k}") for k in BASE_FEATURES]
    feats = df.select(cols)
    return feats.to_numpy()
