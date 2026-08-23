"""s014: champion + close-position history (pos_{t-1}) and position streaks."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s014_lgbm_position_history"


def _signed_streak(up: np.ndarray) -> np.ndarray:
    change = np.flatnonzero(np.diff(up.astype(int))) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [len(up)]])
    lengths = ends - starts
    signed = np.where(up[starts], lengths, -lengths)
    return np.repeat(signed, lengths)


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    rng = (df["high"] - df["low"]).to_numpy()
    pos = np.where(rng > 0, (df["close"].to_numpy() - df["low"].to_numpy()) / np.where(rng > 0, rng, 1.0), 0.5)
    ratr = df.select(
        ((pl.col("high") - pl.col("low"))
         / (pl.col("high") - pl.col("low")).rolling_mean(24).clip(1e-9)).alias("r")
    ).to_numpy()
    pos_prev = np.roll(pos, 1)
    pos_prev[0] = np.nan
    streak = _signed_streak(pos > 0.5)
    return np.column_stack([base, imb, pos, ratr, pos_prev, streak])


def new_model():
    return _lgbm()
