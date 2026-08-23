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
| 6 | s005_lgbm_plus_imbalance | +0.0327 | +0.0518 | +0.042270 | KEEP |  | b29645f |
| 7 | s006_lgbm_regularized | +0.0274 | +0.0480 | +0.037700 | reset |  |  |
| 8 | s007_lgbm_capacity_up | +0.0328 | +0.0467 | +0.039735 | reset |  |  |
| 9 | s008_lgbm_lr005 | +0.0329 | +0.0479 | +0.040364 | reset |  |  |
| 10 | s009_lgbm_imbalance_split | +0.0316 | +0.0485 | +0.040067 | reset |  |  |
| 11 | s010_lgbm_activity_z | +0.0300 | +0.0473 | +0.038624 | reset |  |  |
| 12 | s011_lgbm_bar_position | +0.0309 | +0.0576 | +0.044257 | KEEP | **champion** | 8384ec9 |
