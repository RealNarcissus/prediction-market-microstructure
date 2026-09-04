"""s012: ensemble — mean of champion LGBM and R4 logistic probabilities."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s000_r4_baseline import new_model as _logit
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s012_ensemble_lgbm_logit"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    return np.column_stack([base, imb])


class MeanEnsemble:
    def __init__(self):
        self.a = _lgbm()
        self.b = _logit()
        self.classes_ = np.array([0, 1])

    def fit(self, X, y):
        self.a.fit(X, y)
        self.b.fit(X, y)
        return self

    def predict_proba(self, X):
        pa = self.a.predict_proba(X)[:, 1]
        pb = self.b.predict_proba(X)[:, 1]
        p1 = 0.5 * pa + 0.5 * pb
        return np.column_stack([1 - p1, p1])


def new_model():
    return MeanEnsemble()
