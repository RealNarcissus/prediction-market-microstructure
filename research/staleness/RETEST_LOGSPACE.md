# Calibrated re-test with log-space fair (round 33)

split: 1788004800000 (2026-08-29 12:00 UTC); lambda+isotonic fit on train only

## v1_r24  —  lambda(train) 1.70

train n=37,594  test n=70,944  gated trades=28,105
EV/trade +5.83c  CI [+4.06, +7.55]c  (daily-block)
win rate 0.422  avg ask 0.351
favorites control (N=28105): EV -3.31c CI [-4.11, -2.02]c

## v2_ewma  —  lambda(train) 1.95

train n=37,594  test n=70,944  gated trades=28,997
EV/trade +7.75c  CI [+5.30, +9.95]c  (daily-block)
win rate 0.516  avg ask 0.426
favorites control (N=28997): EV -3.38c CI [-4.22, -2.06]c
