"""s003: base returns + realized volatility features.

Rolling std of 1-bar log returns over {6, 24, 96} bars and the ratio of
short to long vol (vol regime). Volatility conditions regime-switching in
short-horizon direction predictability.
"""
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from locked.data import base_trailing_returns

NAME = "s003_r4_plus_realized_vol"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    r1 = (pl.col("close") / pl.col("close").shift(1)).log()
    vol = (
        df.select(
            [r1.rolling_std(k).alias(f"rv{k}") for k in (6, 24, 96)]
        ).to_numpy()
    )
    ratio = vol[:, 0] / np.where(vol[:, 2] > 0, vol[:, 2], np.nan)
    return np.column_stack([base, vol, ratio])


def new_model():
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "logit",
                LogisticRegression(
                    C=1.0, solver="lbfgs", max_iter=1000, random_state=0
                ),
            ),
        ]
    )
