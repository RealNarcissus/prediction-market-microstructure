"""BOCPD over per-minute flow bias — first detector for the feature-bakeoff lane.

Feature-bakeoff discipline (round 208, brti-edge): candidate features must be
scored PROSPECTIVELY against settlement before any live use. This module
implements detector #1 (rounds 210-211): Bayesian Online Changepoint Detection
(Adams & MacKay 2007, Gaussian sufficient-statistics variant) run over the
per-minute taker-buy flow bias

    bias_t = (taker_buy_volume_t - volume_t / 2) / volume_t

computed from the Binance 1m klines we already store. Signed order flow is the
raw material for the flow-bias regimes the Moret & Lillo RL-MM (2609.11614)
and Jebali BOCPD (2609.07989) papers both key on.

Outputs (research-only; nothing here touches any live gate):
  - per-minute run-length distribution summary
  - detected break timestamps (posterior run-length drops below threshold)
  - pre/post-break bias means, for a first look at whether breaks segment
    the tape into materially different flow regimes

CLI:
    .venv/bin/python research/staleness/bocpd.py [--symbol BTCUSDT] [--days 30]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "data" / "raw"
OUT = REPO / "research" / "staleness" / "BOCPD_FLOWBIAS.md"

HAZARD = 1.0 / 250.0        # expected run length ~250 minutes
MAX_RUNS = 500              # truncate the run-length grid (Adams-MacKay pruning)
MU0_KAPPA = 1.0             # prior strength on the bias mean
MU0 = 0.0                   # prior mean: no directional bias
ALPHA0 = 2.0                # prior dof for the variance
BETA0 = 1e-4                # prior scale (bias is O(0.1), so tight-ish)
BREAK_THRESHOLD = 0.5       # P(break) at minute t = P(run_length == 0 | data)


def load_flow_bias(symbol: str, days: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-minute flow bias and timestamps from stored 1m klines."""
    import polars as pl

    d = RAW / symbol / "kline_1m"
    files = sorted(d.glob("*.parquet"))[-max(1, days // 2):]
    if not files:
        raise SystemExit(f"no kline files under {d}")
    df = pl.concat([pl.read_parquet(str(f)) for f in files])
    need = {"ts_ms", "volume"}
    missing = need - set(df.columns)
    if not ("taker_buy_volume" in df.columns or "taker_buy_base_volume" in df.columns):
        missing.add("taker_buy_base_volume")
    if missing:
        raise SystemExit(f"kline schema missing {missing}; have {df.columns}")
    df = df.sort("ts_ms").unique(subset=["ts_ms"], keep="last", maintain_order=True)
    tb_col = "taker_buy_volume" if "taker_buy_volume" in df.columns else "taker_buy_base_volume"
    vol = df["volume"].to_numpy().astype(float)
    tb = df[tb_col].to_numpy().astype(float)
    ts = df["ts_ms"].to_numpy().astype(np.int64)
    ok = np.isfinite(vol) & np.isfinite(tb) & (vol > 0)
    bias = np.full(len(vol), np.nan)
    bias[ok] = (tb[ok] - vol[ok] / 2.0) / vol[ok]
    m = np.isfinite(bias)
    return bias[m], ts[m]


def bocpd_gaussian(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Adams-MacKay BOCPD with Gaussian mean/variance posterior (NIG prior).

    Returns (P(run_length==0) per step, E[run_length] per step).
    """
    from scipy.special import gammaln

    n = len(x)
    kappa = np.array([MU0_KAPPA])
    mu = np.array([MU0])
    alpha = np.array([ALPHA0])
    beta = np.array([BETA0])
    log_R = np.array([0.0])
    R0 = np.zeros(n)
    Rmean = np.zeros(n)

    for t in range(n):
        # Student-t predictive log-prob under each candidate run (current stats)
        df = 2.0 * alpha
        scale2 = (beta * (1.0 + 1.0 / kappa)) / alpha
        z = (x[t] - mu) / np.sqrt(scale2)
        log_pred = (
            gammaln((df + 1) / 2) - gammaln(df / 2)
            - 0.5 * np.log(df * np.pi * scale2)
            - ((df + 1) / 2) * np.log1p(z * z / df)
        )
        # growth of existing runs + mass for a fresh run
        log_growth = log_R + log_pred + np.log(1.0 - HAZARD)
        log_new = np.log(HAZARD) + np.logaddexp.reduce(log_R + log_pred)
        log_R_new = np.concatenate([[log_new], log_growth])

        # pad stats: slot 0 is the fresh run (prior), slots 1.. keep old stats
        kappa = np.concatenate([[MU0_KAPPA], kappa])
        mu = np.concatenate([[MU0], mu])
        alpha = np.concatenate([[ALPHA0], alpha])
        beta = np.concatenate([[BETA0], beta])

        # prune all together
        if len(log_R_new) > MAX_RUNS:
            order = np.argsort(log_R_new)[::-1][:MAX_RUNS]
            log_R_new, kappa, mu, alpha, beta = (
                log_R_new[order], kappa[order], mu[order], alpha[order], beta[order])

        # normalize
        log_R_new -= np.logaddexp.reduce(log_R_new)
        R = np.exp(log_R_new)

        # normal-gamma update with x[t] for every surviving run
        kappa_new = kappa + 1.0
        mu = mu + (x[t] - mu) / kappa_new
        alpha = alpha + 0.5
        beta = beta + 0.5 * kappa * (x[t] - mu) ** 2 / kappa_new
        kappa = kappa_new

        R0[t] = R[0]
        Rmean[t] = float((R * np.arange(len(R))).sum())
        log_R = log_R_new

    return R0, Rmean


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--snapshot", action="store_true",
                    help="read from the persistent flow-bias snapshot "
                         "(data/flowbias_<sym>.parquet) instead of the "
                         "rolling kline store — accumulated history")
    args = ap.parse_args()

    if args.snapshot:
        import polars as pl

        snap = REPO / "data" / f"flowbias_{args.symbol}.parquet"
        if not snap.exists():
            print(f"FATAL: {snap} missing — run flowbias_snapshot.py first",
                  file=sys.stderr)
            sys.exit(2)
        df = pl.read_parquet(str(snap))
        bias = df["bias"].to_numpy()
        ts = df["ts_ms"].to_numpy()
    else:
        bias, ts = load_flow_bias(args.symbol, args.days)
    # clip extreme bias values (thin-volume minutes) to keep the Student-t sane
    lo, hi = np.quantile(bias, [0.001, 0.999])
    bias = np.clip(bias, lo, hi)

    R0, Rmean = bocpd_gaussian(bias)
    breaks = np.where(R0 > BREAK_THRESHOLD)[0]

    lines = [
        f"# BOCPD flow-bias detector — {args.symbol}",
        "",
        f"minutes analyzed: {len(bias):,}  "
        f"({ts[0]} .. {ts[-1]})",
        f"bias mean {bias.mean():+.4f}  sd {bias.std():.4f}  "
        f"(taker-buy share minus 0.5, per 1m bar)",
        f"hazard {HAZARD}  (prior mean run ~{1/HAZARD:.0f} min)",
        f"breaks detected (P(run==0) > {BREAK_THRESHOLD}): {len(breaks)}",
        f"mean run length (posterior): {Rmean.mean():.1f} min",
        "",
    ]
    if len(breaks):
        lines.append("| break index | ts (UTC) | P(break) |")
        lines.append("|---|---|---|")
        import datetime

        for b in breaks[:20]:
            utc = datetime.datetime.fromtimestamp(
                int(ts[b]) / 1000, tz=datetime.timezone.utc
            ).strftime("%Y-%m-%d %H:%M")
            lines.append(f"| {b} | {utc} | {R0[b]:.3f} |")
        # pre/post break bias contrast for the first 10 breaks
        lines.append("")
        lines.append("## pre/post-break bias contrast (first 10 breaks, +-60 min window)")
        for b in breaks[:10]:
            pre = bias[max(0, b - 60):b]
            post = bias[b:b + 60]
            if len(pre) >= 20 and len(post) >= 20:
                lines.append(
                    f"- break@{b}: pre {pre.mean():+.4f} -> post {post.mean():+.4f} "
                    f"(delta {post.mean() - pre.mean():+.4f})"
                )
    else:
        lines.append("no breaks above threshold — flow bias is regime-stable "
                     "at this hazard over the scanned window")
    lines.append("")
    lines.append("NEXT (bakeoff discipline, round-208): score conditional gate EV")
    lines.append("inside vs outside break windows PROSPECTIVELY before any gate use.")

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
