import pytest

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


def test_scalar_symbols_raises(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
binance:
  symbols: btcusdt
""")
    with pytest.raises(ValueError, match=r"config binance\.symbols must be a list, got str"):
        load_config(cfg_file)


def test_null_section_uses_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("""
fees:
storage:
""")
    cfg = load_config(cfg_file)
    assert cfg.fees.rate == 0.07
    assert cfg.fees.round_cents is True
    assert cfg.storage.sqlite_path == "data/collector.db"
