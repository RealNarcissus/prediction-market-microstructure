# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=71,788  gated trades=28,392
EV/trade +6.09c  CI [+4.22, +7.83]c  (daily-block)
win rate 0.424  avg ask 0.351
favorites control (N=28392): EV -2.99c CI [-4.03, -1.47]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=71,788  gated trades=29,331
EV/trade +8.00c  CI [+5.46, +10.39]c  (daily-block)
win rate 0.519  avg ask 0.426
favorites control (N=29331): EV -3.02c CI [-4.02, -1.49]c
