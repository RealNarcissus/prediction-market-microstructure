"""s022: s021 + causal streak of the imbalance sign (imb > 0 streaks)."""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns
from strategies.s021_lgbm_s018_plus_causal_streak import _causal_streak

NAME = "s022_lgbm_pos_and_imb_streaks"


def build_features(df: pl.DataFrame) -> np.ndarray:
    from strategies.s021_lgbm_s018_plus_causal_streak import (
        build_features as _s021,
    )

    x = _s021(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)
    imb_streak = _causal_streak(imb > 0)
    return np.column_stack([x, imb_streak])


def new_model():
    return LGBMClassifier(
        n_estimators=300, num_leaves=31, max_depth=6, min_child_samples=2000,
        learning_rate=0.03, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.9, reg_lambda=1.0, random_state=0, n_jobs=4,
        verbose=-1,
    )
