# BOCPD flow-bias detector — BTCUSDT

minutes analyzed: 19,698  (1787490840000 .. 1789328940000)
bias mean +0.0096  sd 0.2447  (taker-buy share minus 0.5, per 1m bar)
hazard 0.004  (prior mean run ~250 min)
breaks detected (P(run==0) > 0.5): 4881
mean run length (posterior): 12.1 min

| break index | ts (UTC) | P(break) |
|---|---|---|
| 499 | 2026-08-23 22:42 | 0.942 |
| 500 | 2026-08-23 22:43 | 0.939 |
| 501 | 2026-08-23 22:44 | 0.944 |
| 502 | 2026-08-23 22:45 | 0.944 |
| 503 | 2026-08-23 22:46 | 0.944 |
| 504 | 2026-08-23 22:47 | 0.943 |
| 505 | 2026-08-23 22:48 | 0.914 |
| 506 | 2026-08-23 22:49 | 0.944 |
| 507 | 2026-08-23 22:50 | 0.944 |
| 508 | 2026-08-23 22:51 | 0.941 |
| 509 | 2026-08-23 22:52 | 0.944 |
| 510 | 2026-08-23 22:53 | 0.945 |
| 511 | 2026-08-23 22:54 | 0.944 |
| 512 | 2026-08-23 22:55 | 0.944 |
| 513 | 2026-08-23 22:56 | 0.943 |
| 514 | 2026-08-23 22:57 | 0.942 |
| 515 | 2026-08-23 22:58 | 0.945 |
| 516 | 2026-08-23 22:59 | 0.932 |
| 517 | 2026-08-23 23:00 | 0.889 |
| 518 | 2026-08-23 23:01 | 0.945 |

## pre/post-break bias contrast (first 10 breaks, +-60 min window)
- break@499: pre +0.0540 -> post -0.0069 (delta -0.0609)
- break@500: pre +0.0577 -> post -0.0155 (delta -0.0732)
- break@501: pre +0.0595 -> post -0.0204 (delta -0.0800)
- break@502: pre +0.0589 -> post -0.0237 (delta -0.0826)
- break@503: pre +0.0527 -> post -0.0136 (delta -0.0663)
- break@504: pre +0.0510 -> post -0.0118 (delta -0.0629)
- break@505: pre +0.0522 -> post -0.0176 (delta -0.0698)
- break@506: pre +0.0464 -> post -0.0169 (delta -0.0633)
- break@507: pre +0.0387 -> post -0.0149 (delta -0.0536)
- break@508: pre +0.0344 -> post -0.0139 (delta -0.0483)

NEXT (bakeoff discipline, round-208): score conditional gate EV
inside vs outside break windows PROSPECTIVELY before any gate use.
