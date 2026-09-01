"""Venue-accurate fair value for Polymarket crypto Up/Down binaries (v2).

Settlement regimes (verified from docs/changelog; see
research/external/EXTERNAL_CATALOG.md sections 1a and 1d):

  snapshot  launch -> 2026-08-07   settle = price snapshot at window close
  twap30    2026-08-07 -> 08-14    settle = 30s average (5m); 60s (15m/4h)
  twap60    2026-08-14 -> now      settle = 60s average (5m and 15m)

Strike regimes:
  pre-Aug-7:  strike = snapshot price at window open (our 1m-open proxy)
  post-Aug-7: strike = average of the first w seconds at window open

Math (per-minute variance sigma^2, e.g. from the r24 estimate):
  d = minutes remaining to close, w = averaging window in minutes
  (w -> 0 for the snapshot regime).

  snapshot:      S = P_T                              Var(S) = sigma^2 * d
  twap, d >= w:  S = mean of path over final w minutes (all future)
                     Var(S) = sigma^2 * w / 3
  twap, d <  w:  S = ((w-d)*A + d*P_t) / w   with A = realized mean of the
                     last (w-d) minutes; future part adds
                     Var(S) = sigma^2 * d^3 / (3 w^2)
  fair_up = Phi( (E[S] - K) / sqrt(Var(S)) ),  E[S] = current spot (driftless).

EMPIRICAL CORRECTION (round 30, supersedes the earlier catalog note):
  The v1 running-TWAP model (audit.py) has MORE mid-window variance than the
  venue's final-window settlement (5m window at open+60s: sd_v1 = 1.21 sigma
  vs sd_v2 = 0.577 sigma), so v2 fair values are MORE extreme, not less.
  The v1 overconfidence measured in CALIBRATED_RETEST therefore cannot be
  explained by the averaging-window mismatch; the surviving candidate causes
  are sigma understatement (r24's 24-minute lookback), strike basis (Binance
  1m open vs Chainlink TWAP), and adverse selection in observed quotes.
  Isotonic calibration remains the final layer either way.
"""

from __future__ import annotations

import math

MINUTES_PER_DAY = 1440.0


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def variance_final_window(sigma_1m: float, w_minutes: float) -> float:
    """Var of the time-average of the path over the final w minutes (all future)."""
    if w_minutes <= 0:
        raise ValueError("w_minutes must be positive")
    return (sigma_1m ** 2) * w_minutes / 3.0


def variance_within_window(sigma_1m: float, d_minutes: float, w_minutes: float) -> float:
    """Var of the final-w average when only the last d < w minutes are future."""
    if not (0 <= d_minutes <= w_minutes):
        raise ValueError("require 0 <= d_minutes <= w_minutes")
    return (sigma_1m ** 2) * (d_minutes ** 3) / (3.0 * (w_minutes ** 2))


def variance_running_twap_v1(sigma_1m: float, n_fut: float, n_total: float) -> float:
    """Var of the v1 running-TWAP settlement (audit.py), for comparison."""
    if n_fut <= 0 or n_total <= 0 or n_fut > n_total:
        raise ValueError("require 0 < n_fut <= n_total")
    var_fut = (sigma_1m ** 2) * ((n_fut + 1) * (2 * n_fut + 1)) / (6.0 * n_fut)
    return ((n_fut / n_total) ** 2) * var_fut


def fair_up_v2(
    spot: float,
    strike: float,
    sigma_1m: float,
    d_minutes: float,
    w_minutes: float,
    realized_avg: float | None = None,
) -> float:
    """P(settlement > strike) under the venue's actual settlement process.

    w_minutes = 0 selects the snapshot (European digital) regime.
    realized_avg is the mean of the last (w - d) minutes when d < w; when it
    is None the future-only approximation Var = sigma^2 * w / 3 is used
    (documented approximation; exact form requires the realized path).
    """
    if sigma_1m <= 0 or d_minutes < 0:
        raise ValueError("require sigma_1m > 0 and d_minutes >= 0")

    if w_minutes <= 0:  # snapshot regime: European digital on the close
        sd = sigma_1m * math.sqrt(max(d_minutes, 1e-9))
        return min(max(norm_cdf((spot - strike) / sd), 0.0), 1.0)

    if d_minutes >= w_minutes:
        sd = math.sqrt(variance_final_window(sigma_1m, w_minutes))
        return min(max(norm_cdf((spot - strike) / sd), 0.0), 1.0)

    # inside the final averaging window
    if realized_avg is None:
        sd = math.sqrt(variance_final_window(sigma_1m, w_minutes))
        return min(max(norm_cdf((spot - strike) / sd), 0.0), 1.0)
    mean_s = ((w_minutes - d_minutes) * realized_avg + d_minutes * spot) / w_minutes
    sd = math.sqrt(variance_within_window(sigma_1m, d_minutes, w_minutes))
    return min(max(norm_cdf((mean_s - strike) / sd), 0.0), 1.0)
