"""Cross-validate orderbook snapshot semantics against executed trades.

For sampled trades: find the latest snapshot <= trade ts for the same
(market_id, token_id). Report:
  - fraction of trades inside [best_bid, best_ask] of that snapshot
  - |price - mid| distribution
  - a worked example: one market's quote evolution vs its trades
Verdict rule: >70% inside => snapshots are true two-sided books.
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

DATA = Path(__file__).resolve().parents[2] / "data/polymarket"
DAY = "2026-03-06"


def main() -> None:
    ob = pl.read_parquet(DATA / f"orderbooks_{DAY}.parquet")
    tr = pl.read_parquet(DATA / f"trades_{DAY}.parquet")

    ob = ob.with_columns(
        pl.col("timestamp").dt.epoch("ms").alias("ts_ms"),
    ).select(["market_id", "token_id", "ts_ms", "best_bid", "best_ask", "mid_price"])
    tr = tr.with_columns(
        pl.col("timestamp").dt.epoch("ms").alias("ts_ms"),
    ).select(["market_id", "token_id", "ts_ms", "side", "price", "size"])

    # pick the 5 most-traded markets
    top = (
        tr.group_by("market_id").len().sort("len", descending=True)
        .head(5)["market_id"].to_list()
    )
    tr_t = tr.filter(pl.col("market_id").is_in(top))
    ob_t = ob.filter(pl.col("market_id").is_in(top)).sort("ts_ms")

    # join AsOf per token: latest snapshot at/before each trade
    joined = pl.DataFrame()
    for mid in top:
        t_m = tr_t.filter(pl.col("market_id") == mid).sort("ts_ms")
        o_m = ob_t.filter(pl.col("market_id") == mid)
        j = t_m.join_asof(o_m, on="ts_ms", by="token_id", strategy="backward")
        joined = pl.concat([joined, j])

    j = joined.drop_nulls(["best_bid"])
    inside = (j["price"] >= j["best_bid"]) & (j["price"] <= j["best_ask"])
    dist_mid = (j["price"] - j["mid_price"]).abs()
    print(f"trades checked: {j.height} across {len(top)} markets")
    print(f"inside [bid,ask]: {inside.mean():.1%}")
    print(f"|price-mid|: median {dist_mid.median():.4f}, p90 {dist_mid.quantile(0.9):.4f}")
    print(f"snapshot spreads: median {(j['best_ask']-j['best_bid']).median():.3f}")

    # worked example: richest token's first 3 minutes
    ex_mid = top[0]
    ex_tok = (
        tr_t.filter(pl.col("market_id") == ex_mid)["token_id"]
        .mode()[0]
    )
    o = ob_t.filter((pl.col("market_id") == ex_mid) & (pl.col("token_id") == ex_tok))
    o = o.filter(pl.col("ts_ms") % 10_000 < 200).head(12)  # ~every 10s
    print(f"\nworked example {ex_mid} token ...{str(ex_tok)[-6:]}:")
    for r in o.iter_rows(named=True):
        t = datetime_str(r["ts_ms"])
        print(f"  {t}  bid {r['best_bid']:.3f} ask {r['best_ask']:.3f}")
    ex_tr = (
        tr_t.filter((pl.col("market_id") == ex_mid) & (pl.col("token_id") == ex_tok))
        .sort("ts_ms").head(8)
    )
    print("  trades:")
    for r in ex_tr.iter_rows(named=True):
        print(f"  {datetime_str(r['ts_ms'])}  {r['side']:4s} {r['price']:.3f} x{r['size']:.0f}")


def datetime_str(ms: int) -> str:
    import datetime as dt

    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%H:%M:%S")


if __name__ == "__main__":
    main()
