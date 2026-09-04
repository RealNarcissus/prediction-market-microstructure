"""s031: InventionV2 — V1 + causal position streak + flow-switch dummy."""
from __future__ import annotations

import numpy as np
import polars as pl

from strategies.s030_invention_v1 import build_features as _v1, SIGNALS
from strategies.s002_lgbm_base import new_model as _lgbm  # unused; kept out
from invented.formula import InventedFormula, causal_streak, core_signals
from locked.data import base_trailing_returns  # noqa: F401

NAME = "s031_invention_v2"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _v1(df)
    sig = core_signals(df)
    streak = causal_streak(sig["pos"] > 0.5)
    sign = np.sign(sig["imb"])
    switch = sign - np.roll(sign, 1)
    switch[0] = np.nan
    return np.column_stack([x, streak, switch])


def new_model():
    f = InventedFormula(l2=1.0)
    f.names = list(SIGNALS) + ["streak", "flow_switch"]
    return f
