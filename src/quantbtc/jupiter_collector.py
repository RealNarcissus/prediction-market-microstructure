from __future__ import annotations

import asyncio
import time

from quantbtc.jupiter import (
    JupiterClient,
    best_bid_ask,
    parse_epoch_event,
    parse_orderbook,
)
from quantbtc.store import Store

# Verified live (docs/RECON.md): up/down epochs are discovered per horizon tag.
HORIZON_TAGS = ("5m", "15m")


class JupiterPoller:
    """Polls up/down epochs; records best bid/ask for active epochs and
    final resolutions after close. poll_once is the pure testable step."""

    def __init__(
        self,
        client: JupiterClient,
        store: Store,
        assets: tuple[str, ...] = ("BTC", "ETH", "SOL"),
        result_delay_s: float = 5.0,
        poll_interval_s: float = 2.0,
    ):
        self.client = client
        self.store = store
        self.assets = assets
        self.result_delay_ms = int(result_delay_s * 1000)
        self.poll_interval_s = poll_interval_s

    async def poll_once(self, now_ms: int | None = None) -> None:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        for tag in HORIZON_TAGS:
            events = await self.client.get_events(
                category="crypto", tags=tag, include_markets=True
            )
            for event in events:
                ep = parse_epoch_event(event)
                if ep is None or ep.asset not in self.assets:
                    continue
                await self._process_epoch(ep, now_ms)

    async def _process_epoch(self, ep, now_ms: int) -> None:
        for market_id, side in (
            (ep.up_market_id, "up"),
            (ep.down_market_id, "down"),
        ):
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

        active = ep.epoch_start_ms <= now_ms < ep.close_ms
        if active and ep.status == "open" and ep.up_market_id:
            # The Up market's yes/no ladders ARE both sides (buying no-Up
            # == betting Down), so one orderbook call covers the epoch.
            ob = parse_orderbook(
                await self.client.get_orderbook(ep.up_market_id)
            )
            rows = []
            for side, levels in (("up", ob["yes"]), ("down", ob["no"])):
                bid, ask = best_bid_ask(levels)
                rows.append(
                    {
                        "ts_ms": now_ms,
                        "market_id": ep.up_market_id,
                        "side": side,
                        "bid": bid,
                        "ask": ask,
                        "bid_qty": max(levels, key=lambda l: l.price).qty
                        if levels
                        else None,
                        "ask_qty": min(levels, key=lambda l: l.price).qty
                        if levels
                        else None,
                    }
                )
            self.store.insert_quotes(rows)

        if (
            not active
            and now_ms >= ep.close_ms + self.result_delay_ms
            and ep.up_market_id
            and ep.down_market_id
            and self.store.resolution(ep.up_market_id) is None
        ):
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
        while True:
            try:
                await self.poll_once()
                self.store.set_state(
                    "last_poll_ms", str(int(time.time() * 1000))
                )
            except Exception as exc:  # keep the daemon alive on API hiccups
                print(f"[jupiter] poll error: {exc!r}")
            await asyncio.sleep(self.poll_interval_s)
