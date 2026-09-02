# Collector data integrity verification
**Verdict: PASS**

## quotes: 316,990 rows
- duplicate (ts_ms, market_id, side): 0
- markets with non-monotonic ts: 0
- crossed/invalid book rows: 7339 (2.315%)
- markets: 7,415
- top max inter-quote gaps:
  - POLY-3801318-0: 813s WARN
  - POLY-3809040-0: 791s WARN
  - POLY-3819811-0: 733s WARN
  - POLY-3785175-0: 722s WARN
  - POLY-3813867-0: 705s WARN
## resolutions: 13,468 rows
- duplicate market rows: 0
- outcome outside (up,down): 0
## twap tape: 26,417 rows across 12 files
- duplicate (observed_at, symbol, window): 0
- non-monotonic series: 0
- value out of (0, 1e7): 0