from __future__ import annotations

import asyncio
import time

import httpx

from quantbtc.jupiter import (
    JupiterClient,
    best_bid_ask,
    parse_epoch_event,
    parse_orderbook,
)
from quantbtc.store import Store

# Verified live (docs/RECON.md): up/down epochs are discovered per horizon tag.
HORIZON_TAGS = ("5m", "15m")
# Recency-ranked search phrases per asset (search beats deep pagination
# for surfacing the CURRENTLY-live epoch).
ASSET_QUERY = {
    "BTC": "bitcoin up or down",
    "ETH": "ethereum up or down",
    "SOL": "solana up or down",
}


class JupiterPoller:
    """Polls up/down epochs; records best bid/ask for active epochs and
    final resolutions after close. Rate-limited: discovery is cached and
    refreshed periodically, orderbook fetches are budgeted per cycle and
    round-robined across active epochs, and 429s trigger backoff.

    poll_once is the pure testable step.
    """

    def __init__(
        self,
        client: JupiterClient,
        store: Store,
        assets: tuple[str, ...] = ("BTC", "ETH", "SOL"),
        result_delay_s: float = 5.0,
        poll_interval_s: float = 10.0,
        discovery_interval_s: float = 60.0,
        orderbook_budget: int = 5,
        discovery_pages: int = 3,
    ):
        self.client = client
        self.store = store
        self.assets = assets
        self.result_delay_ms = int(result_delay_s * 1000)
        self.poll_interval_s = poll_interval_s
        self.discovery_interval_s = discovery_interval_s
        self.orderbook_budget = orderbook_budget
        self.discovery_pages = discovery_pages
        self._epochs: list = []  # cached EpochEvent list
        self._last_discovery_ms = 0
        self._rr_index = 0

    async def _discover(self, now_ms: int, force: bool = False) -> None:
        if (
            not force
            and self._epochs
            and now_ms - self._last_discovery_ms
            < self.discovery_interval_s * 1000
        ):
            return
        by_event: dict[str, object] = {}

        async def collect(events: list) -> None:
            for event in events:
                ep = parse_epoch_event(event)
                if ep is None or ep.asset not in self.assets:
                    continue
                if ep.up_market_id is None and ep.event_id:
                    # search payload omits market fields: hydrate once
                    try:
                        full = await self.client.get_event(ep.event_id)
                        hydrated = parse_epoch_event(full)
                        if hydrated is not None:
                            ep = hydrated
                    except Exception as exc:
                        print(f"[jupiter] hydrate {ep.event_id} failed: {exc!r}")
                if ep.up_market_id is not None:
                    by_event.setdefault(ep.event_id, ep)

        # 1) recency-ranked search per asset: catches the LIVE epoch even
        #    when the tags listing buries it under past ones
        for asset in self.assets:
            if asset in ASSET_QUERY:
                try:
                    await collect(
                        await self.client.get_event_search(ASSET_QUERY[asset])
                    )
                except Exception as exc:
                    print(f"[jupiter] search {asset} failed: {exc!r}")
        # 2) paginated tags listing: breadth (pre-listed future epochs)
        for tag in HORIZON_TAGS:
            for offset in range(0, self.discovery_pages * 10, 10):
                events = await self.client.get_events(
                    category="crypto",
                    tags=tag,
                    include_markets=True,
                    start=offset,
                )
                await collect(events)
                if not (isinstance(events, list) and len(events) >= 10):
                    break
        # keep only epochs relevant around now (bounded memory)
        horizon_max = 900_000
        cutoff = now_ms - 3_600_000
        self._epochs = [
            ep
            for ep in by_event.values()
            if ep.close_ms >= cutoff and ep.epoch_start_ms <= now_ms + horizon_max * 8
        ]
        self._last_discovery_ms = now_ms

    async def poll_once(self, now_ms: int | None = None, force: bool = False) -> None:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        await self._discover(now_ms, force=force)

        for ep in self._epochs:
            for market_id in (ep.up_market_id, ep.down_market_id):
                if not market_id:
                    continue
                self.store.upsert_market(
                    {
                        "market_id": market_id,
                        "event_id": ep.event_id,
                        "title": ep.title,
                        "asset": ep.asset,
                        "horizon_s": ep.horizon_s,
                        "open_time_ms": ep.epoch_start_ms,
                        "close_time_ms": ep.close_ms,
                        "strike": None,
                        "first_seen_ms": now_ms,
                    }
                )

        active = [
            ep
            for ep in self._epochs
            if ep.epoch_start_ms <= now_ms < ep.close_ms
            and ep.status == "open"
            and ep.up_market_id
        ]
        fetched = 0
        n = len(active)
        while fetched < self.orderbook_budget and fetched < n:
            ep = active[self._rr_index % n]
            self._rr_index += 1
            await self._record_quotes(ep, now_ms)
            fetched += 1

        for ep in self._epochs:
            await self._maybe_resolve(ep, now_ms)

    async def _record_quotes(self, ep, now_ms: int) -> None:
        # The Up market's yes/no arrays are BID LADDERS (buying no-Up == betting
        # Down). Best bid per side = max(ladder); the ask to BUY a side is the
        # mirror: 1 - best bid of the opposite side. One orderbook call covers
        # the epoch.
        ob = parse_orderbook(await self.client.get_orderbook(ep.up_market_id))
        bid_up = max((lv.price for lv in ob["yes"]), default=None)
        bid_down = max((lv.price for lv in ob["no"]), default=None)
        qty_up = max(ob["yes"], key=lambda lv: lv.price).qty if ob["yes"] else None
        qty_down = max(ob["no"], key=lambda lv: lv.price).qty if ob["no"] else None

        def ask(side_bid: float | None, opp_bid: float | None):
            if side_bid is None or opp_bid is None:
                return None
            return min(1.0, 1.0 - opp_bid)

        self.store.insert_quotes(
            [
                {
                    "ts_ms": now_ms, "market_id": ep.up_market_id, "side": "up",
                    "bid": bid_up, "ask": ask(bid_up, bid_down),
                    "bid_qty": qty_up, "ask_qty": qty_down,
                },
                {
                    "ts_ms": now_ms, "market_id": ep.up_market_id, "side": "down",
                    "bid": bid_down, "ask": ask(bid_down, bid_up),
                    "bid_qty": qty_down, "ask_qty": qty_up,
                },
            ]
        )

    async def _maybe_resolve(self, ep, now_ms: int) -> None:
        if (
            now_ms < ep.close_ms + self.result_delay_ms
            or not ep.up_market_id
            or not ep.down_market_id
            or self.store.resolution(ep.up_market_id) is not None
        ):
            return
        fresh = await self.client.get_market(ep.up_market_id)
        if fresh.get("result") in ("yes", "no"):
            up_won = fresh["result"] == "yes"
            self.store.upsert_resolution(
                ep.up_market_id,
                "up" if up_won else "down",
                resolved_ms=ep.close_ms,
                checked_ms=now_ms,
            )
            self.store.upsert_resolution(
                ep.down_market_id,
                "down" if up_won else "up",
                resolved_ms=ep.close_ms,
                checked_ms=now_ms,
            )

    async def run_forever(self) -> None:
        backoff_s = self.poll_interval_s
        while True:
            try:
                await self.poll_once()
                self.store.set_state("last_poll_ms", str(int(time.time() * 1000)))
                backoff_s = self.poll_interval_s
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    backoff_s = min(backoff_s * 2, 120.0)
                    print(f"[jupiter] 429 rate-limited; backing off {backoff_s}s")
                else:
                    print(f"[jupiter] poll error: {exc!r}")
            except Exception as exc:  # keep the daemon alive on API hiccups
                print(f"[jupiter] poll error: {exc!r}")
            await asyncio.sleep(backoff_s)
