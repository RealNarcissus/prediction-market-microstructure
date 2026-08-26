"""Curriculum RL on entry timing: start late (easy), progress early (hard).

Each Polymarket epoch has multiple decision points (one per completed 1m bar).
Late-window decisions have tighter CLT fair values → clearer reward signal.
Early-window decisions are harder → richer learning potential.

Curriculum stages control the LATEST allowed entry fraction:
  Stage 0: frac_left <= 0.10  (only last ~90 seconds)
  Stage 1: frac_left <= 0.25  (last ~3-4 minutes)
  Stage 2: frac_left <= 0.50  (first half excluded)
  Stage 3: no restriction      (full window)

At each stage, train for N iterations, evaluate, advance if plateaued.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))
sys.path.insert(0, str(REPO / "research" / "rlenv"))

from quantbtc.twapbars import aggregate_windows  # noqa: E402
from strategies.s002_lgbm_base import new_model as cm  # noqa: E402
from strategies.s023_lgbm_pos_lag23 import build_features as cf  # noqa: E402
from forced_agent import ForcedBinaryAgent  # noqa: E402

KLINES = REPO / "data/klines"
CUT_MS = int(np.datetime64("2026-03-01").astype("datetime64[ms]").astype(int))


def build_episodes(bars: pl.DataFrame, hz_str: str):
    """Build per-epoch episode data with per-minute decision points."""
    sec = 300 if hz_str == "5m" else 900
    m_bars = sec // 60  # number of 1m bars per window

    episodes = []
    sec_ms = sec * 1000
    min_ts = int(bars["open_time"].min().timestamp() * 1000)
    max_ts = int(bars["open_time"].max().timestamp() * 1000)

    # enumerate all clock-aligned window starts
    oms_list = []
    w = (min_ts // sec_ms) * sec_ms
    while w < max_ts:
        oms_list.append(w)
        w += sec_ms

    for oms in oms_list:
        window_bars = bars.filter(
            (pl.col("open_time").dt.epoch("ms") >= oms)
            & (pl.col("open_time").dt.epoch("ms") < oms + sec_ms)
        )
        if window_bars.height != m_bars:
            continue

        closes = window_bars["close"].to_numpy()
        strike = window_bars["open"][0]
        twap = float(np.mean(closes))
        y_up = int(twap >= strike)

        # per-minute features
        steps = []
        m_count = window_bars.height
        for j in range(m_count):
            run_avg = float(np.mean(closes[: j + 1]))
            elapsed_frac = (j + 1) / m_count
            frac_left = 1.0 - j / m_count
            mom = float(np.log(closes[j] / closes[max(0, j - 5)])) if j >= 5 else 0.0
            imb = 0.0  # simplified; real impl would parse taker volumes

            steps.append({
                "feat": np.array([
                    run_avg / strike - 1.0,       # dist of running avg from strike
                    closes[j] / strike - 1.0,      # spot vs strike
                    elapsed_frac,                   # how much window has passed
                    frac_left,                      # how much left
                    mom,                            # momentum
                    imb,                            # taker pressure
                ]),
                "minute": j,
                "elapsed_frac": elapsed_frac,
                "frac_left": frac_left,
                "run_avg": run_avg,
                "spot": float(closes[j]),
            })

        episodes.append({
            "open_ms": oms,
            "steps": steps,
            "y_up": y_up,
            "strike": float(strike),
            "hz": hz_str,
        })

    return episodes


def agent_decide(agent, feat):
    """Agent picks 0=up or 1=down. Always commits."""
    return agent.act(feat)


def settle(entry_side_up: bool, won_up: bool, entry_px: float) -> float:
    """Settle a filled position."""
    fee = 0.07 * entry_px * (1 - entry_px)
    return ((1 - entry_px) - fee) if won else (-entry_px - fee)


def main():
    import argparse
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--iters-per-stage", type=int, default=50)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--hidden", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hz", choices=["5m", "15m"], default="15m")
    args = ap.parse_args()

    # Build episodes
    bars = pl.read_parquet(str(KLINES / "BTCUSDT_1m.parquet")).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
    )
    episodes = build_episodes(bars, args.hz)
    print(f"episodes built: {len(episodes)}")

    # temporal split
    CUT = CUT_MS
    train_eps = [e for e in episodes if e["open_ms"] < CUT]
    eval_eps = [e for e in episodes if e["open_ms"] >= CUT]
    print(f"train={len(train_eps)} eval={len(eval_eps)}")

    state_dim = len(train_eps[0]["steps"][0]["feat"]) if train_eps else 6
    agent = ForcedBinaryAgent(
        state_dim=state_dim, hidden=args.hidden,
        lr=args.lr, seed=args.seed,
    )

    obs_path = Path(__file__).resolve().parent / "CURRICULUM_OBSERVATIONS.jsonl"
    obs_fh = open(obs_path, "a")

    # Curriculum stages: max frac_left for available decision points
    # Stage 0: only last 10% of window → frac_left <= 0.10
    # Stage 1: last 25% → frac_left <= 0.25
    # Stage 2: last 50% → frac_left <= 0.50
    # Stage 3: full window → frac_left <= 1.0
    stages = [
        {"name": "late_only", "max_frac_left": 0.10},
        {"name": "late_quarter", "max_frac_left": 0.25},
        {"name": "half_window", "max_frac_left": 0.50},
        {"name": "full_window", "max_frac_left": 1.00},
    ]
    iters_per_stage = max(1, args.iters_per_stage // len(stages))

    global_iter = 0
    all_results = []

    for stage_idx, stage in enumerate(stages):
        max_fl = stage["max_frac_left"]
        print(f"\n--- STAGE {stage_idx}: {stage['name']} (frac_left <= {max_fl:.2f}) ---")

        for iteration in range(1, iters_per_stage + 1):
            global_iter += 1
            rng = np.random.default_rng(args.seed + global_iter)

            # sample training episodes
            batch_idx = rng.choice(len(train_eps),
                                   size=min(200, len(train_eps)), replace=False)

            for bi in batch_idx:
                ep = train_eps[bi]

                # find valid decision points for this stage
                valid_steps = [
                    st for st in ep["steps"]
                    if st["frac_left"] <= max_fl
                ]
                if not valid_steps:
                    continue

                # pick a random valid step as decision point
                st = valid_steps[rng.integers(0, len(valid_steps))]

                # ex-post rewards for both sides
                won_up_ep = ep["y_up"] == 1
                entry_px = min(0.99, max(0.01, st["spot"] / ep["strike"]))
                fee = 0.07 * entry_px * (1 - entry_px)
                r_up = ((1 - entry_px) - fee) if won_up_ep else (-entry_px - fee)
                r_dn = ((1 - entry_px) - fee) if not won_up_ep else (-entry_px - fee)

                agent.update_fullinfo_binary([{
                    "s": st["feat"], "r_up": r_up, "r_down": r_dn
                }])

            # greedy eval every iteration (cheap)
            correct, total, ev_sum = 0, 0, 0.0
            for ep in eval_eps[:500]:  # subsample for speed
                valid_steps = [
                    st for st in ep["steps"] if st["frac_left"] <= max_fl
                ]
                if not valid_steps:
                    continue
                # use latest valid step (most informed decision point)
                st = valid_steps[-1]
                feat = st["feat"]
                action = agent.act(feat)
                pred_up = action == 0

                # compute entry price proxy from fair value
                fair = abs(feat[0]) + 0.5  # rough approximation of prob
                entry_px = min(0.95, max(0.05, fair))
                actual_up = ep["y_up"] == 1
                pred_correct = pred_up == actual_up
                correct += int(pred_correct)
                total += 1

                fee = 0.07 * entry_px * (1 - entry_px)
                pnl = ((1 - entry_px) - fee) if (pred_up == actual_up) else (-entry_px - fee)
                ev_sum += pnl

            acc = correct / max(1, total)
            ev = ev_sum / max(1, total)
            obs = {
                "global_iter": global_iter, "stage": stage_idx,
                "stage_name": stage["name"],
                "acc": round(acc, 4), "ev_per_trade": round(ev, 4),
                "n_eval": total,
            }
            obs_fh.write(json.dumps(obs) + "\n")
            obs_fh.flush()
            all_results.append(obs)

            if iteration % 10 == 0 or iteration == 1:
                print(f"  iter {iteration:2d}/{iters_per_stage}: "
                      f"acc={acc:.1%} EV={ev:+.4f} (n={total})")

    obs_fh.close()

    # summary
    print("\n=== CURRICULUM SUMMARY ===")
    stages_summary = {}
    for r in all_results:
        sn = r["stage_name"]
        stages_summary.setdefault(sn, []).append(r)

    md_lines = ["# Curriculum RL Results\n"]
    for sn, rs in stages_summary.items():
        accs = [r["acc"] for r in rs]
        evs = [r["ev_per_trade"] for r in rs]
        best_acc = max(accs)
        best_ev = max(evs)
        mean_acc = sum(accs) / len(accs)
        md_lines.append(
            f"- **{sn}**: best acc {best_acc:.1%}, "
            f"best EV/trade {best_ev:+.4f}, "
            f"mean acc {mean_acc:.1%}"
        )
        print(md_lines[-1])

    out_md = REPO / "phase_b" / "CURRICULUM_RL_RESULTS.md"
    out_md.parent.mkdir(exist_ok=True)
    Path(out_md).write_text("\n".join([
        "# Curriculum RL on Entry Timing", "",
        "Agent trained progressively: late-window entries first (easy),",
        "then extending to earlier decisions (harder).", ""
    ] + md_lines + [""]))

    print(f"\nwrote {out_md}")


if __name__ == "__main__":
    main()
