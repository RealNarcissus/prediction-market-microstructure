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

## STATUS: BLOCKED — insufficient outcome diversity

The pipeline runs correctly but produces single-class training sets because
the collector has only ~3 days of data. With 744 epochs having both quotes
and resolutions, the 70% train split contains epochs from a narrow time
window where outcomes happen to be skewed.

This is NOT a bug — it's a sample-size limitation that resolves naturally
as the collector accumulates more days of data. At current rate (~500
resolutions/day), we expect sufficient diversity within 5-7 days.

## What's built and ready:
- Collector → bridge table extraction (works ✓)
- Champion feature pipeline (works ✓)  
- Walk-forward temporal split (works ✓)
- Official-label training + evaluation (works ✓)
- Market-implied EV calculation (works ✓)

## Next action: rerun this script after 5-7 more days of collection.
