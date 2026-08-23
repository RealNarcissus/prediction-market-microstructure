"""s000: R4 baseline — L2 logistic on trailing log returns [f1,f2,f3,f5,f10].

Faithful port of the prior attempt's R4 (Herdr src/models.py): StandardScaler
+ LogisticRegression(penalty=l2, C=1.0, lbfgs, max_iter=1000, random_state=0).
Reference validation MCC: 5m +0.0236, 15m +0.0419 (pooled 2025).
"""
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from locked.data import base_trailing_returns

NAME = "s000_r4_baseline"


def build_features(df: pl.DataFrame) -> np.ndarray:
    return base_trailing_returns(df)


def new_model():
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "logit",
                LogisticRegression(
                    penalty="l2",
                    C=1.0,
                    fit_intercept=True,
                    solver="lbfgs",
                    max_iter=1000,
                    tol=1e-4,
                    class_weight=None,
                    random_state=0,
                ),
            ),
        ]
    )
