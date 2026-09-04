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
| 12 | s011_lgbm_bar_position | +0.0309 | +0.0576 | +0.044257 | KEEP |  | 8384ec9 |
| 13 | s012_ensemble_lgbm_logit | +0.0286 | +0.0472 | +0.037895 | reset |  |  |
| 14 | s013_lgbm_isotonic | +0.0298 | +0.0492 | +0.039505 | reset |  |  |
| 15 | **INVALID** s014_lgbm_position_history | +0.5621 | +0.5804 | +0.571279 | reset |  | f1b21fe |
| 16 | s015_lgbm_range_dynamics | +0.0306 | +0.0484 | +0.039490 | reset |  |  |
| 17 | s016_lgbm_wick_asymmetry | +0.0329 | +0.0514 | +0.042138 | reset |  |  |
| 18 | s017_lgbm_open_gap | +0.0330 | +0.0547 | +0.043861 | reset |  |  |
| 19 | s018_lgbm_weighted_imbalance | +0.0326 | +0.0583 | +0.045434 | reset |  |  |
| 20 | s019_lgbm_imb_split_with_pos | +0.0311 | +0.0568 | +0.043932 | reset |  |  |
| 21 | s015_lgbm_range_dynamics | +0.0306 | +0.0484 | +0.039490 | reset |  |  |
| 22 | s016_lgbm_wick_asymmetry | +0.0329 | +0.0514 | +0.042138 | reset |  |  |
| 23 | s017_lgbm_open_gap | +0.0330 | +0.0547 | +0.043861 | reset |  |  |
| 24 | s018_lgbm_weighted_imbalance | +0.0326 | +0.0583 | +0.045434 | KEEP |  | 3f1f0ec |
| 25 | s019_lgbm_imb_split_with_pos | +0.0311 | +0.0568 | +0.043932 | reset |  |  |
| 26 | s020_lgbm_causal_streak | +0.0314 | +0.0582 | +0.044813 | reset |  |  |
| 27 | s021_lgbm_s018_plus_causal_streak | +0.0321 | +0.0592 | +0.045680 | KEEP |  | aadb06b |
| 28 | s022_lgbm_pos_and_imb_streaks | +0.0307 | +0.0580 | +0.044342 | reset |  |  |
| 29 | s023_lgbm_pos_lag23 | +0.0319 | +0.0609 | +0.046396 | KEEP | **champion** | 2ba00a4 |
