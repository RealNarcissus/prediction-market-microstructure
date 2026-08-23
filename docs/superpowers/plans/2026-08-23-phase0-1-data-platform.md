# Quant-BTC Phase 0+1: Fee Foundation & Data Platform — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Jupiter fee/economics foundation (Phase 0) and the always-on Binance + Jupiter data collection platform (Phase 1) per `docs/superpowers/specs/2026-08-23-jupiter-direction-model-design.md`.

**Architecture:** A Python package `quantbtc` with five areas: config, fee math, Jupiter API client, a Binance websocket collector writing Parquet, a Jupiter quote poller writing SQLite, and a daemon that runs both with graceful shutdown/restart. Pure parse/math functions are separated from I/O so everything is unit-testable offline; live-network pieces are thin wrappers verified by a one-time recon script.

**Tech Stack:** Python 3.11+, httpx, websockets, polars, PyYAML, sqlite3 (stdlib), pytest.

**Out of scope (later plans):** feature builder, Φ(d₂) fair-value engine, LightGBM models, paper trader, statistical verdict tooling.

**Verified API facts used below** (from developers.jup.ag, 2026-08-23):
- Base URL `https://api.jup.ag/prediction/v1`, auth header `x-api-key`.
- `GET /events` (params incl. `filter=live`, `includeMarkets`), `GET /markets/{marketId}`, `GET /orderbook/{marketId}`, `GET /trading-status`.
- Market fields: `marketId`, `eventId`, `title`, `status` (`open|closed|cancelled`), `result` (`null|yes|no`), `openTime`/`closeTime` (unix seconds), `pricing` with `buyYesPriceUsd` etc. where **1,000,000 = $1.00**.
- Orderbook: `yes`/`no` arrays of `[price_in_cents, qty]`, plus `yes_dollars`/`no_dollars` (`[["0.0100", qty], ...]`).
- Fees: charged on execution, rounded **up to the nearest cent**; documented samples match `rate × p × (1−p)` per contract with rate = 0.07 (100 @ $0.25 → $1.32; 100 @ $0.01 → $0.07). Task 6 re-verifies against live data.
- Binance Futures WS combined stream: `wss://fstream.binance.com/stream?streams=<s>@aggTrade/<s>@depth20@100ms/<s>@kline_1m`.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `config/config.yaml`, `src/quantbtc/__init__.py`, `tests/conftest.py`, `tests/test_scaffold.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "quantbtc"
version = "0.1.0"
description = "Short-horizon direction model vs Jupiter Up/Down (paper trading research)"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "websockets>=12.0",
    "polars>=1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: hits live network APIs (deselect with '-m \"not integration\"')"]
```

- [ ] **Step 2: Create `config/config.yaml`** (values pinned/updated by Task 6 recon)

```yaml
fees:
  rate: 0.07          # per-contract coefficient, Kalshi-style; verified in Task 6
  round_cents: true   # Jupiter rounds the order fee up to the nearest cent

jupiter:
  base_url: https://api.jup.ag/prediction/v1
  api_key_env: JUP_API_KEY
  poll_interval_s: 2.0
  result_delay_s: 5.0        # wait after closeTime before fetching final result
  event_filter: live
  asset_patterns: ["BTC", "ETH", "SOL"]

binance:
  symbols: [btcusdt, ethusdt, solusdt]
  ws_url: wss://fstream.binance.com/stream
  rest_url: https://fapi.binance.com

storage:
  sqlite_path: data/collector.db
  parquet_dir: data/raw
```

- [ ] **Step 3: Create package and test files**

`src/quantbtc/__init__.py`:
```python
"""quantbtc: short-horizon direction research vs Jupiter Up/Down."""
```

`tests/conftest.py`:
```python
import pytest
from pathlib import Path

@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
```

`tests/test_scaffold.py`:
```python
def test_package_imports():
    import quantbtc
    assert quantbtc.__doc__
```

- [ ] **Step 4: Install and run tests**

Run: `cd /home/charleton/Desktop/agentProjects/ZCode/quant-btc && python3.11 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest -q`
Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml config/ src/ tests/
git commit -m "chore: project scaffold with config skeleton"
```

---

### Task 2: Config loader

**Files:**
- Create: `src/quantbtc/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
from quantbtc.config import load_config

