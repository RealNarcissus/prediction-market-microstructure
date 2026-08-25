"""s034: InventionV4 — lean architecture + direct-MCC weight refinement.

Architecture drops the dead nonlinear terms found by weight inspection
(V3: imb_sq/imb_x_pos/streak_x_imb ~ 0). Fit: IRLS init, then a SEEDED
random hill-climb that maximizes MCC ON THE TRAINING FOLD ONLY — training
on the metric we select with. Validation stays untouched by construction.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

RESEARCH = Path(__file__).resolve().parents[1]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from invented.formula import InventedFormula, sigmoid  # noqa: E402

NAME = "s034_invention_v4_mcc"

SIGNALS = ["imb", "pos", "ratr24", "r10", "streak", "flow_switch"]


class MCCFormula(InventedFormula):
    def __init__(self, l2: float = 1.0, iters: int = 25,
                 refine_iters: int = 600, seed: int = 0):
        super().__init__(l2=l2, iters=iters)
        self.refine_iters = refine_iters
        self.seed = seed

    @staticmethod
    def _mcc(y: np.ndarray, p1: np.ndarray) -> float:
        pred = (p1 >= 0.5).astype(int)
        tp = int(((pred == 1) & (y == 1)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        den = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
        if den == 0:
            return 0.0
        return (tp * tn - fp * fn) / den**0.5

    def _p1(self, Z: np.ndarray, w: np.ndarray) -> np.ndarray:
        return sigmoid(Z @ w)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MCCFormula":
        super().fit(X, y)
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        Z = np.column_stack([np.ones(len(X)), (X - self.mu) / self.sd])
        rng = np.random.default_rng(self.seed)

        def mcc(w: np.ndarray) -> float:
            return self._mcc(y.astype(int), self._p1(Z, w))

        best_w, best = self.w.copy(), mcc(self.w)
        for _ in range(self.refine_iters):
            cand = best_w + rng.normal(0, 0.15, size=best_w.shape)
            score = mcc(cand)
            if score > best:
                best_w, best = cand, score
        self.w = best_w
        return self


def build_features(df: pl.DataFrame) -> np.ndarray:
    from invented.formula import core_signals, causal_streak

    sig = core_signals(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)
    switch = np.sign(imb) - np.roll(np.sign(imb), 1)
    switch[0] = np.nan
    streak = causal_streak(sig["pos"] > 0.5)
    cols = {
        "imb": imb,
        "pos": sig["pos"],
        "ratr24": sig["ratr24"],
        "r10": sig["r10"],
        "streak": streak,
        "flow_switch": switch,
    }
    return np.column_stack([cols[k] for k in SIGNALS])


def new_model():
    f = MCCFormula(l2=1.0, refine_iters=600, seed=0)
    f.names = list(SIGNALS)
    return f
