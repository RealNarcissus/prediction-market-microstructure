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

See `research/RESULTS.md`. **s005_lgbm_plus_imbalance** (primary 0.042270;
5m MCC +0.0327, 15m MCC +0.0518) — LightGBM + taker-buy imbalance, +29% over
the R4 baseline after 7 trials.

### Batch-1 findings (2026-08-23, 7 trials)

- LightGBM >> logistic on the same 5 features (0.0395 vs 0.0327) — nonlinear
  structure is real out-of-sample, not capacity noise (heavier-regularized
  variant s006 also beat the logit but lost to s002: keep mid-capacity).
- Taker-buy imbalance helps both models (logit: +0.0013; LGBM: +0.0028).
- Realized-vol features and longer lookbacks + time-of-day: no help (RESET).

## Idea backlog (agent: work top-down, one change per experiment)

1. LGBM hyperparameter neighborhood around s002 (num_leaves 31 worked;
   try 63 / min_child_samples 1000 / lr 0.05 with n_est 200 — capacity
   frontier).
2. Interactions: give LGBM the imbalance split by up/down volume separately
   (TBV and V-TBV as two columns) instead of the single ratio.
3. Volume/count activity z-scores (rolling 24-bar z).
4. Intra-bar position features: close position within bar range
   (close-low)/(high-low), and bar range / ATR.
5. Ensemble: average s005 with the R4 logit probabilities (variance
   reduction; cheap).
6. Calibration-aware variant: isotonic on fold-internal holdout; expect no
   MCC change — check tail calibration error improves without hurting MCC.

After each batch of ~10 experiments, STOP and summarize findings for the
human (diminishing returns are expected; report honestly).
