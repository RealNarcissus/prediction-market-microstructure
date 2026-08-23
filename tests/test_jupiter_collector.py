import asyncio
import json
from pathlib import Path

from quantbtc.jupiter import parse_epoch_event
from quantbtc.jupiter_collector import JupiterPoller
from quantbtc.store import Store

FIX = Path(__file__).parent / "fixtures" / "jupiter"


class FakeClient:
    """Models the real API: get_events returns events per horizon tag."""

    def __init__(self, by_tag, market_results, orderbooks):
        self._by_tag = by_tag
        self._markets = market_results
        self._obs = orderbooks
        self.orderbook_calls: list[str] = []

    async def get_events(self, tags=None, **_):
        return self._by_tag.get(tags, [])

    async def get_market(self, market_id):
        return self._markets[market_id]

    async def get_orderbook(self, market_id):
        self.orderbook_calls.append(market_id)
        return self._obs[market_id]


def _first_updown_event():
    data = json.loads((FIX / "crypto_events_5m.json").read_text())
    for e in data["data"]:
        if parse_epoch_event(e) is not None:
            return e
    raise AssertionError("no updown event in fixture")


def _ep(event):
    return parse_epoch_event(event)


def _poll(client, tmp_path, now):
    store = Store(tmp_path / "c.db")
    poller = JupiterPoller(client=client, store=store)
    asyncio.run(poller.poll_once(now))
    return store


def test_poll_captures_quotes_for_active_epoch(tmp_path):
    event = _first_updown_event()
    ep = _ep(event)
    now = ep.epoch_start_ms + 60_000  # 1 minute into the epoch
    client = FakeClient(
        by_tag={"5m": [event], "15m": []},
        market_results={},
        orderbooks={
            ep.up_market_id: json.loads(
                (FIX / "orderbook_sample.json").read_text()
            )
        },
    )
    store = _poll(client, tmp_path, now)

    up = store.market(ep.up_market_id)
    assert up["asset"] == ep.asset
    assert up["horizon_s"] == ep.horizon_s
    assert up["open_time_ms"] == ep.epoch_start_ms
    assert up["close_time_ms"] == ep.close_ms
    assert store.market(ep.down_market_id) is not None

    # both sides from the single Up-market orderbook (yes=up, no=down)
    assert store.quote_count_since(0) == 2
    rows = store.conn.execute(
        "SELECT side, bid, ask FROM quotes ORDER BY side"
    ).fetchall()
    by_side = {r["side"]: r for r in rows}
    assert by_side["up"]["bid"] == 0.51 and by_side["up"]["ask"] == 0.48
    assert by_side["down"]["bid"] == 0.48 and by_side["down"]["ask"] == 0.47
    assert client.orderbook_calls == [ep.up_market_id]


def test_poll_skips_epoch_before_window(tmp_path):
    event = _first_updown_event()
    ep = _ep(event)
    client = FakeClient(
        by_tag={"5m": [event], "15m": []}, market_results={}, orderbooks={}
    )
    store = _poll(client, tmp_path, now=ep.epoch_start_ms - 60_000)
    assert store.market(ep.up_market_id) is not None  # markets recorded
    assert store.quote_count_since(0) == 0  # but no quotes fetched


def test_poll_resolves_closed_epoch_after_delay(tmp_path):
    event = _first_updown_event()
    ep = _ep(event)
    closed = json.loads(json.dumps(event))
    for m in closed.get("markets") or []:
        if m.get("marketId") == ep.up_market_id:
            m["status"] = "closed"
            m["result"] = "yes"
        if m.get("marketId") == ep.down_market_id:
            m["status"] = "closed"
            m["result"] = "no"
    up_closed = next(
        m
        for m in closed["markets"]
        if m.get("marketId") == ep.up_market_id
    )
    client = FakeClient(
        by_tag={"5m": [closed], "15m": []},
        market_results={ep.up_market_id: up_closed},
        orderbooks={},
    )
    store = _poll(client, tmp_path, now=ep.close_ms + 10_000)

    assert store.resolution(ep.up_market_id)["outcome"] == "up"
    assert store.resolution(ep.down_market_id)["outcome"] == "down"
    assert store.quote_count_since(0) == 0
