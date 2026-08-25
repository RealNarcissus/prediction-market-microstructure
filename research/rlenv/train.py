"""RL training campaign: REINFORCE agent on the TWAP-epoch environment.

Walk-forward protocol (temporal discipline, mirroring the locked harness):
  TRAIN episodes: [2022-01-01, 2025-01-01)
  VALIDATION    : [2025-01-01, 2026-01-01) pooled
  SEALED        : >= 2026-01-01 — never loaded here

Usage:
  python research/rlenv/train.py --horizon 900 --iters 8 --episodes-per-iter 4000

Observations append to research/rlenv/OBSERVATIONS.jsonl and are summarized
in research/rlenv/LOG.md.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from agent import PolicyAgent
from env import build_windows, load_1m_bars

REPO_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(REPO_SRC))
from quantbtc.fees import order_fee  # noqa: E402

RESEARCH = Path(__file__).resolve().parents[1]
DATA_1M = (
    "/home/charleton/Desktop/agentProjects/Herdr/quant-btc/data/raw/"
    "btcusdt-usdtm-1m.parquet"
)
TRAIN_END = np.datetime64("2025-01-01")
VAL_END = np.datetime64("2026-01-01")


def play_episode(agent: PolicyAgent, ep: dict, greedy: bool) -> dict:
    """One episode. Returns metrics; performs learning if not greedy."""
    trajectory = []
    entered = False
    entry_step = None
    for step in ep["steps"]:
        s = step["feat"]
        a = agent.act(s, greedy=greedy or entered)
        R = 0.0
        if a in (1, 2) and not entered:
            entered = True
            entry_step = (a, step)
            fair = step["fair"]
            # BUGFIX: the Down side costs (1 - fair), not fair
            entry_price = fair if a == 1 else max(0.0, min(1.0, 1.0 - fair))
            fee = order_fee(entry_price, 1) / 1
            won = (a == 1 and ep["y_up"] == 1) or (a == 2 and ep["y_up"] == 0)
            R = ((1 - entry_price) - fee) if won else (-entry_price - fee)
            trajectory.append({"s": s, "a": a, "R": R})
            break  # one entry per episode; episode ends for the agent
        else:
            trajectory.append({"s": s, "a": a, "R": 0.0})
    if not greedy:
        agent.update_episode(trajectory)
    out = {
        "entered": entered,
        "side": ("up" if entry_step[0] == 1 else "down") if entry_step else None,
        "entry_min": (
            round((entry_step[1]["t_ms"] - ep["open_time_ms"]) / 60_000, 1)
            if entry_step else None
        ),
        "reward": (trajectory[-1]["R"] if entered else 0.0),
        "y_up": ep["y_up"],
    }
    return out


def fullinfo_steps(ep: dict) -> list[dict]:
    """All-minute steps with EX-POST rewards for every action.

    Once the window settles, the reward of entering up/down at any minute is
    fully determined (entry price = fair value known at decision time). This
    turns the optimal-stopping problem into a full-information contextual
    bandit — the statistically efficient way to learn the stopping map.
    """
    steps = []
    for step in ep["steps"]:
        fair = np.clip(step["fair"], 1e-4, 1 - 1e-4)
        up_won = ep["y_up"] == 1
        fee_up = order_fee(fair, 1)
        fee_dn = order_fee(1.0 - fair, 1)
        # Up side costs `fair`; Down side costs (1 - fair) — mirrored book
        r_up = ((1 - fair) - fee_up) if up_won else (-fair - fee_up)
        r_dn = (fair - fee_dn) if not up_won else (-(1.0 - fair) - fee_dn)
        steps.append(
            {"s": step["feat"], "r_skip": 0.0, "r_up": r_up, "r_down": r_dn}
        )
    return steps


def evaluate(agent: PolicyAgent, episodes: list[dict]) -> dict:
    rs, wins, entries = [], 0, 0
    for ep in episodes:
        o = play_episode(agent, ep, greedy=True)
        if o["entered"]:
            entries += 1
            wins += int((o["side"] == "up") == (o["y_up"] == 1))
            rs.append(o["reward"])
    ev = float(np.mean(rs)) if rs else 0.0
    lo = hi = ev
    if len(rs) > 30:
        rng = np.random.default_rng(0)
        boots = [
            float(np.mean(rng.choice(rs, size=len(rs), replace=True)))
            for _ in range(2000)
        ]
        lo, hi = float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
    return {
        "episodes": len(episodes),
        "entries": entries,
        "entry_rate": round(entries / max(1, len(episodes)), 4),
        "win_rate": round(wins / max(1, entries), 4) if entries else None,
        "ev_per_trade": round(ev, 4),
        "ev_ci95": [round(lo, 4), round(hi, 4)],
        "total_pnl": round(sum(rs), 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=900)
    ap.add_argument("--iters", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--hidden", type=int, default=24)
    ap.add_argument("--episodes-per-iter", type=int, default=4000)
    args = ap.parse_args()

    t0 = time.time()
    bars = load_1m_bars(DATA_1M)
    eps = build_windows(bars, horizon_s=args.horizon)
    train = [e for e in eps
             if e["open_time_ms"] < int(TRAIN_END.astype("datetime64[ms]").astype(int))]
    val = [e for e in eps
           if int(TRAIN_END.astype("datetime64[ms]").astype(int)) <= e["open_time_ms"]
           < int(VAL_END.astype("datetime64[ms]").astype(int))]
    print(f"episodes: train {len(train)}, val {len(val)} "
          f"({time.time()-t0:.0f}s to build)")

    agent = PolicyAgent(state_dim=len(train[0]["steps"][0]["feat"]),
                        hidden=args.hidden, lr=args.lr, seed=args.seed)

    # honest checkpointing: model SELECTION uses only val-H1 (2025 H1);
    # the reported number comes from val-H2 (2025 H2), never seen during
    # selection. Without this, picking best-of-N iterations overfits val.
    mid_2025 = int(np.datetime64("2025-07-01").astype("datetime64[ms]").astype(int))
    val_h1 = [e for e in val if e["open_time_ms"] < mid_2025]
    val_h2 = [e for e in val if e["open_time_ms"] >= mid_2025]

    obs_dir = RESEARCH / "rlenv"
    obs_dir.mkdir(exist_ok=True)
    obs_path = obs_dir / "OBSERVATIONS.jsonl"

    # pre-training validation baseline (untrained policy)
    base_val = evaluate(agent, val)

    rng = np.random.default_rng(args.seed + 1)
    history = []
    best_sel_ev = float("-inf")
    best_snapshot = None
    for it in range(1, args.iters + 1):
        t_it = time.time()
        batch = rng.choice(len(train), size=min(args.episodes_per_iter, len(train)),
                           replace=False)
        for bi in batch:
            agent.update_fullinfo(fullinfo_steps(train[int(bi)]))
        rewards = []  # greedy train sample for monitoring
        for bi in batch[:500]:
            o = play_episode(agent, train[int(bi)], greedy=True)
            rewards.append(o["reward"])
        val_metrics = evaluate(agent, val)
        sel = evaluate(agent, val_h1)  # SELECTION metric (2025 H1 only)
        if sel["ev_per_trade"] > best_sel_ev:
            best_sel_ev = sel["ev_per_trade"]
            best_snapshot = {k: v2.copy() for k, v2 in agent.__dict__.items()
                             if isinstance(v2, np.ndarray)}
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "iter": it,
            "train_mean_reward": round(float(np.mean(rewards)), 4),
            "train_entry_rate": round(float(np.mean([r != 0 for r in rewards])), 4),
            "val": val_metrics,
            "val_h1_select_ev": sel["ev_per_trade"],
            "secs": round(time.time() - t_it, 1),
            "config": {"horizon_s": args.horizon, "seed": args.seed,
                       "lr": args.lr, "hidden": args.hidden},
        }
        history.append(rec)
        with open(obs_path, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        v = val_metrics
        print(f"iter {it:3d} | train R {rec['train_mean_reward']:+.4f} "
              f"(enter {rec['train_entry_rate']:.0%}) | VAL entries "
              f"{v['entries']}/{v['episodes']} win {v['win_rate']} "
              f"EV {v['ev_per_trade']:+.4f} CI {v['ev_ci95']} "
              f"| {rec['secs']}s")

    print("\nBASELINE (untrained):", json.dumps(base_val))
    print("BEST VAL EV (biased — selected on same set):",
          max([h["val"]["ev_per_trade"] for h in history], default=None))
    if best_snapshot is not None:
        for k, v2 in best_snapshot.items():
            setattr(agent, k, v2)
        rep_h1 = evaluate(agent, val_h1)
        rep_h2 = evaluate(agent, val_h2)
        print("HONEST CHECKPOINT (selected on 2025-H1):")
        print("  selection half (H1):", json.dumps(rep_h1))
        print("  reporting half (H2):", json.dumps(rep_h2))
        np.savez(RESEARCH / "rlenv" / "best_policy.npz",
                 **{k: v for k, v in best_snapshot.items()})
        print("policy -> research/rlenv/best_policy.npz")
    print("observations ->", obs_path)


if __name__ == "__main__":
    main()
