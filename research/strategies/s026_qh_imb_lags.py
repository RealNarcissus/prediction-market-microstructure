"""s026: Quarter-Hour Effect (arXiv:2607.09426) — imb lags.

The paper shows order-flow imbalance OI_t (= our taker imbalance) has
phase-structured persistence anchored at 15-minute boundaries, with a
lag-lattice at multiples of 15'. At 5m cadence the same-phase lag is 3 bars;
at 15m it is 1 bar. Features: imb lag-1 and same-phase lag (3 for 5m data,
applied generically as lag 3).
"""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s023_lgbm_pos_lag23 import build_features as _s023
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s026_qh_imb_lags"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _s023(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)
    imb_l1 = np.roll(imb, 1)
    imb_l1[0] = np.nan
    imb_l3 = np.roll(imb, 3)
    imb_l3[:3] = np.nan
    return np.column_stack([x, imb_l1, imb_l3])


def new_model():
    return _lgbm()
