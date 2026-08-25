"""Download Binance Vision monthly 1m klines + REST tail -> continuous series."""
from __future__ import annotations

import datetime as dt
import io
import time
import zipfile
from pathlib import Path

import httpx
import polars as pl

sys_path = str(Path(__file__).resolve().parents[2] / "src")
if sys_path not in __import__("sys").path:
    import sys as _sys

    _sys.path.insert(0, sys_path)
from quantbtc.binance_rest import fetch_klines  # noqa: E402

OUT = Path("data/klines")
ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
MONTHS = [f"2025-{m:02d}" for m in range(8, 13)] + [f"2026-{m:02d}" for m in range(1, 9)]
COLS = ["open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "count", "taker_buy_base_volume",
        "taker_buy_quote_volume", "ignore"]


def vision_month(client: httpx.Client, symbol: str, month: str) -> pl.DataFrame | None:
    url = f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/1m/{symbol}-1m-{month}.zip"
    r = client.get(url, timeout=120.0)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    name = zf.namelist()[0]
    df = pl.read_csv(io.BytesIO(zf.read(name)), has_header=False)
    df.columns = COLS
    # newer Vision files ship decimal STRINGS; normalize types
    df = df.with_columns([
        pl.col("open_time").cast(pl.Int64),
        pl.col("close_time").cast(pl.Int64),
        pl.col("count").cast(pl.Int64),
        *[pl.col(c).cast(pl.Float64) for c in (
            "open", "high", "low", "close", "volume", "quote_volume",
            "taker_buy_base_volume", "taker_buy_quote_volume",
        )],
    ])
    return df


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = httpx.Client(timeout=120.0)
    now_ms = int(time.time() * 1000)
    floats = ["open", "high", "low", "close", "volume", "quote_volume",
              "taker_buy_base_volume", "taker_buy_quote_volume"]
    for symbol in ASSETS:
        frames = []
        for month in MONTHS:
            try:
                df = vision_month(client, symbol, month)
            except Exception as exc:
                print(f"{symbol} {month}: error {exc!r}")
                time.sleep(2)
                continue
            if df is None:
                print(f"{symbol} {month}: not published yet")
                continue
            frames.append(df)
            print(f"{symbol} {month}: {df.height} rows")
            time.sleep(0.3)
        if not frames:
            continue
        full = pl.concat(frames).unique(subset=["open_time"]).sort("open_time")
        # Vision recently switched to MICROSECOND open_time + string prices
        full = full.with_columns([
            pl.when(pl.col("open_time") > 10**14)
              .then(pl.col("open_time") // 1000)
              .otherwise(pl.col("open_time")).cast(pl.Int64).alias("open_time"),
            *[pl.col(c).cast(pl.Float64) for c in floats],
            pl.col("count").cast(pl.Int64),
            pl.col("close_time").cast(pl.Int64),
        ]).drop_nulls(["open_time"])

        # REST tail for the current (unpublished) month
        path = OUT / f"{symbol}_1m.parquet"
        last = int(full["open_time"][-1])
        start = last + 60_000
        raw = []
        try:
            raw = fetch_klines(client, symbol, start, now_ms,
                               rest_url="https://api.binance.com")
        except Exception as exc:
            print(f"{symbol} REST tail error: {exc!r}")
        if raw:
            tail = pl.DataFrame({
                "open_time": [int(k[0]) for k in raw],
                "open": [float(k[1]) for k in raw],
                "high": [float(k[2]) for k in raw],
                "low": [float(k[3]) for k in raw],
                "close": [float(k[4]) for k in raw],
                "volume": [float(k[5]) for k in raw],
                "quote_volume": [float(k[7]) for k in raw],
                "count": [int(k[8]) for k in raw],
                "taker_buy_base_volume": [float(k[9]) for k in raw],
                "taker_buy_quote_volume": [float(k[10]) for k in raw],
                "close_time": [int(k[6]) for k in raw],
                "ignore": [0] * len(raw),
            })
            full = pl.concat([full, tail.select(full.columns)]).unique(
                subset=["open_time"]
            ).sort("open_time")
        full.write_parquet(path)
        t0 = dt.datetime.fromtimestamp(full["open_time"][0] / 1000, tz=dt.timezone.utc)
        t1 = dt.datetime.fromtimestamp(full["open_time"][-1] / 1000, tz=dt.timezone.utc)
        print(f"-> {path}: {full.height} rows ({t0.date()} .. {t1.date()})")


if __name__ == "__main__":
    main()
