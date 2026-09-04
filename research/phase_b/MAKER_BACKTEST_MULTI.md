# Maker-entry backtest MULTI (official outcomes, real quote fills)

| month | asset | hz | delta | fills | win | EV/trade | PnL |
|---|---|---|---|---|---|---|---|
| 2026-04 | BTC | 15m | 0.00 | 33 | 63.6% | -0.0570 | -1.88 |
| 2026-04 | BTC | 15m | 0.02 | 32 | 62.5% | -0.0544 | -1.74 |
| 2026-04 | BTC | 5m | 0.00 | 62 | 66.1% | -0.0859 | -5.33 |
| 2026-04 | BTC | 5m | 0.02 | 61 | 67.2% | -0.0596 | -3.64 |
| 2026-04 | ETH | 15m | 0.00 | 38 | 68.4% | -0.0161 | -0.61 |
| 2026-04 | ETH | 15m | 0.02 | 36 | 72.2% | +0.0310 | +1.12 |
| 2026-04 | ETH | 5m | 0.00 | 65 | 75.4% | -0.0547 | -3.56 |
| 2026-04 | ETH | 5m | 0.02 | 63 | 74.6% | -0.0537 | -3.38 |
| 2026-04 | SOL | 15m | 0.00 | 35 | 62.9% | -0.0470 | -1.64 |
| 2026-04 | SOL | 15m | 0.02 | 31 | 64.5% | -0.0328 | -1.02 |
| 2026-04 | SOL | 5m | 0.00 | 46 | 67.4% | -0.1424 | -6.55 |
| 2026-04 | SOL | 5m | 0.02 | 45 | 68.9% | -0.1163 | -5.23 |

**By delta (all months/assets/horizons):**
- delta 0.00: fills 279, win 68.1%, EV -0.0702, total PnL -19.57
- delta 0.02: fills 268, win 69.0%, EV -0.0519, total PnL -13.90

## CONCLUSION (Option 1 hardening, 2026-08-26): edge does NOT generalize

The March 2026 positive EV (+6.6c/trade) **did not survive** the
multi-month/multi-asset expansion. April 2026: 279+268 fills across
3 assets x 2 horizons x 2 deltas — win rates 62–75% yet EV NEGATIVE in
11 of 12 cells. Buying favorites that dip through our level means paying
0.60–0.80 for outcomes realized ~68% of the time: the residual direction
signal does not cover the adverse-selection cost of resting bids.

Combined record of the naive maker strategy: ~2,127 fills,
EV ≈ −0.006/trade overall — statistically indistinguishable from zero,
practically not tradable.

Implications:
1. The simple "rest bid below fair" strategy family is dead on current
   evidence. Do not pilot it.
2. Remaining live hypotheses require either (a) much stronger conditional
   entry selection (only extreme-confidence epochs), (b) queue-aware
   modeling where passive fills are earned rather than assumed, or
   (c) the Jupiter-specific staleness capture that motivated the project
   originally — testable only when our own collector's quote history
   matures against its own resolutions.
3. Methodology note: the trades-print fill proxy (March) and the
   price-series crossing proxy (April) disagree in sign — fill-model
   sensitivity dominates this strategy class. Any future positive
   backtest must show robustness ACROSS both fill models before it
   counts.
