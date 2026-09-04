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
    resolutions = c.execute("SELECT COUNT(*) n FROM resolutions").fetchone()["n"]
    last_quote = c.execute("SELECT MAX(ts_ms) m FROM quotes").fetchone()["m"]
    per_asset = c.execute(
        "SELECT asset, COUNT(*) n FROM markets GROUP BY asset ORDER BY asset"
    ).fetchall()
    lag_s = (
        round((now_ms - last_quote) / 1000, 1) if last_quote else None
    )

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
        f"| Last quote age (s) | {lag_s} |",
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
                lines.append(
                    f"- {sym_dir.name}/{stream_dir.name}: {n} hour-files"
                )
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
        store,
        cfg.storage.parquet_dir,
        since_ms=now - 24 * 3600 * 1000,
        now_ms=now,
    )
    out = Path("reports")
    out.mkdir(exist_ok=True)
    path = out / f"daily-{time.strftime('%Y%m%d')}.md"
    path.write_text(md)
    store.close()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
