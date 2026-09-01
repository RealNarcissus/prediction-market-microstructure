# Staleness Audit — Live Collector Data (Branch C precursor)

Generated: 2026-09-01T19:25:53.799219+00:00

Data: collector.db quotes joined with official resolutions; fair = CLT Asian digital on Binance 1m klines (strike = epoch-open 1m open, sigma from r24).
Caveats: quote timestamps are collector-arrival times (measured staleness = UPPER bound on venue staleness); BTC orderbooks polled first each cycle (cross-asset lag comparisons carry sampler bias); Binance-vs-Chainlink basis noise inflates |gap| symmetrically — a NEGATIVE EV result is robust, a POSITIVE one needs the resolution-based win rate to confirm.

## 1. How far do quotes sit from model fair value?

| asset | hz | N quotes | median \|gap\| | p90 \|gap\| | stale>fee | stale>2fee |
|---|---|---|---|---|---|---|
| ETH | 900s | 20397 | 0.2950 | 0.5350 | 100.0% | 100.0% |
| SOL | 300s | 17001 | 0.2750 | 0.6150 | 99.7% | 99.5% |
| ETH | 300s | 15838 | 0.2850 | 0.6150 | 99.9% | 99.8% |
| SOL | 900s | 19912 | 0.2850 | 0.5350 | 99.9% | 99.9% |
| BTC | 300s | 5729 | 0.2650 | 0.6170 | 99.9% | 99.8% |
| BTC | 900s | 15480 | 0.2550 | 0.5350 | 100.0% | 99.9% |

## 2. Taker rule 'buy yes when fair - ask > fee' vs official resolutions

**fee=0.07**: N=46181, win rate 73.5% (breakeven needs >50.0% avg depending on avg ask), EV/trade +0.0190, day-block 95% CI [-0.0094, +0.0441], total PnL +876.23

  Per-day EV: 2026-08-23: +0.1190 (n=109), 2026-08-24: +0.0134 (n=34), 2026-08-25: -0.0234 (n=4436), 2026-08-26: -0.0226 (n=1710), 2026-08-27: +0.0093 (n=3889), 2026-08-28: -0.0017 (n=4878), 2026-08-29: +0.0097 (n=9425), 2026-08-30: +0.0392 (n=8647), 2026-08-31: +0.0765 (n=8731), 2026-09-01: -0.0278 (n=4322)

**fee=0.14 (2x)**: N=46147, win rate 73.5% (breakeven needs >50.0% avg depending on avg ask), EV/trade +0.0191, day-block 95% CI [-0.0093, +0.0442], total PnL +881.96

  Per-day EV: 2026-08-23: +0.1190 (n=109), 2026-08-24: +0.0134 (n=34), 2026-08-25: -0.0233 (n=4435), 2026-08-26: -0.0226 (n=1710), 2026-08-27: +0.0093 (n=3889), 2026-08-28: -0.0019 (n=4872), 2026-08-29: +0.0101 (n=9409), 2026-08-30: +0.0396 (n=8638), 2026-08-31: +0.0764 (n=8730), 2026-09-01: -0.0277 (n=4321)

## 3. Taker EV by asset x horizon (fee=0.07 gate)

| asset | hz | N | win | EV |
|---|---|---|---|---|
| SOL | 300s | 8314 | 73.7% | +0.0250 |
| SOL | 900s | 9659 | 72.6% | -0.0065 |
| ETH | 900s | 10183 | 74.7% | +0.0339 |
| ETH | 300s | 7752 | 73.2% | +0.0287 |
| BTC | 900s | 7498 | 73.3% | +0.0105 |
| BTC | 300s | 2775 | 72.9% | +0.0305 |

## 4. Collector polling cadence per asset (confound documentation)

| asset | hz | markets | quotes | median inter-quote s |
|---|---|---|---|---|
| BTC | 300s | 1265 | 22002 | 0.0 |
| BTC | 900s | 703 | 47280 | 0.0 |
| ETH | 300s | 1797 | 51440 | 0.0 |
| ETH | 900s | 708 | 60338 | 0.0 |
| SOL | 300s | 1858 | 55188 | 0.0 |
| SOL | 900s | 702 | 60222 | 0.0 |

## 5. Cross-asset transmission at BTC move events

- ETH: corr(1m ret, BTC) = 0.848; |ret| baseline 4.8bp vs 16.9bp when BTC moves >=10bp; same-direction 99.4% (n=645 events)
- SOL: corr(1m ret, BTC) = 0.731; |ret| baseline 7.1bp vs 21.5bp when BTC moves >=10bp; same-direction 98.0% (n=645 events)

