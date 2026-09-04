"""Live paper wallet — the controlled $5 test, run forward.

PRE-REGISTERED RULES (frozen 2026-09-02, mirror research/staleness/wallet_sim.py v3):
  Envelope : $5.00 allowance, reset at each UTC midnight (day = independent trial).
  Entry    : YES-side quote of an Up/Down market; gate
             gap_cal = fair_cal - ask > 0.07*ask*(1-ask)  [same as CALIBRATED_RETEST]
             1 contract per trade; cost = ask + ceil-cent order fee.
  Capacity : ONE concurrent position; ONE entry per epoch (asset, open_ms, hz)
             — never both sides; skip signals while a position is open.
  Sizing   : exactly 1 contract (weights all price regions equally; max-contracts
             sizing was shown to concentrate capital in the failing deep tail).
  Exit     : hold to settlement against OFFICIAL resolutions from the collector;
             positions unresolved 2h past close are marked unresolved (no PnL).
  Fair     : CLT Asian digital on Binance 1m klines (strike = epoch-open 1m open,
             running TWAP mean, sigma = r24 * sqrt(pi/2)) — mirrors audit.py.
  Calibration: isotonic fair->P(win) fit ONCE on scored quotes before
             LIVE_START (2026-09-02 00:00 UTC), frozen in calibration.npz.
             Refits ONLY at declared weekly checkpoints (--build-calibration),
             never intra-run.
  Freshness: only quotes with ts within 30s of processing time are tradable
             (no backfill-trading stale signals after downtime).
  Ledger   : data/paper_wallet.db (SQLite, append-only trades), report:
             research/staleness/WALLET_LIVE.md.

DECISION GATE (pre-registered): live per-contract EV with day-block CI after
>= 2 weeks, all-weeks-positive discipline, before any capital discussion.
"""
from __future__ import annotations

import argparse
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from quantbtc.fees import order_fee

COLLECTOR_DB = REPO / "data" / "collector.db"
LEDGER_DB = REPO / "data" / "paper_wallet.db"
RAW = REPO / "data" / "raw"
CALIBRATION = REPO / "research" / "staleness" / "calibration.npz"
REPORT = REPO / "research" / "staleness" / "WALLET_LIVE.md"

LIVE_START_MS = int(np.datetime64("2026-09-02T00:00:00").astype("datetime64[ms]").astype(int))
ALLOWANCE_CENTS = 500
FEE_RATE = 0.07
POLL_S = 10.0
FRESHNESS_S = 30
UNRESOLVED_TIMEOUT_S = 2 * 3600
SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}

_DDL = """
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_ts_ms INTEGER NOT NULL,
  market_id TEXT NOT NULL,
  asset TEXT NOT NULL,
  hz_s INTEGER NOT NULL,
  open_ms INTEGER NOT NULL,
  close_ms INTEGER NOT NULL,
  is_up_market INTEGER NOT NULL,
  ask REAL NOT NULL,
  fair_cal REAL NOT NULL,
  gap_cal REAL NOT NULL,
  cost_cents INTEGER NOT NULL,
  entry_day TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  won INTEGER,
  pnl_cents INTEGER,
  settled_ts_ms INTEGER,
  UNIQUE(market_id, entry_ts_ms)
);
CREATE TABLE IF NOT EXISTS wallet_meta (k TEXT PRIMARY KEY, v TEXT);
"""


# ---------------- calibration ----------------

def build_calibration() -> None:
    """Fit isotonic on ALL scored quotes before LIVE_START; freeze to npz."""
    import polars as pl
    from sklearn.isotonic import IsotonicRegression

    src = REPO / "research" / "staleness" / "scored_quotes.parquet"
    df = pl.read_parquet(str(src)).filter(pl.col("ts_ms") < LIVE_START_MS)
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    iso.fit(df["fair"].to_numpy(), df["won"].to_numpy())
    np.savez(str(CALIBRATION), x=iso.X_thresholds_, y=iso.y_thresholds_,
             n_fit=len(df), live_start_ms=LIVE_START_MS)
    print(f"calibration frozen: {len(df)} quotes < {datetime.fromtimestamp(LIVE_START_MS/1000, tz=timezone.utc).isoformat()}")


def load_calibration():
    if not CALIBRATION.exists():
        print(f"FATAL: {CALIBRATION} missing — run with --build-calibration first", file=sys.stderr)
        sys.exit(2)
    z = np.load(str(CALIBRATION))
    x, y = z["x"], z["y"]

    def predict(fair):
        return float(np.interp(fair, x, y))  # interp clips to endpoints

    return predict


