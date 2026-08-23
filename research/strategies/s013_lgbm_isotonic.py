"""s013: champion + isotonic calibration on an inner temporal split.

Expectation: MCC ~unchanged or slightly moved (monotone maps can shift the
0.5 crossing); the point is the tail-calibration diagnostic.
"""
from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression

from strategies.s005_lgbm_plus_imbalance import build_features as _feats
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s013_lgbm_isotonic"


class InnerIsotonic:
    """Fit base model on the first 80% (temporal) of train, isotonic on the
    last 20%; predict = calibrated probability."""

    def __init__(self):
        self.base = _lgbm()
        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.classes_ = np.array([0, 1])

    def fit(self, X, y):
        n = len(y)
        cut = int(n * 0.8)
        self.base.fit(X[:cut], y[:cut])
        p_raw = self.base.predict_proba(X[cut:])[:, 1]
        self.iso.fit(p_raw, y[cut:])
        return self

    def predict_proba(self, X):
        p1 = self.iso.predict(self.base.predict_proba(X)[:, 1])
        return np.column_stack([1 - p1, p1])


def build_features(df: pl.DataFrame) -> np.ndarray:
    return _feats(df)


def new_model():
    return InnerIsotonic()
