from quantbtc.store import Store


def test_store_roundtrip(tmp_path):
    s = Store(tmp_path / "collector.db")
    s.upsert_market(
        {
            "market_id": "m1",
            "event_id": "e1",
            "title": "BTC 5m",
            "asset": "BTC",
            "horizon_s": 300,
            "open_time_ms": 1_000,
            "close_time_ms": 130_000,
            "strike": None,
            "first_seen_ms": 500,
        }
    )
    s.insert_quotes(
        [
            {
                "ts_ms": 1_100,
                "market_id": "m1",
                "side": "yes",
                "bid": 0.48,
                "ask": 0.52,
                "bid_qty": 10.0,
                "ask_qty": 8.0,
            },
            {
                "ts_ms": 1_100,
                "market_id": "m1",
                "side": "no",
                "bid": 0.47,
                "ask": 0.50,
                "bid_qty": 9.0,
                "ask_qty": 7.0,
            },
        ]
    )
    s.upsert_resolution("m1", "yes", resolved_ms=130_500, checked_ms=140_000)

    assert s.market("m1")["asset"] == "BTC"
    assert s.quote_count_since(0) == 2
    assert s.resolution("m1")["outcome"] == "yes"

    s.insert_quotes(
        [
            {
                "ts_ms": 1_100,
                "market_id": "m1",
                "side": "yes",
                "bid": 0.48,
                "ask": 0.52,
                "bid_qty": 10.0,
                "ask_qty": 8.0,
            }
        ]
    )
    assert s.quote_count_since(0) == 2  # dedup by PK

    s.set_state("last_poll_ms", "12345")
    assert s.get_state("last_poll_ms") == "12345"
    assert s.get_state("missing") is None


def test_upsert_market_updates_existing(tmp_path):
    s = Store(tmp_path / "collector.db")
    rec = {
        "market_id": "m2",
        "event_id": "e2",
        "title": "t",
        "asset": "SOL",
        "horizon_s": 900,
        "open_time_ms": 0,
        "close_time_ms": 0,
        "strike": None,
        "first_seen_ms": 1,
    }
    s.upsert_market(rec)
    rec["strike"] = 123.45
    s.upsert_market(rec)
    assert s.market("m2")["strike"] == 123.45
