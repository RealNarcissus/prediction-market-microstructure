"""s017: champion + open-gap ((open - prev close)/ATR24)."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s017_lgbm_open_gap"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    rng_expr = pl.col("high") - pl.col("low")
    feats = df.select(
        [
            ((pl.col("close") - pl.col("low"))
             / rng_expr.clip(1e-9)).alias("pos"),
            (rng_expr / rng_expr.rolling_mean(24).clip(1e-9)).alias("ratr"),
            ((pl.col("open") - pl.col("close").shift(1))
             / rng_expr.rolling_mean(24).clip(1e-9)).alias("gap"),
        ]
    ).to_numpy()
    return np.column_stack([base, imb, feats])


def new_model():
    return _lgbm()
