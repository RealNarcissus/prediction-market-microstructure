"""Regenerate the README figures from local research artifacts.

Reads (not redistributed in the repo):
  data/paper_wallet.db            live $5-controlled paper wallet ledger
  data/paper_gate.db              twin daemon ledger (independent replication)
  research/staleness/calibration_compare.parquet   tracked fair-value scores

Writes docs/img/*.png. Deterministic: bootstrap seed fixed below.

Figures:
  pnl_cumulative.png    cumulative realized PnL, both cohorts + verdict window
  ev_daily.png          per-day EV of the v2 cohort (dispersion, honest)
  backtest_vs_live.png  pre-live gated backtest EV vs realized live EV (95% CI)
  reliability.png       isotonic-calibrated probability vs empirical win rate
"""

from __future__ import annotations

import datetime
import sqlite3
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from research.staleness.retest_logspace import (  # noqa: E402
    FEE_RATE, PARQUET, SPLIT_MS, fit_lambda, sigmoid,
)

UTC = datetime.timezone.utc
IMG = REPO / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

W_START = datetime.datetime(2026, 9, 4, 15, 2, tzinfo=UTC)
W_END = datetime.datetime(2026, 9, 18, 15, 2, tzinfo=UTC)
SEED = 20260918
C_MAIN, C_NEG, C_POS, C_REF = "#4477AA", "#EE6677", "#228833", "#999999"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "savefig.bbox": "tight",
    "axes.grid": True, "grid.alpha": 0.25, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
})


def load_settled(db: str, gated: bool) -> list[tuple[int, int, int]]:
    c = sqlite3.connect(str(REPO / db))
    q = "SELECT entry_ts_ms, pnl_cents, won FROM trades WHERE status='settled'"
    if gated:
        q += " AND gate='v2'"
    q += " ORDER BY entry_ts_ms"
    rows = list(c.execute(q))
    c.close()
    return rows


def day_block_ci(rows, n_boot: int = 10_000) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    days: dict[str, list[int]] = {}
    for ts, pnl, _ in rows:
        key = datetime.datetime.fromtimestamp(ts / 1000, tz=UTC).date()
        days.setdefault(key, []).append(pnl)
    arrs = [np.array(v, dtype=float) for v in days.values()]
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(arrs), size=len(arrs))
        boots.append(np.concatenate([arrs[i] for i in idx]).mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(lo), float(hi)


def backtest_gated_ev() -> tuple[float, float, pl.DataFrame]:
    """Pre-live expectation: round-102 protocol on the tracked score parquet."""
    df = pl.read_parquet(str(PARQUET)).filter(pl.col("cfg") == "v2_ewma").sort("ts_ms")
    tr = df.filter(pl.col("ts_ms") < SPLIT_MS)
    te = df.filter(pl.col("ts_ms") >= SPLIT_MS)
    z_tr, won_tr = tr["z"].to_numpy(), tr["won"].to_numpy().astype(float)
    lam = fit_lambda(z_tr, won_tr)
    iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(z_tr / lam), won_tr)
    te = te.with_columns(pl.Series("prob", iso.predict(sigmoid(te["z"].to_numpy() / lam))))
    te = te.with_columns((FEE_RATE * pl.col("ask") * (1 - pl.col("ask"))).alias("fee"))
    gated = te.filter((pl.col("prob") - pl.col("ask")) > pl.col("fee")).with_columns(
        pl.when(pl.col("won") == 1)
        .then(1 - pl.col("ask") - pl.col("fee"))
        .otherwise(-pl.col("ask") - pl.col("fee"))
        .alias("ev")
    )
    rows = [(int(r["ts_ms"]), int(round(float(r["ev"]) * 100)), int(r["won"]))
            for r in gated.to_dicts()]
    return float(np.mean([r[1] for r in rows])), rows and day_block_ci(rows), te


def fig_pnl_cumulative(wallet) -> None:
    ts = [datetime.datetime.fromtimestamp(r[0] / 1000, tz=UTC) for r in wallet]
    cum = np.cumsum([r[1] for r in wallet]) / 100.0
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.axvspan(W_START, W_END, color=C_REF, alpha=0.15,
               label="pre-registered verdict window")
    ax.plot(ts, cum, color=C_MAIN, lw=1.4)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("entry time (UTC)")
    ax.set_ylabel("cumulative realized PnL (USD, 1 contract/trade)")
    ax.set_title("Paper wallet, 3,832 settled trades — v1 + v2 cohorts")
    ax.legend(loc="lower left", frameon=False)
    ax.margins(y=0.10)
    ymin, ymax = ax.get_ylim()
    for d, lbl in ((W_START, "gate v2 live"), (W_END, "verdict: FAILED")):
        ax.axvline(d, color=C_NEG, lw=1.0, ls="--")
        ax.text(d, ymin + 0.05 * (ymax - ymin), f" {lbl}", rotation=90,
                va="bottom", ha="right", fontsize=8, color=C_NEG)
    fig.savefig(IMG / "pnl_cumulative.png")
    plt.close(fig)


