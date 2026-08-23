import pytest

from quantbtc.fairvalue import AsianDigital

# BTC-ish: sigma ~ 45%/year. Per-sqrt(second): 0.45 / sqrt(365.25*24*3600)
SIGMA = 0.45 / (365.25 * 24 * 3600) ** 0.5


def test_atm_at_open_is_half():
    av = AsianDigital(strike=100.0, total_s=300.0, sigma=SIGMA)
    p = av.prob_up(spot=100.0, elapsed_s=1.0, running_avg=100.0)
    assert p == pytest.approx(0.5, abs=0.01)


def test_monotone_in_spot():
    av = AsianDigital(strike=100.0, total_s=300.0, sigma=SIGMA)
    ps = [av.prob_up(spot=s, elapsed_s=60.0, running_avg=100.0)
          for s in (99.0, 99.9, 100.0, 100.1, 101.0)]
    assert ps == sorted(ps)


def test_deep_moneyness():
    av = AsianDigital(strike=100.0, total_s=300.0, sigma=SIGMA)
    assert av.prob_up(spot=130.0, elapsed_s=0.1, running_avg=130.0) > 0.99
    assert av.prob_up(spot=70.0, elapsed_s=0.1, running_avg=70.0) < 0.01


def test_running_average_dominates_late():
    av = AsianDigital(strike=100.0, total_s=300.0, sigma=SIGMA)
    # 1 second left, average far above strike: essentially decided
    assert av.prob_up(spot=90.0, elapsed_s=299.0, running_avg=105.0) > 0.99
    assert av.prob_up(spot=110.0, elapsed_s=299.0, running_avg=95.0) < 0.01


def test_expired_is_step_function():
    av = AsianDigital(strike=100.0, total_s=300.0, sigma=SIGMA)
    assert av.prob_up(spot=0.0, elapsed_s=300.0, running_avg=100.5) == 1.0
    assert av.prob_up(spot=1e9, elapsed_s=301.0, running_avg=99.5) == 0.0


def test_mid_epoch_sensitivity():
    """Sanity: 1% spot move mid-epoch shifts probability by several points."""
    av = AsianDigital(strike=100.0, total_s=300.0, sigma=SIGMA)
    p_lo = av.prob_up(spot=99.0, elapsed_s=150.0, running_avg=99.5)
    p_hi = av.prob_up(spot=101.0, elapsed_s=150.0, running_avg=100.5)
    assert p_hi - p_lo > 0.5  # a 1% move mid-window is decisive
