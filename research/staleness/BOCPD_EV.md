# Conditional gate EV around BOCPD flow-regime breaks

detector: hazard 0.040 (data-driven, round-234); snapshot 19,698 min; breaks in window: 4,502
trades scored: 631 settled v2 in snapshot span
post-break cohort (break within 25 min before entry): n=385  EV -4.10c  win 0.392
stable-flow cohort (no break in window): n=246  EV -3.95c  win 0.423
EV delta (post-break minus stable): -0.16c

## HONEST CAVEATS
1. EXPLORATORY IN-SAMPLE: detector params were tuned on this same
   history. Not prospective. Prospective = freeze the detector,
   score only trades that settle afterwards.
2. Flow bias is BTC-only; trades span BTC/ETH/SOL (cross-asset
   leakage in both cohorts).
3. Cohort split is by entry timing only — no fee/latency change.

