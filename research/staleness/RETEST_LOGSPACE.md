# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=59,999  gated trades=23,080
EV/trade +4.98c  CI [+4.46, +5.50]c  (trade-level)
win rate 0.406  avg ask 0.344
favorites control (N=23080): EV -3.43c CI [-3.93, -2.92]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=59,999  gated trades=23,945
EV/trade +6.81c  CI [+6.29, +7.32]c  (trade-level)
win rate 0.504  avg ask 0.424
favorites control (N=23945): EV -3.39c CI [-3.90, -2.89]c
