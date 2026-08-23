# Design: Short-Horizon Direction Model vs Jupiter Up/Down

**Date:** 2026-08-23
**Status:** Approved (planning phase)
**Project root:** `quant-btc/`

## 1. Goal

Predict whether BTC (and later SOL) will close above or below its epoch strike price on Jupiter's Up/Down prediction market, at 5-minute and 15-minute horizons. Paper trade these predictions as simulated Jupiter contract buys with the venue's exact fee structure applied. Decide, with statistical rigor, whether the strategy is profitable enough to justify real-money trading.

**Primary success metric:** mean per-trade expected value (net of all fees) with the lower bound of its 95% bootstrap confidence interval above zero, measured over a live paper-trading sample.

**Valid "failure" outcome:** "no exploitable edge found" is an acceptable and cheap result. The project is designed to discover the truth, not to justify trading.

## 2. Context

### 2.1 Fixed decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Role of Jupiter | The venue. Paper trading simulates buying Up/Down contracts on Jupiter, including fees. |
| Go-live bar | Statistical significance: positive net EV, CI lower bound > 0. |
| Infrastructure | Local machine first, architect for one-config-change VPS migration later. |
| Approach | Classical ML (LightGBM) + fee-aware selective trading (Approach 1). |

### 2.2 Prior findings from the earlier attempt (`~/Desktop/agentProjects/Herdr/quant-btc`, Aug 2026)

A six-experiment series on 54 months of Binance BTCUSDT perp data (2022-01 → 2026-06, walk-forward 2025 validation, Holm-corrected gates, locked H1-2026 holdout) established:

1. **A small but real direction signal exists.** L2 logistic on trailing returns: 52.07% balanced accuracy (5m) / 52.52% (15m) on the locked holdout; contrarian effect at 15m similar (52.57%). Statistically significant after multiple-comparison correction and replicated out-of-sample.
2. **Best feature: taker-buy volume imbalance.** Adding it lifted 5m test gross edge from +0.87 to +3.74 bps/trade and tail win rate from 53.3% to 57.4%. Open-interest change (k=1 bar) added nothing.
3. **Selectivity works but thins out:** at θ=0.10 only 0.5–0.9% of bars trade; win rates on traded subsets 54–61%, but fold-to-fold variance is large (one 15m fold had 14 trades).
4. **Tail calibration is the key weakness.** In exactly the region where trades fire (P<0.40 or P>0.60), the model is systematically overconfident (predicts ~63%, observes ~51–56%). Platt scaling barely helped (slope ≈ 0.98).
5. **The old venue's fees killed it, not the signal.** Gross edge of 1–4 bps/trade vs 4–10 bps exchange fees → every configuration net-negative.

**What that attempt never tested:** Jupiter as venue (binary-contract economics), market-implied probability as feature/benchmark, mid-epoch entry timing (distance-to-strike), cross-asset signals (SOL), order-book depth, and intra-epoch quote trajectories. All of these are this project's reason to exist — this is a **venue pivot with a proven signal core**, not a from-scratch modeling effort.

**Directly reusable assets:** the frozen canonical dataset (1m raw + 5m/15m + OI parquets, referenced by config path, not copied), and the evaluation harness pattern (pre-registered windows, walk-forward folds, locked holdout, selectivity framework, calibration diagnostics).

**Caution it forces into the design:** 52% accuracy was measured against a 50/50 coin-flip baseline. On Jupiter we buy at the *implied* probability, so the bar is beating the market's own forecast — strictly harder. Hence the market-efficiency baseline measurement in Phase 2 is the true go/no-go, and §4.3's model must combine exchange features with market-implied probability rather than compete alone.

## 3. Market mechanics (verified 2026-08-23)

