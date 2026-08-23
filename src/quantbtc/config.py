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
