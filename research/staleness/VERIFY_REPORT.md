# Collector data integrity verification
**Verdict: PASS**

## quotes: 315,026 rows
- duplicate (ts_ms, market_id, side): 0
- markets with non-monotonic ts: 0
- crossed/invalid book rows: 7334 (2.328%)
- markets: 7,362
- top max inter-quote gaps:
  - POLY-3801318-0: 813s WARN
  - POLY-3809040-0: 791s WARN
  - POLY-3819811-0: 733s WARN
  - POLY-3785175-0: 722s WARN
  - POLY-3813867-0: 705s WARN
## resolutions: 13,368 rows
- duplicate market rows: 0
- outcome outside (up,down): 0
## twap tape: 10,050 rows across 4 files
- duplicate (observed_at, symbol, window): 0
- non-monotonic series: 0
- value out of (0, 1e7): 0