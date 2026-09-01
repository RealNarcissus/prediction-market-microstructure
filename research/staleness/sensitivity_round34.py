"""Round 34: sensitivity + residual attribution for the log-space re-test.

1. Split sensitivity: re-run the v2_ewma gate with the temporal split moved
   (Aug 30 / Aug 31) — does the +6.8c EV survive different train/test cuts?
2. Residual attribution: where does the extreme-band overconfidence live?
   Bucket calibrated-fair residual (realized - fair) by remaining-time d,
   sigma level, asset, and horizon — to separate strike-basis noise from
   vol-understatement and inform the Chainlink-data strike-basis test.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from pathlib import Path
from sklearn.isotonic import IsotonicRegression

REPO = Path(__file__).resolve().parents[2]
PARQUET = REPO / "research" / "staleness" / "calibration_compare.parquet"
OUT = REPO / "research" / "staleness" / "SENSITIVITY_ROUND34.md"
FEE_RATE = 0.07


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def fit_lambda(z, won):
    grid = np.arange(0.5, 8.001, 0.05)
    bs = [float(((sigmoid(z / l) - won) ** 2).mean()) for l in grid]
    return float(grid[int(np.argmin(bs))])


def gate_ev(d, split_ms):
    tr = d.filter(pl.col("ts_ms") < split_ms)
    te = d.filter(pl.col("ts_ms") >= split_ms)
    if tr.height < 1000 or te.height < 1000:
        return None
    lam = fit_lambda(tr["z"].to_numpy(), tr["won"].to_numpy().astype(float))
    iso = IsotonicRegression(out_of_bounds="clip").fit(
        sigmoid(tr["z"].to_numpy() / lam), tr["won"].to_numpy().astype(float)
    )
    te = te.with_columns((pl.col("z") / lam).alias("zl"))
    te = te.with_columns(pl.Series("prob", iso.predict(sigmoid(te["zl"].to_numpy()))))
    te = te.with_columns((FEE_RATE * pl.col("ask") * (1 - pl.col("ask"))).alias("fee"))
    g = te.filter((pl.col("prob") - pl.col("ask")) > pl.col("fee")).with_columns(
        pl.when(pl.col("won") == 1)
        .then(1 - pl.col("ask") - pl.col("fee"))
        .otherwise(-pl.col("ask") - pl.col("fee"))
        .alias("ev")
    )
    if g.height < 30:
        return None
    return lam, tr.height, te.height, g.height, float(g["ev"].mean()), float(g["won"].mean())


def main() -> None:
    df = pl.read_parquet(str(PARQUET)).filter(pl.col("cfg") == "v2_ewma")
    lines = ["# Round 34: split sensitivity + residual attribution (v2_ewma)", ""]

    # 1. split sensitivity
    lines.append("## Split sensitivity (gate EV at different temporal cuts)")
    lines.append("")
    lines.append("| split (UTC) | train n | test n | gated | EV/trade | win rate |")
    lines.append("|---|---|---|---|---|---|")
    for label, ms in [
        ("Aug 29 12:00", 1788004800000),
        ("Aug 30 00:00", 1788048000000),
        ("Aug 31 00:00", 1788134400000),
    ]:
        r = gate_ev(df, ms)
        if r:
            lam, tr_n, te_n, g_n, ev, wr = r
            lines.append(f"| {label} | {tr_n:,} | {te_n:,} | {g_n:,} | {ev*100:+.2f}c | {wr:.3f} |")
        else:
            lines.append(f"| {label} | — | — | — | insufficient | — |")
    lines.append("")

    # 2. residual attribution on the FULL sample (calibration, not gate EV)
    lam = fit_lambda(df["z"].to_numpy(), df["won"].to_numpy().astype(float))
    d = df.with_columns((pl.col("z") / lam).alias("zl"))
    d = d.with_columns(pl.Series("prob", sigmoid(d["zl"].to_numpy())))
    d = d.with_columns((pl.col("won") - pl.col("prob")).alias("resid"))
    d = d.filter((pl.col("prob") >= 0.9) | (pl.col("prob") <= 0.1))

    def bucket(by):
        g = (
            d.group_by(by)
            .agg(
                pl.len().alias("n"),
                pl.col("resid").mean().alias("mean_resid"),
            )
            .sort(by)
        )
        return g

    lines.append(f"## Extreme-band residual attribution (n={d.height:,}; lambda={lam:.2f})")
    lines.append("")
    lines.append("### By remaining time d (minutes to close)")
    lines.append(bucket(pl.col("ts_ms").sub(0).mul(0).alias("_")).drop("_") if False else "")
    db = d.with_columns(
        pl.when(pl.col("in_final")).then(pl.lit("final-60s"))
        .otherwise(pl.lit("d>=60s")).alias("d_bucket")
    )
    for b in ("final-60s", "d>=60s"):
        s = db.filter(pl.col("d_bucket") == b)
        lines.append(f"- {b}: n={s.height:,} mean resid {float(s['resid'].mean()):+.4f}")
    lines.append("")
    lines.append("### By asset")
    for row in bucket(pl.col("asset")).to_dicts():
        lines.append(f"- {row['asset']}: n={row['n']:,} mean resid {row['mean_resid']:+.4f}")
    lines.append("")
    lines.append("### By horizon")
    for row in bucket(pl.col("hz")).to_dicts():
        lines.append(f"- {row['hz']}: n={row['n']:,} mean resid {row['mean_resid']:+.4f}")
    lines.append("")
    lines.append("Reading: a residual that is stable across d/asset/hz points to a")
    lines.append("scale factor (strike basis or fat tails); concentration in one")
    lines.append("bucket points to a localized mechanism.")

    OUT.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
