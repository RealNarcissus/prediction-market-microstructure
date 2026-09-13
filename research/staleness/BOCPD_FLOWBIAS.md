# BOCPD flow-bias detector — BTCUSDT

minutes analyzed: 785  (1789246800000 .. 1789328760000)
bias mean +0.0673  sd 0.2930  (taker-buy share minus 0.5, per 1m bar)
hazard 0.004  (prior mean run ~250 min)
breaks detected (P(run==0) > 0.5): 277
mean run length (posterior): 75.6 min

| break index | ts (UTC) | P(break) |
|---|---|---|
| 500 | 2026-09-13 15:02 | 0.645 |
| 502 | 2026-09-13 15:04 | 0.786 |
| 503 | 2026-09-13 15:05 | 0.860 |
| 504 | 2026-09-13 15:06 | 0.963 |
| 507 | 2026-09-13 15:09 | 0.530 |
| 508 | 2026-09-13 15:10 | 0.513 |
| 509 | 2026-09-13 15:11 | 0.557 |
| 510 | 2026-09-13 15:12 | 0.513 |
| 512 | 2026-09-13 15:14 | 0.600 |
| 513 | 2026-09-13 15:15 | 0.593 |
| 514 | 2026-09-13 15:16 | 0.574 |
| 515 | 2026-09-13 15:17 | 0.531 |
| 517 | 2026-09-13 15:19 | 0.532 |
| 518 | 2026-09-13 15:20 | 0.586 |
| 519 | 2026-09-13 15:21 | 0.585 |
| 520 | 2026-09-13 15:22 | 0.550 |
| 521 | 2026-09-13 15:23 | 0.596 |
| 522 | 2026-09-13 15:24 | 0.608 |
| 523 | 2026-09-13 15:25 | 0.605 |
| 524 | 2026-09-13 15:26 | 0.594 |

## pre/post-break bias contrast (first 10 breaks, +-60 min window)
- break@500: pre +0.1298 -> post -0.0437 (delta -0.1736)
- break@502: pre +0.1122 -> post -0.0348 (delta -0.1470)
- break@503: pre +0.1003 -> post -0.0281 (delta -0.1284)
- break@504: pre +0.0958 -> post -0.0302 (delta -0.1260)
- break@507: pre +0.0924 -> post -0.0336 (delta -0.1260)
- break@508: pre +0.0803 -> post -0.0350 (delta -0.1153)
- break@509: pre +0.0804 -> post -0.0355 (delta -0.1159)
- break@510: pre +0.0691 -> post -0.0249 (delta -0.0940)
- break@512: pre +0.0530 -> post -0.0137 (delta -0.0667)
- break@513: pre +0.0538 -> post -0.0236 (delta -0.0774)

NEXT (bakeoff discipline, round-208): score conditional gate EV
inside vs outside break windows PROSPECTIVELY before any gate use.
