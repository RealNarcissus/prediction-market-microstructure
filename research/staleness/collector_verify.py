"""Collector data integrity verification (round 51 — the replay/verify
discipline adopted from 0xpoot-poot/polymarket-5m-recorder).

Checks (no mutation, read-only):
  1. collector.db quotes: duplicate (ts_ms, market_id, side) rows
  2. per-market timestamp monotonicity
  3. book sanity: rows with bid >= ask (crossed/locked) or bid/ask <= 0
  4. poll-gap report: max inter-quote gap per market (top offenders)
  5. resolutions: duplicate market rows, outcome value domain
  6. TWAP tape files: monotonic observed_at per (symbol, window),
     duplicate (observed_at, symbol, window), value sanity (0 < v < 1e7)

Output: VERIFY_REPORT.md + console summary. Exit code 1 if any hard error
(duplicates, domain violations); warnings (gaps, crossed rows) exit 0.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "collector.db"
TAPE_DIR = REPO / "data" / "twap_tape"
OUT = REPO / "research" / "staleness" / "VERIFY_REPORT.md"

HARD = []   # errors
SOFT = []   # warnings


def main() -> None:
    lines = ["# Collector data integrity verification", ""]

    conn = sqlite3.connect(str(DB))
    quotes = pl.read_database(
        "SELECT ts_ms, market_id, side, bid, ask FROM quotes", conn)
    res = pl.read_database("SELECT market_id, outcome FROM resolutions", conn)
    conn.close()

    # 1. duplicates
    dup = (quotes.group_by(["ts_ms", "market_id", "side"]).len()
                 .filter(pl.col("len") > 1))
    lines.append(f"## quotes: {quotes.height:,} rows")
    lines.append(f"- duplicate (ts_ms, market_id, side): {dup.height}")
    if dup.height:
        HARD.append(f"{dup.height} duplicate quote keys")
        lines.append("  - " + "; ".join(str(t) for t in dup.head(3).to_dicts()))

    # 2. monotonic ts per market
    bad_mono = 0
    for (mk,), g in quotes.sort("ts_ms").group_by(["market_id"]).agg(
        pl.col("ts_ms")
    ).to_dicts() and []:
        pass
    tsg = quotes.sort("ts_ms").group_by("market_id").agg(pl.col("ts_ms"))
    for row in tsg.to_dicts():
        a = np.asarray(row["ts_ms"])
        if (np.diff(a) < 0).any():
            bad_mono += 1
    lines.append(f"- markets with non-monotonic ts: {bad_mono}")
    if bad_mono:
        SOFT.append(f"{bad_mono} non-monotonic markets")

    # 3. book sanity
    crossed = quotes.filter(
        (pl.col("bid") >= pl.col("ask"))
        | (pl.col("bid") <= 0) | (pl.col("ask") <= 0)
    )
    lines.append(f"- crossed/invalid book rows: {crossed.height} ({crossed.height/quotes.height*100:.3f}%)")
    if crossed.height:
        SOFT.append(f"{crossed.height} crossed/invalid book rows")

    # 4. poll gaps (top 5)
    gaps = (quotes.sort("ts_ms")
                  .group_by("market_id")
                  .agg(pl.col("ts_ms").max().alias("mx"), pl.col("ts_ms").min().alias("mn"),
                       pl.len().alias("n")))
    lines.append(f"- markets: {gaps.height:,}")
    conn2 = sqlite3.connect(str(DB))
    mm = pl.read_database("SELECT market_id, close_time_ms FROM markets", conn2)
    conn2.close()
    gaps = gaps.join(mm, on="market_id", how="inner")
    # largest gap between consecutive quotes vs market life
    top = (quotes.sort("ts_ms")
                 .with_columns(pl.col("ts_ms").diff().over("market_id").alias("gap"))
                 .filter(pl.col("gap").is_not_null())
                 .group_by("market_id").agg(pl.col("gap").max().alias("max_gap"))
                 .sort("max_gap", descending=True).head(5))
    lines.append("- top max inter-quote gaps:")
    for row in top.to_dicts():
        secs = row["max_gap"] / 1000.0
        flag = " WARN" if secs > 600 else ""
        if secs > 1800:
            HARD.append(f"market {row['market_id']} gap {secs:.0f}s")
        lines.append(f"  - {row['market_id']}: {secs:.0f}s{flag}")

    # 5. resolutions
    dupr = res.group_by("market_id").len().filter(pl.col("len") > 1)
    bad_out = res.filter(~pl.col("outcome").is_in(["up", "down"]))
    lines.append(f"## resolutions: {res.height:,} rows")
    lines.append(f"- duplicate market rows: {dupr.height}")
    lines.append(f"- outcome outside (up,down): {bad_out.height}")
    if dupr.height:
        HARD.append(f"{dupr.height} duplicate resolution rows")
    if bad_out.height:
        HARD.append(f"{bad_out.height} bad outcome values")

    # 6. TWAP tape
    files = sorted(TAPE_DIR.glob("*.parquet"))
    if files:
        tape = pl.concat([pl.read_parquet(str(f)) for f in files])
        dup_t = (tape.group_by(["observed_at_ms", "symbol", "window_s"]).len()
                     .filter(pl.col("len") > 1))
        mono_bad = 0
        for row in tape.sort("observed_at_ms").group_by(["symbol", "window_s"]).agg(
            pl.col("observed_at_ms")
        ).to_dicts():
            a = np.asarray(row["observed_at_ms"])
            if (np.diff(a) < 0).any():
                mono_bad += 1
        bad_val = tape.filter(
            (pl.col("value_str").cast(pl.Float64, strict=False) <= 0)
            | (pl.col("value_str").cast(pl.Float64, strict=False) > 1e7)
        )
        lines.append(f"## twap tape: {tape.height:,} rows across {len(files)} files")
        lines.append(f"- duplicate (observed_at, symbol, window): {dup_t.height}")
        lines.append(f"- non-monotonic series: {mono_bad}")
        lines.append(f"- value out of (0, 1e7): {bad_val.height}")
        if dup_t.height:
            HARD.append(f"{dup_t.height} duplicate tape keys")
        if bad_val.height:
            HARD.append(f"{bad_val.height} bad tape values")
    else:
        lines.append("## twap tape: no files yet")

    verdict = "FAIL" if HARD else "PASS"
    lines.insert(1, f"**Verdict: {verdict}**")
    if HARD:
        lines.append("")
        lines.append("Hard errors:")
        lines += [f"- {h}" for h in HARD]
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))
    sys.exit(1 if HARD else 0)


import numpy as np  # noqa: E402

if __name__ == "__main__":
    main()
