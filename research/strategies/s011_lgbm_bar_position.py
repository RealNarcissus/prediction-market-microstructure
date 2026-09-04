"""s011: champion + intra-bar position (close within range) and range/ATR."""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s011_lgbm_bar_position"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    feats = df.select(
        [
            ((pl.col("close") - pl.col("low"))
             / (pl.col("high") - pl.col("low") + 1e-9)).alias("pos"),
            ((pl.col("high") - pl.col("low"))
             / (pl.col("high") - pl.col("low")).rolling_mean(24).clip(1e-9)
             ).alias("ratr"),
        ]
    ).to_numpy()
    return np.column_stack([base, imb, feats])


def new_model():
    return _lgbm()
