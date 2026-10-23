"""Paper trader v1 — pulled forward ahead of Phase B.

At each Jupiter epoch open (first `entry_window_s` seconds), compute the
Phase-A champion's P(up) for the NEXT window from the last completed
spot 5m/15m bars, and if |p - 0.5| > theta, simulate a buy of the model's
side at the LIVE Jupiter ask (from the collector's quotes table), with the
exact Jupiter fee. Outcomes fill in when the collector records resolutions.

Phase A.5 justifies at-open entries near 0.50 (quotes hug 50/50 early);
the max_ask cap skips epochs where the open quote has already moved.
"""
from __future__ import annotations

import asyncio
import pickle
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from quantbtc.config import Config
from quantbtc.fees import order_fee
from quantbtc.twapbars import aggregate_windows

RESEARCH = Path(__file__).resolve().parents[2] / "research"
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))


@dataclass(frozen=True)
class Decision:
    action: str          # "buy_up" | "buy_down" | "skip"
    p_model: float
    reason: str = ""


def decide(p_model: float, theta: float) -> Decision:
    if p_model >= 0.5 + theta:
        return Decision("buy_up", p_model)
    if p_model <= 0.5 - theta:
        return Decision("buy_down", p_model)
    return Decision("skip", p_model, reason=f"|p-0.5|<theta({theta})")


def pnl_of(action: str, entry_price: float, contracts: int, won: bool) -> float:
    fee = order_fee(entry_price, contracts)
    gross = (
        contracts * (1.0 - entry_price) if won else -contracts * entry_price
    )
    return gross - fee


def _champion_build(df: pl.DataFrame) -> np.ndarray:
    from strategies.s023_lgbm_pos_lag23 import build_features

    return build_features(df)


def _champion_model():
    from strategies.s002_lgbm_base import new_model

    return new_model()


def load_spot_1m(
    parquet_dir: str | Path, symbol: str = "BTCUSDT"
) -> pl.DataFrame:
    """Load collected kline_1m parquet, normalizing WS-schema files
    (ts_ms/taker_buy_volume) to the canonical REST/twapbars schema."""
    root = Path(parquet_dir) / symbol / "kline_1m"
    schema = {
        "open_time": pl.Datetime("ms", "UTC"), "open": pl.Float64,
        "high": pl.Float64, "low": pl.Float64, "close": pl.Float64,
        "volume": pl.Float64, "taker_buy_base_volume": pl.Float64,
        "count": pl.Int64,
    }
    if not root.exists():
        return pl.DataFrame(schema=schema)
    frames = []
    for f in sorted(root.glob("*.parquet")):
        df = pl.read_parquet(f)
        if "ts_ms" in df.columns:  # WS collector schema
            df = df.with_columns(
                pl.col("ts_ms").cast(pl.Datetime("ms", "UTC")).alias("open_time"),
                pl.col("taker_buy_volume").alias("taker_buy_base_volume"),
                pl.lit(0, dtype=pl.Int64).alias("count"),
            )
        frames.append(df.select(list(schema.keys())))
    df = pl.concat(frames).unique(subset=["open_time"]).sort("open_time")
    return df.select(list(schema.keys()))


