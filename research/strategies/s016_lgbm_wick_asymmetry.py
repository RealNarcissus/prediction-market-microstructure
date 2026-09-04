"""s016: champion + wick asymmetry (upper vs lower wick share of range)."""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s016_lgbm_wick_asymmetry"


def build_features(df: pl.DataFrame) -> np.ndarray:
    base = base_trailing_returns(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / v - 1.0, 0.0)
    rng_expr = pl.col("high") - pl.col("low")
    body_hi = pl.max_horizontal("open", "close")
    body_lo = pl.min_horizontal("open", "close")
    safe_rng = rng_expr.clip(1e-9)
    feats = df.select(
        [
            ((pl.col("close") - pl.col("low")) / safe_rng).alias("pos"),
            (rng_expr / rng_expr.rolling_mean(24).clip(1e-9)).alias("ratr"),
            ((pl.col("high") - body_hi) / safe_rng).alias("wick_up"),
            ((body_lo - pl.col("low")) / safe_rng).alias("wick_dn"),
        ]
    ).to_numpy()
    asym = feats[:, 2] - feats[:, 3]
    return np.column_stack([base, imb, feats, asym])


def new_model():
    return _lgbm()
