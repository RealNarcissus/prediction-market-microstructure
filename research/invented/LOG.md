# The Invention — Experiment Log

**Phase:** side quest (human-directed 2026-08-24): invent an original
quantitative formula for prediction markets; find, experiment, update,
evaluate — like training weights, but as a mathematical formula.
**Loop:** autoresearch-pattern through the locked walk-forward harness
(guard-verified, sealed holdout untouched, implausibility gate armed).
**Selection metric:** mean pooled walk-forward validation MCC (5m+15m).
**Reference champion:** s023 LightGBM, primary **0.046396**.

---

## The formula family

    P(window TWAP >= strike) = sigma( w0 + Σ w_i · z(s_i) )

- `s_i`: standardized microstructure signals computed from completed bars only
- `z()`: fold-local standardization (mean/sd from training fold)
- `w`: fitted by IRLS with L2 regularization; optional seeded hill-climb
  refinement toward direct train-MCC (V4)
- Every weight is auditable; inference is one dot product (live-cheap)

Signal dictionary: `imb` (taker imbalance 2·TBV/V−1), `pos` (close position
in bar range), `ratr24` (range/ATR24), `r10` (10-bar log return),
`streak` (causal position streak), `flow_switch` (imbalance sign flip).

## Experiments

| Ver | Trial | Hypothesis | Result | Δ vs prev |
|---|---|---|---|---|
| V1 | 32 | core signals [imb,pos,ratr24,r10] suffice in linear form | **0.035888** | — |
| V2 | 33 | + streak + flow_switch add regime structure | **0.036202** | +0.0003 |
| V3 | 34 | + nonlinearities imb·pos, imb², streak·imb | **0.036617** | +0.0004 |
| V4 | 35 | direct-MCC hill-climb beats log-loss fitting | **0.036478** | −0.0001 |
| V5 | 36 | AR(1) path-persistence modulation (TWAP-aware) | **0.036676** | +0.0002 |

All five RESET vs champion. The family plateaued at ≈0.0367.

## Weight forensics (from V3 fits across folds)

Mean |weight| ranking: imb 0.067, r10 0.065, streak 0.042, flow_switch
0.029, pos 0.011, then dead terms (≤0.005: imb_sq, imb_x_pos,
streak_x_imb, ratr24).

Findings:
1. Directional pressure (`imb`) and short momentum (`r10`) are THE signals.
2. `pos` is nearly worthless *linearly* yet was a top feature inside trees
   → its value is conditional/interaction structure, which a linear formula
   cannot express without pre-computed interactions.
3. Engineered interactions added nothing — trees already monetize them.
4. Training on train-MCC directly (V4) did not generalize better than
   IRLS log-loss; the logistic optimum is already MCC-near-optimal here.
5. AR(1) persistence modulation (V5) gave a hair of 15m lift (+0.0592→
   +0.0503 vs V3... within noise); the TWAP-average argument is sound but
   the effect is below this dataset's noise floor.

## Conclusions

1. **The interpretable-formula family saturates at ≈0.0367**, ~21% below
   the tree champion on identical data/folds. Interpretability costs real
   accuracy at this signal complexity.
2. The champion's edge lives in *conditional* structure (tree splits over
   combined states), not in marginal signal weights.
3. The invention remains valuable as: live-inference-cheap baseline,
   weight-auditable reference, and the skeleton Phase B will extend with
   market-implied terms (fair-value gap, quote staleness) where closed
   forms are natural.

## Next ideas (backlog for this phase)

1. V6: fit on OFFICIAL Jupiter resolutions once collected (~2 weeks) —
   labels with oracle truth may change which signals carry weight.
2. V7: two-stage formula — invention as prior, tiny residual correction
   from quote-staleness features at decision time.
3. V8: per-horizon weight vectors with shared sparsity pattern (group lasso).
