"""The evaluation harness: runs a strategy through the locked walk-forward
protocol and returns pooled out-of-sample metrics. Strategies are the ONLY
agent-modifiable surface (research/strategies/).

Strategy contract:
    NAME: str
    def build_features(df: pl.DataFrame) -> np.ndarray   # rows aligned to df, no lookahead
    def new_model() -> sklearn-like estimator with fit(X, y) and
                       predict_proba(X) -> (n, 2)  (column order: [P(y=0), P(y=1)])
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from . import data, folds, metrics


@dataclass(frozen=True)
class HorizonResult:
    mcc: float
    balanced_accuracy: float
    log_loss: float
    tail_calibration_error: float
    n_val: int
    n_tail: int


@dataclass(frozen=True)
class EvalResult:
    strategy: str
    res_5m: HorizonResult
    res_15m: HorizonResult

    @property
    def primary(self) -> float:
        """Keep-or-reset scalar: mean pooled-validation MCC across horizons."""
        return (self.res_5m.mcc + self.res_15m.mcc) / 2.0


def evaluate_horizon(
    strategy_module, parquet_path: str | Path
) -> HorizonResult:
    bars = data.load_bars(parquet_path)
    # Truncate at the seal BEFORE labeling: the loop never touches (and no
    # label ever peeks into) the sealed H1-2026 holdout.
    bars = bars.filter(pl.col("open_time") < folds.SEALED_AFTER)
    df = data.compute_labels(bars)
    folds.assert_no_sealed_leakage(df)
    X = strategy_module.build_features(df)
    y = df["target_y"].to_numpy().astype(int)
    if X.shape[0] != len(y):
        raise ValueError(f"{strategy_module.NAME}: features misaligned with rows")
    # Strategies may have their own lookback warmups (leading NaNs); those
    # rows are excluded from both train and validation by position. This is
    # deterministic per row and leaks nothing.
    finite = np.isfinite(X).all(axis=1)

    pooled_p = np.zeros(len(y))
    pooled_pred = np.zeros(len(y), dtype=int)
    val_mask = np.zeros(len(y), dtype=bool)
    for fold in folds.get_validation_folds(df):
        tr = np.array([i for i in fold.train_idx if finite[i]], dtype=int)
        va = np.array([i for i in fold.val_idx if finite[i]], dtype=int)
        model = strategy_module.new_model()
        model.fit(X[tr], y[tr])
        proba = model.predict_proba(X[va])
        p1 = proba[:, list(model.classes_).index(1)] if hasattr(model, "classes_") else proba[:, 1]
        pooled_p[va] = p1
        pooled_pred[va] = (p1 >= 0.5).astype(int)
        val_mask[va] = True

    yv, pv, pp = y[val_mask], pooled_p[val_mask], pooled_pred[val_mask]
    tail = np.abs(pv - 0.5) > 0.1
    return HorizonResult(
        mcc=metrics.safe_mcc(yv, pp),
        balanced_accuracy=metrics.safe_balanced_accuracy(yv, pp),
        log_loss=metrics.safe_log_loss(yv, pv),
        tail_calibration_error=metrics.tail_calibration_error(yv, pv),
        n_val=int(val_mask.sum()),
        n_tail=int(tail.sum()),
    )


def evaluate_strategy(strategy_module, data_5m: str, data_15m: str) -> EvalResult:
    return EvalResult(
        strategy=strategy_module.NAME,
        res_5m=evaluate_horizon(strategy_module, data_5m),
        res_15m=evaluate_horizon(strategy_module, data_15m),
    )
