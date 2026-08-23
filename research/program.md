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

See `research/RESULTS.md`. **s011_lgbm_bar_position** (primary 0.044257;
5m MCC +0.0309, 15m MCC +0.0576) — LGBM + imbalance + intra-bar position,
+35% over the R4 baseline after 14 trials.

### Batch-1 findings (trials 1–7)

- LightGBM >> logistic on the same 5 features (0.0395 vs 0.0327) — nonlinear
  structure is real out-of-sample, not capacity noise (heavier-regularized
  variant s006 also beat the logit but lost to s002: keep mid-capacity).
- Taker-buy imbalance helps both models (logit: +0.0013; LGBM: +0.0028).
- Realized-vol features and longer lookbacks + time-of-day: no help (RESET).

### Batch-2 findings (trials 8–14)

- **Intra-bar position ((close-low)/(high-low)) + range/ATR is the win**:
  0.0423 -> 0.0443, driven by 15m (+0.0518 -> +0.0576). Bar-level
  microstructure carries signal beyond close-to-close returns.
- Hyperparameter neighborhood (capacity up, lr 0.05): no help — s002's spec
  sits at a local optimum. Stop tuning; features are where the gains are.
- Imbalance-as-two-columns, activity z-scores: no help.
- LGBM+logit ensemble: logit drags the LGBM down. Drop it.
- Isotonic (inner temporal split): slightly HURT MCC (0.5-crossing shifts);
  tail calibration did not improve enough to justify. Keep uncalibrated for
  MCC; calibration revisited only when the metric becomes net EV.

## Idea backlog (agent: work top-down, one change per experiment)

1. More bar microstructure on top of s011: position of close in range over
   the LAST TWO bars each (pos_t, pos_{t-1}), and consecutive same-direction
   close-position streak length.
2. Range dynamics: range/ATR over {6, 24} bars; range compression
   (narrow-range-N pattern indicator).
3. Wick asymmetry: upper wick vs lower wick share of total range.
4. Open-gap within bar: (open - close_prev)/ATR (overnight/intra-bar gap).
5. Volume-weighted position: imbalance weighted by range/ATR.
6. Re-check imbalance ratio vs split AFTER bar-position is in the feature
   set (interactions may have changed what helps).

After each batch of ~10 experiments, STOP and summarize findings for the
human (diminishing returns are expected; report honestly).
