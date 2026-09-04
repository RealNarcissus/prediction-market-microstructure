from __future__ import annotations

import math


def fee_per_contract(price: float, rate: float = 0.07) -> float:
    """Per-contract fee: rate * price * (1 - price), Kalshi/Jupiter-style.

    Jupiter's documented samples (100 @ $0.25 -> $1.32; 100 @ $0.01 -> $0.07)
    match rate=0.07 exactly. Re-verified against live data in a later recon task.
    """
    if not 0.0 <= price <= 1.0:
        raise ValueError(f"price must be in [0, 1], got {price}")
    return rate * price * (1.0 - price)


def order_fee(
    price: float,
    contracts: int,
    rate: float = 0.07,
    round_cents: bool = True,
) -> float:
    """Total fee for an order of `contracts` bought at `price`.

    Jupiter rounds the order fee UP to the nearest cent (docs), giving an
    effective 1-cent minimum on any executed order.
    """
    if contracts < 1:
        raise ValueError("contracts must be >= 1")
    raw = fee_per_contract(price, rate) * contracts
    if round_cents:
        return math.ceil(round(raw, 6) * 100.0) / 100.0
    return raw


def breakeven_win_prob(price: float, fee_per_contr: float) -> float:
    """Win probability at which EV per contract is zero.

    Buying at `price` with fee `fee_per_contr`: EV = q*(1-p) - (1-q)*p - f
    = q - p - f, so breakeven q* = p + f.
    """
    return min(1.0, price + fee_per_contr)


def expected_value(
    win_prob: float, price: float, fee_per_contr: float
) -> float:
    """Expected profit per contract (in USD, payout = 1)."""
    return win_prob - price - fee_per_contr
