"""Calibrated-fair re-test — does the staleness edge survive honest calibration?

Protocol (pre-registered before running):
  Split   : temporal — calibration fit on quotes < 2026-08-29 00:00 UTC,
            test on >= 2026-08-29 (the denser, cleaner recent span).
  Mapping : global isotonic regression fair -> P(token wins), fit on ALL
            scored train quotes (not just gated), monotone, clipped.
  Rule    : buy yes at ask when calibrated_gap = fair_cal - ask > fee(ask).
  Primary : test-span EV with day-block bootstrap CI (4 blocks — thin,
            reported with per-day EV).
  Controls: (a) uncalibrated gap rule on the same test span (apples-to-apples);
            (b) favorites control — buy the same N cheapest-ask quotes with
            NO model signal (does the fair add value beyond buying favorites?);
            (c) calibration quality on test (mean fair_cal vs realized win).
  Verdict : CI excludes 0 AND beats favorites control -> founding thesis
            (exploitable staleness) survives. CI covers 0 -> unresolved;
            EV <= 0 after calibration -> venue sharper than our pricer,
            honest negative.

Sealed H1-2026 holdout untouched (live collector span only).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "research" / "staleness" / "scored_quotes.parquet"
OUT = REPO / "research" / "staleness" / "CALIBRATED_RETEST.md"

SPLIT_MS = int(np.datetime64("2026-08-29T00:00:00").astype("datetime64[ms]").astype(int))


def day_boot_ci(pnl: np.ndarray, days: np.ndarray, n_boot: int = 10000, seed: int = 0):
    uniq = np.unique(days)
    day_pnl = {d: pnl[days == d] for d in uniq}
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        smp = np.concatenate([day_pnl[d] for d in rng.choice(uniq, size=len(uniq), replace=True)])
        boots.append(float(np.mean(smp)))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    per_day = {str(d): float(day_pnl[d].mean()) for d in uniq}
    per_day_n = {str(d): int((days == d).sum()) for d in uniq}
    return float(lo), float(hi), per_day, per_day_n


def rule_stats(sel: pl.DataFrame) -> dict:
    d = sel.to_dicts()
    n = len(d)
    pnl = np.array([x["ev_buy"] for x in d])
    wr = float(np.mean([x["won"] for x in d]))
    avg_ask = float(np.mean([x["ask"] for x in d]))
    be = avg_ask + float(np.mean([x["fee"] for x in d]))
    days = np.array([datetime.fromtimestamp(int(x["ts_ms"]) / 1000, tz=timezone.utc).date() for x in d])
    lo, hi, per_day, per_day_n = day_boot_ci(pnl, days)
    return {
        "n": n, "ev": float(pnl.mean()), "wr": wr, "avg_ask": avg_ask, "breakeven": be,
        "ci_lo": lo, "ci_hi": hi, "per_day": per_day, "per_day_n": per_day_n,
        "total": float(pnl.sum()),
    }


def fmt_rule(label: str, s: dict) -> str:
    pd_str = ", ".join(f"{d}: {v:+.4f} (n={s['per_day_n'][d]})" for d, v in s["per_day"].items())
    return (
        f"**{label}**: N={s['n']}, win {s['wr']:.1%} vs breakeven {s['breakeven']:.1%} "
        f"(avg ask {s['avg_ask']:.3f}), EV/trade {s['ev']:+.4f}, "
        f"day-block 95% CI [{s['ci_lo']:+.4f}, {s['ci_hi']:+.4f}], total {s['total']:+.2f}\n"
        f"\n  Per-day EV: {pd_str}\n"
    )


def main() -> None:
    df = pl.read_parquet(str(SRC))
    df = df.with_columns((pl.col("ts_ms") >= SPLIT_MS).alias("is_test"))
    train = df.filter(~pl.col("is_test"))
    test = df.filter(pl.col("is_test"))

    # --- fit isotonic on ALL train quotes (fair -> won) ---
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    iso.fit(train["fair"].to_numpy(), train["won"].to_numpy())

    for frame in (train, test):
        pass
    train = train.with_columns(pl.Series("fair_cal", iso.predict(train["fair"].to_numpy())))
    test = test.with_columns(pl.Series("fair_cal", iso.predict(test["fair"].to_numpy())))
    train = train.with_columns((pl.col("fair_cal") - pl.col("ask")).alias("gap_cal"))
    test = test.with_columns((pl.col("fair_cal") - pl.col("ask")).alias("gap_cal"))

    lines = ["# Calibrated-Fair Re-Test — does the staleness edge survive honest calibration?", ""]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append(f"Split: calibration fit on {train.height} quotes (< 2026-08-29), test on {test.height} quotes (>= 2026-08-29).")
    lines.append("Isotonic mapping fair->P(win) fit on ALL train quotes; gate = calibrated gap > fee(ask). Protocol pre-registered in script docstring.")
    lines.append("")

    # calibration quality
    lines.append("## 1. Calibration quality on TEST span")
    lines.append("")
    lines.append("| fair_cal bucket | N | mean fair_cal | realized win | miscalibration |")
    lines.append("|---|---|---|---|---|")
    tb = test.to_dicts()
    for lo, hi, label in [(0.0, 0.5, "<50c"), (0.5, 0.65, "50-65c"), (0.65, 0.8, "65-80c"), (0.8, 0.95, "80-95c"), (0.95, 1.01, ">95c")]:
        sub = [x for x in tb if lo <= x["fair_cal"] < hi]
        if len(sub) < 50:
            continue
        n = len(sub)
        fm = float(np.mean([x["fair_cal"] for x in sub]))
        wr = float(np.mean([x["won"] for x in sub]))
        lines.append(f"| {label} | {n} | {fm:.3f} | {wr:.3f} | {wr-fm:+.3f} |")
    lines.append("")

    # primary: calibrated rule on test
    lines.append("## 2. TEST-span taker rule results")
    lines.append("")
    lines.append("### Primary: calibrated gap gate")
    cal = rule_stats(test.filter(pl.col("gap_cal") > pl.col("fee")))
    lines.append(fmt_rule("fair_cal - ask > fee", cal))
    lines.append("")
    lines.append("### Control A: uncalibrated gap gate (same test span)")
    unc = rule_stats(test.filter(pl.col("gap") > pl.col("fee")))
    lines.append(fmt_rule("raw fair - ask > fee", unc))
    lines.append("")
    lines.append("### Control B: favorites — same N cheapest asks, no model signal")
    n_target = cal["n"]
    all_test = test.to_dicts()
    all_test_sorted = sorted(all_test, key=lambda x: x["ask"])
    fav = pl.DataFrame(all_test_sorted[:n_target])
    fav_stats = rule_stats(fav)
    lines.append(fmt_rule(f"cheapest {n_target} asks (no signal)", fav_stats))
    lines.append("")

    # by asset x horizon for the calibrated rule
    lines.append("### Calibrated gate by asset x horizon")
    lines.append("")
    lines.append("| asset | hz | N | win | EV |")
    lines.append("|---|---|---|---|---|")
    cal_df = test.filter(pl.col("gap_cal") > pl.col("fee"))
    for (a, h), g in cal_df.group_by(["asset", "hz"]):
        gd = g.to_dicts()
        ev = float(np.mean([x["ev_buy"] for x in gd]))
        wr = float(np.mean([x["won"] for x in gd]))
        lines.append(f"| {a} | {h} | {len(gd)} | {wr:.1%} | {ev:+.4f} |")
    lines.append("")

    # by phase
    lines.append("### Calibrated gate by epoch phase")
    lines.append("")
    lines.append("| phase | N | avg ask | win | breakeven | EV |")
    lines.append("|---|---|---|---|---|---|")
    for lo, hi, label in [(0, 60, "0-60s"), (60, 180, "60-180s"), (180, 420, "180-420s"), (420, 10000, ">420s")]:
        s = cal_df.filter((pl.col("tau_rem") >= lo) & (pl.col("tau_rem") < hi))
        if s.height == 0:
            continue
        d = s.to_dicts()
        n = len(d)
        aa = float(np.mean([x["ask"] for x in d]))
        wr = float(np.mean([x["won"] for x in d]))
        ev = float(np.mean([x["ev_buy"] for x in d]))
        be = aa + float(np.mean([x["fee"] for x in d]))
        lines.append(f"| {label} | {n} | {aa:.3f} | {wr:.1%} | {be:.1%} | {ev:+.4f} |")
    lines.append("")

    # verdict
    lines.append("## 3. Verdict")
    lines.append("")
    beats_fav = cal["ev"] > fav_stats["ev"]
    sig = cal["ci_lo"] > 0
    if sig and beats_fav:
        lines.append("**EDGE SURVIVES: test CI excludes 0 AND calibrated gate beats the favorites control.** Founding thesis (exploitable staleness) is alive; next step is paper-trade design with sizing/latency reality.")
    elif cal["ev"] <= 0:
        lines.append("**HONEST NEGATIVE: calibrated EV <= 0 on test.** After honest calibration the venue is at least as sharp as our pricer; exploitable staleness is not established at this sample.")
    else:
        lines.append(
            f"**UNRESOLVED: calibrated EV positive ({cal['ev']:+.4f}) but CI covers 0 ({cal['ci_lo']:+.4f}, {cal['ci_hi']:+.4f})"
            + ("" if beats_fav else " AND does not beat the favorites control") + ".** "
            "Thin-sample limbo: the direction is encouraging but not proven; more test days or a tighter rule needed."
        )
    lines.append("")
    lines.append("Notes: 4 daily blocks in test span (thin for day-block bootstrap — per-day EV listed above); fee scenario 0.07 only (2x scenario changes gate marginally since gaps are large); isolated quotes, no queue/latency modeling — this is an upper bound on executable edge.")

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
