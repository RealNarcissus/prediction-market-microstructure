"""Liquidity-formation analysis: when does a tradeable book exist?

For every Polymarket up/down epoch (Up-token rows only), measures the time
from window open until the quote becomes "real" under three spread
thresholds (<=10c, <=5c, <=2c), per asset/horizon. Also records the best
ask at the moment each threshold is first met — the earliest price a
paper entry could actually get.

Output: research/phase_b/LIQUIDITY.md + data/polymarket/liquidity.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

DATA = Path(__file__).resolve().parents[2] / "data/polymarket"
OUT_MD = Path(__file__).resolve().parents[1] / "phase_b" / "LIQUIDITY.md"
THRESHOLDS = [0.10, 0.05, 0.02]


def load_up_token_books() -> pl.DataFrame:
    frames = []
    for f in sorted(DATA.glob("orderbooks_*.parquet")):
        ob = pl.read_parquet(f)
        if ob.height == 0:
            continue
        ob = ob.filter(pl.col("question").str.contains("(?i)up"))
        ob = ob.with_columns(
            pl.col("timestamp").dt.epoch("ms").alias("ts_ms"),
            pl.col("market_id")
            .str.extract(r"-(\d{10})$", 1)
            .cast(pl.Int64)
            .mul(1000)
            .alias("open_ms"),
            pl.col("market_id")
            .str.extract(r"updown-(\d+?m)-", 1)
            .alias("hz"),
        )
        # january-era files use numeric ids (pre-sluggify): unusable here
        ob = ob.filter(pl.col("open_ms").is_not_null())
        # only the first 3 minutes after open matter for entry timing
        ob = ob.filter(
            (pl.col("ts_ms") >= pl.col("open_ms"))
            & (pl.col("ts_ms") <= pl.col("open_ms") + 180_000)
        )
        if ob.height:
            frames.append(ob.select(
                ["market_id", "asset", "hz", "open_ms", "ts_ms",
                 "best_bid", "best_ask", "spread"]
            ))
    return pl.concat(frames) if frames else pl.DataFrame()


def main() -> None:
    books = load_up_token_books()
    if books.is_empty():
        print("no orderbook data found")
        return

    books = books.with_columns(
        ((pl.col("ts_ms") - pl.col("open_ms")) // 1000).alias("secs_from_open"),
        pl.when(pl.col("spread") <= THRESHOLDS[2]).then(pl.lit("t002"))
        .when(pl.col("spread") <= THRESHOLDS[1]).then(pl.lit("t005"))
        .when(pl.col("spread") <= THRESHOLDS[0]).then(pl.lit("t010"))
        .otherwise(pl.lit("wide")).alias("band"),
    )

    # first time each market reaches each band (and its ask at that moment)
    firsts = (
        books.filter(pl.col("band") != "wide")
        .sort("ts_ms")
        .group_by(["market_id", "asset", "hz", "band"])
        .agg(
            pl.col("secs_from_open").first().alias("sec"),
            pl.col("best_ask").first().alias("ask_at_formation"),
        )
    )
    piv = firsts.pivot(on="band", index=["market_id", "asset", "hz"],
                       values="sec").fill_null(180)
    asks = firsts.pivot(on="band", index=["market_id"], values="ask_at_formation")

    lines = [
        "# Liquidity formation after epoch open (Up-token books)",
        "",
        "Time until spread first reaches threshold; seconds from open.",
        "",
        "| asset | hz | n | t<=10c med/p90 | t<=5c med/p90 | t<=2c med/p90 |",
        "|---|---|---|---|---|---|",
    ]
    for (asset, hz), g in sorted(piv.group_by(["asset", "hz"]),
                                 key=lambda kv: kv[0]):
        n = g.height
        row = [asset, hz, str(n)]
        for band in ("t010", "t005", "t002"):
            if band in g.columns:
                s = sorted(g[band].to_list())
                row.append(f"{s[len(s)//2]:.0f}s/{s[int(len(s)*0.9)]:.0f}s")
            else:
                row.append("n/a")
        lines.append("| " + " | ".join(row) + " |")

    overall = {b: sorted(piv[b].to_list()) for b in ("t010", "t005", "t002") if b in piv.columns}
    lines += ["", "**Overall medians:** " + ", ".join(
        f"{b}: {v[len(v)//2]:.0f}s" for b, v in overall.items()
    )]
    lines += [
        "",
        "Ask at formation (median): " + ", ".join(
            f"{b}: {asks[b].median():.2f}" for b in ("t010", "t005", "t002")
            if b in asks.columns
        ),
    ]

    OUT_MD.write_text("\n".join(lines) + "\n")
    piv.join(asks, on="market_id", how="left").write_parquet(
        DATA / "liquidity.parquet"
    )
    print("\n".join(lines))
    print(f"\nwrote {OUT_MD} and data/polymarket/liquidity.parquet")


if __name__ == "__main__":
    main()