# ---------------- fair value (mirrors audit.py) ----------------

class KlineCache:
    """Rolling kline window per symbol. Re-reads the last few hour-files each
    refresh (throttled): the in-progress hour file keeps growing, so
    load-once-by-name would freeze the live tail.
    """

    WINDOW_MS = 3 * 3600 * 1000
    RELOAD_S = 30.0

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._last_load: dict[str, float] = {}

    def refresh(self, symbol: str, now_ms: int | None = None) -> None:
        now = time.time()
        if symbol in self._data and now - self._last_load.get(symbol, 0) < self.RELOAD_S:
            return
        self._last_load[symbol] = now
        import polars as pl

        d = RAW / symbol / "kline_1m"
        files = sorted(d.glob("*.parquet"))[-4:] if d.exists() else []
        if not files:
            return
        try:
            df = pl.concat([pl.read_parquet(str(f)).select(["ts_ms", "open", "close"]) for f in files])
        except Exception:
            return
        df = df.sort("ts_ms").unique(subset=["ts_ms"], keep="last", maintain_order=True)
        ts = df["ts_ms"].to_numpy().astype(np.int64)
        cutoff = (now_ms if now_ms is not None else int(now * 1000)) - self.WINDOW_MS
        m = ts >= cutoff
        ts = ts[m]
        opn = df["open"].to_numpy().astype(float)[m]
        close = df["close"].to_numpy().astype(float)[m]
        if len(ts) < 30:
            self._data[symbol] = {"ts": ts, "open": opn, "close": close, "r24": np.full(len(ts), np.nan)}
            return
        absr = np.full(len(ts), np.nan)
        absr[1:] = np.abs(np.log(close[1:] / close[:-1]))
        r24 = np.full(len(ts), np.nan)
        csum = np.nan_to_num(absr)
        nn = np.cumsum(np.isfinite(absr).astype(float))
        for i in range(len(ts)):
            lo = max(0, i - 24)
            n = nn[i] - nn[lo]
            if n >= 12:
                r24[i] = (csum[i] - csum[lo]) / max(n, 1)
        self._data[symbol] = {"ts": ts, "open": opn, "close": close, "r24": r24}

    def get(self, symbol: str) -> dict | None:
        d = self._data.get(symbol)
        if d is None or len(d.get("ts", [])) < 30:
            return None
        return d


def fair_yes(cache_data: dict, open_ms: int, hz_s: int, ts_ms: int, is_up_market: bool) -> float | None:
    """CLT Asian digital P(Up wins) for the epoch, as of ts_ms. None if unscoreable."""
    ts, opn, close, r24 = cache_data["ts"], cache_data["open"], cache_data["close"], cache_data["r24"]
    N = hz_s // 60
    i_open = int(np.searchsorted(ts, open_ms))
    if i_open >= len(ts) or int(ts[i_open]) != open_ms:
        j = int(np.searchsorted(ts, open_ms - 60_000))
        if j >= len(ts) or abs(int(ts[j]) - open_ms) > 60_000:
            return None
        i_open = j
    i_now = int(np.searchsorted(ts, ts_ms, side="right")) - 1
    if i_now < i_open:
        return None
    count_obs = i_now - i_open + 1
    n_fut = N - count_obs
    if n_fut < 0:
        return None
    K = float(opn[i_open])
    sum_obs = float(np.sum(close[i_open : i_now + 1]))
    last_close = float(close[i_now])
    e_twap = (sum_obs + last_close * n_fut) / N
    sig = r24[i_now] * math.sqrt(math.pi / 2.0) if np.isfinite(r24[i_now]) else np.nan
    if not np.isfinite(sig) or sig <= 0:
        return None
    if n_fut > 0:
        var_fut = (sig ** 2) * ((n_fut + 1) * (2 * n_fut + 1)) / (6.0 * n_fut)
        var_twap = (n_fut / N) ** 2 * var_fut
    else:
        var_twap = 1e-12
    sd = math.sqrt(max(var_twap, 1e-12))
    z = (e_twap - K) / sd
    fair_up = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    fair_up = min(max(fair_up, 0.005), 0.995)
    return fair_up if is_up_market else 1.0 - fair_up


# ---------------- wallet engine (pure) ----------------

