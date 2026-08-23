"""s015: champion + range dynamics (range/ATR6, narrowest-of-5 indicator)."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s015_lgbm_range_dynamics"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    rng_expr = pl.col("high") - pl.col("low")
    feats = df.select(
        [
            (rng_expr / rng_expr.rolling_mean(24).clip(1e-9)).alias("ratr24"),
            (rng_expr / rng_expr.rolling_mean(6).clip(1e-9)).alias("ratr6"),
            (rng_expr <= rng_expr.rolling_min(5)).cast(pl.Float64).alias("nr5"),
        ]
    ).to_numpy()
    return np.column_stack([base, imb, feats])


def new_model():
    return _lgbm()