def test_load_config_defaults_and_overrides(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
fees:
  rate: 0.07
jupiter:
  poll_interval_s: 3.0
binance:
  symbols: [btcusdt, solusdt]
storage:
  sqlite_path: data/x.db
""")
    cfg = load_config(cfg_file)
    assert cfg.fees.rate == 0.07
    assert cfg.fees.round_cents is True
    assert cfg.jupiter.poll_interval_s == 3.0
    assert cfg.jupiter.base_url == "https://api.jup.ag/prediction/v1"
    assert cfg.binance.symbols == ("btcusdt", "solusdt")
    assert cfg.storage.sqlite_path == "data/x.db"
    assert cfg.storage.parquet_dir == "data/raw"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'quantbtc.config'`

- [ ] **Step 3: Write `src/quantbtc/config.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class FeesConfig:
    rate: float = 0.07
    round_cents: bool = True


@dataclass(frozen=True)
class JupiterConfig:
    base_url: str = "https://api.jup.ag/prediction/v1"
    api_key_env: str = "JUP_API_KEY"
    poll_interval_s: float = 2.0
    result_delay_s: float = 5.0
    event_filter: str = "live"
    asset_patterns: tuple[str, ...] = ("BTC", "ETH", "SOL")


@dataclass(frozen=True)
class BinanceConfig:
    symbols: tuple[str, ...] = ("btcusdt", "ethusdt", "solusdt")
    ws_url: str = "wss://fstream.binance.com/stream"
    rest_url: str = "https://fapi.binance.com"


@dataclass(frozen=True)
class StorageConfig:
    sqlite_path: str = "data/collector.db"
    parquet_dir: str = "data/raw"


@dataclass(frozen=True)
class Config:
    fees: FeesConfig = FeesConfig()
    jupiter: JupiterConfig = JupiterConfig()
    binance: BinanceConfig = BinanceConfig()
    storage: StorageConfig = StorageConfig()


def load_config(path: str | Path = "config/config.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    fees = FeesConfig(**raw.get("fees", {}))
    jup_raw = dict(raw.get("jupiter", {}))
    if "asset_patterns" in jup_raw:
        jup_raw["asset_patterns"] = tuple(jup_raw["asset_patterns"])
    jup = JupiterConfig(**jup_raw)
    bnc_raw = dict(raw.get("binance", {}))
    if "symbols" in bnc_raw:
        bnc_raw["symbols"] = tuple(bnc_raw["symbols"])
    bnc = BinanceConfig(**bnc_raw)
    storage = StorageConfig(**raw.get("storage", {}))
    return Config(fees=fees, jupiter=jup, binance=bnc, storage=storage)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_config.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/config.py tests/test_config.py
git commit -m "feat: config loader with typed sections"
```

---

### Task 3: Fee model (the economics core)

**Files:**
- Create: `src/quantbtc/fees.py`
- Test: `tests/test_fees.py`

- [ ] **Step 1: Write the failing test** (uses Jupiter's documented worked examples)

```python
import pytest
from quantbtc.fees import (
    fee_per_contract, order_fee, breakeven_win_prob, expected_value,
)

def test_fee_per_contract_kalshi_formula():
    assert fee_per_contract(0.25) == pytest.approx(0.07 * 0.25 * 0.75)
    assert fee_per_contract(0.50) == pytest.approx(0.0175)

def test_order_fee_matches_jupiter_documented_samples():
    # Jupiter docs: 100 contracts @ $0.25 -> $1.32 fee; 100 @ $0.01 -> $0.07
    assert order_fee(0.25, 100) == pytest.approx(1.32)
    assert order_fee(0.01, 100) == pytest.approx(0.07)

def test_order_fee_rounds_up_to_cent_and_has_minimum_one_cent():
    assert order_fee(0.01, 1) == pytest.approx(0.01)   # 0.00693c -> 1c
    assert order_fee(0.30, 7) == pytest.approx(0.11)   # 7*0.0147=0.1029 -> 0.11

def test_order_fee_can_skip_rounding():
    assert order_fee(0.25, 100, round_cents=False) == pytest.approx(1.3125)

def test_breakeven_and_ev():
    f = fee_per_contract(0.50)                     # 0.0175
    assert breakeven_win_prob(0.50, f) == pytest.approx(0.5175)
    assert expected_value(0.55, 0.50, f) == pytest.approx(0.0325)

def test_invalid_price_rejected():
    with pytest.raises(ValueError):
        fee_per_contract(1.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_fees.py -q`
Expected: FAIL with `ModuleNotFoundError`/`ImportError`

- [ ] **Step 3: Write `src/quantbtc/fees.py`**

```python
from __future__ import annotations

import math


def fee_per_contract(price: float, rate: float = 0.07) -> float:
    """Per-contract fee: rate * price * (1 - price), Kalshi/Jupiter-style.

    Jupiter's documented samples (100 @ $0.25 -> $1.32; 100 @ $0.01 -> $0.07)
    match rate=0.07 exactly. Re-verified against live data in Task 6.
    """
    if not 0.0 <= price <= 1.0:
        raise ValueError(f"price must be in [0, 1], got {price}")
    return rate * price * (1.0 - price)


def order_fee(
    price: float,
    contracts: int,
    rate: float = 0.07,
    round_cents: bool = True,
) -> float:
    """Total fee for an order of `contracts` bought at `price`.

    Jupiter rounds the order fee UP to the nearest cent (docs), giving an
    effective 1-cent minimum on any executed order.
    """
    if contracts < 1:
        raise ValueError("contracts must be >= 1")
    raw = fee_per_contract(price, rate) * contracts
    if round_cents:
        return math.ceil(round(raw, 6) * 100.0) / 100.0
    return raw


def breakeven_win_prob(price: float, fee_per_contr: float) -> float:
    """Win probability at which EV per contract is zero.

    Buying at `price` with fee `fee_per_contr`: EV = q*(1-p) - (1-q)*p - f
    = q - p - f, so breakeven q* = p + f.
    """
    return min(1.0, price + fee_per_contr)


def expected_value(
    win_prob: float, price: float, fee_per_contr: float
) -> float:
    """Expected profit per contract (in USD, payout = 1)."""
    return win_prob - price - fee_per_contr
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_fees.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/fees.py tests/test_fees.py
git commit -m "feat: fee model matching Jupiter documented fee samples"
```

---

### Task 4: Breakeven table CLI

**Files:**
- Create: `src/quantbtc/economics.py`
- Test: `tests/test_economics.py`

- [ ] **Step 1: Write the failing test**

```python
from quantbtc.economics import breakeven_rows

def test_breakeven_rows_structure_and_math():
    rows = breakeven_rows(prices=[0.25, 0.50], rate=0.07)
    assert rows[0] == {
        "price": 0.25,
        "fee_per_contract": 0.07 * 0.25 * 0.75,
        "breakeven_win_prob": 0.25 + 0.07 * 0.25 * 0.75,
    }
    assert rows[1]["breakeven_win_prob"] > rows[0]["breakeven_win_prob"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_economics.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `src/quantbtc/economics.py`**

```python
from __future__ import annotations

from quantbtc.fees import breakeven_win_prob, fee_per_contract

DEFAULT_PRICES = [0.05 * k for k in range(1, 20)]  # 0.05 .. 0.95


def breakeven_rows(
    prices: list[float], rate: float = 0.07
) -> list[dict[str, float]]:
    return [
        {
            "price": p,
            "fee_per_contract": fee_per_contract(p, rate),
            "breakeven_win_prob": breakeven_win_prob(
                p, fee_per_contract(p, rate)
            ),
        }
        for p in prices
    ]


def render_markdown(rows: list[dict[str, float]]) -> str:
    lines = [
        "# Breakeven table (rate=0.07, per-contract fees)",
        "",
        "| Buy price | Fee/contract | Breakeven win prob |",
        "|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| ${r['price']:.2f} | ${r['fee_per_contract']:.4f} "
            f"| {r['breakeven_win_prob']:.4f} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    from pathlib import Path

    out = Path("docs/breakeven.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text(render_markdown(breakeven_rows(DEFAULT_PRICES)))
    print(f"wrote {out}")
```

- [ ] **Step 4: Run test and CLI**

Run: `.venv/bin/pytest tests/test_economics.py -q && .venv/bin/python -m quantbtc.economics`
Expected: PASS (1 passed); then `wrote docs/breakeven.md`

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/economics.py tests/test_economics.py docs/breakeven.md
git commit -m "feat: breakeven economics table CLI"
```

---

### Task 5: Jupiter client (parse layer + thin HTTP wrapper)

**Files:**
- Create: `src/quantbtc/jupiter.py`
- Test: `tests/test_jupiter.py`, `tests/fixtures/jupiter/market_sample.json`, `tests/fixtures/jupiter/orderbook_sample.json`

- [ ] **Step 1: Create fixtures** (shape per developers.jup.ag docs; Task 6 replaces with real captures)

`tests/fixtures/jupiter/market_sample.json`:
```json
{
  "marketId": "abc123",
  "eventId": "evt456",
  "title": "BTC Up or Down - 5 minute - 2026-08-23 14:00 ET",
  "status": "open",
  "result": null,
  "openTime": 1784773200,
  "closeTime": 1784773500,
  "pricing": {
    "buyYesPriceUsd": 125000,
    "buyNoPriceUsd": 90000,
    "sellYesPriceUsd": 100000,
    "sellNoPriceUsd": 850000,
    "volume": 500000000
  }
}
```

`tests/fixtures/jupiter/orderbook_sample.json`:
```json
{
  "yes": [[48, 120.5], [49, 80], [51, 200]],
  "no": [[47, 90], [48, 150]],
  "yes_dollars": [["0.4800", 120.5], ["0.4900", 80], ["0.5100", 200]],
  "no_dollars": [["0.4700", 90], ["0.4800", 150]]
}
```

- [ ] **Step 2: Write the failing test**

```python
import json
from pathlib import Path

import pytest

from quantbtc.jupiter import (
    JupiterMarket, Level, parse_market, parse_orderbook, best_bid_ask,
    extract_asset_horizon,
)

FIX = Path(__file__).parent / "fixtures" / "jupiter"


def test_price_scale_documented_one_million_equals_one_dollar():
    from quantbtc.jupiter import PRICE_SCALE
    assert PRICE_SCALE == 1_000_000


def test_parse_market_normalizes_units():
    d = json.loads((FIX / "market_sample.json").read_text())
    m = parse_market(d)
    assert isinstance(m, JupiterMarket)
    assert m.market_id == "abc123"
    assert m.open_time_ms == 1784773200000   # unix seconds -> ms
    assert m.buy_yes_usd == pytest.approx(0.125)
    assert m.buy_no_usd == pytest.approx(0.09)
    assert m.volume == pytest.approx(500.0)
    assert m.result is None
    assert m.status == "open"


def test_parse_orderbook_cents_to_usd():
    d = json.loads((FIX / "orderbook_sample.json").read_text())
    ob = parse_orderbook(d)
    assert ob["yes"][0] == Level(price=0.48, qty=120.5)
    assert ob["no"][1] == Level(price=0.48, qty=150.0)


def test_best_bid_ask_from_sorted_levels():
    levels = [Level(0.48, 10), Level(0.51, 20), Level(0.53, 5)]
    bid, ask = best_bid_ask(levels)
    assert bid == pytest.approx(0.53)   # highest buy
    assert ask == pytest.approx(0.48)   # lowest offer


def test_extract_asset_horizon():
    assert extract_asset_horizon("BTC Up or Down - 5 minute - x") == ("BTC", 300)
    assert extract_asset_horizon("SOL 15-Minute Up/Down") == ("SOL", 900)
    assert extract_asset_horizon("Who wins the election?") == (None, None)
```

Field names, price scale, and response shape come from developers.jup.ag (2026-08-23) and are re-verified against live captures in Task 6; if reality differs, fix `parse_market`/fixtures to match the captured JSON.

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_jupiter.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 4: Write `src/quantbtc/jupiter.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

PRICE_SCALE = 1_000_000  # docs: 1,000,000 = $1.00


@dataclass(frozen=True)
class JupiterMarket:
    market_id: str
    event_id: str
    title: str
    status: str          # open | closed | cancelled
    result: str | None   # null | yes | no
    open_time_ms: int
    close_time_ms: int
    buy_yes_usd: float | None
    buy_no_usd: float | None
    sell_yes_usd: float | None
    sell_no_usd: float | None
    volume: float | None


@dataclass(frozen=True)
class Level:
    price: float
    qty: float


def _usd(raw) -> float | None:
    if raw is None:
        return None
    return raw / PRICE_SCALE


def _ms(seconds) -> int:
    return int(seconds) * 1000 if seconds is not None else 0


def parse_market(d: dict) -> JupiterMarket:
    pricing = d.get("pricing") or {}
    return JupiterMarket(
        market_id=d["marketId"],
        event_id=d.get("eventId", ""),
        title=d.get("title", ""),
        status=d.get("status", ""),
        result=d.get("result"),
        open_time_ms=_ms(d.get("openTime")),
        close_time_ms=_ms(d.get("closeTime")),
        buy_yes_usd=_usd(pricing.get("buyYesPriceUsd")),
        buy_no_usd=_usd(pricing.get("buyNoPriceUsd")),
        sell_yes_usd=_usd(pricing.get("sellYesPriceUsd")),
        sell_no_usd=_usd(pricing.get("sellNoPriceUsd")),
        volume=_usd(pricing.get("volume")),
    )


def parse_orderbook(d: dict) -> dict[str, list[Level]]:
    """`yes`/`no` arrays are [price_in_cents, qty]; normalize price to USD."""
    out: dict[str, list[Level]] = {}
    for side in ("yes", "no"):
        out[side] = [
            Level(price=float(p) / 100.0, qty=float(q))
            for p, q in d.get(side, [])
        ]
    return out


def best_bid_ask(levels: list[Level]) -> tuple[float | None, float | None]:
    if not levels:
        return None, None
    prices = [lv.price for lv in levels]
    return max(prices), min(prices)


_ASSET_RE = re.compile(r"\b(BTC|ETH|SOL)\b")
_HORIZON_RE = re.compile(r"\b(5|15)\s*[- ]?\s*(min|minute)", re.IGNORECASE)


def extract_asset_horizon(title: str) -> tuple[str | None, int | None]:
    asset = _ASSET_RE.search(title)
    hz = _HORIZON_RE.search(title)
    return (
        asset.group(1) if asset else None,
        int(hz.group(1)) * 60 if hz else None,
    )


class JupiterClient:
    """Thin async wrapper over api.jup.ag/prediction/v1. No secrets in code."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=self._headers(api_key),
            timeout=10.0,
        )

    @staticmethod
    def _headers(api_key: str | None) -> dict[str, str]:
        headers = {"accept": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        return headers

    async def _get(self, path: str, params: dict | None = None):
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _unwrap(data, key: str):
        # Response envelope ({"events": [...]} vs bare list) confirmed in Task 6.
        if isinstance(data, dict) and key in data:
            return data[key]
        return data

    async def get_events(
        self, event_filter: str = "live", include_markets: bool = True
    ) -> list[dict]:
        data = await self._get(
            "/events",
            {"filter": event_filter, "includeMarkets": str(include_markets).lower()},
        )
        return self._unwrap(data, "events")

    async def get_market(self, market_id: str) -> dict:
        return await self._get(f"/markets/{market_id}")

    async def get_orderbook(self, market_id: str) -> dict:
        return await self._get(f"/orderbook/{market_id}")

    async def trading_status(self) -> dict:
        return await self._get("/trading-status")

    async def aclose(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_jupiter.py -q`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add src/quantbtc/jupiter.py tests/test_jupiter.py tests/fixtures/
git commit -m "feat: Jupiter client with unit-normalizing parsers"
```

---

### Task 6: Live recon (Phase 0 exit evidence)

**Files:**
- Create: `scripts/jupiter_recon.py`
- Create: `docs/RECON.md` (filled by running the script)
- Modify: `config/config.yaml` (pin any corrections found)

This task requires a Jupiter API key. Get it from the Jupiter developer Portal and export it: `export JUP_API_KEY=<key>`. If no key is available yet, still complete Steps 1–3 (script + dry-run against `/trading-status` which may be public) and mark the live steps blocked.

- [ ] **Step 1: Write `scripts/jupiter_recon.py`**

```python
"""One-time recon against the live Jupiter Prediction API (Phase 0).

Captures raw JSON fixtures, identifies the Up/Down crypto events, verifies
the fee formula, and prints a summary to paste into docs/RECON.md.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

FIXTURE_DIR = Path("tests/fixtures/jupiter")
BASE_URL = "https://api.jup.ag/prediction/v1"


async def main() -> None:
    headers = {"accept": "application/json"}
    if key := os.environ.get("JUP_API_KEY"):
        headers["x-api-key"] = key
    else:
        print("WARNING: JUP_API_KEY not set; some endpoints may 401.")
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(base_url=BASE_URL, headers=headers, timeout=15.0) as c:
        status = (await c.get("/trading-status")).json()
        (FIXTURE_DIR / "trading_status.json").write_text(json.dumps(status, indent=2))
        print("trading-status:", status)

        resp = await c.get("/events", params={"filter": "live", "includeMarkets": "true"})
        data = resp.json()
        events = data.get("events", data) if isinstance(data, dict) else data
        (FIXTURE_DIR / "events_live.json").write_text(json.dumps(data, indent=2))
        print(f"live events: {len(events)}")

        crypto = [
            e for e in events
            if any(k in json.dumps(e).upper() for k in ("BTC", "ETH", "SOL"))
            and any(k in json.dumps(e).upper() for k in ("UP", "DOWN", "5", "15"))
        ]
        print(f"candidate up/down crypto events: {len(crypto)}")
        for e in crypto[:5]:
            print(" -", e.get("id") or e.get("eventId"), "|", e.get("title"))
            for m in e.get("markets", [])[:4] if isinstance(e.get("markets"), list) else []:
                mid = m.get("marketId")
                if not mid:
                    continue
                ob = (await c.get(f"/orderbook/{mid}")).json()
                (FIXTURE_DIR / f"orderbook_{mid[:8]}.json").write_text(
                    json.dumps(ob, indent=2)
                )
                print(f"   market {mid}: open={m.get('openTime')} "
                      f"close={m.get('closeTime')} result={m.get('result')}")

        print("\nNEXT: paste findings into docs/RECON.md; fix fixtures/tests if")
        print("field names, price scales, or event shapes differ from assumptions.")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Run recon live**

Run: `JUP_API_KEY=$JUP_API_KEY .venv/bin/python scripts/jupiter_recon.py`
Expected: prints trading status, live event count, ≥1 candidate up/down event with orderbook fixtures written. If 401/403: API key problem — resolve via the Portal before continuing.

- [ ] **Step 3: Reconcile assumptions and record findings**

Compare captured fixtures against Task 5's assumptions:
1. If `pricing` scale or field names differ (e.g., prices already in USD decimals), update `PRICE_SCALE`/`parse_market` and the fixture-based tests to match reality; rerun tests.
2. If the up/down event shape differs (strike location, how Up/Down appear as markets), record the mapping in `docs/RECON.md` and extend `extract_asset_horizon` regexes if titles differ.
3. If any API response exposes explicit fee data (order previews, docs), verify `rate=0.07` against it and adjust `config/config.yaml` `fees.rate`.
4. Note observed rate limits (if any 429s) and set a safe `poll_interval_s`.

Write `docs/RECON.md` with sections: Endpoints used, Event/market shape, Price units verified, Fee verification, Rate limits, Open questions.

- [ ] **Step 4: Run full test suite**

Run: `.venv/bin/pytest -q`
Expected: all PASS (fixture-based tests still green after any reconciliation)

- [ ] **Step 5: Commit**

```bash
git add scripts/jupiter_recon.py docs/RECON.md tests/fixtures/jupiter/ config/config.yaml src/quantbtc/jupiter.py tests/test_jupiter.py
git commit -m "feat: live Jupiter recon; pin event shape and fee verification"
```

---

### Task 7: SQLite store

**Files:**
- Create: `src/quantbtc/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
from quantbtc.store import Store


def test_store_roundtrip(tmp_path):
    s = Store(tmp_path / "collector.db")
    s.upsert_market({
        "market_id": "m1", "event_id": "e1", "title": "BTC 5m",
        "asset": "BTC", "horizon_s": 300, "open_time_ms": 1_000,
        "close_time_ms": 130_000, "strike": None, "first_seen_ms": 500,
    })
    s.insert_quotes([
        {"ts_ms": 1_100, "market_id": "m1", "side": "yes",
         "bid": 0.48, "ask": 0.52, "bid_qty": 10.0, "ask_qty": 8.0},
        {"ts_ms": 1_100, "market_id": "m1", "side": "no",
         "bid": 0.47, "ask": 0.50, "bid_qty": 9.0, "ask_qty": 7.0},
    ])
    s.upsert_resolution("m1", "yes", resolved_ms=130_500, checked_ms=140_000)

    assert s.market("m1")["asset"] == "BTC"
    assert s.quote_count_since(0) == 2
    assert s.resolution("m1")["outcome"] == "yes"

    s.insert_quotes([{"ts_ms": 1_100, "market_id": "m1", "side": "yes",
                      "bid": 0.48, "ask": 0.52, "bid_qty": 10.0, "ask_qty": 8.0}])
    assert s.quote_count_since(0) == 2   # dedup by PK

    s.set_state("last_poll_ms", "12345")
    assert s.get_state("last_poll_ms") == "12345"
    assert s.get_state("missing") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_store.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `src/quantbtc/store.py`**

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

_DDL = """
CREATE TABLE IF NOT EXISTS markets (
    market_id TEXT PRIMARY KEY,
    event_id TEXT,
    title TEXT,
    asset TEXT,
    horizon_s INTEGER,
    open_time_ms INTEGER,
    close_time_ms INTEGER,
    strike REAL,
    first_seen_ms INTEGER
);
CREATE TABLE IF NOT EXISTS quotes (
    ts_ms INTEGER NOT NULL,
    market_id TEXT NOT NULL,
    side TEXT NOT NULL,          -- 'yes' (Up) | 'no' (Down)
    bid REAL, ask REAL, bid_qty REAL, ask_qty REAL,
    PRIMARY KEY (ts_ms, market_id, side)
);
CREATE TABLE IF NOT EXISTS resolutions (
    market_id TEXT PRIMARY KEY,
    outcome TEXT,                -- 'yes' | 'no'
    resolved_ms INTEGER,
    checked_ms INTEGER
);
CREATE TABLE IF NOT EXISTS collector_state (
    k TEXT PRIMARY KEY, v TEXT
);
CREATE INDEX IF NOT EXISTS idx_quotes_market ON quotes(market_id, ts_ms);
"""


class Store:
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_DDL)
        self.conn.commit()

    def upsert_market(self, rec: dict) -> None:
        self.conn.execute(
            """INSERT INTO markets ({cols}) VALUES ({qs})
               ON CONFLICT(market_id) DO UPDATE SET
                 title=excluded.title, strike=excluded.strike,
                 open_time_ms=excluded.open_time_ms,
                 close_time_ms=excluded.close_time_ms""".format(
                cols=",".join(rec.keys()),
                qs=",".join("?" * len(rec)),
            ),
            tuple(rec.values()),
        )
        self.conn.commit()

    def market(self, market_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM markets WHERE market_id=?", (market_id,)
        ).fetchone()
        return dict(row) if row else None

    def insert_quotes(self, rows: list[dict]) -> None:
        self.conn.executemany(
            """INSERT OR IGNORE INTO quotes
               (ts_ms, market_id, side, bid, ask, bid_qty, ask_qty)
               VALUES (:ts_ms, :market_id, :side, :bid, :ask, :bid_qty, :ask_qty)""",
            rows,
        )
        self.conn.commit()

    def quote_count_since(self, ts_ms: int) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) c FROM quotes WHERE ts_ms >= ?", (ts_ms,)
        ).fetchone()["c"]

    def upsert_resolution(
        self, market_id: str, outcome: str, resolved_ms: int, checked_ms: int
    ) -> None:
        self.conn.execute(
            """INSERT INTO resolutions (market_id, outcome, resolved_ms, checked_ms)
               VALUES (?,?,?,?)
               ON CONFLICT(market_id) DO UPDATE SET
                 outcome=excluded.outcome,
                 resolved_ms=excluded.resolved_ms,
                 checked_ms=excluded.checked_ms""",
            (market_id, outcome, resolved_ms, checked_ms),
        )
        self.conn.commit()

    def resolution(self, market_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM resolutions WHERE market_id=?", (market_id,)
        ).fetchone()
        return dict(row) if row else None

    def set_state(self, key: str, value: str) -> None:
        self.conn.execute(
            """INSERT INTO collector_state (k, v) VALUES (?,?)
               ON CONFLICT(k) DO UPDATE SET v=excluded.v""",
            (key, value),
        )
        self.conn.commit()

    def get_state(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT v FROM collector_state WHERE k=?", (key,)
        ).fetchone()
        return row["v"] if row else None

    def close(self) -> None:
        self.conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_store.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/store.py tests/test_store.py
