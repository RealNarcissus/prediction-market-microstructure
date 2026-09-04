"""s030: InventionV1 — IRLS probit formula on core signals.

Formula: P = sigma(w0 + w1*z(imb) + w2*z(pos) + w3*z(ratr24) + w4*z(r10))
Weights fitted by IRLS (L2=1.0, 25 iters) on walk-forward training folds.
Hypothesis: a compact interpretable closed form can capture most of the
champion's edge; its weights quantify each signal's contribution.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

RESEARCH = Path(__file__).resolve().parents[1]
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

from invented.formula import InventedFormula, causal_streak, core_signals  # noqa: E402
from locked.data import base_trailing_returns  # noqa: E402  (conftest path)

NAME = "s030_invention_v1"

SIGNALS = ["imb", "pos", "ratr24", "r10"]


def build_features(df: pl.DataFrame) -> np.ndarray:
    sig = core_signals(df)
    return np.column_stack([sig[k] for k in SIGNALS])


def new_model():
    f = InventedFormula(l2=1.0)
    f.names = list(SIGNALS)
    return f


# r10 is part of the champion core; keep parity with s023 by appending the
# trailing-return block too — no: V1 tests signals ALONE. The locked harness
# consumes build_features only; keep it minimal.
