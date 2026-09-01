"""Staleness audit — Branch C precursor measurement on live collector data.

Question (the project's founding thesis, spec §3.2 #1): do Jupiter/Polymarket
5m/15m crypto binary quotes lag the underlying enough to trade against?

Method (assumption-light, no ML):
  1. Per collected quote, compute the CLT Asian-digital fair value of the
     market's yes token from Binance 1m klines (strike = epoch-open 1m open,
     running TWAP mean, per-minute sigma from r24). Basis risk (Binance vs
     Chainlink, 1m-close TWAP vs oracle TWAP) is an accepted approximation —
     settlement_check measured ~83% agreement.
  2. gap = fair_yes - ask_yes. A taker rule "buy when gap > fee(ask)" is the
     direct economic test: EV, win rate, N, per-day EV vs OFFICIAL
     resolutions from the collector (no fair-value assumption on the
     outcome leg — basis risk shows up in the win rate).
  3. Cross-asset: at BTC |1m move| events, does SOL/ETH underlying respond
     same-minute (transmission premise) and do SOL/ETH quotes reprice
     slower than BTC quotes (venue-side, polling-order confound noted)?

Confound notes:
  - Quote timestamps are COLLECTOR ARRIVAL times; a reprice between polls is
    invisible. Measured staleness is a LOWER bound on venue responsiveness...
    i.e. quotes can only look fresher than they are? No: sampler delay makes
    quotes look SLOWER (older fair at arrival). So measured staleness is an
    UPPER bound on venue staleness. If even this upper bound shows no edge,
    the venue is at least that sharp.
  - Collector prioritizes BTC orderbooks first each cycle -> SOL/ETH measured
    lags include extra sampler wait. Fair-gap metric is largely immune
    (compare quote to fair at the same instant); event-lag comparisons
    across assets are NOT — reported with the caveat.

Outputs: research/staleness/STALENESS_AUDIT.md + printed summary.
Sealed H1-2026 holdout untouched (this is post-seal live collection only).
"""
from __future__ import annotations

import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

DB = REPO / "data" / "collector.db"
RAW = REPO / "data" / "raw"
OUT = REPO / "research" / "staleness" / "STALENESS_AUDIT.md"

FEE_RATE = 0.07
FEE_RATE_2X = 0.14  # spec §3 "Jupiter total ≈ 2× Polymarket" scenario
SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT"}


def norm_cdf(x):
    return 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))


def load_klines(symbol: str) -> pl.DataFrame:
    files = sorted((RAW / symbol / "kline_1m").glob("*.parquet"))
    dfs = [pl.read_parquet(str(f)) for f in files]
    df = pl.concat(dfs).sort("ts_ms")
    # dedup repeated minutes (hour-file flush overlap), keep last
    df = df.unique(subset=["ts_ms"], keep="last", maintain_order=True)
    return df.sort("ts_ms")


def build_symbol_arrays(df: pl.DataFrame):
    ts = df["ts_ms"].to_numpy().astype(np.int64)
    close = df["close"].to_numpy().astype(float)
    opn = df["open"].to_numpy().astype(float)
    logret = np.full(len(ts), np.nan)
    logret[1:] = np.log(close[1:] / close[:-1])
    absr = np.abs(logret)
    # rolling mean |ret| over 24 min (r24), sigma = r24 * sqrt(pi/2)
    r24 = np.full(len(ts), np.nan)
    csum = np.cumsum(np.nan_to_num(absr))
    nn = np.cumsum(np.isfinite(absr).astype(float))
    for i in range(len(ts)):
        lo = max(0, i - 24)
        n = nn[i] - nn[lo]
        if n >= 12:
            r24[i] = (csum[i] - csum[lo]) / max(n, 1)
    sigma = r24 * math.sqrt(math.pi / 2.0)
    prefix_close = np.concatenate([[0.0], np.cumsum(close)])
    return ts, close, opn, sigma, prefix_close


