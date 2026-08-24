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

See `research/RESULTS.md`. **s023_lgbm_pos_lag23** (primary 0.046396;
5m MCC +0.0319, 15m MCC +0.0609) — LGBM + imbalance + bar position +
range-weighted imbalance + position history (pos_{t-2}, pos_{t-3}).
**+42% over the R4 baseline** across 27 counted trials.

### Batch-1 findings (trials 1–7)

- LightGBM >> logistic on the same 5 features (0.0395 vs 0.0327) — nonlinear
  structure is real out-of-sample. Mid-capacity spec (s002) is the sweet
  spot; heavier regularization also beat the logit but lost to s002.
- Taker-buy imbalance helps both models (logit: +0.0013; LGBM: +0.0028).
- Realized-vol features and longer lookbacks + time-of-day: no help (RESET).

### Batch-2 findings (trials 8–14)

- **Intra-bar position ((close-low)/(high-low)) + range/ATR is the win**:
  0.0423 -> 0.0443, driven by 15m (+0.0518 -> +0.0576). Bar-level
  microstructure carries signal beyond close-to-close returns.
- Hyperparameter neighborhood: no help — s002's spec is at a local optimum.
  Stop tuning; features are where the gains are.
- LGBM+logit ensemble: logit drags the LGBM down. Isotonic slightly HURT
  MCC (0.5-crossing shifts); calibration deferred until net-EV metric.

### ⚠️ INCIDENT LOG — trial 8 (s014): accidental leakage, caught and reversed

s014 reported MCC 0.5713 (impossible; ceiling ~0.05). Root cause: its
"streak" feature used ex-post run lengths — a row's value encoded how long
the run *became*, i.e. future bars. Feature-target correlation confirmed
(+0.145 vs ±0.04 for legit features). Response: s014 invalidated in the
ledger and quarantined to `research/archive/`; s011 champion restored;
batch-3 verdicts re-adjudicated (fresh trials, honestly counted); runner
now BLOCKS any auto-keep above MCC 0.15 pending human review
(`--accept-implausible` overrides). Lesson: implausibility IS a test.

### Batch-3 findings (re-adjudicated, trials 15–22)

- **s018 KEEP**: imbalance weighted by range/ATR adds real signal
  (0.0443 → 0.0454) — directional pressure matters more in wide bars.
- **s020 reset-vs-s018 but beats old champion** (0.0448): CAUSAL position
  streak + pos_{t-1} help; combine with s018 in batch 4.
- Range dynamics (ratr6, narrowest-of-5), wick asymmetry, open-gap,
  imbalance-as-two-columns: all no help (RESET).

### Batch-4 findings (trials 23–27)

- Position history is the vein: pos_{t-2}/pos_{t-3} KEEP (0.0454 → 0.0464);
  the s021 combo (causal streak + pos_prev) also KEEP (0.0457).
- Full merge of all additions (s025) RESET — beyond pos lags, the extra
  streak/pos_prev features overlap and add noise. Feature set is saturating.
- imb-sign streak and ratr12/48: no help.

### Phase-A status: PLATEAU REACHED

Gains have flattened (batch-4 keeps: +0.0002 and +0.0007; batch-1 keeps
averaged +0.003) and the backlog below the noise floor is exhausted.
**Decision: Phase A closed.** Standing plan:
1. Hold the sealed-holdout verdict until Phase B is modeled — one clean
   verdict covering the Phase-A champion and the Phase-B (Jupiter) strategy
   together is worth more than spending it twice.
2. Wait for ~3 weeks of Jupiter collection (running; see data/collector.db).
3. Phase B: metric switches to net-EV-after-fees vs market-implied baseline;
   this file gets a new Phase-B section from the human at that point.

## Idea backlog (FROZEN — Phase A closed; reopen only by human edit)

1. (low priority) Hour-of-day interactions with pos/imb features.
2. (low priority) LGBM monotone constraints on imb features.

After each batch of ~10 experiments, STOP and summarize findings for the
human (diminishing returns are expected; report honestly).

### Literature batch (2026-08-24, human-directed: arXiv autoresearch)

Four published edge formulas reproduced on our data through the locked
harness (trials 28-31): Quarter-Hour imb lags and flow-switch dummies
(arXiv:2607.09426), VPIN volume-clock toxicity (arXiv:1912.10343), and
Amihud-impact-weighted imbalance (Amihud 2002 + arXiv:2602.00776).
**All four RESET** — the s023 champion already absorbs the
OHLCV-computable literature. Full catalog with formulas, verdicts, and
replication-cost estimates: `research/litreview/CATALOG.md`. Tier-2
formulas (OFI, micro-price, Hawkes) await ~2 weeks of collected
depth/tick data — they are Phase-B candidates, not Phase-A.
