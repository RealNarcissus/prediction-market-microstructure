"""Entry-forced RL: agent must pick Up or Down every epoch. No skip."""
import json, sys, time
from pathlib import Path
import numpy as np, polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "research"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from quantbtc.twapbars import aggregate_windows
from strategies.s002_lgbm_base import new_model as cm
from strategies.s023_lgbm_pos_lag23 import build_features as cf
from forced_agent import ForcedBinaryAgent

KL = REPO / "data/klines"
CUT = int(np.datetime64("2026-03-01").astype("datetime64[ms]").astype(int))


def main():
    import argparse
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--iters", type=int, default=300)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hz", choices=["5m", "15m"], default="15m")
    args = ap.parse_args()

    # Build dataset from klines
    bars = pl.read_parquet(str(KL / "BTCUSDT_1m.parquet")).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC")))
    agg = aggregate_windows(bars, args.hz)
    agg = agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next")).drop_nulls(["y_next"])
    X = cf(agg)
    y = agg["y_next"].to_numpy().astype(int)
    fin = np.isfinite(X).all(axis=1)
    opens = agg["open_time"].dt.epoch("ms").to_numpy()[fin]
    X = X[fin]; y = y[fin]

    tr_mask = opens < CUT
    ev_mask = opens >= CUT
    print(f"train={tr_mask.sum()} eval={ev_mask.sum()}")

    state_dim = X.shape[1]
    agent = ForcedBinaryAgent(state_dim=state_dim, hidden=args.hidden,
                              lr=args.lr, seed=args.seed)

    obs_path = Path(__file__).resolve().parent / "FORCED_OBSERVATIONS.jsonl"
    best_acc = 0.0; best_iter = 0

    for iteration in range(1, args.iters + 1):
        t0 = time.time()

        # Sample training batch
        rng = np.random.default_rng(args.seed + iteration)
        batch_idx = rng.choice(np.flatnonzero(tr_mask),
                               size=min(200, int(tr_mask.sum())), replace=False)

        # Full-info update: ex-post rewards for both sides
        for wi in batch_idx:
            won_up = y[wi] == 1
            fee = 0.07 * 0.5 * 0.5  # at mid entry
            r_up = ((1 - 0.5) - fee) if won_up else (-0.5 - fee)
            r_dn = ((1 - 0.5) - fee) if not won_up else (-0.5 - fee)
            agent.update_fullinfo_binary([{"s": X[wi], "r_up": r_up, "r_down": r_dn}])

        # Greedy evaluation on holdout
        correct = 0
        total_pnl = 0.0
        n_ev = int(ev_mask.sum())
        ev_indices = np.flatnonzero(ev_mask)
        for wi in ev_indices:
            action = agent.act(X[wi])  # 0=up, 1=down
            pred_up = action == 0
            actual_up = y[wi] == 1
            if pred_up == actual_up:
                correct += 1
            entry = 0.50
            fee = 0.07 * entry * (1 - entry)
            pnl = ((1 - entry) - fee) if (pred_up == actual_up) else (-entry - fee)
            total_pnl += pnl

        acc = correct / max(1, len(ev_indices))
        obs = {"iter": iteration, "acc": round(acc, 4), "pnl": round(total_pnl, 2)}
        with open(obs_path, "a") as fh:
            fh.write(json.dumps(obs) + "\n")

        if acc > best_acc:
            best_acc = acc; best_iter = iteration
        if iteration % 25 == 0 or iteration <= 3:
            print(f"iter {iteration:3d}: acc={acc:.1%} pnl={total_pnl:+.2f} "
                  f"| best={best_acc:.1%}@{best_iter}")

    print(f"\nBest: {best_acc:.1%} @ iter {best_iter}")
    print(f"Supervised baseline: ~52.5%")
    print(f"Random baseline: 50.0%")


if __name__ == "__main__":
    main()
