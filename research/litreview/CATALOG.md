# Literature Edge-Formula Catalog (autoresearch on arXiv q-fin)

Method: alphaXiv's "autoarxiv" pattern (agent reads paper -> minimal
reproduction on our data -> replication-cost estimate), run through the
locked walk-forward harness (guard, trial ledger, sealed holdout).
Every TESTED entry has a trial number in `research/RESULTS.md`.

**Context: baseline champion s023 (primary MCC 0.046396).**

## Tier 1 — reproduced on our data (verdict: no improvement)

| # | Formula (verbatim source) | Paper | Our implementation | Verdict |
|---|---|---|---|---|
| 28 | `OI_t = Σ V_k·D_k / Σ V_k`, same-phase lags (15' lattice) | [arXiv:2607.09426](https://arxiv.org/abs/2607.09426) "Quarter-Hour Effect" (Binance perps; OOS R² 3.4%, AUC 0.60 at 10s boundary horizon) | s026: imb lag-1 + lag-3 | RESET 0.0421 — paper's horizon (10s/4-12h) doesn't overlap our 5m/15m next-window target |
| 29 | Flow-switch reversal dummies (buyer↔seller switches in W_t) | same | s027: sign(imb_t) − sign(imb_{t−1}) | RESET 0.0430 |
| 30 | VPIN = mean n-bucket \|V_buy−V_sell\|/V under volume clock | [arXiv:1912.10343](https://arxiv.org/abs/1912.10343) (Easley-LdP-O'Hara lineage; toxicity → volatility) | s028: volume-weighted rolling \|2f−1\| (true TBV, no BVC inference needed) | RESET 0.0437 — VPIN predicts volatility/toxicity, not direction; consistent with its literature |
| 31 | Amihud Illiq = mean(\|r\|/dollarVol); impact-weighted imbalance | Amihud (2002); interaction per [arXiv:2602.00776](https://arxiv.org/abs/2602.00776) | s029: log Illiq(24) + imb×logIlliq | RESET 0.0456 — closest of the four; impact regime may matter at Phase B |

Honest summary: our champion already absorbs most of what OHLCV+TBV
computable literature offers. The paper families that DID transfer earlier
(imbalance, intra-bar position) are the same families these papers build on.

## Tier 2 — cataloged for Phase B / future projects (data accumulating)

| Formula | Paper | Data needed | Status |
|---|---|---|---|
| OFI: ΔP = λ·OFI, OFI = Σ e_n (best bid/ask size changes) | [arXiv:1011.6402](https://arxiv.org/abs/1011.6402) Cont-Kukanov-Stoikov (R²≈65% contemporaneous) | L2 top-of-book history | depth20 collecting live since 2026-08-23; backtestable after ~2 weeks |
| Micro-price m = (V_bid·ask + V_ask·bid)/(V_bid+V_ask) | Stoikov (Micro-Price) | top-of-book sizes | same |
| Hawkes self-excitation Λ(t) = μ + Σ α·β·e^{−β(t−t_i)} | [arXiv:2312.16190](https://arxiv.org/abs/2312.16190) (crypto LOB) | trade-tick history | aggTrade collecting live |
| Spoofability / multi-scale Hawkes order features | [arXiv:2504.15908](https://arxiv.org/abs/2504.15908) | L2 depth | future |
| Kyle λ under privacy noise (closed form) | [arXiv:2605.15746](https://arxiv.org/abs/2605.15746) | theory + flow | future (theory) |
| Quarter-hour opening return (10s VWAP window at boundary) | [arXiv:2607.09426](https://arxiv.org/abs/2607.09426) | 1s/aggTrade at boundaries | partially computable from collected aggTrade; the 4-12h horizon suits a FUTURE swing project, not our epochs |

## Tier 3 — negative-context references (methodology guards)

- [arXiv:2605.04004](https://arxiv.org/abs/2605.04004) — systematic
  falsification: 14 intraday-momentum families on 5m MNQ, ALL untradable
  after 2-point costs. Validates our fee-first, negative-results-welcome
  methodology.
- [arXiv:2512.15732](https://arxiv.org/abs/2512.15732) — "Red Queen's
  Trap": 300% validation APY DRL crypto system decayed 70% live; failure
  attributed to ignoring microstructure friction. Validates classical-ML
  + paper-trading gates over end-to-end RL.

## Replication-cost notes (autoarxiv convention)

- Full OFI/micro-price backtests: blocked ONLY on data accumulation
  (~2 weeks of depth20), zero new engineering (features plug into the
  locked harness unchanged).
- Full Quarter-Hour replication (10s boundary VWAP, ACM): needs 1s-level
  data at boundaries — feasible from collected aggTrade with new feature
  plumbing; est. 1-2 days work; payoff uncertain at our horizons.
- Hawkes fitting: est. 2-3 days (tick-decay estimation, per-epoch
  windows); candidate for Phase B if staleness edge confirmed.
