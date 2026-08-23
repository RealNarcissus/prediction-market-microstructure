import asyncio
import os
import signal
from pathlib import Path

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
    paper_factory=None,
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
                discovery_interval_s=cfg.jupiter.discovery_interval_s,
                orderbook_budget=cfg.jupiter.orderbook_budget,
                discovery_pages=cfg.jupiter.discovery_pages,
            )

    if binance_factory is None:

        def binance_factory(writer):
            return BinanceCollector(
                cfg.binance.symbols, cfg.binance.ws_url, writer
            )

    if paper_factory is None:

        def paper_factory():
            from quantbtc.paper import PaperTrader

            trader = PaperTrader(
                cfg, cfg.storage.sqlite_path, "data/paper.db"
            )
            model_dir = Path("data")
            if (model_dir / "paper_model_5m.pkl").exists():
                trader.load_models(model_dir)
                return trader
            return None  # models not trained yet: run without paper trader

    paper = paper_factory()
    return poller_factory(store), binance_factory(writer), store, paper


async def _run(poller, binance, paper=None) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    tasks = [
        asyncio.create_task(binance.run(), name="binance"),
        asyncio.create_task(poller.run_forever(), name="jupiter"),
    ]
    if paper is not None:
        tasks.append(asyncio.create_task(paper.run_forever(), name="paper"))
    await stop.wait()
    binance.stop()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def main() -> None:
    poller, binance, store, paper = build_runtime()
    print(
        f"[daemon] jupiter=poller binance=collector "
        f"paper={'armed' if paper is not None else 'OFF (no models found)'}",
        flush=True,
    )
    try:
        asyncio.run(_run(poller, binance, paper))
    finally:
        store.close()
    print("collector stopped cleanly")


if __name__ == "__main__":
    main()
