from datetime import datetime, timedelta, timezone

import polars as pl
import pytest

from quantbtc.twapbars import aggregate_windows, label_disagreement


def _bars_1m(n_minutes: int) -> pl.DataFrame:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 100.0
    for i in range(n_minutes):
        o = price
        # deterministic zig-zag so TWAP and endpoint labels diverge sometimes
        c = o + (0.6 if i % 3 != 0 else -1.2)
        price = c
        rows.append(
            {
                "open_time": start + timedelta(minutes=i),
                "open": o, "high": max(o, c) + 0.1, "low": min(o, c) - 0.1,
                "close": c, "volume": 10.0,
                "taker_buy_base_volume": 5.0, "count": 5,
            }
        )
    return pl.DataFrame(rows)


def test_windows_complete_only_and_aligned():
    agg = aggregate_windows(_bars_1m(23), "5m")  # 4 full windows + 3min rest
    assert agg.height == 4
    assert (agg["open_time"].dt.minute() % 5 == 0).all()


def test_twap_label_is_mean_of_closes_vs_first_open():
    agg = aggregate_windows(_bars_1m(10), "5m")
    w0 = agg.row(0, named=True)
    mean_close = _bars_1m(5)["close"].mean()
    assert w0["twap"] == pytest.approx(mean_close)
    assert w0["strike"] == 100.0  # first 1m open
    assert w0["y_twap"] == int(mean_close >= 100.0)


def test_endpoint_vs_twap_disagreement_measured():
    agg = aggregate_windows(_bars_1m(30), "5m")
    d = label_disagreement(agg)
    assert 0.0 <= d <= 1.0
