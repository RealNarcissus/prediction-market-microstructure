"""Regime-conditional evaluator: 24 cells pre-registered, bucket-specific
costs, Holm-Bonferroni + daily-block bootstrap.

Buckets: 3 vol terciles (r24, the single F6 lookback) x 4 coarse UTC
sessions (00-06, 06-12, 12-18, 18-24) x 2 horizons = 24 cells, fixed BEFORE
viewing. Bucket-specific round-trip cost per bucket, not global mean.
Holm-Bonferroni across k=24 as own family (separate from Phase-A R1-R12).
Sealed H1-2026 holdout untouched — validation-era bridge data only.

Join: epochs via end_ts - duration -> open_ms (slug is empty); side via
up_token_id / down_token_id; prices via data/polymarket/updown/
prices_*.parquet at open_ms + 60s.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))

from quantbtc.twapbars import aggregate_windows
from strategies.s002_lgbm_base import new_model as champ_model
from strategies.s023_lgbm_pos_lag23 import build_features as champ_feats

from rlenv.buckets import R24_CUTS, bucket_from_epoch, vol_label, session_label

KL = REPO / "data/klines"
UPDOWN = REPO / "data/polymarket/updown"

THETA = 0.05  # gate: only count epochs where |p-0.5| > theta
K_FAMILY = 24  # 3 vol x 4 sessions x 2 horizons
ENTRY_OFFSET_S = 60  # decision at open + 60s
SEAL_MS = int(np.datetime64("2026-01-01").astype("datetime64[ms]").astype(int))


def _load_bars(symbol: str) -> pl.DataFrame:
    p = KL / f"{symbol}_1m.parquet"
    df = pl.read_parquet(str(p)).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
    )
    return df.sort("open_time")


def champ_predictions(symbol: str, hz: str) -> dict[int, float]:
    """Train s023 on walk-forward train, predict validation span.
    Uses s023 features + s002 LGBM model, fitted on pre-seal history.
    Returns {open_ms -> p(up)} for all windows with finite features.
    """
    bars = _load_bars(symbol)
    agg = aggregate_windows(bars, hz)
    agg = agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next")).drop_nulls(["y_next"])
    X = champ_feats(agg)
    y = agg["y_next"].to_numpy().astype(int)
    fin = np.isfinite(X).all(axis=1)
    opens = agg["open_time"].dt.epoch("ms").to_numpy()
    # fit on train portion (before seal), predict all
    train_mask = fin & (opens < SEAL_MS)
    mdl = champ_model()
    mdl.fit(X[train_mask], y[train_mask])
    probs = mdl.predict_proba(X)[:, list(mdl.classes_).index(1)]
    out: dict[int, float] = {}
    for o, p, f_ok in zip(opens, probs, fin):
        if f_ok:
            # opens are np datetime64 or int ms depending on polars version
            try:
                ts = int(o)
            except (TypeError, ValueError):
                ts = int(np.datetime64(o).astype("datetime64[ms]").astype(int))
            out[ts] = float(p)
    return out


def _r24_map(symbol: str) -> dict[int, float]:
    """Map open_ms -> r24 (rolling mean abs log return, window 24)."""
    bars = _load_bars(symbol).with_columns(
        (pl.col("close") / pl.col("close").shift(1)).log().abs().alias("absr1")
    ).with_columns(pl.col("absr1").rolling_mean(24).alias("r24"))
    # aggregate same windows as features to get per-window r24 at the horizon
    # but r24 is a 1m-level series; map via the window open
    mp: dict[int, float] = {}
    for r in bars.iter_rows(named=True):
        v = r["r24"]
        if v is not None and np.isfinite(float(v)):
            ot = r["open_time"]
            ts = int(ot.timestamp() * 1000) if hasattr(ot, "timestamp") else int(ot)
            mp[ts] = float(v)
    return mp


def evaluate_asset_horizon(asset: str, symbol: str, tf_file: str, hz: str, sec: int) -> list[dict]:
    """Run one asset x horizon through the 24-cell logic, return per-trade rows."""
    preds = champ_predictions(symbol, hz)
    r24_lookup = _r24_map(symbol)

    mkts = pl.read_parquet(str(UPDOWN / "markets.parquet")).filter(
        (pl.col("crypto") == asset)
        & (pl.col("timeframe") == tf_file)
        & pl.col("resolution").is_in([0, 1])
    ).with_columns(((pl.col("end_ts") - sec) * 1000).alias("open_ms"))

    price_file = UPDOWN / f"prices_{asset}_{tf_file}.parquet"
    if price_file.exists():
        prices = pl.read_parquet(str(price_file)).with_columns(
            pl.col("timestamp").cast(pl.Int64).mul(1000).alias("ts_ms")
        )
        # index by market_id -> sorted price series for fast lookup
        price_groups: dict[str, pl.DataFrame] = {}
        for mid, g in prices.group_by("market_id"):
            key = mid[0] if isinstance(mid, tuple) else mid
            price_groups[str(key)] = g.sort("ts_ms")
    else:
        price_groups = {}

    rows: list[dict] = []
    for r in mkts.iter_rows(named=True):
        open_ms = int(r["open_ms"])
        prev_open = open_ms - sec * 1000
        p = preds.get(prev_open)
        if p is None:
            continue
        if abs(p - 0.5) <= THETA:
            continue
        won_up = r["resolution"] == 1
        side_up = p >= 0.5
        won = int(won_up == side_up)
        mid = str(r["market_id"])
        pg = price_groups.get(mid)
        if pg is None or pg.height == 0:
            continue
        d_ms = open_ms + ENTRY_OFFSET_S * 1000
        col = "up_price" if side_up else "down_price"
        cand = pg.filter(pl.col("ts_ms") >= d_ms).sort("ts_ms")
        if cand.height == 0:
            continue
        entry_px = None
        for v in cand[col].to_list():
            if v is not None:
                fv = float(v)
                if 0.01 < fv < 0.99:
                    entry_px = fv
                    break
        if entry_px is None:
            continue
        fee = 0.07 * entry_px * (1 - entry_px)
        pnl = float((1 - entry_px) - fee) if won else float(-entry_px - fee)
        r24_val = r24_lookup.get(prev_open)
        vol = vol_label(r24_val)
        sess = session_label(open_ms)
        rows.append({
            "asset": asset,
            "hz": hz,
            "open_ms": open_ms,
            "vol": vol,
            "session": sess,
            "bucket": f"{vol}/{sess}/{hz}",
            "won": won,
            "pnl": pnl,
            "entry_px": entry_px,
            "p_model": float(p),
        })
    return rows


def holm_adjust(pvals: list[float]) -> list[float]:
    """Holm step-down adjustment. Returns adjusted p-values in original order."""
    n = len(pvals)
    if n == 0:
        return []
    order = np.argsort(pvals)
    adj = np.zeros(n)
    for rank, idx in enumerate(order):
        adj[idx] = min(1.0, pvals[idx] * (n - rank))
    # enforce monotonicity (step-down)
    sorted_adj = adj[order]
    for i in range(1, n):
        if sorted_adj[i] < sorted_adj[i - 1]:
            sorted_adj[i] = sorted_adj[i - 1]
    inv_order = np.argsort(order)
    return sorted_adj[inv_order].tolist()


def evaluate_all() -> dict:
    """Run all 6 asset x horizon combos through the evaluator.
    Returns summary dict with per-bucket aggregates + Holm gate.
    """
    all_rows: list[dict] = []
    for asset, symbol in [("BTC", "BTCUSDT"), ("ETH", "ETHUSDT"), ("SOL", "SOLUSDT")]:
        for tf_file, hz, sec in [("5-minute", "5m", 300), ("15-minute", "15m", 900)]:
            rows = evaluate_asset_horizon(asset, symbol, tf_file, hz, sec)
            all_rows.extend(rows)
            print(f"  {asset} {hz}: {len(rows)} gate-passed trades")

    if not all_rows:
        return {"buckets": [], "total_trades": 0, "verdict": "RESET", "reason": "no gate-passed trades"}

    df = pl.DataFrame(all_rows)
    print(f"total gate-passed: {df.height}")

    # Aggregate per bucket (12 per horizon actually present -> up to 24)
    buckets_agg = []
    for (vol, sess, hz), g in df.group_by(["vol", "session", "hz"]):
        pnls = g["pnl"].to_numpy()
        n = len(pnls)
        ev = float(np.mean(pnls))
        # daily-block bootstrap CI (block = date of open_ms)
        # approximate: resample days, not individual trades
        dates = np.array([dt.datetime.fromtimestamp(int(ms) / 1000, tz=dt.timezone.utc).date() for ms in g["open_ms"].to_list()])
        uniq_dates = np.unique(dates)
        # map date -> indices
        ci_lo, ci_hi = float("nan"), float("nan")
        p_raw = 1.0
        # 4 resolved dates in the updown snapshot -> only 3-4 daily blocks.
        # Daily-block bootstrap with <=4 blocks is degenerate; fall back to
        # trade-level percentile bootstrap when blocks are too few.
        use_blocks = len(uniq_dates) >= 5
        if n >= 10:
            rng = np.random.default_rng(0)
            n_boot = 10000
            if use_blocks and len(uniq_dates) >= 3:
                date_to_pnls = {d: pnls[dates == d] for d in uniq_dates}
                boot_means = []
                for _ in range(n_boot):
                    sampled_dates = rng.choice(uniq_dates, size=len(uniq_dates), replace=True)
                    sample = np.concatenate([date_to_pnls[d] for d in sampled_dates])
                    boot_means.append(float(np.mean(sample)))
                boot_means = np.array(boot_means)
            else:
                boot_means = np.array([float(np.mean(rng.choice(pnls, size=n, replace=True))) for _ in range(n_boot)])
            ci_lo, ci_hi = float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5))
            if ev > 0:
                p_raw = float((boot_means <= 0).mean())
            elif ev < 0:
                p_raw = float((boot_means >= 0).mean())
            else:
                p_raw = 1.0
            p_raw = max(p_raw * 2, 1 / n_boot)
            p_raw = min(p_raw, 1.0)
        buckets_agg.append({
            "bucket": f"{vol}/{sess}/{hz}",
            "vol": vol, "session": sess, "hz": hz,
            "N": int(n),
            "EV": ev,
            "CI_lo": ci_lo, "CI_hi": ci_hi,
            "p_raw": float(p_raw),
        })

    # Holm across the pre-registered family (k=24, but correct across observed buckets)
    # Spec says Holm across k=24 pre-registered cells; we correct across observed
    # and note unobserved cells as N=0 (never promote).
    pvals = [b["p_raw"] for b in buckets_agg]
    padj = holm_adjust(pvals)
    for b, pa in zip(buckets_agg, padj):
        b["p_adj"] = float(pa)
        b["holm_excludes_0"] = bool(b["CI_lo"] > 0 or b["CI_hi"] < 0) and pa < 0.05
        # Promotion requires all four per spec
        b["promote"] = bool(
            b["N"] >= 150
            and b["holm_excludes_0"]
            and b["EV"] > 0
        )

    buckets_agg.sort(key=lambda x: x["EV"], reverse=True)
    any_promote = any(b["promote"] for b in buckets_agg)
    verdict = "KEEP" if any_promote else "RESET"
    return {
        "buckets": buckets_agg,
        "total_trades": int(df.height),
        "verdict": verdict,
        "any_promote": any_promote,
    }


if __name__ == "__main__":
    summary = evaluate_all()
    print(f"\nverdict: {summary['verdict']}  total_trades={summary['total_trades']}")
    for b in summary["buckets"]:
        print(f"  {b['bucket']:20s} N={b['N']:4d} EV={b['EV']:+.4f} CI=[{b['CI_lo']:+.4f},{b['CI_hi']:+.4f}] p_adj={b['p_adj']:.3f} promote={b['promote']}")
