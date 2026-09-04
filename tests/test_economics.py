from quantbtc.economics import breakeven_rows

def test_breakeven_rows_structure_and_math():
    rows = breakeven_rows(prices=[0.25, 0.50], rate=0.07)
    assert rows[0] == {
        "price": 0.25,
        "fee_per_contract": 0.07 * 0.25 * 0.75,
        "breakeven_win_prob": 0.25 + 0.07 * 0.25 * 0.75,
    }
    assert rows[1]["breakeven_win_prob"] > rows[0]["breakeven_win_prob"]
