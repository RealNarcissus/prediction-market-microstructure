# Round 102: per-day EV breakdown + side-separated delta fit

config v2_ewma, lambda(train)=1.95, gated n=29,350

## 1. Per-day EV (test span, gated trades)

| UTC date | n | EV/trade (c) | win rate |
|---|---|---|---|
| 2026-08-29 | 4,281 | +3.84 | 0.540 |
| 2026-08-30 | 7,563 | +5.15 | 0.466 |
| 2026-08-31 | 7,969 | +10.65 | 0.536 |
| 2026-09-01 | 4,911 | +9.36 | 0.527 |
| 2026-09-02 | 4,626 | +10.75 | 0.548 |

## 2. Side-separated (delta, lambda) fit on full fair population

markets table: 19,048 rows, suffix mix: [{'suffix': '1', 'count': 9524}, {'suffix': '0', 'count': 9524}]
duplicate market rows: 0 (join is 1:1 per side-suffixed id)

parquet rows without market match: 0 (of 109,429)

| side | n | delta* | lambda* | Brier | Brier (delta=0) |
|---|---|---|---|---|---|
| UP (-0 markets) | 109,429 | +0.00 | 1.90 | 0.1727 | 0.1727 |
| DOWN (-1 markets) | 0 | — | — | — | — |

