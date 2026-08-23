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
    side TEXT NOT NULL,
    bid REAL, ask REAL, bid_qty REAL, ask_qty REAL,
    PRIMARY KEY (ts_ms, market_id, side)
);
CREATE TABLE IF NOT EXISTS resolutions (
    market_id TEXT PRIMARY KEY,
    outcome TEXT,
    resolved_ms INTEGER,
    checked_ms INTEGER
);
CREATE TABLE IF NOT EXISTS collector_state (
    k TEXT PRIMARY KEY, v TEXT
);
CREATE INDEX IF NOT EXISTS idx_quotes_market ON quotes(market_id, ts_ms);
"""

_MARKET_COLS = (
    "market_id, event_id, title, asset, horizon_s, "
    "open_time_ms, close_time_ms, strike, first_seen_ms"
)


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
            f"INSERT INTO markets ({_MARKET_COLS}) VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(market_id) DO UPDATE SET "
            "title=excluded.title, strike=excluded.strike, "
            "open_time_ms=excluded.open_time_ms, "
            "close_time_ms=excluded.close_time_ms",
            (
                rec["market_id"], rec.get("event_id"), rec.get("title"),
                rec.get("asset"), rec.get("horizon_s"),
                rec.get("open_time_ms"), rec.get("close_time_ms"),
                rec.get("strike"), rec.get("first_seen_ms"),
            ),
        )
        self.conn.commit()

    def market(self, market_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM markets WHERE market_id=?", (market_id,)
        ).fetchone()
        return dict(row) if row else None

    def insert_quotes(self, rows: list[dict]) -> None:
        self.conn.executemany(
            "INSERT OR IGNORE INTO quotes "
            "(ts_ms, market_id, side, bid, ask, bid_qty, ask_qty) "
            "VALUES (:ts_ms, :market_id, :side, :bid, :ask, :bid_qty, :ask_qty)",
            rows,
        )
        self.conn.commit()

    def quote_count_since(self, ts_ms: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) c FROM quotes WHERE ts_ms >= ?", (ts_ms,)
        ).fetchone()
        return row["c"]

    def upsert_resolution(
        self, market_id: str, outcome: str, resolved_ms: int, checked_ms: int
    ) -> None:
        self.conn.execute(
            "INSERT INTO resolutions (market_id, outcome, resolved_ms, checked_ms) "
            "VALUES (?,?,?,?) ON CONFLICT(market_id) DO UPDATE SET "
            "outcome=excluded.outcome, resolved_ms=excluded.resolved_ms, "
            "checked_ms=excluded.checked_ms",
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
            "INSERT INTO collector_state (k, v) VALUES (?,?) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
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
