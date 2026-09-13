# BOCPD flow-bias detector — BTCUSDT

minutes analyzed: 792  (1789243200000 .. 1789325580000)
bias mean +0.0671  sd 0.2961  (taker-buy share minus 0.5, per 1m bar)
hazard 0.004  (prior mean run ~250 min)
breaks detected (P(run==0) > 0.5): 224
mean run length (posterior): 73.5 min

| break index | ts (UTC) | P(break) |
|---|---|---|
| 560 | 2026-09-13 15:02 | 0.644 |
| 562 | 2026-09-13 15:04 | 0.784 |
| 563 | 2026-09-13 15:05 | 0.859 |
| 564 | 2026-09-13 15:06 | 0.963 |
| 567 | 2026-09-13 15:09 | 0.532 |
| 568 | 2026-09-13 15:10 | 0.515 |
| 569 | 2026-09-13 15:11 | 0.559 |
| 570 | 2026-09-13 15:12 | 0.516 |
| 572 | 2026-09-13 15:14 | 0.602 |
| 573 | 2026-09-13 15:15 | 0.596 |
| 574 | 2026-09-13 15:16 | 0.577 |
| 575 | 2026-09-13 15:17 | 0.535 |
| 577 | 2026-09-13 15:19 | 0.537 |
| 578 | 2026-09-13 15:20 | 0.590 |
| 579 | 2026-09-13 15:21 | 0.589 |
| 580 | 2026-09-13 15:22 | 0.554 |
| 581 | 2026-09-13 15:23 | 0.600 |
| 582 | 2026-09-13 15:24 | 0.612 |
| 583 | 2026-09-13 15:25 | 0.609 |
| 584 | 2026-09-13 15:26 | 0.598 |

## pre/post-break bias contrast (first 10 breaks, +-60 min window)
- break@560: pre +0.1298 -> post -0.0437 (delta -0.1736)
- break@562: pre +0.1122 -> post -0.0348 (delta -0.1470)
- break@563: pre +0.1003 -> post -0.0281 (delta -0.1284)
- break@564: pre +0.0958 -> post -0.0302 (delta -0.1260)
- break@567: pre +0.0924 -> post -0.0336 (delta -0.1260)
- break@568: pre +0.0803 -> post -0.0350 (delta -0.1153)
- break@569: pre +0.0804 -> post -0.0355 (delta -0.1159)
- break@570: pre +0.0691 -> post -0.0249 (delta -0.0940)
- break@572: pre +0.0530 -> post -0.0137 (delta -0.0667)
- break@573: pre +0.0538 -> post -0.0236 (delta -0.0774)

NEXT (bakeoff discipline, round-208): score conditional gate EV
inside vs outside break windows PROSPECTIVELY before any gate use.
