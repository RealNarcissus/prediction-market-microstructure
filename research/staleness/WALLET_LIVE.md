# Live Paper Wallet — $5 Controlled Staleness Test

Started: 2026-09-01 (service `quantbtc-wallet`), trading from **2026-09-02 00:00 UTC** (pre-registered LIVE_START).

Rules (frozen — see `research/staleness/live_wallet.py` docstring):
- $5.00 allowance per UTC day, 1 contract per trade, ONE concurrent position, one entry per epoch
- Entry: calibrated gap `fair_cal - ask > fee(ask)`, calibration isotonic frozen on 94,357 quotes before launch
- Hold to settlement against official resolutions; unresolved 2h past close marked unresolved (no PnL)
- Quote freshness 30s; crash-safe (open positions and day wallet restored from ledger)
- Entry at recorded collector-arrival ask — documented upper bound; live fills will be worse

Decision gate: live per-contract EV day-block CI after >=2 weeks, all-weeks-positive, before any capital discussion.

Daily status appended below by the daemon at UTC day rollover.

## 2026-09-02 00:00 UTC — wallet status

| entry day | trades | wins | realized PnL |
|---|---|---|---|
| **total** | 0 | 0 | **+0.00** |


## 2026-09-03 05:37 UTC — wallet status

| entry day | trades | wins | realized PnL |
|---|---|---|---|
| 2026-09-02 | 68 | 36 | -2.73 |
| **total** | 68 | 36 | **-2.73** |


## 2026-09-04 02:15 UTC — wallet status

| entry day | trades | wins | realized PnL |
|---|---|---|---|
| 2026-09-02 | 68 | 36 | -2.73 |
| 2026-09-03 | 23 | 7 | -5.00 |
| **total** | 91 | 43 | **-7.73** |


## 2026-09-04 06:33 UTC — wallet status

| entry day | trades | wins | realized PnL |
|---|---|---|---|
| 2026-09-02 | 68 | 36 | -2.73 |
| 2026-09-03 | 23 | 7 | -5.00 |
| 2026-09-04 | 8 | 6 | +1.38 |
| **total** | 99 | 49 | **-6.35** |

