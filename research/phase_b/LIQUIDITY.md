# Liquidity formation after epoch open (Up-token books)

Time until spread first reaches threshold; seconds from open.

| asset | hz | n | t<=10c med/p90 | t<=5c med/p90 | t<=2c med/p90 |
|---|---|---|---|---|---|

**Overall medians:** 

Ask at formation (median): 

## ⚠️ Interpretation warning (2026-08-25)

Across 51k in-window snapshots (Mar 6), spread stays pinned at ~0.80
(median 0.80, min 0.37, max 0.89) for the entire first 3 minutes —
i.e., books look like 10¢/90¢ placeholder walls that never tighten.
Yet 23M trades cleared in this period, which contradicts a literal
reading. Two possibilities:
  1. Opening books really are walls, and trades cross them (fills far
     from fair value — entry timing then matters enormously).
  2. The bot's per-token book capture has inverted/complementary fields
     (same class of bug as our own Jupiter mirror-ask fix).
Resolution path: pull one trades day-file and compare EXECUTED prices to
concurrent best_bid/best_ask snapshots. Do not backtest against these
quotes until this is settled.

## ✅ VERDICT (2026-08-25): snapshots are true two-sided books

Cross-validation of 32,780 executed trades (top-5 markets, Mar 6) against
their latest prior snapshot: **97.9% executed inside [bid, ask]**;
|price−mid| median 0.14. No inversion bug.

Refined microstructure picture of the first 3 minutes:
- Books open WIDE (~10¢/90¢ walls, median spread 0.80) and tighten slowly.
- But heavy flow clears AT/near mid (repeated 0.500 prints — consistent
  with Polymarket's midpoint-matching facility), so fills near fair value
  DO happen without crossing the full spread.
- Implication split:
    * Taker entries at the ask are expensive early (ask ≈ 0.90 walls).
    * Mid/maker-style fills near 0.50 are empirically common — making a
      maker-based entry strategy (or midpoint-match reliance) the most
      promising Phase-B execution design, with inventory risk as the cost.