- Jupiter offers 5-min and 15-min Up/Down binary markets on BTC, ETH, SOL (and others).
- Contracts are priced in USDC. A winning share pays exactly 1 USDC; losers expire worthless.
- Each epoch sets a strike from the oracle price at window open (Chainlink Data Streams secures BTC/ETH/SOL markets; Pyth Pro powers some BTC markets) and resolves Up/Down on the oracle price at window close.
- Trading fees: Jupiter charges an additional fee equal to the Polymarket fee, so total fee ≈ 2× Polymarket's, scaling with contract price. No fee on claiming payouts.
- The Jupiter Prediction API (open beta) provides programmatic access to markets and prices; liquidity is aggregated from Polymarket and Kalshi.

**Phase 0 obligation:** extract the exact current fee schedule and per-market resolution source from official docs, hard-code nothing — all venue parameters live in config. Note: Polymarket activated taker fees on crypto markets in January 2026 (documented in arXiv:2606.04217), so both legs of the fee model are nonzero; Jupiter total ≈ 2× the Polymarket taker fee.

### 3.2 Documented inefficiencies and formulas (literature, verified 2026-08-23)

Three inefficiencies are documented in exactly our market type, in order of expected value:

1. **Quote staleness / underreaction ("hug fifty-fifty").** 5-minute crypto Up/Down quotes on Polymarket are calibrated but not *sharp* — they hover near 50¢ while the underlying's realized path implies lopsided probabilities (Gruener, SSRN 6863546, 209k contracts on BTC/ETH/SOL/DOGE). Compression-toward-50 is structural across Kalshi and Polymarket (Le, arXiv:2602.19520). Live bots exploiting the Binance-feed-vs-quote lag report ~70% win rates; late-window momentum loading in the final 90s is documented. **This is the primary edge hypothesis: reprice faster than the aggregated book.**

2. **Digital-option fair value as the reference price.** An Up contract is a cash-or-nothing binary; with r ≈ 0 at these tenors its fair value is `F = Φ(d₂)`, `d₂ = [ln(S/K) − σ²τ/2] / (σ√τ)`, where S = live spot, K = epoch strike, τ = time to settlement, σ = short-window realized volatility. Near ATM, fair probability moves ≈ `φ(0)/(σ√τ)` per unit of ln(S/K) — at 5m with σ√τ ≈ 8 bps, **1 bp of spot displacement ≈ ±4.8 probability points** (≈ ±2.8 at 15m). A quote that has not repriced after a 1–2 bp move is mispriced by 5–10 points — several times the fee hurdle. This yields a model-free reference price to trade against, independent of the ML model.

3. **Settlement-window distortion.** Manipulation concentrated in the final ~50 s of 5-minute contracts: near-settlement flow spikes up to 3.9×, near-even outcomes flip 65% of the time under pushes, and the median absolute 5-min BTC move is only 6.6 bps (Dai–Jia–Yu, arXiv:2606.31675). The effect is **much attenuated at 15 minutes**. Rules adopted: no near-ATM entries in the final minute of 5m epochs (configurable cutoff); 15m is the primary horizon, 5m secondary.

Microstructure features with literature backing, all computable from the planned collector:

- **Order flow imbalance (OFI):** ΔP = λ·OFI over short windows, slope λ inversely proportional to depth; explains ~65% of contemporaneous price changes in equities (Cont–Kukanov–Stoikov, arXiv:1011.6402 / JFEC 2014); multi-level extension MLOFI (Xu & Gould 2020). OFI and liquidity shocks are documented predictors of near-term crypto returns (arXiv:2602.00776; crypto LOB predictability: arXiv:2403.09267, arXiv:2312.16190).
- **Micro-price (imbalance-weighted mid):** `m = (V_bid·ask + V_ask·bid)/(V_bid + V_ask)` — leans toward the side with less size; high-frequency fair-price estimator (Stoikov, "The Micro-Price", SSRN 3158995 / Quantitative Finance).
- **Honest ML ceiling:** peer-reviewed out-of-sample short-horizon direction accuracy is low-to-mid 50s percent (meta-analysis arXiv:2606.00071; walk-forward-with-costs protocol arXiv:2606.00060). This matches the prior attempt's ~52% and confirms the ML model's role is *blending and sharpening* the above signals, not replacing them.

