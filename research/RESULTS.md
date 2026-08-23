# Autoresearch results ledger

Primary metric: mean pooled walk-forward validation MCC (5m, 15m).
Every trial here counts toward deflated final statistics.

| # | strategy | 5m MCC | 15m MCC | primary | kept | champion | commit |
|---|---|---|---|---|---|---|---|
| 1 | s000_r4_baseline | +0.0236 | +0.0418 | +0.032710 | KEEP |  | 27938e7 |
| 2 | s001_r4_plus_imbalance | +0.0228 | +0.0452 | +0.033983 | KEEP |  | c6edacb |
| 3 | s002_lgbm_base | +0.0287 | +0.0503 | +0.039501 | KEEP |  | 4be9b1d |
| 4 | s004_r4_longer_lookbacks_tod | +0.0229 | +0.0369 | +0.029905 | reset |  |  |
| 5 | s003_r4_plus_realized_vol | +0.0227 | +0.0436 | +0.033163 | reset |  |  |
| 6 | s005_lgbm_plus_imbalance | +0.0327 | +0.0518 | +0.042270 | KEEP | **champion** | b29645f |
