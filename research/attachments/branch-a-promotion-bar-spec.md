# Branch A Promotion Bar — Regime-Conditional EV Analysis (s023)

## Objective

Test whether s023's predictive edge concentrates in specific volatility or
time-of-day regimes such that it clears real transaction costs in that
subset, even though it does not clear costs on average. This is a
post-hoc bucketing analysis on **existing** predictions — no retraining.

## Guardrails — resolve before any bucket analysis runs

1. **Reconcile the paper-trading ledger.** 61 rows stated, but
   13 (executed) + 7 (cap-blocked) + 36 (theta skips) = 56. Find the
   missing 5 and confirm the ledger before any bucket EV number is
   trusted to draw on it.
2. **Tag id-namespace provenance.** Every table this analysis produces
   must state explicitly whether it joins on `market_id` or `token_id`.
   A zero-overlap join must not be reported as a zero-signal result.
3. **Exclude, don't interpolate, the collector gaps.** The three
   downtime windows (497 min, 457 min, 253 min) are excluded from every
   EV/accuracy number here, flagged in the output, never backfilled.
4. **Sealed H1-2026 holdout stays untouched.** Branch A runs only on
   already-used validation-era data. It is not the closing arbiter —
   Branch B is.

Do not proceed past this section until all three guardrail items are
resolved and logged.

## Pre-registered bucket definitions (fixed before results are viewed)

- **Volatility:** tercile split (low/mid/high) of realized vol, using
  **one** lookback window from the existing F6 set (6/24/96 bars) —
  state which. Do not sweep multiple lookbacks in this pass.
- **Time-of-day:** coarse session windows (e.g. 4–6 buckets), not raw
  hourly bins — controls the number of hypotheses tested.
- **Horizon:** 5m and 15m run and reported separately.
- **Total cell count fixed and written down before viewing results**
  (e.g. 3 vol terciles × 5 time windows × 2 horizons = 30 cells, or
  fewer if coarsened further).

## Cost model

EV per bucket = `p_bucket − c_bucket`, where `c_bucket` is the
**empirically observed, bucket-specific** round-trip cost (spread /
fill-adjusted), not a global average. High-vol buckets likely carry
wider spreads — this must be measured per bucket, not assumed constant.
Use the queue-aware depth-estimation fill proxy where available;
otherwise state which of the trade-print (optimistic) or price-series
(pessimistic) proxies was used.

## Statistical bar for promotion

A bucket promotes to a real-quote paper backtest only if **all** of:

1. `N ≥ 150` independent trades in that bucket, net of excluded gap
   periods (guards against repeating E2's inconclusive n=81).
2. 95% CI on net EV, via daily-block bootstrap (10k resamples,
   consistent with S3, respecting the no-shuffle walk-forward rule
   S1), excludes zero **after** multiple-comparison correction.
3. Net EV is positive in at least 2 of the available 3+ independent
   months individually, not just pooled — guards against a single
   month driving the result, the same failure mode that flipped E3's
   sign between March and April.
4. The cost figure used is that bucket's own measured cost, not the
   global average.

**Multiple comparisons:** Holm-Bonferroni across the full
pre-registered cell count, declared as its own trial family, separate
from the Phase-A R1–R12 promotion gates.

## Stop / negative-result handling

If no bucket clears all four conditions, that is the deliverable —
log it with the same epistemic weight as the RL "rational abstinence"
result. Do not re-slice into finer buckets after seeing results; that
is the p-hacking this bar exists to prevent. A genuinely new bucketing
idea gets its own separately-declared, separately-corrected pass.

## Deliverable

One table: bucket definition · N · pooled EV · per-month EV · CI ·
corrected p-value · promote/no-promote verdict — plus the id-namespace
and gap-exclusion notes from the guardrails section.
