"""Round 111: refreeze calibration_v2 on the FIXED z scale.

The paper daemon (paper_gate.py) was updated to the round-107 fixed z
(sd = sigma*sqrt(d-2/3)), but calibration_v2.npz holds lambda=1.95 +
isotonic fit on the ORIGINAL z scale (lambda* 0.60-0.65 on fixed z).
Running fixed z through the old mapping = miscalibrated gate. This script
refits lambda + isotonic on fixed z over the TRAIN span only and refreezes
calibration_v2.npz, with the same degeneracy guard. The daemon's test
window restarts at this refreeze (disclosed in PAPER_GATE_LIVE.md).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from research.staleness.audit import (  # noqa: E402
    DB, SYMBOLS, build_symbol_arrays, load_klines,
)
from research.staleness.calibration_compare import build_sigma_variants  # noqa: E402
from research.staleness.paper_gate import CALIBRATION_V2  # noqa: E402
from research.staleness.retest_logspace import SPLIT_MS, fit_lambda, sigmoid  # noqa: E402
from research.staleness.round107_fairfix import fair_v2_fixed  # noqa: E402
from research.staleness.calibration_compare import fair_v2  # noqa: E402


def main() -> None:
    conn = sqlite3.connect(str(DB))
    markets = pl.read_database(
        "SELECT market_id, asset, horizon_s, open_time_ms, close_time_ms FROM markets", conn)
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
    q = quotes.join(markets, on="market_id", how="inner").join(res, on="market_id", how="inner")
    q = q.filter(
        (pl.col("is_up_market") & (pl.col("side") == "up"))
        | (~pl.col("is_up_market") & (pl.col("side") == "down"))
    ).filter(
        pl.col("bid").is_not_null() & pl.col("ask").is_not_null()
        & (pl.col("bid") > 0.01) & (pl.col("ask") < 0.99)
        & (pl.col("bid") < pl.col("ask"))
    )

    sig_variants, sym_meta = {}, {}
    for a, s in SYMBOLS.items():
        df = load_klines(s)
        ts, close, opn, sigma_r24, prefix = build_symbol_arrays(df)
        sig_variants[a] = build_sigma_variants(df)["ewma"]
        sym_meta[a] = (ts, close, opn)

    z_list, won_list = [], []
    for r in q.to_dicts():
        asset = r["asset"]
        if asset not in sym_meta:
            continue
        ts, close, opn = sym_meta[asset]
        open_ms, close_ms = int(r["open_time_ms"]), int(r["close_time_ms"])
        hz_s, tsq = int(r["horizon_s"]), int(r["ts_ms"])
        if not (open_ms <= tsq < close_ms) or tsq >= SPLIT_MS:
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
        n_fut = N - (i_now - i_open + 1)
        if n_fut < 0:
            continue
        K, spot = float(opn[i_open]), float(close[i_now])
        d_min = n_fut
        realized_avg = float(opn[i_now]) if d_min < 1 else None
        ew = sig_variants[asset][i_now]
        if not np.isfinite(ew):
            continue
        z = fair_v2_fixed(ew, spot, K, d_min, 1.0, realized_avg)
        z_list.append(z if r["is_up_market"] else -z)
        won_list.append(int(r["token_won"]))

    z_tr = np.array(z_list)
    won_tr = np.array(won_list, dtype=float)
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
    print(f"train n={len(z_tr):,} fixed-z lambda={lam:.2f} distinct={distinct} tercile_gap={gap:.3f}")
    if distinct < 10 or gap <= 0.05:
        print("FATAL: fixed-z calibration degenerate — refusing to freeze", file=sys.stderr)
        sys.exit(1)
    np.savez(str(CALIBRATION_V2), x=iso.X_thresholds_, y=iso.y_thresholds_,
             lam=lam, n_fit=len(z_tr), split_ms=SPLIT_MS)
    print(f"calibration_v2 refrozen on FIXED z: lambda={lam:.2f}")


if __name__ == "__main__":
    main()
