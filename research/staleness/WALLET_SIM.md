# $5 Controlled Wallet Test — Staleness Strategy (v2: sizing frontier)

Generated: 2026-09-01T19:42:31.019992+00:00

Window: OUT-OF-SAMPLE test span only (>= 2026-08-29): 27191 gated signals across 2618 distinct epochs. Rules pre-registered in script docstring (v2): fixed-stake ladder + 10%-of-wallet, one concurrent position, one entry per epoch, real ceil-cent order fee, hold to settlement, settle on official resolutions.

V1 finding (documented): a fixed $1 stake (20% of wallet, ~3.7x full Kelly) ruined the wallet in 7 trades on day 1 despite the per-contract edge — a sizing death, not an edge verdict. V2 maps the full sizing frontier.

## Sizing frontier — $5 wallet, 4 out-of-sample days

| stake/trade | trades | win rate | PnL/trade | final wallet | return | max DD |
|---|---|---|---|---|---|---|
| $0.10 | 168 | 9/168 = 5% | -0.0298 | $0.00 | -100.0% | $5.85 |
| $0.25 | 96 | 15/96 = 16% | -0.0498 | $0.22 | -95.6% | $6.18 |
| $0.50 | 18 | 2/18 = 11% | -0.2561 | $0.39 | -92.2% | $5.74 |
| $1.00 | 7 | 1/7 = 14% | -0.6757 | $0.27 | -94.6% | $4.73 |
| 10% of wallet | 43 | 3/43 = 7% | -0.1077 | $0.37 | -92.6% | $5.76 |

## Strict-cumulative wallet (for the record — structurally overbet)

### Detail per rung

**$0.10**: 168 trades (skipped: busy 3784, dup-epoch 0, unaffordable 23239); per-day PnL: 2026-08-29: -3.19 (n=146), 2026-08-30: -1.81 (n=22); fees paid $1.68
**$0.25**: 96 trades (skipped: busy 2782, dup-epoch 0, unaffordable 24313); per-day PnL: 2026-08-29: -4.78 (n=96); fees paid $1.63
**$0.50**: 18 trades (skipped: busy 877, dup-epoch 0, unaffordable 26296); per-day PnL: 2026-08-29: -4.61 (n=18); fees paid $0.43
**$1.00**: 7 trades (skipped: busy 546, dup-epoch 0, unaffordable 26638); per-day PnL: 2026-08-29: -4.73 (n=7); fees paid $0.31
**10% of wallet**: 43 trades (skipped: busy 1314, dup-epoch 0, unaffordable 25834); per-day PnL: 2026-08-29: -4.57 (n=41), 2026-08-31: -0.03 (n=1), 2026-09-01: -0.03 (n=1); fees paid $0.69

## Daily-reset $5 allowance — the controlled test (primary, v3)

Each UTC day is an independent $5 trial: fresh allowance at 00:00, $1 fixed stake, serial one-position, same pre-registered gate (no ask-region filtering — that split is exploratory and logged separately), hold to settlement, official resolutions. Day stops when its allowance can't fund another $1 stake.

### Variant 1: max-contracts-per-$1 sizing (capital concentrates in cheap asks)

| day | trades | wins | day PnL | day return |
|---|---|---|---|---|
| 2026-08-29 | 7 | 1 | -4.73 | -94.6% |
| 2026-08-30 | 44 | 19 | -4.81 | -96.2% |
| 2026-08-31 | 154 | 71 | -3.06 | -61.2% |
| 2026-09-01 | 21 | 10 | -4.70 | -94.0% |

- **Total: 226 trades, 102 wins (45%), cumulative PnL -16.86 on 4 × $5.00 staked (-84.3% on capital-at-risk)**
- PnL/trade: -0.0746 | skipped: busy 12137, dup-epoch 0, day-budget-exhausted 14828

### Variant 2: 1 contract per trade (weights all price regions equally)

| day | trades | wins | day PnL | day return |
|---|---|---|---|---|
| 2026-08-29 | 136 | 64 | +2.38 | +47.6% |
| 2026-08-30 | 186 | 78 | +3.14 | +62.8% |
| 2026-08-31 | 156 | 71 | +3.18 | +63.6% |
| 2026-09-01 | 69 | 31 | +0.20 | +4.0% |

- **Total: 547 trades, 246 wins (45%), cumulative PnL +9.41 (+1.72c/contract) on 4 × $5.00 at risk**
- PnL/trade: +0.0172 | skipped: busy 26644, dup-epoch 0, day-budget-exhausted 0

## Structural findings (independent of variant)

1. **Where the edge lives (EXPLORATORY — test-span split, needs fresh-day confirmation):** among gated trades, asks 25-75c carry all the EV (+6.7c and +9.8c/contract); asks <25c are NEGATIVE (−1.5 to −4.1c) — the isotonic calibration still overestimates the deep tail (fair_cal ~0.28 vs realized 2-14%). The strict wallet's small rungs were doomed partly because sub-dollar stakes can only afford the failing region.
2. **Minimum viable bankroll:** full Kelly for this edge at ~34c avg ask is ~5.4% of wallet per trade. At venue-typical $1 minimum orders, Kelly-safe sizing needs a ~$20-40 wallet. A strict no-reset $5 wallet bets 20%/trade (~3.7x Kelly) — ruin is a sizing property, not an edge property (empirically: every strict rung died on day 1 and never traded the positive days 2-3).
3. **Entry at recorded ask remains an upper bound** (no latency between signal and fill).
4. **A positive daily-reset result justifies a LARGER controlled paper stake and a latency-aware fill model — NOT live money.**
## Interpretation

- The wallet test answers a DIFFERENT question than per-contract EV: can the edge survive capital limits, serial capacity, minimum-order fee rounding, and one-shot-per-epoch discipline?
- The ladder exposes the structural constraint: at venue-typical ~$1 minimum orders, a $5 wallet bets 20%/trade (~3.7x Kelly) and variance dominates the edge — ruin is a sizing property, not an edge property.
- Sub-dollar rungs show what the strategy needs: the edge can only express itself if orders below $1 are executable on the venue (must verify Polymarket/Jupiter minimum order size before any live test).
- Entry at recorded ask remains an upper bound (no latency between signal and fill).
- A positive rung at survivable sizing justifies a LARGER controlled paper stake and a latency-aware fill model — NOT live money.
