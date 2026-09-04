"""Calibrated re-test with the log-space fair (round 33).

Uses calibration_compare.parquet (per-quote z per config) — fully in-sample
independent of the old audit fairs. Honest protocol:
  - temporal split at 2026-08-29 12:00 UTC (train = earlier, test = later)
  - lambda re-fit on TRAIN only (Brier-minimizing), isotonic on TRAIN
    (z/lambda -> calibrated prob)
  - test gate: buy yes at ask when calibrated_prob - ask > fee(ask)
  - EV per trade vs official resolutions; daily-block bootstrap CI (fallback
    trade-level when <5 days); favorites control (same-N cheapest asks)
Configs compared: v1_r24 (running TWAP) vs v2_ewma (champion from round 32).
"""

from __future__ import annotations

import numpy as np
import polars as pl
from pathlib import Path
from sklearn.isotonic import IsotonicRegression

REPO = Path(__file__).resolve().parents[2]
PARQUET = REPO / "research" / "staleness" / "calibration_compare.parquet"
OUT = REPO / "research" / "staleness" / "RETEST_LOGSPACE.md"
FEE_RATE = 0.07
SPLIT_MS = 1788004800000  # 2026-08-29 12:00 UTC


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def fit_lambda(z: np.ndarray, won: np.ndarray) -> float:
    grid = np.arange(0.5, 8.001, 0.05)
    best, bl = None, None
    for l in grid:
        b = float(((sigmoid(z / l) - won) ** 2).mean())
        if bl is None or b < bl:
            best, bl = l, b
    return float(best)


def daily_boot_ci(df: pl.DataFrame, n_boot: int = 5000, seed: int = 7):
    ev = df["ev"].to_numpy()
    days = df["ts_ms"].to_numpy() // 86_400_000
    uniq = np.unique(days)
    if len(uniq) < 5:
        rng = np.random.default_rng(seed)
        boots = [float(np.mean(rng.choice(ev, len(ev)))) for _ in range(n_boot)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        return float(np.mean(ev)), float(lo), float(hi), "trade-level"
    rng = np.random.default_rng(seed)
    means = []
    by_day = {d: ev[days == d] for d in uniq}
    for _ in range(n_boot):
        sample = np.concatenate([by_day[d] for d in rng.choice(uniq, len(uniq))])
        means.append(float(np.mean(sample)))
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(np.mean(ev)), float(lo), float(hi), "daily-block"


def run_config(df: pl.DataFrame, cfg: str) -> list[str]:
    d = df.filter(pl.col("cfg") == cfg).sort("ts_ms")
    tr = d.filter(pl.col("ts_ms") < SPLIT_MS)
    te = d.filter(pl.col("ts_ms") >= SPLIT_MS)
    z_tr, won_tr = tr["z"].to_numpy(), tr["won"].to_numpy().astype(float)
    lam = fit_lambda(z_tr, won_tr)
    iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(z_tr / lam), won_tr)

    te = te.with_columns((pl.col("z") / lam).alias("z_l"))
    te = te.with_columns(
        pl.Series("prob", iso.predict(sigmoid(te["z_l"].to_numpy())))
    )
    te = te.with_columns((FEE_RATE * pl.col("ask") * (1 - pl.col("ask"))).alias("fee"))
    gated = te.filter((pl.col("prob") - pl.col("ask")) > pl.col("fee")).with_columns(
        pl.when(pl.col("won") == 1)
        .then(1 - pl.col("ask") - pl.col("fee"))
        .otherwise(-pl.col("ask") - pl.col("fee"))
        .alias("ev")
    )
    lines = [f"## {cfg}  —  lambda(train) {lam:.2f}", ""]
    lines.append(f"train n={tr.height:,}  test n={te.height:,}  gated trades={gated.height:,}")
    if gated.height < 30:
        lines.append("insufficient gated trades")
        return lines
    ev, lo, hi, mode = daily_boot_ci(gated)
    lines.append(f"EV/trade {ev*100:+.2f}c  CI [{lo*100:+.2f}, {hi*100:+.2f}]c  ({mode})")
    wr = float(gated["won"].mean())
    lines.append(f"win rate {wr:.3f}  avg ask {float(gated['ask'].mean()):.3f}")
    # favorites control: same N cheapest asks in test (any gate)
    ctrl = te.sort("ask").head(gated.height)
    cevc = ctrl.with_columns(
        pl.when(pl.col("won") == 1)
        .then(1 - pl.col("ask") - FEE_RATE * pl.col("ask") * (1 - pl.col("ask")))
        .otherwise(-pl.col("ask") - FEE_RATE * pl.col("ask") * (1 - pl.col("ask")))
        .alias("ev")
    )
    cev, clo, chi, _ = daily_boot_ci(cevc)
    lines.append(f"favorites control (N={gated.height}): EV {cev*100:+.2f}c CI [{clo*100:+.2f}, {chi*100:+.2f}]c")
    lines.append("")
    return lines


def main() -> None:
    df = pl.read_parquet(str(PARQUET))
    lines = ["# Calibrated re-test with log-space fair (round 33)", "",
             f"split: {SPLIT_MS} (2026-08-29 12:00 UTC); lambda+isotonic fit on train only", ""]
    for cfg in ("v1_r24", "v2_ewma"):
        lines += run_config(df, cfg)
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
