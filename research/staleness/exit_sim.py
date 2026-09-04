"""Round 39: sell-into-catch-up exit simulation (SIRMARTINGALE variant).

Entry: round-33 gate on v2_ewma (lambda + isotonic fit on TRAIN only,
split 2026-08-29 12:00 UTC); buy yes at ask when prob - ask > fee.
Exits (on the same market's subsequent collector quotes):
  hold        : ride to resolution (round-33 baseline)
  catch-up Tc : sell at the current bid once mid >= entry_ask + Tc/100
                (checked only until close-30s; else hold to settlement)
Fees charged on both taker legs. Compares mean EV/trade and win rate.
"""

from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from research.staleness.audit import DB, SYMBOLS, build_symbol_arrays, load_klines  # noqa: E402

OUT = REPO / "research" / "staleness" / "EXIT_SIM.md"
FEE_RATE = 0.07
SPLIT_MS = 1788004800000


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def build_sigma(df: pl.DataFrame, kind: str):
    ts = df["ts_ms"].to_numpy().astype(np.int64)
    close = df["close"].to_numpy().astype(float)
    r = np.full(len(ts), np.nan)
    r[1:] = np.log(close[1:] / close[:-1])
    a = np.abs(r)
    out = np.full(len(ts), np.nan)
    if kind == "ewma":
        lam = math.exp(math.log(0.5) / 30.0)
        w = np.nan
        for i in range(len(ts)):
            if np.isfinite(a[i]):
                w = a[i] if not np.isfinite(w) else lam * w + (1 - lam) * a[i]
                out[i] = w
    return out * math.sqrt(math.pi / 2.0)


