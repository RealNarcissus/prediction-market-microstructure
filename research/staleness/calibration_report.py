"""Pre-launch calibration report — mandatory gate before any wallet (re)start.

Lesson (2026-09-03): the live $5 wallet ran 91 trades on a collapsed
calibration (fair_cal pinned at 0.737 — a step function from isotonic fit on
buggy v1 fairs). A 30-second validation would have caught it pre-launch:
non-degenerate fair_cal distribution, sane gate rate, non-trivial band table.

Usage:
    .venv/bin/python research/staleness/calibration_report.py [--check-only]

Exit 0 = calibration usable for trading. Exit 1 = COLLAPSED, do not launch.
Also writes research/staleness/CALIBRATION_REPORT.md.

Checks (all must pass):
  1. Non-degenerate: fair_cal must take >= 10 distinct values on the
     validation sample (catches constant/step-function collapse).
  2. Gate rate: fraction of quotes passing (fair_cal - ask > fee) must be
     in [0.01, 0.60] — outside means the gate is dead or indiscriminate.
  3. Spread: fair_cal range (p99 - p01) must exceed 0.20 — a collapsed
     calibration compresses everything near one value.
  4. Band sanity: split validation sample into fair_cal terciles; each
     tercile's realized win rate must differ from the others (max pairwise
     gap > 0.05) — a flat win-rate profile means the mapping carries no
     information.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from research.staleness.live_wallet import (  # noqa: E402
    CALIBRATION, LIVE_START_MS, FEE_RATE, load_calibration,
)

OUT = REPO / "research" / "staleness" / "CALIBRATION_REPORT.md"
SRC = REPO / "research" / "staleness" / "scored_quotes.parquet"


def main() -> int:
    print("=== Pre-launch calibration report ===")
    calib = load_calibration()
    df = pl.read_parquet(str(SRC)).filter(pl.col("ts_ms") < LIVE_START_MS)
    print(f"validation sample: {len(df)} pre-launch quotes")
    fair = df["fair"].to_numpy()
    # NOTE: scored_quotes.parquet holds v1 fairs — this reproduces the exact
    # input the live calibration was built on. A collapsed input here means
    # the frozen mapping cannot discriminate, regardless of later fair_v2 work.
    fair_cal = np.array([calib(f) for f in fair])
    won = df["won"].to_numpy().astype(float)
    ask = df["ask"].to_numpy()

    lines = ["# Pre-Launch Calibration Report", ""]
    ok = True

    # 1. degeneracy
    distinct = len(np.unique(np.round(fair_cal, 4)))
    c1 = distinct >= 10
    ok &= c1
    lines.append(f"1. distinct fair_cal values: {distinct} — {'PASS' if c1 else 'FAIL (collapsed: <10 distinct values)'}")

    # 2. gate rate
    fee = FEE_RATE * ask * (1 - ask)
    gate = (fair_cal - ask) > fee
    rate = float(gate.mean())
    c2 = 0.01 <= rate <= 0.60
    ok &= c2
    lines.append(f"2. gate rate: {rate:.3f} — {'PASS' if c2 else 'FAIL (outside [0.01, 0.60])'}")

    # 3. spread
    spread = float(np.percentile(fair_cal, 99) - np.percentile(fair_cal, 1))
    c3 = spread > 0.20
    ok &= c3
    lines.append(f"3. fair_cal p99-p01 spread: {spread:.3f} — {'PASS' if c3 else 'FAIL (compressed: <=0.20)'}")

    # 4. band sanity — use UNIQUE tercile edges so a collapsed mapping
    # (few distinct values) yields degenerate bins rather than NaN gaps
    edges = np.unique(np.quantile(fair_cal, [0.0, 1 / 3, 2 / 3, 1.0]))
    wrs = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (fair_cal >= lo) & (fair_cal <= hi) if hi == edges[-1] else (fair_cal >= lo) & (fair_cal < hi)
        wrs.append(float(won[m].mean()) if m.sum() >= 100 else float("nan"))
    valid = [w for w in wrs if np.isfinite(w)]
    gap = (max(valid) - min(valid)) if len(valid) >= 2 else 0.0
    c4 = gap > 0.05
    ok &= c4
    lines.append(f"4. tercile win rates: {[f'{w:.3f}' for w in wrs]} (max gap {gap:.3f}) — {'PASS' if c4 else 'FAIL (flat profile: gap <= 0.05)'}")

    lines.append("")
    lines.append(f"**VERDICT: {'USABLE — may launch' if ok else 'COLLAPSED — do NOT launch or restart without rebuilding'}**")
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[1:]))
    print(f"\nwrote {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