class WalletEngine:
    """Pure state machine; events in, trades/settlements out. Cents-int math."""

    def __init__(self, calib_predict, allowance_cents: int = ALLOWANCE_CENTS,
                 now_ms: int | None = None):
        self.calib = calib_predict
        self.allowance_cents = allowance_cents
        self.day: str | None = None
        self.day_wallet_cents = allowance_cents
        self.position: dict | None = None
        self.seen_epochs: set[tuple] = set()
        self.now_ms = now_ms

    def _now(self) -> int:
        return self.now_ms if self.now_ms is not None else int(time.time() * 1000)

    def _day_of(self, ts_ms: int) -> str:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    def on_quote(self, market: dict, quote: dict, fair: float | None) -> dict:
        """Decide on one yes-side quote. Returns action dict:
        {action: skip|trade, reason, trade?}
        """
        ts = int(quote["ts_ms"])
        day = self._day_of(ts)
        if day != self.day:
            self.day = day
            self.day_wallet_cents = self.allowance_cents
            # position carries over (settles on its own clock)
        if self.position is not None and ts >= self.position["close_ms"]:
            # settlement is booked by on_resolution; block until then
            pass
        if self.position is not None:
            return {"action": "skip", "reason": "busy"}
        ask = float(quote["ask"])
        if not (0.01 < ask < 0.99) or quote["bid"] is None or ask <= quote["bid"]:
            return {"action": "skip", "reason": "bad_quote"}
        if fair is None:
            return {"action": "skip", "reason": "no_fair"}
        fee_unrounded = FEE_RATE * ask * (1 - ask)
        gap = fair - ask
        if gap <= fee_unrounded:
            return {"action": "skip", "reason": "no_gate"}
        fair_cal = self.calib(fair)
        gap_cal = fair_cal - ask
        if gap_cal <= fee_unrounded:
            return {"action": "skip", "reason": "no_gate_cal"}
        epoch_key = (market["asset"], int(market["open_time_ms"]), int(market["horizon_s"]))
        if epoch_key in self.seen_epochs:
            return {"action": "skip", "reason": "dup_epoch"}
        fee_c = int(math.ceil(round(order_fee(ask, 1, rate=FEE_RATE), 6) * 100))
        cost_c = int(round(ask * 100)) + fee_c
        if self.day_wallet_cents < cost_c:
            return {"action": "skip", "reason": "day_budget"}
        self.seen_epochs.add(epoch_key)
        self.day_wallet_cents -= cost_c
        trade = {
            "entry_ts_ms": ts, "market_id": quote["market_id"],
            "asset": market["asset"], "hz_s": int(market["horizon_s"]),
            "open_ms": int(market["open_time_ms"]), "close_ms": int(market["close_time_ms"]),
            "is_up_market": int(market["is_up_market"]),
            "ask": ask, "fair_cal": fair_cal, "gap_cal": gap_cal,
            "cost_cents": cost_c, "entry_day": day,
        }
        self.position = trade
        return {"action": "trade", "trade": trade}

    def on_resolution(self, market_id: str, outcome: str, resolved_ts_ms: int | None) -> dict | None:
        """Settle the open position if it matches. Returns settlement dict or None.

        Accounting: cost left the day wallet at entry; payout (100c if won,
        else 0) returns at settlement. Net trade PnL = payout - cost.
        """
        if self.position is None or self.position["market_id"] != market_id:
            return None
        p = self.position
        won = (bool(p["is_up_market"]) == (outcome == "up"))
        payout_c = 100 if won else 0
        pnl_c = payout_c - p["cost_cents"]
        self.day_wallet_cents += payout_c
        self.position = None
        return {"market_id": market_id, "won": int(won), "pnl_cents": pnl_c,
                "settled_ts_ms": resolved_ts_ms or self._now()}


# ---------------- ledger ----------------

def open_ledger() -> sqlite3.Connection:
    conn = sqlite3.connect(str(LEDGER_DB))
    conn.row_factory = sqlite3.Row
    conn.executescript(_DDL)
    conn.commit()
    return conn