git commit -m "feat: sqlite store for markets, quotes, resolutions, state"
```

---

### Task 8: Binance websocket collector (parsers + parquet writer)

**Files:**
- Create: `src/quantbtc/binance_ws.py`
- Test: `tests/test_binance_ws.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime, timezone

from quantbtc.binance_ws import (
    parse_agg_trade, parse_kline, parse_depth, streams_for, hour_key,
)


def test_parse_agg_trade():
    row = parse_agg_trade({
        "e": "aggTrade", "s": "BTCUSDT", "p": "50000.10",
        "q": "0.123", "T": 1784773200123, "m": False,
    })
    assert row == {"ts_ms": 1784773200123, "symbol": "BTCUSDT",
                   "price": 50000.10, "qty": 0.123, "agg_buy": True}


def test_parse_kline_keeps_taker_volume():
    row = parse_kline({
        "e": "kline", "E": 1784773200500, "s": "BTCUSDT",
        "k": {"t": 1784773200000, "o": "50000", "h": "50100", "l": "49900",
              "c": "50050", "v": "12.5", "T": 1784773259999, "q": "625000",
              "V": "7.5", "Q": "375000"},
    })
    assert row["ts_ms"] == 1784773200000
    assert row["close"] == 50050.0
    assert row["volume"] == 12.5
    assert row["taker_buy_volume"] == 7.5   # imbalance feature source


