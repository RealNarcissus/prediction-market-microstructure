# Pre-registered two-week gate verdict — v2 cohort: **FAILED (honest negative)**

## Delivery note (why this is late)

The verdict was pre-registered for 2026-09-18 15:02 UTC (catalog rounds
201/208) and scheduled as automation `automation-775dd112`. That automation
**never dispatched** (runCount 0, marked completed) because the session host
was inactive 2026-09-14 .. 2026-10-23. It is computed here on 2026-10-23
from the append-only ledgers the daemons kept writing unattended. The rule,
the window boundary, the calibration, and the daemon code are unchanged since
pre-registration; only the delivery is late, and no interim computation of
this verdict was run in between (the twin ledger had zero human interaction).

## Pre-registered rule

> Live per-contract EV positive with day-block CI excluding 0 (upward)
> AND all-weeks-positive — REQUIRED before any capital discussion;
> anything else = honest negative, gate retired, feature-bakeoff first.

Window: gate-v2 trades with entry < 2026-09-18 15:02 UTC (gate switch ratified 2026-09-04 15:02 UTC). Units: cents per 1-contract trade.

### Primary — live $5-controlled wallet (gate='v2')

- settled v2 trades in window: **n=1,146** (2026-09-04 .. 2026-09-18)
- pooled per-contract EV: **-2.22c** (= -0.0222 USD/contract), win rate 0.415
- day-block bootstrap 95% CI (10,000 resamples of whole UTC entry days): **[-4.40c, -0.30c]**

| UTC day | n | EV/trade (c) | win rate |
|---|---|---|---|
| 2026-09-04 | 33 | -8.64 | 0.394 |
| 2026-09-05 | 81 | -6.14 | 0.383 |
| 2026-09-06 | 80 | -0.20 | 0.425 |
| 2026-09-07 | 80 | +2.52 | 0.463 |
| 2026-09-08 | 35 | -12.49 | 0.314 |
| 2026-09-09 | 64 | -5.53 | 0.359 |
| 2026-09-10 | 66 | -5.85 | 0.333 |
| 2026-09-11 | 32 | -15.59 | 0.312 |
| 2026-09-12 | 81 | -2.58 | 0.444 |
| 2026-09-13 | 110 | +0.15 | 0.464 |
| 2026-09-14 | 103 | +0.41 | 0.427 |
| 2026-09-15 | 102 | +0.52 | 0.402 |
| 2026-09-16 | 97 | -1.02 | 0.464 |
| 2026-09-17 | 115 | -4.35 | 0.365 |
| 2026-09-18 | 67 | +6.39 | 0.537 |

| ISO week | n | EV/trade (c) | positive? |
|---|---|---|---|
| 2026-W36 | 194 | -4.11 | no |
| 2026-W37 | 468 | -3.56 | no |
| 2026-W38 | 484 | -0.16 | no |

### Twin confirmation — paper_gate daemon (same fair_v2 stack)

- settled v2 trades in window: **n=1,197** (2026-09-04 .. 2026-09-18)
- pooled per-contract EV: **-1.94c** (= -0.0194 USD/contract), win rate 0.414
- day-block bootstrap 95% CI (10,000 resamples of whole UTC entry days): **[-4.15c, -0.06c]**

| UTC day | n | EV/trade (c) | win rate |
|---|---|---|---|
| 2026-09-04 | 45 | -12.87 | 0.267 |
| 2026-09-05 | 81 | -6.14 | 0.383 |
| 2026-09-06 | 81 | +0.36 | 0.432 |
| 2026-09-07 | 80 | -0.97 | 0.412 |
| 2026-09-08 | 37 | -11.81 | 0.324 |
| 2026-09-09 | 56 | -7.30 | 0.357 |
| 2026-09-10 | 66 | -5.85 | 0.333 |
| 2026-09-11 | 75 | +1.53 | 0.440 |
| 2026-09-12 | 82 | -5.22 | 0.402 |
| 2026-09-13 | 110 | -3.44 | 0.427 |
| 2026-09-14 | 96 | +3.39 | 0.479 |
| 2026-09-15 | 102 | +1.33 | 0.402 |
| 2026-09-16 | 96 | +1.04 | 0.490 |
| 2026-09-17 | 126 | -1.20 | 0.405 |
| 2026-09-18 | 64 | +4.88 | 0.500 |

| ISO week | n | EV/trade (c) | positive? |
|---|---|---|---|
| 2026-W36 | 207 | -5.06 | no |
| 2026-W37 | 506 | -3.95 | no |
| 2026-W38 | 484 | +1.49 | YES |

## Verdict

| requirement (pre-registered) | primary result | met? |
|---|---|---|
| per-contract EV > 0 | -2.22c | **NO** |
| day-block 95% CI excludes 0 upward | [-4.40c, -0.30c] (excludes 0 DOWNWARD) | **NO** |
| all ISO weeks positive | 0/3 weeks positive (twin: 1/3, best week +1.49c) | **NO** |

**FAILED — honest negative.** The backtested +8-9c/trade edge did not survive
live paper execution: realized -2.22c/trade over the pre-registered window,
-2.04c/trade over the full v2 cohort to date, twin independently at -2.24c.
The gate is retired from any capital discussion. Any revival requires a
feature-bakeoff candidate that survives prospective realized-EV scoring
(round-235 precedent: the first candidate, BOCPD flow-regime conditioning,
was scored and killed at -0.16c delta).

## Reference comparisons (pre-registered context)

- **brti-edge null (round 208):** an independent team's best walk-forward skill
  on filled trades was 0.93% against a 5% requirement (285 trades, -65% bankroll).
  Our result is consistent with that null: no measurable skill on filled trades.
- **Adverse-move-at-fill (ADV_MOVE_FILLS.md):** -1.75c mean markout at +30s over
  571 fills (median -2.00c, 56.9% adverse) — execution drag roughly fee-sized,
  so the shortfall is backtest-edge overstatement plus dispersion, not latency alone.
- **Nunes IC/PnL non-identifiability (round 216):** feature quality cannot proxy
  realized PnL; only realized-EV scoring (used here) is decisive.
- **BOCPD-EV bakeoff (round 235):** flow-regime conditioning carries no conditional
  information about trade outcomes (EV delta -0.16c = null).

## Post-hoc extension (Sep 18 -> Oct 23) — NOT pre-registered

The daemons kept trading after the window; reported for completeness only.

- wallet: n=2,556 settled, EV -1.96c, CI [-3.43c, -0.56c], 11/36 days positive
- twin:   n=2,527 settled, EV -2.38c, CI [-4.05c, -0.83c]
- cumulative v2 cohort (both windows): 3,702 settled, -7,555c (-75.55 USD) — the negative PERSISTS, no drift toward positive
- censoring caveat: the 500c/day loss allowance pinned six extension days at
  exactly -5.00 USD, so the uncapped post-window EV is somewhat WORSE than -1.96c

## What was NOT tested

Latency-to-venue, queue position, depth-aware sizing, maker (resting) entries,
and capital-scaled slippage. The wallet is paper: fills assumed at the observed
ask with the 0.07*p*(1-p) taker fee. None of these were part of the
pre-registration; they are candidates for any future bakeoff, not evidence.

## Operational state during the gap

All four daemons ran unattended 2026-09-14 .. 2026-10-23 (collector 1.94M quotes,
81.5k market rows, fresh to 11s on 2026-10-23; services restarted at host reboot
2026-10-23 21:27 IST with no state loss — wallet restored 3,873 historical trades).
No thresholds, calibration, or code were touched during the gap.
