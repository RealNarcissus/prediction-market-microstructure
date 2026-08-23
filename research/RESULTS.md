# Autoresearch results ledger

Primary metric: mean pooled walk-forward validation MCC (5m, 15m).
Every trial here counts toward deflated final statistics.

| # | strategy | 5m MCC | 15m MCC | primary | kept | champion | commit |
|---|---|---|---|---|---|---|---|
| 1 | s000_r4_baseline | +0.0236 | +0.0418 | +0.032710 | KEEP |  | 27938e7 |
| 2 | s001_r4_plus_imbalance | +0.0228 | +0.0452 | +0.033983 | KEEP |  | c6edacb |
| 3 | s002_lgbm_base | +0.0287 | +0.0503 | +0.039501 | KEEP | **champion** | 4be9b1d |
