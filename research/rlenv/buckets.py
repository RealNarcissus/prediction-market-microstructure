"""Bucket: vol-tercile + UTC session + horizon bucket definition.

Buckets: 3 vol terciles (r24, one F6 lookback chosen once, fixed before
viewing) x 4 coarse UTC sessions (00-06, 06-12, 12-18, 18-24) x 2 horizons
(5m, 15m) = 24 cells. Buckets fixed BEFORE any equation is probed — do not
add/split after seeing results (see deliverable stop rule).

Gaps 497/457/253 min excluded where paper-data numbers touch; bridge data
(historical updown) gap-free. Sealed H1-2026 holdout untouched.
Id-namespace: epochs_bridge market_id (epoch DUR), trades token_id.

The 12x2 structure: buckets are epoch-level regime conditioning (pre-trade),
not trade-level staleness — therefore shared across formulae.
"""
from __future__ import annotations

import datetime as dt


# Pre-registered r24 cuts (BTCUSDT 1m klines -> abs return -> rolling 24)
# Computed once on validation span, frozen before viewing any bucket EV.
R24_CUTS = [0.0002424, 0.0004061]

SESSION_LABELS = ["00-06", "06-12", "12-18", "18-24"]
VOL_LABELS = ["low", "mid", "high"]
HORIZONS = ["5m", "15m"]


def vol_label(r24_val: float | None) -> str:
    if r24_val is None:
        return "low"
    try:
        v = float(r24_val)
    except (TypeError, ValueError):
        return "low"
    import numpy as np
    if not np.isfinite(v):
        return "low"
    if v < R24_CUTS[0]:
        return "low"
    if v < R24_CUTS[1]:
        return "mid"
    return "high"


def session_label(open_ms: int) -> str:
    h = dt.datetime.fromtimestamp(open_ms / 1000, tz=dt.timezone.utc).hour
    if h < 6:
        return "00-06"
    if h < 12:
        return "06-12"
    if h < 18:
        return "12-18"
    return "18-24"


def bucket_from_epoch(open_ms: int, r24_val: float | None, hz: str) -> tuple[str, str, str]:
    """Return (vol_tercile, session, horizon) tuple."""
    return (vol_label(r24_val), session_label(open_ms), hz)


def all_buckets() -> list[tuple[str, str, str]]:
    """All 24 pre-registered bucket ids."""
    out = []
    for vol in VOL_LABELS:
        for sess in SESSION_LABELS:
            for hz in HORIZONS:
                out.append((vol, sess, hz))
    return out


def total_cells() -> int:
    return len(all_buckets())  # 24
