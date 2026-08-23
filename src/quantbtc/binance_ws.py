from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import websockets


def parse_agg_trade(d: dict) -> dict:
    return {
        "ts_ms": d["T"],
        "symbol": d["s"],
        "price": float(d["p"]),
        "qty": float(d["q"]),
        "agg_buy": not d["m"],  # m=True => buyer is maker => aggressive sell
    }


def parse_kline(d: dict) -> dict:
    k = d["k"]
    return {
        "ts_ms": k["t"],
        "symbol": d["s"],
        "open": float(k["o"]),
        "high": float(k["h"]),
        "low": float(k["l"]),
        "close": float(k["c"]),
        "volume": float(k["v"]),
        "taker_buy_volume": float(k["V"]),
        "quote_volume": float(k["q"]),
    }


def parse_depth(d: dict, fallback_ts_ms: int | None = None) -> dict:
    """Top-of-book from either Binance WS depth format.

    Futures partial depth: {"E": ts, "s": sym, "b": [...], "a": [...]}.
    Spot partial depth: {"lastUpdateId": .., "bids": [...], "asks": [...]}
    (no event time -- fall back to local receive time).
    """

    def lvl(rows: list, i: int) -> tuple[float | None, float | None]:
        if len(rows) <= i:
            return None, None
        return float(rows[i][0]), float(rows[i][1])

    if "b" in d or "a" in d:
        bids, asks, ts, sym = d.get("b", []), d.get("a", []), d.get("E"), d.get("s", "")
    else:
        bids, asks, ts, sym = d.get("bids", []), d.get("asks", []), None, ""

    b1p, b1q = lvl(bids, 0)
    b2p, b2q = lvl(bids, 1)
    a1p, a1q = lvl(asks, 0)
    a2p, a2q = lvl(asks, 1)
    return {
        "ts_ms": ts if ts is not None else (fallback_ts_ms or int(time.time() * 1000)),
        "symbol": sym,
        "bid1_px": b1p,
        "bid1_qty": b1q,
        "bid2_px": b2p,
        "bid2_qty": b2q,
        "ask1_px": a1p,
        "ask1_qty": a1q,
        "ask2_px": a2p,
        "ask2_qty": a2q,
    }


def streams_for(symbols: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for s in symbols:
        out += [f"{s}@aggTrade", f"{s}@depth20@100ms", f"{s}@kline_1m"]
    return out


def hour_key(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y%m%d%H")


class HourlyParquetWriter:
    """Buffers rows and flushes one Parquet file per UTC hour per stream."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._buffers: dict[tuple[str, str, str], list[dict]] = {}

    def add(self, symbol: str, stream: str, row: dict) -> None:
        key = (symbol, stream, hour_key(row["ts_ms"]))
        self._buffers.setdefault(key, []).append(row)

    def flush(self) -> int:
        written = 0
        for (symbol, stream, hour), rows in list(self._buffers.items()):
            path = self.root / symbol / stream / f"{hour}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            new = pl.DataFrame(rows)
            if path.exists():
                new = pl.concat([pl.read_parquet(path), new])
            new.write_parquet(path)
            written += len(rows)
            del self._buffers[(symbol, stream, hour)]
        return written


class BinanceCollector:
    def __init__(self, symbols, ws_url: str, writer: HourlyParquetWriter):
        self.symbols = tuple(symbols)
        self.ws_url = ws_url
        self.writer = writer
        self._stop = asyncio.Event()
        self._last_flush = time.monotonic()

    async def run(self) -> None:
        url = f"{self.ws_url}?streams={'/'.join(streams_for(self.symbols))}"
        backoff = 1.0
        try:
            while not self._stop.is_set():
                try:
                    async with websockets.connect(url, ping_interval=20) as ws:
                        backoff = 1.0
                        async for raw in ws:
                            self._handle(json.loads(raw))
                            if self._stop.is_set():
                                break
                except (websockets.ConnectionClosed, OSError):
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60.0)
        finally:
            # Runs on stop, cancel, and error alike: never lose buffered rows.
            self.writer.flush()

    def _handle(self, msg: dict) -> None:
        stream: str = msg.get("stream", "")
        data: dict = msg.get("data", msg)
        if stream.endswith("@aggTrade"):
            self.writer.add(
                stream.split("@")[0].upper(), "aggTrade", parse_agg_trade(data)
            )
        elif stream.endswith("@kline_1m"):
            self.writer.add(
                stream.split("@")[0].upper(), "kline_1m", parse_kline(data)
            )
        elif "@depth" in stream:
            self.writer.add(
                stream.split("@")[0].upper(),
                "depth20",
                parse_depth(data, fallback_ts_ms=int(time.time() * 1000)),
            )
        # Periodic flush: bound in-memory buffering to ~60s of data.
        now = time.monotonic()
        if now - self._last_flush > 60.0:
            self.writer.flush()
            self._last_flush = now

    def stop(self) -> None:
        self._stop.set()
