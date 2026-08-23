# Autoresearch Program — quant-btc

This file is the HUMAN's steering document. The agent (loop) reads it and
proposes strategies accordingly; the agent never edits it.

## Mission

Maximize the primary metric — **mean pooled walk-forward validation MCC
(5m + 15m) on the Herdr frozen BTC dataset** — as Phase A of the project.
Phase A is exchange-side research only. When enough Jupiter quote history
exists (~3 weeks of collection), the metric switches to net-EV-after-fees
vs the market-implied baseline and this file gets a new section from the
human.

## Hard rules (never violated by the loop)

1. `research/locked/` is immutable — guard-verified before every run.
2. The sealed H1-2026 holdout is never evaluated on. Only the human triggers
   `runner.py verdict`, and every use is counted in the ledger.
3. Every experiment goes through `runner.py run` so the trial count stays
   honest for deflated final statistics.
4. Strategies must be deterministic (fixed seeds) and use no lookahead:
   features at row i may only use bars ≤ i.
5. Keep-or-reset is greedy on primary MCC with epsilon 1e-4. Tail
   calibration error is recorded as a secondary diagnostic — do not
   sacrifice it silently.

## Strategy contract

One file in `research/strategies/sNNN_name.py` exposing:
- `NAME: str`
- `build_features(df) -> np.ndarray` (rows aligned to df; NaN warmup rows OK)
- `new_model()` — sklearn-like: `fit(X, y)`, `predict_proba(X)` returning
  `(n, 2)` with column order `[P(y=0), P(y=1)]`, exposing `classes_`

## Current champion

See `research/RESULTS.md`. Baseline: s000 (R4 port, primary 0.032710,
matching the Herdr reference).

## Idea backlog (agent: work top-down, one change per experiment)

1. Taker-buy volume imbalance feature `2*TBV/V - 1` (Herdr Exp005 found it
   lifted traded-subset win rates and per-trade edge; on pure MCC it was
   roughly neutral — test whether MCC also moves).
2. Realized volatility features: rolling std of 1-bar returns over
   {6, 24, 96} bars, and vol-of-vol.
3. LightGBM (small: ≤300 leaves, deep limits, strong min_child_samples,
   fixed seed) on the base 5 features — capture nonlinearity the logit misses.
4. Longer lookbacks f_{20}, f_{50} and hourly-aligned seasonality
   (time-of-day one-hots via sin/cos of minute-of-day).
5. Trade-count and volume z-score features (activity bursts).
6. Calibration-aware variant: isotonic on fold-internal holdout — expect no
   MCC change; useful only if tail calibration error improves (note it).

After each batch of ~10 experiments, STOP and summarize findings for the
human (diminishing returns are expected; report honestly).
