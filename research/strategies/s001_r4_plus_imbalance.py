"""s001: base trailing returns + taker-buy volume imbalance.

imbalance_t = 2*TBV_t/V_t - 1 (Herdr Exp005 formula). Its value there was
in traded-subset economics, not MCC; this tests the MCC question cleanly.
"""
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from locked.data import base_trailing_returns

NAME = "s001_r4_plus_imbalance"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    return np.column_stack([base, imb])


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
