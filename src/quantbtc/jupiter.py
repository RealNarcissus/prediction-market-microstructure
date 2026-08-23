from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

PRICE_SCALE = 1_000_000  # docs: 1,000,000 = $1.00


@dataclass(frozen=True)
class JupiterMarket:
    market_id: str
    event_id: str
    title: str
    status: str  # open | closed | cancelled
    result: str | None  # null | yes | no
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
        # Response envelope ({"events": [...]} vs bare list) confirmed in recon.
        if isinstance(data, dict) and key in data:
            return data[key]
        return data

    async def get_events(
        self, event_filter: str = "live", include_markets: bool = True
    ) -> list[dict]:
        data = await self._get(
            "/events",
            {"filter": event_filter, "includeMarkets": str(include_markets).lower()},
        )
        return self._unwrap(data, "events")

    async def get_market(self, market_id: str) -> dict:
        return await self._get(f"/markets/{market_id}")

    async def get_orderbook(self, market_id: str) -> dict:
        return await self._get(f"/orderbook/{market_id}")

    async def trading_status(self) -> dict:
        return await self._get("/trading-status")

    async def aclose(self) -> None:
        await self._client.aclose()
