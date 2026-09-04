"""Trial ledger: every experiment logged for knowledge aggregation and for
deflated final statistics (the verdict must account for ALL trials run)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from locked.harness import EvalResult

DB_PATH = Path(__file__).resolve().parent / "results.db"

_DDL = """
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    strategy TEXT NOT NULL,
    description TEXT,
    mcc_5m REAL, mcc_15m REAL, primary_metric REAL,
    ba_5m REAL, ba_15m REAL,
    ll_5m REAL, ll_15m REAL,
    tail_5m REAL, tail_15m REAL,
    n_val_5m INTEGER, n_val_15m INTEGER, n_tail_5m INTEGER, n_tail_15m INTEGER,
    kept INTEGER NOT NULL,          -- 1 = became champion, 0 = reset
    invalid INTEGER NOT NULL DEFAULT 0,  -- 1 = invalidated post-hoc (leakage etc.)
    is_champion INTEGER NOT NULL DEFAULT 0,
    git_commit TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    strategy TEXT NOT NULL,
    holdout_mcc_5m REAL, holdout_mcc_15m REAL,
    trials_count INTEGER,
    notes TEXT
);
"""


class Ledger:
    def __init__(self, path: Path = DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_DDL)
        self.conn.commit()

    def champion(self) -> sqlite3.Row | None:
        row = self.conn.execute(
            "SELECT * FROM experiments WHERE is_champion=1 "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row

    def record(
        self, result: EvalResult, description: str, kept: bool, notes: str = ""
    ) -> int:
        cur = self.conn.cursor()
        if kept:
            cur.execute("UPDATE experiments SET is_champion=0 WHERE is_champion=1")
        ts = datetime.now(timezone.utc).isoformat()
        cur.execute(
            """INSERT INTO experiments (ts, strategy, description,
                 mcc_5m, mcc_15m, primary_metric, ba_5m, ba_15m,
                 ll_5m, ll_15m, tail_5m, tail_15m,
                 n_val_5m, n_val_15m, n_tail_5m, n_tail_15m,
                 kept, is_champion, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                ts, result.strategy, description,
                result.res_5m.mcc, result.res_15m.mcc, result.primary,
                result.res_5m.balanced_accuracy, result.res_15m.balanced_accuracy,
                result.res_5m.log_loss, result.res_15m.log_loss,
                result.res_5m.tail_calibration_error,
                result.res_15m.tail_calibration_error,
                result.res_5m.n_val, result.res_15m.n_val,
                result.res_5m.n_tail, result.res_15m.n_tail,
                int(kept), int(kept), notes,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def set_git_commit(self, exp_id: int, commit: str) -> None:
        self.conn.execute(
            "UPDATE experiments SET git_commit=? WHERE id=?", (commit, exp_id)
        )
        self.conn.commit()

    def trials_count(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) c FROM experiments"
        ).fetchone()["c"]

    def record_verdict(
        self, strategy: str, mcc_5m: float, mcc_15m: float, notes: str
    ) -> None:
        self.conn.execute(
            "INSERT INTO verdicts (ts, strategy, holdout_mcc_5m, "
            "holdout_mcc_15m, trials_count, notes) VALUES (?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(), strategy,
                mcc_5m, mcc_15m, self.trials_count(), notes,
            ),
        )
        self.conn.commit()
