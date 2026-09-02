# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=71,325  gated trades=28,252
EV/trade +6.05c  CI [+4.22, +7.78]c  (daily-block)
win rate 0.424  avg ask 0.351
favorites control (N=28252): EV -2.98c CI [-4.02, -1.47]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=71,325  gated trades=29,194
EV/trade +7.95c  CI [+5.39, +10.28]c  (daily-block)
win rate 0.519  avg ask 0.427
favorites control (N=29194): EV -3.06c CI [-4.10, -1.54]c