def record_trade(conn: sqlite3.Connection, t: dict) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO trades
           (entry_ts_ms, market_id, asset, hz_s, open_ms, close_ms, is_up_market,
            ask, fair_cal, gap_cal, cost_cents, entry_day, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'open')""",
        (t["entry_ts_ms"], t["market_id"], t["asset"], t["hz_s"], t["open_ms"],
         t["close_ms"], t["is_up_market"], t["ask"], t["fair_cal"], t["gap_cal"],
         t["cost_cents"], t["entry_day"]),
    )
    conn.commit()


def book_settlement(conn: sqlite3.Connection, market_id: str, won: int, pnl_c: int, settled_ts_ms: int) -> None:
    conn.execute(
        """UPDATE trades SET status='settled', won=?, pnl_cents=?, settled_ts_ms=?
           WHERE market_id=? AND status='open'""",
        (won, pnl_c, settled_ts_ms, market_id),
    )
    conn.commit()


def mark_unresolved(conn: sqlite3.Connection, market_id: str, now_ms: int) -> None:
    conn.execute(
        "UPDATE trades SET status='unresolved', settled_ts_ms=? WHERE market_id=? AND status='open'",
        (now_ms, market_id),
    )
    conn.commit()


# ---------------- daemon ----------------

def load_yes_quotes(conn: sqlite3.Connection, since_ms: int) -> list[dict]:
    rows = conn.execute(
        """SELECT q.ts_ms, q.market_id, q.side, q.bid, q.ask,
                  m.asset, m.horizon_s, m.open_time_ms, m.close_time_ms
           FROM quotes q JOIN markets m ON q.market_id = m.market_id
           WHERE q.ts_ms > ? ORDER BY q.ts_ms""",
        (since_ms,),
    ).fetchall()
    out = []
    for r in rows:
        is_up = r["market_id"].endswith("-0")
        want = "up" if is_up else "down"
        if r["side"] != want:
            continue
        out.append({
            "ts_ms": int(r["ts_ms"]), "market_id": r["market_id"],
            "side": r["side"], "bid": r["bid"], "ask": r["ask"],
            "asset": r["asset"], "horizon_s": int(r["horizon_s"]),
            "open_time_ms": int(r["open_time_ms"]), "close_time_ms": int(r["close_time_ms"]),
            "is_up_market": is_up,
        })
    return out


def poll_cycle(conn: sqlite3.Connection, ledger: sqlite3.Connection, engine: WalletEngine,
               cache: KlineCache, state: dict) -> None:
    now_ms = int(time.time() * 1000)
    watermark = state.get("watermark", LIVE_START_MS - 60_000)
    quotes = load_yes_quotes(conn, watermark - 60_000)
    processed: set = state.setdefault("processed", set())
    fresh = 0
    for q in quotes:
        key = (q["ts_ms"], q["market_id"], q["side"])
        if key in processed:
            continue
        processed.add(key)
        if q["ts_ms"] > watermark:
            watermark = q["ts_ms"]
        # freshness: no backfill-trading stale signals
        if now_ms - q["ts_ms"] > FRESHNESS_S * 1000:
            continue
        if q["ts_ms"] < LIVE_START_MS:
            continue
        fresh += 1
        sym = SYMBOLS.get(q["asset"])
        if sym is None:
            continue
        cache.refresh(sym)
        cd = cache.get(sym)
        fair = fair_yes(cd, q["open_time_ms"], q["horizon_s"], q["ts_ms"], q["is_up_market"]) if cd else None
        decision = engine.on_quote(q, q, fair)
        if decision["action"] == "trade":
            t = decision["trade"]
            record_trade(ledger, t)
            print(f"[wallet] TRADE {t['asset']} {t['hz_s']}s {t['market_id']} ask={t['ask']:.2f} "
                  f"fair_cal={t['fair_cal']:.3f} gap_cal={t['gap_cal']:+.3f} cost={t['cost_cents']}c "
                  f"day_left={engine.day_wallet_cents}c", flush=True)
    state["watermark"] = watermark
    if len(processed) > 400_000:
        state["processed"] = set(list(processed)[-200_000:])

    # settle open positions from collector resolutions
    open_pos = engine.position
    if open_pos is not None:
        r = conn.execute("SELECT outcome FROM resolutions WHERE market_id=?", (open_pos["market_id"],)).fetchone()
        if r is not None:
            res = engine.on_resolution(open_pos["market_id"], r["outcome"], now_ms)
            if res:
                book_settlement(ledger, res["market_id"], res["won"], res["pnl_cents"], res["settled_ts_ms"])
                print(f"[wallet] SETTLE {res['market_id']} won={res['won']} pnl={res['pnl_cents']}c "
                      f"day_wallet={engine.day_wallet_cents}c", flush=True)
        elif now_ms > open_pos["close_ms"] + UNRESOLVED_TIMEOUT_S * 1000:
            mark_unresolved(ledger, open_pos["market_id"], now_ms)
            engine.position = None
            print(f"[wallet] UNRESOLVED {open_pos['market_id']} (timeout)", flush=True)

    # day rollover report
    today = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    if state.get("last_report_day") != today:
        write_daily_report(ledger, state)
        state["last_report_day"] = today


def write_daily_report(ledger: sqlite3.Connection, state: dict) -> None:
    rows = ledger.execute(
        """SELECT entry_day, COUNT(*) n, SUM(pnl_cents) pnl, SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) w
           FROM trades WHERE status='settled' GROUP BY entry_day ORDER BY entry_day"""
    ).fetchall()
    lines = ["", f"## {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — wallet status", ""]
    lines.append("| entry day | trades | wins | realized PnL |")
    lines.append("|---|---|---|---|")
    tot = 0
    for r in rows:
        tot += r["pnl"] or 0
        lines.append(f"| {r['entry_day']} | {r['n']} | {r['w'] or 0} | {(r['pnl'] or 0)/100:+.2f} |")
    lines.append(f"| **total** | {sum(r['n'] for r in rows)} | {sum(r['w'] or 0 for r in rows)} | **{tot/100:+.2f}** |")
    lines.append("")
    with open(REPORT, "a") as fh:
        fh.write("\n".join(lines) + "\n")


def restore_state(ledger: sqlite3.Connection, engine: WalletEngine) -> None:
    """Crash recovery: rebuild seen epochs, day wallet, and any open position
    from the ledger so a restart doesn't orphan positions or re-enter epochs.
    """
    rows = ledger.execute("SELECT * FROM trades").fetchall()
    for r in rows:
        engine.seen_epochs.add((r["asset"], r["open_ms"], r["hz_s"]))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    spent = ledger.execute(
        "SELECT COALESCE(SUM(cost_cents),0) s FROM trades WHERE entry_day=? AND status='open'", (today,)
    ).fetchone()["s"]
    paid_back = ledger.execute(
        """SELECT COALESCE(SUM(CASE WHEN won=1 THEN 100 ELSE 0 END),0) s
           FROM trades WHERE entry_day=? AND status='settled'""", (today,)
    ).fetchone()["s"]
    engine.day = today
    engine.day_wallet_cents = engine.allowance_cents - int(spent) + int(paid_back)
    open_rows = ledger.execute("SELECT * FROM trades WHERE status='open'").fetchall()
    if open_rows:
        r = open_rows[-1]
        engine.position = {
            "entry_ts_ms": r["entry_ts_ms"], "market_id": r["market_id"],
            "asset": r["asset"], "hz_s": r["hz_s"], "open_ms": r["open_ms"],
            "close_ms": r["close_ms"], "is_up_market": bool(r["is_up_market"]),
            "ask": r["ask"], "fair_cal": r["fair_cal"], "gap_cal": r["gap_cal"],
            "cost_cents": r["cost_cents"], "entry_day": r["entry_day"],
        }
        print(f"[wallet] restored open position {r['market_id']} (entry {r['entry_day']})", flush=True)
    print(f"[wallet] restored: {len(rows)} historical trades, day_wallet={engine.day_wallet_cents}c", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-calibration", action="store_true")
    ap.add_argument("--once", action="store_true", help="single poll cycle (debug)")
    args = ap.parse_args()

    if args.build_calibration:
        build_calibration()
        return

    calib = load_calibration()
    conn = sqlite3.connect(str(COLLECTOR_DB))
    conn.row_factory = sqlite3.Row
    ledger = open_ledger()
    engine = WalletEngine(calib)
    restore_state(ledger, engine)
    cache = KlineCache()
    state: dict = {"watermark": LIVE_START_MS - 60_000, "processed": set(),
                   "last_report_day": None}
    print(f"[wallet] live from {datetime.fromtimestamp(LIVE_START_MS/1000, tz=timezone.utc)} "
          f"allowance={ALLOWANCE_CENTS}c/day, 1 contract/trade, serial", flush=True)
    while True:
        try:
            poll_cycle(conn, ledger, engine, cache, state)
        except Exception as exc:
            print(f"[wallet] poll error: {exc!r}", flush=True)
        if args.once:
            break
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