Two cautions from the literature that shape methodology: apparent cross-venue mispricing often evaporates once observation timing is controlled ("Mistiming is not Arbitrage", SSRN 7170178) — so all staleness measurement must use millisecond-synchronized timestamps on both feeds, never hindsight sampling. And spurious profitability appears easily under naive pooled inference on overlapping windows (Gruener) — significance tests must use trade-level, time-clustered (block) bootstrap.

### 3.1 Economics

Per trade on side priced `p` (0–1) with total fee `f(p)`:

- Win: `+(1 − p − f(p))`
- Loss: `−(p + f(p))`
- Breakeven win probability: `(p + f(p)) / 1`

Implication: raw accuracy is not the target. The model outputs a calibrated P(up); a trade is placed only when `model_prob − implied_prob` exceeds a fee-derived hurdle. Most epochs are skipped by design.

## 4. Architecture

Five independent modules with clear interfaces. All inter-module communication is via the local data store (SQLite for state/ledger, Parquet for bulk ticks) and config.

```
quant-btc/
  config/config.yaml          # venue params, fees, assets, horizons, thresholds
  src/collector/              # always-on daemons: exchange + Jupiter feeds
  src/features/               # feature building, epoch labeling
  src/model/                  # training, calibration, walk-forward harness
  src/paper/                  # venue simulator, position sizing, P&L ledger
  src/eval/                   # metrics, bootstrap tests, reports
  tests/                      # unit + integration tests
  data/                       # SQLite + Parquet (gitignored)
  docs/superpowers/specs/
```

### 4.1 Data collector

- Sources: Binance public API (1s klines and/or aggTrades for BTC/ETH/SOL, top-of-book depth snapshots) and Jupiter Prediction API (live bid/ask per contract side, epoch metadata: strike, open/close times, official resolution).
- **All records carry millisecond timestamps from the source feed** — quote-staleness measurement is only valid with synchronized clocks on both feeds (see §3.2 caution).
- Runs as a daemon on the local machine, restart-safe; backfills gaps from Binance historical endpoints where possible. Jupiter intra-epoch quotes cannot be backfilled — gaps are recorded, never fabricated.
- Labels come exclusively from official settled resolutions, never recomputed from exchange data.

### 4.2 Feature & label builder

- Feature families (all computed as-of decision time, no lookahead): **live digital-option fair value Φ(d₂) and its gap vs the Jupiter quote** (§3.2); multi-lookback returns; realized volatility; **taker-buy volume imbalance (proven best feature from prior attempt)**; **order flow imbalance (OFI) and micro-price from depth snapshots**; bid-ask spread; BTC↔SOL lead-lag; Jupiter implied-probability trajectory within the epoch; distance of spot from strike (native to the fair-value formula); time-of-day; time remaining in epoch. Open-interest change is excluded (proven uninformative).
- One row per (asset, horizon, epoch), keyed and versioned so features can be rebuilt without re-collection.

### 4.3 Model

- One calibrated (isotonic) LightGBM classifier per (asset × horizon); initial scope: BTC and SOL × {5m, 15m} = 4 models — **15m primary, 5m secondary** (per §3.2 settlement findings).
- Isotonic calibration chosen over Platt specifically because the prior attempt showed tail overconfidence that Platt scaling could not fix; tail-region calibration is a first-class metric, not a footnote.
- **The model's job is sharpening, not solo prediction:** inputs blend the Φ(d₂) fair value, Jupiter implied probability, and microstructure features; baselines to beat are fair-value-alone and implied-alone.
- Walk-forward training: fit on trailing window, predict subsequent epochs, roll forward. No random splits — time order is sacred.
- Baselines evaluated first and reported alongside: always-up, momentum, contrarian, implied probability alone, Φ(d₂) fair value alone.

