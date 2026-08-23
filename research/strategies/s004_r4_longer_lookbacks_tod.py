"""s004: longer lookbacks (f20, f50) + time-of-day cyclical features."""
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from locked.data import base_trailing_returns

NAME = "s004_r4_longer_lookbacks_tod"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    c = df["close"]
    f20 = (c / c.shift(20)).log().to_numpy()
    f50 = (c / c.shift(50)).log().to_numpy()
    minute_of_day = (
        df["open_time"].dt.hour() * 60 + df["open_time"].dt.minute()
    ).to_numpy()
    tod_sin = np.sin(2 * np.pi * minute_of_day / 1440.0)
    tod_cos = np.cos(2 * np.pi * minute_of_day / 1440.0)
    return np.column_stack([base, f20, f50, tod_sin, tod_cos])


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
