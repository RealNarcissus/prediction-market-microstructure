"""End-to-end harness determinism on synthetic data."""
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
from sklearn.dummy import DummyClassifier

from locked.harness import evaluate_horizon  # noqa: E402  (conftest path)

NAME = "toy_constant"


def _bars_with_signal(n_days: int, path: str):
    rng = np.random.default_rng(7)
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    n = n_days * 24
    steps = rng.normal(0, 0.1, n)  # small: keep synthetic prices positive
    close = 100 + np.cumsum(steps)
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    df = pl.DataFrame(
        {
            "open_time": [start + timedelta(hours=i) for i in range(n)],
            "open": open_,
            "high": np.maximum(open_, close) + 0.1,
            "low": np.minimum(open_, close) - 0.1,
            "close": close,
            "volume": np.abs(rng.normal(10, 2, n)),
            "taker_buy_base_volume": np.abs(rng.normal(5, 1, n)),
            "count": rng.integers(1, 50, n),
        }
    )
    df.write_parquet(path)


def build_features(df: pl.DataFrame) -> np.ndarray:
    c = df["close"]
    return df.select(
        [(c / c.shift(k)).log().alias(f"f{k}") for k in (1, 2)]
    ).to_numpy()


def new_model():
    return DummyClassifier(strategy="prior")


def test_harness_deterministic_and_seal_safe(tmp_path):
    pq = tmp_path / "toy.parquet"
    _bars_with_signal(400, str(pq))
    r1 = evaluate_horizon(sys.modules[__name__], str(pq))
    r2 = evaluate_horizon(sys.modules[__name__], str(pq))
    # NaN != NaN breaks dataclass eq; compare field-wise with NaN==NaN
    d1, d2 = r1.__dict__, r2.__dict__
    for k in d1:
        a, b = d1[k], d2[k]
        same = (a == b) or (a != a and b != b)
        assert same, f"{k}: {a} != {b}"
    assert r1.n_val > 0
    # frame must end before the seal (2026-01-01): synthetic data ends 2025-07
