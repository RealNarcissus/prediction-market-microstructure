"""Phase B ingestion: Polymarket historical 5m/15m data -> epoch bridge table.

Reads data/polymarket/ (markets_all, resolutions_all, orderbooks_*.parquet)
and produces data/polymarket/epochs_bridge.parquet: one row per epoch with
official outcome plus quote-derived decision probes at open+delta:

  entry_ask_up / entry_ask_down : best asks at first snapshot >= open+10s
  mid0                          : opening mid of the Up token

This gives the paper trader's exact decision inputs on REAL historical
quotes — the Phase-B training/backtest substrate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

DATA = Path(__file__).resolve().parents[2] / "data/polymarket"


def load() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    markets = pl.read_parquet(DATA / "markets_all.parquet")
    res = pl.read_parquet(DATA / "resolutions_all.parquet")
    # resolutions use their own id scheme; join on (asset, start_time)
    res_small = res.select(
        pl.col("asset"),
        pl.col("start_time").alias("start"),
        pl.col("outcome"),
        pl.col("resolved_at"),
    )
    m2 = markets.with_columns(
        pl.col("market_type").str.extract(r"crypto_(\w+)", 1).alias("horizon"),
        pl.col("start_time").alias("start"),
    )
    epochs = (
        m2.join(res_small, on=["asset", "start"], how="inner")
        .select(
            "market_id", "asset", "horizon", "start", "end_time",
            "outcome", "resolved_at", "event_id",
        )
        .rename({"start": "open_time_utc", "end_time": "close_time_utc"})
        .sort("open_time_utc")
    )
    return epochs, markets, res


def quote_probes(ob_dir: Path) -> pl.DataFrame:
    """For every epoch, take the first orderbook snapshot in [open+8s,
    open+120s] per outcome token and record best bid/ask. Orderbook
    market_id is the same slug as markets.market_id — direct join."""
    frames = []
    for f in sorted(Path(ob_dir).glob("orderbooks_*.parquet")):
        ob = pl.read_parquet(f)
        if ob.height == 0:
            continue
        ob = ob.with_columns(
            pl.col("timestamp").dt.epoch("ms").alias("ts_ms"),
            pl.col("market_id")
            .str.extract(r"-(\d{10})$", 1)
            .cast(pl.Int64)
            .mul(1000)
            .alias("open_ms"),
        )
        ob = ob.filter(
            (pl.col("ts_ms") >= pl.col("open_ms") + 8_000)
            & (pl.col("ts_ms") <= pl.col("open_ms") + 120_000)
        )
        if ob.height:
            frames.append(ob)

    if not frames:
        return pl.DataFrame()
    ob_all = pl.concat(frames)
    firsts = (
        ob_all.sort("timestamp")
        .group_by(["market_id", "asset", "question"])
        .agg(
            pl.col("ts_ms").first().alias("quote_ts_ms"),
            pl.col("best_bid").first().alias("bid"),
            pl.col("best_ask").first().alias("ask"),
            pl.col("mid_price").first().alias("mid"),
        )
        .with_columns(
            pl.when(pl.col("question").str.contains("(?i)up"))
            .then(pl.lit("up"))
            .otherwise(pl.lit("down"))
            .alias("side_token")
        )
    )
    up = firsts.filter(pl.col("side_token") == "up").select(
        [
            "market_id",
            "quote_ts_ms",
            pl.col("bid").alias("entry_bid_up"),
            pl.col("ask").alias("entry_ask_up"),
            pl.col("mid").alias("mid0_up"),
        ]
    )
    dn = firsts.filter(pl.col("side_token") == "down").select(
        ["market_id",
         pl.col("bid").alias("entry_bid_down"),
         pl.col("ask").alias("entry_ask_down")]
    )
    return up.join(dn, on="market_id", how="full")


def main() -> None:
    epochs, markets, res = load()
    print(f"epochs joined: {epochs.shape}")
    print(epochs.group_by(["asset", "horizon"]).len().sort(["asset"]))
    out = DATA / "epochs_bridge.parquet"
    epochs.write_parquet(out)
    print(f"wrote {out}")

    probes = quote_probes(DATA)
    full = epochs.join(probes, on="market_id", how="left")
    cov = full.filter(pl.col("entry_ask_up").is_not_null()).height
    print(f"epochs with entry quotes: {cov}/{full.height}")
    full.write_parquet(DATA / "epochs_bridge_quotes.parquet")
    print(f"wrote {DATA / 'epochs_bridge_quotes.parquet'}")


if __name__ == "__main__":
    main()
