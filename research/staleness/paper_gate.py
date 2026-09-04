"""Integrated-gate paper daemon — fair_v2 + lambda + isotonic, run forward.

STEP 2 of the 6-step sequence. This is the gate the round-33 re-test actually
measured (v2_ewma, lambda(train)=1.95, isotonic on train, EV +8.04c/trade,
daily-block CI [+5.48,+10.47]); the live $5 daemon tests a DIFFERENT gate
(v1 fair + collapsed pre-launch calibration, constant fair_cal=0.737).

STRICT SEPARATION from the live control (Step 5):
  - reads: collector.db quotes/resolutions (shared sensor, read-only use),
    Binance 1m klines under data/raw (shared sensor).
  - writes: ONLY data/paper_gate.db (own ledger) and
    research/staleness/PAPER_GATE_LIVE.md (own report).
  - NEVER touches data/paper_wallet.db, research/staleness/WALLET_LIVE.md,
    or research/staleness/calibration.npz (the live control's files).
  - calibration frozen in research/staleness/calibration_v2.npz
    (train-only fit at SPLIT_MS, same protocol as retest_logspace.py);
    refits ONLY at declared checkpoints, never intra-run.

Entry/exit/capacity mirror live_wallet.py: $5/day allowance, 1 contract,
serial, one entry per epoch, hold to settlement, 30s freshness.

Usage:
    .venv/bin/python research/staleness/paper_gate.py --build-calibration
    .venv/bin/python research/staleness/paper_gate.py [--once]
"""

from __future__ import annotations

import argparse
import math
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from quantbtc.fees import order_fee  # noqa: E402
from research.staleness.live_wallet import (  # noqa: E402
    ALLOWANCE_CENTS,
    COLLECTOR_DB,
    FEE_RATE,
    FRESHNESS_S,
    POLL_S,
    SYMBOLS,
    UNRESOLVED_TIMEOUT_S,
    WalletEngine,
    book_settlement,
    load_yes_quotes,
    mark_unresolved,
)
from research.staleness.retest_logspace import (  # noqa: E402
    PARQUET as COMPARE_PARQUET,
    SPLIT_MS,
    fit_lambda,
    sigmoid,
)

LEDGER_DB = REPO / "data" / "paper_gate.db"
RAW = REPO / "data" / "raw"
CALIBRATION_V2 = REPO / "research" / "staleness" / "calibration_v2.npz"
REPORT = REPO / "research" / "staleness" / "PAPER_GATE_LIVE.md"

