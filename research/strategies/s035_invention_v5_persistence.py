"""s035: InventionV5 — path-persistence modulation.

Jupiter pays on the window's AVERAGE path. How much directional pressure
converts into average drift depends on return persistence: with positive
AR(1) rho, pressure compounds; with negative rho (mean reversion), it
cancels. Features: trailing AR(1) coefficient rho_50 (regression of r_t on
r_{t-1} over 50 bars), and imb * rho_50.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from strategies.s032_invention_v3 import build_features as _v3
from invented.formula import InventedFormula

NAME = "s035_invention_v5_persistence"


def ar1_rho(r: np.ndarray, window: int = 50) -> np.ndarray:
    out = np.full(len(r), np.nan)
    for i in range(window, len(r) + 1):
        x = r[i - window : i]
        x0, x1 = x[:-1], x[1:]
        ok = np.isfinite(x0) & np.isfinite(x1)
        if ok.sum() < 10 or np.var(x0[ok]) < 1e-18:
            continue
        out[i - 1] = float(np.corrcoef(x0[ok], x1[ok])[0, 1])
    return out


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _v3(df)
    c = df["close"]
    r = (c / c.shift(1)).log().to_numpy()
    with np.errstate(invalid="ignore"):
        rho = ar1_rho(r)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2.0 * tbv / np.where(v > 0, v, 1.0) - 1.0, 0.0)
    return np.column_stack([x, rho, imb * rho])


def new_model():
    f = InventedFormula(l2=1.0)
    f.names = [
        "imb", "pos", "ratr24", "r10", "streak", "flow_switch",
        "imb_x_pos", "imb_sq", "streak_x_imb", "ar1_rho", "imb_x_rho",
    ]
    return f
