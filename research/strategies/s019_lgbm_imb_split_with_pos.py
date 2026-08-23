"""s019: re-test imbalance as buy/sell columns, now that bar-position is in."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s019_lgbm_imb_split_with_pos"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    buy = np.where(v > 0, tbv / v, 0.0)
    sell = np.where(v > 0, (v - tbv) / v, 0.0)
    rng_expr = pl.col("high") - pl.col("low")
    feats = df.select(
        [
            ((pl.col("close") - pl.col("low")) / rng_expr.clip(1e-9)).alias("pos"),
            (rng_expr / rng_expr.rolling_mean(24).clip(1e-9)).alias("ratr"),
        ]
    ).to_numpy()
    return np.column_stack([base, buy, sell, feats])


def new_model():
    return _lgbm()
