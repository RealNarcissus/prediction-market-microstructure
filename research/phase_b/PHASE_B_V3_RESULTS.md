# Phase B v3 — Official-Label Training Results

Trained on updown dataset official resolutions (~6k epochs Feb–Aug 2026)
with full-year Binance Vision klines for features.
Temporal split: train ≤ Jun 30, eval Jul–Aug.

| asset | horizon | total | train | eval | accuracy | mean p |
|---|---|---|---|---|---|---|
| BTC | 15ms | 205 | 143 | 62 | 50.0% | 0.510 |
| BTC | 5ms | 616 | 431 | 185 | 51.3% | 0.503 |
| ETH | 15ms | 205 | 143 | 62 | 46.8% | 0.503 |
| ETH | 5ms | 616 | 431 | 185 | 50.8% | 0.503 |
| SOL | 15ms | 205 | 143 | 62 | 50.0% | 0.538 |
| SOL | 5ms | 616 | 431 | 185 | 46.0% | 0.534 |
