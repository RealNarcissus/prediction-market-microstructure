# Round 34: split sensitivity + residual attribution (v2_ewma)

## Split sensitivity (gate EV at different temporal cuts)

| split (UTC) | train n | test n | gated | EV/trade | win rate |
|---|---|---|---|---|---|
| Aug 29 12:00 | 37,594 | 59,999 | 23,945 | +6.81c | 0.504 |
| Aug 30 00:00 | 48,135 | 49,458 | 20,529 | +6.94c | 0.481 |
| Aug 31 00:00 | 66,911 | 30,682 | 12,828 | +8.10c | 0.504 |

## Extreme-band residual attribution (n=23,492; lambda=1.85)

### By remaining time d (minutes to close)

- final-60s: n=3,052 mean resid -0.0062
- d>=60s: n=20,440 mean resid -0.0097

### By asset
- BTC: n=6,855 mean resid -0.0136
- ETH: n=8,418 mean resid -0.0034
- SOL: n=8,219 mean resid -0.0116

### By horizon
- 300s: n=6,061 mean resid -0.0021
- 900s: n=17,431 mean resid -0.0117

Reading: a residual that is stable across d/asset/hz points to a
scale factor (strike basis or fat tails); concentration in one
bucket points to a localized mechanism.