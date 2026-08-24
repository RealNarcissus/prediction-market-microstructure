"""s027: Quarter-Hour Effect (arXiv:2607.09426) — flow-switch reversal dummies.

The paper's predictive regression controls W_t include short-term reversal
dummies for buyer->seller and seller->buyer flow switches. Feature: a signed
switch indicator = sign(imb_t) - sign(imb_{t-1}) in {-2,0,+2}.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s026_qh_imb_lags import build_features as _s026
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s027_qh_flow_switch"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _s026(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)
    sign = np.sign(imb)
    switch = sign - np.roll(sign, 1)
    switch[0] = np.nan
    return np.column_stack([x, switch])


def new_model():
    return _lgbm()
