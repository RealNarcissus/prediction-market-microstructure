# Operations — data plane & paper-trading daemons

The research program concluded in October 2026 and the four systemd user
services were stopped and disabled. This document is the runbook: what ran,
what it collected, and how to bring it back.

## Services (all currently stopped + disabled)

| unit | role |
|---|---|
| `quantbtc.service` | data collector: Jupiter Up/Down quotes/resolutions + Binance WS (aggTrade, top-of-book depth 100 ms, 1m klines) |
| `quantbtc-twap.service` | Chainlink TWAP tape collector (settlement oracle) |
| `quantbtc-wallet.service` | live paper wallet, $5/day controlled, gate v2 |
| `quantbtc-paper-gate.service` | twin daemon, same gate, independent ledger |

Unit files live in `~/.config/systemd/user/`. To resume:

    systemctl --user enable --now quantbtc quantbtc-twap quantbtc-wallet quantbtc-paper-gate
    systemctl --user status quantbtc            # health
    journalctl --user -u quantbtc -f            # live output

To stop again: `systemctl --user disable --now <unit>`.

## Setup

    python3.11 -m venv .venv
    .venv/bin/pip install -e '.[dev,research]'

The collector needs a Jupiter Prediction API key in `.env` (gitignored):

    JUP_API_KEY=...

## What it collects (→ `data/`, gitignored)

- Jupiter: up/down epoch metadata, best bid/ask for active BTC/ETH/SOL epochs
  (rate-limited: discovery every 60 s paginated, ≤5 orderbooks per 10 s cycle,
  429 backoff), and final resolutions → `data/collector.db`
- Binance spot WS: aggTrade + top-of-book depth (100 ms) + 1m klines for
  BTC/ETH/SOL → hourly Parquet under `data/raw/<SYM>/<stream>/`
- Chainlink TWAP settlement tape → consumed by the settlement checks

## Backfill Binance kline gaps

    .venv/bin/python -m quantbtc.backfill --symbol btcusdt --hours-ago 24

## Daily sanity report

    .venv/bin/python -m quantbtc.report     # -> reports/daily-YYYYMMDD.md

## Notes

- Binance **spot** streams are used (futures WS is blocked in some
  environments; spot tracks the Chainlink oracle's aggregate feeds).
- Everything is path-driven via `config/config.yaml`; a fresh machine only
  needs the repo, a venv, and `.env`.
- Collected data is deliberately not redistributed (see README "Data").
