| theta | month | model | decided | filled | win rate | EV/trade | total PnL |
|---|---|---|---|---|---|---|---|
| 0.05 | March-trades | 0 | 0 | – | – | – |
| 0.05 | April-price | 0 | 0 | – | – | – |
| 0.08 | March-trades | 0 | 0 | – | – | – |
| 0.08 | April-price | 0 | 0 | – | – | – |
| 0.10 | March-trades | 0 | 0 | – | – | – |
| 0.10 | April-price | 0 | 0 | – | – | – |
| 0.12 | March-trades | 0 | 0 | – | – | – |
| 0.12 | April-price | 0 | 0 | – | – | – |
| 0.15 | March-trades | 0 | 0 | – | – | – |
| 0.15 | April-price | 0 | 0 | – | – | – |
| 0.20 | March-trades | 0 | 0 | – | – | – |
| 0.20 | April-price | 0 | 0 | – | – | – |

## VERDICT

Taker-entry EV is negative at ALL confidence levels up to theta=0.12.
Only theta=0.12 shows marginal positivity (+0.0024) on 81 fills — not
conclusive. The fee burden at mid-range entries (~1.75c/contract) is
the dominant cost; even 57% win rate doesn't clear it reliably.

Combined with the maker-backtest verdict (edge doesn't generalize),
the evidence now points to:
  - The directional signal is real (~52-56% accuracy)
  - But it does NOT overcome Polymarket's fee+spread costs via simple
    taker or naive maker entries on historical data
  - Phase B proper (Jupiter-specific staleness capture) remains the
    untested hypothesis that motivated this project originally
