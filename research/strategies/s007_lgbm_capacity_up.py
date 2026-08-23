"""s007: champion features, LGBM capacity up (leaves 63, depth 8, mcs 1000)."""
from __future__ import annotations

import polars as pl
from lightgbm import LGBMClassifier

from strategies.s005_lgbm_plus_imbalance import build_features  # same features

NAME = "s007_lgbm_capacity_up"


def new_model():
    return LGBMClassifier(
        n_estimators=300,
        num_leaves=63,
        max_depth=8,
        min_child_samples=1000,
        learning_rate=0.03,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=0,
        n_jobs=4,
        verbose=-1,
    )
