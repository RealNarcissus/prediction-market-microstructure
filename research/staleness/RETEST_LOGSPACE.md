# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=65,578  gated trades=25,862
EV/trade +6.74c  CI [+4.22, +10.58]c  (daily-block)
win rate 0.437  avg ask 0.358
favorites control (N=25862): EV -3.60c CI [-4.84, -2.26]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=65,578  gated trades=26,826
EV/trade +8.45c  CI [+5.48, +11.95]c  (daily-block)
win rate 0.528  avg ask 0.430
favorites control (N=26826): EV -3.70c CI [-5.00, -2.33]c
