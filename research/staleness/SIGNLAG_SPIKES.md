# Round 38: sign-lag conditionals + A/B/C spikes

## Part 1 — sign-lag conditional stats (1m klines, G·001 method)

| asset | n(up-then) | mean next ret after UP (bp) | n(down-then) | mean next ret after DOWN (bp) | reversion? |
|---|---|---|---|---|---|
| BTC | 4,809 | +0.20 | 4,835 | -0.22 | continuation/mixed |
| ETH | 4,889 | +0.14 | 4,910 | -0.16 | continuation/mixed |
| SOL | 4,694 | +0.37 | 4,678 | -0.28 | continuation/mixed |

## Part 2 — A/B/C spike classification (BTC 5m markets, collector quotes)

spikes detected: 1432 (|Δmid| ≥ 4c over ≤2 min)

| class | n | mean post-5m reversion (c, + = revert) |
|---|---|---|
| A | 32 | -29.02 |
| B | 1360 | +0.11 |
| C | 40 | +27.47 |

Class A = PM move aligned with a >=10bp external move; B = external flat;
C = external moved opposite. B reverting hardest supports fade-the-book
logic; A not reverting confirms information-backed moves.