def test_parse_depth_uses_futures_ws_format():
    # Binance FUTURES partial depth stream: keys b/a, event time E.
    row = parse_depth({
        "e": "depthUpdate", "E": 1784773200100, "s": "BTCUSDT",
        "b": [["49999.5", "1.5"], ["49999.0", "2.0"]],
        "a": [["50000.5", "0.8"]],
    })
    assert row["ts_ms"] == 1784773200100
    assert row["symbol"] == "BTCUSDT"
    assert row["bid1_px"] == 49999.5 and row["bid1_qty"] == 1.5
    assert row["bid2_px"] == 49999.0
    assert row["ask1_px"] == 50000.5 and row["ask1_qty"] == 0.8
    assert row["ask2_px"] is None


def test_streams_for_all_symbols():
    streams = streams_for(("btcusdt", "solusdt"))
    assert "btcusdt@aggTrade" in streams
    assert "solusdt@depth20@100ms" in streams
    assert "solusdt@kline_1m" in streams
    assert len(streams) == 6


def test_hour_key():
    expected = datetime.fromtimestamp(
        1784773200, tz=timezone.utc
    ).strftime("%Y%m%d%H")
    assert hour_key(1784773200123) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_binance_ws.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `src/quantbtc/binance_ws.py`**

```python
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import websockets


def parse_agg_trade(d: dict) -> dict:
    return {
        "ts_ms": d["T"],
        "symbol": d["s"],
        "price": float(d["p"]),
        "qty": float(d["q"]),
        "agg_buy": not d["m"],  # m=True => buyer is maker => aggressive sell
    }


def parse_kline(d: dict) -> dict:
    k = d["k"]
    return {
        "ts_ms": k["t"],
        "symbol": d["s"],
        "open": float(k["o"]), "high": float(k["h"]),
        "low": float(k["l"]), "close": float(k["c"]),
        "volume": float(k["v"]),
        "taker_buy_volume": float(k["V"]),
        "quote_volume": float(k["q"]),
    }


def parse_depth(d: dict) -> dict:
    """Binance FUTURES partial depth payload: event time E, sides b/a."""
    def lvl(side: str, i: int) -> tuple[float | None, float | None]:
        rows = d.get(side, [])
        if len(rows) <= i:
            return None, None
        return float(rows[i][0]), float(rows[i][1])

    b1p, b1q = lvl("b", 0)
    b2p, b2q = lvl("b", 1)
    a1p, a1q = lvl("a", 0)
    a2p, a2q = lvl("a", 1)
    return {
        "ts_ms": d.get("E", int(time.time() * 1000)),
        "symbol": d.get("s", ""),
        "bid1_px": b1p, "bid1_qty": b1q, "bid2_px": b2p, "bid2_qty": b2q,
        "ask1_px": a1p, "ask1_qty": a1q, "ask2_px": a2p, "ask2_qty": a2q,
    }


def streams_for(symbols: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for s in symbols:
        out += [f"{s}@aggTrade", f"{s}@depth20@100ms", f"{s}@kline_1m"]
    return out


def hour_key(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y%m%d%H")


class HourlyParquetWriter:
    """Buffers rows and flushes one Parquet file per UTC hour per stream."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._buffers: dict[tuple[str, str, str], list[dict]] = {}

    def add(self, symbol: str, stream: str, row: dict) -> None:
        key = (symbol, stream, hour_key(row["ts_ms"]))
        self._buffers.setdefault(key, []).append(row)

    def flush(self) -> int:
        written = 0
        for (symbol, stream, hour), rows in list(self._buffers.items()):
            path = self.root / symbol / stream / f"{hour}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            new = pl.DataFrame(rows)
            if path.exists():
                new = pl.concat([pl.read_parquet(path), new])
            new.write_parquet(path)
            written += len(rows)
            del self._buffers[(symbol, stream, hour)]
        return written


class BinanceCollector:
    def __init__(self, symbols, ws_url: str, writer: HourlyParquetWriter):
        self.symbols = tuple(symbols)
        self.ws_url = ws_url
        self.writer = writer
        self._stop = asyncio.Event()

    async def run(self) -> None:
        url = f"{self.ws_url}?streams={'/'.join(streams_for(self.symbols))}"
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    backoff = 1.0
                    async for raw in ws:
                        self._handle(json.loads(raw))
                        if self._stop.is_set():
                            break
            except (websockets.ConnectionClosed, OSError):
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
        self.writer.flush()

    def _handle(self, msg: dict) -> None:
        stream: str = msg.get("stream", "")
        data: dict = msg.get("data", msg)
        if stream.endswith("@aggTrade"):
            self.writer.add(stream.split("@")[0].upper(), "aggTrade",
                            parse_agg_trade(data))
        elif stream.endswith("@kline_1m"):
            self.writer.add(stream.split("@")[0].upper(), "kline_1m",
                            parse_kline(data))
        elif "@depth" in stream:
            self.writer.add(stream.split("@")[0].upper(), "depth20",
                            parse_depth(data))

    def stop(self) -> None:
        self._stop.set()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_binance_ws.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/binance_ws.py tests/test_binance_ws.py
git commit -m "feat: Binance WS collectors with hourly parquet writer"
```

