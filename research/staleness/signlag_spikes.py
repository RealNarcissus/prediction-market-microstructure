"""Round 38: sign-lag conditional stats + A/B/C spike classification.

Part 1 (G·001 method, applied to our 1m klines): group bars by prior-bar
return sign and measure the conditional next return — is reversion or
continuation alive per asset?

Part 2 (nagi777 three-state spike model on our collector quotes): detect
Polymarket mid spikes (|delta mid| >= 4c over <= 2 min) on BTC 5m markets and
classify by driver using the Binance 1m reference over the same window:
  A information-backed : |ext move| >= 10bp, same sign as PM move
  B book-driven        : |ext move| < 10bp
  C reference-lags     : |ext move| >= 10bp, opposite sign
Then measure the post-spike 5-minute PM reversion rate per class — the
actionable stat (do book-driven spikes mean-revert?).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from research.staleness.audit import DB, RAW, SYMBOLS, load_klines, build_symbol_arrays  # noqa: E402

OUT = REPO / "research" / "staleness" / "SIGNLAG_SPIKES.md"


def part1_signlag() -> list[str]:
    lines = ["## Part 1 — sign-lag conditional stats (1m klines, G·001 method)", ""]
    lines.append("| asset | n(up-then) | mean next ret after UP (bp) | n(down-then) | mean next ret after DOWN (bp) | reversion? |")
    lines.append("|---|---|---|---|---|---|")
    for asset in SYMBOLS:
        df = load_klines(SYMBOLS[asset])
        close = df["close"].to_numpy().astype(float)
        r = np.full(len(close), np.nan)
        r[1:] = np.log(close[1:] / close[:-1])
        up_then = np.where(np.roll(r, 1) > 0, r, np.nan)
        dn_then = np.where(np.roll(r, 1) < 0, r, np.nan)
        mu_up = np.nanmean(up_then[24:-1]) * 1e4
        mu_dn = np.nanmean(dn_then[24:-1]) * 1e4
        n_up, n_dn = int(np.isfinite(up_then).sum()), int(np.isfinite(dn_then).sum())
        rev = "reversion" if (mu_up < 0 and mu_dn > 0) else "continuation/mixed"
        lines.append(
            f"| {asset} | {n_up:,} | {mu_up:+.2f} | {n_dn:,} | {mu_dn:+.2f} | {rev} |"
        )
    lines.append("")
    return lines


def part2_spikes() -> list[str]:
    lines = ["## Part 2 — A/B/C spike classification (BTC 5m markets, collector quotes)", ""]
    conn_lines = None
    import sqlite3
    conn = sqlite3.connect(str(DB))
    m = pl.read_database(
        "SELECT market_id, asset, horizon_s, open_time_ms, close_time_ms FROM markets WHERE asset='BTC' AND horizon_s=300", conn
    )
    q = pl.read_database(
        "SELECT ts_ms, market_id, side, bid, ask, bid_qty, ask_qty FROM quotes WHERE market_id IN (SELECT market_id FROM markets WHERE asset='BTC' AND horizon_s=300)", conn
    )
    conn.close()
    m = m.with_columns(pl.col("market_id").str.slice(-1).alias("suffix")).with_columns(
        (pl.col("suffix") == "0").alias("is_up")
    )
    q = q.join(m, on="market_id")
    q = q.filter(
        (pl.col("is_up") & (pl.col("side") == "up"))
        | (~pl.col("is_up") & (pl.col("side") == "down"))
    )
    q = q.filter(pl.col("bid").is_not_null() & pl.col("ask").is_not_null())
    q = q.with_columns(((pl.col("bid") + pl.col("ask")) / 2).alias("mid"))

    # external reference: BTC 1m klines
    kdf = load_klines(SYMBOLS["BTC"])
    kts = kdf["ts_ms"].to_numpy().astype(np.int64)
    kc = kdf["close"].to_numpy().astype(float)

    def ext_move(t0, t1):
        i0, i1 = np.searchsorted(kts, t0), np.searchsorted(kts, t1)
        if i1 <= i0 or i1 >= len(kc):
            return None
        return math_ret(kc[i0], kc[min(i1, len(kc) - 1)])

    def math_ret(a, b):
        return np.log(b / a) if a > 0 else None

    counts = {"A": 0, "B": 0, "C": 0}
    rev_counts = {"A": [], "B": [], "C": []}
    spikes = 0
    mids = q.sort("ts_ms").group_by("market_id").agg(pl.col("mid"), pl.col("ts_ms"))
    for row in mids.to_dicts():
        mid_arr, ts_arr = row["mid"], row["ts_ms"]
        if len(mid_arr) < 8:
            continue
        mid_arr = np.asarray(mid_arr, float)
        ts_arr = np.asarray(ts_arr, np.int64)
        for i in range(2, len(mid_arr) - 2):
            if ts_arr[i] - ts_arr[i - 2] > 180_000:
                continue
            dm = mid_arr[i] - mid_arr[i - 2]
            if abs(dm) < 0.04:
                continue
            ext = ext_move(int(ts_arr[i - 2]), int(ts_arr[i]))
            if ext is None:
                continue
            spikes += 1
            same = (dm > 0) == (ext > 0)
            if abs(ext) >= 0.001 and same:
                cls = "A"
            elif abs(ext) < 0.001:
                cls = "B"
            else:
                cls = "C"
            counts[cls] += 1
            # post-spike 5-min reversion: does mid move back toward pre-spike?
            fut = (ts_arr >= ts_arr[i]) & (ts_arr <= ts_arr[i] + 300_000)
            if fut.sum() >= 1:
                post = mid_arr[fut][-1]
                rev = (post - mid_arr[i]) * (-np.sign(dm))
                rev_counts[cls].append(max(rev, 0.0) if False else rev)

    lines.append(f"spikes detected: {spikes} (|Δmid| ≥ 4c over ≤2 min)")
    lines.append("")
    lines.append("| class | n | mean post-5m reversion (c, + = revert) |")
    lines.append("|---|---|---|")
    for cls in "ABC":
        arr = rev_counts[cls]
        mrev = float(np.mean(arr)) * 100 if arr else float("nan")
        lines.append(f"| {cls} | {counts[cls]} | {mrev:+.2f} |")
    lines.append("")
    lines.append("Class A = PM move aligned with a >=10bp external move; B = external flat;")
    lines.append("C = external moved opposite. B reverting hardest supports fade-the-book")
    lines.append("logic; A not reverting confirms information-backed moves.")
    return lines


def main() -> None:
    lines = ["# Round 38: sign-lag conditionals + A/B/C spikes", ""]
    lines += part1_signlag()
    lines += part2_spikes()
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
