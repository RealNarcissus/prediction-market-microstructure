# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=71,835  gated trades=28,404
EV/trade +6.12c  CI [+4.22, +7.89]c  (daily-block)
win rate 0.424  avg ask 0.351
favorites control (N=28404): EV -2.92c CI [-4.05, -1.24]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=71,835  gated trades=29,350
EV/trade +8.04c  CI [+5.48, +10.47]c  (daily-block)
win rate 0.519  avg ask 0.426
favorites control (N=29350): EV -2.94c CI [-4.04, -1.26]c
