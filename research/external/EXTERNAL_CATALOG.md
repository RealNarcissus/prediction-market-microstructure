
- 2026-09-02: round 82 — haoo99 DOWNGRADED to DISCARD-CAUTION (exe-distribution funnel pattern; README is end-user marketing). The PM↔Kalshi gap-arb concept stands; the tooling entry does not. Tape 8.64h (steady). Drift clean (arXiv 2608.30999).

- 2026-09-02: round 74 — CI checkpoint (103,435 quotes): **v2_ewma +8.50c/
  trade, daily-block CI [+5.48,+12.05]** — fifth consecutive stable/
  strengthening confirmation; Brier 0.1716 (still improving); lambda 1.86.
  Tape 2.64h. Drift clean (arXiv 2608.30999).

- 2026-09-02: round 75 — PR&R llms.txt FAQ cross-confirms the settlement
  model a third time: "Up/Down markets settle against the 60-second TWAP of
  the reference feed, not the spot tick"; their /data/price-feed sells the
  rebuilt 60s TWAP series (our tape's commercial twin, also available as
  free samples). YouTube lane: JS-walled (deferred). Tape 2.67h. Drift

- 2026-09-02: round 76 — PR&R adverse-selection glossary page captured
  (precise formulation: "a passive quote is filled precisely when it is
  wrong... the fills a market maker receives are a biased sample of the
  ones it offered"; the common mistake = widening quotes permanently
  instead of detecting-and-withdrawing). Sharpens our own interpretation:
  our taker fills are also a biased sample (we take offers stale because
  informed flow moved them) — the measured +8.5c/trade EV is the residual
  AFTER that adverse selection, earned because our fair is faster than the
  slowest quoters. Tape 2.75h. Drift clean (arXiv 2608.30999).

- 2026-09-02: round 77 — TWAP-settlement glossary page captured (PR&R's
  crispest formulation: "a bot reading the last trade price will disagree
  with settlement near a close, because spot and the 60-second average are
  different numbers"; "the single most consequential mechanical detail for
  anyone automating short-cycle crypto markets — and the one most often
  missed"; backtesting requires the reconstructed 60s TWAP series, not a
  spot tape — their /data/price-feed sells exactly that, our tape collects
  it live). Tape span 8.64h (wall-clock passed during the goal pause) —
  the strike-basis stability gate is now 1/3 satisfied.

- 2026-09-02: round 78 — pushed-this-week GitHub scan (~10 repos/day birth
  rate in the niche): new themes spotted — post-only maker strategies
  ("GTC Post-Only, Zero Fees"), weather-consensus vs Polymarket weather
  markets, and audience-sentiment signals (danmu-intel: esports chat crowd
  wisdom mapped to Polymarket esports markets — a novel signal source
  concept). Nothing research-grade beyond watch items; Cleverfuxaqo
  Telegram bot now ★168. Tape 8.64h (unchanged span — the service session
  is steady). Drift clean (arXiv 2608.30999).

- 2026-09-02: round 79 — spread-capture guide's "no exit management" section
  extracted: **once a balanced pair is locked at blended cost < $1.00, any
  exit destroys guaranteed margin** ("no stop-losses, no take-profits, no
  mid-window sells... the correct behavior given the structure"). NOTE the
  scope: that logic is PAIR-specific — a one-sided directional position
  (ours) carries direction risk, so exits remain a live design question for
  us (round-33/39/abrownfox analyses). Their settlement-listener pattern
  (resolution events → per-market P&L → session totals) mirrors our live
  wallet's resolution handling. Tape 8.64h (span unchanged — wall-clock
  minutes since round 78). Drift clean (arXiv 2608.30999).

- 2026-09-02: round 83 — abrownfox engine.ts slot lifecycle read (completing
  the analysis): the NEW engine enters EARLY (median ~47s after open — the
  180-270s window was the OLD pre-pivot bot), gated to a fair-band ask
  (askInFairBand 45-55¢), budget-capped clips (min(clipUsd, maxSlotUsd −
  spent)), fresh fetchBook at entry, per-slot runtime rate-limiting.
  **Architecturally the closest to our engine**: open+60s entry, mid-band
  asks, fee-gated — differences remain their hand-tuned signal vs our
  derived z and their scratch-culling vs our hold. The late-window spectrum
  attribution is unchanged (old-abrownfox/soulcrancer/BTC5MScour in the
  late zone; new-abrownfox and us in the early coin-flip band). Tape 8.64h
  (steady). Drift clean (arXiv 2608.30999).

- 2026-09-02: round 80 — CI checkpoint on a substantial fresh batch (108,538
  quotes, +5,107): **v2_ewma EV +7.75c/trade, daily-block CI [+5.30,+9.95]**
  — the estimate re-centered from +8.50 as new days arrived (normal
  re-estimation; still solidly positive), lambda* refined to 1.90 (from
  1.86), ECE improving to 0.0271. Tape span 8.64h of real accumulated time
  since deployment. Drift clean (arXiv 2608.30999).
  clean (arXiv 2608.30999).
# External Research Catalog — prediction markets / short-horizon trading

Started 2026-09-01 (sweep ongoing per user objective: broad continuous scan of
projects, papers, edge formulae, practitioner resources; keep what is useful,
discard what is not, record everything).

**Project constraints every verdict is tied to:**
- Our venue: Polymarket 5m/15m BTC/ETH/SOL Up/Down (Chainlink TWAP strike/settle,
  fee = 0.07·p·(1−p) per contract, bounded payout $0/$1).
- Our thesis: calibrated staleness/fair-value gap (CLT Asian-digital fair vs
  quoted price), regime-conditional (24 buckets), NOT raw direction prediction.
- Paper-trading stage ($5/day envelope, live daemon running since 2026-09-02T00:00Z).
- Sealed H1-2026 holdout untouched; no re-slicing buckets after results.
- Venue caveat (user, verbatim): microstructure formulas from continuous LOBs
  do not transfer as-is to a binary prediction market; naive-port failures are
  evidence against the port, not the phenomenon.

Verdict legend: **ACT** = actionable now; **REF** = keep as reference/tooling;
**DEFER** = revisit when depth/tick data or bankroll crosses threshold;
**DISCARD** = not useful for this project (with reason).

---

## 1. Venue facts (Polymarket docs — verified 2026-09-01/02)

### 1a. Settlement regime timeline (verified — affects all our fair-value math)

