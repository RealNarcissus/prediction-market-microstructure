# Phase B Report — Official Label Training

First training run using OFFICIAL Jupiter resolutions instead of
TWAP proxies. Entry priced at ACTUAL Jupiter asks.

| asset | hz | matched | train | eval | official acc | avg ask | mean EV | +EV count |
|---|---|---|---|---|---|---|---|---|

## Key questions this answers:

1. Does the model trained on official outcomes beat random?
2. Is the model's edge sufficient to overcome Jupiter fees?
3. How does official-label training compare to TWAP-proxy training?

## Interpretation guide:
- If official-label accuracy ≈ TWAP-proxy accuracy → basis risk is low
- If mean EV > 0 at market asks → strategy has live edge
- If neither → wait for more data or pivot approach
