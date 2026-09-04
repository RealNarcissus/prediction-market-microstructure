# Loop Runbook — Long-Horizon arXiv Auto-Research

## Budgets (hard — loop cannot claim GOAL_COMPLETE early)

- `papers_target: 20` — number of papers in `research/rlenv/paper_queue.yaml` to sweep.
- `helpful_target: 3` — number of formulae that **KEEP** (promote ≥1 bucket) on net-EV after fees.
- `knowledge_stall_steps: 8` — consecutive `RESET`+`DEFERRED` with no `KEEP` yields `KNOWLEDGE_STOPPED` (parked, not success).
- `CHUNK_SIZE: 2` papers per step. `Lifecycle.papers_swept` counts papers, `step_count` counts steps.

`harness.Lifecycle.evaluate` returns `END` when `step_budget` or wall-clock exceeded, `KNOWLEDGE_STOPPED` on stall, else `LEARNING_PROGRESS`. Only `is_goal_complete()` (both targets met) is success. Human halt always wins.

## Status semantics

- `RESET` — scored, no bucket promoted. Honest negative, same weight as `KEEP`.
- `DEFERRED` — gated on depth/tick data not yet available (e.g. OFI/micro-price need `depth20` ≥14d, Hawkes needs `aggTrade`). Logged with `deferred_reason`; does not refute the phenomenon.
- `KEEP` — ≥1 bucket meets `N≥150 ∧ Holm CI excludes 0 ∧ EV>0 ∧ bucket-specific cost`.
- `NEAR_PROMOTE` (when logged) — would promote if `N≥150` were met but sample still thin; tracks `max_N`.
- `CHUNK` — outer lifecycle entry for a 2-paper chunk.

## Venue caveat (do not relax — copy verbatim)

> The papers you previously cataloged (VPIN, Amihud, Quarter-Hour effect) are built for continuous limit order books on spot/futures venues. A binary prediction market has different quote dynamics, different depth structure, and a bounded payout — there's no strong reason to expect those formulas transfer as-is, so their failing to help isn't strong evidence against the underlying microstructure phenomena, just against naive porting. If you ever revisit M3/M8 (OFI, Hawkes) you'd want depth/tick data from the actual venue, not just the formula.

Every formula must have a **binary translation** (logit shift or `ΔEV`, not price target; incorporate `fee(p)=0.07·p·(1-p)` and `breakeven=p+fee`; handle TWAP settlement) before scoring. Tag `NAIVE_PORT` if only spot equation was scored.

## How to run

Single step (resumes from max step in `research/rlenv/OBSERVATIONS.jsonl` + `lifecycle.json`):
```
.venv/bin/python research/rlenv/loop_formula.py
```

Manual sweep helper:
```
.venv/bin/python research/rlenv/evaluator.py   # 24-cell baseline (w=0)
```

## Files

- Queue: `research/rlenv/paper_queue.yaml` (human-editable, single source).
- Harness: `research/rlenv/harness.py` (`Lifecycle`, `Budget`, atomic `lifecycle.json`).
- Loop: `research/rlenv/loop_formula.py` (`run_step`, queue-driven `main`, `guard.verify`, `NaN→null` sanitized JSON).
- Chunks: `research/rlenv/arxiv_chunk.py` (`next_chunk`, `load_queue`, `papers_target/helpful_target`).
- Formulae: `research/rlenv/formulae/*.py` (OFI, lambda, VPIN filter, Amihud regime, Hawkes, micro-price, Q-Hour).
- Scorer: `research/rlenv/evaluator.py` (24-cell, Holm k=24, fallback bootstrap).
- Buckets: `research/rlenv/buckets.py` (`R24_CUTS`, `vol_label`, `session_label`).
- Logs: `research/rlenv/OBSERVATIONS.jsonl` (append-only, fsync, strict JSON), `research/rlenv/lifecycle.json`.

## Sample thickening

Historical bridge has only 4 resolved dates (Apr 6-9, ~530 gate-passed trades); `N≥150` per bucket will usually fail until live collector thickens to ~7-12 days (active since 2026-08-27). Loop logs `RESET` honestly on thin sample; depth-gated papers auto-`DEFERRED` and become runnable after `depth20` accumulation without code change.

## Branch rule

Do not run the loop alongside Branches A/B/C in the same process. Loop OR branch, not both. Collector stays active but uncoupled.
