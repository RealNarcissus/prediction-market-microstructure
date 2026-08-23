# Design: Short-Horizon Direction Model vs Jupiter Up/Down

**Date:** 2026-08-23
**Status:** Approved (planning phase)
**Project root:** `quant-btc/`

## 1. Goal

Predict whether BTC (and later SOL) will close above or below its epoch strike price on Jupiter's Up/Down prediction market, at 5-minute and 15-minute horizons. Paper trade these predictions as simulated Jupiter contract buys with the venue's exact fee structure applied. Decide, with statistical rigor, whether the strategy is profitable enough to justify real-money trading.

**Primary success metric:** mean per-trade expected value (net of all fees) with the lower bound of its 95% bootstrap confidence interval above zero, measured over a live paper-trading sample.

**Valid "failure" outcome:** "no exploitable edge found" is an acceptable and cheap result. The project is designed to discover the truth, not to justify trading.

## 2. Fixed decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Role of Jupiter | The venue. Paper trading simulates buying Up/Down contracts on Jupiter, including fees. |
| Go-live bar | Statistical significance: positive net EV, CI lower bound > 0. |
| Infrastructure | Local machine first, architect for one-config-change VPS migration later. |
| Approach | Classical ML (LightGBM) + fee-aware selective trading (Approach 1). |

## 3. Market mechanics (verified 2026-08-23)

- Jupiter offers 5-min and 15-min Up/Down binary markets on BTC, ETH, SOL (and others).
- Contracts are priced in USDC. A winning share pays exactly 1 USDC; losers expire worthless.
- Each epoch sets a strike from the oracle price at window open (Chainlink Data Streams secures BTC/ETH/SOL markets; Pyth Pro powers some BTC markets) and resolves Up/Down on the oracle price at window close.
- Trading fees: Jupiter charges an additional fee equal to the Polymarket fee, so total fee ≈ 2× Polymarket's, scaling with contract price. No fee on claiming payouts.
- The Jupiter Prediction API (open beta) provides programmatic access to markets and prices; liquidity is aggregated from Polymarket and Kalshi.

**Phase 0 obligation:** extract the exact current fee schedule and per-market resolution source from official docs, hard-code nothing — all venue parameters live in config.

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

- Sources: Binance public API (1s klines and/or aggTrades for BTC/ETH/SOL, depth snapshots) and Jupiter Prediction API (live bid/ask per contract side, epoch metadata: strike, open/close times, official resolution).
- Runs as a daemon on the local machine, restart-safe; backfills gaps from Binance historical endpoints where possible. Jupiter intra-epoch quotes cannot be backfilled — gaps are recorded, never fabricated.
- Labels come exclusively from official settled resolutions, never recomputed from exchange data.

### 4.2 Feature & label builder

- Feature families (all computed as-of decision time, no lookahead): multi-lookback returns; realized volatility; volume/trade imbalance; bid-ask spread; BTC↔SOL lead-lag; Jupiter implied-probability trajectory within the epoch; distance of spot from strike; time-of-day.
- One row per (asset, horizon, epoch), keyed and versioned so features can be rebuilt without re-collection.

### 4.3 Model

- One calibrated (isotonic) LightGBM classifier per (asset × horizon); initial scope: BTC and SOL × {5m, 15m} = 4 models.
- Walk-forward training: fit on trailing window, predict subsequent epochs, roll forward. No random splits — time order is sacred.
- Baselines evaluated first and reported alongside: always-up, momentum, and market-implied probability (Jupiter's own quote as forecast).

### 4.4 Paper trader (venue simulator)

Per epoch, at a configurable offset after epoch open:
1. Compute model P(up) from features as-of that moment.
2. Read Jupiter's live ask for the chosen side; implied probability = ask.
3. Apply the fee schedule from config; compute per-contract EV.
4. Enter only if EV exceeds the configured hurdle.
5. Size with fractional Kelly (¼-Kelly on model-vs-implied edge, hard cap per trade), fill simulated at the live ask at decision time (slippage = ask − mid recorded).
6. Write every round — including skipped ones and the skip reason — to the ledger.

### 4.5 Evaluation & reporting

- Forecast quality: Brier score and log loss, model vs market-implied probability, per asset/horizon.
- Trading outcomes: hit rate (Wilson CI), per-trade net EV, cumulative P&L, edge-vs-outcome calibration.
- Significance: bootstrap (10k resamples) 95% CI on mean per-trade EV over executed trades.
- A daily report script renders a markdown summary from the ledger (no dashboard server in scope).

## 5. Phases & kill criteria

| Phase | Deliverable | Duration | Exit / kill |
|---|---|---|---|
| 0. Recon | Jupiter API access confirmed; exact fee schedule + resolution source in config; fee calculator with unit tests; breakeven tables | 2–4 days | Fee math verified against docs; API reliably queryable |
| 1. Collect | Collector daemon running unattended; backtest harness built in parallel | 2–3 weeks | Dataset of thousands of epochs with quotes + resolutions |
| 2. Model | Baselines + LightGBM walk-forward results | ~1 week | **Kill:** if the model cannot beat market-implied Brier/log loss out-of-sample, stop and write the no-edge report |
| 3. Paper trade | Live model vs live Jupiter quotes; simulated fills; full ledger | ≥2 weeks AND ≥1,000 executed trades (whichever is later) | Complete ledger; no code changes to strategy during run |
| 4. Verdict | Go/no-go memo with bootstrap CI, capacity notes, risk list | 1 day | Explicit user decision |

## 6. Stack & testing

- Python 3.11+, `httpx`, `websockets`, `polars`, `LightGBM`, `scikit-learn` (calibration), SQLite. No GPU.
- Config-driven (single `config.yaml`): local→VPS migration must be a config/env change, not code.
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

- [Jupiter Prediction Markets — user docs](https://docs.jup.ag/user-docs/trade/predict) (fees: total = 2× Polymarket fee; free claims)
- [Jupiter Prediction — developer platform](https://dev.jup.ag/docs/prediction) (Prediction API open beta, Polymarket/Kalshi liquidity)
- [Chainlink × Jupiter announcement](https://x.com/chainlink/status/2031354239474176035) (5m/15m BTC/ETH/SOL markets secured by Chainlink Data Streams)
- [Pyth Pro × Jupiter Predict](https://www.pyth.network/success-stories/jupiter-predict-uses-pyth-pro-to-power-its-btc-and-spcx-markets) (Pyth Pro as real-time pricing layer for BTC markets)
- [Settlement Manipulation in Prediction Markets (arXiv)](https://arxiv.org/pdf/2606.31675) (settlement-time order flow effects)
