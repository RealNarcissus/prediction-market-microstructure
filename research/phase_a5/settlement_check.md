# Settlement inspection: oracle vs proxies

Official Jupiter resolutions vs Binance-spot-derived labels.

| asset | horizon | n | TWAP-proxy agree | endpoint agree | twap!=endpoint |
|---|---|---|---|---|---|
| BTC | 300s | 40 | 33/40 (82%) | 32/40 (80%) | 7 |
| BTC | 900s | 15 | 13/15 (87%) | 13/15 (87%) | 2 |
| ETH | 300s | 16 | 13/16 (81%) | 15/16 (94%) | 2 |
| ETH | 900s | 15 | 15/15 (100%) | 15/15 (100%) | 0 |
| SOL | 300s | 16 | 13/16 (81%) | 13/16 (81%) | 0 |
| SOL | 900s | 11 | 10/11 (91%) | 10/11 (91%) | 0 |

**Overall: TWAP-proxy agrees with the oracle 97/113 (85.8%); endpoint 98/113 (86.7%).**

Basis risk = 1 - agreement. Every disagreement point is edge lost
or mislabeled training data for TWAP-proxy models; if the endpoint
rate is materially lower, the TWAP approximation is earning its keep.