---

### Task 9: Jupiter quote poller

**Files:**
- Create: `src/quantbtc/jupiter_collector.py`
- Test: `tests/test_jupiter_collector.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio
import json
from pathlib import Path

from quantbtc.jupiter_collector import JupiterPoller
from quantbtc.store import Store

FIX = Path(__file__).parent / "fixtures" / "jupiter"


class FakeClient:
    def __init__(self, events, market_results, orderbooks):
        self._events = events
        self._markets = market_results
        self._obs = orderbooks
        self.orderbook_calls: list[str] = []

    async def get_events(self, **_):
        return self._events

    async def get_market(self, market_id):
        return self._markets[market_id]

    async def get_orderbook(self, market_id):
        self.orderbook_calls.append(market_id)
        return self._obs[market_id]


def _market(mid, title, status="open", result=None, open_s=1000, close_s=1300):
    return {
        "marketId": mid, "eventId": f"ev-{mid}", "title": title,
        "status": status, "result": result,
        "openTime": open_s, "closeTime": close_s,
        "pricing": {"buyYesPriceUsd": 120000, "buyNoPriceUsd": 880000,
                    "sellYesPriceUsd": 110000, "sellNoPriceUsd": 850000,
                    "volume": 1000000},
    }


def _poll(client, tmp_path, now_ms):
    store = Store(tmp_path / "c.db")
    poller = JupiterPoller(
        client=client, store=store,
        asset_patterns=("BTC",), result_delay_s=5.0,
    )
    asyncio.run(poller.poll_once(now_ms))
    return store


def test_poll_captures_quotes_for_open_market(tmp_path):
    m = _market("m1", "BTC Up or Down - 5 minute")
    client = FakeClient(
        events=[{"id": "ev-m1", "title": m["title"], "markets": [m]}],
        market_results={"m1": m},
        orderbooks={"m1": json.loads((FIX / "orderbook_sample.json").read_text())},
    )
    store = _poll(client, tmp_path, now_ms=1_100_000)
    assert store.market("m1")["asset"] == "BTC"
    assert store.market("m1")["horizon_s"] == 300
    assert store.quote_count_since(0) == 2       # yes + no rows
    assert client.orderbook_calls == ["m1"]


def test_poll_skips_non_matching_assets(tmp_path):
    m = _market("m2", "Who wins Super Bowl?")
    client = FakeClient(
        events=[{"id": "ev-m2", "title": m["title"], "markets": [m]}],
        market_results={"m2": m}, orderbooks={},
    )
    store = _poll(client, tmp_path, now_ms=1_100_000)
    assert store.market("m2") is None
    assert store.quote_count_since(0) == 0


def test_poll_resolves_closed_market_after_delay(tmp_path):
    closed = _market("m3", "BTC Up or Down - 15 minute",
                     status="closed", result="yes", open_s=1000, close_s=1300)
    client = FakeClient(
        events=[{"id": "ev-m3", "title": closed["title"], "markets": [closed]}],
        market_results={"m3": closed}, orderbooks={},
    )
    store = _poll(client, tmp_path, now_ms=1_400_000)  # > close+5s
    assert store.resolution("m3")["outcome"] == "yes"
    assert store.quote_count_since(0) == 0          # closed: no quotes fetched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_jupiter_collector.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `src/quantbtc/jupiter_collector.py`**

```python
from __future__ import annotations

