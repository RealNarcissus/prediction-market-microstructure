"""Characterize the best RL checkpoint's entries: WHEN it enters, at WHAT
fair prices, and bucketed EV — the external-validity picture."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agent import PolicyAgent  # noqa: E402
from env import build_windows, load_1m_bars  # noqa: E402
from train import DATA_1M  # noqa: E402

snap = np.load(Path(__file__).resolve().parents[1] / "rlenv" / "best_policy.npz")
agent = PolicyAgent(state_dim=snap["W1"].shape[1], hidden=snap["W1"].shape[0],
                    lr=1e-9, seed=999)
for k in snap.files:
    setattr(agent, k, snap[k])

bars = load_1m_bars(DATA_1M)
eps = build_windows(bars, horizon_s=900)
mid = int(np.datetime64("2025-07-01").astype("datetime64[ms]").astype(int))
val_h2 = [e for e in eps
          if int(np.datetime64("2025-07-01").astype("datetime64[ms]").astype(int))
          <= e["open_time_ms"]
          < int(np.datetime64("2026-01-01").astype("datetime64[ms]").astype(int))]

entry_min, entry_fair, wins = [], [], []
side_counts = {"up": 0, "down": 0}
buckets = {}
for ep in val_h2[:6000]:
    o = None
    for step in ep["steps"]:
        s = step["feat"]
        a = agent.act(s, greedy=True)
        if a in (1, 2):
            side = "up" if a == 1 else "down"
            won = (a == 1) == (ep["y_up"] == 1)
            f = step["fair"]
            b = round(f * 10) / 10
            buckets.setdefault(b, []).append(won)
            entry_min.append((step["t_ms"] - ep["open_time_ms"]) / 60_000)
            entry_fair.append(f)
            wins.append(1 if won else 0)
            side_counts[side] += 1
            break

print(f"episodes sampled: {min(6000, len(val_h2))} | entries: {len(entry_fair)}")
print(f"entry minute: median {np.median(entry_min):.0f}, p10 {np.percentile(entry_min,10):.0f}, p90 {np.percentile(entry_min,90):.0f}")
print(f"entry fair value: median {np.median(entry_fair):.3f}, p10 {np.percentile(entry_fair,10):.3f}, p90 {np.percentile(entry_fair,90):.3f}")
print("sides:", side_counts)
print("\nEV by entry-fair bucket (bucket | n | win rate | avg |win-payout asymmetry|):")
for b in sorted(buckets):
    w = buckets[b]
    print(f"  F~{b:.1f}: n={len(w):5d} win={sum(w)/len(w):.1%}")
