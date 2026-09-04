"""Minimal Binance spot REST klines fetcher (for paper-trader training)."""
from __future__ import annotations

import httpx


def fetch_klines(
    client: httpx.Client,
    symbol: str,
    start_ms: int,
    end_ms: int,
    interval: str = "1m",
    rest_url: str = "https://api.binance.com",
) -> list[list]:
    """Raw kline lists from /api/v3/klines, paged, newest-last."""
    out: list[list] = []
    cursor = start_ms
    while cursor < end_ms:
        resp = client.get(
            f"{rest_url}/api/v3/klines",
            params={
                "symbol": symbol.upper(),
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms - 1,
                "limit": 1000,
            },
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        out.extend(batch)
        cursor = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    return out
