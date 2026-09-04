from quantbtc.report import build_report
from quantbtc.store import Store


def test_report_counts_and_gaps(tmp_path):
    store = Store(tmp_path / "c.db")
    store.upsert_market(
        {
            "market_id": "m1",
            "event_id": "e",
            "title": "BTC 5m",
            "asset": "BTC",
            "horizon_s": 300,
            "open_time_ms": 1_000,
            "close_time_ms": 130_000,
            "strike": None,
            "first_seen_ms": 500,
        }
    )
    store.insert_quotes(
        [
            {
                "ts_ms": 10_000,
                "market_id": "m1",
                "side": "up",
                "bid": 0.5,
                "ask": 0.52,
                "bid_qty": 1.0,
                "ask_qty": 1.0,
            }
        ]
    )
    store.upsert_resolution("m1", "up", 130_500, 140_000)

    md = build_report(store, parquet_root=tmp_path, since_ms=0, now_ms=200_000)
    assert "| Metric | Value |" in md
    assert "| Quotes captured | 1 |" in md
    assert "| Markets seen | 1 |" in md
    assert "| Resolutions | 1 |" in md
    assert "BTC" in md
