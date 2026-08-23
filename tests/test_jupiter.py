import json
from pathlib import Path

import pytest

from quantbtc.jupiter import (
    EpochEvent,
    JupiterMarket,
    Level,
    best_bid_ask,
    extract_asset_horizon,
    parse_epoch_event,
    parse_market,
    parse_orderbook,
)

FIX = Path(__file__).parent / "fixtures" / "jupiter"


def test_price_scale_documented_one_million_equals_one_dollar():
    from quantbtc.jupiter import PRICE_SCALE

    assert PRICE_SCALE == 1_000_000


def test_parse_epoch_event_from_live_capture():
    data = json.loads((FIX / "crypto_events_5m.json").read_text())
    epochs = [parse_epoch_event(e) for e in data["data"]]
    epochs = [e for e in epochs if e is not None]
    assert epochs, "fixture must contain updown epochs"
    e = epochs[0]
    assert isinstance(e, EpochEvent)
    assert e.asset == "BTC"
    assert e.horizon_s == 300
    assert e.epoch_start_ms > 0
    assert e.close_ms == e.epoch_start_ms + 300_000  # closeTime = start + 5m
    assert e.up_market_id and e.down_market_id
    assert e.up_market_id != e.down_market_id


def test_parse_epoch_event_rejects_non_updown():
    assert parse_epoch_event({"metadata": {"slug": "what-price-will-btc-hit"}}) is None
    assert parse_epoch_event({}) is None


def test_parse_market_normalizes_units():
    d = json.loads((FIX / "market_sample.json").read_text())
    m = parse_market(d)
    assert isinstance(m, JupiterMarket)
    assert m.market_id == "abc123"
    assert m.open_time_ms == 1784773200000  # unix seconds -> ms
    assert m.buy_yes_usd == pytest.approx(0.125)
    assert m.buy_no_usd == pytest.approx(0.09)
    assert m.volume == pytest.approx(500.0)
    assert m.result is None
    assert m.status == "open"


def test_parse_orderbook_cents_to_usd():
    d = json.loads((FIX / "orderbook_sample.json").read_text())
    ob = parse_orderbook(d)
    assert ob["yes"][0] == Level(price=0.48, qty=120.5)
    assert ob["no"][1] == Level(price=0.48, qty=150.0)


def test_best_bid_ask_from_sorted_levels():
    levels = [Level(0.48, 10), Level(0.51, 20), Level(0.53, 5)]
    bid, ask = best_bid_ask(levels)
    assert bid == pytest.approx(0.53)  # highest buy
    assert ask == pytest.approx(0.48)  # lowest offer


def test_best_bid_ask_empty():
    assert best_bid_ask([]) == (None, None)


def test_extract_asset_horizon():
    assert extract_asset_horizon("BTC Up or Down - 5 minute - x") == ("BTC", 300)
    assert extract_asset_horizon("SOL 15-Minute Up/Down") == ("SOL", 900)
    assert extract_asset_horizon("Who wins the election?") == (None, None)
