from datetime import datetime, timezone

from quantbtc.binance_ws import (
    HourlyParquetWriter,
    hour_key,
    parse_agg_trade,
    parse_depth,
    parse_kline,
    streams_for,
)


def test_parse_agg_trade():
    row = parse_agg_trade(
        {
            "e": "aggTrade",
            "s": "BTCUSDT",
            "p": "50000.10",
            "q": "0.123",
            "T": 1784773200123,
            "m": False,
        }
    )
    assert row == {
        "ts_ms": 1784773200123,
        "symbol": "BTCUSDT",
        "price": 50000.10,
        "qty": 0.123,
        "agg_buy": True,
    }


def test_parse_kline_keeps_taker_volume():
    row = parse_kline(
        {
            "e": "kline",
            "E": 1784773200500,
            "s": "BTCUSDT",
            "k": {
                "t": 1784773200000,
                "o": "50000",
                "h": "50100",
                "l": "49900",
                "c": "50050",
                "v": "12.5",
                "T": 1784773259999,
                "q": "625000",
                "V": "7.5",
                "Q": "375000",
            },
        }
    )
    assert row["ts_ms"] == 1784773200000
    assert row["close"] == 50050.0
    assert row["volume"] == 12.5
    assert row["taker_buy_volume"] == 7.5  # imbalance feature source


def test_parse_depth_uses_futures_ws_format():
    row = parse_depth(
        {
            "e": "depthUpdate",
            "E": 1784773200100,
            "s": "BTCUSDT",
            "b": [["49999.5", "1.5"], ["49999.0", "2.0"]],
            "a": [["50000.5", "0.8"]],
        }
    )
    assert row["ts_ms"] == 1784773200100
    assert row["symbol"] == "BTCUSDT"
    assert row["bid1_px"] == 49999.5 and row["bid1_qty"] == 1.5
    assert row["bid2_px"] == 49999.0
    assert row["ask1_px"] == 50000.5 and row["ask1_qty"] == 0.8
    assert row["ask2_px"] is None


def test_parse_depth_spot_format_uses_fallback_ts():
    row = parse_depth(
        {
            "lastUpdateId": 7,
            "bids": [["49999.5", "1.5"]],
            "asks": [["50000.5", "0.8"]],
        },
        fallback_ts_ms=1784773200200,
    )
    assert row["ts_ms"] == 1784773200200
    assert row["bid1_px"] == 49999.5
    assert row["ask1_px"] == 50000.5


def test_streams_for_all_symbols():
    streams = streams_for(("btcusdt", "solusdt"))
    assert "btcusdt@aggTrade" in streams
    assert "solusdt@depth20@100ms" in streams
    assert "solusdt@kline_1m" in streams
    assert len(streams) == 6


def test_hour_key():
    expected = datetime.fromtimestamp(1784773200, tz=timezone.utc).strftime(
        "%Y%m%d%H"
    )
    assert hour_key(1784773200123) == expected


def test_hourly_writer_flushes_one_file_per_stream_hour(tmp_path):
    w = HourlyParquetWriter(tmp_path)
    ts = 1784773200123
    w.add("BTCUSDT", "aggTrade", {"ts_ms": ts, "price": 1.0, "qty": 2.0})
    w.add("BTCUSDT", "aggTrade", {"ts_ms": ts + 5, "price": 1.1, "qty": 2.1})
    assert w.flush() == 2
    import polars as pl

    path = tmp_path / "BTCUSDT" / "aggTrade" / f"{hour_key(ts)}.parquet"
    df = pl.read_parquet(path)
    assert df.height == 2
    # flush again with a new row: file is appended, not clobbered
    w.add("BTCUSDT", "aggTrade", {"ts_ms": ts + 10, "price": 1.2, "qty": 2.2})
    w.flush()
    assert pl.read_parquet(path).height == 3
    assert w.flush() == 0  # nothing buffered
