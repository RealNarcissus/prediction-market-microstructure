"""s020: champion + CAUSAL position streak and pos_{t-1}.

Fix of the s014 leak: streak counts only up to bar t (each row knows how
long the run INCLUDING t is, never how long it will become).
"""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s020_lgbm_causal_streak"


def _causal_streak(up: np.ndarray) -> np.ndarray:
    """Signed streak length as of each bar (causal — no future run info)."""
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
    return np.column_stack([base, imb, pos, ratr, pos_prev, streak])


def new_model():
    return _lgbm()
