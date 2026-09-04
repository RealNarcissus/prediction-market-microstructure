"""Environment validity self-tests: fair values must be sane.

Guards against the units bug that produced degenerate {0,1} fair values
(research/rlenv/LOG.md, incident 2)."""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import sys

RESEARCH = Path(__file__).resolve().parents[1] / "research"
RL = RESEARCH / "rlenv"
for p in (str(RESEARCH), str(RL)):
    if p not in sys.path:
        sys.path.insert(0, p)

from env import build_windows, load_1m_bars  # noqa: E402
from train import DATA_1M  # noqa: E402


def _june_windows():
    bars = load_1m_bars(DATA_1M)
    bars = bars.filter(
        (pl.col("open_time") >= datetime(2025, 6, 1, tzinfo=timezone.utc))
        & (pl.col("open_time") < datetime(2025, 7, 1, tzinfo=timezone.utc))
    )
    return build_windows(bars, horizon_s=900)


@pytest.mark.skipif(not Path(DATA_1M).exists(), reason="Herdr 1m data absent")
def test_minute0_fair_is_not_degenerate():
    """Median minute-0 fair must be near coin-flip, and exact-certainty
    outputs ({0},{1}) must be rare (they were the EWMA/Levy-units bug)."""
    eps = _june_windows()
    assert len(eps) > 100
    fairs0 = np.array([ep["steps"][0]["fair"] for ep in eps])
    med = float(np.median(fairs0))
    assert 0.3 < med < 0.7, f"minute-0 median fair off coin-flip: {med}"
    sat = float(np.mean((fairs0 <= 1e-6) | (fairs0 >= 1 - 1e-6)))
    assert sat < 0.02, f"{sat:.1%} of window opens are fully decided"


@pytest.mark.skipif(not Path(DATA_1M).exists(), reason="Herdr 1m data absent")
def test_fair_not_stuck_at_extremes_within_episode():
    eps = _june_windows()
    interior_frac_all = []
    for ep in eps[:200]:
        fracs = np.array([st["fair"] for st in ep["steps"]])
        interior_frac_all.append(
            float(np.mean((fracs > 1e-3) & (fracs < 1 - 1e-3)))
        )
    # windows CAN become decided late; but episodes should not be born
    # saturated end-to-end
    assert float(np.median(interior_frac_all)) > 0.4, (
        "episodes are saturated end-to-end — units bug is back"
    )
