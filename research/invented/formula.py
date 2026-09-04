"""The Invention: a parametric prediction-market edge formula.

    P(window TWAP >= strike) = sigma( w0 + SUM_i w_i * z(s_i) )

where s_i are standardized microstructure signals computed from COMPLETED
bars only (no lookahead), z() is fold-local standardization, and the weights
w are fitted by iteratively reweighted least squares (IRLS) on walk-forward
training folds with L2 regularization.

Design intent (vs Phase-A LightGBM champion):
- interpretable closed form: every weight is readable and auditable
- cheap inference for live paper trading
- the autoresearch loop evolves the SIGNAL SET and REGULARIZATION
  (the "architecture"), while IRLS finds the best weights ("training")
"""
from __future__ import annotations

import numpy as np


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


class InventedFormula:
    """IRLS-fitted logistic formula over standardized signals."""

    def __init__(self, l2: float = 1.0, iters: int = 25):
        self.l2 = l2
        self.iters = iters
        self.w: np.ndarray | None = None      # [w0, w1..wk]
        self.mu: np.ndarray | None = None     # signal means (train)
        self.sd: np.ndarray | None = None     # signal sds (train)
        self.names: list[str] | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "InventedFormula":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        self.mu = X.mean(axis=0)
        sd = X.std(axis=0)
        sd[sd < 1e-12] = 1.0
        self.sd = sd
        Z = np.column_stack([np.ones(len(X)), (X - self.mu) / self.sd])
        w = np.zeros(Z.shape[1])
        for _ in range(self.iters):
            p = sigmoid(Z @ w)
            W = np.clip(p * (1 - p), 1e-6, None)
            grad = Z.T @ (y - p) - self.l2 * w
            H = (Z.T * W) @ Z + self.l2 * np.eye(Z.shape[1])
            try:
                step = np.linalg.solve(H, grad)
            except np.linalg.LinAlgError:
                step = np.linalg.lstsq(H, grad, rcond=None)[0]
            w = w + step
        self.w = w
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        Z = np.column_stack([np.ones(len(X)), (X - self.mu) / self.sd])
        p1 = sigmoid(Z @ self.w)
        return np.column_stack([1 - p1, p1])

    @property
    def classes_(self):
        return np.array([0, 1])

    def weight_report(self) -> str:
        lines = ["w0(intercept)=%+.4f" % self.w[0]]
        for name, wi in zip(self.names or [], self.w[1:]):
            lines.append(f"  {name:16s} {wi:+.4f}")
        return "\n".join(lines)


# ---- the signal set (each computable at epoch open from completed bars) --

import polars as pl  # noqa: E402


def core_signals(df) -> dict:  # df: polars DataFrame -> {name: array}
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)

    rng = df["high"].to_numpy() - df["low"].to_numpy()
    pos = np.where(
        rng > 0,
        (df["close"].to_numpy() - df["low"].to_numpy()) / np.where(rng > 0, rng, 1.0),
        0.5,
    )

    c = df["close"]
    r10 = (c / c.shift(10)).log().to_numpy()

    ratr24 = (
        df.select(
            ((pl.col("high") - pl.col("low"))
             / ((pl.col("high") - pl.col("low")).rolling_mean(24).clip(1e-9))
             ).alias("r")
        ).to_numpy().T[0]
    )
    return {"imb": imb, "pos": pos, "ratr24": ratr24, "r10": r10}


def causal_streak(up: np.ndarray) -> np.ndarray:
    u = up.astype(int)
    n = len(u)
    change = np.zeros(n, dtype=bool)
    change[0] = True
    change[1:] = np.diff(u) != 0
    idx = np.arange(n)
    last_change = np.maximum.accumulate(np.where(change, idx, 0))
    length = idx - last_change + 1
    return np.where(u == 1, length, -length)
