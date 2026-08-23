"""s009: imbalance split into buy/sell pressure columns instead of one ratio."""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s009_lgbm_imbalance_split"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    buy = np.where(v > 0, tbv / v, 0.0)
    sell = np.where(v > 0, (v - tbv) / v, 0.0)
    return np.column_stack([base, buy, sell])


def new_model():
    return _lgbm()
