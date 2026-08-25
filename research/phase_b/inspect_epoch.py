"""Inspect one epoch's books + trades (file-based, no heredoc quirks)."""
import sys
from datetime import datetime, timezone

import polars as pl

slug = sys.argv[1] if len(sys.argv) > 1 else "btc-updown-5m-1773100800"
day = "2026-03-10"

ob = (
    pl.read_parquet(f"data/polymarket/orderbooks_{day}.parquet")
    .filter(pl.col("market_id") == slug)
    .with_columns(pl.col("timestamp").dt.epoch("ms").alias("ts_ms"))
    .drop_nulls(["mid_price"])
)
trades = (
    pl.read_parquet(f"data/polymarket/trades_{day}.parquet")
    .filter(pl.col("market_id") == slug)
    .with_columns(pl.col("timestamp").dt.epoch("ms").alias("ts_ms"))
    .sort("ts_ms")
)

finals = {}
for t_key, g in ob.group_by("token_id"):
    t = t_key[0] if isinstance(t_key, tuple) else t_key
    finals[t] = float(g.sort("ts_ms")["mid_price"][-1])
winner = max(finals, key=finals.get)
loser = [t for t in finals if t != winner][0]

print(f"epoch {slug} | trades total {trades.height}")
print("DEBUG trades token_id dtype:", trades.schema["token_id"])
print("DEBUG finals key types:", {type(k).__name__ for k in finals})
for name, tok in (("WINNER", winner), ("LOSER", loser)):
    g = trades.filter(pl.col("token_id") == tok).head(5)
    print(f"{name} ..{str(tok)[-6:]} first prints:")
    for r in g.iter_rows(named=True):
        t = datetime.fromtimestamp(r["ts_ms"] / 1000, timezone.utc).strftime("%H:%M:%S")
        print(f"   {t} {r['side']:4s} {r['price']:.3f} x{r['size']:.1f}")

print("\nwinning-token book, first 10 snapshots:")
g = ob.filter(pl.col("token_id") == winner).sort("ts_ms").head(10)
for r in g.iter_rows(named=True):
    t = datetime.fromtimestamp(r["ts_ms"] / 1000, timezone.utc).strftime("%H:%M:%S")
    print(f"   {t} bid {r['best_bid']:.2f} ask {r['best_ask']:.2f}")
