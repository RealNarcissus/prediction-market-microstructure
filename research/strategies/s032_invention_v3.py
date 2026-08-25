"""s032: InventionV3 — V2 + structured nonlinearities:
imb*pos (pressure-position interaction), imb^2 (pressure convexity),
streak*imb (streak-aligned pressure).
"""
from __future__ import annotations

import numpy as np
import polars as pl

from strategies.s031_invention_v2 import build_features as _v2
from invented.formula import InventedFormula, core_signals

NAME = "s032_invention_v3"


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _v2(df)
    sig = core_signals(df)
    pos = sig["pos"]
    streak = x[:, -2]  # streak column from V2
    imb = sig["imb"]
    return np.column_stack([x, imb * pos, imb**2, streak * imb])


def new_model():
    f = InventedFormula(l2=1.0)
    f.names = [
        "imb", "pos", "ratr24", "r10", "streak", "flow_switch",
        "imb_x_pos", "imb_sq", "streak_x_imb",
    ]
    return f
