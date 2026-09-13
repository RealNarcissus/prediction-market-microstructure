"""Round 107: score the fair_v2 mid-window variance fix.

Hypothesis (from Loimola code-read): fair_v2's d>=w branch uses
sd = sigma*sqrt(w/3) — the variance of the final-window average
CONDITIONAL on knowing the spot at the window start. From mid-window,
the level still has to travel there: correct Var(S) = sigma^2*(d-w)
+ sigma^2*w/3, i.e. sd = sigma*sqrt(d - 2w/3) for w=1.

Reuses calibration_compare machinery; scores v2_ewma original vs fixed z:
lambda*, Brier, ECE, band table, plus the retest_logspace gated protocol
(train-only lambda+iso, gated EV with daily-block CI) on both.
"""

from __future__ import annotations

import math
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
from research.staleness.calibration_compare import (  # noqa: E402
    build_sigma_variants, fair_v2,
)
from research.staleness.retest_logspace import (  # noqa: E402
    FEE_RATE, SPLIT_MS, daily_boot_ci, fit_lambda, sigmoid,
)

OUT = REPO / "research" / "staleness" / "ROUND107_FAIRFIX.md"
BANDS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]


def fair_v2_fixed(sigma_now, spot, K, d_min, w_min=1.0, realized_avg=None):
    """v2 with the path-variance term restored for d >= w."""
    if d_min >= w_min:
        sd = sigma_now * math.sqrt(max(d_min - 2.0 * w_min / 3.0, 1e-12))
        z = math.log(spot / K) / max(sd, 1e-12)
        return z
    return fair_v2(sigma_now, spot, K, d_min, w_min, realized_avg, return_z=True)


def main() -> None:
    conn = sqlite3.connect(str(DB))
    markets = pl.read_database(
        "SELECT market_id, title, asset, horizon_s, open_time_ms, close_time_ms FROM markets", conn)
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
        variants = build_sigma_variants(df)
        sig_variants[a] = variants
        sym_meta[a] = (ts, close, opn, prefix)

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
        n_fut = N - (i_now - i_open + 1)
        if n_fut < 0:
            continue
        K = float(opn[i_open])
        spot = float(close[i_now])
        d_min = n_fut
        in_final = d_min < 1
        realized_avg = float(opn[i_now]) if in_final else None
        ew = sig_variants[asset]["ewma"][i_now]
        if not np.isfinite(ew):
            continue
        z_orig = fair_v2(ew, spot, K, d_min, 1.0, realized_avg, return_z=True)
        z_fix = fair_v2_fixed(ew, spot, K, d_min, 1.0, realized_avg)
        z_yes_o = z_orig if r["is_up_market"] else -z_orig
        z_yes_f = z_fix if r["is_up_market"] else -z_fix
        rows.append({"won": int(r["token_won"]), "ask": float(r["ask"]),
                     "ts_ms": tsq, "z_orig": z_yes_o, "z_fix": z_yes_f,
                     "d_min": d_min})

    df = pl.DataFrame(rows)
    print(f"scored: {df.height:,} quotes")
    lines = ["# Round 107: fair_v2 mid-window variance fix — scored", "",
             f"quotes scored: {df.height:,} (v2_ewma sigma; z_orig vs z_fix)", ""]
    results = {}
    for name, col in (("v2_ewma_ORIG", "z_orig"), ("v2_ewma_FIXED", "z_fix")):
        z = df[col].to_numpy()
        won = df["won"].to_numpy().astype(float)
        grid = np.arange(0.5, 8.001, 0.02)
        briers = [float((((1 / (1 + np.exp(-(z / l)))) - won) ** 2).mean()) for l in grid]
        lam = float(grid[int(np.argmin(briers))])
        fair = 1 / (1 + np.exp(-(z / lam)))
        brier = float(((fair - won) ** 2).mean())
        ece, nb = 0.0, 0
        band_rows = []
        dcal = df.with_columns(pl.Series("fc", fair))
        for lo, hi in zip(BANDS[:-1], BANDS[1:]):
            b = dcal.filter((pl.col("fc") >= lo) & (pl.col("fc") < hi))
            if b.height < 30:
                continue
            mf, wr, n = float(b["fc"].mean()), float(b["won"].mean()), b.height
            ece += (n / df.height) * abs(wr - mf)
            nb += 1
            band_rows.append((lo, hi, n, mf, wr, wr - mf))
        lines.append(f"## {name} — lambda* {lam:.2f} Brier {brier:.4f} ECE {ece:.4f}")
        lines.append("")
        lines.append("| band | n | mean fair | realized | error |")
        lines.append("|---|---|---|---|---|")
        for lo, hi, n, mf, wr, err in band_rows:
            lines.append(f"| [{lo:.1f},{hi:.1f}) | {n:,} | {mf:.3f} | {wr:.3f} | {err:+.3f} |")
        lines.append("")

        # gated protocol (retest_logspace, train-only lambda+iso)
        tr = df.filter(pl.col("ts_ms") < SPLIT_MS)
        te = df.filter(pl.col("ts_ms") >= SPLIT_MS)
        z_tr, w_tr = tr[col].to_numpy(), tr["won"].to_numpy().astype(float)
        lam_t = fit_lambda(z_tr, w_tr)
        iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(z_tr / lam_t), w_tr)
        te = te.with_columns((pl.col(col) / lam_t).alias("zl"))
        te = te.with_columns(pl.Series("prob", iso.predict(sigmoid(te["zl"].to_numpy()))))
        te = te.with_columns((FEE_RATE * pl.col("ask") * (1 - pl.col("ask"))).alias("fee"))
        gated = te.filter((pl.col("prob") - pl.col("ask")) > pl.col("fee")).with_columns(
            pl.when(pl.col("won") == 1)
            .then(1 - pl.col("ask") - pl.col("fee"))
            .otherwise(-pl.col("ask") - pl.col("fee")).alias("ev"))
        ev, lo, hi, mode = daily_boot_ci(gated)
        wr = float(gated["won"].mean())
        lines.append(f"gated: n={gated.height:,} EV {ev*100:+.2f}c/trade "
                     f"CI [{lo*100:+.2f},{hi*100:+.2f}] ({mode}) WR {wr:.3f} "
                     f"lambda(train) {lam_t:.2f}")
        lines.append("")
        results[name] = (lam, brier, ece, gated.height, ev, lo, hi, lam_t)

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
