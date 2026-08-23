import pytest
from quantbtc.fees import (
    fee_per_contract, order_fee, breakeven_win_prob, expected_value,
)

def test_fee_per_contract_kalshi_formula():
    assert fee_per_contract(0.25) == pytest.approx(0.07 * 0.25 * 0.75)
    assert fee_per_contract(0.50) == pytest.approx(0.0175)

def test_order_fee_matches_jupiter_documented_samples():
    # Jupiter docs: 100 contracts @ $0.25 -> $1.32 fee; 100 @ $0.01 -> $0.07
    assert order_fee(0.25, 100) == pytest.approx(1.32)
    assert order_fee(0.01, 100) == pytest.approx(0.07)

def test_order_fee_rounds_up_to_cent_and_has_minimum_one_cent():
    assert order_fee(0.01, 1) == pytest.approx(0.01)   # 0.00693c -> 1c
    assert order_fee(0.30, 7) == pytest.approx(0.11)   # 7*0.0147=0.1029 -> 0.11

def test_order_fee_can_skip_rounding():
    assert order_fee(0.25, 100, round_cents=False) == pytest.approx(1.3125)

def test_breakeven_and_ev():
    f = fee_per_contract(0.50)                     # 0.0175
    assert breakeven_win_prob(0.50, f) == pytest.approx(0.5175)
    assert expected_value(0.55, 0.50, f) == pytest.approx(0.0325)

def test_invalid_price_rejected():
    with pytest.raises(ValueError):
        fee_per_contract(1.5)
