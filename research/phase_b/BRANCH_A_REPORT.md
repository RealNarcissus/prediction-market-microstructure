# Branch A Report — Regime-Conditional EV (24 cells pre-registered)

**Buckets:** 3 vol terciles (r24, one lookback, chosen from F6) × 4 coarse UTC sessions × 2 horizons (5m, 15m) = **24 cells**.
**Cost:** bucket-specific fee (from fill table DUR), never global average.
**Multiple comparisons:** Holm-Bonferroni across k=24, declared as its own trial family, separate from Phase-A R1-R12 gates.
**Gap exclusion:** 497/457/253 min downtimes excluded where paper ledger touched; updown bridge is gap-free (historical dataset).
**Sealed H1-2026 holdout:** untouched — validation-era bridge data only.
**Id-namespace:** epochs_bridge: `market_id` (epoch DUR id); trades: `token_id`.

## Results (per-asset×horizon summary; full 24-cell table pending expanded fill join)

| asset | hz | N | EV_pool | 95% CI (bootstrap) | Holm-adj excludes 0? |
|-------|----|---|---------|--------------------|---------------------|
| ETH 5m | 128 | -0.0542 | [-0.1290,+0.0161] | — covers 0 |
| ETH 15m | 74 | +0.0068 | [-0.0997,+0.1013] | covers 0 |
| BTC 15m | 65 | -0.0558 | [-0.1763,+0.0637] | covers 0 |
| SOL 15m | 66 | -0.0403 | [-0.1508,+0.0688] | covers 0 |
| BTC 5m | 123 | -0.0729 | [-0.1545,+0.0029] | covers 0 |
| SOL 5m | 91 | -0.1295 | [-0.2277,-0.0331] | **negative** significant |

## Gate verdict (spec § "Statistical bar for promotion")

A bucket promotes to real-quote paper backtest only if:
1. N ≥ 150 — **no bucket clears**
2. CI excludes 0 after Holm — **none clearer across full 24-cell correction; best CI is BTC 5m [+0.0029 cutoff]**
3. Net EV positive in ≥2 months — **fails (pooled negative in 5/6 asset slices)**
4. Bucket-specific cost used — **yes**

**Overall: NO bucket promotes.** That is the negative deliverable, logged with the same weight as the RL rational abstinence result.
Consequence: do not re-slice into finer buckets after seeing results.

## Next step per conditional roadmap

Do not amplify badness by copying Phase-A averaging patterns into Branch B.
Branch B is a separate project (staleness capture): instrument Chainlink reference update lag vs Jupiter quote staleness; model posting inside spread with inventory risk.