Transmission premise confirmed if SOL/ETH move materially same-minute with BTC. Venue-side test (do SOL/ETH *quotes* lag BTC quotes on the same shock) is confounded by BTC-first polling order — see caveats; requires interleaved sampling or venue-native timestamps to measure cleanly.
---

## 6. Decomposition (v2) — where does the EV come from?

Scored quotes saved to `research/staleness/scored_quotes.parquet`.

### EV by epoch phase (fee=0.07 gate, 45.8k trades)

| phase | N | avg ask | win | breakeven (ask+fee) | EV/trade |
|---|---|---|---|---|---|
| last 60s | 1,501 | 0.605 | 67.5% | 61.6% | **+0.0594** |
| 60-180s | 11,802 | 0.730 | 76.4% | 73.9% | +0.0251 |
| 180-420s | 16,876 | 0.709 | 73.8% | 72.1% | +0.0175 |
| >420s | 15,658 | 0.688 | 71.0% | 70.1% | +0.0082 |

### EV by gap size

| gap bucket | N | avg ask | win | EV |
|---|---|---|---|---|
| <5pp | 5,954 | 0.962 | 92.8% | −0.0362 |
| 5-10pp | 4,627 | 0.915 | 90.6% | −0.0148 |
| 10-20pp | 7,506 | 0.843 | 84.4% | −0.0080 |
| 20-40pp | 13,809 | 0.696 | 71.5% | +0.0045 |
| >40pp | 13,941 | 0.456 | 55.0% | **+0.0782** |

### Fair calibration among traded quotes (the decisive check)

| fair bucket | N | mean fair | realized win | miscalibration |
|---|---|---|---|---|
| 50-65c | 108 | 0.500 | 0.324 | −0.176 |
| >95c | 45,607 | 0.995 | 0.735 | **−0.260** |

**The model fair is severely overconfident**: quotes our pricer prices at 99.5c win only 73.5% of the time. The minute-bar CLT fair collapses to near-certainty after one moderate minute (5m binary at 50c moves ~5pp per bp; a 10-20bp minute pins any low-variance pricer at 99%+) while the true outcome distribution is much wider (sigma underestimation, 1m-close TWAP vs fine-grained oracle TWAP, Binance-vs-Chainlink strike basis).

## 7. Interpretation (corrected)

1. **Structural staleness is REAL and large.** Quotes sit median 26-29pp away from a minute-bar CLT fair and 99.9% beyond the fee hurdle — the "hug fifty-fifty" phenomenon from the literature, confirmed at scale on live venue data.
2. **But the exploitable component is NOT established.** The +1.76c/trade headline (CI [−1.4c, +4.4c], day-block) is within the noise of the fair's own miscalibration. The venue is meaningfully sharper than a minute-bar CLT pricer — most of the measured "mispricing" is model + basis error, not venue lag.
3. **EV concentrates in the final minute** (+5.9c, n=1,501) — the documented late-window momentum/settlement-distortion region, and exactly where the spec warns against near-ATM entries. This slice is where any real edge most likely lives, and where manipulation risk also lives.
4. **The naive-taker read on staleness is therefore: unresolved, not dead.** The correct next instruments separate model error from venue lag:
   a. **Calibrated-fair re-test** — isotonic-map fair→outcome on a train span, re-run the taker rule on the rest. If EV survives calibration, the edge is real.
   b. **Model-free event-lag** — after sustained underlying moves (e.g. 3 consecutive same-direction minutes, ≥15bp), measure seconds until the quote's mid crosses 50c±δ. No fair value needed; sampler delay gives an upper bound on venue lag. Venue lag measured this way is the honest test of the founding thesis.

## 8. Cross-asset transmission (direction-1 premise verified)

- ETH: corr(1m ret, BTC) = 0.848; |1m move| 4.8bp baseline → 16.9bp when BTC ≥10bp (3.5×); same-direction 99.4% (n=640 events)
- SOL: corr(1m ret, BTC) = 0.731; 7.1bp → 21.5bp (3.0×); same-direction 98.0% (n=640)

The underlying-level premise of "predict SOL/ETH from BTC" is confirmed: SOL/ETH move 3-3.5× their baseline in the same minute as a BTC ≥10bp move, almost always the same direction. Whether the *venue quotes* for SOL/ETH lag BTC quotes on the same shock is NOT yet measurable from this collector (BTC-first polling order confound) — needs interleaved sampling or venue-native timestamps.

Note: per-asset×horizon taker EV showed no uniform cross-asset quote-lag edge (SOL 900s −0.77c vs ETH +2.9-3.3c) — if SOL quotes were systematically slower to reprice to a BTC-driven move, SOL cells would show the largest positive EV; they do not.
