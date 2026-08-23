from __future__ import annotations

from dataclasses import dataclass
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
    poll_interval_s: float = 10.0
    result_delay_s: float = 5.0
    discovery_interval_s: float = 120.0
    orderbook_budget: int = 5
    discovery_pages: int = 2
    asset_patterns: tuple[str, ...] = ("BTC", "ETH", "SOL")


@dataclass(frozen=True)
class BinanceConfig:
    symbols: tuple[str, ...] = ("btcusdt", "ethusdt", "solusdt")
    # Spot streams: futures WS (fstream) is blocked in some environments;
    # spot works and tracks the Chainlink oracle's aggregate spot feeds.
    ws_url: str = "wss://stream.binance.com:9443/stream"
    rest_url: str = "https://api.binance.com"


@dataclass(frozen=True)
class StorageConfig:
    sqlite_path: str = "data/collector.db"
    parquet_dir: str = "data/raw"


@dataclass(frozen=True)
class ResearchConfig:
    data_5m: str = (
        "/home/charleton/Desktop/agentProjects/Herdr/quant-btc/"
        "data/processed/btcusdt-usdtm-5m.parquet"
    )
    data_15m: str = (
        "/home/charleton/Desktop/agentProjects/Herdr/quant-btc/"
        "data/processed/btcusdt-usdtm-15m.parquet"
    )


@dataclass(frozen=True)
class PaperConfig:
    assets: tuple[str, ...] = ("BTC",)
    entry_window_s: float = 90.0
    theta: float = 0.05
    contracts: int = 10
    max_ask: float = 0.55
    train_days: int = 90


@dataclass(frozen=True)
class Config:
    fees: FeesConfig = FeesConfig()
    jupiter: JupiterConfig = JupiterConfig()
    binance: BinanceConfig = BinanceConfig()
    storage: StorageConfig = StorageConfig()
    research: ResearchConfig = ResearchConfig()
    paper: PaperConfig = PaperConfig()


def _as_tuple(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"config {key} must be a list, got {type(value).__name__}")
    return tuple(value)


def load_config(path: str | Path = "config/config.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    fees = FeesConfig(**(raw.get("fees") or {}))
    jup_raw = dict(raw.get("jupiter") or {})
    if "asset_patterns" in jup_raw:
        jup_raw["asset_patterns"] = _as_tuple(jup_raw["asset_patterns"], "jupiter.asset_patterns")
    jup = JupiterConfig(**jup_raw)
    bnc_raw = dict(raw.get("binance") or {})
    if "symbols" in bnc_raw:
        bnc_raw["symbols"] = _as_tuple(bnc_raw["symbols"], "binance.symbols")
    bnc = BinanceConfig(**bnc_raw)
    storage = StorageConfig(**(raw.get("storage") or {}))
    research = ResearchConfig(**(raw.get("research") or {}))
    paper_raw = dict(raw.get("paper") or {})
    if "assets" in paper_raw:
        paper_raw["assets"] = _as_tuple(paper_raw["assets"], "paper.assets")
    paper = PaperConfig(**paper_raw)
    return Config(
        fees=fees, jupiter=jup, binance=bnc, storage=storage,
        research=research, paper=paper,
    )
