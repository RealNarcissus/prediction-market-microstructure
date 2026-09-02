# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=63,987  gated trades=25,237
EV/trade +5.89c  CI [+4.03, +7.87]c  (daily-block)
win rate 0.425  avg ask 0.353
favorites control (N=25237): EV -3.62c CI [-4.94, -2.29]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=63,987  gated trades=26,135
EV/trade +7.61c  CI [+4.92, +10.19]c  (daily-block)
win rate 0.517  avg ask 0.428
favorites control (N=26135): EV -3.69c CI [-5.05, -2.27]c