### 4.4 Paper trader (venue simulator)

Per epoch, at a configurable offset after epoch open (entries blocked in the final configurable window of 5m epochs when near ATM, per §3.2):
1. Compute Φ(d₂) fair value and model P(up) from features as-of that moment.
2. Read Jupiter's live ask for the chosen side; implied probability = ask.
3. Apply the fee schedule from config; compute per-contract EV using the model probability (with fair-value gap as the primary screen).
4. Enter only if EV exceeds the configured hurdle.
5. Size with fractional Kelly (¼-Kelly on model-vs-implied edge, hard cap per trade), fill simulated at the live ask at decision time (slippage = ask − mid recorded).
6. Write every round — including skipped ones and the skip reason — to the ledger.

### 4.5 Evaluation & reporting

- Forecast quality: Brier score and log loss, model vs market-implied probability vs Φ(d₂) fair value, per asset/horizon.
- Trading outcomes: hit rate (Wilson CI), per-trade net EV, cumulative P&L, edge-vs-outcome calibration.
- Significance: **block (time-clustered) bootstrap** (10k resamples) 95% CI on mean per-trade EV over executed trades — dependence-robust per Gruener's caution on overlapping windows.
- A daily report script renders a markdown summary from the ledger (no dashboard server in scope).

## 5. Phases & kill criteria

| Phase | Deliverable | Duration | Exit / kill |
|---|---|---|---|
| 0. Recon | Jupiter API access confirmed; exact fee schedule + resolution source in config; fee calculator with unit tests; breakeven tables | 2–4 days | Fee math verified against docs; API reliably queryable |
| 1. Collect | Collector daemon running unattended (Jupiter quotes/resolutions cannot be backfilled — this phase starts day one and gates everything Jupiter-specific); in parallel, port the prior attempt's BTC dataset + harness and rerun the proven feature core as the exchange-only baseline | 2–3 weeks | Dataset of thousands of epochs with quotes + resolutions |
| 2. Model | Market-efficiency baseline first (Brier of Jupiter implied prob vs outcomes), then LightGBM walk-forward: model-with-implied vs implied-alone | ~1 week | **Kill:** if model+implied cannot beat implied-alone Brier/log loss out-of-sample, stop and write the no-edge report |
| 3. Paper trade | Live model vs live Jupiter quotes; simulated fills; full ledger | ≥2 weeks AND ≥1,000 executed trades (whichever is later) | Complete ledger; no code changes to strategy during run |
| 4. Verdict | Go/no-go memo with bootstrap CI, capacity notes, risk list | 1 day | Explicit user decision |

## 6. Stack & testing

- Python 3.11+, `httpx`, `websockets`, `polars`, `LightGBM`, `scikit-learn` (calibration), SQLite. No GPU.
- Config-driven (single `config.yaml`): local→VPS migration must be a config/env change, not code. The prior attempt's dataset (`Herdr/quant-btc/data/`) is referenced by config path, never copied or mutated.
- Methodology ported from the prior attempt: pre-registered evaluation windows, frozen parameters, locked holdout, repro verification scripts per experiment.
- Unit tests: fee calculator, EV/hurdle logic, Kelly sizing, ledger arithmetic (all pure functions).
- Integration tests: collector against live APIs (marked, rate-limited); walk-forward determinism test (same inputs → same metrics).

## 7. Risks & honest limitations

- **Near-efficient markets:** 5-minute direction is close to a coin flip; any edge will be small. The selective-trading filter is the strategy, not a safety extra.
- **Settlement basis risk:** features come largely from Binance data, but epochs settle on Chainlink/Pyth oracle prints. Divergence between the two is measured during Phase 1 and reported; labels always use official resolutions.
- **Overfitting:** walk-forward only; feature and hyperparameter choices frozen before Phase 3 begins; strategy code frozen during the paper run.
- **API/venue changes:** Jupiter's Prediction API is beta; fee schedules can change. All venue parameters in config with a recorded as-of date.
- **Capacity/slippage:** simulated fills at live ask approximate reality but understate competition for size. Phase 4 memo must treat capacity as unknown until real trading.
- **Settlement-time manipulation:** research documents spot order-flow spikes near 5-min settlement times. Recorded as a risk; not exploited in v1.

