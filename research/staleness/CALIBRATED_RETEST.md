# Calibrated-Fair Re-Test — does the staleness edge survive honest calibration?

Generated: 2026-09-01T18:55:41.164101+00:00

Split: calibration fit on 30755 quotes (< 2026-08-29), test on 63076 quotes (>= 2026-08-29).
Isotonic mapping fair->P(win) fit on ALL train quotes; gate = calibrated gap > fee(ask). Protocol pre-registered in script docstring.

## 1. Calibration quality on TEST span

| fair_cal bucket | N | mean fair_cal | realized win | miscalibration |
|---|---|---|---|---|
| <50c | 32221 | 0.261 | 0.256 | -0.005 |
| 50-65c | 262 | 0.512 | 0.370 | -0.142 |
| 65-80c | 30593 | 0.716 | 0.745 | +0.028 |

## 2. TEST-span taker rule results

### Primary: calibrated gap gate
**fair_cal - ask > fee**: N=27013, win 38.2% vs breakeven 35.4% (avg ask 0.341), EV/trade +0.0287, day-block 95% CI [-0.0011, +0.0494], total +776.01

  Per-day EV: 2026-08-29: +0.0211 (n=7113), 2026-08-30: +0.0258 (n=8224), 2026-08-31: +0.0572 (n=8579), 2026-09-01: -0.0249 (n=3097)


### Control A: uncalibrated gap gate (same test span)
**raw fair - ask > fee**: N=30781, win 74.2% vs breakeven 71.2% (avg ask 0.701), EV/trade +0.0296, day-block 95% CI [-0.0110, +0.0602], total +909.86

  Per-day EV: 2026-08-29: +0.0097 (n=9425), 2026-08-30: +0.0392 (n=8647), 2026-08-31: +0.0765 (n=8731), 2026-09-01: -0.0473 (n=3978)


### Control B: favorites — same N cheapest asks, no model signal
**cheapest 27013 asks (no signal)**: N=27013, win 21.8% vs breakeven 26.1% (avg ask 0.249), EV/trade -0.0423, day-block 95% CI [-0.0647, -0.0327], total -1141.31

  Per-day EV: 2026-08-29: -0.0318 (n=7303), 2026-08-30: -0.0334 (n=9122), 2026-08-31: -0.0437 (n=7646), 2026-09-01: -0.0918 (n=2942)


### Calibrated gate by asset x horizon

| asset | hz | N | win | EV |
|---|---|---|---|---|
| BTC | 900s | 4675 | 35.2% | +0.0162 |
| BTC | 300s | 1725 | 33.4% | +0.0330 |
| ETH | 900s | 5923 | 43.2% | +0.0439 |
| SOL | 300s | 4870 | 36.6% | +0.0229 |
| ETH | 300s | 4540 | 36.9% | +0.0352 |
| SOL | 900s | 5280 | 39.5% | +0.0212 |

### Calibrated gate by epoch phase

| phase | N | avg ask | win | breakeven | EV |
|---|---|---|---|---|---|
| 0-60s | 1075 | 0.299 | 37.7% | 31.0% | +0.0663 |
| 60-180s | 7238 | 0.261 | 30.1% | 27.1% | +0.0295 |
| 180-420s | 9918 | 0.335 | 37.7% | 34.7% | +0.0299 |
| >420s | 8782 | 0.420 | 45.6% | 43.4% | +0.0222 |

## 3. Verdict

**UNRESOLVED: calibrated EV positive (+0.0287) but CI covers 0 (-0.0011, +0.0494).** Thin-sample limbo: the direction is encouraging but not proven; more test days or a tighter rule needed.

Notes: 4 daily blocks in test span (thin for day-block bootstrap — per-day EV listed above); fee scenario 0.07 only (2x scenario changes gate marginally since gaps are large); isolated quotes, no queue/latency modeling — this is an upper bound on executable edge.

---

## 4. Robustness (post-hoc, exploratory — not part of the pre-registered primary)

### EV monotonicity in calibrated gap (test span, gated trades)

| calibrated gap | N | avg ask | realized win | EV |
|---|---|---|---|---|
| fee-5pp | 2,890 | 0.446 | 42.9% | −0.0309 |
| 5-10pp | 4,484 | 0.395 | 38.9% | −0.0192 |
| 10-20pp | 10,037 | 0.314 | 34.6% | +0.0208 |
| 20-40pp | 7,740 | 0.305 | 39.1% | +0.0735 |
| >40pp | 1,307 | 0.200 | 32.7% | **+0.1165** |

Strongly monotone above 10pp — the signature of a real signal, not noise. Small-gap trades (gap ≈ fee hurdle) lose, as expected when the signal-to-noise ratio is ~1; the edge lives entirely where the model disagrees with the book by >10pp.

### ETH 900s alone (strongest cell)

N=5,923, EV +4.39¢, day-block 95% CI **[+0.0006, +0.0721] — excludes zero.** Per-day: −2.0¢ / +7.5¢ / +6.3¢ / +5.0¢ (3 of 4 positive).
Raw p ≈ 0.016 — but this cell was selected as the best of 6 post-hoc; Holm across the 6 asset×horizon cells gives p_adj ≈ 0.10, NOT significant under the project's own multiple-comparisons discipline. It is the leading candidate, not a confirmed promotion.

### What the controls establish

- Favorites control (same N cheapest asks, no signal): EV **−4.23¢** [−6.5¢, −3.3¢]. The calibrated gate's +2.87¢ on the same N is a **+7.1¢ swing attributable to the fair-value signal**. The edge is NOT "buying cheap favorites."
- Uncalibrated vs calibrated gates land at nearly identical EV (+2.96¢ vs +2.87¢) while selecting completely different trades (avg ask 0.70 vs 0.34) — two disjoint rule families agree on the magnitude, which is a robustness point in the signal's favor.

## 5. Honest verdict (updated)

**The staleness thesis is alive for the first time on honest data.** Calibrated, resolution-confirmed, temporally out-of-sample EV is positive in all 6 asset×horizon cells, monotone in signal strength, +7¢ swing vs the no-signal control — but the pooled CI covers zero by 0.11¢, and the best single cell does not survive Holm across its family.

Under the project's own promotion bar (Branch-A spec): per-cell N ✓ (≥1,725 everywhere), CI-excludes-0 ✗ pooled / ✗ after Holm per-cell, EV>0 in ≥2 months — untestable at 4 test days.

**Not promotable yet. Not refuted.** The gap between this and every previous experiment: those failed *against* the gate; this one is *approaching* it as sample grows.

### Pre-registered weekly re-test protocol (for the next runs)

1. Collector keeps running; every ~7 days re-run `calibrated_retest.py` with the split moved forward (calibration on all history before the new test week). No rule changes between runs.
2. Family stays 6 cells (3 asset × 2 horizon) + pooled; Holm across 6, separate from all previous families.
3. Promotion requires: pooled CI excludes 0, or ≥1 cell passes Holm, AND EV>0 in ≥2 distinct weeks.
4. Before any paper trade: latency-aware fill model (signal decays with time-since-print), fee confirmation (0.07 documented vs spec's "2× Polymarket" note), and interleaved orderbook polling to kill the sampler bias.
