"""s023: champion s018 + position history pos_{t-2}, pos_{t-3} (decay)."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s018_lgbm_weighted_imbalance import build_features as _s018
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s023_lgbm_pos_lag23"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _s018(df)  # includes pos_t
    rng_expr = pl.col("high") - pl.col("low")
    pos = df.select(
        ((pl.col("close") - pl.col("low")) / rng_expr.clip(1e-9)).alias("p")
    ).to_numpy().T[0]
    lag2 = np.roll(pos, 2)
    lag3 = np.roll(pos, 3)
    lag2[:2] = np.nan
    lag3[:3] = np.nan
    return np.column_stack([x, lag2, lag3])


def new_model():
    return _lgbm()
