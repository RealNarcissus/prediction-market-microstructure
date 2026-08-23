# Phase A.5 — TWAP-label reality check & EV-at-open

## 5m

- endpoint-vs-TWAP label disagreement: **13.1%** (windows where what Phase A trained on != what Jupiter pays)
- champion MCC on TWAP labels (walk-forward val 2025): **+0.0337**
- fee per contract at 0.50 entry: $0.0200

| strategy | trades | win rate | EV/trade | 95% CI |
|---|---|---|---|---|
| always-up (theta=None baseline) | 105119 | 0.497 | -0.0227 | [-0.0256, -0.0197] |
| model-sign | 105119 | 0.517 | -0.0031 | [-0.0061, -0.0002] |
| model-sign theta=0.02 | 66161 | 0.526 | +0.0058 | [+0.0021, +0.0095] |
| model-sign theta=0.05 | 26239 | 0.546 | +0.0264 | [+0.0203, +0.0326] |
| model-sign theta=0.10 | 3858 | 0.568 | +0.0484 | [+0.0328, +0.0643] |

## 15m

- endpoint-vs-TWAP label disagreement: **15.1%** (windows where what Phase A trained on != what Jupiter pays)
- champion MCC on TWAP labels (walk-forward val 2025): **+0.0646**
- fee per contract at 0.50 entry: $0.0200

| strategy | trades | win rate | EV/trade | 95% CI |
|---|---|---|---|---|
| always-up (theta=None baseline) | 35039 | 0.498 | -0.0225 | [-0.0274, -0.0176] |
| model-sign | 35039 | 0.532 | +0.0123 | [+0.0072, +0.0174] |
| model-sign theta=0.02 | 26792 | 0.540 | +0.0204 | [+0.0146, +0.0263] |
| model-sign theta=0.05 | 15912 | 0.553 | +0.0327 | [+0.0256, +0.0399] |
| model-sign theta=0.10 | 5239 | 0.576 | +0.0557 | [+0.0423, +0.0689] |