def main() -> None:
    conn = sqlite3.connect(str(DB))
    markets = pl.read_database("SELECT market_id, title, asset, horizon_s, open_time_ms, close_time_ms FROM markets", conn)
    quotes = pl.read_database("SELECT ts_ms, market_id, side, bid, ask FROM quotes", conn)
    res = pl.read_database("SELECT market_id, outcome FROM resolutions", conn)
    conn.close()

    # market side from suffix: -0 = Up market, -1 = Down market (RECON)
    markets = markets.with_columns(
        pl.col("market_id").str.slice(-1).alias("suffix")
    ).with_columns(
        (pl.col("suffix") == "0").alias("is_up_market")
    )
    # token won: (suffix==0) == (outcome=='up')
    res = res.with_columns(
        pl.col("market_id").str.slice(-1).alias("suffix"),
        (pl.col("outcome") == "up").alias("up_won"),
    ).with_columns(
        ((pl.col("suffix") == "0") == pl.col("up_won")).alias("token_won")
    ).select(["market_id", "token_won"])

    # keep the yes-side quote rows per market (side == token of that market)
    # collector stores side 'up'/'down' per market; the market's own token:
    #   Up market -> side 'up' row is its yes book; Down market -> 'down' row
    q = (
        quotes.join(markets, on="market_id", how="inner")
        .join(res, on="market_id", how="inner")
    )
    q = q.filter(
        (pl.col("is_up_market") & (pl.col("side") == "up"))
        | (~pl.col("is_up_market") & (pl.col("side") == "down"))
    )
    q = q.filter(
        pl.col("bid").is_not_null() & pl.col("ask").is_not_null()
        & (pl.col("bid") > 0.01) & (pl.col("ask") < 0.99)
        & (pl.col("bid") < pl.col("ask"))  # drop crossed/locked snapshots
    )
    print(f"yes-side quotes after filters: {q.height}")

    # per-symbol kline arrays
    sym_data = {a: build_symbol_arrays(load_klines(s)) for a, s in SYMBOLS.items()}

    rows = []
    qd = q.to_dicts()
    for r in qd:
        asset = r["asset"]
        if asset not in sym_data:
            continue
        ts, close, opn, sigma, prefix = sym_data[asset]
        open_ms = int(r["open_time_ms"])
        close_ms = int(r["close_time_ms"])
        hz_s = int(r["horizon_s"])
        tsq = int(r["ts_ms"])
        if not (open_ms <= tsq < close_ms):
            continue
        N = hz_s // 60
        i_open = int(np.searchsorted(ts, open_ms))
        if i_open >= len(ts) or ts[i_open] != open_ms:
            # no kline exactly at epoch open (gap) — try nearest within 60s
            j = int(np.searchsorted(ts, open_ms - 60_000))
            if j >= len(ts) or abs(int(ts[j]) - open_ms) > 60_000:
                continue
            i_open = j
        i_now = int(np.searchsorted(ts, tsq, side="right")) - 1
        if i_now < i_open:
            continue
        count_obs = i_now - i_open + 1
        n_fut = N - count_obs
        if n_fut < 0:
            continue
        K = float(opn[i_open])  # strike proxy: epoch-open 1m open
        sum_obs = float(prefix[i_now + 1] - prefix[i_open])
        last_close = float(close[i_now])
        avg_obs = sum_obs / count_obs
        # E[TWAP at close]: observed bars fixed; future bars ~ last close
        e_twap = (sum_obs + last_close * n_fut) / N
        # Var of future average: sigma^2 * (n+1)(2n+1)/(6n) per-minute steps
        if n_fut > 0:
            var_fut = (sigma[i_now] ** 2) * ((n_fut + 1) * (2 * n_fut + 1)) / (6.0 * n_fut)
            var_twap = (n_fut / N) ** 2 * var_fut
        else:
            var_twap = 1e-12
        sd = math.sqrt(max(var_twap, 1e-12))
        fair_up = float(norm_cdf((e_twap - K) / sd))
        fair_up = min(max(fair_up, 0.005), 0.995)
        fair_yes = fair_up if r["is_up_market"] else 1.0 - fair_up
        ask = float(r["ask"])
        bid = float(r["bid"])
        mid = (bid + ask) / 2.0
        fee = FEE_RATE * ask * (1 - ask)
        gap = fair_yes - ask  # edge if we buy yes at ask
        tau_rem = (close_ms - tsq) / 1000.0
        rows.append({
            "market_id": r["market_id"], "asset": asset, "hz": f"{hz_s}s", "ts_ms": tsq,
            "open_ms": open_ms, "won": int(r["token_won"]),
            "ask": ask, "mid": mid, "fair": fair_yes,
            "gap": gap, "fee": fee,
            "ev_buy": (1 - ask - fee) if r["token_won"] else (-ask - fee),
            "tau_rem": tau_rem, "sigma_1m": float(sigma[i_now]) if np.isfinite(sigma[i_now]) else np.nan,
        })

    df = pl.DataFrame(rows)
    df.write_parquet(str(REPO / "research" / "staleness" / "scored_quotes.parquet"))
    print(f"scored quotes: {df.height}")
    if df.is_empty():
        OUT.write_text("# Staleness audit\n\nNo scoreable quotes.\n")
        return

    df = df.with_columns([
        (pl.col("gap") > pl.col("fee")).alias("buy_signal"),
        (pl.col("gap") > 2 * pl.col("fee")).alias("buy_signal_2x"),
        ((pl.col("gap").abs()) > pl.col("fee")).alias("stale_beyond_fee"),
    ])

    lines = ["# Staleness Audit — Live Collector Data (Branch C precursor)", ""]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("Data: collector.db quotes joined with official resolutions; fair = CLT Asian digital on Binance 1m klines (strike = epoch-open 1m open, sigma from r24).")
    lines.append("Caveats: quote timestamps are collector-arrival times (measured staleness = UPPER bound on venue staleness); BTC orderbooks polled first each cycle (cross-asset lag comparisons carry sampler bias); Binance-vs-Chainlink basis noise inflates |gap| symmetrically — a NEGATIVE EV result is robust, a POSITIVE one needs the resolution-based win rate to confirm.")
    lines.append("")

    # 1. headline stale fractions
    lines.append("## 1. How far do quotes sit from model fair value?")
    lines.append("")
    lines.append("| asset | hz | N quotes | median \\|gap\\| | p90 \\|gap\\| | stale>fee | stale>2fee |")
    lines.append("|---|---|---|---|---|---|---|")
    for (a, h), g in df.group_by(["asset", "hz"]):
        gd = g.to_dicts()
        gaps = np.abs(np.array([d["gap"] for d in gd]))
        sf = float(np.mean([d["stale_beyond_fee"] for d in gd]))
        sf2 = float(np.mean([d["stale_beyond_fee"] and d["gap"].__abs__() > 2 * d["fee"] for d in gd]))
        lines.append(f"| {a} | {h} | {len(gd)} | {np.median(gaps):.4f} | {np.percentile(gaps, 90):.4f} | {sf:.1%} | {sf2:.1%} |")
    lines.append("")

    # 2. THE economic test: taker rule vs official resolutions
    lines.append("## 2. Taker rule 'buy yes when fair - ask > fee' vs official resolutions")
    lines.append("")
    for rate_label, col in [("fee=0.07", "buy_signal"), ("fee=0.14 (2x)", "buy_signal_2x")]:
        sel = df.filter(pl.col(col))
        n = sel.height
        if n == 0:
            lines.append(f"**{rate_label}: no trades fire.**")
            continue
        ev = float(sel["ev_buy"].mean())
        wr = float(sel["won"].mean())
        # per-day EV + day-block bootstrap
        days = np.array([datetime.fromtimestamp(int(t) / 1000, tz=timezone.utc).date() for t in sel["ts_ms"].to_list()])
        pnl = sel["ev_buy"].to_numpy()
        uniq = np.unique(days)
        per_day = {str(d): float(pnl[days == d].mean()) for d in uniq}
        rng = np.random.default_rng(0)
        boots = []
        day_pnl = {d: pnl[days == d] for d in uniq}
        for _ in range(10000):
            smp = np.concatenate([day_pnl[d] for d in rng.choice(uniq, size=len(uniq), replace=True)])
            boots.append(float(np.mean(smp)))
        lo, hi = np.percentile(boots, [2.5, 97.5])
        lines.append(f"**{rate_label}**: N={n}, win rate {wr:.1%} (breakeven needs >{(0.5+0.0):.1%} avg depending on avg ask), EV/trade {ev:+.4f}, day-block 95% CI [{lo:+.4f}, {hi:+.4f}], total PnL {pnl.sum():+.2f}")
        lines.append("")
        lines.append("  Per-day EV: " + ", ".join(f"{d}: {v:+.4f} (n={(days==np.datetime64(d)).sum() if isinstance(d, np.datetime64) else sum(1 for x in days if str(x)==d)})" for d, v in per_day.items()))
        lines.append("")

    # 3. by bucket (asset x hz)
    lines.append("## 3. Taker EV by asset x horizon (fee=0.07 gate)")
    lines.append("")
    lines.append("| asset | hz | N | win | EV |")
    lines.append("|---|---|---|---|---|")
    for (a, h), g in df.filter(pl.col("buy_signal")).group_by(["asset", "hz"]):
        gd = g.to_dicts()
        ev = float(np.mean([d["ev_buy"] for d in gd]))
        wr = float(np.mean([d["won"] for d in gd]))
        lines.append(f"| {a} | {h} | {len(gd)} | {wr:.1%} | {ev:+.4f} |")
    lines.append("")

    # 4. polling cadence (confound doc)
    lines.append("## 4. Collector polling cadence per asset (confound documentation)")
    lines.append("")
    lines.append("| asset | hz | markets | quotes | median inter-quote s |")
    lines.append("|---|---|---|---|---|")
    for (a, h), g in q.group_by(["asset", "hz"]) if "hz" in q.columns else []:
        pass
    conn2 = sqlite3.connect(str(DB))
    cad = conn2.execute("""
        SELECT m.asset, m.horizon_s, COUNT(DISTINCT q.market_id) mk, COUNT(*) qn
        FROM quotes q JOIN markets m ON q.market_id=m.market_id GROUP BY m.asset, m.horizon_s
    """).fetchall()
    for a, hz, mk, qn in cad:
        ts_arr = np.array([r[0] for r in conn2.execute(
            "SELECT q.ts_ms FROM quotes q JOIN markets m ON q.market_id=m.market_id WHERE m.asset=? AND m.horizon_s=? ORDER BY q.ts_ms", (a, hz)
        ).fetchall()])
        med_gap = float(np.median(np.diff(ts_arr))) if len(ts_arr) > 2 else float("nan")
        lines.append(f"| {a} | {hz}s | {mk} | {qn} | {med_gap/1000:.1f} |")
    conn2.close()
    lines.append("")

    # 5. cross-asset transmission (user direction: BTC moves -> SOL/ETH)
    lines.append("## 5. Cross-asset transmission at BTC move events")
    lines.append("")
    ts_b, close_b, _, _, _ = sym_data["BTC"]
    lr_b = np.full(len(ts_b), np.nan)
    lr_b[1:] = np.log(close_b[1:] / close_b[:-1])
    for tgt in ("ETH", "SOL"):
        ts_t, close_t, _, _, _ = sym_data[tgt]
        lr_t = np.full(len(ts_t), np.nan)
        lr_t[1:] = np.log(close_t[1:] / close_t[:-1])
        # align on common minutes
        common, i_b, i_t = np.intersect1d(ts_b, ts_t, return_indices=True)
        rb = lr_b[i_b]
        rt = lr_t[i_t]
        fin = np.isfinite(rb) & np.isfinite(rt)
        rb, rt = rb[fin], rt[fin]
        corr = float(np.corrcoef(rb, rt)[0, 1])
        ev_mask = np.abs(rb) >= 0.001  # >=10bp BTC minute move
        base = float(np.mean(np.abs(rt)))
        cond = float(np.mean(np.abs(rt[ev_mask]))) if ev_mask.sum() > 0 else float("nan")
        same_dir = float(np.mean(np.sign(rt[ev_mask]) == np.sign(rb[ev_mask]))) if ev_mask.sum() > 0 else float("nan")
        lines.append(f"- {tgt}: corr(1m ret, BTC) = {corr:.3f}; |ret| baseline {base*1e4:.1f}bp vs {cond*1e4:.1f}bp when BTC moves >=10bp; same-direction {same_dir:.1%} (n={int(ev_mask.sum())} events)")
    lines.append("")
    lines.append("Transmission premise confirmed if SOL/ETH move materially same-minute with BTC. Venue-side test (do SOL/ETH *quotes* lag BTC quotes on the same shock) is confounded by BTC-first polling order — see caveats; requires interleaved sampling or venue-native timestamps to measure cleanly.")

    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT}")
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
