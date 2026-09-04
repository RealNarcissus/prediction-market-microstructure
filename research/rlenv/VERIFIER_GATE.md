# Verifier Gate — mandatory checklist before any environment/reward change

Prime-RL's #1 success factor: RL works when rewards are deterministic and
cannot be rescued by shaping. We learned the same lesson twice (s014 leak;
fair-value units bug). NO change to `research/rlenv/env.py`,
`research/locked/`, or reward accounting merges without each box ticked
with evidence linked in the commit message.

- [ ] **Settlement arithmetic**: untrained-agent EV equals −fee within
      tolerance on a smoke run (proof: fee bleed is priced correctly).
- [ ] **No lookahead**: features at minute t use bars ≤ t; labels only at
      close (asserted by test).
- [ ] **Fair-value sanity**: median minute-0 fair ∈ [0.3, 0.7]; exact {0,1}
      saturation < 2% of window opens; episodes not born saturated
      (tests/test_rlenv.py).
- [ ] **Side-price symmetry**: Down entries cost (1 − fair_up) ± tolerance,
      never fair_up itself.
- [ ] **Implausibility gate**: any evaluation result beyond MCC/EV bounds
      set in config is blocked pending human review.
- [ ] **Sealed holdout untouched**: no code path reads ≥2026-01 data.
- [ ] **Determinism**: same seed → identical metrics on rerun.

Shaping terms (efficiency bonuses etc.) are allowed ONLY if they cannot
flip a losing action to positive total reward.