def train_models(bars_1m: pl.DataFrame, out_dir: str | Path) -> dict[str, float]:
    """Train 5m/15m champion models on TWAP next-window labels; persist."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = {}
    for hz in ("5m", "15m"):
        agg = aggregate_windows(bars_1m, hz)
        agg = agg.with_columns(
            pl.col("y_twap").shift(-1).alias("y_next")
        ).drop_nulls(["y_next"])
        X = _champion_build(agg)
        y = agg["y_next"].to_numpy().astype(int)
        finite = np.isfinite(X).all(axis=1)
        model = _champion_model()
        model.fit(X[finite], y[finite])
        with open(out_dir / f"paper_model_{hz}.pkl", "wb") as fh:
            pickle.dump(model, fh)
        p_train = model.predict_proba(X[finite])[:, 1]
        acc = float(((p_train >= 0.5).astype(int) == y[finite]).mean())
        info[hz] = acc
    return info


class PaperLedger:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_ms INTEGER, market_id TEXT UNIQUE, event_id TEXT,
                asset TEXT, horizon_s INTEGER,
                action TEXT, p_model REAL, entry_price REAL,
                contracts INTEGER, fee REAL, notes TEXT,
                outcome TEXT, pnl REAL, settled_ms INTEGER
            );
            """
        )
        self.conn.commit()

    def has_trade(self, market_id: str) -> bool:
        return (
            self.conn.execute(
                "SELECT 1 FROM paper_trades WHERE market_id=?", (market_id,)
            ).fetchone()
            is not None
        )

    def record(self, rec: dict, now_ms: int) -> None:
        self.conn.execute(
            """INSERT OR IGNORE INTO paper_trades
               (ts_ms, market_id, event_id, asset, horizon_s, action,
                p_model, entry_price, contracts, fee, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                now_ms, rec["market_id"], rec["event_id"], rec["asset"],
                rec["horizon_s"], rec["action"], rec["p_model"],
                rec["entry_price"], rec["contracts"], rec["fee"],
                rec["notes"],
            ),
        )
        self.conn.commit()

    def open_trades(self) -> list[dict]:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM paper_trades WHERE action LIKE 'buy%' "
                "AND outcome IS NULL"
            ).fetchall()
        ]

    def settle(self, trade_id: int, won: bool, pnl: float) -> None:
        self.conn.execute(
            "UPDATE paper_trades SET outcome=?, pnl=?, settled_ms=? WHERE id=?",
            ("won" if won else "lost", pnl, int(time.time() * 1000), trade_id),
        )
        self.conn.commit()

    def summary(self) -> str:
        rows = self.conn.execute(
            """SELECT action, COUNT(*) n,
                      SUM(CASE WHEN outcome='won' THEN 1 ELSE 0 END) w,
                      SUM(CASE WHEN outcome IS NOT NULL THEN 1 ELSE 0 END) s,
                      SUM(pnl) pnl
               FROM paper_trades GROUP BY action"""
        ).fetchall()
        return "\n".join(
            f"{r['action']}: {r['n']} trades, {r['w'] or 0}/{r['s'] or 0} "
            f"settled won, pnl {r['pnl'] or 0.0:+.2f}"
            for r in rows
        )


class PaperTrader:
    def __init__(self, cfg: Config, collector_db: str | Path, paper_db: str | Path):
        self.cfg = cfg
        self.ledger = PaperLedger(paper_db)
        self.collector = collector_db
        self.models: dict[str, object] = {}

    def load_models(self, model_dir: str | Path) -> None:
        for hz in ("5m", "15m"):
            with open(Path(model_dir) / f"paper_model_{hz}.pkl", "rb") as fh:
                self.models[hz] = pickle.load(fh)

    def _collector(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.collector)
        conn.row_factory = sqlite3.Row
        return conn

    def p_model(self, hz: str, bars_1m: pl.DataFrame, now_ms: int) -> float | None:
        """Champion P(next window is Up) from completed windows only."""
        m = 5 if hz == "5m" else 15
        win_ms = m * 60_000
        cur_win_start_ms = (now_ms // win_ms) * win_ms
        done = bars_1m.filter(
            pl.col("open_time").dt.epoch("ms") < cur_win_start_ms
        )
        agg = aggregate_windows(done, hz)
        if agg.height < 12:
            return None
        X = _champion_build(agg)  # features need the full frame for shifts
        if not np.isfinite(X[-1]).all():
            return None
        proba = self.models[hz].predict_proba(X[-1:])
        return float(proba[0, list(self.models[hz].classes_).index(1)])

    def step(self, now_ms: int | None = None) -> None:
        now_ms = now_ms or int(time.time() * 1000)
        assets = set(self.cfg.paper.assets)
        entry_window_ms = int(self.cfg.paper.entry_window_s * 1000)
        with self._collector() as conn:
            rows = conn.execute(
                """SELECT market_id, event_id, asset, horizon_s,
                          open_time_ms, close_time_ms
                   FROM markets WHERE asset IS NOT NULL"""
            ).fetchall()
            for r in rows:
                rec = dict(r)
                if rec["asset"] not in assets:
                    continue
                if not rec["market_id"].endswith("-0"):
                    continue  # decide once per epoch, on the Up market id
                since_open = now_ms - rec["open_time_ms"]
                if not (0 <= since_open <= entry_window_ms):
                    continue
                if self.ledger.has_trade(rec["market_id"]):
                    continue

                def record_skip(reason: str, p=None, price=None) -> None:
                    self.ledger.record(
                        rec | {
                            "action": "skip", "p_model": p,
                            "entry_price": price, "contracts": 0,
                            "fee": 0.0, "notes": reason,
                        },
                        now_ms,
                    )

                quote = conn.execute(
                    """SELECT ts_ms, side, bid, ask FROM quotes
                       WHERE market_id=? ORDER BY ts_ms DESC LIMIT 2""",
                    (rec["market_id"],),
                ).fetchall()
                quotes = {q["side"]: q for q in quote}
                if "up" not in quotes or now_ms - quotes["up"]["ts_ms"] > 30_000:
                    continue  # transient: retry next step within the window

                bars = load_spot_1m(self.cfg.storage.parquet_dir, f"{rec['asset']}USDT")
                p = self.p_model(
                    "5m" if rec["horizon_s"] == 300 else "15m", bars, now_ms
                )
                if p is None:
                    continue  # transient: retry next step within the window
                d = decide(p, self.cfg.paper.theta)
                if d.action == "skip":
                    record_skip(d.reason, p=p)
                    continue
                side = "up" if d.action == "buy_up" else "down"
                ask = quotes[side]["ask"] if side in quotes else None
                if ask is None or ask > self.cfg.paper.max_ask:
                    record_skip(f"ask>{self.cfg.paper.max_ask}", p=p, price=ask)
                    continue
                n = self.cfg.paper.contracts
                self.ledger.record(
                    rec | {
                        "action": d.action, "p_model": p,
                        "entry_price": ask, "contracts": n,
                        "fee": order_fee(ask, n), "notes": "",
                    },
                    now_ms,
                )

    def settle(self) -> int:
        settled = 0
        with self._collector() as conn:
            for t in self.ledger.open_trades():
                res = conn.execute(
                    "SELECT outcome FROM resolutions WHERE market_id=?",
                    (t["market_id"],),
                ).fetchone()
                if not res:
                    continue
                won = (
                    res["outcome"] == "up" and t["action"] == "buy_up"
                ) or (res["outcome"] == "down" and t["action"] == "buy_down")
                self.ledger.settle(t["id"], won, pnl_of(
                    t["action"], t["entry_price"], t["contracts"], won
                ))
                settled += 1
        return settled

    async def run_forever(self) -> None:
        n = 0
        while True:
            try:
                self.step()
                self.settle()
                n += 1
                if n % 12 == 1:  # ~once a minute: ops heartbeat
                    print(f"[paper] alive: {n} steps", flush=True)
            except Exception as exc:
                print(f"[paper] error: {exc!r}", flush=True)
            await asyncio.sleep(5)
