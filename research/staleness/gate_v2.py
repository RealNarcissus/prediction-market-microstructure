"""Shared integrated gate (gate_v2): the venue-accurate fair + frozen calibration.

Single source of truth for BOTH paper daemons (live_wallet.py and
paper_gate.py). Extracted so the two can never diverge again: previously
live_wallet carried its own v1 fair + collapsed calibration while
paper_gate carried a fixed v2 fair + refrozen calibration, and the live
$5 wallet traded the broken one for 130 trades.

Contents:
  EwmaKlineCache  rolling 1m-klines window with EWMA(30m halflife) sigma
                  (the v2_ewma config the round-32/33 scores were built on).
  fair_yes_v2     venue-accurate z for the epoch (final-60s TWAP settlement,
                  log space, round-107 mid-window variance fix:
                  Var(S) = sigma^2*(d-w) + sigma^2*w/3 for d >= w).
  load_calibration_v2 / CALIBRATION_V2
                  train-only lambda + isotonic mapping, frozen in
                  calibration_v2.npz (lambda 0.65, n_fit 37,594, 62 distinct
                  x values). Refits ONLY via round111_recalibrate.py at
                  declared checkpoints, never intra-run.
  build_calibration_v2
                  train-only (lambda, isotonic) fit with degeneracy guard
                  (distinct >= 10, tercile win-rate gap > 0.05); refuses to
                  freeze a collapsed mapping.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from research.staleness.retest_logspace import (  # noqa: E402
    PARQUET as COMPARE_PARQUET,
    SPLIT_MS,
    fit_lambda,
    sigmoid,
)

RAW = REPO / "data" / "raw"
CALIBRATION_V2 = REPO / "research" / "staleness" / "calibration_v2.npz"

EWMA_HALFLIFE = 30.0
K_PI2 = math.sqrt(math.pi / 2.0)


def build_calibration_v2() -> None:
    """Fit lambda + isotonic on TRAIN span only; freeze to calibration_v2.npz.

    Refuses to write when the mapping is degenerate (same spirit as the
    pre-launch gate: distinct>=10, tercile win-rate gap>0.05).
    """
    import polars as pl
    from sklearn.isotonic import IsotonicRegression

    df = pl.read_parquet(str(COMPARE_PARQUET)).filter(
        pl.col("cfg") == "v2_ewma"
    ).sort("ts_ms")
    tr = df.filter(pl.col("ts_ms") < SPLIT_MS)
    z_tr = tr["z"].to_numpy()
    won_tr = tr["won"].to_numpy().astype(float)
    lam = fit_lambda(z_tr, won_tr)
    iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(z_tr / lam), won_tr)
    prob_tr = iso.predict(sigmoid(z_tr / lam))

    distinct = len(np.unique(np.round(prob_tr, 4)))
    edges = np.unique(np.quantile(prob_tr, [0.0, 1 / 3, 2 / 3, 1.0]))
    wrs = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (prob_tr >= lo) & (prob_tr <= hi) if hi == edges[-1] else (prob_tr >= lo) & (prob_tr < hi)
        wrs.append(float(won_tr[m].mean()) if m.sum() >= 100 else float("nan"))
    valid = [w for w in wrs if np.isfinite(w)]
    gap = (max(valid) - min(valid)) if len(valid) >= 2 else 0.0
    print(f"train n={tr.height:,} lambda={lam:.2f} distinct={distinct} tercile_gap={gap:.3f}")
    if distinct < 10 or gap <= 0.05:
        print("FATAL: v2 calibration degenerate — refusing to freeze", file=sys.stderr)
        sys.exit(1)
    np.savez(str(CALIBRATION_V2), x=iso.X_thresholds_, y=iso.y_thresholds_,
             lam=lam, n_fit=len(tr), split_ms=SPLIT_MS)
    print(f"calibration_v2 frozen: {len(tr)} train quotes, lambda={lam:.2f}")


def load_calibration_v2():
    if not CALIBRATION_V2.exists():
        print(f"FATAL: {CALIBRATION_V2} missing — run with --build-calibration first",
              file=sys.stderr)
        sys.exit(2)
    z = np.load(str(CALIBRATION_V2))
    x, y, lam = z["x"], z["y"], float(z["lam"])

    def predict(zscore: float, is_up_market: bool) -> float:
        zy = zscore if is_up_market else -zscore
        return float(np.interp(sigmoid(zy / lam), x, y))

    return predict


class EwmaKlineCache:
    """Rolling kline window per symbol with EWMA(30m halflife) sigma.

    3h window = 180 bars vs 30-bar halflife, so seed transient is ~1.5%
    weight — noted, accepted.
    """

    WINDOW_MS = 3 * 3600 * 1000
    RELOAD_S = 30.0

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._last_load: dict[str, float] = {}

    def refresh(self, symbol: str, now_ms: int | None = None) -> None:
        now = time.time()
        if symbol in self._data and now - self._last_load.get(symbol, 0) < self.RELOAD_S:
            return
        self._last_load[symbol] = now
        import polars as pl

        d = RAW / symbol / "kline_1m"
        files = sorted(d.glob("*.parquet"))[-4:] if d.exists() else []
        if not files:
            return
        try:
            df = pl.concat([pl.read_parquet(str(f)).select(["ts_ms", "open", "close"])
                            for f in files])
        except Exception:
            return
        df = df.sort("ts_ms").unique(subset=["ts_ms"], keep="last", maintain_order=True)
        ts = df["ts_ms"].to_numpy().astype(np.int64)
        cutoff = (now_ms if now_ms is not None else int(now * 1000)) - self.WINDOW_MS
        m = ts >= cutoff
        ts = ts[m]
        opn = df["open"].to_numpy().astype(float)[m]
        close = df["close"].to_numpy().astype(float)[m]
        n = len(ts)
        ewma = np.full(n, np.nan)
        if n >= 2:
            lam = math.exp(math.log(0.5) / EWMA_HALFLIFE)
            w = np.nan
            for i in range(1, n):
                a = abs(math.log(close[i] / close[i - 1])) if close[i - 1] > 0 else np.nan
                if np.isfinite(a):
                    w = a if not np.isfinite(w) else lam * w + (1 - lam) * a
                    ewma[i] = w * K_PI2
        self._data[symbol] = {"ts": ts, "open": opn, "close": close, "ewma": ewma}

    def get(self, symbol: str) -> dict | None:
        d = self._data.get(symbol)
        if d is None or len(d.get("ts", [])) < 60:
            return None
        return d


def fair_yes_v2(cache_data: dict, open_ms: int, hz_s: int, ts_ms: int) -> float | None:
    """Venue-accurate z for the epoch (final-60s TWAP settlement, log space).

    Round-107 fix: from mid-window the level must still travel to the final
    window — Var(S) = sigma^2*(d-w) + sigma^2*w/3 for d >= w, NOT just the
    conditional sigma^2*w/3. Side is applied by the caller via the
    is_up_market flag of load_calibration_v2's predict.
    """
    ts, opn, close, ewma = (cache_data["ts"], cache_data["open"],
                            cache_data["close"], cache_data["ewma"])
    N = hz_s // 60
    i_open = int(np.searchsorted(ts, open_ms))
    if i_open >= len(ts) or int(ts[i_open]) != open_ms:
        j = int(np.searchsorted(ts, open_ms - 60_000))
        if j >= len(ts) or abs(int(ts[j]) - open_ms) > 60_000:
            return None
        i_open = j
    i_now = int(np.searchsorted(ts, ts_ms, side="right")) - 1
    if i_now < i_open:
        return None
    n_fut = N - (i_now - i_open + 1)
    if n_fut < 0:
        return None
    K = float(opn[i_open])
    spot = float(close[i_now])
    sig = float(ewma[i_now]) if np.isfinite(ewma[i_now]) else np.nan
    if not np.isfinite(sig) or sig <= 0 or K <= 0 or spot <= 0:
        return None
    d_min = float(n_fut)
    if d_min >= 1.0:
        sd = sig * math.sqrt(max(d_min - 2.0 / 3.0, 1e-12))
        z = math.log(spot / K) / max(sd, 1e-12)
    else:
        if n_fut <= 0:
            return None
        realized_avg = float(opn[i_now])
        mean_s = ((1.0 - d_min) * realized_avg + d_min * spot)
        sd = sig * math.sqrt(max(d_min ** 3 / 3.0, 1e-12))
        z = math.log(max(mean_s, 1e-9) / K) / max(sd, 1e-12)
    return z
