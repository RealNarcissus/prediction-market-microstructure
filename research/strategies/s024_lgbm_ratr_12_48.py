"""s024: champion s018 + multi-horizon range (ratr12, ratr48)."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s018_lgbm_weighted_imbalance import build_features as _s018
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s024_lgbm_ratr_12_48"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _s018(df)
    rng_expr = pl.col("high") - pl.col("low")
    extra = df.select(
        [
            (rng_expr / rng_expr.rolling_mean(12).clip(1e-9)).alias("r12"),
            (rng_expr / rng_expr.rolling_mean(48).clip(1e-9)).alias("r48"),
        ]
    ).to_numpy()
    return np.column_stack([x, extra])


def new_model():
    return _lgbm()
