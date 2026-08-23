"""Label and fold correctness: the anti-leakage invariants."""
from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from locked import data, folds  # noqa: E402  (path set by conftest)


def _toy_bars(n_hours: int) -> pl.DataFrame:
    start = datetime(2024, 12, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(n_hours):
        t = start + timedelta(hours=i)
        o = 100.0 + i
        c = o + (1.0 if i % 2 == 0 else -0.5)  # alternating green/red
        rows.append(
            {"open_time": t, "open": o, "high": max(o, c) + 0.1,
             "low": min(o, c) - 0.1, "close": c, "volume": 10.0,
             "taker_buy_base_volume": 5.0, "count": 5}
        )
    return pl.DataFrame(rows)


def test_labels_use_next_bar_open_close_and_drop_edges():
    df = _toy_bars(20)
    labeled = data.compute_labels(df)
    # warmup (10) + final bar (no next) dropped
    assert len(labeled) == len(df) - data.MAX_LOOKBACK - 1
    ts = df["open_time"].to_list()
    y = labeled["target_y"].to_list()
    # bar i label = green(next bar): closes go +1 (green) on even i
    for row_i, label in zip(range(data.MAX_LOOKBACK, len(df) - 1), y):
        next_open = df["open"][row_i + 1]
        next_close = df["close"][row_i + 1]
        assert label == (1.0 if next_close > next_open else 0.0)
    # no sealed-region dependence: seal far in future here


def test_folds_boundaries_purge_and_seal():
    # 430 hourly bars of days from 2024-12-01 ends ~2026-02: crosses the seal
    df = _toy_bars(24 * 430)
    labeled = data.compute_labels(df)
    fs = folds.get_validation_folds(labeled)
    assert [f.fold_name for f in fs] == ["F1", "F2", "F3", "F4"]
    ts = labeled["open_time"].to_list()
    for f, expected_start in zip(
        fs, ["2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01"]
    ):
        assert all(ts[i] >= datetime.fromisoformat(expected_start + "T00:00:00+00:00") for i in f.val_idx)
        # purge: the 11 bars just before the boundary are NOT in train
        boundary = datetime.fromisoformat(expected_start + "T00:00:00+00:00")
        excluded = [i for i in range(len(ts)) if boundary - timedelta(hours=11) <= ts[i] < boundary]
        assert all(i not in f.train_idx for i in excluded)
    # an untruncated frame crossing the seal must be fatal to the loop
    with pytest.raises(RuntimeError, match="sealed holdout leakage"):
        folds.assert_no_sealed_leakage(labeled)