def main() -> None:
    conn = sqlite3.connect(str(DB))
    markets = pl.read_database("SELECT market_id, asset, horizon_s, open_time_ms, close_time_ms FROM markets", conn)
    quotes = pl.read_database("SELECT ts_ms, market_id, side, bid, ask FROM quotes", conn)
    res = pl.read_database("SELECT market_id, outcome FROM resolutions", conn)
    conn.close()
    markets = markets.with_columns(pl.col("market_id").str.slice(-1).alias("suffix")).with_columns(
        (pl.col("suffix") == "0").alias("is_up"))
    res = res.with_columns(
        pl.col("market_id").str.slice(-1).alias("suffix"),
        (pl.col("outcome") == "up").alias("up_won"),
    ).with_columns(((pl.col("suffix") == "0") == pl.col("up_won")).alias("token_won")).select(["market_id", "token_won"])
    q = quotes.join(markets, on="market_id").join(res, on="market_id")
    q = q.filter(
        (pl.col("is_up") & (pl.col("side") == "up")) | (~pl.col("is_up") & (pl.col("side") == "down"))
    ).filter(
        pl.col("bid").is_not_null() & pl.col("ask").is_not_null()
        & (pl.col("bid") > 0.01) & (pl.col("ask") < 0.99) & (pl.col("bid") < pl.col("ask"))
    )
    sig = {}
    meta = {}
    for a, s in SYMBOLS.items():
        kdf = load_klines(s)
        ts, close, opn, _, prefix = build_symbol_arrays(kdf)
        sig[a] = build_sigma(kdf, "ewma")
        meta[a] = (ts, close, opn, prefix)

    scored = []
    for r in q.to_dicts():
        a = r["asset"]
        if a not in meta:
            continue
        ts, close, opn, prefix = meta[a]
        o, c, tsq = int(r["open_time_ms"]), int(r["close_time_ms"]), int(r["ts_ms"])
        if not (o <= tsq < c):
            continue
        N = int(r["horizon_s"]) // 60
        i_open = int(np.searchsorted(ts, o))
        if i_open >= len(ts) or ts[i_open] != o:
            continue
        i_now = int(np.searchsorted(ts, tsq, side="right")) - 1
        if i_now < i_open:
            continue
        count_obs = i_now - i_open + 1
        n_fut = N - count_obs
        if n_fut < 0:
            continue
        K = float(opn[i_open])
        spot = float(close[i_now])
        sg = float(sig[a][i_now])
        if not np.isfinite(sg) or sg <= 0:
            continue
        d_min = float(n_fut)
        if d_min >= 1.0:
            z = math.log(spot / K) / (sg * math.sqrt(1 / 3.0))
        else:
            A = float(opn[i_now])
            mean_s = (1 - d_min) * A + d_min * spot
            sd = sg * math.sqrt(max(d_min ** 3 / 3.0, 1e-12))
            z = math.log(max(mean_s, 1e-9) / K) / max(sd, 1e-12)
        scored.append({
            "market_id": r["market_id"], "ts_ms": tsq, "z": z,
            "won": int(r["token_won"]), "ask": float(r["ask"]), "bid": float(r["bid"]),
            "close_ms": c,
        })
    df = pl.DataFrame(scored).sort("ts_ms")
    tr = df.filter(pl.col("ts_ms") < SPLIT_MS)
    te = df.filter(pl.col("ts_ms") >= SPLIT_MS)
    lam = None
    grid = np.arange(0.5, 8.001, 0.05)
    ztr, wtr = tr["z"].to_numpy(), tr["won"].to_numpy().astype(float)
    bl = None
    for l in grid:
        b = float(((sigmoid(ztr / l) - wtr) ** 2).mean())
        if bl is None or b < bl:
            lam, bl = float(l), b
    iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(ztr / lam), wtr)
    te = te.with_columns((pl.col("z") / lam).alias("zl"))
    te = te.with_columns(pl.Series("prob", iso.predict(sigmoid(te["zl"].to_numpy()))))
    te = te.with_columns((FEE_RATE * pl.col("ask") * (1 - pl.col("ask"))).alias("fee"))
    gated = te.filter((pl.col("prob") - pl.col("ask")) > pl.col("fee")).sort("ts_ms")

    # quote paths per market for exits
    paths = quotes.sort("ts_ms").group_by("market_id").agg(
        pl.col("ts_ms"), pl.col("bid"), pl.col("ask"))
    pmap = {r["market_id"]: (r["ts_ms"], r["bid"], r["ask"]) for r in paths.to_dicts()}

    def simulate(target_c):
        evs, wins, n_exit = [], 0, 0
        for r in gated.to_dicts():
            ask, fee, mk, close_ms = r["ask"], r["fee"], r["market_id"], r["close_ms"]
            ts_arr, bid_arr, ask_arr = pmap.get(mk, (None, None, None))
            if ts_arr is None:
                continue
            pnl_hold = (1 - ask - fee) if r["won"] else (-ask - fee)
            pnl = pnl_hold
            exited = False
            stop = close_ms - 30_000
            for t, b, ak in zip(ts_arr, bid_arr, ask_arr):
                if t <= r["ts_ms"] or t > stop:
                    continue
                if b is None or ak is None or b <= 0.01:
                    continue
                mid = (b + ak) / 2
                if mid >= ask + target_c / 100.0:
                    fee2 = FEE_RATE * b * (1 - b)
                    pnl = (b - ask) - fee - fee2
                    exited = True
                    break
            if exited:
                n_exit += 1
            if pnl > 0:
                wins += 1
            evs.append(pnl)
        return float(np.mean(evs)), wins / len(evs), n_exit

    lines = ["# Round 39: sell-into-catch-up exit simulation (v2_ewma gate)", "",
             f"lambda(train) {lam:.2f}; gated entries {gated.height:,}; exits at bid, fees on both legs", "",
             "| strategy | EV/trade | win rate | early exits |", "|---|---|---|---|"]
    ev0, wr0, _ = simulate(999)  # never exits => hold baseline
    lines.append(f"| hold to settlement | {ev0*100:+.2f}c | {wr0:.3f} | 0 |")
    for tc in (2, 3, 5, 8):
        ev, wr, ne = simulate(tc)
        lines.append(f"| catch-up {tc}c | {ev*100:+.2f}c | {wr:.3f} | {ne:,} |")
    OUT.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
