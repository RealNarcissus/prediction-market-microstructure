# Settlement inspection: oracle vs proxies

Official Jupiter resolutions vs Binance-spot-derived labels.

| asset | horizon | n | TWAP-proxy agree | endpoint agree | twap!=endpoint |
|---|---|---|---|---|---|
| BTC | 300s | 24 | 19/24 (79%) | 19/24 (79%) | 6 |
| BTC | 900s | 8 | 6/8 (75%) | 7/8 (88%) | 1 |
| ETH | 300s | 5 | 4/5 (80%) | 4/5 (80%) | 0 |
| ETH | 900s | 9 | 9/9 (100%) | 9/9 (100%) | 0 |
| SOL | 300s | 6 | 5/6 (83%) | 5/6 (83%) | 0 |
| SOL | 900s | 6 | 5/6 (83%) | 5/6 (83%) | 0 |

**Overall: TWAP-proxy agrees with the oracle 48/58 (82.8%); endpoint 49/58 (84.5%).**

Basis risk = 1 - agreement. Every disagreement point is edge lost
or mislabeled training data for TWAP-proxy models; if the endpoint
rate is materially lower, the TWAP approximation is earning its keep.
