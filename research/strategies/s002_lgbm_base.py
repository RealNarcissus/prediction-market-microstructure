"""s002: LightGBM on the base trailing returns — can trees beat the logit
on MCC out-of-sample, or do they overfit 5m noise?"""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns

NAME = "s002_lgbm_base"


def build_features(df: pl.DataFrame) -> np.ndarray:
    return base_trailing_returns(df)


def new_model():
    return LGBMClassifier(
        n_estimators=300,
        num_leaves=31,
        max_depth=6,
        min_child_samples=2000,
        learning_rate=0.03,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=0,
        n_jobs=4,
        verbose=-1,
    )