| Period | Settlement | Source |
|---|---|---|
| launch → 2026-08-07 00:00 UTC | **single-snapshot** price at window close (Chainlink Data Streams) | [crypto.news](https://crypto.news/polymarket-five-second-exploit-manipulation-twap-fix/), [CoinDesk 2026-08-07](https://www.coindesk.com/business/2026/08/07/how-a-five-second-trick-let-traders-drain-millions-from-polymarket) |
| 2026-08-07 → 2026-08-14 | **TWAP: 30s average for 5m markets, 60s for 15m/4h**; **strike (price-to-beat) also moves to the TWAP feed on this date** — both the open and the settle come from the applicable TWAP feed | [changelog /changelog/predictions.md](https://docs.polymarket.com/changelog/predictions.md) (fetched round 10), Genfinity |
| 2026-08-14 → now | **5m markets moved to 60s TWAP** (replacing the 30s window), 00:00 UTC → **current regime: 60s TWAP for BOTH strike and settlement on 5m and 15m** | changelog (fetched round 10) |

- **Taker matching delay on crypto markets: 250ms → 50ms on 2026-08-17** (changelog) → resolves the `secondsDelay` VERIFY action: the delay exists but is negligible at our timescales.

- Why it changed: Stanford + SMU study ([arXiv:2606.31675](https://arxiv.org/abs/2606.31675)): **821 accounts earned $8.2M** pushing Binance BTC across the strike in the final 2–3s of snapshot-settled 5m windows (cost $5–20k to move spot → $50k+ payout; fragmented orders, off-hours timing). "A bet the market treated as near certain was overturned one time in three" (90%+ priced contracts flipped in manipulated windows). Ex-MMs, **93% of losses fell on retail**. Fix raises attack cost but sustained full-window pushes remain possible.
- Kalshi comparison: CF Benchmarks index with 60-second moving average + KYC/CFTC.
- **Impact on us**: (i) our updown historical data spans BOTH regimes → any label-based analysis should carry a settlement-regime flag (Aug 7 boundary); (ii) our CLT fair models a *running* TWAP to window close, but venue settles the **final 30s/60s average** — `research/staleness/fair_v2.py` implements the venue-accurate math (Var = σ²·w/3 for final window w at distance d ≥ w; σ²·d³/(3w²) blend inside the window; European digital for the snapshot regime). **CORRECTED (round 30)**: v1's running-TWAP sd is LARGER mid-window than v2's final-window sd (5m at open+60s: 1.21σ vs 0.577σ), so v2 fairs are MORE extreme — the averaging mismatch runs the OPPOSITE way from the earlier note and cannot explain the v1 overconfidence (fair 95¢ → 73.5% realized); surviving causes: σ understatement (r24 24-min lookback), strike basis (Binance 1m open vs Chainlink TWAP), adverse selection in observed quotes; (iii) live wallet should avoid entries in the final ~90s (manipulation-noise zone; also the sniper-bots' contest zone).

| Fact | Detail | Impact on us |
|---|---|---|
| Min order size — order-type + market dependent | Docs book example: `min_order_size: "5"` **shares** (limit orders). CSDN practitioner (犀牛_c, [project summary](https://blog.csdn.net/2301_76809965/article/details/161971817)): market orders via py-clob-client `MarketOrderArgs` take `amount` in **USDC** and fail below `amount=1` → $1 min for market orders. Both can be per-market fields. | **ACT**: do not hardcode — read `min_order_size` per market from the CLOB API in wallet/evaluator. $5 envelope: 1 market order/day typical, or 5-share limit at ask≤$1.00. |
| Order types GTC, GTD, FOK, FAK | Market orders support FOK (fill-all-or-kill) and FAK (fill-and-kill) | **ACT**: FOK removes the legging risk noted by the Zhihu arb tutorial for YES+NO combos. Also enables "take only if full size" entries in the wallet. |
| Post-only orders | Place maker order that can't take | **REF**: for maker entries (our asks region 25–75¢ carries all EV) |
| Batch orders | 1–15 orders per call | REF (only if we ever ladder) |
| Tick size regime | 0.01 → 0.0001 rules by price band | REF — affects rounding in fair-vs-ask comparisons |
| `market.trading.secondsDelay` + `delayed` status | Some markets have a matching delay on marketable orders | **VERIFY**: if 5m/15m crypto markets carry a near-settlement matching delay, late-window sniping dynamics change. Check CLOB API for our exact markets. |
| Chainlink TWAP Prices page exists (Market Data section) | Polymarket publishes the TWAP feed its crypto markets settle on | **ACT**: replaces our Binance-proxy strike/TWAP fair value with the venue's own oracle series → cleaner fair_yes, removes Binance-vs-Chainlink basis from the staleness signal. |
| **Maker Rebates CONFIRMED** (docs /programs/maker-rebates.md, fetched 2026-09-02) | Taker fees fund maker rebates paid **daily in pUSD** ($1 min payout), performance-based (share of your liquidity that got taken), **fee-curve weighted** using the same formula as taker fees. Category table: **Crypto 20%**, Sports 15%, Finance/Politics/Economics/Culture/Weather/Other/Mentions/Tech 25%, Geopolitics fee-free. | **REF→ACT(maker mode)**: 20% of collected crypto fees flow to makers — the "101¢ per pair" claims likely monetize this. Informs the maker-mode EV question. |
| Taker Rebate Program — **fully captured** (docs /programs/taker-rebates.md, fetched 2026-09-02) | Live **2026-05-28**. wV = TradeSize × (1−EntryPrice) × CategoryWeight × Bonuses; tier from trailing-30d wV; 7 tiers Bronze→Obsidian; daily pUSD payouts; one-time tier bonuses. **Crypto CategoryWeight = 2.3** (highest mentioned). Design note: the (1−EntryPrice) term pays MORE wV per dollar to takers buying the CHEAP side — the venue subsidizes exactly the longshot-taking that MMs won't quote. | **REF** — at our $5/day scale rebates are rounding errors; relevant only at volume. (Earlier April-sample footnote withdrawn — see §1d: fees existed from Feb/Mar 2026, before our sample start.) |
| Chainlink Data Streams docs ([overview](https://docs.chain.link/data-streams), index round 6) | Pull-based low-latency feed family powering the venue's crypto settlement. Relevant schemas/concepts from the docs index: **Crypto Report Schema v2 (Crypto Standard) and v3 (Crypto Advanced), DEX State Price Streams, Crypto Top-of-Book Streams, Calculated Streams, Liquidity-Weighted Bid/Ask, Candlestick API**; llms.txt index for agent consumption | **REF→ACT(#10 refinement)**: the settlement feed's own schema defines what "the venue's number" is — if we ever subscribe (licensing required), the v3 advanced fields and liquidity-weighted quotes would replace ALL proxies in our fair model. Until then, document schema drift risk: our fair assumes 1m-bar sampling, the stream updates faster |
| QuickNode top-10 bots ([guide](https://www.quicknode.com/builders-guide/best/top-10-polymarket-trading-bots)) | Listicle census of bot products (body JS-walled to curl; scope captured via round-1 search summary) | REF (listicle; no methodology) |
| [Moonsat: 6 main types of up/down bots](https://moonsat.medium.com/6-main-types-of-trading-bots-on-up-down-markets-on-polymarket-12893a484f28) | Taxonomy article (403 via WebFetch, absent from author RSS window, no wayback snapshot) | PERMANENTLY DEFERRED — taxonomy partially covered by compendium §2 (11 strategies) and our own §2 map |
| [Medium/Illumination: 4 strategies (2026)](https://medium.com/illumination/beyond-simple-arbitrage-4-polymarket-strategies-bots-actually-profit-from-in-2026-ddacc92c5b4f) | 403 + no snapshot; MM example $1,247/$10k/3wk known from search summary | PERMANENTLY DEFERRED (economics noted; no methodology gain expected beyond compendium) |
| Liquidity Rewards | [docs /programs/liquidity-rewards.md](https://docs.polymarket.com/programs/liquidity-rewards.md) exists; $1M attached to August crypto TWAP markets (~$550k on 5m) per TradoxVPS/LinkedIn | REF (maker mode) |
| Venue depth bound | KaustubhPatange README: 5m markets hold **≤150k USDC of token liquidity per side** at any moment | **KEEP-INSIGHT**: our bankroll can never be constrained by venue depth at our scale — but at whale scale ($4–5k bets) fills move the book; also explains one-tick spreads |
| Latency (practitioner) | r/algotrading bot builder: "Polymarket lags Binance by 1–2 seconds" (informal) vs OpenMarket's 347ms collector-clock quote response | KEEP-INSIGHT: venue reprices in ≲2s on Binance moves — staleness windows for takers are short; our edge must be settlement-math-based (fair vs price), not latency sniping |
| Real-time data feeds | [docs /market-data/realtime-data.md](https://docs.polymarket.com/market-data/realtime-data.md) exists (WS channel details pending) | REF for collector v2 |

### 1c. CLOB API surface — captured for collector v2 (round 7)

From [clob-openapi.yaml](https://docs.polymarket.com/api-spec/clob-openapi.yaml) (fetched, 54 endpoints). Key for us:

- Market data: `/book`, `/books`, `/price`, `/prices`, `/prices-history`, `/batch-prices-history`, `/midpoint(s)`, `/spread(s)`, `/last-trade-price(s)`, `/tick-size/{token_id}`
- **`/fee-rate/{token_id}`** — per-token fee rate at runtime → closes the "query fee instead of hardcode" action; `/neg-risk/{token_id}` for multi-outcome flags
- Market discovery: `/simplified-markets`, `/sampling-markets`, `/clob-markets/{condition_id}`, `/markets-by-token/{token_id}`, `/markets/live-activity/{condition_id}`
- Order lifecycle: `/order`, `/orders`, `/cancel-all`, `/cancel-market-orders`, `/data/orders`, `/data/trades`
- Rewards: `/rewards/user/*`, `/rewards/markets/current` (liquidity-rewards discovery for maker mode), `/rebates/current`
- Auth/ops: `/auth/api-key`, `/balance-allowance`, `/heartbeats`, error codes at `/resources/error-codes.md`
- WS (via borntoup, §5): `wss://ws-subscriptions-clob.polymarket.com/ws/market` — events `book`, `price_change`, `last_trade_price`, `best_bid_ask`, `new_market`, `market_resolved`
- **Verdict: ACT** — this is the definitive API map for collector v2 (WS events + REST backfill via /books + /prices-history) and for runtime fee/min-size reads.
| Taker Rebate Program + Maker Rebates | Programs pages exist (details pending fetch) | **VERIFY**: rebates change net-EV math; taker rebates are unusual and would fatten our taker edge if we qualify. |
| **Fee formula CONFIRMED for our sample** (docs fetched round 3; timeline pinned from changelog round 10) | Current docs: `fee = C × feeRate × p × (1−p)`, **crypto feeRate = 0.07** (peak $1.75/100 shares at 0.50). Makers never charged; 20% of crypto fees → maker rebates; tiered taker rebate on top. **Fee history (changelog §1d): squared curve (peak 1.56% = 0.25·(p(1−p))²) ran until Fee Structure V2 on 2026-03-30; 5m markets launched 2026-02-12 with fees; coefficients drift (sports 0.03→0.05 on Jul 10) and fees are set at match time since CLOB V2 — docs snapshots go stale.** | **RESOLVED**: our `0.07·p·(1−p)` model matches Fee Structure V2 (2026-03-30 onward), which covers our ENTIRE sample (starts Apr 6) — validated, no code change. The earlier "news claims are wrong" statement is corrected: the 1.56% figure described the real pre-Mar-30 curve. Runtime `/fee-rate/{token_id}` queries remain mandatory (coefficients drift). |

Sources: [Place Orders](https://docs.polymarket.com/trading/place-orders),
[Fees](https://docs.polymarket.com/trading/fees),
[py-clob-client#326](https://github.com/Polymarket/py-clob-client/issues/326).

### 1d. Fee & platform timeline — fully pinned from the changelog (round 10)

Source: [changelog/predictions.md](https://docs.polymarket.com/changelog/predictions.md) (fetched in full, round 10).

| Date | Change | Impact on us |
|---|---|---|
| ≤ Feb 2026 | 15m crypto markets carry taker fees on the **squared curve** (peak 1.56% at 0.50 = `0.25·(p·(1−p))²`) | Explains the "1.56%" claims we initially dismissed — both formulas were real, in sequence |
| 2026-02-12 | **5-minute crypto markets launch with taker fees** (same curve as 15m) + maker rebates | 5m fee era begins |
| 2026-03-06 | Fees extend to ALL crypto markets (1H/4H/daily/weekly), new markets only | — |
| **2026-03-30** | **Fee Structure V2**: per-category rates → **crypto feeRate 0.07** (peak 1.75% at 0.50) | Our evaluator/wallet formula matches the V2 regime |
| 2026-03-31 | Fees must be computed from the per-market `feeSchedule` object | Runtime reads mandatory (docs snapshots go stale) |
| **2026-04-28** | **CLOB V2 live**: fees set at match time (`feeRateBps` removed from orders); pUSD replaces USDC.e collateral; open orders wiped | **Sample regime boundary**: our updown data starts Apr 6 → first ~3 weeks are V1-era; analyses should carry a CLOB V1/V2 flag |
| 2026-07-10 | Sports fee coefficient 0.03→0.05; sports maker rebate 25%→15% | Proof coefficients drift → never hardcode; query `/fee-rate/{token_id}` |
| 2026-08-07 / 14 / 17 | TWAP strike+settlement live; 5m window 30s→60s; taker delay 250ms→50ms | See §1a |

- **Net sample-consistency verdict (supersedes the earlier April footnote)**: our sample starts **2026-04-06** → the ENTIRE sample is in the Fee-Structure-V2 era (0.07·p·(1−p)) — our fee model is validated across the whole sample. Remaining sample regime flags: CLOB V1→V2 (Apr 28), snapshot→TWAP (Aug 7), 5m 30s→60s (Aug 14).

## 2. GitHub repos (English + Chinese-dev)

| Repo | What it is | Verdict |
|---|---|---|
| [Polymarket/poly-market-maker](https://github.com/Polymarket/poly-market-maker) | Official CLOB keeper: keeps quotes near midpoint, 2 strategies | **REF** — template for a maker-mode wallet later; read for order-lifecycle handling |
| [warproxxx/poly-maker](https://github.com/warproxxx/poly-maker) | Community maker-only MM bot for CLOB V2 | **REF** |
| [Polymarket/polymarket-cli](https://github.com/Polymarket/polymarket-cli) | CLI + JSON API for markets/orders | **REF** (our paper daemon already has its own collector; CLI useful for manual ops) |
| [duzhi5368/FKPolyTools](https://github.com/duzhi5368/FKPolyTools) | (Chinese dev) TS SDK: real-time arb detection WebSocket + auto-exec, smart-money tracking, copy trading, market scan/rebalance | **REF/DEFER** — arb-detection logic is a reference implementation for our staleness gap detector; smart-money tracking is a future feature idea; copy trading DISCARD |
| [jon-becker/prediction-market-analysis](https://github.com/jon-becker/prediction-market-analysis) | Framework + largest public Polymarket/Kalshi trade dataset | **REF** — potential cross-check of our collector against a public archive |
| poly-sdk / pmxt | Programmatic-trading SDKs; pmxt unifies Polymarket/Kalshi/Limitless | REF (pmxt interesting if we ever add a second venue) |
| Rust arb kit (BTC strategy + AI agent module) | Low-latency arb components; claim of single-day profits on 15m BTC markets (unverified marketing) | **DEFER** — latency engineering irrelevant at our paper stage; unverified PnL claims |
| OpenClaw Polymarket bot / PolymTradeBot (SaaS) / copy-trading bots (PolySyncer review) | Turnkey/commercial bots, "AI trader" CLIs | **DISCARD** — no published edge methodology, survivorship-marketing, and we don't buy signals |
| [gregyoung14/openmarket](https://github.com/gregyoung14/openmarket) (full README fetched) | 17.8k-LOC Rust pipeline: WS collectors → timestamp sync → features (43) → logistic+Platt, 559 walk-forward windows (~357k rows). **Model AUC 0.8377 vs naive mid-price prior 0.8405; Brier 0.165 vs 0.163; ECE 0.026 vs 0.014** → model slightly UNDERPERFORMS the venue's own mid-price. 261,889 simulated +EV trades → **−0.116/trade** after fees+slippage. Microstructure: 16ms median lead-lag (heavy tails −186/+316ms), 347ms collector-clock quote response, **91.9% spreads one tick (0.01)**. Archival shutdown, frozen v0.5.2, Apache 2.0; data on HuggingFace `gregyoung14/openmarket-btc-polymarket` (727M rows, 605.6M PM ticks, 62.3M Binance trades, 2.9M lag pairs, 4,450 markets, 93-day span Feb 12–May 15 2026) | **KEEP-CORNERSTONE**: independent falsification of the venue-feature lane (mirrors our Phase-B/RL nulls). Validates our lane choice: features from the venue book cannot beat the venue mid; the remaining edge classes are (a) exogenous fair-value (underlying → binary fair, our staleness approach) and (b) maker economics. Also a **validation dataset overlapping our Apr-2026 updown window** — our collector join and labels can be cross-checked against their archive. And a warning: one-tick spreads make mid-price backtests look better than reality — we always enter at the ask (correct side). |
| [aulekator/Polymarket-BTC-15-Minute-Trading-Bot](https://github.com/aulekator/Polymarket-BTC-15-Minute-Trading-Bot) | "Production-grade" 15m BTC bot: 7-phase signal pipeline (spike detection, Fear&Greed sentiment, price divergence `PriceDivergenceProcessor`), self-learning, NautilusTrader-based; endorsed on X by @AlterEgo_eth as "most serious open-source bot"; commercial listing at PolBots | **REF** — NautilusTrader integration pattern; signal taxonomy shows competitor feature sets (sentiment/divergence = different families from ours). No verified PnL. |
| [KaustubhPatange/polymarket-trade-engine](https://github.com/KaustubhPatange/polymarket-trade-engine) (README fetched) | TS engine for BTC/ETH/XRP/SOL/DOGE/HYPE/BNB 5m+15m: strategy test harness, run-analysis dashboard, LEARNING/GUIDE/MOTIVATION docs; deliberate TS-not-Rust rationale: "5-min markets have thin liquidity (≤150k USDC/side), interactions via standard CLOB APIs — speed is not the bottleneck" | **REF** — engineering reference; the depth number and the "speed is not the bottleneck at our scale" reasoning both support our architecture choices |
| [Benjam1nCup/Polymarket-trading-bot-python-V2](https://github.com/Benjam1nCup/Polymarket-trading-bot-python-V2) (README fetched) | MIT "education" repo (sells full bots): post-TWAP-60s strategies — Momentum Arbitrage (multi-signal, ~$2.5k rec. capital), **TWAP Reversal Bot targeting "final 90 seconds when BTC TWAP is near the boundary"** (whale-reversal sniper), "101-cents bot" claiming ≥101¢ returned per $1 YES+NO pair (~190 trades/day) — likely monetizing the maker rebate on top of par | **DISCARD as evidence** (self-reported, selective screenshots, "never incurs a loss" is a red flag). **KEEP the strategy taxonomy**: (i) confirms the final-90s window is where manipulation/reversal battles happen → stay out or model explicitly; (ii) the 101-cents claim implies maker-rebate economics can push paired payouts above par — worth a math check if we ever go maker mode. |
| [tradoxvps.com](https://tradoxvps.com/blog/) + LinkedIn | Polymarket-specific VPS vendor; $1M liquidity-rewards coverage; TWAP-settlement explainers | REF (infra vendor exists → latency game is real for the fast lane) |
| [chudi.dev: Binance→Polymarket momentum signal pipeline](https://chudi.dev/blog/binance-polymarket-momentum-signal-pipeline) | Sub-100ms order execution on PM signals from Binance flow | REF (the fast lane we deliberately don't contest) |
| [Novals83/5min-btc-polymarket](https://github.com/Novals83/5min-btc-polymarket) (README fetched) | OpenClaw skill, momentum-into-close: entry ~2min before expiry after BTC moved $70–100 in-window, crowd-skew check, enter WITH momentum, 50% allocation, micro-hedge opposite side at extreme skew (95/5) | **REF**: the late-window momentum playbook with a conditional (skew) gate — a plausible source of the fillable sub-edge within the 74.8/75.3 zero-lag average. Unverified. Note "confirm move already happened" = conditioning on realized path, which is legitimate post-TWAP (settlement is path-dependent) |
| [aleczzhang/PolySignal](https://github.com/aleczzhang/PolySignal) | Open-source: tracks Polymarket+Kalshi in real time, infers cause-effect chains → actionable signals | REF — cross-venue signal inference is a future feature idea |
| PolySignal-name cluster (polysignal .net/.co/.pro/.info/.xyz/.dev) | Six different paid "signal" products sharing one brand; one sells a "fully-automatic BTC bot" for 5m/15m markets | **DISCARD + WARNING**: brand-squatting cluster is a scam vector — never connect wallets or pay for signals |
| [Oceanjackson1/Prediction-Market-Arbitrage-Compendium](https://github.com/Oceanjackson1/Prediction-Market-Arbitrage-Compendium) (README + academic-foundation + ALL 11 strategy pages fetched rounds 4/8/9/12) | CN-language deep-research repo grounded in arXiv:2508.03474. Rounds 8/9 covered D (maker: ~0.2% of volume → profit; inventory risk), G (bond: 90%+ of $10k+ orders in >$0.95 markets; UMA oracle attack tail), K (sequential two-leg grid), E (polyclaw: contrapositive-logic hedges, CTF split-then-sell execution, coverage tiers T1≥95%), H (esports official-API 30–40s > broadcasts; mempool frontrunning discarded). **Round 12: A — intra-platform rebalancing** (YES+NO bid-sum < $0.97 + NegRisk multi-outcome; scanner [runesatsdev/polymarket-arbitrage-bot](https://github.com/runesatsdev/polymarket-arbitrage-bot) with >$5k whale-flow tracking, signal-only; ⚠️ their '2% settlement fee' premise = pre-Mar-30 fee era, superseded by §1d). **B — cross-platform** (PM_YES + Kalshi_NO < $1 net of both fees; risks: settlement-rule divergence, UMA oracle ($7M manipulation Mar 2025), dual capital lockup, leg risk; **[taetaehoho/poly-kalshi-arb](https://github.com/taetaehoho/poly-kalshi-arb)**: Rust, lock-free orderbook cache, SIMD arb detection, concurrent dual-leg execution — the reference implementation for our Kalshi lane). **C — latency arb** ('most profitable 2025-26': Binance >0.3% move, PM lagged 2–15s in the early era (OpenMarket later measured 347ms); the $313→$414k bot mechanism; **compendium's own update: dynamic taker fees killed the lane at scale**; [lingreerjr-eng/latency-bot](https://github.com/lingreerjr-eng/latency-bot)). **F — AI probability estimation** ([Polymarket/agents](https://github.com/Polymarket/agents) official: Gamma + ChromaDB RAG + LLM prob + Kelly sizing; 'core challenge is LLM probability calibration'; $2.2M/2mo unverified — news-driven LLM probs are not our lane; our calibrated s023 stack IS the probability model). **I — unified API** ([guzus/dr-manhattan](https://github.com/guzus/dr-manhattan): 'CCXT for PMs' — Polymarket/Kalshi/Limitless/Opinion/PredictFun, full CTF split/merge/redeem, MCP integration; Rust port gtg7784/dr-manhattan-rust) | **REF→ACT(second venue)**: poly-kalshi-arb + dr-manhattan are the two concrete libraries for the Kalshi expansion; A/C confirm our positioning (mechanical arb hyper-competitive + fee-killed); F = the LLM lane we deliberately don't run |

## 3. Chinese ecosystem (GitHub-dominant; Gitee has none venue-specific)

| Source | Content | Verdict |
|---|---|---|
| [Zhihu: 4000万美金的套利市场](https://zhuanlan.zhihu.com/p/1989016130568860070) | Hands-on Polymarket arb bot tutorial; hybrid architecture (off-chain matching, on-chain settlement), CTF conditional tokens; YES+NO < $1.00 arb basis; warns of legging risk (outdated re: FOK availability) | **REF** — best structural explainer of venue mechanics from the CN side; the $40M/yr arb-profit figure quantifies how contested the pure-arb lane is |
| CSDN: Polymarket auto-trading bot project summary (犀牛_c, [article](https://blog.csdn.net/2301_76809965/article/details/161971817)) | Full-fetched. Python/ClobClient FOK bot; pitfalls: deposit-wallet flow ("maker address not allowed"), API-key flakiness, WS/strategy thread duplicate-order bug (state flag fix), FOK "couldn't be fully filled" retry loop, market-order min $1 (`amount` in USDC), Python 3.10–3.12 only, HK server, proxy instability | **REF** — production pitfall checklist directly applicable when our paper daemon goes real; sibling CSDN "copy trading bot 24.7%/mo" articles are content-marketing spam → DISCARD |
| [Binance Square bot-war stats](https://www.binance.com/en/square/post/pos.market) | 37% of volume from 3.7% bot addresses; arb window compressed 12.3s → 2.7s; 73% of arb profit to HFT scripts | **KEEP-INSIGHT**: pure-arb lane is HFT-contested and closing. Our staleness lane (30s–5m horizons, requires fair-value modeling) is the *slower* lane that HFT doesn't fully clear — supports our positioning |
| HTX 万字指南 (170+ tools), MarsBit (18 tools), Tencent News roundup | Ecosystem catalogs; claim of a bot turning $313 → $414k on 15-min crypto markets | **DISCARD** as evidence (unverified marketing); **REF** as source maps for finding more repos |
| Coinman case: 3237 trades, $1.2M/yr, 6-layer arb stack | Reverse-engineered top CN arb account | **REF** — the "6 layers" (data feed, latency, fee tier, sizing, inventory rebal, kill-switch) is a checklist mirroring our own infra plan |

## 4. arXiv / SSRN (2025–2026 wave)

| Paper | What it shows | Verdict |
|---|---|---|
| [arXiv:2604.24366](https://arxiv.org/abs/2604.24366) Microstructure Evidence from the Polymarket Order Book | Tick-level archive (~30M+ obs) of the WS order-book feed; flagship microstructure study | **REF→DEFER**: adopt their feature definitions when our depth20 history ≥2 weeks (matches our Tier-2 OFI/micro-price plan; venue-native, satisfies the caveat) |
| [arXiv:2607.26245](https://arxiv.org/abs/2607.26245) OpenMarket: synchronized Polymarket–Binance dataset | Public aligned PM↔exchange data | **ACT-REF**: methodological template for our collector joins (their alignment scheme can validate our `end_ts−duration → open_ms` join and our cross-asset transmission work) |
| [arXiv:2605.00864](https://arxiv.org/abs/2605.00864) NBA arb analysis | "Profound microstructural efficiency": only 7 executable in-game arbs | **KEEP-INSIGHT**: single-market anomalies are rare and transient → consistent with our finding that naive fair-value edges mostly evaporate after calibration; our edge must come from *calibration + regime*, not raw mispricing |
| [arXiv:2508.03474](https://arxiv.org/abs/2508.03474) Unravelling the Probabilistic Forest (Saguillo et al.) — **published at AFT 2025** ([LIPIcs](https://drops.dagstuhl.de/storage/00lipics/lipics-vol354-aft2025/html/LIPIcs.AFT.2025.27/LIPIcs.AFT.2025.27.html)); 86M OrderFilled bids, 2024-04→2025-04 | Taxonomy: market-rebalancing arb (within condition) vs combinatorial/cross-market arb (LLM-embedding-detected logical dependencies). Numbers: **~$39.59M total arb profit** ($10.58M single-condition); **7,051 conditions (41%)** had exploitable deviations, mean deviation ~40%; top arbiter $2.01M/4,049 trades ≈ $496/trade; top-3 $4.38M; politics = largest absolute profit, sports = most frequent/smallest; **non-atomic legs** (unlike DeFi arbs, one leg can fail); follow-up Medium: **62% of LLM-detected dependencies fail to hold** | **REF→ENRICHED** — frames our staleness trade as rebalancing subclass; the 41%/40%-deviation numbers quantify how common gross mispricing is before costs; non-atomicity = the legging risk every practitioner hit |
| [arXiv:2606.04217](https://arxiv.org/abs/2606.04217) Polymarket-v1 DB | 1.2B trades / 1.3M markets / $61B; tests microstructure-quality → forecast-accuracy link | REF |
| [arXiv:2510.15612](https://arxiv.org/abs/2510.15612) SoK: DePM microstructure | Systematization of decentralized prediction-market MM | REF (background) |
| [arXiv:2604.20421](https://arxiv.org/abs/2604.20421) full-lifecycle datasets; [PolyBench 2604.14199](https://arxiv.org/abs/2604.14199) LLM benchmark (38,666 markets) | Datasets/benchmarks | DISCARD for edge purposes (LLM-forecast benchmark ≠ our problem); REF as data sources |
| [arXiv:2603.03136](https://arxiv.org/abs/2603.03136) Anatomy of Polymarket (2024 election) | PM vs polls aggregation | DISCARD (politics, not our horizon) |
| **kacho.io 5m-crypto dataset** ([HN Show](https://news.ycombinator.com/item?id=48573307), [page](https://kacho.io/polymarket-5min-crypto-dataset), HF `kachoio/polymarket-5-minute-crypto-up-down-markets`, Kaggle mirror) | ~89k markets / **26.8M per-second top-of-book samples**, Mar–May 2026, BTC/ETH/SOL/XRP/DOGE/HYPE/BNB, CC0, 99.8% coverage (~1.5h total outages). Author's own caveat: not good enough to fully backtest live trading | **ACT-REF**: second validation dataset overlapping our window; 1s top-of-book cadence ≈ our collector granularity but 7 coins and longer span — cross-check our quote-derived EV estimates against a 7-coin sample |

### 4b. LMSR / AMM market-making literature (academic lane, round 2)

- Hanson, [Logarithmic Market Scoring Rules](https://www.eecs.harvard.edu/cs286r/courses/fall10/papers/mktscore.pdf) — foundational bounded-loss AMM; [practical implementation walkthrough](http://blog.oddhead.com/2006/10/30/implementing-hansons-market-maker/).
- Sandholm/Othman, [Liquidity-Sensitive LMSR](https://www.cs.cmu.edu/~sandholm/www/liquidity-sensitive%20automated%20market%20maker.teac.pdf) — fixes standard LMSR spread dynamics.
- [A Bayesian Market Maker (EC'12)](https://www.cs.tau.ac.il/~fiat/cgt12/EC_2012/docs/p215.pdf) — MM robustness against intelligent agents (the "who profits from whom" math).
- [Efficiency of Constant Log Utility MMs (arXiv 2510.12952)](https://arxiv.org/html/2510.12952v1); [Configurable arbitrage & slippage in AMMs (FRL 2025)](https://www.sciencedirect.com/science/article/abs/pii/S1544612325008748).
- [ChainSecurity audit of Polymarket ConditionalTokens](https://reports.chainsecurity.com/Polymarket/ChainSecurity_Polymarket_ConditionalTokens_Audit.pdf) — contract-level risk reference.
- Verdict: **REF/DEFER** — Polymarket's crypto markets are CLOB (not LMSR), so LMSR math applies to (a) understanding AMM-based rivals (Limitless etc.) and (b) the maker-mode pricing question later. Not directly actionable now.
| SSRN "Polymarket Paradox" (Abid 2026) | Manipulation/whale activity; $250M+ settled via governance votes after oracle disputes | **KEEP-RISK**: resolution risk is a real tail for live trading — our ledger must record settlement-dispute incidents |
| **Capital Lock-Up Costs in Prediction Markets** (working paper, via [LinkedIn discussion](https://www.linkedin.com/posts/jose-francisco-jr_predictionmarkets-marketmicrostructure-activity-7492895541559820290-WNrq), round 9) | Claims **up to 88% of apparent PM "mispricing" is compensation for locked-up capital** (time value between trade and resolution), not inefficiency | **KEEP-CORNERSTONE**: fundamental control for gap-based EV work — gross mispricing ≠ net edge when capital is locked. **Good news for us**: 5m/15m windows lock capital for minutes → lock-up compensation is negligible in our markets, so our measured staleness edge is *cleaner* than politics-market anomalies. Any expansion to long-dated markets must add a lock-up term to fair value |
| [arXiv:2607.17991 Optimal Market Making in Prediction Markets](https://arxiv.org/abs/2607.17991) (round 9 scan) | Stochastic-control MM framework; price modeled as a conditional process | REF→DEFER (maker-mode theory reference) |
| Binary Prediction Markets: Failure Modes and Mechanical Stress Tests Using Polymarket Data (arXiv q-fin.TR, May 2026, 18pp; round 9 scan) | Failure modes + mechanical stress tests on Polymarket data | KEEP-RISK (robustness checklist; locate full text next scan) |
| [arXiv:2605.10400 Resolution-Aware Perpetual Futures on Binary Prediction Markets](https://arxiv.org/abs/2605.10400) (round 9 scan) | Risk-design framework on Polymarket data; **v2 subtitle = "Failure Modes and Mechanical Stress Tests Using Polymarket Data"** — the stress-test paper resolved into this entry (round 10) | REF (derivative structures on PMs; outside current scope) |
| [arXiv:2608.21888 Short-horizon mean reversion in cryptocurrency markets](https://arxiv.org/html/2608.21888v1) (Kitron & Wengrowicz, 2026-08-22; round 11 scan) | Matched cross-market measurement: **at 15-minute horizons, directional mean reversion is far stronger and more pervasive in crypto than in US equities** | **KEEP→research-queue candidate**: rigorous external measurement of the phenomenon our chop-regime findings and the contrarian-bot experiment touch; cross-check our 15m regime results against their framework |
| arXiv August 2026 batch (round 11 scan of q-fin.TR recent, 25 titles) | Relevant others: 2608.00885 Optimal Trading of Microstructure Mean Reversion (methodology REF); 2608.04373 Public Trader Identity: Adverse Selection and Return Predictability (ties to our adverse-selection lessons); 2608.09188 When Cross-Venue Agreement Is Not Price Discovery (24/7 perp oracles); 2608.07709 Rough Hawkes–Heston microstructure (deferred Hawkes Tier-2 theory); 2608.23915 Equilibrium in closed CFMM economies (AMM-venue theory) | REF (cataloged for the deferred-lane theory stack) |

## 5. Reddit / practitioner threads

| Thread | Claim | Verdict |
|---|---|---|
| [r/SideProject: bot on 5-min crypto markets](https://www.reddit.com/r/SideProject/comments/1vckypo/i_made_a_bot_that_trades_polymarkets_5minute/) | "$180 overnight" | DISCARD as evidence (single-night, no CI); the existence of many such bots = competition note |
| [r/algotrading: 5-min bot update 2](https://www.reddit.com/r/algotrading/comments/1u0cz4n/update_2_i_was_bored_so_i_though_of_making_a_5min/) | Profits in trends, loses badly in chop/reversal | **KEEP-INSIGHT**: independent replication of our regime-conditional result — momentum-style edges on these markets are regime-dependent; matches our vol-tercile bucketing |
| [r/Polymarket: 7 months testing every 5-min strategy](https://www.reddit.com/r/Polymarket/comments/1un85mg/i_spent_7_months_testing_every_strategy_on/) | Deep-dive (fetch blocked; retry) | PENDING — highest-priority retry: matches our exact market |
| [r/PredictionsMarkets: reality of bots](https://www.reddit.com/r/PredictionsMarkets/comments/1uju247/reality_of_trading_bots_in_polymarket_ideas/) + [consistency thread](https://www.reddit.com/r/PredictionsMarkets/comments/1u7jkvv/has_anyone_actually_built_a_consistently/) | Realistic expectations; few consistently profitable | KEEP-INSIGHT (prior calibration for our expectations) |
| [r/AI_Agents: self-rewriting bot cautionary tale](https://www.reddit.com/r/AI_Agents/comments/1rkpm7y/we_built_a_trading_bot_that_rewrites_its_own/) | "83% win rate… 5 wins totaled $12.78 but a single loss cost $100" | **KEEP-INSIGHT**: win-rate is meaningless in binary markets; EV per trade is the only metric (independent replication of our fee-first EV framing) |
| [HN 48461522: arb bot real numbers](https://news.ycombinator.com/item?id=48461522) — **author = kachoio** (the 5m-dataset person; NOT gregyoung14/OpenMarket — earlier conflation corrected) | Jan–late Mar 2026, 3,858 bets, ~$5k net on Polymarket esports: **+$8.3k from guaranteed arbs, −$3.2k from directional legs placed with the SAME ≥7% edge threshold**. Directional legs lost to: stale quotes picked off by faster bots (adverse selection), a devig method running hot on favourites, and a team-matching bug (bookmaker A-vs-B order flipped vs Polymarket's — an AI-coded bot flaw). Fill times ~25min posting at best_bid+1¢; spreads 20–30¢. "Every arb is a directional bet that eventually got arbed." | **KEEP-CORNERSTONE**: (i) existence proof for exogenous-fair + take-mispricing shape (~$2k/mo); (ii) **direct warning for our taker trade**: quotes you can see are often stale FOR A REASON (informed flow) — adverse selection is the failure mode our calibration gate and regime conditioning must survive; (iii) devig-on-favorites bias ≈ our overconfidence-on-extremes finding — fair models that underweight uncertainty at extremes overstate edge exactly where asks are cheapest; (iv) AI-code lesson: verify entity alignment (team/market matching) explicitly |
| [HN 48573307: free 5m crypto dataset](https://news.ycombinator.com/item?id=48573307) — **repo located round 2**: [kacho.io page](https://kacho.io/polymarket-5min-crypto-dataset), HF `kachoio/polymarket-5-minute-crypto-up-down-markets`, Kaggle mirror (see §4) | ~89k markets / 26.8M per-second top-of-book samples, Mar–May 2026, 7 coins, CC0, 99.8% coverage | **ACT-REF** — second validation dataset alongside OpenMarket |
| [HN 47091557: Uncovering insiders and alpha with AI](https://news.ycombinator.com/item?id=47091557) (159 pts; comments fetched via Algolia, round 5) | peterjliu's Compound-AI analysis of PM data to surface insiders; PM framed as calibrated-probability source for downstream decisions (e.g., hedge sizing). Debate highlights: **on-chain transparency asymmetry (SamPatt): trades public, orders NOT — copy-trading popular but "by the time the trade is known the edge is often gone," worsened by copy-eurs racing each other**; BoxFour: PMs fall under CFTC oversight, insider rules exist, enforcement pending; currymj: commodities framing (ag firms legally trade soy futures on private supply info); 0x3f: long-dated market prices ≠ pure probabilities (time value) | **KEEP-INSIGHT**: (i) order-vs-trade visibility asymmetry makes copy-trading alpha decay mechanically → confirms DISCARD of all copy-trading lanes; (ii) our 5m/15m crypto lane has no classic insider channel (underlying price is public and instant) — the manipulation/adverse-selection channels we documented ARE the venue's "insider" analog; (iii) legal/oversight trend worth a tail-risk watch |
| [Yahoo Finance: arb bots dominate](https://finance.yahoo.com/) (search snippet) | Bot trading exclusively BTC/ETH/SOL 15m up/down, $4–5k bets, claimed 98% win rate | DISCARD as evidence (98% WR with big size on 15m markets = likely paired-side arb or marketing); competition note only |
| [dev.to/soulcrancerdev: TWAP resolution changes bot design](https://dev.to/soulcrancerdev/how-polymarket-twap-resolution-changes-trading-bot-design-2g1o) + [trading strategies journal](https://dev.to/soulcrancerdev/polymarket-trading-strategies-2ja4) | Practitioner journal on the "current TWAP edition": signals, data pipelines, execution, risk after Aug-7 switch | **REF** (fetch pending) — closest practitioner running-log to our setup; check their signal list vs ours |
| [dev.to/soulcrancerdev: trading strategies journal](https://dev.to/soulcrancerdev/polymarket-trading-strategies-2ja4) (fetched round 6) | Live research journal on the TWAP edition, two LIVE strategies: (1) **EndCycle Sniping** — buy the late-cycle favorite at 64–84¢ in the FINAL minute of 5m BTC windows; thesis: "uncertainty compresses as the clock runs out" faster than a deteriorating book (thinner size, slower quote updates) reprices; example fill: Buy Down 84¢ at 12:24:12 in a 12:25-close window. (2) Momentum Spike Sniping after sharp repricing. Author caveat: "displayed account figures are UI snapshots, not a verified track record" | **KEEP with CONFLICT**: this is the exact final-minute zone we queued a no-entry rule for (§8.4). Their claimed edge (book lags time-decay) and the Stanford/SMU manipulation evidence (final-seconds pushes) describe the SAME window — both can be true: quoting lags create the dislocation, manipulation creates the noise. Our exclusion rule stands for the $5 wallet (small sample can't survive the noise); revisit only with verified-track-record evidence and regime conditioning. Their entries at 64–84¢ also mean they take OUR cheap-side region near expiry |
| [dev.to/nagi777: momentum spike research](https://dev.to/nagi777/polymarket-momentum-arbitrage-real-time-spike-research-3n80) (fetched round 6) | The best methodology write-up found: distinguishes PM moves carrying *new information* vs *book pressure*. Spike detector `S_t = z(M_t) + α·z(OI_t) + β·z(R_t)` (PM prob return + order imbalance + external reference return, rolling z-scores); **three-state classification: A information-backed (PM+reference+liquidity align), B book-driven (PM moves, reference flat), C reference-driven (reference moves, PM lags)**; data notes: WS gives event-level book snapshots/price changes/last-trade, CLOB price-history is 1m+ aggregated ("a one-minute candle can hide the exact sequence that created the spike") | **KEEP-CORNERSTONE (method)**: State C IS our staleness trade; the A/B/C taxonomy is directly adoptable for our observation logging (classify each quote-gap by its driver before trading it). Their z-scored spike composite is a candidate feature for the regime model. Event-level WS note supports collector v2 staying event-based |
| [blog.devgenius.io: "math that guarantees profit"](https://blog.devgenius.io/just-found-the-math-that-guarantees-profit-on-polymarket-and-why-retail-traders-are-just-providing-6163b4c431a2) | 17,218 market conditions, ~41% had single-market arb | **KEEP-INSIGHT with contradiction**: 41% vs NBA paper's 7 executable arbs — reconciles by market type (long-tail/illiquid politics vs in-game sports). Our 5m/15m crypto = high-volume sports-like regime → expect NBA-style efficiency, i.e., few mechanical arbs; our edge must be model-based. "Retail traders are just providing" framing matches the Stanford/SMU 93%-retail-losses finding. |
| [dev.to/abrownfox001: lessons from 4 strategies](https://dev.to/abrownfox001/building-a-production-polymarket-trading-bot-lessons-from-4-strategies-49k0) (fetched round 7) | Live-tested strategy evolution: (1) **15m UP/DOWN directional bot — final 60s entries at $0.80–0.99 → −37.81% live**: "paying the spread on near-certain outcomes is negative EV by construction"; (2) multi-tier scanner: pure YES+NO arb rare, "high-confidence bets often hid information asymmetry", resolution windows too narrow; (3) CEX momentum on Binance→PM lag: **paper traded on BID prices (Gamma API) but live filled at ASK (CLOB) → "fantasy profits" that vanished in production**; (4) current: **Bregman Projection Arbitrage** — Bregman divergence from the probability simplex, Frank-Wolfe allocation (step 2/(iter+2)), detects binary/multi-outcome/cross-market inconsistencies; guardrails: ≥0.5%+$0.50 profit, VWAP liquidity check, depth validation, auto-hedge partial fills, ≤10%/opportunity | **KEEP-CORNERSTONE (postmortem)**: (i) their #1 is the SAME trade as soulcrancerdev's EndCycle Sniping — claimed profitable there, −37.81% here → the final-minute favorite trade is unproven at best; our no-entry rule gains a second leg of evidence; (ii) bid-vs-ask simulator drift is the canonical killer — our ask-side entries already match execution, keep it that way; (iii) Bregman/Frank-Wolfe is the principled upgrade over naive sum<1 arb for any multi-outcome/rebalancing work |
| [dev.to/borntoup: production bot architecture 2026](https://dev.to/borntoup/building-a-polymarket-trading-bot-in-2026-websockets-order-books-clob-execution-risk-3kcd) (fetched round 7) | Production walkthrough: **market WS `wss://ws-subscriptions-clob.polymarket.com/ws/market`** with events `book`, `price_change`, `last_trade_price`, `best_bid_ask`, `new_market`, `market_resolved` (some behind feature flags); normalizer → in-memory order book (bids/asks maps, best bid/ask, last trade, timestamp) → strategy; scanner filters markets (liquidity/volume/token IDs); strict separation of strategy / execution / risk engine / position manager / monitoring | **ACT (collector v2 blueprint)**: event names + state-machine layout match what our WS-based collector v2 needs; the best_bid_ask event (when enabled) would halve our book-parsing work |
| [r/Polymarket 7-months thread](https://www.reddit.com/r/Polymarket/comments/1un85mg/i_spent_7_months_testing_every_strategy_on/) (+ [r/PredictionsMarkets crosspost](https://www.reddit.com/r/PredictionsMarkets/comments/1uoqskg/how_efficient_are_polymarkets_5min_crypto_markets/)) — u/momentum_maxi | ~1.7M candles + ~4,600 real resolved 5m windows through every strategy angle. **Momentum: resolves 74.8% but the ask is 75.3% → −0.4pt gap → "zero fillable lag"** — direction is real, the venue prices it. Strategies 5&6: band-based favorites vs cheap lottos on 4,569 real book windows (body blocked; findings via search snippets) | **KEEP-CORNERSTONE**: practitioner-scale quantification of the OpenMarket null on OUR markets. Motto: "most strategies fail not because the strategy is wrong, but because the market is already efficient by the time retail can act" — exactly why our gate is calibrated-fair-gap > fee, not direction |
| [r/PredictionsMarkets: "craziest strategy"](https://www.reddit.com/r/PredictionsMarkets/comments/1syulwz/this_is_the_craziest_polymarket_strategy_ive_seen/) | Trader **profitable with a 1.4% win rate over 34,000 trades** via order-book structure | **KEEP-INSIGHT**: maker-economics existence proof — spread-earning MMs lose most individual "trades" (adverse selection) but profit on volume. Complement to the 83%-WR-losing bot: BOTH win rate and loss rate are meaningless; only EV/trade × count matters |
| [r/algotrading: free dataset post](https://www.reddit.com/r/algotrading/comments/1u8fsg7/free_dataset_polymarket_5min_crypto_updown_order/) | Author's warning: strategies "look great on mid/top quotes and fall apart once you add queue position, spread crossing, and missed fills" | **KEEP-INSIGHT**: execution-reality discount on all backtests — our ask-side entries are the correct conservative side, but fills at size are never guaranteed |
| [Crypticorn 15-min strategy](https://www.crypticorn.com/polymarket-5-minute-strategy/) | "Wait 5 min to reveal the true move, then enter" (15m markets) | DISCARD (generic content-marketing) — but the timing instinct (early-window information is weak) matches our entry-at-open+60s design |
| [Foresight News: 试过25个方向，只活了4个](https://foresightnews.pro/article/detail/95873) (CN strategy retrospective; fetch blocked, stats via search) | "Tried 25 directions, only 4 survived": **92% of Polymarket traders lose money; bots take 73% of arb profits; 45% of crypto-category participation is bots** | **KEEP-INSIGHT**: the sober CN retrospective matches every western number we've collected; "4 of 25 survived" = ~16% strategy survival rate, consistent with our 29-trial ledger (5 keeps) |
| [Binance Square: 4-bot $500 experiment](https://www.binance.com/zh-CN/square/post/296107213210482) | Four bots, $500 each, 1 week: the **contrarian/mean-reversion bot survived** ("dumbest strategy lives longest") | **KEEP-INSIGHT**: short-run experimental evidence that reversal beats momentum in chop regimes — the regime dependence story again; also a warning that 1-week experiments prove little (our own minimum: daily-block CI over weeks) |
| [cnyes 鉅亨網: bot wallet analysis](https://news.cnyes.com/news/id/6455403) (CN) | Top profitable wallets ~70% bots; top-5% bot-suspected wallets = 75% of volume; **823 wallets with >$100k net profit since Jan 2025**; thesis "AI hasn't taken over prediction markets yet" | **KEEP-INSIGHT**: profit is concentrated but the tail is real (823 wallets >$100k) — the size of the genuine-edge population is non-trivial; consistent with maker/arb concentration rather than directional skill |
| r/algotrading: open-source MM bot (MIT) | Author: CLOB liquidity "utterly useless" in most markets | REF — liquidity depth matters for sizing; consistent with our asks 25–75¢ EV concentration and 5-share min |

- 2026-09-02: round 54 — kacho TICK-LEVEL cross-check EXECUTED (btc_ticks
  downloaded, 4.7M rows of per-second top-of-book with bid/ask/sizes; 182MB
  kept local): on overlapping markets (2 with exact-second joins ≥60
  samples; 452 matched seconds) **median |our up_price − kacho mid| = 0.005
  (half a tick), 64.8% within 1 tick, 86.9% within 2 ticks** — two
  independent recorders sampling the same book at offset moments, no
  systematic discrepancy. Complements the outcome-level check (91.56%,
  round 36) with price-level agreement. Optional deeper pass: ±2s
  tolerance join across all 2,066 overlapping markets.

### 5b. BTC5MScour full forensics (round 53, report body fetched)

- The strategy in one line: **"not about knowing where Bitcoin is going; it
  is about knowing where Bitcoin already is"** — sweep stale offers at
  $0.96–0.99 on the near-certain side in the final window (~900 trades/day,
  single slug btc-updown-5m, zero diversification).
- Economics: +$26,520 / 26 days / $1.498M deployed (1.77% ROI); **98.8% of
  capital in the $0.90–1.00 band at a 99.3% win rate** (+$18,543); the
  remaining 1.2% "gets complicated".
- **The June 21 anomaly**: a 2-hour cluster produced +$13,000 across
  adjacent windows AND the single worst market (−$2,460) — the tail risk of
  being a late-window toll collector when BTC moves violently. This is the
  concrete failure mode our final-90s exclusion rule is built against.
- Completes the late-window spectrum with hard numbers: BTC5MScour
  +1.77%/26d (toll collection) ↔ abrownfox −37.81% (same trade, wider
  entries) ↔ soulcrancer unverifiable claims ↔ 0xzkleo's ★136 public bot
  entering at 180–270s.

## 6. Kalshi / other venues

| Source | Content | Verdict |
|---|---|---|
| [rodlaf/kalshimarketmaker](https://github.com/rodlaf/kalshimarketmaker) (+ [HN thread](https://news.ycombinator.com/item?id=43073378)) | MM bot with safety controls, parallel strategy configs | **REF** — the safety-control structure (per-strategy config, kill-switch) is a checklist for our live daemon |
| [botforkalshi 30+ bots catalog](https://www.botforkalshi.com/blog/open-source-kalshi-bot-ecosystem), [Alphascope review](https://www.alphascope.app/blog/kalshi-trading-bot-github) | Ecosystem maps | REF |
| OctagonAI / yllvar Kalshi bots | AI-CLI and enterprise-style bots | DISCARD (no edge methodology) |
| [Medium: 4 strategies bots profit from (2026)](https://medium.com/illumination/beyond-simple-arbitrage-4-polymarket-strategies-bots-actually-profit-from-in-2026-ddacc92c5b4f) | MM example $1,247 on $10k/3wk (12.5%) | PENDING fetch (403) — MM-on-$10k economics matter if we scale past paper stage |

### 6b. Venue landscape beyond Polymarket/Kalshi (round 3)

| Venue | Mechanics | Verdict |
|---|---|---|
| [Limitless](https://iq.wiki/wiki/limitless-exchange) (Base) | CLOB; short-term high-frequency crypto + stock price predictions — hourly and 30–60min markets ([CryptoRadar](https://cryptoradar.com/sponsored/best-crypto-native-prediction-markets-beyond-polymarket-and-kalshi), [KuCoin playbook](https://www.kucoin.com/blog/en-the-prediction-market-playbook-uncovering-alpha-top-players-core-risks-and-the-infrastructure-landscape)) | **DEFER** — closest structural twin to our markets (CLOB, minutes-horizon, crypto); a second venue for the same staleness fair-value engine if/when we scale; already covered by pmxt's unified API |
| Myriad (BNB Chain) | Casual/embedded AMM markets; case study in [arXiv:2601.01706](https://arxiv.org/html/2601.01706v1) "Semantic Non-Fungibility and Violations of the Law of One Price" (deterministic AMM pricing rules → LoOP violations) | REF — the academic entry point for AMM-based rival venues; connects to §4b LMSR lane |
| PRDT Finance + [Alchemy's 56 Web3 PM list](https://www.alchemy.com/dapps/best/web3-prediction-markets) | More up/down-style platforms | REF (venue map) |

### 6c-2. PR&R — on-chain bot forensics site (round 13, SLIP-ME report fetched in full)

[Poly Research & Robotics](https://www.polyresearchrobotics.com/reports/slip-me) publishes systematic wallet-forensics reports on Polymarket traders (reports 001+, incl. SIRMARTINGALE, ohanism; + a Strategy Database and Data Resources section). **The highest-quality external analysis found in this sweep** — every fill mapped, two-leg P&L decomposition, reproducibility grading.

**SLIP-ME report (Report 009, 2026-05-01) — the definitive 5m-BTC bot anatomy:**
- 188,932 trades / 4,725 markets / 23 days; 4,723 of 4,725 markets = btc-updown-5m (pure specialization; the 2 outliers are a routing bug). Flat 6,500–9,700 trades per UTC hour — **no session/weekend edge**.
- **Net +$111.8K; ROI +2.59% on $4.32M deployed; win rate 53.4%; 22/22 green days.**
- **Two-leg decomposition**: quotes both YES+NO on 98.6% of markets (~40 fills each) → the "spread leg" **bleeds −$97,523** (median paired cost $1.0183 — above par!). The directional leg — **loading the winner in the final 90 seconds** as the BTC tick carries one side toward certainty — earns **+$204,450**. Presence costs money; information + timing pays.
- 5×+ skewed markets: dominant side wins **99.8%** of the time.
- Reproducibility grade: "Logic yes, scale harder" (logic reproducible, capital scale is the barrier).
- **Resolves the 101¢/rebate question empirically (action #9)**: pair-buying at market costs $1.0183 > $1.00 → mechanical pair-arb at taker prices is NET NEGATIVE; the "101¢ per pair" marketing requires maker-rebate flow, which SLIP-ME (a buyer) doesn't earn.

**BONEREAPER report (fetched in full, round 19) — the direct fair-value-MM competitor, fully forensicated:**
- Scale: 1.34M trades / 22 days / 14,168 resolved markets (~61k trades/day, 99.8% buys, median ticket $5.56, power-law sizing — top 5% of fills carry 57.3% of capital). **+$443,754 realized (+1.527% on $29.09M deployed), 22/23 green days, 100% of rolling 7/15-day windows green.**
- Mechanics: both-sides MM on 5m+15m crypto binaries — pairs both outcomes on **96.7%** of markets within **10s median hedge lag**, almost never sells (0.08%), holds everything to resolution; lets the dominant side run when its **USDC-imbalance dominance ratio** warrants.
- **The calibration signature (the key validation standard for us)**: dominant-side win rate climbs **smoothly 59% (1.0–1.5×) → 97.7% (5×+)** as conviction grows, and entry-price-band win rates track implied probability **within ~2 points across the full $0–$1 range** — "a calibration signature you only get from a working model." This is exactly the standard our fair-rebuild must meet (ECE-style, per price band, per dominance bucket).
- Observed vs inferred: fair-value source not in the trade data (inferred external BTC/ETH reference feed); fill-and-burst execution; the 2026-03-29 red day is the regime to characterize (only −$2.5K).
- **Window caveat**: Mar 25–Apr 16, 2026 straddles Fee-Structure V2 (Mar 30) and is entirely pre-TWAP — economics reflect the older fee curve and snapshot settlement; our current regime differs on both.
- PR&R's own follow-ups worth adopting: ratio ≥1.5× filter shadowing at 1% scale; replicate the fair-value layer against the wallet's entry timestamps; stack ratio+paired-cost filters; characterize the red-day regime.
- **Tail finds**: (i) **Mean-Reversion Guide G·001 — "The HFT mean-reversion playbook applied to the BTC Up/Down 15-min market, with worked code and validation"** — top-priority next read alongside BONEREAPER; (ii) PR&R data store sells **full-depth BTC/ETH/SOL/XRP/BNB/DOGE Up/Down books at 1-second cadence** — a richer-than-top-of-book source for our markets (dataset cross-validation queue); (iii) KCH123 = high-volume momentum scalper on crypto up/down books (watch); LIL222 = patient low-frequency directional.

**G·001 worked example + real lesson (round 21, fetched):** the 15-min BTC bot loop closes each 15-min bar via `last_trade_price`, exits any open position at market, subscribes to the next market, takes `signal = −sign(log_return)`, **skips unless |modeled EV| > spread_cost + buffer**, enters 2% of capital via marketable limit at 1-tick slippage, and re-runs validation weekly. Illustrative economics: 35,040 trades/yr × $0.40 net/trade ≈ **$14K/yr on $10K capital ("the boring middle")**, 3–5×/yr with Kelly-ish reinvestment — explicitly boxed as illustrative, contingent on (a) the edge being alive, (b) execution tightness, (c) regime stability. The real lesson: the BCH example's 52% win rate compounding to 21× comes from "a tiny statistical edge, traded frequently, with compounding." Note their exit at next bar open = the sell-early pattern again, not hold-to-settlement.
**BTC5MScour report (Jul 9, 2026 — the most recent PR&R report; fetched round 21):** 23,638 trades / 2,744 markets / 26 days, **+$26,520 at +1.8% ROI on $1.50M volume — but win rate 95.8% with both-sides rate 0.3%**: a pure single-sided deep-favorite buyer (late-window near-certain side). The archetype completes the picture: the EndCycle/favorite trade CAN profit (+1.8%/26d) but only at razor margins — consistent with abrownfox's −37.81% as the unfiltered version and soulcrancer's claims as the condition-gated version. Avg position $63.
**KCH123 report (Report 002; fetched round 21):** sports-directional whale — $76.5M notional, 78,148 trades, 60.9% WR, filtered P&L only **+$25,654** (0.03% of notional). Value for us is methodological: PR&R's pay-vs-bleed filter decomposition (which market subsets carry the edge) is the same discipline as our 24-bucket regime evaluation, applied to a wallet. Sports lane — low direct relevance.

**PR&R Mean-Reversion Guide G·001 (round 20, method fully captured):** [Stealing HFT's mean reversion playbook](https://www.polyresearchrobotics.com/guide/mean-reversion-polymarket-bot) — free, with worked code and a worked example on the BTC 15-min Up/Down market. Method (11 steps): prices → log returns → lag-1 autoregression → **sign encoding (magnitude deliberately discarded)** → group by prior-move direction → compute conditional next-return stats per bucket → **out-of-sample validation pipeline** → signal → trade → evaluate. Framing: pro mean reversion is not Bollinger Bands — it is "recent moves get unwound" measured as conditional probability. Two claims worth keeping: (i) **bounded probability prices make reversion mechanically more likely** (a market at 0.85 cannot trend to infinity); (ii) most published strategies overfit patterns that evaporate by deployment — hence the OOS pipeline as the core discipline. Worked-example result numbers sit deeper in the page (re-read next round); method is the transferable part. **Relevance to us**: this is the conditional-reversal measurement our chop-regime findings and Binance-Square contrarian experiment point to, formalized for our markets; the sign-lag conditional stats are a cheap addition to our next evaluator run.

**PR&R data store + 94-resource directory (round 25, both fetched):**
- **Data store** ([/data](https://www.polyresearchrobotics.com/data)): pre-built backtest datasets as Parquet ZIPs. **Crypto: full-depth Up/Down books (BTC/ETH/SOL/XRP/BNB/DOGE), 5m+15m cycles, 1-second cadence — each coin folder bundles the order books WITH Binance 1-second klines AND the Chainlink reference feed** (the complete fair-model input bundle; $25/mo or $50/3-mo). Free samples: 80 cycles of BTC/ETH/SOL/XRP books (9 MB) + sports/esports/weather samples, free with account + Discord verification.
- **Data-resources directory** ([/strategies/resources](https://www.polyresearchrobotics.com/strategies/resources)): the 94 bot-building feeds, categorized — crypto exchange WS/REST (Binance spot+futures WS, Coinbase, Kraken v2, Bybit V5, CoinGecko, CoinMarketCap, CoinDesk/CCData), oracle feeds (**Chainlink Data Streams WS, Pyth Hermes WS+REST, Polymarket RTDS**), sports odds (TheRundown, Sportradar, OddsPapi, SportsGameOdds, The Odds API, ESPN hidden scoreboard, MLB GUMBO, API-Sports), esports (PandaScore, GRID.gg, Riot, Steam Dota2, HLTV, Abios, OpticOdds), weather (NWS, Open-Meteo, Tomorrow.io, Meteomatics, AccuWeather, Weatherbit, Visual Crossing, Xweather, WeatherFlow), macro (FRED, BLS v2, Treasury Fiscal Data).
- **Verdict: KEEP-CORNERSTONE (input-feed map)** — for our lanes the additions are Chainlink Data Streams WS + Polymarket RTDS (both already action-queued) and Pyth Hermes as an alternative oracle cross-check; the weather/macro/sports feeds map the other verticals' edge sources (gghff-style). Free samples noted as the zero-cost validation path for the data bundle.

**RN1 operator manual (round 29 — the corpus's most complete strategy spec):** 1.40M rows over Oct 2025–Mar 2026, $131.85M notional, 38,975 conditions, 99.985% buys, median ticket $9.84, edge category "spread + lean". Structure: both-sides accumulation, bursty automated inventory-aware execution, **2.0× dominance ratio as the side-weight threshold** (the concrete parameter behind BONEREAPER's 1.5× and ohanism's paired-dominance), with sections for market selection, entry/execution, pricing/spread, dominance ratio, position sizing, exit behavior, risk, operational rhythm, a rebuildable blueprint, and a confidence map separating observed from inferred. The 18-section template is itself the best available spec format for documenting a live trading engine. Remaining ~19 sports/politics reports: method sections sampled via this + the descriptor sweep — they run the same archetypes (spread+lean, directional, MM) on other verticals; recorded as classified, watch for new entries only.

**PR&R classification COMPLETE — all 36 reports (round 24):**
- **bonereaper-update**: 44 days (vs the original's 22), 2.69M trades / 37,228 markets, +$458,493 but at **+0.2% ROI — marginal ROI diluted ~7.5× as the fair-value MM scaled up**. The single most important new data point: even the best forensicated bot's edge decays with size (capacity constraint on the fair-value MM lane).
- **sinenooneei**: 2,057 trades / 265 markets, **+$349,407 at +16.3% ROI** — the new ROI leader, at LOW frequency (a concentrated specialist, not a bot grid); reinforces that high ROI lives in selectivity, not throughput.
- **doggystyie**: 172,530 trades / $5.9M, **−1.0% ROI** — the first documented losing big bot; negative confirmation that scale without edge just multiplies bleed.
- Convergence confirmed across the full set: 080BEc +1.5%, 0x04b6d7 +0.7%, B1C58 +1.6%, Ratue +1.9%, RandomGameBet +1.9%, X-MoneyForWhiskas +0.9%, NeverSmiling +0.4% — the 0.3–9.9% band now holds with sinenooneei (+16.3%) as the sole concentrated exception.
- No unread report is BTC-up/down-specific beyond the five already deep-read (SLIP-ME, SIRMARTINGALE, BONEREAPER, ohanism, BTC5MScour) — the crypto lane of the PR&R corpus is fully mined. Remaining unread reports are sports/politics/other-vertical (on watch).

**Deep-reads (round 23): vidarx + gghff.**
- **vidarx** (Trader Analysis, Apr 19): $11.99M volume, 1,025,590 BUY / 8 SELL, **win rate 48.4%** (below coin-flip) yet +$103,949 realized — a pure spread/inventory MM whose profit is invisible in surface metrics and only appears in the conviction-curve decomposition. Third documented case (after SLIP-ME's 53.4% and the 1.4%-WR maker) that win rate carries zero signal about edge quality on these books.
- **gghff** (Trader Report, May 13): **not crypto — a weather bot**. The entire 13,004-trade book is daily temperature-distribution markets (Singapore, Miami, Warsaw, Houston, London, Seoul, …): buy every bucket in a city's temperature distribution, weight toward the most probable outcomes, collect at settlement. +$10,926 at **+9.9% ROI** — the highest high-frequency ROI in the PR&R set, earned from a meteorological-model edge (better forecast distributions than the market's), not from microstructure. Confirms the weather category of the 297-strategy database is genuinely profit-bearing for model-advantaged traders — an entirely different edge class (information/model quality) from our staleness lane.
- Classification now 16 of 36 reports.

**PR&R classification sweep (round 22, descriptors read for 8 more reports — 14 of 36 total):**
- **vidarx**: always-on crypto bot, 1,025,598 BUY tickets / 8 SELLs, $11.99M deployed, +$103,949 — "**a conviction curve that suggests a real edge underneath the spread book**" → same class as BONEREAPER; top-priority unread alongside gghff.
- **gghff**: 13,004 trades / 23d, **+9.9% ROI** — the highest ROI among high-frequency wallets.
- **exitliquidty**: 1,234 trades / 73 markets, **+$330,940 at +86.4% ROI** — concentrated whale, different species from the bots.
- billbenter2026: 892,903 trades, +0.7% · gabigol: 324,515 trades (likely the "Gabagool" $100k/mo Reddit bot), +2.1% · sixx7: 586,261 trades, +0.9% · pbot-6b: 65,567 trades / 9,843 markets, +4.7% · flippingsharks: 89,684 trades, +0.3%.
- **THE CONVERGENCE INSIGHT (now empirically solid across 14 forensicated wallets)**: every high-volume bot on our markets runs **0.3–9.9% monthly ROI** on deployed capital, with win rates 38–96% — the entire "AI bot makes millions" narrative dissolves into single-digit monthly returns at scale, won through frequency × tiny edges × discipline. BONEREAPER (+1.5%) and ohanism (+3.0%) are typical, not exceptional. Bankroll expectations for any real deployment should be set accordingly.

**PR&R reports index (round 19): 36 trader reports, grouped by strategy.**
- Read so far: SLIP-ME (009), SIRMARTINGALE (008), ohanism — 3 of 36.
- **Top-priority unread: BONEREAPER — "Fair-value market maker on 5- and 15-minute crypto up-or-down binaries"** — the direct competitor running OUR strategy class (exogenous fair → MM quotes); its read is the highest-value next item in the PR&R lane.
- Also flagged by name: BTC5MScour (5-minute BTC specialist), plus ~30 other high-volume wallet reconstructions (Vito3Corleone, Michi1, LBTrading, NeverSmiling, Bonereaper Update, etc.) on watch.

**PR&R Guides index (round 18, 12 guides) + spread-capture guide deep-read:**
- [How to Build a Spread-Capture Bot for 5-Minute BTC Markets](https://www.polyresearchrobotics.com/guide/how-to-build-a-spread-capture-bot): the maker-mode primer for our exact markets. **Key mechanism — time-separated pairing**: accumulate both sides on their *separate* dips so the blended pair cost lands below $1.00 even though simultaneous pairing never does (this REFINES the round-17 pair-cost conclusion: SLIP-ME's $1.0183 was simultaneous; sequential dip-buying with a paired-cost ceiling is the viable form). Mechanics covered: paired-cost gate computation, inverse-weighted allocation to minimize blended cost, per-leg dip entry with ceiling enforcement, explicit "no exit management" design (with a section on what happens if you add one), session scheduling, edge-longevity monitoring, capacity limits. Honest framing: "not a ready-made profitable bot."
- Other guides: "Watch a Better Trader, Then Copy Their Edge" (live comparison loop turning winning wallets into bot improvements — the forensics workflow as a process), "How Quants Read Market State" (market-state vs trend-lines), Weather Bot build.
- **Impact on the action queue**: the sequential-dip pairing with a blended-cost ceiling is THE concrete maker-mode entry design for any future maker experiment; pairs with strategy K's sequential grid and ohanism's paired-dominance signal.

**PR&R Strategy Database + site facts (fetched round 16):**
- [Strategy Database](https://www.polyresearchrobotics.com/strategies): **297 cataloged strategies**, sortable by technique and market category (crypto, sports, esports, weather, macro, stocks, politics, mentions…), each with a full write-up (mechanics, requirements, applicable Polymarket markets, needed datasets). Arbitrage section alone: 34 entries — notable for us: **Pre-Resolution Oracle-Lag Lock-In** (our staleness trade under another name), Resolution-Source Scrape-to-Order First-Mover (strategy H's law applied to resolution feeds), Settlement-Timing Funding Arbitrage, Kalshi-Polymarket Identical-Contract Relative Value, Split/Merge Redemption Arbitrage (CTF), Multi-Outcome Overround Shorting (Dutch-book lay).
- **94 bot-building data resources** (APIs, websockets, RSS, data providers, live-odds services) — the richest tooling map found.
- **TWAP Price Feed product** (Data Store) — venue-native settlement-series access; a candidate source for action #10 (fair-model TWAP input) if licensing is reasonable.
- Business model (via /llms.txt): guides, trader reports, and strategy database are **free**; funded by the historical-data store; no affiliate deals; 1,000+ member Discord; site updated 2026-08-27. Every page serves `Accept: text/markdown` / `.md` suffix (agent-friendly).
- **Deep-reads of 5 strategy pages intersecting our lanes (round 17, all fetched via .md):**
1. **Pre-Resolution Oracle-Lag Lock-In (#061)**: buys the winner during UMA's proposal/dispute lag on real-world events. **NOT applicable to our lane** — our crypto markets auto-resolve via Chainlink TWAP with no proposal window; the oracle-lag edge class exists only on UMA-resolved markets. Precision gained: our staleness is *feed-vs-book* lag, not *oracle* lag.
2. **Resolution-Source Scrape-to-Order First-Mover (#138)**: poll the canonical source named in the resolution rule, pre-stage signed orders, fire on change. For our markets the canonical source (Chainlink stream/Binance) is already our fair input — this page is the general form of our architecture; its novel bits are pre-staged orders and ToS-legality review.
3. **Kalshi-Polymarket Identical-Contract RV (#054)**: hold-to-settlement cross-venue lock; requires resolution-criteria reconciliation. **Crypto up/down caveat**: the two venues settle on DIFFERENT indices (Chainlink stream vs CF Benchmarks BRTI) → basis risk makes them not strictly identical contracts; pure RV applies to same-print markets (CPI/Fed).
4. **Settlement-Timing Funding Arbitrage (#056)**: near-certain long-dated markets under $1 = underpriced cost-of-carry; annualized-yield rotation. This operationalizes the round-9 capital lock-up paper. Minutes-horizon lock-up → N/A for us.
5. **Split/Merge Redemption Arbitrage / CTF (#053)**: correct mechanics — mint $1 pair and sell both halves when BIDS sum > $1; buy both when ASKS sum < $1 and redeem (PR&R's summary garbles the directions). On liquid crypto books, competed to SLIP-ME's $1.0183 pair cost → viable only on illiquid markets after gas.
- **Cross-cutting conclusion**: none of the five apply to the 5m/15m TWAP lane — Chainlink auto-resolution (no oracle lag), minute lock-up (no carry), and a fee curve plus competition (no pair arb) make our lane structurally distinct. Our edge class (calibrated feed-vs-book gap within TWAP-settled short windows) is confirmed rare in the taxonomy — consistent with it being unclaimed.

Verdict: **KEEP-CORNERSTONE (reference hub)** — the 297-strategy catalog is the comprehensive map of the technique space; deep-reads of the ~10 strategies intersecting our lanes (staleness, TWAP, MM, crypto up/down) are queued.

**ohanism report (Trader Report, 2026-05-08) — the third archetype, hybrid at scale:**
- 694,439 trades / 37,982 markets / 27 days (~21,800/day, 24/7, BTC/ETH/SOL/XRP Up/Down = 99.2% crypto); **+$258,687 on $8.57M deployed = +3.02% ROI**; 64.4% win rate; avg position $14.
- **Hybrid MM + directional**: pairs both sides 33.3% of the time (locks spread when the pair is cheap), expresses directional views the other 67%, **using the dominance ratio on paired fills as the conviction signal**.
- Third design point on the maker↔directional spectrum (SLIP-ME: directional-in-disguise; SIRMARTINGALE: pure latency taker; ohanism: explicit hybrid). The paired-dominance signal — how lopsided your own two-side fills are — is a novel conviction metric worth remembering for maker mode.

**SIRMARTINGALE report (Report 008, 2026-04-29) — the working latency-arb archetype:**
- +$119.6K / 28d, **ROI +82.95%** on ~$361K turnover, 23,440 trades / 3,996 markets, 38.4% win rate, 26/27 green days.
- Directional micro-arb on 5m+15m BTC (78%) / ETH (22%) Up/Down only: watches the spot tape, fires a directional buy when one side of the book prices under his fair value, then **unloads aggressively into orderbook strength before resolution** — an arbitrageur of the few-second spot-tape↔CLOB lag, NOT a hold-to-settlement trader.
- Bounded sizing throughout ($366 max fill, $134 P99) despite the Martingale name; 2026 era: this is the lane dynamic taker fees compressed but small capital with fast exits still works.
- Reproducibility grade: "Hard — spot feed + low latency" (vs SLIP-ME's "logic yes, scale harder").
- **Design contrast for our records**: SLIP-ME = big capital, presence quoting, holds to resolution, final-90s loading; SIRMARTINGALE = small capital, no presence cost, sells the reversion once the book reprices. Our taker model is closer to SIRMARTINGALE's entry logic (fair-vs-price gap) but holds to settlement — the "sell into the catch-up" exit is a candidate variant to simulate before our next wallet checkpoint.

Verdict: **KEEP-CORNERSTONE (forensics method + facts)**. (i) The final-90s zone is now triple-documented (manipulation study, sniper bots, SLIP-ME's profit engine) — it is where real money operates with slip-tolerant tooling; our no-entry rule stays correct for a $5 paper wallet but the zone deserves explicit modeling if we ever scale. (ii) Surface metrics mislead: a "53.4% WR maker" is actually a directional late-loader bleeding spread — the two-leg decomposition lens should be adopted for our own wallet reporting. (iii) Presence-based quoting as an information cost is a maker-mode design input.

### 6c. Whale tracking / analytics tools (round 3)

| Tool | What it does | Verdict |
|---|---|---|
| [sporeking's corrected whale tracker](https://dune.com/sporeking/polymarket-whale-tracker-corrected-deep-dive-fixed-charts) + [order-owner maker/taker version](https://dune.com/sporeking/polymarket-whale-tracker-corrected-order-owner-maker-taker) | Dune dashboards on OrderFilled events; the corrected one **detects whales buying both outcomes in the same binary market** (paired-arb / rebate-farming detection) | **REF→ACT(maker check)**: the both-sides detector is exactly the empirical test for the 101¢/rebate-farming question; SQL approach reusable if we join Dune |
| [polymarketanalytics.com](https://polymarketanalytics.com/) | Free real-time whale/top-trader/wallet-PnL tracking across 1M+ wallets, live odds, OI, volume | REF (future smart-money feature; FKPolyTools equivalent, EN-side) |
| [Dune leaderboard/whale dashboards](https://dune.com/genejp999/polymarket-leaderboard), [lujanodera analysis + Whalewatchpoly](https://dune.com/lujanodera/polymarket-analysis), [polymark.et dunedata](https://polymark.et/product/dunedata), [Kairos](https://kairos.trade/compare/polymarket-analytics) (>$10k fills, 30d PnL), [SightWhale guide](https://www.sightwhale.com/blog/en/polymarket-whale-tracking-tools-2026-complete-guide), [tools guide](https://polymarkets.co.il/en/guide/tools-resources/) | Whale/sentiment analytics cluster | REF (map; low priority at our scale) |
| [aarora4/Awesome-Prediction-Market-Tools](https://github.com/aarora4/Awesome-Prediction-Market-Tools) (incl. Polytrackerbot — Twitter bot tracking high-conviction whale wallets) | Curated awesome-list | REF (source map for future sweeps) |

### 6d. Twitter/X lane findings (round 3)

- [r/algotrading: "Polymarket bot posts?"](https://www.reddit.com/r/algotrading/comments/1uo4cin/polymarket_bot_posts/) — practitioners report **hundreds of likely fake Twitter posts** about Polymarket algos and copy-trade accounts. **KEEP-WARNING**: the social "inspiration" lane is heavily polluted; only open-source (verifiable code) and academic (verifiable method) sources earn weight — this catalog's weighting rule going forward.
- [0xLeon on X](https://x.com/Leoninweb3/status/2017081662195323144): 3.7% of users (~54k addresses) generate 37.44% of Polymarket volume — independent corroboration of the Binance Square bot-war stat already in §3.
- [HN: Uncovering insiders and alpha with AI](https://news.ycombinator.com/item?id=47091557): argues real alpha is in **microstructure/cross-venue discrepancies (Polymarket vs Kalshi)** rather than event prediction — consistent with our positioning.
- X trending "AI bots dominate Polymarket" posts ($500→$600 claims): DISCARD (marketing).

### 6e. Japan / Korea lane — resolved as structural negative (round 5)

- [Japan Times](https://www.japantimes.co.jp/business/2026/05/22/companies/polymarket-japan-prediction-markets/) + [Bloomberg](https://www.bloomberg.com/news/articles/2026-05-22/polymarket-is-said-to-seek-japan-market-approval-in-global-push) (2026-05-22): Polymarket seeking Japanese government approval, official entry targeted ~2030.
- [StartPolymarket country guide](https://startpolymarket.com/countries/japan/): Japan is a legal grey area — Polymarket runs **"frontend close-only"** there; [MetaMask's PM integration](https://metamask.io/prediction-markets) explicitly unavailable in Japan.
- Domestic: Gumi / Gc Labs exploring Japan-based prediction-market offerings; no Japanese practitioner bot community exists yet to mine.
- Korea: strict gambling regime; no meaningful PM trading community surfaced across searches.
- **Verdict: LANE CLOSED (negative)** — the absence of JP/KR practitioner content is regulatory, not a search failure. Revisit only if/when Polymarket's Japanese approval lands (~2030) or Gumi ships.

**6f-2. Venue-lane completion: PRDT / Opinion / Predict.fun (round 28):**
- **PRDT Finance** ([learn hub](https://prdt.finance/learn)): 1–30 minute Up/Down rounds, **fixed-time fixed-payout pool-odds model** — the platform sets payouts from pool-side odds; NOT a CLOB (no book, no maker mode, house edge built into the payout). Binary-options structure; DEFERRED (our taker logic would port but the pool's built-in edge makes it a different risk class; 80% revenue sharing for PRDT stakers).
- **Opinion** ([docs](https://docs.opinion.trade), opinion.trade): **a genuine CLOB** on BNB Chain — order-book depth, trade prices, candles via a published [`opinion-clob-sdk`](https://pypi.org/) (Python); macro focus (Fed/CPI/jobs) plus crypto Up/Down (ETH/BNB/BTC price levels); YZi Labs-backed, ~$190.6M volume at launch, #3 among prediction markets. **Third CLOB venue** for the staleness engine; dr-manhattan already supports it.
- **Predict.fun**: BNB-native, "**Polymarket-style order book exchange**", launch partner for Binance Wallet's in-app prediction market; acquired Probable. **Differentiator: yield-bearing collateral** — funds routed through Venus Protocol earn yield while parked (≈25% maker rebate on filled orders also mentioned). **Model implication**: yield-bearing collateral mechanically reduces the cost-of-carry that the capital-lock-up paper (round 9) says explains most long-dated "mispricing" — on Predict, near-certain long-dated contracts should price TIGHTER to $1 than on Polymarket. Our minutes-horizon lane is unaffected, but this is a real input for any cross-venue fair model.
- Also noted: Polymarket itself is now live on BSC via partnership, with minute-level "BNB Up/Down 5m" markets — the venue is expanding the exact product we trade.
- Drift checks clean (arXiv 2608.30999; PR&R still 36 reports).

### 6f. Kalshi crypto short-duration contracts — cross-venue comparison (round 8)

- [Kalshi 15-min crypto category](https://kalshi.com/category/crypto/frequency/fifteen_min) + [hourly](https://kalshi.com/category/crypto/frequency/hourly) + [BTC main](https://kalshi.com/category/crypto/btc): **KXBTC15M** up/down contracts on BTC/ETH/SOL/XRP/BNB, 24/7, per-market volume >$1.1M, "up to 6x leverage" display.
- Settlement: **CF Benchmarks BRTI** (CFTC-regulated index administrator) with a **60-second averaging window** at settlement ([KXBTC15M explainer](https://predictionmarketspicks.com/articles/kalshi-bitcoin-15-minute-markets)) — structurally identical to Polymarket's post-Aug-7 60s TWAP for 15m markets.
- Community: [r/algotrading Kalshi 15m indicators thread](https://www.reddit.com/r/algotrading/comments/1ru03le/is_anyone_interested_in_discussing_a_kalshi_15/).
- **Verdict: DEFER→STRATEGIC**: a second venue running the SAME product shape. Our staleness fair-value engine is venue-agnostic (needs: window, strike, settlement series, quotes) → Kalshi 15m is the natural expansion or cross-venue hedge (compendium strategy B); CFTC regulation/KYC = different counterparty and fee regime (Kalshi's fee formula is the same 0.07·p·(1−p) shape). Record as the roadmap's "second venue" candidate.

### 6g. Compendium strategy deep-reads D/G/K (round 8, fetched in full)

- **D — Market Making**: revenue = spread capture + Maker Rewards + position rewards (4% APY on eligible markets); rule of thumb **~0.2% of traded volume becomes profit** ($1M monthly volume ≈ $2k/market); core risk = inventory risk (lower in low-vol markets). poly-market-maker's two modes (Bands around mid / AMM-curve by inventory) + poly-maker's market-discovery scoring (volatility at 3h/24h/7d/30d, reward score by distance-from-mid) are the reference implementations. **REF→maker-mode checklist**.
- **G — "Bond" strategy (buy >$0.95, hold to settlement)**: claimed 520%+ annualized is naive (assumes instant turnover, ignores black swans — the UMA oracle attack collapsed $0.99 contracts to $0). **Key microstructure fact: 90%+ of $10k+ orders occur in >$0.95 markets** — whale flow concentrates in near-certainties, where adverse selection is worst. Tools: [guzus/dr-manhattan](https://github.com/guzus/dr-manhattan), pmxt. Our 5m/15m lane settles too fast for bond economics; DISCARD for us, KEEP the whale-flow fact.
- **K — Volatility grid (sequential two-leg)**: in 15m markets, buy UP at panic price, then DOWN after stabilization, total < $0.95 → guaranteed >$0.05 at settlement; range-bound chop only, stop on trends, mind dynamic taker fees. Time-separated rebalancing arb where leg 1 is a directional catch. **REF** — a variant of our staleness trade with a guaranteed-outcome exit; relevant if panic dislocations appear early in windows (our EV-by-gap monotonicity hints at this).

## 7. Practitioner tactics (single lines worth keeping)

- @w00dsbot (Threads): "Wait for 5-minute BTC contract mispricings (<$0.35)" —
  cheap-side entries only. **Maps directly onto our finding**: our EV lives at
  asks 25–75¢ with calibrated gap; <$0.35 mispricing entries ≈ our gap>fee
  filter on the low side. Independent confirmation of the entry region.
- Chop kills trend-following bots (r/algotrading) = our vol-regime buckets.
- MM beats directional on these venues per multiple independent sources —
  our answer is intermediate: we *take* stale quotes with a calibrated fair
  (taker), but a maker mode is the documented path if taker edge decays.

### 7b. soulcrancerdev's TWAP-bot design guidance (dev.to, fetched 2026-09-02 — closest external articulation of our architecture)

- Target = "probability that a specific **resolution process** produces one
  outcome," not the terminal price. Alignment rule: signal source, execution
  model, and resolution model must describe the **same variable**.
- Causal chain: Spot move → TWAP evolution → resolution probability →
  Polymarket price. "A spot feed showing +1.0% may overstate what the TWAP
  benchmark has captured" ("benchmark mismatch").
- Path dependence: an early move affects the average differently than a late
  one (time-weighting) — matches our running-average fair math and its
  final-window correction item.
- Pipeline: Market rules → reference data → TWAP reconstruction → probability
  model → market price → execution → resolution audit; their model ladder
  (A) terminal direction → (B) spot vs start → (C) estimated TWAP vs start →
  (D) TWAP probability + book = our own evolution from s023 to staleness fair.
- Treat the Chainlink stream as its own data source with its own methodology
  (displayed data may be delayed) — independent support for collecting the
  venue-native TWAP series (action #10).
- Loss-debug taxonomy: market interpretation / reference data / TWAP estimate /
  calibration / execution / variance — without it "every loss looks identical."
  Worth adopting verbatim in our WALLET_LIVE day reports.

## 8. Standing insights & action queue (updated as sweep continues)

### Insights (evidence-backed)

1. **The venue-feature lane is independently falsified** (OpenMarket: 43-feature
   walk-forward model AUC 0.8377 < naive mid 0.8405; −0.116/trade after costs;
   mirrors our Phase-B/RL nulls and the litreview Tier-1 RESETs). Our remaining
   lanes — exogenous fair-value + calibration (staleness) and maker economics —
   are exactly the ones the external record does NOT refute.
2. **Our overconfidence finding now has a mechanism**: venue settles the final
   30s (5m) / 60s (15m) average; our CLT fair models a running TWAP over the
   whole remaining window → variance understated → fair too extreme → isotonic
   layer has been silently fixing it. Fixing the fair model should sharpen the
   gate (less reliance on the calibration remap).
3. **Fee model confirmed exact** (crypto feeRate 0.07, `fee=C·rate·p·(1−p)`) —
   one less unknown; news summaries disagreeing with docs are wrong.
4. **The final ~90s of each window is a contest zone** (snapshot-era: $8.2M
   extraction; TWAP-era: sniper bots target it) — entries there carry
   manipulation noise; 93% of manipulation losses fell on retail.
5. **Regime dependence is consensus** (r/algotrading chop finding ≈ our vol
   terciles; aulekator's divergence processor; sniper bots' boundary-proximity
   condition).
6. **Existence proof for our trade shape**: HN arb bot (~$5k/3mo on 3,858 bets)
   = exogenous fair (de-vigged sportsbooks) + take venue mispricing. Same
   structure as ours (exogenous fair = CLT on underlying), different signal.
7. **Arb lane compression** (12.3s→2.7s windows; sub-100ms pipelines) → do not
   chase mechanical arb on our markets; NBA-style efficiency expected.
8. **Maker rebate economics** (20% of crypto taker fees redistributed; "101¢
   per pair" claims) → maker mode is the documented path if taker edge decays.

### Action queue

| # | Action | When |
|---|---|---|
| 1 | Fee model: no change (confirmed). Note fee-introduction date as sample-consistency footnote if findable | done |
| 2 | Add settlement-regime flag (snapshot vs TWAP-30s/60s, boundary 2026-08-07) to any updown-label analysis; all our *quote* data is already post-switch | next evaluator run |
| 3 | Rebuild fair model with final-window averaging (Var: d≥w → σ²·w/3; d<w blend toward European) in `staleness` fair + live wallet; re-run calibrated re-test | next research session |
| 4 | Live wallet: queue "no entries in final 90s" rule — do NOT change mid-experiment (the running $5/day test must stay strategy-consistent); apply at next checkpoint | after wallet test window |
| 5 | Read `min_order_size` per-market from CLOB API in wallet/evaluator instead of assuming | next wallet change |
| 6 | Cross-validate our collector join/labels vs OpenMarket HF archive (overlap: Feb–May 2026) | next research session |
| 7 | ~~Locate HN 48573307 free 5m dataset repo~~ DONE: kacho.io / HF `kachoio/polymarket-5-minute-crypto-up-down-markets` (26.8M 1s top-of-book samples, Mar–May 2026, 7 coins, CC0) | done |
| 8 | Read Taker Rebate tiers + Moonsat 6-types + Medium build logs (fetch-blocked); r/Polymarket 7-months full body (core findings captured via search snippets) | next session |
| 9 | Maker-rebate math check (can paired YES+NO + 20% crypto rebate exceed par?) | deferred (maker mode only) |
| 10 | Add collector job for the venue's Chainlink TWAP/Data Streams series (replaces Binance proxy in fair value; removes basis risk) | next session |
| 11 | Check `market.trading.secondsDelay` for our 5m/15m markets via CLOB API; if delayed matching applies near settlement, exclude those windows | next session |
| 12 | Ledger: record settlement-dispute/manipulation incidents as tail-risk events | ongoing |
| 13 | Adopt soulcrancerdev's loss-debug taxonomy in WALLET_LIVE day reports (interpretation/reference/TWAP-estimate/calibration/execution/variance) | next wallet report |
| 14 | New feature candidate from the practitioner record: **realized-TWAP-progress** (fraction of final-window move already realized + crowd-skew) — Novals83's conditional gate and soulcrancerdev's path-dependence both point here | next research session |

### Sweep log (append-only)
- 2026-09-01: batch 1 (venue fees/min-order, GitHub EN retry, CN ecosystem,
  practitioner threads) → §1–§3, §7.
- 2026-09-02: batch 2 (docs deep-read, arXiv 2025–26 wave, Reddit, Kalshi,
  Gitee verification, Medium) → §4–§6.
- 2026-09-02: batch 3 (settlement-manipulation study + TWAP-switch timeline,
  OpenMarket full read, fee formula confirmation, dev.to lane, HN threads,
  crypto.news/CoinDesk/Genfinity, Benjam1nCup/aulekator/KaustubhPatange repos)
  → §1a, §2, §5, §8. OPEN: taker-rebate detail, HN thread bodies, Medium 403s
  (benjamincup/moonsat/kaustubhpatange), r/Polymarket 7-months body, Twitter/X
  direct search (timeouts), LMSR/AMM academic lane, Yahoo article.
- 2026-09-02: round 2 — fetch-blocked items cleared via reader/curl/Algolia:
  soulcrancerdev TWAP-design article (§7b), Maker Rebates table (§1, crypto
  20%), HN 5m-dataset repo identified = kacho.io/CC0 (§4), LMSR/AMM academic
  set (§4b), 7-months thread core findings via search snippets (74.8% vs 75.3%
  zero-fillable-lag, §5), PolySignal open-source + 6-domain scam cluster (§2),
  Novals83 skill (§2), KaustubhPatange depth quote (§1/§2), 1.4%-WR maker
  existence proof (§5). Authorship note (corrected in round 4): kachoio =
  HN arb-bot post + 5m-dataset release; gregyoung14 = OpenMarket — two
  researchers on similar arcs (arb bot → null/partial result → data release).
  Reddit body + Medium remain proxy-blocked.
- 2026-09-02: round 3 — whale-tracking lane (§6c: sporeking both-sides
  detector, polymarketanalytics, Kairos/SightWhale map, Awesome list),
  Twitter/X lane (§6d: fake-bot-post warning = catalog weighting rule,
  0xLeon bot-dominance corroboration, PM-vs-Kalshi microstructure alpha
  argument), venue landscape (§6b: Limitless CLOB 30-60min markets = closest
  twin venue; Myriad AMM + arXiv:2601.01706 LoOP study; Alchemy 56-venue map),
  Taker Rebate Program fully captured (§1: live 2026-05-28, wV formula, crypto
  weight 2.3, cheap-side subsidy design; April-sample fee footnote).
  STILL OPEN: JP/KR deeper communities (search timeouts ×2), Medium bodies,
  7-months full body, HN comment bodies.
- 2026-09-02: round 4 — JP/KR-lane search surfaced CN retrospective set
  (Foresight News 25-strategies: 92% lose / bots take 73% of arb profit /
  45% crypto participation; Binance Square 4-bot $500 experiment: contrarian
  survived; cnyes: 823 wallets >$100k since 2025-01), Oceanjackson1 compendium
  (§2: 11-strategy map, IMDEA-grounded), arXiv:2508.03474 enriched (§4: AFT
  2025, $39.59M, 41% of conditions, non-atomic legs), HN 48461522 comments
  fetched via Algolia (§5: kachoio authorship correction + adverse-selection
  lesson + devig-on-favourites bias). freedium mirror unreachable.
  STILL OPEN: Medium bodies, 7-months full body, true JP/KR-language lanes.
- 2026-09-02: round 5 — HN 47091557 comments fetched via Algolia (§5:
  order-vs-trade visibility asymmetry kills copy-trading alpha; CFTC oversight
  trend; PM-as-probability-source framing). Japan/Korea lane CLOSED as
  structural negative (§6e: frontend close-only mode, ~2030 approval target,
  Gumi domestic). Wayback Machine has NO snapshots of the three blocked pages
  (kaustubhpatange Medium, moonsat Medium, 7-months thread) → those bodies are
  permanently unfetchable from this environment; snippet-level coverage stands
  as recorded. LANE STATE: all named open items now either captured, closed,
  or permanently deferred; future rounds should open NEW lanes rather than
  retry these.
- 2026-09-02: round 6 — new lanes opened and mostly cleared: soulcrancerdev
  strategies journal fetched (§5: EndCycle Sniping = LIVE final-minute
  favorite-buying at 64–84¢, direct conflict with our no-entry rule, our rule
  stands pending verified track record; Momentum Spike Sniping live),
  nagi777 fetched (§5: A/B/C three-state spike classifier — State C = our
  staleness trade; adopt taxonomy for observation logging), AFT-2025 full
  HTML captured (§4: heuristic reduction from O(2^(n+m)), LLM annotation
  with 7B-class models), Chainlink Data Streams docs index (§1: crypto
  schemas v2/v3, calculated streams, liquidity-weighted quotes — action #10
  refinement), QuickNode/Moonsat/Illumination resolved as listicle-REF or
  permanently deferred. REMAINING UNFETCHED: dev.to abrownfox001 4-strategy
  lessons + borntoup WS/CLOB/risk (next round), CLOB API reference deep-read.
- 2026-09-02: round 7 — dev.to set completed: abrownfox001 postmortem fetched
  (§5: -37.81% live on final-60s favorite entries = second leg of evidence
  for our no-entry rule; bid-vs-ask paper bug; Bregman/Frank-Wolfe arb
  engine), borntoup production architecture fetched (§5: WS endpoint +
  event names). CLOB OpenAPI captured (§1c: 54 endpoints; /fee-rate/
  {token_id} closes runtime-fee action; rewards endpoints for maker mode).
  Catalog structurally complete for the practitioners+infra cluster;
  next rounds: new topics (perps docs, additional venues, new papers).
- 2026-09-02: round 8 — Kalshi cross-venue lane opened (§6f: KXBTC15M 24/7
  up/down on 5 coins, CF Benchmarks BRTI 60s-average settlement = same shape
  as our 15m markets, >$1.1M/market volume; second-venue candidate),
  compendium D/G/K deep-reads (§6g: maker rule-of-thumb 0.2% of volume,
  90%+ of $10k+ orders in >$0.95 markets, sequential two-leg grid variant),
  Perps market-sessions concept noted (feed-set switching by session —
  parallels our own session buckets; Perps fees doc JS-walled, Perps itself
  low-relevance to our PM work).
- 2026-09-02: round 9 — arXiv fresh scan: Capital Lock-Up Costs working paper
  (§4: up to 88% of apparent mispricing = locked-capital compensation; our
  5m/15m lane is lock-up-negligible → cleaner edge), Optimal MM in Prediction
  Markets 2607.17991, Binary PM Failure Modes stress tests (May 2026),
  Resolution-Aware Perpetuals 2605.10400. Compendium E/H fetched (§2:
  polyclaw contrapositive hedges + CTF split-and-sell execution; esports
  30-40s official-API-vs-stream law; mempool frontrunning discarded).
  Changelog doc JS-walled this round (retry via web_reader next scan).
  CSDN/Zhihu fresh scan deferred to monthly cadence (lane already dense).
- 2026-09-02: round 10 — changelog fetched in full (§1d: complete fee &
  platform timeline). Contradiction resolved: squared fee curve (1.56% peak)
  ran until Fee Structure V2 (2026-03-30) when crypto feeRate became 0.07;
  our ENTIRE sample (Apr 6 start) is in the 0.07 era → fee model validated;
  earlier April-predates-fees footnote withdrawn. New regime flags: CLOB V2
  cutover inside sample (Apr 28, match-time fees + pUSD), strike moved to
  TWAP feed on Aug 7 (price-to-beat is now an average, not a snapshot),
  5m TWAP window 30s→60s on Aug 14, crypto taker delay 250ms→50ms on Aug 17
  (secondsDelay action resolved). Failure-Modes paper identified as subtitle
  of arXiv:2605.10400v2 (merged into existing entry). CSDN/Zhihu fresh scan:
  only reposts/guides + the BlockBeats fee-timeline story (recorded);
  deployment/API-overview/AI-agent articles = REF-grade, copy-trading guide
  DISCARD. Perps fees page remains JS-walled (deferred, low relevance).
- 2026-09-02: round 11 (monthly cadence) — arXiv q-fin.TR recent scanned with
  titles (§4: 2608.21888 15m mean-reversion-in-crypto measurement = research-
  queue cross-check; 5 more REF titles). Changelog watch: NO entries after
  Aug 17 → no fee/parameter drift since the round-10 pin; watch continues.
  Perps context from CN scan: launched 2026-04-21, 10x leverage, funding-rate
  mechanism (separate product, low relevance; fee page stays deferred);
  QQ News history note: crypto maker rebate share previously 100% → now 20%.
  CN fee-formula restatement (Foresight) is a garbled version of the docs
  curve — docs + changelog remain authoritative.
- 2026-09-02: round 12 — compendium A/B/C/F/I deep-reads complete: ALL 11
  strategy pages now read (§2 row rewritten with full detail). Key: strategy
  B's poly-kalshi-arb (Rust, SIMD, dual-leg) + dr-manhattan = ACT tools for
  the Kalshi second-venue lane; strategy C documents the latency-arb golden
  age AND its death by dynamic taker fees; A's fee premise corrected against
  §1d; F = LLM lane (not ours). arXiv re-pull: nothing newer than 2608.30999
  (round-11 scan current). Zhihu new finds: 套利圣经 (RohOnChain translation),
  LLM-mining arb paper digest, BitsLab arb analysis ("public arb strategies
  hyper-competitive"), 10,000-season simulation ("only 3 strategies survived —
  model-driven positive-EV ones") — corroborates Foresight 25→4 and our
  29-trial/5-keep ledger. No TWAP-for-Polymarket articles on Zhihu.
- 2026-09-02: round 13 — drift checks clean (arXiv newest still 2608.30999;
  changelog newest still Aug 17). Reddit scan surfaced PR&R
  (polyresearchrobotics.com) — on-chain bot-forensics reports; SLIP-ME report
  fetched in full (§6c-2): 188,932 fills mapped, two-leg decomposition
  (spread leg −$97.5K as cost of presence, final-90s directional leg
  +$204.5K, net +$111.8K/23d at 2.59% ROI), 5×-skew → 99.8% win rate,
  pair-cost $1.0183 > par resolves the 101¢/rebate question (mechanical
  pair-arb net-negative at taker prices). New: Gabagool bot profile
  ($100k/mo, waits for cheap mispriced moments = our trade shape),
  r/Polymarket TA-on-live-BTC thread (retail fair-value instinct).
- 2026-09-02: round 14 — drift checks clean (arXiv 2608.30999; changelog
  Aug 17). PR&R SIRMARTINGALE report fetched (§6c-2): working latency-arb
  archetype, +82.95% ROI/28d, sell-into-catch-up exit (hold-vs-exit variant
  flagged for wallet simulation). ohanism report remains unread (watch).
- 2026-09-02: round 15 — drift checks clean (arXiv 2608.30999; changelog
  Aug 17). PR&R ohanism report fetched (§6c-2): hybrid MM+directional
  archetype at extreme scale (694k fills/27d, +3.02% ROI, paired-dominance
  as conviction signal). All three PR&R trader reports now read; PR&R
  Strategy Database remains on watch. Practitioner content scan: no new
  items beyond rounds 13-14 findings (same-day re-scan).
- 2026-09-02: round 16 — drift checks clean (arXiv 2608.30999; changelog
  Aug 17). PR&R Strategy Database fetched (§6c-2): 297 strategies + 94 data
  resources + TWAP Price Feed product; site is free/data-funded (llms.txt);
  deep-reads of the ~10 strategies intersecting our lanes queued. All named
  PR&R items now captured.
- 2026-09-02: round 17 — 5 PR&R strategy deep-reads (§6c-2): oracle-lag lock-in
  NOT applicable (UMA-only; our lane auto-resolves), scrape-first-mover = our
  architecture's general form, Kalshi RV carries index-basis risk for crypto
  up/down (Chainlink vs CF Benchmarks), settlement-timing carry = lock-up
  paper operationalized (N/A at minutes), CTF split/merge mechanics corrected
  and shown competed-away on liquid books. Cross-cutting: our edge class is
  structurally distinct in the 297-strategy taxonomy. Drift checks clean
  (arXiv 2608.30999; changelog Aug 17).
- 2026-09-02: round 18 — drift clean (arXiv 2608.30999; changelog Aug 17).
  PR&R guides index read (12 guides); spread-capture guide deep-read:
  time-separated pairing (blended pair cost < $1.00 via separate dips)
  REFINES the round-17 simultaneous-pair-cost conclusion — the viable
  maker-mode entry design for our markets, queued alongside strategy K's
  sequential grid and ohanism's paired-dominance signal.
- 2026-09-02: round 19 — drift clean (arXiv 2608.30999; changelog Aug 17).
  PR&R reports index enumerated: 36 reports total (3 read). BONEREAPER
  (fair-value MM on 5/15m crypto binaries = our direct competitor) flagged
  as the top-priority next deep-read; BTC5MScour second; remaining ~30 on
  watch queue.
- 2026-09-02: round 19b — BONEREAPER report fetched in full (§6c-2): the
  fair-value-MM competitor at +\$443.8K/22d, calibration signature within ~2
  points across all price bands, dominance→win-rate 59→97.7%, both-sides
  96.7% with 10s hedge lag; window straddles Fee-V2 and is pre-TWAP (caveat
  recorded). Tail finds: Mean-Reversion Guide G·001 with worked code on BTC
  15-min (top-priority next read), PR&R full-depth 1s-cadence book data for
  our 6 symbols (cross-validation source), KCH123/LIL222 on watch.
- 2026-09-02: round 20 — drift clean (arXiv 2608.30999; changelog Aug 17).
  G·001 mean-reversion guide method captured (§6c-2): sign-lag conditional
  stats + OOS pipeline for BTC 15-min; worked-example numbers on deeper page
  (re-read next round). BTC5MScour/KCH123 reports remain queued.
- 2026-09-02: round 21 — G·001 worked example + real lesson captured (skip
  unless EV > spread+buffer; $14K/yr-on-$10K illustrative; tiny edge ×
  frequency × compounding). BTC5MScour: single-sided deep-favorite buyer,
  95.8% WR at +1.8% ROI/26d — the favorite trade's razor margin quantified.
  KCH123: sports whale, pay-vs-bleed filter method (0.03% of notional is
  the profit). Drift checks clean (arXiv 2608.30999; changelog Aug 17).
- 2026-09-02: round 22 — descriptors read for 8 more PR&R reports (14/36
  total): ROI-convergence insight established (all high-volume bots 0.3-9.9%
  monthly ROI; vidarx conviction-curve bot and gghff highest-ROI flagged for
  deep-read). Drift checks clean (arXiv 2608.30999; changelog Aug 17).
- 2026-09-02: round 23 — vidarx + gghff deep-read (§6c-2, 16/36 classified):
  vidarx = 48.4%-WR profitable MM (win-rate-meaningless, case 3); gghff =
  weather-distribution bot at +9.9% ROI (model-quality edge, different class
  from microstructure lanes). Drift checks clean (arXiv 2608.30999;
  changelog Aug 17).
- 2026-09-02: round 24 — PR&R classification COMPLETE (36/36): bonereaper-
  update shows marginal ROI dilution to +0.2% at scale (edge-decay/capacity
  constraint on fair-value MM), sinenooneei +16.3% at low frequency (new ROI
  leader, concentrated specialist), doggystyie -1.0% (losing big bot). No
  BTC-specific reports remain unread — crypto lane of PR&R fully mined.
  Drift checks clean (arXiv 2608.30999; changelog Aug 17).
- 2026-09-02: round 25 — PR&R data store + 94-resource directory captured
  (§6c-2): full-depth 1s books bundled with Binance 1s klines + Chainlink
  reference feed ($25/mo, 80-cycle free sample); resources categorized
  (crypto/oracle/sports/esports/weather/macro feeds). PR&R site now fully
  perused end-to-end. Drift checks clean (arXiv 2608.30999; changelog
  Aug 17).
- 2026-09-02: round 26 — drift: arXiv unchanged (2608.30999); changelog
  re-fetch intermittent (prior round-22 snapshot showed Aug 17 top; watch
  continues). PR&R report count still 36 (no new). Fresh practitioner scan
  (7-day window): NEW r/PredictionsMarkets postmortem "My Polymarket bot
  wins 68% of the time and still loses money" (3 months on BTC Up/Down —
  4th independent instance of the win-rate lesson on our exact market);
  "How to Build a Polymarket Trading Bot (After CLOB V2)" free tutorial
  (REF, matches our Apr-28 boundary); "$3 bets over 80k times → $273k+"
  small-ticket frequency analysis (consistent with BONEREAPER's $5.56
  median ticket); retail endgame-sniping rule (price>90 & <99 in last
  1-2min) = the favorite trade at retail level. No CSDN results this week.
- 2026-09-02: round 26b — changelog verified on retry: newest entry still
  Aug 17 (50ms taker delay). No venue drift across rounds 22–26.
- 2026-09-02: round 27 — Perps fees page fetched (transient failures
  resolved by retry loop): flat notional-rate tiered schedule — taker
  0.0400%→0.0200% (\$1B+ tier), maker 0.0125%→−0.0050% rebate at top tier;
  fee = abs(Price × Quantity) × Rate, daily tier re-eval, 7-day metrics
  view. Traditional derivatives model, unrelated to the p·(1−p) curve —
  closes the LAST named open item in the catalog. Drift clean (arXiv
  2608.30999; PR&R still 36 reports; changelog last verified Aug 17).
- 2026-09-02: round 28 — venue-lane completion (§6f-2): PRDT = fixed-odds
  pool model (no book; deferred), Opinion = third CLOB venue with Python SDK
  (macro + crypto Up/Down), Predict.fun = order book + Venus yield-bearing
  collateral (reduces lock-up compensation → tighter long-dated fair; 25%
  maker rebate; Binance Wallet integration). Polymarket live on BSC with
  minute-level BNB 5m markets. Drift clean.
- 2026-09-02: round 29 — RN1 operator manual read (2.0x dominance threshold;
  18-section spec template; spread+lean archetype at \$131.85M scale).
  Remaining PR&R sports/politics method sections sampled-sufficient — same
  archetypes on other verticals. Drift clean (arXiv 2608.30999).
- 2026-09-02: round 30 — research queue BEGUN: fair_v2 implemented
  (research/staleness/fair_v2.py + tests/research/test_fair_v2.py, 7 tests
  green; suite-external polars collection errors pre-existing in default
  env). **Mechanism correction**: v1 running-TWAP variance is LARGER
  mid-window than venue final-window → v2 more extreme → averaging mismatch
  does NOT explain measured overconfidence; σ understatement / strike basis
  / adverse selection elevated as candidate causes. Empirical re-test vs
  resolutions + σ-lookback sweep = next research session. Drift clean.
- 2026-09-02: round 31 — research queue: empirical calibration comparison
  EXECUTED (research/staleness/calibration_compare.py + CALIBRATION_COMPARE.md;
  97,356 quotes x 4 configs, all in the 60s-TWAP regime). **MAJOR FIND: units
  bug in audit.py** — (e_twap − K) is a PRICE difference divided by a RETURN
  sd → every v1 fair pinned at the 0/1 clip → the staleness audit's "median
  |gap| 26-29pp" magnitudes were artifacts, and the calibrated re-test's
  +2.87¢ EV actually measured direction-following (buy the ITM side cheap),
  not genuine fair-vs-quote staleness. Fixed in log space for both v1 and v2
  (fair_v2.py z = ln(E[S]/K)/sd). Results (log-space): v2 beats v1 (Brier
  0.1951-0.1954 vs 0.1969; ECE 0.146 vs 0.150); σ lookback matters modestly
  (r60/EWMA ≥ r24); ALL configs show an S-curve — realized COMPRESSED toward
  0.5 (fair 0.98 → realized 0.82; fair 0.15 → realized 0.34), mid bands
  [0.4,0.6] well calibrated (±0.01). Signature = σ understatement ~2-3x;
  queued: Brier-minimizing σ multiplier λ fit + strike-basis decomposition.
  Wallet implication: the live wallet's gate (same pinned formula) is
  effectively direction-following — interpretation note recorded; no
  mid-experiment change (fair_v2 integration queued after the window).
- 2026-09-02: round 32 — Brier-minimizing sigma multiplier lambda fit EXECUTED
  (comparison script now stores raw z and fits lambda per config): **v2_r24
  lambda*=1.94, v2_r60 1.88, v2_ewma 1.86, v1_r24 1.60**. With lambda
  applied: Brier v1 0.1843 vs v2 0.1720-0.1725; ECE v1 0.0455 vs v2
  0.0285-0.0306 (nearly halved); band errors flat at +-0.03 across all ten
  bands, residual overconfidence only in the extreme band (fair>0.9:
  realized ~0.885 vs 0.958 — strike-basis/fat-tails candidate, still queued).
  Interpretation: (i) the sigma understatement is ~1.9x, stable across
  lookbacks (a systematic scale factor, not a lookback artifact — r60/EWMA
  absorbed by lambda); (ii) v2+lambda is the calibration champion and the
  reference for wallet integration (queued after the $5 window);
  (iii) remaining extreme-band residual = strike-basis decomposition item.
- 2026-09-02: round 33 — calibrated re-test re-run with log-space fair
  (research/staleness/retest_logspace.py + RETEST_LOGSPACE.md): temporal
  split 2026-08-29 12:00 UTC, lambda + isotonic fit on TRAIN only, gate =
  calibrated_prob - ask > fee, test-only evaluation. **v2_ewma: EV +6.81c
  CI [+6.29,+7.32] on 23,945 gated trades (win rate 0.504, avg ask 0.424)**
  vs v1_r24 +4.98c [+4.46,+5.50] on 23,080 (WR 0.406, ask 0.344). Favorites
  control NEGATIVE for both (-3.4c) — the gate selects real signal, not
  cheap quotes. v2 beats v1 by +1.8c/trade — the venue-accurate settlement
  math has direct economic value. lambda refit on train (1.95) matches the
  full-sample 1.86-1.94 (stable). CAVEATS: test window only ~2.5 days ->
  trade-level bootstrap (CI optimistic vs daily-block); gate takes 40% of
  quotes (isotonic remap wide); mid-experiment wallet untouched.
- 2026-09-02: round 34 — split sensitivity + residual attribution EXECUTED
  (research/staleness/sensitivity_round34.py + SENSITIVITY_ROUND34.md):
  (i) the +6.8c gate EV is robust across three temporal cuts (+6.81/+6.94/
  +8.10 — rising with more train data; not a split artifact); (ii) extreme-
  band residual attribution (n=23,492, lambda=1.85): flat across remaining
  time (final-60s -0.006 vs d>=60s -0.010), mild asset variation (BTC
  -0.014 / ETH -0.003 / SOL -0.012), horizon concentration (5m -0.002 vs
  15m -0.012) — scale-factor signature (strike basis or fat tails), 5m
  nearly perfectly calibrated. Next: strike-basis test needs Chainlink tape
  (queued); daily-block CI waits for >=5 gated days (collector thickening).
- 2026-09-02: round 35 — cross-validation round: (i) the local updown price
  files cover Apr-May 2026 markets with ZERO id overlap against collector
  resolutions (Aug era) — that external route needs the OpenMarket/kacho
  downloads (46GB / HF; queued as a dedicated session with exact commands
  already in the catalog); (ii) internal quote-based label validation run:
  final-quote mid vs official resolution agrees 95.3% when post-close
  snapshots are included (trivially), and **76.15% on honest final quotes
  within 30s of close — with 88% of disagreements being genuinely-undecided
  books (mid in [0.35,0.65])**. That near-close uncertainty is structurally
  CORRECT under 60s-TWAP settlement (half the averaging window unrealized
  at 30s-out) — internal evidence the venue books price the TWAP process,
  and no label-inversion signature (76% >> 24%). Collector join/labels
  validated as sound; external archive cross-check remains queued.
  Drift clean (arXiv 2608.30999).
- 2026-09-02: round 36 — external cross-validation EXECUTED on the kacho
  archive (data/external/btc_markets.parquet downloaded, 15,682 BTC 5m
  markets, Mar 24-May 18 2026): joined on condition_id against our updown
  markets (2,066 matched). **Outcome agreement 91.56%** (564/616 both-known)
  — no systematic inversion; the 8.4% divergence is kacho's tick-inferred
  outcome vs the venue's official resolution field. **Bonus find: the venue's
  own fee_rate_bps metadata corroborates the changelog timeline** —
  fee_rate_bps=1000 populated on 15,055 markets from 2026-03-27 (Fee
  Structure V2 era), then unset (-1) on 63,953 later markets (feeRateBps
  deprecated at CLOB V2 Apr 28, fees set at match time). Drift clean.
- 2026-09-02: round 37 — kacho cross-validation extended to ETH and SOL
  (data/external/{eth,sol}_markets.parquet): ETH 93.34% (575/616), SOL
  91.07% (561/616) — combined with BTC, 1,848 both-known market pairs at
  ~92.0% agreement, uniform across assets. The consistent ~8% divergence is
  a systematic source difference (kacho tick-inferred outcome vs venue
  official resolution field), not asset noise and not label inversion.
  External label cross-check for the April-era updown lane: COMPLETE.
  Tick-level files available on HF for a deeper future check (redirect
  sizes to be confirmed via ranged GET). Drift clean (arXiv 2608.30999).
- 2026-09-02: round 38 — sign-lag conditionals + A/B/C spikes EXECUTED
  (research/staleness/signlag_spikes.py + SIGNLAG_SPIKES.md):
  (i) 1m klines show MILD CONTINUATION on all three assets (next-ret after
  UP +0.20/+0.14/+0.37 bp for BTC/ETH/SOL; after DOWN −0.22/−0.16/−0.28) —
  the G·001 reversion edge is NOT alive at the 1m bar level here, and
  positive autocorrelation mechanistically supports part of the λ≈1.9
  σ understatement (autocorrelated moves inflate multi-minute variance vs
  the iid formula); (ii) A/B/C spike classification on BTC 5m collector
  quotes (1,432 spikes, |Δmid|≥4c/2min): **95% are class B (external flat)
  and their post-5m reversion is +0.11c — essentially ZERO**: fade-the-book
  is dead on average, PM repricings stick without external news (likely
  intra-minute information the 1m close-to-close misses); class A (32,
  external-aligned) CONTINUES (−29c reversion); class C (40, external-
  opposite) reverts hard (+27c) — the only fade candidate, but rare.
- 2026-09-02: round 39 — sell-into-catch-up exit simulation EXECUTED
  (research/staleness/exit_sim.py + EXIT_SIM.md; 26,077 gated entries,
  lambda(train)=1.95, exits at bid with both-leg fees): catch-up 2c/3c/5c/8c
  show +27.6/+28.6/+30.3/+32.2c per trade at 82-95% win rate vs hold's
  +7.57c. **ARTIFACT WARNING (recorded as the primary finding)**: exits fire
  on the NEXT collector snapshot (30-60s stale) — the "catch-up" profit is
  the staleness itself, claimable only by faster actors; our own entry ask
  would have moved in reality. This is the exact stale-quote illusion the
  r/algotrading free-dataset author and OpenMarket's one-tick-spread note
  warn about. Honest value of the result: it QUANTIFIES the exit premium
  (+20-25c/trade conditional on fills) as the price of execution speed —
  SIRMARTINGALE-class latency revenue — and confirms hold-to-settlement is
  the correct baseline at our polling cadence. No deployable edge claimed.
- 2026-09-02: round 40 — DAILY-BLOCK MILESTONE: collector crossed >=5 gated
  UTC days; re-test re-run with fresh data (101,581 quotes scored, +4k vs
  round 31) and the daily-block bootstrap now fires: **v2_ewma EV +7.61c/
  trade, daily-block CI [+4.92, +10.19]** — excludes zero on the honest
  day-level basis (v1_r24 +5.89c [+4.03,+7.87]); favorites control negative
  (-3.69c [-5.05,-2.27]); lambda* stable across the added days (1.86-1.96).
  The wider CI vs trade-level ([+6.29,+7.32] in round 33) is the expected
  day-clustering correction. Weekly re-test checkpoints continue; the
  wallet decision gate (2 consecutive all-weeks-positive weeks on the live
  $5 ledger) is unchanged and separate.
- 2026-09-02: round 41 — STRIKE-BASIS JOB STEP 1 COMPLETE: Chainlink TWAP
  tape collector is LIVE on the credential-free RTDS relay
  (wss://ws-live-data.polymarket.com). Protocol reverse-engineered from
  @polymarket/client 0.8.1: subscribe = {"action":"subscribe",
  "subscriptions":[{"topic":"crypto_prices_twap_sixty","type":"update"},...]}
  (server keys crypto_prices_twap_{thirty,sixty}; symbols filtered
  client-side; Origin header REQUIRED — bare connects are reset).
  research/staleness/twap_collector.py captures ~1s-cadence
  btc/eth/sol-usd TWAP values for both windows (349 rows in 60s verified,
  windows disambiguated via envelope topic; connect-retry added for the
  flaky gateway). Once the tape spans full windows alongside quotes, the
  strike-basis decomposition replaces the Binance-proxy strike.
- 2026-09-02: round 42 — TWAP collector DEPLOYED as systemd user service
  quantbtc-twap.service (mirrors quantbtc.service: Restart=always,
  WorkingDirectory=repo, logs to data/twap_collector.log; continuous mode
  added to the script: seconds=0 runs forever). Verified capturing: 222+
  rows in the first session file, both windows, all three symbols, tape
  growing across 30s checks. The strike-basis decomposition unblocks once
  the tape spans full windows alongside collector quotes. Drift clean
  (arXiv 2608.30999).
- 2026-09-02: round 43 — strike-basis PRELIMINARY measurement (tape ~13 min
  of 60s-window data; full decomposition deferred until the tape spans
  1-2 days): first 5m-window strike basis (Chainlink 60s-TWAP strike −
  Binance 1m-open proxy) = **−4.73bp (BTC), −3.58bp (ETH), −4.76bp (SOL)**
  — consistently negative ~4-5bp across assets on this single window,
  i.e. ~0.4-0.5 σ_m. If persistent, the Binance-proxy strike carries a
  small systematic negative bias (Chainlink prints slightly below Binance
  spot) — a component of, but not the whole, the λ≈1.9 residual. Also
  noted: kline files flush with lag (03:10 at 08:40 UTC) — fresh-Binance
  strikes for the tape era came from the REST endpoint; the service tape
  is healthy (1,906+ rows, real-time within 6s).
- 2026-09-02: round 44 — watch rotation + tape health check: service active
  and flushing (last flush seconds before check); tape span corrected to
  its true value (~17 min — the entire TWAP deployment happened within the
  last quarter-hour of wall clock; no malfunction). Basis measurement still
  n=1 per asset pending days of accumulation — unchanged plan: full
  decomposition when the tape spans 1-2 days. Drift clean (arXiv
  2608.30999).
- 2026-09-02: round 45 — watch rotation (arXiv unchanged; PR&R still 36
  reports; tape span 0.33h — decomposition gated on ~24h, as planned).
  G·001 worked-example detail now fetched first-hand and matches the
  round-21 snippet exactly ($0.40/trade, ~35k trades/yr, ~$14K/yr on $10K,
  weekly re-validation, "the bot doesn't need to be smart — it needs to be
  honest about its edge"); oracle-lag strategy page confirmed to carry no
  UMA timing specifics (round-17 verdict stands).
### 2b. Fresh GitHub scan — repos updated this week (round 46, sorted by updated)

| Repo | What it is | Verdict |
|---|---|---|
| [0xzkleo/polymarket-5min-crypto-trading-bot](https://github.com/0xzkleo/polymarket-5min-crypto-trading-bot) (★136; README fetched round 47) | NautilusTrader bot, multi-signal fusion + **XGBoost edge gate vs Polymarket price**, entry window **seconds 180–270 of the 300s market (late-window)**, one bet/window, TP/SL + anti-chase + spread filter, sim/live modes, Grafana. **Freemium funnel**: premium claims "98.8%+ win rate on 200k+ trades" with "proof shared only on a call"; public model trains on "general / warming" data; feature list not enumerated publicly | **REF (stack pattern) / DISCARD (claims)** per the catalog weighting rule: the XGBoost-gate + late-window-entry architecture is the third documented entrant in the final-90s zone (soulcrancer claims, abrownfox −37.81%, 0xzkleo ★136); the 98.8% claim is unverifiable call-only marketing. Feature-vs-fair_z comparison deferred to a code read (models/ dir) — README enumerates none |
| [PricePepel/polymarket-tracker](https://github.com/PricePepel/polymarket-tracker) (★4, updated 2026-09-02) | Auto-tracks top-50 Polymarket crypto traders' BTC 5m bets, 15-min refresh | REF (smart-money tracking on our exact markets) |
| [0xpoot-poot/polymarket-5m-recorder](https://github.com/0xpoot-poot/polymarket-5m-recorder) (updated 2026-09-01) | Recorder + orderbook-reconstruction library for 5m markets | REF (second validator for our collector join) |
| [atalaydor/polymarket-15m-seven-canonical-data](https://github.com/atalaydor/polymarket-15m-seven-canonical-data) (updated 2026-09-02) | Canonical historical dataset, 15m markets | REF (third validation dataset candidate) |
| [reeleen-bit/5mUpDownBTC-Lite](https://github.com/reeleen-bit/5mUpDownBTC-Lite) | Free live Price-to-Beat tracker, 7 coins | REF |
| [Ameerqasqas/polymarket-directional-arbitrage-bot](https://github.com/Ameerqasqas/polymarket-directional-arbitrage-bot) (Rust) | Classic locked-arb on Up/Down | REF |
| thxthanxwe / DiegoBermud65 "bot" repos | Keyword-stuffed marketing / copy-trading | DISCARD (fake-repo pattern per §6d) |

Drift: arXiv unchanged (2608.30999); changelog newest still Aug 17; tape healthy (5,030 rows, span 0.37h, fresh within 5s).

### 2d. 0xpoot-poot/polymarket-5m-recorder cross-check (round 49, README + twap-collector source read)

TypeScript data infrastructure for the same 5m series (BTC/ETH/SOL/XRP/DOGE/BNB/HYPE):
- **Architecture confirms ours from an independent implementation**: multi-oracle collectors (Binance/Bybit/Coinbase/OKX + Chainlink), a dedicated TWAP collector, book reconstruction from the WS feed with drift callbacks, per-market tapes on disk.
- **TWAP protocol cross-check**: they use `wss://ws.dataengine.chain.link` DIRECT with HMAC credentials (paid Data Streams), recording both 30s+60s feeds tagged by feedID with the window "resolved in post". Our quantbtc-twap uses the credential-free RTDS relay with the window resolved from the envelope topic — same data, simpler path. Validated.
- **Key quote confirms the HN visibility asymmetry with implementation detail**: "The Polymarket market WebSocket gives you a fast, complete view of the book — and zero wallet identity... scanning Polygon OrderFilled logs and joining them back on transaction_hash is the only thing here that knows who anyone is."
- **Their on-chain attribution pipeline** (OrderFilled scan → `traders.db` → wallet leaderboard) is the PR&R forensics method as a runnable pipeline — a candidate to adopt if we ever do our own forensics.
- **Verification discipline exceeds ours**: 61 offline tests + `npm run replay` that re-checks every recorded snapshot against reconstruction. **Adopt**: add a replay/verify mode to our collector (queued).
- Read-only ("nothing places an order"). Verdict: **KEEP-CORNERSTONE (infrastructure reference)**.

### 2c. 0xzkleo code-read — the 25-feature vector vs our fair_z (round 48)

FEATURE_NAMES from core/strategy/ml_engine.py (fetched in full): rsi,
macd_line, macd_signal, pct_b, ret1/3/5/15, vol_regime, cvd_delta_norm,
ob_imbalance, funding_rate, oi_change, liq_imbalance, liq_total_norm,
tick_vel_60s, tick_vel_30s, poly_ob_imbalance, spot_momentum, poly_prob,
hour_sin, hour_cos, is_ny_open, is_asia_open, is_dead_zone.

- **Their model**: 25-feature discriminative XGBoost predicting P(UP) from
  market state. **Ours**: a 3-parameter structural model (strike distance,
  σ, final-window variance → closed-form Φ + λ calibration).
- **Overlap**: spot_momentum/returns ≈ our z numerator; vol_regime ≈ our
  regime buckets; session flags ≈ our sessions; poly_prob = the venue's own
  price (they use it as a feature; we compare against it).
- **Their unique features are the falsified lane**: CVD, tick velocity,
  liquidations, funding/OI, Deribit PCR — venue/order-flow features that
  OpenMarket's 43-feature null and our Phase-B RESETs already covered.
- **The decisive absence**: no settlement-process feature anywhere — no TWAP
  reconstruction, no time-to-settlement variance, no strike-distance
  normalization by remaining variance. Their XGBoost must *learn* what our
  closed form *derives* from the venue's documented settlement process.
- Fusion weights confirm the live signal set is just **OrderBookImbalance
  0.60 + SpikeDetection 0.40** (8 other processors shipped at weight 0.0) —
  and round 38 measured exactly those two classes: 95% of book moves don't
  revert (B) and information-aligned moves continue (A).
- Also: they ship their own `core/settlement/twap_feed.py` (19KB) — the
  post-Aug-7 TWAP feed reader, validating our tape-collector necessity.

Verdict: **KEEP-CORNERSTONE (comparative)** — the most-starred public bot on
our markets sits entirely in the lane the evidence falsifies and lacks the
settlement math that defines ours. Our differentiator survives its strongest
public test.
- 2026-09-02: round 47 — 0xzkleo README read (§2b): freemium funnel with
  unverifiable 98.8% premium claims (DISCARD per weighting rule); public
  stack = NautilusTrader + XGBoost gate + late-window entry (180-270s) —
  third documented entrant in the contested zone; features not enumerated
  publicly (code-read queued). Tape span 0.40h (decomposition still gated).
- 2026-09-02: round 49 — recorder cross-check EXECUTED (§2d): their
  architecture validates ours (multi-oracle + TWAP collector + on-chain
  attribution); their Data Streams HMAC path vs our RTDS relay = same data
  simpler; replay-verify discipline adopted as a queued collector upgrade.
  Drift clean (arXiv 2608.30999).

### 2e. atalaydor 15m canonical dataset — pipeline-in-construction (round 50, repo tree + README read)

- **Not yet a dataset**: production "locked until one Actions canary establishes usable evidence for all seven assets" — the repo ships the pipeline (acquire/audit/discovery/manifest via PMXT as the acquisition source; content-addressed Releases; canary receipts; per-UTC-day partitions) but no published data files yet.
- Engineering quality is high (canary/receipt/audit discipline; dataset contract + quality policy docs) — revisit when it publishes; candidate fourth validation source for the 15m lane.
- Verdict: **DEFER (revisit on publication)**. Tape at 0.84h (growing).
- 2026-09-02: round 50 — atalaydor dataset inspected: pipeline-in-construction
  (canary-gated, no data published yet) → DEFER on publication. Tape 0.84h.
  Drift clean (arXiv 2608.30999).
- 2026-09-02: round 51 — collector replay/verify mode IMPLEMENTED and run
  (research/staleness/collector_verify.py + VERIFY_REPORT.md; the discipline
  adopted from the 0xpoot-poot recorder, round 49): **PASS** — 315,026
  quotes with zero duplicate keys and zero non-monotonic markets; 2.33%
  crossed-book rows (analysis-filtered anyway); top poll gaps 705-813s
  (WARN only, better than the historical 497+ min gaps); resolutions clean;
  TWAP tape 10,050 rows zero anomalies. Gates: tape 1.0h / daily-block days
  accumulating — unchanged.

### 2f. 0xzkleo settlement/twap_feed.py cross-check (round 52)

Their 19KB TWAP reader vs our quantbtc-twap tape collector — **independent
implementations agree on every protocol detail**: same endpoint
(`wss://ws-live-data.polymarket.com`), same topics
(`crypto_prices_twap_thirty` / `_sixty`), window_s carried per tick, and the
same structural insight: **the "Price to Beat" is locked from the TWAP
observation AT the market-open boundary, and settlement closes off the
end-boundary TWAP** — both boundaries are TWAP observations, confirming the
changelog-based strike/settlement model in fair_v2. Their scoring weights
(twap_open 80, twap_near 50) reveal their late-window signal mixes the
opening strike with the near-boundary TWAP. They also cache ticks on disk to
survive restarts (our per-session Parquet files + systemd Restart=always
serve the same purpose). Verdict: **KEEP (protocol cross-validation)** —
our collector's endpoint/topics/strike-model now validated against a second
independent implementation.
- 2026-09-02: round 52 — 0xzkleo twap_feed.py cross-check (§2f): same
  endpoint/topics/semantics as our tape collector; "PTB locked from the
  open-boundary TWAP" confirms fair_v2's strike model from a second
  implementation. Tape 0.94h (decomposition still gated).
- 2026-09-02: round 53 — BTC5MScour full forensics fetched (§5b): toll-
  collection anatomy confirmed ($0.96-0.99 entries, 99.3% WR on 98.8% of
  capital, 1.77% ROI/26d) + the June 21 anomaly (−$2,460 single-market
  tail) as the documented failure mode our final-90s rule avoids. Tape
  1.02h. Drift clean (arXiv 2608.30999).

### 2g. TWAP-keyword GitHub scan (round 62)

- The post-Aug-7 "TWAP bot" keyword is now SEO-polluted: multiple
  keyword-stuffed repos (0xohioism ★107, MattheusFeittosa, n9xdev "$150k+
  trader", thxthanxwe-class) repeat bot-keywords in descriptions — the
  §6d fake-repo signature. Benjam1nCup's education repo now ★170.
- **abrownfox0/abrownfox001-twap60-prediction-trigger-system** (updated
  2026-09-01): the −37.81% postmortem author's continuation — a TWAP-60
  prediction trigger system, i.e. they pivoted from directional entries to
  settlement-trigger logic after the loss. Worth a code read next session.
- funstersland/twap-hunter (Aug 19): unknown quality, on watch.
- Drift: arXiv unchanged (2608.30999); changelog newest still Aug 17.

### 2h. abrownfox001 twap60 trigger system — CODE-READ (round 53+, round 63; README + signal.ts + tree fetched)

The −37.81% postmortem author's pivot, now live-traded with a published
wallet (`0x12b7…0b0b`, active since Jan 2026) and TypeScript source.

- **The archetype flip**: from late-window directional entries (−37.81%) to
  **coin-flip-band entries (~45–55¢, ≈90% of trades) with breakeven scratch
  exits** — "low-conviction tickets flatten at ~breakeven; only strong reads
  ride to redemption" (~930 markets of scratch exits at avg buy 0.504 / sell
  0.503). This is the live-traded answer to our round-39 exit question.
- **The public signal (signal.ts)**: `pUp = sigmoid(2.5·raw)`,
  `raw = 0.7·(clip(twapBps/8) + 0.3·clip(twapMom20s/5)) + 0.2·clip(cexMom20s/5)
  + 0.1·((t/300 − 0.5)·2·twapTerm)` — a **TWAP-anchored directional read that
  is conceptually our fair_z with hand-tuned constants**: the 8bp divisor is
  a fixed σ proxy (ours: measured r24/EWMA × λ=1.9), the weights replace our
  closed-form settlement math, and the time-term scales the lean by time-in-slot.
- **Measured claim** (150 resolved markets at ~50¢, Jul 2026, public
  trade/resolution data): **60.7% held-side win rate, ≈ +24.5% ROI sample**.
  Small, self-selected, but on-chain verifiable.
- **Explicit archetype contrast in their own README**: convergence farming
  (94–99¢, BTC5MScour-style toll collection) vs this account (50¢ directional
  with conviction culling) — matching our forensics taxonomy.
- Fees "far less binding at ~50¢ than at 99¢" (fee curve shape) — consistent
  with our EV math.

Verdict: **KEEP-CORNERSTONE (the closest external analogue to our engine)** —
same structural lane (settlement-anchored fair in the coin-flip band),
hand-tuned where ours is derived, live-traded where ours is paper. Their
measured 60.7%/150-markets and our +8.42¢/26.8k-trades daily-block CI are now
two independent, mutually consistent measurements of the same edge class.

### 2i. Created-this-week scan (round 50, round 73 — repos born since Aug 25)

- [draxmit/prediction-market-accuracy-study](https://github.com/draxmit/prediction-market-accuracy-study) (created 2026-09-02): EDA on ~100k resolved markets (Kalshi/Manifold/Polymarket). Findings: **confidence is the strongest predictor of directional accuracy** (>90% confidence → <5% wrong-direction; near 50% → coin flip) — matching BONEREAPER's dominance curve and our calibration signature at scale; **YES bias**; keywords "coinflip"/"anytime"/"daily" are 6–9× overrepresented in wrong-direction outcomes. **KEEP-REF (comparative calibration study)**.
- [Nabeel-javed/polymarket-strategy-lab](https://github.com/Nabeel-javed/polymarket-strategy-lab) (created 2026-08-28): read-only $200 LP-only experiment testing long-duration liquidity rewards + **BTC 15-minute maker rebates**; simulates pro-rata reward accrual, the $1 daily payout minimum, and the live taker-fee schedule; uses the same market WS endpoint as our collector. **KEEP-REF (maker-mode runnable reference)**.
- [Cleverfuxaqo1668/Polymarket-Telegram-Bot](https://github.com/Cleverfuxaqo1668/Polymarket-Telegram-Bot) (★168 in <1 week): fastest-growing new repo, likely funnel — watch only. The rest of the born-this-week set is unstarred/spam (DISCARD).

### 2j. Kalshi tooling lane (round 81 — repos pushed today)

- ~~[haoo99/Polymarket-Kalshi-Arbitrage-Bot](https://github.com/haoo99/Polymarket-Kalshi-Arbitrage-Bot)~~ (★3, pushed 2026-09-02; **DOWNGRADED round 82 after README read**): end-user funnel — pre-built Windows `.exe` distribution, "no coding needed" marketing; the TS source (arbitrage.ts, marketMatcher.ts, redeemer.ts) exists but the distribution model is the §6d malware red flag. **DISCARD-CAUTION**; the concept (PM↔Kalshi 15-min BTC gap arb) remains valid — write our own if the port advances.
- [Crayz916/prediction-market-arbitrage-bot](https://github.com/Crayz916/prediction-market-arbitrage-bot) (pushed today): synthetic PM↔Kalshi arb — second implementation, same lane. REF.
- The copy-trade repos (Singhalesebradycardia99, UnitedStars111) and AI-lane (anglil Gemini bot) remain DISCARD per standing rules; "self-improving bot" marketing (mehpackers13) DISCARD.
- **Signal**: the PM↔Kalshi 15-min BTC arb lane is live and actively built by multiple parties — the compendium's "windows shrinking" assessment confirmed; our cross-venue entry (if any) would compete here.
- 2026-09-02: round 54 — kacho tick-level check EXECUTED (182MB tick file,
  4.7M rows): price-level agreement median 0.005 (half tick), 86.9% within
  2 ticks on 452 matched seconds — recordings consistent, no systematic
  discrepancy. Tape 1.06h. Drift clean.
- 2026-09-02: round 56 — **EVALUATOR PLACEHOLDER CONTAMINATION CONFIRMED
  (record-level)**: of the 2,341 April-era entry prices the 24-bucket
  evaluator took from the updown price files at open+60s, **68.7% are
  both-sides-stuck 0.50 placeholders, 10.9% have the up-side stuck, and only
  20.4% (477) are live** (ETH 5m: 99.1% placeholder; SOL 5m: 99.3%). Two
  record-level consequences: (i) the Branch-A "no bucket promotes" null was
  computed on ~80% fake entry prices — it was never a valid test; the
  accurate statement is that the April-era bucket test is INVALID due to
  placeholder contamination, not that no edge exists in those buckets;
  (ii) outcome labels were independent of entry prices, so accuracy metrics
  stand. The round-31+ fair_v2/λ/re-test work is UNAFFECTED (built on
  collector quotes, not the updown files). A corrected April-era bucket
  re-run on the ~477 live entries is possible but N≥150/bucket is unlikely;
  the live quote-based pipeline supersedes it. Also queued: apply the
  placeholder filter to any future use of the updown price files.
- 2026-09-02: round 55 — DEEP kacho pass resolved + a data-hygiene finding:
  the round-54 discrepancy (0.225 median across 671 markets) was **380,000
  placeholder rows (up_price == 0.50 exactly) in our updown price files** —
  the venue recorder's no-book default. After excluding placeholders, the
  surviving live rows agree with kacho at **median 0.005 (half tick), 84.8%
  within 2 ticks** — matching round 54. Two implications: (i) any consumer
  of the updown price files must filter exact-0.50 rows (the April-era
  evaluator's filters may not have caught them all — a caveat for its entry
  prices; queued check); (ii) the tick-level agreement result is now
  confirmed on the deep sample (live rows only). Placeholder-vs-live
  distinction = consecutive identical 0.50 runs, trivially detectable.
- 2026-09-02: round 59 — STRIKE-BASIS DECOMPOSITION COMPLETE: joint
  (delta, lambda) fit on the fair residuals gives **delta* = 0.00 exactly**
  (lambda*=1.85, Brier unchanged) — the -5.5bp Chainlink-vs-Binance level
  bias does NOT appear in the fair residuals. Why: the collector stores
  up-token books only (the -1 down-token markets carry no quotes — that is
  the collector's design, discovered via the side-join), so every scored
  quote is an up-market yes token, and our z uses Binance-vs-Binance for
  BOTH strike and settlement — the +5.5bp source bias cancels in the
  difference. Decomposition conclusion: **the extreme-band residual is
  pure variance understatement (lambda=1.9) plus small fat tails; no
  strike correction is needed in fair_v2**, and the Binance-proxy strike
  is validated for probability purposes despite the level difference. The
  24h tape remains useful for regime stability checks of the basis. The
  side-join also revealed a collector design fact: down-token books are
  not collected (only the -0 up-market series is polled, both sides).
- 2026-09-02: round 58 — strike-basis DISTRIBUTION established (9 windows ×
  3 assets, tape 1.41h): **27/27 windows negative; basis ≈ −5.5bp
  systematic** (BTC mean −5.5 [−4.7,−7.5]; ETH −5.2; SOL −5.9 [−0.1,−11.0]).
  A LEVEL bias between Chainlink-TWAP strikes and Binance-open proxies, not
  drift (drift would average out across windows). Magnitude: half a
  calibrated σ (σ_eff ≈ 11bp) — and it produces opposite-sign fair errors
  on up vs down markets, which the variance-only λ fit cannot absorb. This
  is the first decomposed component of the extreme-band residual: the
  corrected fair uses K_chainlink ≈ K_binance × (1 − 5.5e-4) once the 24h
  tape confirms stability across regimes. collector_verify re-run: PASS
  (315,884 quotes; tape 14,226 rows clean).
- 2026-09-02: round 57 — corrected April-era re-run CLOSED as impossible
  with local data: (i) the updown file's `resolution` column is 99% unset
  (708 of 714 BTC 5m entries carry -1) — the labels the historical
  evaluator used are not in the surviving snapshot; (ii) the kline files
  have been ROTATED — data/raw only spans 2026-08-21 → 09-02, so April-era
  Binance strikes are gone locally (re-downloadable via Binance REST if
  ever required). The round-56 re-qualification stands as final: the April
  bucket analysis is invalid-and-unrecoverable locally; the live
  quote-based pipeline (round 31-40) supersedes it. **Operational fact
  recorded: kline_1m storage is rolling ~12 days — any backtest needing
  older klines must re-download from Binance REST.** Gates: tape 1.06h+.
- 2026-09-02: round 61 — kacho tick deeper pass CLOSED at its maximum
  sample: relaxed thresholds still yield only 3 markets / 559 pairs
  (381,333 placeholder rows dropped — the updown files are overwhelmingly
  0.50 placeholders in the kacho overlap era). Within that maximal sample:
  **median 0.005 (half tick), p90 0.025, 95.5% within 5 ticks** — the
  tick-level agreement result is final. The kacho tick lane is complete;
  no further depth is available from these files.
- 2026-09-02: round 60 — daily-block CI re-check on fresh data (102,911
  quotes, +1,330 vs round 40): **v2_ewma EV +8.42c/trade, daily-block CI
  [+5.48, +11.87]** — strengthened from +7.61c [+4.92,+10.19]; v1_r24
  +6.70c [+4.22,+10.39]; favorites control still negative (-3.75c); lambda*
  stable (v2_ewma 1.86, Brier 0.1718 — marginally improving with data). The
  calibrated gate's positive EV continues to hold and strengthen as gated
  days accumulate. Drift clean (arXiv 2608.30999).
- 2026-09-02: round 62 — TWAP-keyword GitHub scan: SEO pollution arrived
  in the post-Aug-7 bot niche (multiple keyword-stuffed repos); abrownfox's
  twap60 trigger system flagged for next-session code read. Changelog and
  arXiv drift clean.
- 2026-09-02: round 63 — abrownfox twap60 CODE-READ (§2h): KEEP-CORNERSTONE —
  the closest external analogue to our engine (TWAP-anchored ~50¢ directional
  with scratch culling; public signal = hand-tuned fair_z; 60.7% WR on 150
  resolved at ~50¢, +24.5% ROI sample, on-chain verifiable).
- 2026-09-02: round 65 — spread-capture guide FULL BODY extracted (69KB .md;
  the earlier pass only caught the TOC): (i) worked arithmetic — Up
  accumulates on dips at blended $0.36 while Down trades $0.64, then Down
  dips to $0.53 while Up bounces to $0.47 → **pair cost $0.89 vs $1.00
  settlement**; (ii) **reference wallet: median paired cost $0.809/session,
  +3.79% on ~$9,700 (+$369)** — the sequential-dip method is worth ~21¢/pair
  over SLIP-ME's $1.0183 simultaneous cost (the dip-waiting IS the edge);
  (iii) the actual sizing code: depth-scaled clips (BASE 10 / MAX 20 shares,
  DEPTH_GAIN 60 on the dip depth below the side's ceiling = ceiling −
  other_avg, imbalance guard 40 shares); (iv) "a 37% win rate is healthy
  here" — third explicit win-rate-meaningless statement, now from the
  strategy designer; (v) no exit management by design, with a dedicated
  section on what adding one costs. Updates the maker-mode design numbers
  in the catalog: sequential-dip pairing at $0.81 blended is the benchmark,
  not $1.02 simultaneous.
- 2026-09-02: round 64 — CI checkpoint on refreshed data (103,027 quotes,
  +116): **v2_ewma +8.42c/trade, daily-block CI [+5.48,+11.89] — stable**;
  v1_r24 +6.70c; favorites control -3.75c; lambda* fixed at 1.86 (Brier
  0.1718). The +8c/trade day-level result is reproducible across refreshes.
  Drift clean (arXiv 2608.30999).

- 2026-09-02: round 66 — CI checkpoint: **v2_ewma +8.45c/trade, daily-block
  CI [+5.48,+11.95]** — stable with marginal strengthening (+8.42 round 64);
  v1_r24 +6.70c; favorites -3.60c; lambda* stable (v2_r24 1.94, Brier
  0.1722). Drift clean (arXiv 2608.30999). CSDN fresh scan: server-blocked

- 2026-09-02: round 67 — abrownfox engine.ts scratch-culling logic fully
  captured: entry on `edge ≥ edgeThreshold` (edge = |pUp − 0.5|); hold while
  conviction positive; **scratch (limit-sell near bid) when edge <
  entryEdge − decayThreshold OR edge < decayThreshold** (decay-from-entry
  OR absolute floor); scratchAttempts tracked; per-window slot caps
  (clipUsd + maxSlotUsd). Two edge definitions now on record for the
  integration design: theirs = conviction vs coin-flip; ours = value vs
  price paid (prob − ask > fee) — economically stricter (theirs would buy
  a fairly-priced 50¢; ours requires the discount). Tape 2.17h. Drift

- 2026-09-02: round 68 — collector_verify periodic re-run: **PASS** (316,990
  quotes zero dups/non-monotonic; crossed 2.32% stable; TWAP tape 26,417
  rows across 12 files zero anomalies — integrity holds as the tape
  doubles). Reddit fresh scan: blocked (known pattern). Drift clean (arXiv

- 2026-09-02: round 69 — CI checkpoint (103,281 quotes): **v2_ewma +8.46c/
  trade, daily-block CI [+5.48,+11.94]** — fourth consecutive stable
  confirmation, Brier marginally improving (0.1717). Reddit search-based
  scan: empty shell (blocked). Drift clean (arXiv 2608.30999).

- 2026-09-02: round 70 — Kalshi KXBTC15M docs probe: JS-rendered shells
  (curl-inaccessible); the round-42 search-recorded facts (CF Benchmarks
  BRTI, 60s averaging window) stand as the cross-venue settlement record.
  A dedicated Kalshi API session (trading-api.readme.io) remains the path
  if the second-venue port advances. Tape 2.43h (healthy). Drift clean

- 2026-09-02: round 71 — PR&R main build guide indexed (83KB .md fetched;
  "How to Build a Polymarket Trading Bot"): full task-by-task tutorial —
  Gamma market resolution, CLOB WS streaming, signal engine + volume/spread
  filters, order management, risk/bankroll, **market-synchronized
  scheduling**, pre-launch health checks. Structure mirrors our daemon
  design independently (validation by convergence). Tape 2.48h. Drift clean

- 2026-09-02: round 72 — PR&R signal-engine section deep-read: base signal =
  spot-vs-reference direction + the market's implied probability (our
  fair-vs-ask at its simplest); **two pre-signal filters: spread > 6¢ →
  skip; seconds_to_expiry < 120 → skip ("late entries have high adverse
  selection risk")** — the THIRD independent implementation of the
  late-window exclusion (our 90s rule, abrownfox's pivot, PR&R's 120s).
  Tape 2.54h. Drift clean (arXiv 2608.30999).
  (arXiv 2608.30999).
  (arXiv 2608.30999).
  2608.30999).
  clean (arXiv 2608.30999).
  (521, known pattern).
- 2026-09-02: round 73 — created-this-week scan (§2i): draxmit accuracy/
  calibration EDA (~100k markets — confidence-accuracy curve matches ours at
  scale; YES bias; keyword effects) and Nabeel-javed strategy-lab (LP + 15m
  maker-rebate simulation, runnable). Tape 2.58h. Drift clean.
- 2026-09-02: round 81 — Kalshi tooling lane (§2j): haoo99 PM↔Kalshi 15-min
  BTC arb bot (strategy B for our product pair) + a synthetic-arb variant —
  the cross-venue lane is live and competitive. Copy-trade/AI repos
  DISCARD. Drift clean (arXiv 2608.30999; changelog unchanged).