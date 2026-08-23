"""s021: champion s018 + causal position streak + pos_{t-1} (s020's ideas).

Self-contained: does not import uncommitted strategies.
"""
from __future__ import annotations

import numpy as np
import polars as pl
from lightgbm import LGBMClassifier

from locked.data import base_trailing_returns

NAME = "s021_lgbm_s018_plus_causal_streak"


def _causal_streak(up: np.ndarray) -> np.ndarray:
    u = up.astype(int)
    n = len(u)
    change = np.zeros(n, dtype=bool)
    change[0] = True
    change[1:] = np.diff(u) != 0
    idx = np.arange(n)
    last_change = np.maximum.accumulate(np.where(change, idx, 0))
    length = idx - last_change + 1
    return np.where(u == 1, length, -length)


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)
    rng_expr = pl.col("high") - pl.col("low")
    pos, ratr = df.select(
        [
            ((pl.col("close") - pl.col("low")) / rng_expr.clip(1e-9)).alias("pos"),
            (rng_expr / rng_expr.rolling_mean(24).clip(1e-9)).alias("ratr"),
        ]
    ).to_numpy().T
    pos_prev = np.roll(pos, 1)
    pos_prev[0] = np.nan
    streak = _causal_streak(pos > 0.5)
    return np.column_stack(
        [base, imb, pos, ratr, imb * ratr, pos_prev, streak]
    )


def new_model():
    return LGBMClassifier(
        n_estimators=300, num_leaves=31, max_depth=6, min_child_samples=2000,
        learning_rate=0.03, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.9, reg_lambda=1.0, random_state=0, n_jobs=4,
        verbose=-1,
    )
