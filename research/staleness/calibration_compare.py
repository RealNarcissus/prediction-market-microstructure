"""Empirical calibration comparison: v1 running-TWAP fair vs venue-accurate v2
(see fair_v2.py for the math and the round-30 mechanism correction).

Configs (same quotes, same official resolutions, same strike proxy K = epoch
1m-open; strike-basis sensitivity needs Chainlink data and is NOT testable
here — recorded as an open limitation):

  v1_r24   running-TWAP settlement, sigma = r24  (audit.py current)
  v2_r24   final-60s-window settlement,  sigma = r24
  v2_r60   final-60s-window settlement,  sigma = r60 (60-min lookback)
  v2_ewma  final-60s-window settlement,  sigma = EWMA|ret|, 30-min halflife

Metrics per config: band table (mean fair vs realized win rate), Brier, ECE.
All quotes in collector.db postdate 2026-08-14 => single settlement regime
(60s TWAP), so no regime mixing. Output: CALIBRATION_COMPARE.md + parquet.
"""

from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from research.staleness.audit import (  # noqa: E402
    DB, RAW, REPO as AUDIT_REPO, SYMBOLS, build_symbol_arrays, load_klines,
)

FEE_RATE = 0.07
BANDS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def build_sigma_variants(df: pl.DataFrame):
    """Return dict of sigma arrays: r24 (as audit), r60, ewma(halflife 30)."""
    ts = df["ts_ms"].to_numpy().astype(np.int64)
    close = df["close"].to_numpy().astype(float)
    logret = np.full(len(ts), np.nan)
    logret[1:] = np.log(close[1:] / close[:-1])
    absr = np.abs(logret)

    def rolling(n: int, min_obs: int):
        out = np.full(len(ts), np.nan)
        csum = np.cumsum(np.nan_to_num(absr))
        nn = np.cumsum(np.isfinite(absr).astype(float))
        for i in range(len(ts)):
            lo = max(0, i - n)
            k = nn[i] - nn[lo]
            if k >= min_obs:
                out[i] = (csum[i] - csum[lo]) / max(k, 1)
        return out

    # EWMA of |ret| with halflife in bars
    halflife = 30.0
    lam = math.exp(math.log(0.5) / halflife)
    ewma = np.full(len(ts), np.nan)
    w = np.nan
    for i in range(len(ts)):
        a = absr[i]
        if np.isfinite(a):
            w = a if not np.isfinite(w) else lam * w + (1 - lam) * a
            ewma[i] = w
    k = math.sqrt(math.pi / 2.0)
    return {
        "r24": rolling(24, 12) * k,
        "r60": rolling(60, 30) * k,
        "ewma": ewma * k,
    }


def fair_v1(sigma_now, sum_obs, last_close, n_fut, N, K, count_obs, return_z=False):
    """audit.py running-TWAP fair, corrected to return-space z.

    audit.py itself divides a PRICE difference by a RETURN sd — the units bug
    that pinned every v1 fair at the 0/1 clip (found round 31). Here
    z = ln(e_twap/K) / sd_return.
    """
    if n_fut > 0:
        var_fut = (sigma_now ** 2) * ((n_fut + 1) * (2 * n_fut + 1)) / (6.0 * n_fut)
        var = ((n_fut / N) ** 2) * var_fut
    else:
        var = 1e-12
    e = (sum_obs + last_close * n_fut) / N
    z = math.log(max(e, 1e-9) / K) / math.sqrt(max(var, 1e-12))
    return z if return_z else norm_cdf(z)


def fair_v2(sigma_now, spot, K, d_min, w_min=1.0, realized_avg=None, return_z=False):
    """fair_v2 (log-space z): venue final-window settlement (60s => w = 1 min)."""
    if d_min >= w_min or realized_avg is None:
        sd = sigma_now * math.sqrt(w_min / 3.0)
        z = math.log(spot / K) / max(sd, 1e-12)
        return z if return_z else norm_cdf(z)
    mean_s = (w_min - d_min) * realized_avg + d_min * spot
    sd = sigma_now * math.sqrt(max(d_min ** 3 / (3.0 * w_min ** 2), 1e-12)) / w_min
    z = math.log(max(mean_s, 1e-9) / K) / max(sd, 1e-12)
    return z if return_z else norm_cdf(z)


