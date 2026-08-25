# Maker-entry backtest (BTC, Mar 2026, official outcomes)

| horizon | delta | decided | theta-skip | filled | no-map | unfilled | win rate | EV/trade | total PnL |
|---|---|---|---|---|---|---|---|---|---|
| 5m | 0.00 | 4317 | 3073 | 1012 | 0 | 232 | 0.4822 | +0.0662 | +67.02 |
| 5m | 0.01 | 4317 | 3073 | 1017 | 0 | 227 | 0.4838 | +0.0658 | +66.87 |
| 5m | 0.03 | 4317 | 3073 | 1027 | 0 | 217 | 0.483 | +0.0614 | +63.03 |
| 15m | 0.00 | 2159 | 1197 | 834 | 0 | 128 | 0.5036 | +0.0657 | +54.76 |
| 15m | 0.01 | 2159 | 1197 | 844 | 0 | 118 | 0.5047 | +0.0632 | +53.38 |
| 15m | 0.03 | 2159 | 1197 | 856 | 0 | 106 | 0.507 | +0.0588 | +50.30 |

## Interpretation & caveats (2026-08-25)

- **Positive net EV on real data**: +6.6c/trade (5m) and +6.6c (15m) over
  13 days of March 2026, ~1,850 combined fills, fees exact (maker = 0),
  outcomes = official Polymarket resolutions, predictions strictly
  out-of-sample (trained through Feb 28 on Herdr perp TWAP windows,
  applied to March spot windows).
- Maker logic: bids rest BELOW fair (fair - delta); they fill when flow
  prints through our level — i.e., fills are biased toward moments the
  market moves against us (adverse selection INCLUDED in these numbers)
  — and the champion's direction signal still clears costs.
- Caveats before extrapolating: (1) queue position not modeled — real
  fill probability at a given print is <= simulated; (2) partial-fill /
  size ignored (fills require >= 1 contract print through the level);
  (3) one month, one regime; (4) execution assumes our own order visible
  to the midpoint matcher like native Polymarket orders — via Jupiter the
  routing/fee path differs and must be re-derived.
- Debug trail: initial zero-fills were two stacked bugs — polars
  group_by returning tuple keys (silent lookup misses) and missing
  trades day-files from a cwd-mishap download. Both fixed; the tape
  inspection (inspect_epoch.py) confirmed simultaneous complementary
  midpoint-match prints (winner 0.400 / loser 0.600 same second).
