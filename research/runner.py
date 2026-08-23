"""Autoresearch loop runner.

  python research/runner.py run s000_r4_baseline [--desc "..."]   # one experiment
  python research/runner.py list                                  # ledger history
  python research/runner.py verdict <strategy> [--notes "..."]    # spend ONE holdout use (human)

Keep-or-reset: a run whose primary metric beats the champion's becomes the
new champion (its strategy file gets committed); otherwise it is recorded as
a reset and its file left untracked for inspection.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parent
sys.path.insert(0, str(RESEARCH))

import guard  # noqa: E402
from ledger import Ledger  # noqa: E402
from locked.harness import evaluate_strategy  # noqa: E402
from quantbtc.config import load_config  # noqa: E402

EPS = 1e-4  # improvements must exceed float-noise
IMPLAUSIBLE_MCC = 0.15  # no legit 5m/15m crypto MCC comes close; above this
                        # the run is presumed leaky until a human overrides.


def load_strategy(module_name: str):
    return importlib.import_module(f"strategies.{module_name}")


def run_experiment(module_name: str, description: str = "", accept_implausible: bool = False) -> None:
    guard.verify()
    cfg = load_config()
    strat = load_strategy(module_name)
    result = evaluate_strategy(
        strat, cfg.research.data_5m, cfg.research.data_15m
    )
    ledger = Ledger()
    champ = ledger.champion()
    suspect = result.primary > IMPLAUSIBLE_MCC and not accept_implausible
    kept = (
        champ is None or result.primary > champ["primary_metric"] + EPS
    ) and not suspect
    note = (
        f"champion={champ['strategy']} primary={champ['primary_metric']:.6f}"
        if champ else "first champion"
    )
    if suspect:
        note += " | BLOCKED: implausible MCC, suspected leakage " \
                "(rerun with --accept-implausible only after human review)"
    exp_id = ledger.record(result, description or module_name, kept, notes=note)
    strat_file = RESEARCH / "strategies" / f"{module_name}.py"

    if kept:
        commit = subprocess.run(
            ["git", "add", str(strat_file), "research/RESULTS.md"],
            cwd=RESEARCH.parent, capture_output=True, text=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m",
             f"autoresearch keep: {result.strategy} primary={result.primary:.6f}"],
            cwd=RESEARCH.parent, capture_output=True, text=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RESEARCH.parent, capture_output=True, text=True,
        ).stdout.strip()
        ledger.set_git_commit(exp_id, head)
        write_results_md(ledger)
        subprocess.run(["git", "add", "research/RESULTS.md"], cwd=RESEARCH.parent, capture_output=True)
        subprocess.run(["git", "commit", "-q", "--amend", "--no-edit"], cwd=RESEARCH.parent, capture_output=True)
        status = f"KEEP — new champion (beat {champ['strategy']} {champ['primary_metric']:.6f})" if champ else "KEEP — first champion"
    else:
        status = (f"RESET (champion {champ['strategy']} holds at "
                  f"{champ['primary_metric']:.6f})")
    print(f"[{result.strategy}] primary={result.primary:.6f} "
          f"(5m MCC {result.res_5m.mcc:+.4f}, 15m MCC {result.res_15m.mcc:+.4f})")
    print(f"-> {status}")


def verdict(module_name: str, notes: str = "") -> None:
    """Spend one use of the sealed H1-2026 holdout. Human-triggered only."""
    guard.verify()
    cfg = load_config()
    strat = load_strategy(module_name)
    from locked import data as D, folds as F, metrics as M

    out = {}
    for hz, path in (("5m", cfg.research.data_5m), ("15m", cfg.research.data_15m)):
        df_full = D.compute_labels(D.load_bars(path))
        fit_df, hold_df = F.sealed_split(df_full)
        Xf = strat.build_features(fit_df)
        yf = fit_df["target_y"].to_numpy().astype(int)
        Xh = strat.build_features(hold_df)
        yh = hold_df["target_y"].to_numpy().astype(int)
        model = strat.new_model()
        model.fit(Xf, yf)
        proba = model.predict_proba(Xh)
        p1 = proba[:, list(model.classes_).index(1)] if hasattr(model, "classes_") else proba[:, 1]
        pred = (p1 >= 0.5).astype(int)
        out[hz] = M.safe_mcc(yh, pred)
    ledger = Ledger()
    ledger.record_verdict(strat.NAME, out["5m"], out["15m"], notes)
    print(f"HOLDOUT VERDICT {strat.NAME}: 5m MCC {out['5m']:+.4f}, "
          f"15m MCC {out['15m']:+.4f} (trials so far: {ledger.trials_count()})")


def write_results_md(ledger: Ledger) -> None:
    rows = ledger.conn.execute(
        "SELECT id, ts, strategy, description, mcc_5m, mcc_15m, "
        "primary_metric, kept, invalid, is_champion, git_commit "
        "FROM experiments ORDER BY id"
    ).fetchall()
    lines = [
        "# Autoresearch results ledger",
        "",
        "Primary metric: mean pooled walk-forward validation MCC (5m, 15m).",
        "Every trial here counts toward deflated final statistics.",
        "",
        "| # | strategy | 5m MCC | 15m MCC | primary | kept | champion | commit |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        flag = "**INVALID** " if r["invalid"] else ""
        lines.append(
            f"| {r['id']} | {flag}{r['strategy']} | {r['mcc_5m']:+.4f} | "
            f"{r['mcc_15m']:+.4f} | {r['primary_metric']:+.6f} | "
            f"{'KEEP' if r['kept'] else 'reset'} | "
            f"{'**champion**' if r['is_champion'] else ''} | "
            f"{r['git_commit'] or ''} |"
        )
    (RESEARCH / "RESULTS.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    if args[0] == "run":
        desc = ""
        if "--desc" in args:
            desc = args[args.index("--desc") + 1]
        run_experiment(args[1], desc, accept_implausible="--accept-implausible" in args)
    elif args[0] == "list":
        ledger = Ledger()
        write_results_md(ledger)
        print((RESEARCH / "RESULTS.md").read_text())
    elif args[0] == "verdict":
        notes = " ".join(args[args.index("--notes") + 1:]) if "--notes" in args else ""
        verdict(args[1], notes)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
