"""s033: InventionV3 architecture with stronger regularization (L2=10)."""
from __future__ import annotations

import numpy as np
import polars as pl

from strategies.s032_invention_v3 import build_features as _v3
from invented.formula import InventedFormula

NAME = "s033_invention_v3_lam10"


def build_features(df: pl.DataFrame) -> np.ndarray:
    return _v3(df)


def new_model():
    f = InventedFormula(l2=10.0)
    f.names = [
        "imb", "pos", "ratr24", "r10", "streak", "flow_switch",
        "imb_x_pos", "imb_sq", "streak_x_imb",
    ]
    return f
