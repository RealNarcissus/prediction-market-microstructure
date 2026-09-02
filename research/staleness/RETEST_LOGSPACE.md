# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=71,713  gated trades=28,350
EV/trade +6.06c  CI [+4.22, +7.78]c  (daily-block)
win rate 0.424  avg ask 0.351
favorites control (N=28350): EV -3.04c CI [-4.05, -1.57]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=71,713  gated trades=29,287
EV/trade +7.96c  CI [+5.42, +10.30]c  (daily-block)
win rate 0.519  avg ask 0.427
favorites control (N=29287): EV -3.06c CI [-4.03, -1.60]c
