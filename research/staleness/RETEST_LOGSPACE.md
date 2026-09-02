# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=65,317  gated trades=25,831
EV/trade +6.70c  CI [+4.22, +10.39]c  (daily-block)
win rate 0.437  avg ask 0.358
favorites control (N=25831): EV -3.64c CI [-4.98, -2.26]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=65,317  gated trades=26,783
EV/trade +8.42c  CI [+5.48, +11.87]c  (daily-block)
win rate 0.527  avg ask 0.431
favorites control (N=26783): EV -3.75c CI [-5.14, -2.32]c
