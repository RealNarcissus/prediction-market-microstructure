"""Adverse move at fill — execution-quality measurement on our own ledger.

Template: LinusWeigand/updown-MM round-207 (live-measured adverse selection:
survival curves of adverse moves at the quote, bid n=2,348 / ask n=3,335,
p90=2.0c p99=4.1c, quoted half-spread kept above them).

Our analog (taker fills, not quotes): for every settled gate='v2' trade in
data/paper_wallet.db, take the yes-side token's best BID at +30s / +60s /
+120s after entry from data/collector.db, and measure

    markout_k = bid(entry_ts + k) - ask(entry)      [$ per share]

Negative = we could exit for less than we paid = the market moved against us
after our fill (adverse selection + our price impact). The trade's PnL is the
settled outcome; the markout isolates the execution-quality slice.

Outputs: research/staleness/ADV_MOVE_FILLS.md (n, mean/median per horizon,
adverse fraction, survival percentiles) — research-only, touches nothing live.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "research" / "staleness" / "ADV_MOVE_FILLS.md"

HORIZONS = (30, 60, 120)


def main() -> None:
    wall = sqlite3.connect(str(REPO / "data" / "paper_wallet.db"))
    wall.row_factory = sqlite3.Row
    col = sqlite3.connect(str(REPO / "data" / "collector.db"))
    col.row_factory = sqlite3.Row

    trades = wall.execute(
        """SELECT entry_ts_ms, market_id, is_up_market, ask
           FROM trades WHERE gate='v2' AND status='settled'
           ORDER BY entry_ts_ms"""
    ).fetchall()

    rows = []
    for t in trades:
        side = "up" if t["market_id"].endswith("-0") else "down"
        entry_ask = float(t["ask"])
        markouts = {}
        for k in HORIZONS:
            target = t["entry_ts_ms"] + k * 1000
            r = col.execute(
                """SELECT bid, ask FROM quotes
                   WHERE market_id=? AND side=? AND bid IS NOT NULL AND ts_ms>=?
                   ORDER BY ts_ms LIMIT 1""",
                (t["market_id"], side, target),
            ).fetchone()
            if r is not None:
                markouts[k] = float(r["bid"]) - entry_ask
        if markouts:
            rows.append({"markouts": markouts, "ask": entry_ask})

    lines = [
        "# Adverse move at fill — v2 settled trades vs collector tape",
        "",
        f"trades with at least one markout horizon: {len(rows)} "
        f"(of {len(trades)} settled v2 trades)",
        "",
        "markout_k = best_bid(entry+k) - ask(entry)  [$ per share]; "
        "negative = market moved against us after our fill",
        "",
    ]
    for k in HORIZONS:
        vals = np.array([r["markouts"][k] for r in rows if k in r["markouts"]])
        if len(vals) < 10:
            lines.append(f"+{k}s: n={len(vals)} (insufficient)")
            continue
        adv = vals < 0
        lines.append(
            f"+{k}s: n={len(vals):,}  mean {vals.mean()*100:+.2f}c  "
            f"median {np.median(vals)*100:+.2f}c  "
            f"adverse frac {adv.mean():.3f}  "
            f"p10 {np.percentile(vals,10)*100:+.2f}c  "
            f"p90 {np.percentile(vals,90)*100:+.2f}c"
        )
    # survival curve at +60s (closest to LinusWeigand panel (a))
    v60 = np.array([abs(r["markouts"][60]) for r in rows if 60 in r["markouts"]
                    and r["markouts"][60] < 0])
    if len(v60) >= 20:
        lines.append("")
        lines.append("adverse-move survival at +60s (magnitude of adverse moves):")
        lines.append(f"  n={len(v60):,}  p50 {np.percentile(v60,50)*100:.2f}c  "
                     f"p90 {np.percentile(v60,90)*100:.2f}c  "
                     f"p99 {np.percentile(v60,99)*100:.2f}c")
    lines += [
        "",
        "Reading: persistent negative means at +30s/+60s = we systematically",
        "pay the spread plus adverse drift (informed flow ahead of us); the",
        "gap between -mean-markout and the 0.07*p*(1-p) fee is the part of",
        "the backtest-to-live shortfall this measurement explains.",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
