from quantbtc.daemon import build_runtime


class _FakePoller:
    def __init__(self):
        self.started = False

    async def run_forever(self):
        self.started = True

    def stop(self):
        pass


class _FakeBinCollector:
    def __init__(self):
        self.started = False

    async def run(self):
        self.started = True

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
    store.close()


def test_build_runtime_defaults_use_config_paths(tmp_path):
    poller, binance, store = build_runtime(
        config_path=None,
        sqlite_path=tmp_path / "d.db",
        parquet_dir=tmp_path / "praw",
    )
    from quantbtc.binance_ws import BinanceCollector
    from quantbtc.jupiter_collector import JupiterPoller

    assert isinstance(poller, JupiterPoller)
    assert isinstance(binance, BinanceCollector)
    assert poller.assets == ("BTC", "ETH", "SOL")  # Config() defaults
    store.close()