import asyncio
import time

from quantbtc.jupiter import (
    JupiterClient, best_bid_ask, extract_asset_horizon, parse_orderbook,
)
from quantbtc.store import Store


class JupiterPoller:
    """Polls live events; records quotes for open up/down crypto markets and
    final resolutions after close. poll_once is the pure testable step."""

    def __init__(
        self,
        client: JupiterClient,
        store: Store,
        asset_patterns: tuple[str, ...] = ("BTC", "ETH", "SOL"),
        result_delay_s: float = 5.0,
        poll_interval_s: float = 2.0,
        event_filter: str = "live",
    ):
        self.client = client
        self.store = store
        self.asset_patterns = asset_patterns
        self.result_delay_ms = int(result_delay_s * 1000)
        self.poll_interval_s = poll_interval_s
        self.event_filter = event_filter

    async def poll_once(self, now_ms: int | None = None) -> None:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        events = await self.client.get_events(event_filter=self.event_filter)
        for event in events:
            markets = event.get("markets") or []
            if not markets and isinstance(event.get("marketId"), str):
                markets = [event]
            for m in markets:
                await self._process_market(m, now_ms)

    async def _process_market(self, m: dict, now_ms: int) -> None:
        title = m.get("title", "")
        asset, horizon_s = extract_asset_horizon(title)
        if asset is None or asset not in self.asset_patterns:
            return
        market_id = m.get("marketId")
        if not market_id:
            return
        open_ms = int(m.get("openTime") or 0) * 1000
        close_ms = int(m.get("closeTime") or 0) * 1000
        self.store.upsert_market({
            "market_id": market_id,
            "event_id": m.get("eventId", ""),
            "title": title,
            "asset": asset,
            "horizon_s": horizon_s,
            "open_time_ms": open_ms,
            "close_time_ms": close_ms,
            "strike": m.get("strike"),
            "first_seen_ms": now_ms,
        })

        if m.get("status") == "open" and open_ms <= now_ms < close_ms:
            ob = parse_orderbook(await self.client.get_orderbook(market_id))
            rows = []
            for side in ("yes", "no"):
                bid, ask = best_bid_ask(ob[side])
                rows.append({
                    "ts_ms": now_ms, "market_id": market_id, "side": side,
                    "bid": bid, "ask": ask,
                    "bid_qty": ob[side][-1].qty if ob[side] else None,
                    "ask_qty": ob[side][0].qty if ob[side] else None,
                })
            self.store.insert_quotes(rows)

        if (m.get("status") == "closed"
                and now_ms >= close_ms + self.result_delay_ms
                and self.store.resolution(market_id) is None):
            fresh = await self.client.get_market(market_id)
            if fresh.get("result") in ("yes", "no"):
                self.store.upsert_resolution(
                    market_id, fresh["result"],
                    resolved_ms=int(fresh.get("closeTime") or 0) * 1000,
                    checked_ms=now_ms,
                )

    async def run_forever(self) -> None:
        while True:
            try:
                await self.poll_once()
            except Exception as exc:  # keep the daemon alive on API hiccups
                print(f"[jupiter] poll error: {exc!r}")
            await asyncio.sleep(self.poll_interval_s)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_jupiter_collector.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/jupiter_collector.py tests/test_jupiter_collector.py
