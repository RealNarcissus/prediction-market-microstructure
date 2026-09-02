# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=65,687  gated trades=25,920
EV/trade +6.73c  CI [+4.22, +10.49]c  (daily-block)
win rate 0.437  avg ask 0.357
favorites control (N=25920): EV -3.61c CI [-4.81, -2.29]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=65,687  gated trades=26,878
EV/trade +8.46c  CI [+5.48, +11.94]c  (daily-block)
win rate 0.527  avg ask 0.430
favorites control (N=26878): EV -3.71c CI [-4.97, -2.35]c
