"""s006: LightGBM with heavier regularization — is the champion's gain
robust or an artifact of tree capacity?"""
from __future__ import annotations

import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns

NAME = "s006_lgbm_regularized"


def build_features(df: pl.DataFrame):
    return base_trailing_returns(df)


def new_model():
    return LGBMClassifier(
        n_estimators=300,
        num_leaves=16,
        max_depth=4,
        min_child_samples=5000,
        learning_rate=0.03,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.9,
        reg_lambda=5.0,
        random_state=0,
        n_jobs=4,
        verbose=-1,
    )
