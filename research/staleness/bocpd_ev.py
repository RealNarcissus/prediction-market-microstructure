"""Round 235: conditional gate EV inside vs outside BOCPD flow-regime breaks.

First cut of the round-208 discipline applied to the flow-bias detector:
run BOCPD at the data-driven hazard (1/25) over the accumulated snapshot,
mark each settled v2 trade by whether a flow-regime break occurred in the
25 minutes BEFORE its entry, and compare realized per-trade EV + win rate
across cohorts.

HONEST CAVEAT (recorded in output): the detector parameters were tuned on
the same history the trades span — this is an EXPLORATORY in-sample cut,
not prospective validation. Prospective scoring = same computation on
trades that settle AFTER the detector was frozen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
OUT = REPO / "research" / "staleness" / "BOCPD_EV.md"

HAZARD = 1.0 / 25.0          # data-driven scale from round-234 re-fit
POST_BREAK_WINDOW_MS = 25 * 60 * 1000


def main() -> None:
    import research.staleness.bocpd as B

    snap = REPO / "data" / "flowbias_BTCUSDT.parquet"
    df = pl.read_parquet(str(snap))
    x = df["bias"].to_numpy()
    ts = df["ts_ms"].to_numpy()
    lo, hi = np.quantile(x, [0.001, 0.999])
    x = np.clip(x, lo, hi)

    B.HAZARD = HAZARD
    R0, _ = B.bocpd_gaussian(x)
    break_ts = ts[R0 > 0.5]

    wall = sqlite3_connect()
    trades = wall.execute(
        """SELECT entry_ts_ms, pnl_cents, won, status
           FROM trades WHERE gate='v2' AND status='settled'
             AND entry_ts_ms >= ? ORDER BY entry_ts_ms""",
        (int(ts[0]),),
    ).fetchall()

    post, stable = [], []
    for t in trades:
        e = t["entry_ts_ms"]
        # any break in [e - window, e]?
        i = np.searchsorted(break_ts, e)
        j = np.searchsorted(break_ts, e - POST_BREAK_WINDOW_MS)
        n_breaks = i - j
        (post if n_breaks > 0 else stable).append(
            (t["pnl_cents"], t["won"]))

    def stats(coh):
        pnl = np.array([c[0] for c in coh], dtype=float)
        won = np.array([c[1] for c in coh])
        return len(pnl), pnl.mean(), won.mean()

    n_p, ev_p, wr_p = stats(post)
    n_s, ev_s, wr_s = stats(stable)

    lines = [
        "# Conditional gate EV around BOCPD flow-regime breaks",
        "",
        f"detector: hazard {HAZARD:.3f} (data-driven, round-234); "
        f"snapshot {len(x):,} min; breaks in window: {len(break_ts):,}",
        f"trades scored: {n_p + n_s} settled v2 in snapshot span",
        f"post-break cohort (break within 25 min before entry): n={n_p}  "
        f"EV {ev_p:+.2f}c  win {wr_p:.3f}",
        f"stable-flow cohort (no break in window): n={n_s}  "
        f"EV {ev_s:+.2f}c  win {wr_s:.3f}",
        f"EV delta (post-break minus stable): {ev_p - ev_s:+.2f}c",
        "",
        "## HONEST CAVEATS",
        "1. EXPLORATORY IN-SAMPLE: detector params were tuned on this same",
        "   history. Not prospective. Prospective = freeze the detector,",
        "   score only trades that settle afterwards.",
        "2. Flow bias is BTC-only; trades span BTC/ETH/SOL (cross-asset",
        "   leakage in both cohorts).",
        "3. Cohort split is by entry timing only — no fee/latency change.",
        "",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"wrote {OUT}")


def sqlite3_connect():
    import sqlite3

    conn = sqlite3.connect(str(REPO / "data" / "paper_wallet.db"))
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == "__main__":
    main()
