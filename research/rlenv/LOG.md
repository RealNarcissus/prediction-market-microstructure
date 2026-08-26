# RL Environment — Observation Log

**Phase:** side quest (human-directed): reinforcement-learning loop over the
TWAP-epoch trading environment. Stochastic calculus in the state (Levy
Asian-digital fair value), time-series features (EWMA vol, momentum,
vol-regime z), policy-gradient training (REINFORCE + linear value baseline,
hand-derived numpy backprop). Long-horizon: campaigns append to
`OBSERVATIONS.jsonl`; this file records observations and conclusions.

---

## Environment v1 (built 2026-08-24)

- Episodes = Jupiter-style epochs (5m/15m windows from Herdr 1m data,
  complete windows only, sealed at 2026-01-01).
- Decision points: once per completed 1m bar; agent may enter ONCE
  (buy_up / buy_down / skip); episode ends at entry or window close.
- State (8 features, all causal): Asian-digital fair P(up) at spot/elapsed/
  running-average; ln(running_avg/K); ln(spot/K); taker imbalance of the
  last bar; 5-bar momentum; vol-regime z (|r1| / trailing-mean |r1|);
  fraction of window left; last 1m return.
- Entry price = model-free fair value at decision time (edge must come from
  timing/direction, not assumed mispricing). Fees: exact Jupiter formula.
- Reward at close: ±(payout − entry − fee), per contract.
- Walk-forward: train [2022-01, 2025-01), validate [2025-01, 2026-01),
  sealed ≥2026-01. Sizes: train 105,216 / val 35,040 episodes (15m).

## Sanity baselines

| Policy | entries | win rate | EV/trade |
|---|---|---|---|
| Untrained (uniform init, greedy) | 100% | 49.75% | **−0.0197** (= fee bleed ✓) |

The untrained baseline losing exactly the fee is the environment's proof of
correct settlement arithmetic.

## Campaigns

### Campaign 1 — h=900, seed 0, lr 3e-3, hidden 24, iters 60, 8k eps/iter

Status: RUNNING at time of writing. Observations stream to
`OBSERVATIONS.jsonl`; summary to be appended on completion.

### Smoke run (2 iters, pre-campaign)

Confirmed machinery end-to-end (build 39s, 2.6s/iter incl. evaluation).
Observation: initial policy enters ~83–100% of steps — expected under
entropy exploration; watch whether VAL entry rate falls below 100% as the
skip action's zero-reward advantage accumulates.

---

## INCIDENT 2 (2026-08-25): degenerate fair values invalidated two campaigns

Inspection of entry prices showed fairs pinned at exactly {0,1} — impossible
at window open. Root cause chain: EWMA variance initialized ~10^4x too small
AND per-minute vol divided by 60 instead of sqrt(60) (~7.75x), collapsing
the Levy moment-match into its deterministic limit (v^2 -> 0). Additionally,
Down-side entries were charged the UP price (fair instead of 1-fair).
Fixes: correct vol units, CLT-form average pricing (numerically stable at
our tenors), mirrored down-side pricing, v2-degeneracy guard in
AsianDigital, and two regression tests (tests/test_rlenv.py). All prior RL
results are void; superseded below. Lesson repeated: implausible numbers
are findings.

## Campaign C (fixed environment) — HONEST NULL RESULT

Config: h=900s, seed 0, lr 3e-4 (advantage/reward clipping added), 100
iters x 8k episodes, all-actions contextual-bandit gradients.
Result: agent enters 100% of epochs; VAL EV oscillates -0.028..-0.016
(≈ losing exactly the fee). Honest checkpoint: H1 -0.017 / H2 -0.016
(internally consistent, i.e., stable but flat).

Interpretation: naive policy-gradient learns no positive-EV timing/side
policy even though supervised models reach 52-56% directional accuracy on
the same data (Phase A / A.5). Gap hypotheses:
  1. Sparse dollar rewards vs dense supervised labels -> sample efficiency.
  2. Entering at FAIR price guarantees -fee unless timing beats the CLT
     fair value; the skip-vs-enter contrast is weak under REINFORCE-family
     updates (value baseline absorbs it).
  3. Policy stuck in enter-mode attractor (entropy + init).

Backlog (next iterations):
  1. Behavioral cloning init from the s023 champion's decisions, then RL
     fine-tune (warm-start inside the skill region).
  2. Explicit skip-baseline advantage: adv(a) = r_a - r_skip-expectation.
  3. Curriculum: begin episodes mid-window (informative fairs) then extend.
  4. lr/entropy schedules; BTC-only state subset ablation.

### Campaign D — BC warm-start + skip-baseline fine-tune

Config: h=900s, seed 0, lr 3e-4, BC(5 iters over 105,192 episode-level
champion decisions, loss 4.858) -> all-actions fine-tune with explicit
skip-baseline advantages (b = EMA of best-entry reward).

Result: **policy collapsed to pure abstinence** — 0 entries across both
validation halves; EV exactly 0.0 (vs -0.016 fee bleed for enter-everything).

Interpretation:
1. EV 0.0 > -0.016 is a RATIONAL learned conclusion under entry-at-fair
   pricing: when directional skill doesn't clear fees, not playing wins.
   The skip-baseline formulation works — it discovered abstention on its own.
2. Overdetermined by BC target imbalance: the champion trades <1% of
   windows, so ~99% of clone targets were "skip" — the warm-start began
   near-abstinent and fine-tuning confirmed it.
3. The open question remains whether ANY timing policy can clear Jupiter
   fees at fair-value pricing, or whether edge requires mispriced quotes
   (Phase B staleness capture), not better stopping.

Backlog update:
  - Entry-forced evaluation variant (skip disallowed) to isolate side/timing
    skill from the abstention option.
  - Revisit when official-resolution labels mature (Phase B).
  - If real-money Phase C ever runs, the abstinent policy IS the safe
    default the system should fall back to.

## Conf-gate sweep status (2026-08-25)

Script written but blocked on updown dataset schema mismatch:
- `start_ts` is market creation time, NOT epoch window start
- `slug` column is empty (can't join with orderbooks)
- Correct approach: use `end_ts - timeframe_duration` for window start,
  and `up_token_id`/`down_token_id` (present in markets) for side mapping
- Next session: rewrite sweep using these fields (~15 min)
