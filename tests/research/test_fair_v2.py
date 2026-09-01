"""Tests for the venue-accurate fair value (fair_v2).

The variance formulas and regime properties are the point here: the module
exists because the v1 running-TWAP model does not match the venue's actual
final-window settlement (see fair_v2 docstring for the round-30 correction).
"""

from __future__ import annotations

import math

import pytest

from research.staleness.fair_v2 import (
    fair_up_v2,
    variance_final_window,
    variance_running_twap_v1,
    variance_within_window,
)


def test_snapshot_regime_is_european_digital() -> None:
    # w=0: settle on the close price => sd = sigma * sqrt(d)
    spot, strike, sigma, d = 101.0, 100.0, 0.002, 4.0
    expected = 0.5 * (1 + math.erf((spot - strike) / (sigma * math.sqrt(d)) / math.sqrt(2)))
    assert fair_up_v2(spot, strike, sigma, d, w_minutes=0.0) == pytest.approx(expected)


def test_final_window_variance_formula() -> None:
    # Var of time-average of BM over interval w = sigma^2 * w / 3
    assert variance_final_window(0.002, 1.0) == pytest.approx(0.002 ** 2 / 3.0)
    assert variance_final_window(0.001, 0.5) == pytest.approx(0.001 ** 2 * 0.5 / 3.0)


def test_within_window_variance_continuous_at_d_equals_w() -> None:
    # sigma^2 * d^3 / (3 w^2) at d = w equals the all-future form sigma^2 * w / 3
    sigma, w = 0.002, 1.0
    assert variance_within_window(sigma, w, w) == pytest.approx(
        variance_final_window(sigma, w)
    )


def test_fair_independent_of_remaining_time_when_final_window_fully_future() -> None:
    # Discriminating property vs v1: once d >= w, the settlement quantity and
    # its variance do not depend on how much of the window remains.
    vals = [
        fair_up_v2(101.0, 100.0, 0.002, d, w_minutes=1.0)
        for d in (1.0, 2.0, 3.0, 4.0)
    ]
    assert all(v == pytest.approx(vals[0]) for v in vals)


def test_inside_window_pulls_toward_realized_average() -> None:
    # realized avg far above strike with d -> 0: fair -> 1
    fair = fair_up_v2(
        100.0, 100.0, 0.002, d_minutes=0.05, w_minutes=1.0, realized_avg=100.8
    )
    assert fair > 0.99
    # continuity at d = w: with realized_avg == spot it must match the
    # future-only form exactly
    a = fair_up_v2(101.0, 100.0, 0.002, 1.0, 1.0, realized_avg=101.0)
    b = fair_up_v2(101.0, 100.0, 0.002, 1.0, 1.0)
    assert a == pytest.approx(b)


def test_v2_more_extreme_than_v1_mid_window() -> None:
    # 5m window at open+60s: v1 (running TWAP) sd ~1.21 sigma > v2 (final 1m)
    # sd ~0.577 sigma => v2 fair is farther from 0.5. Documents the round-30
    # correction (the earlier catalog note had this backwards).
    sigma = 0.002
    spot, strike = 100.0005, 100.0  # 0.5bp distance: within a sigma, no saturation
    sd_v1 = math.sqrt(variance_running_twap_v1(sigma, n_fut=4.0, n_total=5.0))
    sd_v2 = math.sqrt(variance_final_window(sigma, w_minutes=1.0))
    assert sd_v1 > sd_v2
    from research.staleness.fair_v2 import norm_cdf

    f_v1 = norm_cdf((spot - strike) / sd_v1)
    f_v2 = norm_cdf((spot - strike) / sd_v2)
    assert abs(f_v2 - 0.5) > abs(f_v1 - 0.5)


def test_monotone_in_spot_and_clamped() -> None:
    lo = fair_up_v2(99.0, 100.0, 0.002, 2.0, 1.0)
    hi = fair_up_v2(101.0, 100.0, 0.002, 2.0, 1.0)
    assert lo < hi
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
    with pytest.raises(ValueError):
        fair_up_v2(100.0, 100.0, 0.0, 2.0, 1.0)
    with pytest.raises(ValueError):
        variance_within_window(0.002, 2.0, 1.0)
