# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=65,841  gated trades=25,945
EV/trade +6.75c  CI [+4.22, +10.61]c  (daily-block)
win rate 0.437  avg ask 0.357
favorites control (N=25945): EV -3.58c CI [-4.72, -2.29]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=65,841  gated trades=26,945
EV/trade +8.50c  CI [+5.48, +12.05]c  (daily-block)
win rate 0.528  avg ask 0.431
favorites control (N=26945): EV -3.67c CI [-4.89, -2.33]c
