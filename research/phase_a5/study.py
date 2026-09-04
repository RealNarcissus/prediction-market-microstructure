"""Phase A.5: does the Phase-A champion survive the Jupiter-style TWAP
label, and what is its expected value per trade at open prices with fees?

Method (no Jupiter data used — pure spot proxy):
- Rebuild 5m/15m windows from the Herdr 1m dataset with BOTH labels
  (endpoint = what Phase A trained on; TWAP = what Jupiter pays on).
- Train the champion feature set + LGBM walk-forward on the SAME locked
  quarterly folds, against TWAP labels.
- Simulate entry at epoch OPEN at 0.50 (justified: early quotes hug 50/50
  per SSRN 6863546), fee = order_fee(0.50, n) per Jupiter's formula.
- Strategies: always-up, model-sign, and selective |p-0.5|>theta.
- Block bootstrap (daily blocks) 95% CI on mean EV per trade.

Output: research/phase_a5/REPORT.md + console summary.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl

RESEARCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH))

from locked import folds as locked_folds  # noqa: E402
from strategies.s023_lgbm_pos_lag23 import build_features as champ_features  # noqa: E402
from strategies.s002_lgbm_base import new_model as champ_model  # noqa: E402
from quantbtc.config import load_config  # noqa: E402
from quantbtc.fees import order_fee  # noqa: E402
from quantbtc.twapbars import aggregate_windows, label_disagreement, load_1m  # noqa: E402

FEE_PER_CONTRACT = order_fee(0.50, 1) / 1  # 0.0175 at p=0.5


def walk_forward_pooled(agg: pl.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pooled out-of-sample model probabilities on the 2025 validation folds.

    Label semantics match the locked harness: features of COMPLETED window t
    predict window t+1's TWAP outcome (at epoch open, the last finished
    window is all you know). y_twap is therefore shifted by one window.
    Returns (p, y, open_time) for pooled validation rows only.
    """
    agg = agg.with_columns(
        pl.col("y_twap").shift(-1).alias("y_next"),
        pl.col("open_time").shift(-1).alias("t_next"),
    ).drop_nulls(["y_next"])
    X = champ_features(agg)
    y = agg["y_next"].to_numpy().astype(int)
    ts = agg["t_next"].to_list()
    finite = np.isfinite(X).all(axis=1)
    p = np.zeros(len(y))
    mask = np.zeros(len(y), dtype=bool)
    for fold in locked_folds.get_validation_folds(agg):
        tr = np.array([i for i in fold.train_idx if finite[i]], dtype=int)
        va = np.array([i for i in fold.val_idx if finite[i]], dtype=int)
        model = champ_model()
        model.fit(X[tr], y[tr])
        proba = model.predict_proba(X[va])
        p[va] = proba[:, list(model.classes_).index(1)]
        mask[va] = True
    return p[mask], y[mask], np.array(ts)[mask]


def simulate_ev(p: np.ndarray, y: np.ndarray, theta: float | None) -> dict:
    """EV per contract, buying UP/DOWN at 0.50 by model sign, optional gate."""
    edge = p - 0.5
    choose_up = edge >= 0
    gate = np.ones(len(p), dtype=bool) if theta is None else np.abs(edge) > theta
    idx = np.flatnonzero(gate)
    if len(idx) == 0:
        return {"n": 0, "ev_mean": float("nan"), "ci_lo": float("nan"),
                "ci_hi": float("nan"), "win_rate": float("nan")}
    win = np.where(choose_up[idx], y[idx] == 1, y[idx] == 0)
    pnl = np.where(win, 0.5 - FEE_PER_CONTRACT, -0.5 - FEE_PER_CONTRACT)
    lo, hi = daily_block_bootstrap(pnl, np.array(ts_val)[idx])
    return {
        "n": int(len(idx)),
        "ev_mean": float(pnl.mean()),
        "ci_lo": lo, "ci_hi": hi,
        "win_rate": float(win.mean()),
    }


def daily_block_bootstrap(pnl: np.ndarray, ts, n_boot: int = 10_000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(ts, dtype="datetime64[s]")
    days = arr.astype("datetime64[D]")
    uniq = np.unique(days)
    by_day = {d: pnl[days == d] for d in uniq}
    means = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        sample = np.concatenate([by_day[d] for d in pick])
        means[b] = sample.mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def mcc_of(p: np.ndarray, y: np.ndarray) -> float:
    from sklearn.metrics import matthews_corrcoef

    return float(matthews_corrcoef(y, (p >= 0.5).astype(int)))


def main() -> None:
    global ts_val
    cfg = load_config()
    bars = load_1m(
        "/home/charleton/Desktop/agentProjects/Herdr/quant-btc/data/raw/"
        "btcusdt-usdtm-1m.parquet"
    )
    out_dir = RESEARCH / "phase_a5"
    out_dir.mkdir(exist_ok=True)
    lines = ["# Phase A.5 — TWAP-label reality check & EV-at-open", ""]

    for hz in ("5m", "15m"):
        agg_all = aggregate_windows(bars, hz)
        # respect the seal exactly like the locked harness
        seal = datetime(2026, 1, 1, tzinfo=timezone.utc)
        agg = agg_all.filter(pl.col("open_time") < seal)
        dis = label_disagreement(agg)
        p, y, ts_val = walk_forward_pooled(agg)
        mcc_twap = mcc_of(p, y)
        lines += [
            f"## {hz}",
            "",
            f"- endpoint-vs-TWAP label disagreement: **{dis:.1%}** "
            "(windows where what Phase A trained on != what Jupiter pays)",
            f"- champion MCC on TWAP labels (walk-forward val 2025): "
            f"**{mcc_twap:+.4f}**",
            f"- fee per contract at 0.50 entry: ${FEE_PER_CONTRACT:.4f}",
            "",
            "| strategy | trades | win rate | EV/trade | 95% CI |",
            "|---|---|---|---|---|",
        ]
        for name, theta in (
            ("always-up (theta=None baseline)", None),
            ("model-sign", None),
            ("model-sign theta=0.02", 0.02),
            ("model-sign theta=0.05", 0.05),
            ("model-sign theta=0.10", 0.10),
        ):
            if name.startswith("always"):
                # always-up: no model, entry every window
                win = y == 1
                pnl = np.where(
                    win, 0.5 - FEE_PER_CONTRACT, -0.5 - FEE_PER_CONTRACT
                )
                lo, hi = daily_block_bootstrap(pnl, ts_val)
                r = {"n": len(pnl), "ev_mean": float(pnl.mean()),
                     "ci_lo": lo, "ci_hi": hi, "win_rate": float(win.mean())}
            else:
                r = simulate_ev(p, y, theta)
            lines.append(
                f"| {name} | {r['n']} | {r['win_rate']:.3f} | "
                f"{r['ev_mean']:+.4f} | [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] |"
            )
        lines.append("")

    (out_dir / "REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