LAMBDA_TRAIN = 1.95  # retest_logspace v2_ewma fit on train; re-fit checked at build
EWMA_HALFLIFE = 30.0
K_PI2 = math.sqrt(math.pi / 2.0)

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
"""


def build_calibration_v2() -> None:
    """Fit lambda + isotonic on TRAIN span only; freeze to calibration_v2.npz.

    Refuses to write when the mapping is degenerate (same spirit as the
    pre-launch gate: distinct>=10, tercile win-rate gap>0.05).
    """
    import polars as pl
    from sklearn.isotonic import IsotonicRegression

    df = pl.read_parquet(str(COMPARE_PARQUET)).filter(
        pl.col("cfg") == "v2_ewma"
    ).sort("ts_ms")
    tr = df.filter(pl.col("ts_ms") < SPLIT_MS)
    z_tr = tr["z"].to_numpy()
    won_tr = tr["won"].to_numpy().astype(float)
    lam = fit_lambda(z_tr, won_tr)
    iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(z_tr / lam), won_tr)
    prob_tr = iso.predict(sigmoid(z_tr / lam))

    distinct = len(np.unique(np.round(prob_tr, 4)))
    edges = np.unique(np.quantile(prob_tr, [0.0, 1 / 3, 2 / 3, 1.0]))
    wrs = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (prob_tr >= lo) & (prob_tr <= hi) if hi == edges[-1] else (prob_tr >= lo) & (prob_tr < hi)
        wrs.append(float(won_tr[m].mean()) if m.sum() >= 100 else float("nan"))
    valid = [w for w in wrs if np.isfinite(w)]
    gap = (max(valid) - min(valid)) if len(valid) >= 2 else 0.0
    print(f"train n={tr.height:,} lambda={lam:.2f} distinct={distinct} tercile_gap={gap:.3f}")
    if distinct < 10 or gap <= 0.05:
        print("FATAL: v2 calibration degenerate — refusing to freeze", file=sys.stderr)
        sys.exit(1)
    np.savez(str(CALIBRATION_V2), x=iso.X_thresholds_, y=iso.y_thresholds_,
             lam=lam, n_fit=len(tr), split_ms=SPLIT_MS)
    print(f"calibration_v2 frozen: {len(tr)} train quotes, lambda={lam:.2f}")


def load_calibration_v2():
    if not CALIBRATION_V2.exists():
        print(f"FATAL: {CALIBRATION_V2} missing — run with --build-calibration first",
              file=sys.stderr)
        sys.exit(2)
    z = np.load(str(CALIBRATION_V2))
    x, y, lam = z["x"], z["y"], float(z["lam"])

    def predict(zscore: float, is_up_market: bool) -> float:
        zy = zscore if is_up_market else -zscore
        return float(np.interp(sigmoid(zy / lam), x, y))

    return predict


class EwmaKlineCache:
    """Rolling kline window per symbol with EWMA(30m halflife) sigma.

    Mirrors live_wallet.KlineCache windowing; adds the EWMA|ret| sigma the
    v2_ewma config was scored with (round 32). 3h window = 180 bars vs
    30-bar halflife, so seed transient is ~1.5% weight — noted, accepted.
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
            df = pl.concat([pl.read_parquet(str(f)).select(["ts_ms", "open", "close"])
                            for f in files])
        except Exception:
            return
        df = df.sort("ts_ms").unique(subset=["ts_ms"], keep="last", maintain_order=True)
        ts = df["ts_ms"].to_numpy().astype(np.int64)
        cutoff = (now_ms if now_ms is not None else int(now * 1000)) - self.WINDOW_MS
        m = ts >= cutoff
        ts = ts[m]
        opn = df["open"].to_numpy().astype(float)[m]
        close = df["close"].to_numpy().astype(float)[m]
        n = len(ts)
        ewma = np.full(n, np.nan)
        if n >= 2:
            lam = math.exp(math.log(0.5) / EWMA_HALFLIFE)
            w = np.nan
            for i in range(1, n):
                a = abs(math.log(close[i] / close[i - 1])) if close[i - 1] > 0 else np.nan
                if np.isfinite(a):
                    w = a if not np.isfinite(w) else lam * w + (1 - lam) * a
                    ewma[i] = w * K_PI2
        self._data[symbol] = {"ts": ts, "open": opn, "close": close, "ewma": ewma}

    def get(self, symbol: str) -> dict | None:
        d = self._data.get(symbol)
        if d is None or len(d.get("ts", [])) < 60:
            return None
        return d


def fair_yes_v2(cache_data: dict, open_ms: int, hz_s: int, ts_ms: int) -> float | None:
    """Venue-accurate z for the epoch (final-60s TWAP settlement, log space).

    Mirrors calibration_compare.fair_v2(..., return_z=True); side applied by
    the caller via load_calibration_v2's is_up_market flag.
    """
    ts, opn, close, ewma = (cache_data["ts"], cache_data["open"],
                            cache_data["close"], cache_data["ewma"])
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
    n_fut = N - (i_now - i_open + 1)
    if n_fut < 0:
        return None
    K = float(opn[i_open])
    spot = float(close[i_now])
    sig = float(ewma[i_now]) if np.isfinite(ewma[i_now]) else np.nan
    if not np.isfinite(sig) or sig <= 0 or K <= 0 or spot <= 0:
        return None
    d_min = float(n_fut)
    if d_min >= 1.0:
        sd = sig * math.sqrt(1.0 / 3.0)
        z = math.log(spot / K) / max(sd, 1e-12)
    else:
        if n_fut <= 0:
            return None
        realized_avg = float(opn[i_now])
        mean_s = ((1.0 - d_min) * realized_avg + d_min * spot)
        sd = sig * math.sqrt(max(d_min ** 3 / 3.0, 1e-12))
        z = math.log(max(mean_s, 1e-9) / K) / max(sd, 1e-12)
    return z


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


