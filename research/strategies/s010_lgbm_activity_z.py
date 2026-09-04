"""s010: champion + activity z-scores (rolling 24-bar z of volume and count)."""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s010_lgbm_activity_z"


def _z(expr):
    m = expr.rolling_mean(24)
    s = expr.rolling_std(24)
    return (expr - m) / (s + 1e-12)


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    z = (
        df.select(
            [
                _z(pl.col("volume")).alias("zv"),
                _z(pl.col("count").cast(pl.Float64)).alias("zc"),
            ]
        ).to_numpy()
    )
    return np.column_stack([base, imb, z])


def new_model():
    return _lgbm()