def main() -> None:
    conn = sqlite3.connect(str(DB))
    markets = pl.read_database("SELECT market_id, title, asset, horizon_s, open_time_ms, close_time_ms FROM markets", conn)
    quotes = pl.read_database("SELECT ts_ms, market_id, side, bid, ask FROM quotes", conn)
    res = pl.read_database("SELECT market_id, outcome FROM resolutions", conn)
    conn.close()

    markets = markets.with_columns(
        pl.col("market_id").str.slice(-1).alias("suffix")
    ).with_columns((pl.col("suffix") == "0").alias("is_up_market"))
    res = res.with_columns(
        pl.col("market_id").str.slice(-1).alias("suffix"),
        (pl.col("outcome") == "up").alias("up_won"),
    ).with_columns(
        ((pl.col("suffix") == "0") == pl.col("up_won")).alias("token_won")
    ).select(["market_id", "token_won"])
    q = (
        quotes.join(markets, on="market_id", how="inner")
        .join(res, on="market_id", how="inner")
    )
    q = q.filter(
        (pl.col("is_up_market") & (pl.col("side") == "up"))
        | (~pl.col("is_up_market") & (pl.col("side") == "down"))
    )
    q = q.filter(
        pl.col("bid").is_not_null() & pl.col("ask").is_not_null()
        & (pl.col("bid") > 0.01) & (pl.col("ask") < 0.99)
        & (pl.col("bid") < pl.col("ask"))
    )
    print(f"yes-side quotes after filters: {q.height}")

    sig_variants = {}
    sym_meta = {}
    for a, s in SYMBOLS.items():
        df = load_klines(s)
        ts, close, opn, sigma_r24, prefix = build_symbol_arrays(df)
        variants = build_sigma_variants(df)
        sig_variants[a] = {"r24": sigma_r24, **variants}
        sym_meta[a] = (ts, close, opn, prefix)
    CONFIGS = ["v1_r24", "v2_r24", "v2_r60", "v2_ewma"]

    rows = []
    for r in q.to_dicts():
        asset = r["asset"]
        if asset not in sym_meta:
            continue
        ts, close, opn, prefix = sym_meta[asset]
        open_ms, close_ms = int(r["open_time_ms"]), int(r["close_time_ms"])
        hz_s, tsq = int(r["horizon_s"]), int(r["ts_ms"])
        if not (open_ms <= tsq < close_ms):
            continue
        N = hz_s // 60
        i_open = int(np.searchsorted(ts, open_ms))
        if i_open >= len(ts) or ts[i_open] != open_ms:
            j = int(np.searchsorted(ts, open_ms - 60_000))
            if j >= len(ts) or abs(int(ts[j]) - open_ms) > 60_000:
                continue
            i_open = j
        i_now = int(np.searchsorted(ts, tsq, side="right")) - 1
        if i_now < i_open:
            continue
        count_obs = i_now - i_open + 1
        n_fut = N - count_obs
        if n_fut < 0:
            continue
        K = float(opn[i_open])
        spot = float(close[i_now])
        sum_obs = float(prefix[i_now + 1] - prefix[i_open])
        d_min = n_fut  # minutes remaining (1m bars)
        in_final = d_min < 1
        realized_avg = float(opn[i_now]) if in_final else None
        sig = {k: (v[i_now] if np.isfinite(v[i_now]) else np.nan) for k, v in sig_variants[asset].items()}
        if any(not np.isfinite(v) for v in sig.values()):
            continue
        z_up = {
            "v1_r24": fair_v1(sig["r24"], sum_obs, spot, n_fut, N, K, count_obs, return_z=True),
            "v2_r24": fair_v2(sig["r24"], spot, K, d_min, 1.0, realized_avg, return_z=True),
            "v2_r60": fair_v2(sig["r60"], spot, K, d_min, 1.0, realized_avg, return_z=True),
            "v2_ewma": fair_v2(sig["ewma"], spot, K, d_min, 1.0, realized_avg, return_z=True),
        }
        for cfg, zu in z_up.items():
            z_yes = zu if r["is_up_market"] else -zu
            rows.append({
                "market_id": r["market_id"], "asset": asset, "hz": f"{hz_s}s",
                "won": int(r["token_won"]), "ask": float(r["ask"]),
                "z": z_yes, "cfg": cfg,
                "in_final": in_final, "ts_ms": tsq,
            })

    df = pl.DataFrame(rows)
    df.write_parquet(str(REPO / "research" / "staleness" / "calibration_compare.parquet"))
    lines = ["# Fair calibration comparison: v1 vs v2 (rounds 31-32)", "",
             f"Quotes scored: {df.height // len(CONFIGS):,} x {len(CONFIGS)} configs "
             "(all post-2026-08-14 => 60s-TWAP settlement regime). "
             "z = log-space fair z-score; lambda = sigma multiplier fit by Brier.", ""]
    for cfg in CONFIGS:
        d = df.filter(pl.col("cfg") == cfg)
        z = d["z"].to_numpy()
        won = d["won"].to_numpy().astype(float)
        # Brier-minimizing sigma multiplier: fair = Phi(z / lambda)
        grid = np.arange(0.5, 8.001, 0.02)

        def sigmoid(x):
            out = np.empty_like(x)
            pos = x >= 0
            out[pos] = 1 / (1 + np.exp(-x[pos]))
            ex = np.exp(x[~pos])
            out[~pos] = ex / (1 + ex)
            return out

        briers = [float((((sigmoid(z / l)) - won) ** 2).mean()) for l in grid]
        i = int(np.argmin(briers))
        lam = float(grid[i])
        fair = 1 / (1 + np.exp(-(z / lam)))
        brier = float(((fair - won) ** 2).mean())
        ece = 0.0
        band_rows = []
        df = df.with_columns(pl.when(pl.col("cfg") == cfg)
                             .then(pl.col("z") / lam)
                             .otherwise(pl.col("z")).alias("_z_cal")) if False else df
        zc = d["z"].to_numpy() / lam
        dcal = d.with_columns(pl.Series("fair_cal", sigmoid(zc)))
        for lo, hi in zip(BANDS[:-1], BANDS[1:]):
            b = dcal.filter((pl.col("fair_cal") >= lo) & (pl.col("fair_cal") < hi))
            if b.height < 30:
                continue
            mf, wr, n = float(b["fair_cal"].mean()), float(b["won"].mean()), b.height
            ece += (n / d.height) * abs(wr - mf)
            band_rows.append((lo, hi, n, mf, wr, wr - mf))
        lines.append(f"## {cfg}  —  lambda* {lam:.2f}  Brier {brier:.4f}  ECE {ece:.4f}  (n={d.height:,})")
        lines.append("")
        lines.append("| calibrated fair band | n | mean fair | realized | error |")
        lines.append("|---|---|---|---|---|")
        for lo, hi, n, mf, wr, err in band_rows:
            lines.append(f"| [{lo:.1f},{hi:.1f}) | {n:,} | {mf:.3f} | {wr:.3f} | {err:+.3f} |")
        lines.append("")
    out = REPO / "research" / "staleness" / "CALIBRATION_COMPARE.md"
    out.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