## 8. Out of scope

- Real-money trading (separate project after Phase 4 go decision: VPS deploy, wallet/key management, execution against the live API).
- Deep learning models (possible phase-2 upgrade only if Approach 1 shows promise).
- ETH modeling (data collected from day one; modeling added later if warranted).
- Any dashboard/web UI beyond the markdown report.

## Sources (verified 2026-08-23)

Venue mechanics:
- [Jupiter Prediction Markets — user docs](https://docs.jup.ag/user-docs/trade/predict) (fees: total = 2× Polymarket fee; free claims)
- [Jupiter Prediction — developer platform](https://dev.jup.ag/docs/prediction) (Prediction API open beta, Polymarket/Kalshi liquidity)
- [Chainlink × Jupiter announcement](https://x.com/chainlink/status/2031354239474176035) (5m/15m BTC/ETH/SOL markets secured by Chainlink Data Streams)
- [Pyth Pro × Jupiter Predict](https://www.pyth.network/success-stories/jupiter-predict-uses-pyth-pro-to-power-its-btc-and-spcx-markets) (Pyth Pro as real-time pricing layer for BTC markets)

Prediction-market efficiency and microstructure:
- [Dai, Jia, Yu — Settlement Manipulation in Prediction Markets](https://arxiv.org/abs/2606.31675) (final-50s manipulation of 5-min BTC contracts; median |5m move| 6.6 bps; attenuated at 15m)
- [Gruener — Calibrated but Not Sharp: 5-Minute Crypto Markets on Polymarket](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6863546) (quotes hug 50/50; dependence-robust inference caution)
- [Qin & Yang — Polymarket-v1 database](https://arxiv.org/abs/2606.04217) (1.2B trades; favorite-longshot bias; VPIN↔Brier; crypto taker fees since Jan 2026)
- [Saguillo et al. — Arbitrage in Prediction Markets](https://arxiv.org/abs/2508.03474) (NegRisk arb $29M, bot-dominated) and [Mistiming is not Arbitrage](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7170178) (cross-venue gaps vs observation timing)
- [Akey et al. — Who Wins and Who Loses in Prediction Markets](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103) (69% of traders lose; top 1% take 76.5% of gains)
- [Le — Decomposing Crowd Wisdom](https://arxiv.org/abs/2602.19520) (compression-toward-50 across Kalshi/Polymarket)
- [Cont, Kukanov, Stoikov — The Price Impact of Order Book Events](https://arxiv.org/abs/1011.6402) (OFI: ΔP = λ·OFI, R² ≈ 65%)
- [Stoikov — The Micro-Price](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3158995) (imbalance-weighted mid; SSRN/QF)
- [Briola et al. — Deep Limit Order Book Forecasting: A Microstructural Guide](https://arxiv.org/abs/2403.09267); [Hawkes-based Cryptocurrency Forecasting via LOB](https://arxiv.org/abs/2312.16190)

ML reality check:
- [Bitcoin Price Prediction: Peer-Reviewed Evidence and Meta-Analysis](https://arxiv.org/abs/2606.00071) (honest short-horizon direction accuracy: low-to-mid 50s)
- [Machine Learning-Based Bitcoin Trading Under Realistic Conditions](https://arxiv.org/abs/2606.00060) (27-fold walk-forward, net-of-cost evaluation)
- [Regime-Aware Multi-Model Bitcoin Direction](https://arxiv.org/abs/2607.23370); [LightGBM vs LSTM on Bitcoin](https://arxiv.org/abs/2511.00665)
