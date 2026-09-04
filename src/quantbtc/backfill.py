from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

from quantbtc.binance_ws import hour_key

HOUR_MS = 3600 * 1000


def missing_hours(start_ms: int, end_ms: int, have_hours: set[int]) -> list[int]:
    h = (start_ms // HOUR_MS) * HOUR_MS
    out = []
    while h < end_ms:
        if h not in have_hours and h >= start_ms:
            out.append(h)
        h += HOUR_MS
    return out


def fetch_klines(
    client: httpx.Client,
    rest_url: str,
    symbol: str,
    start_ms: int,
    end_ms: int,
    interval: str = "1m",
) -> list[dict]:
    """Spot /api/v3/klines (same array layout as futures): index 9 is
    taker-buy base volume."""
    rows: list[dict] = []
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
        for k in batch:
            rows.append(
                {
                    "ts_ms": k[0],
                    "symbol": symbol.upper(),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "taker_buy_base_volume": float(k[9]),
                    "quote_volume": float(k[7]),
                }
            )
        cursor = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    return rows


def backfill(
    parquet_dir: str | Path, symbol: str, hours: list[int], rest_url: str
) -> int:
    root = Path(parquet_dir) / symbol.upper() / "kline_1m"
    written = 0
    with httpx.Client(timeout=30.0) as client:
        for h in hours:
            rows = fetch_klines(client, rest_url, symbol, h, h + HOUR_MS)
            if not rows:
                continue
            path = root / f"{hour_key(h)}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            pl.DataFrame(rows).write_parquet(path)
            written += len(rows)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--hours-ago", type=int, default=24)
    ap.add_argument("--parquet-dir", default="data/raw")
    ap.add_argument("--config", default="config/config.yaml")
    args = ap.parse_args()

    from quantbtc.config import load_config

    cfg = load_config(args.config)
    now = int(time.time() * 1000)
    start = now - args.hours_ago * HOUR_MS
    root = Path(args.parquet_dir) / args.symbol.upper() / "kline_1m"
    have: set[int] = set()
    if root.exists():
        for f in root.glob("*.parquet"):
            have.add(
                int(
                    datetime.strptime(f.stem, "%Y%m%d%H")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                    * 1000
                )
            )
    hours = missing_hours(start, now, have)
    n = backfill(args.parquet_dir, args.symbol, hours, cfg.binance.rest_url)
    print(f"backfilled {n} klines across {len(hours)} hours for {args.symbol}")


if __name__ == "__main__":
    main()
