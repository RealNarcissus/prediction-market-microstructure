"""Pre-registered walk-forward folds and the sealed holdout boundary.

Ported from Herdr src/splits.py: 4 expanding quarterly validation folds over
2025, an 11-bar purge at each train/validate boundary (label of bar i touches
bar i+1, so at least 1 bar must go; 11 matches the prior attempt), and the
H1-2026 test holdout that the loop may NEVER evaluate on — only
`runner.py verdict` (human-triggered) spends a use of it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import polars as pl

SEALED_AFTER = datetime(2026, 1, 1, tzinfo=timezone.utc)
PURGE_BARS = 11

_FOLD_DATES = [
    ("F1", "2025-01-01", "2025-04-01"),
    ("F2", "2025-04-01", "2025-07-01"),
    ("F3", "2025-07-01", "2025-10-01"),
    ("F4", "2025-10-01", "2026-01-01"),
]
_TRAIN_START = datetime(2022, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class FoldSplit:
    fold_name: str
    train_idx: list[int]  # positional row indices into the prepared frame
    val_idx: list[int]


def _ts(s: str) -> datetime:
    # NOTE: fromisoformat("2025-01-01+00:00") silently yields a NAIVE
    # datetime on 3.11 ("+00:00" parsed as a time offset, not a tz);
    # always build the full aware form explicitly.
    return datetime.fromisoformat(s + "T00:00:00+00:00")


def get_validation_folds(df: pl.DataFrame) -> list[FoldSplit]:
    ts = df["open_time"].to_list()
    folds: list[FoldSplit] = []
    for name, val_start_s, val_end_s in _FOLD_DATES:
        val_start, val_end = _ts(val_start_s), _ts(val_end_s)
        train_idx = [
            i
            for i, t in enumerate(ts)
            if _TRAIN_START <= t < val_start
        ]
        val_idx = [
            i for i, t in enumerate(ts) if val_start <= t < val_end
        ]
        # purge: drop the last PURGE_BARS train rows adjacent to the boundary
        train_idx = train_idx[:-PURGE_BARS] if len(train_idx) >= PURGE_BARS else []
        folds.append(FoldSplit(fold_name=name, train_idx=train_idx, val_idx=val_idx))
    return folds


def assert_no_sealed_leakage(df: pl.DataFrame) -> None:
    """Validate that a frame prepared for loop use ends before the seal."""
    max_ts = max(df["open_time"].to_list())
    if max_ts >= SEALED_AFTER:
        raise RuntimeError(
            f"sealed holdout leakage: frame reaches {max_ts}, "
            f"seal begins {SEALED_AFTER}"
        )


def sealed_split(df_full: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Human-triggered verdict path only: split at the seal with purge."""
    ts = df_full["open_time"].to_list()
    fit_idx = [i for i, t in enumerate(ts) if t < SEALED_AFTER]
    hold_idx = [i for i, t in enumerate(ts) if t >= SEALED_AFTER]
    fit_idx = fit_idx[:-PURGE_BARS] if len(fit_idx) >= PURGE_BARS else []
    return df_full[fit_idx], df_full[hold_idx]
