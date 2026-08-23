# quant-btc

Short-horizon (5m/15m) BTC/SOL direction research against Jupiter Up/Down
prediction markets. This repo currently contains **Phase 0+1**: the fee
foundation and the always-on data collection platform.

- Spec: `docs/superpowers/specs/2026-08-23-jupiter-direction-model-design.md`
- Live API recon (event shapes, TWAP resolution, rate limits):
  `docs/RECON.md`
- Implementation plan: `docs/superpowers/plans/2026-08-23-phase0-1-data-platform.md`

## Key facts

- Jupiter up/down epochs resolve on the **Chainlink TWAP over the window vs
  the window-start price** (not endpoint price) — see `docs/RECON.md`.
- Fees: `ceil_to_cent(0.07 × p × (1-p) × contracts)` per order (matches
  Jupiter's documented samples; `src/quantbtc/fees.py`).
- Binance **spot** streams are used (futures WS is blocked in some
  environments; spot tracks the Chainlink oracle's aggregate feeds).

## Setup

    python3.11 -m venv .venv
    .venv/bin/pip install -e '.[dev]'

Get a Jupiter Prediction API key from the Jupiter developer Portal and put it
in `.env` (gitignored):

    JUP_API_KEY=...

## Run recon (once, already done — re-run if the API changes)

    set -a; . ./.env; set +a
    .venv/bin/python scripts/jupiter_recon.py
    # findings -> docs/RECON.md

## Run the collector (always-on)

    set -a; . ./.env; set +a
    nohup .venv/bin/python -m quantbtc.daemon >> data/collector.log 2>&1 &

Graceful stop: `kill -TERM <pid>` (flushes parquet buffers, closes sqlite).

What it collects:

- Jupiter: up/down epoch metadata, best bid/ask for active BTC/ETH/SOL epochs
  (rate-limited: discovery every 60 s paginated, ≤5 orderbooks per 10 s
  cycle, 429 backoff), and final resolutions.
- Binance spot WS: aggTrade + top-of-book depth (100 ms) + 1m klines for
  BTC/ETH/SOL → hourly Parquet under `data/raw/<SYM>/<stream>/`.

## Backfill Binance kline gaps

    .venv/bin/python -m quantbtc.backfill --symbol btcusdt --hours-ago 24

## Daily sanity report

    .venv/bin/python -m quantbtc.report
    # -> reports/daily-YYYYMMDD.md

## Tests

    .venv/bin/pytest -q

## VPS migration (later)

Everything path-driven via `config/config.yaml` (`storage.sqlite_path`,
`storage.parquet_dir`). Copy repo + data/, install, run under systemd:

    [Unit]
    Description=quantbtc collector
    After=network-online.target
    [Service]
    WorkingDirectory=/opt/quantbtc
    EnvironmentFile=/opt/quantbtc/.env
    ExecStart=/opt/quantbtc/.venv/bin/python -m quantbtc.daemon
    Restart=always
    RestartSec=10
    [Install]
    WantedBy=multi-user.target

On a VPS, futures WS (`fstream.binance.com`) may be reachable — switch
`binance.ws_url` in config if perp data is preferred.
