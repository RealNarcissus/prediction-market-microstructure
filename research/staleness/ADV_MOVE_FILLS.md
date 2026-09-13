# Adverse move at fill — v2 settled trades vs collector tape

trades with at least one markout horizon: 571 (of 627 settled v2 trades)

markout_k = best_bid(entry+k) - ask(entry)  [$ per share]; negative = market moved against us after our fill

+30s: n=571  mean -1.75c  median -2.00c  adverse frac 0.569  p10 -17.00c  p90 +12.00c
+60s: n=533  mean -0.60c  median -1.00c  adverse frac 0.533  p10 -20.00c  p90 +20.00c
+120s: n=412  mean +0.16c  median -1.00c  adverse frac 0.522  p10 -25.00c  p90 +27.00c

adverse-move survival at +60s (magnitude of adverse moves):
  n=284  p50 9.00c  p90 27.70c  p99 67.00c

Reading: persistent negative means at +30s/+60s = we systematically
pay the spread plus adverse drift (informed flow ahead of us); the
gap between -mean-markout and the 0.07*p*(1-p) fee is the part of
the backtest-to-live shortfall this measurement explains.

