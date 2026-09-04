"""s029: Amihud illiquidity (Amihud 2002) as an impact-regime modulator.

Illiq_t = mean(|r| / dollar volume) over a trailing window — the classic
price-impact-per-dollar proxy (Kyle-lambda cousin). Feature: Illiq (24-bar
trail, log-scaled) and its interaction with taker imbalance
(impact-WEIGHTED directional pressure, per arXiv:2602.00776's finding that
imbalance's predictive shape depends on spread/impact conditions).
"""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s023_lgbm_pos_lag23 import build_features as _s023
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s029_amihud_x_imb"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _s023(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)
    c = df["close"]
    r = (c / c.shift(1)).log().abs()
    dollar_vol = (df["close"] * df["volume"])
    illiq_bar = r / dollar_vol.clip(1e-9)
    illiq = df.select(illiq_bar.fill_null(0).rolling_mean(24).alias("i")).to_numpy().T[0]
    log_illiq = np.log(illiq.clip(1e-18, None))
    return np.column_stack([x, log_illiq, imb * log_illiq])


def new_model():
    return _lgbm()
