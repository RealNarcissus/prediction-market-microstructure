"""Metrics — pooled out-of-sample quality measures (Herdr-compatible)."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    balanced_accuracy_score,
    log_loss,
    matthews_corrcoef,
)


def safe_mcc(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2 or len(np.unique(y_pred)) < 2:
        return 0.0
    return float(matthews_corrcoef(y_true, y_pred))


def safe_balanced_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return 0.5
    return float(balanced_accuracy_score(y_true, y_pred))


def safe_log_loss(y_true: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-12, 1 - 1e-12)
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(log_loss(y_true, p, labels=[0, 1]))


def tail_calibration_error(y_true: np.ndarray, p: np.ndarray) -> float:
    """|mean predicted - observed| over high-confidence rows (|p-0.5|>0.1).

    This is the region where selective trades fire; the prior attempt showed
    systematic overconfidence exactly here. Lower is better.
    """
    mask = np.abs(p - 0.5) > 0.1
    if mask.sum() < 30:
        return float("nan")
    return float(abs(p[mask].mean() - y_true[mask].mean()))
