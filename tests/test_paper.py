"""Paper trader unit tests: decision rule, P&L math, ledger, end-to-end step."""
from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl
import pytest

from quantbtc.config import Config, PaperConfig
from quantbtc.paper import PaperLedger, PaperTrader, decide, pnl_of


def test_decision_theta_gates():
    assert decide(0.60, 0.05).action == "buy_up"
    assert decide(0.40, 0.05).action == "buy_down"
    assert decide(0.52, 0.05).action == "skip"
    assert decide(0.52, 0.05).reason


def test_pnl_math_includes_fee():
    # 10 contracts at 0.50, fee = ceil_cents(0.0175*10)=0.18
    win = pnl_of("buy_up", 0.50, 10, True)
    loss = pnl_of("buy_up", 0.50, 10, False)
    assert win == pytest.approx(10 * 0.5 - 0.18)
    assert loss == pytest.approx(-10 * 0.5 - 0.18)


def test_ledger_roundtrip(tmp_path):
    led = PaperLedger(tmp_path / "p.db")
    rec = {
        "market_id": "M-1", "event_id": "E", "asset": "BTC",
        "horizon_s": 300, "action": "buy_up", "p_model": 0.6,
        "entry_price": 0.5, "contracts": 10, "fee": 0.18, "notes": "",
    }
    led.record(rec, now_ms=1000)
    assert led.has_trade("M-1")
    assert len(led.open_trades()) == 1
    led.settle(1, True, 4.82)
    assert led.open_trades() == []
    assert led.summary().startswith("buy_up: 1 trades")


def _collector_db(tmp_path):
    from quantbtc.store import Store

    store = Store(tmp_path / "c.db")
    store.upsert_market(
        {
            "market_id": "UP-0", "event_id": "E1", "title": "BTC 5m",
            "asset": "BTC", "horizon_s": 300,
            "open_time_ms": int(datetime.now(timezone.utc).timestamp() * 1000) - 10_000,
            "close_time_ms": int(datetime.now(timezone.utc).timestamp() * 1000) + 290_000,
            "strike": None, "first_seen_ms": 0,
        }
    )
    store.insert_quotes(
        [
            {"ts_ms": int(datetime.now(timezone.utc).timestamp() * 1000) - 5_000,
             "market_id": "UP-0", "side": "up", "bid": 0.48, "ask": 0.50,
             "bid_qty": 1.0, "ask_qty": 1.0},
            {"ts_ms": int(datetime.now(timezone.utc).timestamp() * 1000) - 5_000,
             "market_id": "UP-0", "side": "down", "bid": 0.47, "ask": 0.49,
             "bid_qty": 1.0, "ask_qty": 1.0},
        ]
    )
    store.close()


def test_step_records_decision(tmp_path, monkeypatch):
    _collector_db(tmp_path)
    cfg = Config(paper=PaperConfig(assets=("BTC",), theta=0.05))
    trader = PaperTrader(cfg, tmp_path / "c.db", tmp_path / "p.db")

    class FakeModel:
        classes_ = np.array([0, 1])

        def predict_proba(self, X):
            return np.array([[0.35, 0.65]])

    trader.models = {"5m": FakeModel(), "15m": FakeModel()}
    # feed synthetic 1m bars via load_spot_1m patch
    import quantbtc.paper as paper_mod

    start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    n = 240
    closes = 100 + np.cumsum(np.sin(np.arange(n)))
    bars = pl.DataFrame(
        {
            "open_time": [start - timedelta(minutes=i) for i in range(n, 0, -1)],
            "open": closes, "high": closes + 0.5, "low": closes - 0.5,
            "close": closes + 0.1, "volume": np.full(n, 10.0),
            "taker_buy_base_volume": np.full(n, 5.0),
            "count": np.full(n, 5, dtype=int),
        }
    ).sort("open_time")
    bars = bars.with_columns(pl.col("open_time").dt.replace_time_zone("UTC"))
    monkeypatch.setattr(
        paper_mod, "load_spot_1m", lambda *a, **k: bars
    )

    trader.step()
    row = trader.ledger.conn.execute(
        "SELECT action, p_model, entry_price FROM paper_trades"
    ).fetchone()
    assert row["action"] == "buy_up"
    assert row["p_model"] == pytest.approx(0.65)
    assert row["entry_price"] == pytest.approx(0.50)