git commit -m "feat: Jupiter quote poller with resolution capture"
```

---

### Task 10: Daemon runner

**Files:**
- Create: `src/quantbtc/daemon.py`
- Test: `tests/test_daemon.py`

- [ ] **Step 1: Write the failing test**

```python
from quantbtc.daemon import build_runtime


class _FakePoller:
    def __init__(self):
        self.started = False

    async def run_forever(self):
        self.started = True
        import asyncio
        await asyncio.sleep(3600)


class _FakeBinCollector:
    def __init__(self):
        self.started = False

    async def run(self):
        self.started = True
        import asyncio
        await asyncio.sleep(3600)

    def stop(self):
        pass


def test_build_runtime_wires_components(tmp_path):
    poller, binance, store = build_runtime(
        config_path=None,
        sqlite_path=tmp_path / "c.db",
        parquet_dir=tmp_path / "raw",
        poller_factory=lambda store: _FakePoller(),
        binance_factory=lambda writer: _FakeBinCollector(),
    )
    assert isinstance(poller, _FakePoller)
    assert isinstance(binance, _FakeBinCollector)
    from quantbtc.store import Store
    assert isinstance(store, Store)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_daemon.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `src/quantbtc/daemon.py`**

```python
from __future__ import annotations

import asyncio
import os
import signal

from quantbtc.binance_ws import BinanceCollector, HourlyParquetWriter
from quantbtc.config import Config, load_config
from quantbtc.jupiter import JupiterClient
from quantbtc.jupiter_collector import JupiterPoller
from quantbtc.store import Store


def build_runtime(
    config_path: str | None = "config/config.yaml",
    sqlite_path=None,
    parquet_dir=None,
    poller_factory=None,
    binance_factory=None,
):
    cfg: Config = load_config(config_path) if config_path else Config()
    store = Store(sqlite_path or cfg.storage.sqlite_path)
    writer = HourlyParquetWriter(parquet_dir or cfg.storage.parquet_dir)

    if poller_factory is None:
        def poller_factory(store):
            client = JupiterClient(
                cfg.jupiter.base_url,
                api_key=os.environ.get(cfg.jupiter.api_key_env),
            )
            return JupiterPoller(
                client=client, store=store,
                asset_patterns=cfg.jupiter.asset_patterns,
                result_delay_s=cfg.jupiter.result_delay_s,
                poll_interval_s=cfg.jupiter.poll_interval_s,
                event_filter=cfg.jupiter.event_filter,
            )

    if binance_factory is None:
        def binance_factory(writer):
            return BinanceCollector(
                cfg.binance.symbols, cfg.binance.ws_url, writer
            )

    return poller_factory(store), binance_factory(writer), store


async def _run(poller, binance) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    tasks = [
        asyncio.create_task(binance.run(), name="binance"),
        asyncio.create_task(poller.run_forever(), name="jupiter"),
    ]
    await stop.wait()
    binance.stop()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def main() -> None:
    poller, binance, store = build_runtime()
    try:
        asyncio.run(_run(poller, binance))
    finally:
        store.close()
    print("collector stopped cleanly")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_daemon.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Smoke-run the daemon for 60 seconds live**

Run: `timeout 60 .venv/bin/python -m quantbtc.daemon; ls -R data/ | head -30; .venv/bin/python -c "import sqlite3; print(sqlite3.connect('data/collector.db').execute('SELECT COUNT(*) FROM quotes').fetchone())"`
Expected: process exits after 60s with "collector stopped cleanly"; `data/raw/<SYM>/{aggTrade,depth20,kline_1m}/*.parquet` files exist; quotes count > 0 (requires JUP_API_KEY and open epochs).

- [ ] **Step 6: Commit**

```bash
git add src/quantbtc/daemon.py tests/test_daemon.py
git commit -m "feat: daemon runner with graceful shutdown"
```

---

### Task 11: Binance kline backfill

**Files:**
- Create: `src/quantbtc/backfill.py`
- Test: `tests/test_backfill.py`

- [ ] **Step 1: Write the failing test**

```python
from quantbtc.backfill import missing_hours

HOUR_MS = 3600 * 1000
BOUNDARY = 1784772000000  # exactly 495770 * HOUR_MS (a true hour boundary)


def test_missing_hours_simple_range():
    have = {BOUNDARY, BOUNDARY + HOUR_MS}            # hours 0 and 1 present
    missing = missing_hours(BOUNDARY, BOUNDARY + 3 * HOUR_MS, have)
    assert missing == [BOUNDARY + 2 * HOUR_MS]


def test_missing_hours_empty_have():
    assert missing_hours(BOUNDARY, BOUNDARY + 2 * HOUR_MS, set()) == [
        BOUNDARY, BOUNDARY + HOUR_MS
    ]


def test_missing_hours_excludes_before_start():
    # floor() bucket below start must not be reported
    missing = missing_hours(BOUNDARY + 1000, BOUNDARY + 2 * HOUR_MS, set())
    assert missing == [BOUNDARY + HOUR_MS]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_backfill.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `src/quantbtc/backfill.py`**

```python
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

from quantbtc.binance_ws import hour_key, parse_kline

HOUR_MS = 3600 * 1000


def missing_hours(start_ms: int, end_ms: int, have_hours: set[int]) -> list[int]:
    h = (start_ms // HOUR_MS) * HOUR_MS
    out = []
    while h < end_ms:
        if h not in have_hours and h >= start_ms:
            out.append(h)
        h += HOUR_MS
    return out


def fetch_klines(
    client: httpx.Client, rest_url: str, symbol: str,
    start_ms: int, end_ms: int, interval: str = "1m",
) -> list[dict]:
    rows: list[dict] = []
    cursor = start_ms
    while cursor < end_ms:
        resp = client.get(
            f"{rest_url}/fapi/v1/klines",
            params={
                "symbol": symbol.upper(), "interval": interval,
                "startTime": cursor, "endTime": end_ms - 1, "limit": 1500,
            },
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for k in batch:
            rows.append({
                "ts_ms": k[0], "symbol": symbol.upper(),
                "open": float(k[1]), "high": float(k[2]),
                "low": float(k[3]), "close": float(k[4]),
                "volume": float(k[5]),
                "taker_buy_volume": float(k[9]),
                "quote_volume": float(k[7]),
            })
        cursor = batch[-1][0] + 1
        if len(batch) < 1500:
            break
    return rows


def backfill(parquet_dir: str | Path, symbol: str, hours: list[int]) -> int:
    root = Path(parquet_dir) / symbol.upper() / "kline_1m"
    written = 0
    with httpx.Client(timeout=30.0) as client:
        for h in hours:
            rows = fetch_klines(
                client, "https://fapi.binance.com", symbol, h, h + HOUR_MS
            )
            if not rows:
                continue
            path = root / f"{hour_key(h)}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            pl.DataFrame(rows).write_parquet(path)
            written += len(rows)
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--hours-ago", type=int, default=24)
    ap.add_argument("--parquet-dir", default="data/raw")
    args = ap.parse_args()

    now = int(time.time() * 1000)
    start = now - args.hours_ago * HOUR_MS
    root = Path(args.parquet_dir) / args.symbol.upper() / "kline_1m"
    have: set[int] = set()
    if root.exists():
        for f in root.glob("*.parquet"):
            have.add(int(datetime.strptime(
                f.stem, "%Y%m%d%H"
            ).replace(tzinfo=timezone.utc).timestamp() * 1000))
    hours = missing_hours(start, now, have)
    n = backfill(args.parquet_dir, args.symbol, hours)
    print(f"backfilled {n} klines across {len(hours)} hours for {args.symbol}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests + live smoke**

Run: `.venv/bin/pytest tests/test_backfill.py -q && .venv/bin/python -m quantbtc.backfill --symbol btcusdt --hours-ago 2`
Expected: PASS (3 passed); then prints `backfilled 120 klines across 2 hours for btcusdt` (approx).

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/backfill.py tests/test_backfill.py
git commit -m "feat: kline gap backfill via Binance REST"
```

---

### Task 12: Daily sanity report

**Files:**
- Create: `src/quantbtc/report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: Write the failing test**

```python
from quantbtc.report import build_report
from quantbtc.store import Store


def test_report_counts_and_gaps(tmp_path):
    store = Store(tmp_path / "c.db")
    store.upsert_market({
        "market_id": "m1", "event_id": "e", "title": "BTC 5m",
        "asset": "BTC", "horizon_s": 300, "open_time_ms": 1_000,
        "close_time_ms": 130_000, "strike": None, "first_seen_ms": 500,
    })
    store.insert_quotes([{"ts_ms": 10_000, "market_id": "m1", "side": "yes",
                          "bid": 0.5, "ask": 0.52, "bid_qty": 1.0, "ask_qty": 1.0}])
    store.upsert_resolution("m1", "yes", 130_500, 140_000)

    md = build_report(store, parquet_root=tmp_path, since_ms=0, now_ms=200_000)
    assert "| Metric | Value |" in md
    assert "| Quotes captured | 1 |" in md
    assert "| Markets seen | 1 |" in md
    assert "| Resolutions | 1 |" in md
    assert "BTC" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_report.py -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Write `src/quantbtc/report.py`**

```python
from __future__ import annotations

from pathlib import Path

from quantbtc.store import Store


def build_report(
    store: Store, parquet_root: str | Path, since_ms: int, now_ms: int
) -> str:
    c = store.conn
    quotes = c.execute(
        "SELECT COUNT(*) n FROM quotes WHERE ts_ms >= ?", (since_ms,)
    ).fetchone()["n"]
    markets = c.execute("SELECT COUNT(*) n FROM markets").fetchone()["n"]
    resolutions = c.execute(
        "SELECT COUNT(*) n FROM resolutions"
    ).fetchone()["n"]
    last_quote = c.execute("SELECT MAX(ts_ms) m FROM quotes").fetchone()["m"]
    per_asset = c.execute(
        """SELECT asset, COUNT(*) n FROM markets GROUP BY asset ORDER BY asset"""
    ).fetchall()

    lines = [
        "# Collector daily report",
        "",
        f"Window: since {since_ms} (now {now_ms})",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Quotes captured | {quotes} |",
        f"| Markets seen | {markets} |",
        f"| Resolutions | {resolutions} |",
        f"| Last quote ts | {last_quote} |",
        "",
        "## Markets per asset",
        "",
        "| Asset | Markets |",
        "|---|---|",
    ]
    for row in per_asset:
        lines.append(f"| {row['asset']} | {row['n']} |")

    lines += ["", "## Parquet files (Binance)", ""]
    root = Path(parquet_root)
    if root.exists():
        for sym_dir in sorted(root.iterdir()):
            if not sym_dir.is_dir():
                continue
            for stream_dir in sorted(sym_dir.iterdir()):
                n = len(list(stream_dir.glob("*.parquet")))
                lines.append(f"- {sym_dir.name}/{stream_dir.name}: {n} hour-files")
    else:
        lines.append("(no parquet root yet)")

    return "\n".join(lines) + "\n"


def main() -> None:
    import time

    from quantbtc.config import load_config

    cfg = load_config()
    store = Store(cfg.storage.sqlite_path)
    now = int(time.time() * 1000)
    md = build_report(
        store, cfg.storage.parquet_dir, since_ms=now - 24 * 3600 * 1000, now_ms=now
    )
    out = Path("reports")
    out.mkdir(exist_ok=True)
    path = out / f"daily-{time.strftime('%Y%m%d')}.md"
    path.write_text(md)
    store.close()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/pytest tests/test_report.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/quantbtc/report.py tests/test_report.py
git commit -m "feat: daily collector sanity report"
```

---

### Task 13: Runbook + VPS-readiness

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# quant-btc

Short-horizon (5m/15m) BTC/SOL direction research against Jupiter Up/Down.
Phase 0+1: fee foundation + always-on data collection. Spec:
`docs/superpowers/specs/2026-08-23-jupiter-direction-model-design.md`.

## Setup

    python3.11 -m venv .venv
    .venv/bin/pip install -e '.[dev]'

Get a Jupiter Prediction API key from the developer Portal, then:

    export JUP_API_KEY=...

## Run recon (once)

    .venv/bin/python scripts/jupiter_recon.py
    # findings -> docs/RECON.md

## Run the collector (always-on)

    nohup .venv/bin/python -m quantbtc.daemon >> data/collector.log 2>&1 &

Graceful stop: `kill -TERM <pid>` (flushes parquet buffers, closes sqlite).

## Backfill Binance kline gaps

    .venv/bin/python -m quantbtc.backfill --symbol btcusdt --hours-ago 24

## Daily sanity report

    .venv/bin/python -m quantbtc.report

## Tests

    .venv/bin/pytest -q

## VPS migration (later)

Everything path-driven via `config/config.yaml` (`storage.sqlite_path`,
`storage.parquet_dir`). Copy repo + data/, install, run under systemd:

    [Unit]
    Description=quantbtc collector
    [Service]
    WorkingDirectory=/opt/quantbtc
    Environment=JUP_API_KEY=<key>
    ExecStart=/opt/quantbtc/.venv/bin/python -m quantbtc.daemon
    Restart=always
    [Install]
    WantedBy=multi-user.target
```

- [ ] **Step 2: Full suite + commit**

Run: `.venv/bin/pytest -q`
Expected: all PASS

```bash
git add README.md
git commit -m "docs: runbook for collector operation and VPS migration"
```

---

## Definition of done (Phase 0+1)

1. All tests green: `.venv/bin/pytest -q`
2. `docs/RECON.md` exists with verified event shape, price units, fee rate, and rate limits; fixture-based tests match live captures.
3. Daemon survives a 24-hour run: parquet files accumulate for 3 symbols × 3 streams; `quotes` and `resolutions` tables grow; daily report renders.
4. `kill -TERM` flushes buffers (no data loss on restart).

## Follow-up plans (not this one)

- **Phase 2a:** feature builder + Φ(d₂) fair-value engine + walk-forward harness (uses Herdr dataset via config path).
- **Phase 2b:** LightGBM models + market-efficiency baseline + kill-criterion evaluation.
- **Phase 3:** paper trader (venue simulator, ¼-Kelly, ledger) + block-bootstrap significance.
