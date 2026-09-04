"""s018: champion + range-weighted imbalance (imb * range/ATR24)."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s018_lgbm_weighted_imbalance"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    rng_expr = pl.col("high") - pl.col("low")
    pos, ratr = df.select(
        [
            ((pl.col("close") - pl.col("low")) / rng_expr.clip(1e-9)).alias("pos"),
            (rng_expr / rng_expr.rolling_mean(24).clip(1e-9)).alias("ratr"),
        ]
    ).to_numpy().T
    return np.column_stack([base, imb, pos, ratr, imb * ratr])


def new_model():
    return _lgbm()
