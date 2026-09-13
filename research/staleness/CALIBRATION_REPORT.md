# Pre-Launch Calibration Report

## ACTIVE gate_v2 (calibration_v2.npz)

1. distinct fair_cal values: 48 — PASS
2. gate rate: 0.427 — PASS
3. fair_cal p99-p01 spread: 0.868 — PASS
4. tercile win rates: ['0.171', '0.446', '0.807'] (max gap 0.636) — PASS

## RETIRED v1 (calibration.npz) — record only

1. distinct fair_cal values: 6 — FAIL (collapsed: <10 distinct values)
2. gate rate: 0.450 — PASS
3. fair_cal p99-p01 spread: 0.481 — PASS
4. tercile win rates: ['0.492'] (max gap 0.000) — FAIL (flat profile: gap <= 0.05)

**VERDICT: USABLE — may launch** (active v2 gate; retired v1 gate is dead as expected)
