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
| 2026-08-07 → now | **TWAP: 30s average for 5m markets, 60s for 15m/4h**, Chainlink Data Streams; $1M liquidity rewards attached (Aug, ~$550k on 5m markets) | same + [Genfinity 2026-08-12](https://genfinity.io/2026/08/12/chainlink-twap-data-streams-polymarket-crypto-markets/) |

- Why it changed: Stanford + SMU study ([arXiv:2606.31675](https://arxiv.org/abs/2606.31675)): **821 accounts earned $8.2M** pushing Binance BTC across the strike in the final 2–3s of snapshot-settled 5m windows (cost $5–20k to move spot → $50k+ payout; fragmented orders, off-hours timing). "A bet the market treated as near certain was overturned one time in three" (90%+ priced contracts flipped in manipulated windows). Ex-MMs, **93% of losses fell on retail**. Fix raises attack cost but sustained full-window pushes remain possible.
- Kalshi comparison: CF Benchmarks index with 60-second moving average + KYC/CFTC.
- **Impact on us**: (i) our updown historical data spans BOTH regimes → any label-based analysis should carry a settlement-regime flag (Aug 7 boundary); (ii) our CLT fair models a *running* TWAP to window close, but venue settles the **final 30s/60s average** — that averaging-window mismatch plausibly explains the overconfidence we measured (fair 95¢ → 73.5% realized): running-TWAP variance is lower than final-window variance, so our fair values are too extreme. Fix: recompute fair with final-window averaging (Var = σ²·w/3 for window w at distance d ≥ w; blends toward European digital for d < w); (iii) live wallet should avoid entries in the final ~90s (manipulation-noise zone; also the sniper-bots' contest zone).

| Fact | Detail | Impact on us |
|---|---|---|
| Min order size — order-type + market dependent | Docs book example: `min_order_size: "5"` **shares** (limit orders). CSDN practitioner (犀牛_c, [project summary](https://blog.csdn.net/2301_76809965/article/details/161971817)): market orders via py-clob-client `MarketOrderArgs` take `amount` in **USDC** and fail below `amount=1` → $1 min for market orders. Both can be per-market fields. | **ACT**: do not hardcode — read `min_order_size` per market from the CLOB API in wallet/evaluator. $5 envelope: 1 market order/day typical, or 5-share limit at ask≤$1.00. |
| Order types GTC, GTD, FOK, FAK | Market orders support FOK (fill-all-or-kill) and FAK (fill-and-kill) | **ACT**: FOK removes the legging risk noted by the Zhihu arb tutorial for YES+NO combos. Also enables "take only if full size" entries in the wallet. |
| Post-only orders | Place maker order that can't take | **REF**: for maker entries (our asks region 25–75¢ carries all EV) |
| Batch orders | 1–15 orders per call | REF (only if we ever ladder) |
| Tick size regime | 0.01 → 0.0001 rules by price band | REF — affects rounding in fair-vs-ask comparisons |
| `market.trading.secondsDelay` + `delayed` status | Some markets have a matching delay on marketable orders | **VERIFY**: if 5m/15m crypto markets carry a near-settlement matching delay, late-window sniping dynamics change. Check CLOB API for our exact markets. |
| Chainlink TWAP Prices page exists (Market Data section) | Polymarket publishes the TWAP feed its crypto markets settle on | **ACT**: replaces our Binance-proxy strike/TWAP fair value with the venue's own oracle series → cleaner fair_yes, removes Binance-vs-Chainlink basis from the staleness signal. |
| Taker Rebate Program + Maker Rebates | Programs pages exist (details pending fetch) | **VERIFY**: rebates change net-EV math; taker rebates are unusual and would fatten our taker edge if we qualify. |
| **Fee formula CONFIRMED** (docs.polymarket.com/trading/fees, fetched in full 2026-09-02) | `fee = C × feeRate × p × (1−p)`, C = shares, p = price. **Crypto category feeRate = 0.07** → fee table peaks $1.75/100 shares at 0.50. Makers never charged; fees fund Maker Rebates (crypto: 20% of fees, redistributed daily); tiered Taker Rebate Program on top. Fee precision: 5 decimals, min 0.00001 USDC. News claims of "1.56%" (TradingView/Cointelegraph summary) and "up to 3%" (KuCoin) are wrong. | **RESOLVED**: our `0.07·p·(1−p)` model is exactly right for Polymarket crypto — no code change needed. Open minor item: fee introduction date (if fees postdate part of our sample, historical EV was overstated → conservative direction). Rebate programs = potential cost reduction if we ever scale. |

Sources: [Place Orders](https://docs.polymarket.com/trading/place-orders),
[Fees](https://docs.polymarket.com/trading/fees),
[py-clob-client#326](https://github.com/Polymarket/py-clob-client/issues/326).

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
| [KaustubhPatange/polymarket-trade-engine](https://github.com/KaustubhPatange/polymarket-trade-engine) | Open-source engine + `LEARNING.md` (PM/order-book primer) + `docs/GUIDE.md` (strategy dev); author is a BitGo SWE; Medium build log exists (403-blocked) | **REF** — engineering-quality reference; LEARNING.md useful onboarding doc |
| [Benjam1nCup/Polymarket-trading-bot-python-V2](https://github.com/Benjam1nCup/Polymarket-trading-bot-python-V2) (README fetched) | MIT "education" repo (sells full bots): post-TWAP-60s strategies — Momentum Arbitrage (multi-signal, ~$2.5k rec. capital), **TWAP Reversal Bot targeting "final 90 seconds when BTC TWAP is near the boundary"** (whale-reversal sniper), "101-cents bot" claiming ≥101¢ returned per $1 YES+NO pair (~190 trades/day) — likely monetizing the maker rebate on top of par | **DISCARD as evidence** (self-reported, selective screenshots, "never incurs a loss" is a red flag). **KEEP the strategy taxonomy**: (i) confirms the final-90s window is where manipulation/reversal battles happen → stay out or model explicitly; (ii) the 101-cents claim implies maker-rebate economics can push paired payouts above par — worth a math check if we ever go maker mode. |
| [tradoxvps.com](https://tradoxvps.com/blog/) + LinkedIn | Polymarket-specific VPS vendor; $1M liquidity-rewards coverage; TWAP-settlement explainers | REF (infra vendor exists → latency game is real for the fast lane) |
| [chudi.dev: Binance→Polymarket momentum signal pipeline](https://chudi.dev/blog/binance-polymarket-momentum-signal-pipeline) | Sub-100ms order execution on PM signals from Binance flow | REF (the fast lane we deliberately don't contest) |

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
| [arXiv:2508.03474](https://arxiv.org/abs/2508.03474) Unravelling the Probabilistic Forest | Taxonomy: market-rebalancing arb (within condition) vs cross-market arb | **REF** — frames our staleness trade as a "rebalancing" subclass; useful vocabulary |
| [arXiv:2606.04217](https://arxiv.org/abs/2606.04217) Polymarket-v1 DB | 1.2B trades / 1.3M markets / $61B; tests microstructure-quality → forecast-accuracy link | REF |
| [arXiv:2510.15612](https://arxiv.org/abs/2510.15612) SoK: DePM microstructure | Systematization of decentralized prediction-market MM | REF (background) |
| [arXiv:2604.20421](https://arxiv.org/abs/2604.20421) full-lifecycle datasets; [PolyBench 2604.14199](https://arxiv.org/abs/2604.14199) LLM benchmark (38,666 markets) | Datasets/benchmarks | DISCARD for edge purposes (LLM-forecast benchmark ≠ our problem); REF as data sources |
| [arXiv:2603.03136](https://arxiv.org/abs/2603.03136) Anatomy of Polymarket (2024 election) | PM vs polls aggregation | DISCARD (politics, not our horizon) |
| SSRN "Polymarket Paradox" (Abid 2026) | Manipulation/whale activity; $250M+ settled via governance votes after oracle disputes | **KEEP-RISK**: resolution risk is a real tail for live trading — our ledger must record settlement-dispute incidents |

## 5. Reddit / practitioner threads

| Thread | Claim | Verdict |
|---|---|---|
| [r/SideProject: bot on 5-min crypto markets](https://www.reddit.com/r/SideProject/comments/1vckypo/i_made_a_bot_that_trades_polymarkets_5minute/) | "$180 overnight" | DISCARD as evidence (single-night, no CI); the existence of many such bots = competition note |
| [r/algotrading: 5-min bot update 2](https://www.reddit.com/r/algotrading/comments/1u0cz4n/update_2_i_was_bored_so_i_though_of_making_a_5min/) | Profits in trends, loses badly in chop/reversal | **KEEP-INSIGHT**: independent replication of our regime-conditional result — momentum-style edges on these markets are regime-dependent; matches our vol-tercile bucketing |
| [r/Polymarket: 7 months testing every 5-min strategy](https://www.reddit.com/r/Polymarket/comments/1un85mg/i_spent_7_months_testing_every_strategy_on/) | Deep-dive (fetch blocked; retry) | PENDING — highest-priority retry: matches our exact market |
| [r/PredictionsMarkets: reality of bots](https://www.reddit.com/r/PredictionsMarkets/comments/1uju247/reality_of_trading_bots_in_polymarket_ideas/) + [consistency thread](https://www.reddit.com/r/PredictionsMarkets/comments/1u7jkvv/has_anyone_actually_built_a_consistently/) | Realistic expectations; few consistently profitable | KEEP-INSIGHT (prior calibration for our expectations) |
| [r/AI_Agents: self-rewriting bot cautionary tale](https://www.reddit.com/r/AI_Agents/comments/1rkpm7y/we_built_a_trading_bot_that_rewrites_its_own/) | "83% win rate… 5 wins totaled $12.78 but a single loss cost $100" | **KEEP-INSIGHT**: win-rate is meaningless in binary markets; EV per trade is the only metric (independent replication of our fee-first EV framing) |
| [HN 48461522: arb bot real numbers](https://news.ycombinator.com/item?id=48461522) | Jan–late Mar 2026, 3,858 bets, ~$5k net; never predicts winners — de-vigs sportsbook odds and takes pricing differences | **KEEP-INSIGHT**: a durable edge example that is exogenous-model-based (external fair from sportsbooks) + price-difference taking — structurally the SAME shape as our staleness trade (exogenous fair from the underlying, take mispriced venue quotes). Sports lane, ~$2k/mo at real scale. |
| [HN 48573307: free 5m crypto dataset](https://news.ycombinator.com/item?id=48573307) | Public historical dataset for Polymarket 5m crypto markets (24/7, 7 coins); no public history existed before | **REF** — locate repo; second validation source alongside OpenMarket |
| [Yahoo Finance: arb bots dominate](https://finance.yahoo.com/) (search snippet) | Bot trading exclusively BTC/ETH/SOL 15m up/down, $4–5k bets, claimed 98% win rate | DISCARD as evidence (98% WR with big size on 15m markets = likely paired-side arb or marketing); competition note only |
| [dev.to/soulcrancerdev: TWAP resolution changes bot design](https://dev.to/soulcrancerdev/how-polymarket-twap-resolution-changes-trading-bot-design-2g1o) + [trading strategies journal](https://dev.to/soulcrancerdev/polymarket-trading-strategies-2ja4) | Practitioner journal on the "current TWAP edition": signals, data pipelines, execution, risk after Aug-7 switch | **REF** (fetch pending) — closest practitioner running-log to our setup; check their signal list vs ours |
| [dev.to/nagi777: momentum spike research](https://dev.to/nagi777/polymarket-momentum-arbitrage-real-time-spike-research-3n80), [abrownfox001: 4-strategy lessons](https://dev.to/abrownfox001/building-a-production-polymarket-trading-bot-lessons-from-4-strategies-49k0), [borntoup: WS/CLOB/risk 2026](https://dev.to/borntoup/building-a-polymarket-trading-bot-in-2026-websockets-order-books-clob-execution-risk-3kcd) | DEV.to practitioner articles on the same markets | REF (fetch pending) |
| [blog.devgenius.io: "math that guarantees profit"](https://blog.devgenius.io/just-found-the-math-that-guarantees-profit-on-polymarket-and-why-retail-traders-are-just-providing-6163b4c431a2) | 17,218 market conditions, ~41% had single-market arb | **KEEP-INSIGHT with contradiction**: 41% vs NBA paper's 7 executable arbs — reconciles by market type (long-tail/illiquid politics vs in-game sports). Our 5m/15m crypto = high-volume sports-like regime → expect NBA-style efficiency, i.e., few mechanical arbs; our edge must be model-based. "Retail traders are just providing" framing matches the Stanford/SMU 93%-retail-losses finding. |
| r/algotrading: open-source MM bot (MIT) | Author: CLOB liquidity "utterly useless" in most markets | REF — liquidity depth matters for sizing; consistent with our asks 25–75¢ EV concentration and 5-share min |

## 6. Kalshi / other venues

| Source | Content | Verdict |
|---|---|---|
| [rodlaf/kalshimarketmaker](https://github.com/rodlaf/kalshimarketmaker) (+ [HN thread](https://news.ycombinator.com/item?id=43073378)) | MM bot with safety controls, parallel strategy configs | **REF** — the safety-control structure (per-strategy config, kill-switch) is a checklist for our live daemon |
| [botforkalshi 30+ bots catalog](https://www.botforkalshi.com/blog/open-source-kalshi-bot-ecosystem), [Alphascope review](https://www.alphascope.app/blog/kalshi-trading-bot-github) | Ecosystem maps | REF |
| OctagonAI / yllvar Kalshi bots | AI-CLI and enterprise-style bots | DISCARD (no edge methodology) |
| [Medium: 4 strategies bots profit from (2026)](https://medium.com/illumination/beyond-simple-arbitrage-4-polymarket-strategies-bots-actually-profit-from-in-2026-ddacc92c5b4f) | MM example $1,247 on $10k/3wk (12.5%) | PENDING fetch (403) — MM-on-$10k economics matter if we scale past paper stage |

## 7. Practitioner tactics (single lines worth keeping)

- @w00dsbot (Threads): "Wait for 5-minute BTC contract mispricings (<$0.35)" —
  cheap-side entries only. **Maps directly onto our finding**: our EV lives at
  asks 25–75¢ with calibrated gap; <$0.35 mispricing entries ≈ our gap>fee
  filter on the low side. Independent confirmation of the entry region.
- Chop kills trend-following bots (r/algotrading) = our vol-regime buckets.
- MM beats directional on these venues per multiple independent sources —
  our answer is intermediate: we *take* stale quotes with a calibrated fair
  (taker), but a maker mode is the documented path if taker edge decays.

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
| 7 | Locate HN 48573307 free 5m dataset repo; add as second validation source | next session |
| 8 | Read Taker Rebate Program page + soulcrancerdev TWAP-design articles + Moonsat 6-types + r/Polymarket 7-months thread (all fetch-blocked this round) | next session |
| 9 | Maker-rebate math check (can paired YES+NO + rebate exceed par?) | deferred (maker mode only) |
| 10 | Add collector job for the venue's Chainlink TWAP/Data Streams series (replaces Binance proxy in fair value; removes basis risk) | next session |
| 11 | Check `market.trading.secondsDelay` for our 5m/15m markets via CLOB API; if delayed matching applies near settlement, exclude those windows | next session |
| 12 | Ledger: record settlement-dispute/manipulation incidents as tail-risk events | ongoing |

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