def poll_cycle(conn: sqlite3.Connection, ledger: sqlite3.Connection,
               engine: WalletEngine, calib, cache: EwmaKlineCache, state: dict) -> None:
    now_ms = int(time.time() * 1000)
    watermark = state.get("watermark", now_ms - 60_000)
    quotes = load_yes_quotes(conn, watermark - 60_000)
    processed: set = state.setdefault("processed", set())
    for q in quotes:
        key = (q["ts_ms"], q["market_id"], q["side"])
        if key in processed:
            continue
        processed.add(key)
        if q["ts_ms"] > watermark:
            watermark = q["ts_ms"]
        if now_ms - q["ts_ms"] > FRESHNESS_S * 1000:
            continue
        sym = SYMBOLS.get(q["asset"])
        if sym is None:
            continue
        cache.refresh(sym)
        cd = cache.get(sym)
        z = fair_yes_v2(cd, q["open_time_ms"], q["horizon_s"], q["ts_ms"]) if cd else None
        fair = calib(z, q["is_up_market"]) if z is not None else None
        decision = engine.on_quote(q, q, fair)
        if decision["action"] == "trade":
            t = decision["trade"]
            record_trade(ledger, t)
            print(f"[paper-gate] TRADE {t['asset']} {t['hz_s']}s {t['market_id']} "
                  f"ask={t['ask']:.2f} fair_cal={t['fair_cal']:.3f} "
                  f"gap_cal={t['gap_cal']:+.3f} cost={t['cost_cents']}c "
                  f"day_left={engine.day_wallet_cents}c", flush=True)
    state["watermark"] = watermark
    if len(processed) > 400_000:
        state["processed"] = set(list(processed)[-200_000:])

    open_pos = engine.position
    if open_pos is not None:
        r = conn.execute("SELECT outcome FROM resolutions WHERE market_id=?",
                         (open_pos["market_id"],)).fetchone()
        if r is not None:
            res = engine.on_resolution(open_pos["market_id"], r["outcome"], now_ms)
            if res:
                book_settlement(ledger, res["market_id"], res["won"],
                                res["pnl_cents"], res["settled_ts_ms"])
                print(f"[paper-gate] SETTLE {res['market_id']} won={res['won']} "
                      f"pnl={res['pnl_cents']}c day_wallet={engine.day_wallet_cents}c",
                      flush=True)
        elif now_ms > open_pos["close_ms"] + UNRESOLVED_TIMEOUT_S * 1000:
            mark_unresolved(ledger, open_pos["market_id"], now_ms)
            engine.position = None
            print(f"[paper-gate] UNRESOLVED {open_pos['market_id']} (timeout)", flush=True)

    today = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    if state.get("last_report_day") != today:
        write_daily_report(ledger)
        state["last_report_day"] = today


def write_daily_report(ledger: sqlite3.Connection) -> None:
    rows = ledger.execute(
        """SELECT entry_day, COUNT(*) n, SUM(pnl_cents) pnl,
                  SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) w
           FROM trades WHERE status='settled' GROUP BY entry_day ORDER BY entry_day"""
    ).fetchall()
    lines = ["", f"## {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — paper-gate status",
             "", "| entry day | trades | wins | realized PnL |",
             "|---|---|---|---|"]
    tot = 0
    for r in rows:
        tot += r["pnl"] or 0
        lines.append(f"| {r['entry_day']} | {r['n']} | {r['w'] or 0} | {(r['pnl'] or 0)/100:+.2f} |")
    lines.append(f"| **total** | {sum(r['n'] for r in rows)} | {sum(r['w'] or 0 for r in rows)} | **{tot/100:+.2f}** |")
    lines.append("")
    with open(REPORT, "a") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-calibration", action="store_true")
    ap.add_argument("--once", action="store_true", help="single poll cycle (debug)")
    args = ap.parse_args()

    if args.build_calibration:
        build_calibration_v2()
        return

    calib = load_calibration_v2()
    conn = sqlite3.connect(str(COLLECTOR_DB))
    conn.row_factory = sqlite3.Row
    ledger = open_ledger()
    # Engine's calib maps raw fair -> calibrated prob, but our pipeline
    # calibrates from z-scores (side-aware) before calling on_quote — so the
    # engine gets the pre-calibrated prob with an identity mapping. Its raw
    # and calibrated gates then check the same (correct) condition twice.
    engine = WalletEngine(lambda f: float(f), allowance_cents=ALLOWANCE_CENTS)
    cache = EwmaKlineCache()
    now_ms = int(time.time() * 1000)
    state: dict = {"watermark": now_ms - 60_000, "processed": set(),
                   "last_report_day": None}
    print(f"[paper-gate] integrated gate (fair_v2 + lambda + isotonic) from "
          f"{datetime.fromtimestamp(now_ms/1000, tz=timezone.utc)} "
          f"allowance={ALLOWANCE_CENTS}c/day, 1 contract/trade, serial", flush=True)
    print(f"[paper-gate] ledger={LEDGER_DB} (live control untouched)", flush=True)
    while True:
        try:
            poll_cycle(conn, ledger, engine, calib, cache, state)
        except Exception as exc:
            print(f"[paper-gate] poll error: {exc!r}", flush=True)
        if args.once:
            break
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
