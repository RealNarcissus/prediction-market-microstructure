"""s005: champion LightGBM + taker-buy imbalance feature."""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm  # same spec

NAME = "s005_lgbm_plus_imbalance"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    return np.column_stack([base, imb])


def new_model():
    return _lgbm()
