# Settlement inspection: oracle vs proxies

Official Jupiter resolutions vs Binance-spot-derived labels.

| asset | horizon | n | TWAP-proxy agree | endpoint agree | twap!=endpoint |
|---|---|---|---|---|---|
| BTC | 300s | 144 | 117/144 (81%) | 126/144 (88%) | 21 |
| BTC | 900s | 70 | 62/70 (89%) | 68/70 (97%) | 8 |
| ETH | 300s | 151 | 128/151 (85%) | 135/151 (89%) | 17 |
| ETH | 900s | 68 | 59/68 (87%) | 65/68 (96%) | 6 |
| SOL | 300s | 150 | 124/150 (83%) | 138/150 (92%) | 16 |
| SOL | 900s | 63 | 54/63 (86%) | 60/63 (95%) | 8 |

**Overall: TWAP-proxy agrees with the oracle 544/646 (84.2%); endpoint 592/646 (91.6%).**

Basis risk = 1 - agreement. Every disagreement point is edge lost
or mislabeled training data for TWAP-proxy models; if the endpoint
rate is materially lower, the TWAP approximation is earning its keep.
