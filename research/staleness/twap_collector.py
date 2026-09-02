"""Chainlink TWAP tape collector (round 41 — strike-basis job, step 1).

Subscribes to Polymarket RTDS (credential-free) at wss://ws-live-data.polymarket.com
for the topic `prices.crypto.chainlink.twap`, windows 30s and 60s, symbols
btc/usd, eth/usd, sol/usd. Appends (observed_at_ms, symbol, window_s, value_str)
rows to data/twap_tape.parquet (flushed per batch, Parquet per session file).

This is the venue-native strike/settlement series — the input for the
strike-basis decomposition of the extreme-band residual (round 34 finding)
and for replacing the Binance-proxy strike in fair_v2.

Run:  .venv/bin/python research/staleness/twap_collector.py [seconds]
Deployment (after validation): mirror the collector systemd unit pattern.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "data" / "twap_tape"
URL = "wss://ws-live-data.polymarket.com"
SYMBOLS = ["btc/usd", "eth/usd", "sol/usd"]
WINDOWS = [30, 60]


def subscribe_msg() -> str:
    # RTDS wire protocol (reverse-engineered from @polymarket/client 0.8.1):
    # subscriptions are {topic: <server key>, type: "update"}; symbols are
    # filtered client-side. Keys: crypto_prices_twap_{thirty,sixty}.
    subs = [
        {"topic": f"crypto_prices_twap_{'thirty' if w == 30 else 'sixty'}", "type": "update"}
        for w in WINDOWS
    ]
    return json.dumps({"action": "subscribe", "subscriptions": subs})


def flush(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    df = pl.DataFrame(rows)
    if path.exists():
        old = pl.read_parquet(str(path))
        df = pl.concat([old, df]).unique(subset=["observed_at_ms", "symbol", "window_s"], keep="last")
    df.sort("observed_at_ms").write_parquet(str(path))


async def run(seconds: int) -> None:
    import websockets

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"twap_{time.strftime('%Y%m%d_%H%M%S')}.parquet"
    rows: list[dict] = []
    last_flush = time.time()
    deadline = (time.time() + seconds) if seconds > 0 else None  # 0 = continuous
    print(f"connecting {URL} ...", flush=True)
    # Origin header required — bare connects get reset by the gateway
    headers = {"Origin": "https://polymarket.com", "User-Agent": "Mozilla/5.0"}
    async with websockets.connect(URL, ping_interval=20, additional_headers=headers, open_timeout=15) as ws:
        await ws.send(subscribe_msg())
        print(f"subscribed: {SYMBOLS} windows={WINDOWS}", flush=True)
        while deadline is None or time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=10)
            except asyncio.TimeoutError:
                continue
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            # events may arrive single or batched
            events = msg if isinstance(msg, list) else [msg]
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                payload = ev.get("payload", {})
                if not isinstance(payload, dict):
                    continue
                sym = payload.get("symbol", "")
                if str(sym).lower() not in SYMBOLS:
                    continue
                val = payload.get("value")
                obs = payload.get("timestamp")
                topic = str(ev.get("topic", ""))
                win = 60 if "sixty" in topic else (30 if "thirty" in topic else -1)
                if val is None or obs is None:
                    continue
                rows.append({
                    "observed_at_ms": int(obs),
                    "symbol": str(sym),
                    "window_s": win,
                    "value_str": str(val),
                    "recv_at_ms": int(time.time() * 1000),
                })
            if rows and time.time() - last_flush > 5:
                flush(rows, path)
                print(f"flushed {len(rows)} rows -> {path.name}", flush=True)
                rows = []
                last_flush = time.time()
    flush(rows, path)
    print(f"final flush {len(rows)} rows -> {path.name}", flush=True)


def main() -> None:
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 0  # 0 = continuous (service mode)
    attempt = 0
    while True:
        try:
            asyncio.run(run(seconds))
            if seconds > 0:
                return
        except (ConnectionResetError, OSError) as e:
            attempt += 1
            wait = min(5 * attempt, 60)
            print(f"connect failed ({type(e).__name__}); retry in {wait}s", flush=True)
            time.sleep(wait)


if __name__ == "__main__":
    main()
