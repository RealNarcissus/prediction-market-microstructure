from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx

PRICE_SCALE = 1_000_000  # docs: 1,000,000 = $1.00 (pricing fields on /markets)

# Verified live 2026-08-23: up/down epochs are discovered via
# GET /events?category=crypto&tags=5m (or 15m); slug = {asset}-updown-{5m|15m}-{unix_start}
_SLUG_RE = re.compile(r"^(?P<asset>[a-z]+)-updown-(?P<hz>5m|15m)-(?P<start>\d{10})$")
_HORIZON_S = {"5m": 300, "15m": 900}


@dataclass(frozen=True)
class EpochEvent:
    """One up/down epoch (an event with Up and Down markets)."""

    event_id: str
    asset: str  # BTC | ETH | SOL | XRP | DOGE (subcategory upper-cased)
    horizon_s: int  # 300 | 900
    slug: str
    title: str
    epoch_start_ms: int  # from slug timestamp
    close_ms: int  # markets' closeTime (epoch end)
    up_market_id: str | None
    down_market_id: str | None
    status: str  # from first market
    result: str | None  # from first market ("Up"/"Down" resolved titles)


@dataclass(frozen=True)
class JupiterMarket:
    market_id: str
    event_id: str
    title: str
    status: str  # open | closed | cancelled
    result: str | None
    open_time_ms: int
    close_time_ms: int
    buy_yes_usd: float | None
    buy_no_usd: float | None
    sell_yes_usd: float | None
    sell_no_usd: float | None
    volume: float | None


@dataclass(frozen=True)
class Level:
    price: float
    qty: float


def _usd(raw) -> float | None:
    if raw is None:
        return None
    return raw / PRICE_SCALE


def _ms(seconds) -> int:
    return int(seconds) * 1000 if seconds is not None else 0


def parse_epoch_event(d: dict) -> EpochEvent | None:
    """Parse an up/down epoch event; returns None for non-updown events."""
    meta = d.get("metadata") or {}
    slug = meta.get("slug", "")
    m = _SLUG_RE.match(slug)
    if not m:
        return None
    markets = d.get("markets") or []
    up_id = down_id = None
    status, result, close_s = "", None, 0
    for mk in markets:
        title = (mk.get("title") or "").strip().lower()
        if title == "up":
            up_id = mk.get("marketId")
        elif title == "down":
            down_id = mk.get("marketId")
        if not status:
            status = mk.get("status", "")
            result = mk.get("result")
        close_s = max(close_s, int(mk.get("closeTime") or 0))
    return EpochEvent(
        event_id=d.get("eventId") or "",
        asset=m["asset"].upper(),
        horizon_s=_HORIZON_S[m["hz"]],
        slug=slug,
        title=meta.get("title", ""),
        epoch_start_ms=int(m["start"]) * 1000,
        close_ms=close_s * 1000,
        up_market_id=up_id,
        down_market_id=down_id,
        status=status,
        result=result,
    )


def parse_market(d: dict) -> JupiterMarket:
    pricing = d.get("pricing") or {}
    return JupiterMarket(
        market_id=d["marketId"],
        event_id=d.get("eventId", ""),
        title=d.get("title", ""),
        status=d.get("status", ""),
        result=d.get("result"),
        open_time_ms=_ms(d.get("openTime")),
        close_time_ms=_ms(d.get("closeTime")),
        buy_yes_usd=_usd(pricing.get("buyYesPriceUsd")),
        buy_no_usd=_usd(pricing.get("buyNoPriceUsd")),
        sell_yes_usd=_usd(pricing.get("sellYesPriceUsd")),
        sell_no_usd=_usd(pricing.get("sellNoPriceUsd")),
        volume=_usd(pricing.get("volume")),
    )


def parse_orderbook(d: dict) -> dict[str, list[Level]]:
    """`yes`/`no` arrays are [price_in_cents, qty]; normalize price to USD."""
    out: dict[str, list[Level]] = {}
    for side in ("yes", "no"):
        out[side] = [
            Level(price=float(p) / 100.0, qty=float(q)) for p, q in d.get(side, [])
        ]
    return out


def best_bid_ask(levels: list[Level]) -> tuple[float | None, float | None]:
    if not levels:
        return None, None
    prices = [lv.price for lv in levels]
    return max(prices), min(prices)


_ASSET_RE = re.compile(r"\b(BTC|ETH|SOL)\b")
_HORIZON_RE = re.compile(r"\b(5|15)\s*[- ]?\s*(min|minute)", re.IGNORECASE)


def extract_asset_horizon(title: str) -> tuple[str | None, int | None]:
    asset = _ASSET_RE.search(title)
    hz = _HORIZON_RE.search(title)
    return (
        asset.group(1) if asset else None,
        int(hz.group(1)) * 60 if hz else None,
    )


class JupiterClient:
    """Thin async wrapper over api.jup.ag/prediction/v1. No secrets in code."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self._client = httpx.AsyncClient(
            base_url=base_url, headers=self._headers(api_key), timeout=10.0
        )

    @staticmethod
    def _headers(api_key: str | None) -> dict[str, str]:
        headers = {"accept": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        return headers

    async def _get(self, path: str, params: dict | None = None):
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _unwrap(data, key: str):
        # Verified live 2026-08-23: envelope is {"data": [...], "pagination": {...}}.
        if isinstance(data, dict) and key in data:
            return data[key]
        return data

    async def get_events(
        self,
        category: str | None = None,
        tags: str | None = None,
        event_filter: str | None = None,
        include_markets: bool = True,
        start: int | None = None,
    ) -> list[dict]:
        params: dict[str, str] = {"includeMarkets": str(include_markets).lower()}
        if category:
            params["category"] = category
        if tags:
            params["tags"] = tags
        if event_filter:
            params["filter"] = event_filter
        if start is not None:
            params["start"] = start
        data = await self._get("/events", params)
        return self._unwrap(data, "data")

    async def get_event_search(self, query: str, limit: int = 20) -> list[dict]:
        """Keyword search — recency-ranked, reliably surfaces LIVE epochs
        (the tags listing can bury the active epoch under past ones)."""
        data = await self._get("/events/search", {"query": query, "limit": limit})
        return self._unwrap(data, "data")

    async def get_event(self, event_id: str) -> dict:
        """Full event incl. complete embedded markets (search results return
        a markets list WITHOUT marketIds/status)."""
        data = await self._get(f"/events/{event_id}")
        return self._unwrap(data, "data")

    async def get_market(self, market_id: str) -> dict:
        return await self._get(f"/markets/{market_id}")

    async def get_orderbook(self, market_id: str) -> dict:
        return await self._get(f"/orderbook/{market_id}")

    async def trading_status(self) -> dict:
        return await self._get("/trading-status")

    async def aclose(self) -> None:
        await self._client.aclose()
