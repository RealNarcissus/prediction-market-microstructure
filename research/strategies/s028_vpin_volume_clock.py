"""s028: VPIN volume-clock toxicity (Easley, Lopez de Prado, O'Hara;
arXiv:1912.10343) — flow imbalance measured in VOLUME time.

VPIN chunks flow into equal-volume buckets and averages |V_buy − V_sell|/V
over the last n buckets. We observe TRUE taker-buy volume (no bulk-volume
inference needed), so the bucket expectation is the volume-weighted mean of
per-bar |buy−sell|/V over the trailing window — i.e. expected per-bucket
imbalance under the volume clock. Feature: VPIN over a 200-bar trail.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from locked.data import base_trailing_returns
from strategies.s023_lgbm_pos_lag23 import build_features as _s023
from strategies.s002_lgbm_base import new_model as _lgbm

NAME = "s028_vpin_volume_clock"


def vpin_series(volume: np.ndarray, tbv: np.ndarray, window: int = 200) -> np.ndarray:
    buy_frac = np.where(volume > 0, tbv / np.where(volume > 0, volume, 1.0), 0.5)
    bar_imb = np.abs(2.0 * buy_frac - 1.0)
    w = bar_imb * volume
    c_w, c_v = np.cumsum(w), np.cumsum(volume)
    out = np.full(len(volume), np.nan)
    if len(volume) <= window:
        return out
    vols = c_v[window:] - c_v[:-window]
    ok = vols > 0
    out[window:] = np.where(ok, (c_w[window:] - c_w[:-window]) / np.where(ok, vols, 1.0), np.nan)
    return out


def build_features(df: pl.DataFrame) -> np.ndarray:
    x = _s023(df)
    v = df["volume"].to_numpy()
    tbv = df["taker_buy_base_volume"].to_numpy()
    return np.column_stack([x, vpin_series(v, tbv)])


def new_model():
    return _lgbm()