def fig_ev_daily(v2) -> None:
    days: dict[str, list[int]] = {}
    for r in v2:
        key = datetime.datetime.fromtimestamp(r[0] / 1000, tz=UTC).date()
        days.setdefault(key, []).append(r[1])
    ds = sorted(days)
    evs = [np.mean(days[d]) for d in ds]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(range(len(ds)), evs,
           color=[C_POS if e > 0 else C_NEG for e in evs], width=0.8)
    ax.axhline(0, color="black", lw=0.8)
    mean_all = np.mean([r[1] for r in v2])
    ax.axhline(mean_all, color=C_MAIN, lw=1.2,
               label=f"cohort mean {mean_all:+.2f}c/trade")
    step = max(1, len(ds) // 12)
    ax.set_xticks(range(0, len(ds), step))
    ax.set_xticklabels([d.isoformat() for d in ds[::step]], rotation=30, ha="right")
    ax.set_xlabel("entry day (UTC)")
    ax.set_ylabel("EV per trade (cents)")
    ax.set_title("v2 cohort daily EV — 15/50 days positive, no positive week sustained")
    ax.legend(loc="lower left", frameon=False)
    fig.savefig(IMG / "ev_daily.png")
    plt.close(fig)


def fig_backtest_vs_live(wallet, twin) -> None:
    bt_ev, (bt_lo, bt_hi), _ = backtest_gated_ev()
    pre_w = [r for r in wallet if r[0] < int(W_END.timestamp() * 1000)]
    pre_t = [r for r in twin if r[0] < int(W_END.timestamp() * 1000)]
    lo_w, hi_w = day_block_ci(pre_w)
    lo_t, hi_t = day_block_ci(pre_t)
    rows = [
        (f"backtest, gated test-span  (n large)", bt_ev, bt_lo, bt_hi, C_REF),
        (f"live paper wallet, window  (n={len(pre_w):,})", np.mean([r[1] for r in pre_w]), lo_w, hi_w, C_NEG),
        (f"twin daemon, window  (n={len(pre_t):,})", np.mean([r[1] for r in pre_t]), lo_t, hi_t, C_NEG),
    ]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    y = range(len(rows))
    for i, (lbl, ev, lo, hi, c) in enumerate(rows):
        ax.barh(i, ev, xerr=[[ev - lo], [hi - ev]], color=c, alpha=0.85,
                capsize=3, error_kw={"lw": 1.2})
        ax.text(hi + 0.3, i, f"{ev:+.2f}c  [{lo:+.2f}, {hi:+.2f}]", va="center", fontsize=8)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(list(y), [r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("EV per trade (cents), day-block bootstrap 95% CI")
    ax.set_title("The backtest edge did not survive live execution")
    fig.savefig(IMG / "backtest_vs_live.png")
    plt.close(fig)


def fig_reliability() -> None:
    df = pl.read_parquet(str(PARQUET)).filter(pl.col("cfg") == "v2_ewma").sort("ts_ms")
    tr = df.filter(pl.col("ts_ms") < SPLIT_MS)
    te = df.filter(pl.col("ts_ms") >= SPLIT_MS)
    z_tr, won_tr = tr["z"].to_numpy(), tr["won"].to_numpy().astype(float)
    lam = fit_lambda(z_tr, won_tr)
    iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(z_tr / lam), won_tr)

    def curve(z, won, n_bins=10):
        p = iso.predict(sigmoid(z / lam))
        edges = np.quantile(p, np.linspace(0, 1, n_bins + 1))
        xs, ys = [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (p >= lo) & (p <= hi if hi == edges[-1] else (p < hi))
            if m.sum() >= 500:
                xs.append(p[m].mean())
                ys.append(won[m].mean())
        return xs, ys

    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    ax.plot([0, 1], [0, 1], color=C_REF, lw=1, ls="--", label="perfect")
    xs, ys = curve(z_tr, won_tr)
    ax.plot(xs, ys, "o-", color=C_MAIN, label=f"train (n={tr.height:,})")
    z_te, won_te = te["z"].to_numpy(), te["won"].to_numpy().astype(float)
    xs, ys = curve(z_te, won_te)
    ax.plot(xs, ys, "s-", color=C_NEG, label=f"test (n={te.height:,})")
    ax.set_xlabel("calibrated P(win)")
    ax.set_ylabel("empirical win rate")
    ax.set_title("Isotonic calibration (v2_ewma fair, λ train-fit)")
    ax.legend(loc="upper left", frameon=False)
    fig.savefig(IMG / "reliability.png")
    plt.close(fig)


def main() -> None:
    wallet = load_settled("data/paper_wallet.db", gated=False)
    wallet_v2 = load_settled("data/paper_wallet.db", gated=True)
    twin = load_settled("data/paper_gate.db", gated=False)
    fig_pnl_cumulative(wallet)
    fig_ev_daily(wallet_v2)
    fig_backtest_vs_live(wallet_v2, twin)
    fig_reliability()
    for f in sorted(IMG.glob("*.png")):
        print(f"wrote {f} ({f.stat().st_size/1024:.0f} KiB)")


if __name__ == "__main__":
    main()
