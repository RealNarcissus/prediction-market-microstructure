"""s025: full merge — s023 (pos lags) + s021 (causal streak, pos_prev)."""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns
from strategies.s021_lgbm_s018_plus_causal_streak import _causal_streak
from strategies.s023_lgbm_pos_lag23 import build_features as _s023

NAME = "s025_lgbm_full_merge"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _s023(df)  # base, imb, pos, ratr, imb*ratr, pos_{t-2}, pos_{t-3}
    rng_expr = pl.col("high") - pl.col("low")
    pos = df.select(
        ((pl.col("close") - pl.col("low")) / rng_expr.clip(1e-9)).alias("p")
    ).to_numpy().T[0]
    pos_prev = np.roll(pos, 1)
    pos_prev[0] = np.nan
    streak = _causal_streak(pos > 0.5)
    return np.column_stack([x, pos_prev, streak])


def new_model():
    return LGBMClassifier(
        n_estimators=300, num_leaves=31, max_depth=6, min_child_samples=2000,
        learning_rate=0.03, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.9, reg_lambda=1.0, random_state=0, n_jobs=4,
        verbose=-1,
    )
