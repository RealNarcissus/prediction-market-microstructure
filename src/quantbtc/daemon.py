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
                client=client,
                store=store,
                assets=cfg.jupiter.asset_patterns,
                result_delay_s=cfg.jupiter.result_delay_s,
                poll_interval_s=cfg.jupiter.poll_interval_s,
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
