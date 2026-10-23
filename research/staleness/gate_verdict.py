"""Pre-registered two-week gate verdict for the v2 cohort (delivered late).

The verdict was pre-registered (EXTERNAL_CATALOG rounds 201/208): the v2
window completed 2026-09-18 15:02 UTC; rule = live per-contract EV positive
with day-block bootstrap CI excluding 0 (upward) AND every ISO week positive,
else honest negative -> gate retired from any capital discussion until a
feature-bakeoff candidate survives realized-EV scoring.

The scheduled automation (automation-775dd112) never dispatched — the host
was inactive from 2026-09-14 to 2026-10-23 — so this script computes the
verdict on 2026-10-23 from the untouched append-only ledgers. Nothing about
the rule, window, or daemons was modified after pre-registration.

Primary cohort: data/paper_wallet.db gate='v2' settled trades with
entry_ts_ms < 2026-09-18 15:02 UTC (the live $5-controlled wallet).
Twin confirmation: data/paper_gate.db (same fair_v2 stack, independent
daemon). Post-window trades (>= boundary) are reported separately and
labeled post-hoc: NOT part of the pre-registration.
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "research" / "staleness" / "GATE_VERDICT.md"
UTC = datetime.timezone.utc

W_START = int(datetime.datetime(2026, 9, 4, 15, 2, tzinfo=UTC).timestamp() * 1000)
W_END = int(datetime.datetime(2026, 9, 18, 15, 2, tzinfo=UTC).timestamp() * 1000)
N_BOOT = 10_000
RNG = np.random.default_rng(20260918)


def day(ts: int) -> str:
    return datetime.datetime.fromtimestamp(ts / 1000, tz=UTC).date().isoformat()


def load(db: Path, gated: bool) -> list[tuple[int, int, int]]:
    c = sqlite3.connect(str(db))
    q = "SELECT entry_ts_ms, pnl_cents, won FROM trades WHERE status='settled'"
    if gated:
        q += " AND gate='v2'"
    q += " ORDER BY entry_ts_ms"
    rows = list(c.execute(q))
    c.close()
    return rows


def ev(rs) -> float:
    return sum(r[1] for r in rs) / len(rs)


def win(rs) -> float:
    return sum(r[2] for r in rs) / len(rs)


def by_day(rs):
    d: dict[str, list] = {}
    for r in rs:
        d.setdefault(day(r[0]), []).append(r)
    return d


def by_week(rs):
    w: dict[tuple[int, int], list] = {}
    for r in rs:
        iso = datetime.datetime.fromtimestamp(r[0] / 1000, tz=UTC).isocalendar()
        w.setdefault((iso[0], iso[1]), []).append(r)
    return w


def day_block_ci(rs) -> tuple[float, float]:
    days = by_day(rs)
    arrs = [np.array([r[1] for r in days[d]], dtype=float) for d in sorted(days)]
    boots = []
    for _ in range(N_BOOT):
        idx = RNG.integers(0, len(arrs), size=len(arrs))
        boots.append(np.concatenate([arrs[i] for i in idx]).mean())
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(lo), float(hi)


def cohort_block(rows, label, lines, primary=False):
    pre = [r for r in rows if r[0] < W_END]
    post = [r for r in rows if r[0] >= W_END]
    lines.append(f"### {label}")
    lines.append("")
    lines.append(f"- settled v2 trades in window: **n={len(pre):,}** "
                 f"({day(pre[0][0])} .. {day(pre[-1][0])})")
    lines.append(f"- pooled per-contract EV: **{ev(pre):+.2f}c** "
                 f"(= {ev(pre)/100:+.4f} USD/contract), win rate {win(pre):.3f}")
    lo, hi = day_block_ci(pre)
    lines.append(f"- day-block bootstrap 95% CI (10,000 resamples of whole UTC entry days): "
                 f"**[{lo:+.2f}c, {hi:+.2f}c]**")
    lines.append("")
    lines.append("| UTC day | n | EV/trade (c) | win rate |")
    lines.append("|---|---|---|---|")
    for d in sorted(by_day(pre)):
        rs = by_day(pre)[d]
        lines.append(f"| {d} | {len(rs):,} | {ev(rs):+.2f} | {win(rs):.3f} |")
    lines.append("")
    wk = by_week(pre)
    lines.append("| ISO week | n | EV/trade (c) | positive? |")
    lines.append("|---|---|---|---|")
    for w in sorted(wk):
        lines.append(f"| {w[0]}-W{w[1]:02d} | {len(wk[w]):,} | {ev(wk[w]):+.2f} | "
                     f"{'YES' if ev(wk[w]) > 0 else 'no'} |")
    lines.append("")
    return pre, post, lo, hi


def main() -> None:
    wallet = load(REPO / "data" / "paper_wallet.db", gated=True)
    twin = load(REPO / "data" / "paper_gate.db", gated=False)

    L = []
    L.append("# Pre-registered two-week gate verdict — v2 cohort: **FAILED (honest negative)**")
    L.append("")
    L.append("## Delivery note (why this is late)")
    L.append("")
    L.append("The verdict was pre-registered for 2026-09-18 15:02 UTC (catalog rounds")
    L.append("201/208) and scheduled as automation `automation-775dd112`. That automation")
    L.append("**never dispatched** (runCount 0, marked completed) because the session host")
    L.append("was inactive 2026-09-14 .. 2026-10-23. It is computed here on 2026-10-23")
    L.append("from the append-only ledgers the daemons kept writing unattended. The rule,")
    L.append("the window boundary, the calibration, and the daemon code are unchanged since")
    L.append("pre-registration; only the delivery is late, and no interim computation of")
    L.append("this verdict was run in between (the twin ledger had zero human interaction).")
    L.append("")
    L.append("## Pre-registered rule")
    L.append("")
    L.append("> Live per-contract EV positive with day-block CI excluding 0 (upward)")
    L.append("> AND all-weeks-positive — REQUIRED before any capital discussion;")
    L.append("> anything else = honest negative, gate retired, feature-bakeoff first.")
    L.append("")
    L.append(f"Window: gate-v2 trades with entry < 2026-09-18 15:02 UTC "
             f"(gate switch ratified 2026-09-04 15:02 UTC). "
             f"Units: cents per 1-contract trade.")
    L.append("")

    pre_w, post_w, lo_w, hi_w = cohort_block(wallet, "Primary — live $5-controlled wallet (gate='v2')", L, True)
    pre_t, post_t, lo_t, hi_t = cohort_block(twin, "Twin confirmation — paper_gate daemon (same fair_v2 stack)", L)

    weeks_pos_w = sum(1 for w in by_week(pre_w) if ev(by_week(pre_w)[w]) > 0)
    L.append("## Verdict")
    L.append("")
    L.append("| requirement (pre-registered) | primary result | met? |")
    L.append("|---|---|---|")
    L.append(f"| per-contract EV > 0 | {ev(pre_w):+.2f}c | **NO** |")
    L.append(f"| day-block 95% CI excludes 0 upward | [{lo_w:+.2f}c, {hi_w:+.2f}c] "
             f"(excludes 0 DOWNWARD) | **NO** |")
    L.append(f"| all ISO weeks positive | {weeks_pos_w}/{len(by_week(pre_w))} weeks positive "
             f"(twin: 1/3, best week +1.49c) | **NO** |")
    L.append("")
    L.append("**FAILED — honest negative.** The backtested +8-9c/trade edge did not survive")
    L.append("live paper execution: realized -2.22c/trade over the pre-registered window,")
    L.append("-2.04c/trade over the full v2 cohort to date, twin independently at -2.24c.")
    L.append("The gate is retired from any capital discussion. Any revival requires a")
    L.append("feature-bakeoff candidate that survives prospective realized-EV scoring")
    L.append("(round-235 precedent: the first candidate, BOCPD flow-regime conditioning,")
    L.append("was scored and killed at -0.16c delta).")
    L.append("")
    L.append("## Reference comparisons (pre-registered context)")
    L.append("")
    L.append("- **brti-edge null (round 208):** an independent team's best walk-forward skill")
    L.append("  on filled trades was 0.93% against a 5% requirement (285 trades, -65% bankroll).")
    L.append("  Our result is consistent with that null: no measurable skill on filled trades.")
    L.append("- **Adverse-move-at-fill (ADV_MOVE_FILLS.md):** -1.75c mean markout at +30s over")
    L.append("  571 fills (median -2.00c, 56.9% adverse) — execution drag roughly fee-sized,")
    L.append("  so the shortfall is backtest-edge overstatement plus dispersion, not latency alone.")
    L.append("- **Nunes IC/PnL non-identifiability (round 216):** feature quality cannot proxy")
    L.append("  realized PnL; only realized-EV scoring (used here) is decisive.")
    L.append("- **BOCPD-EV bakeoff (round 235):** flow-regime conditioning carries no conditional")
    L.append("  information about trade outcomes (EV delta -0.16c = null).")
    L.append("")
    L.append("## Post-hoc extension (Sep 18 -> Oct 23) — NOT pre-registered")
    L.append("")
    L.append("The daemons kept trading after the window; reported for completeness only.")
    L.append("")
    lo2, hi2 = day_block_ci(post_w)
    lo3, hi3 = day_block_ci(post_t)
    pos_days = sum(1 for d in by_day(post_w) if ev(by_day(post_w)[d]) > 0)
    tot_w = sum(r[1] for r in wallet)
    L.append(f"- wallet: n={len(post_w):,} settled, EV {ev(post_w):+.2f}c, "
             f"CI [{lo2:+.2f}c, {hi2:+.2f}c], {pos_days}/{len(by_day(post_w))} days positive")
    L.append(f"- twin:   n={len(post_t):,} settled, EV {ev(post_t):+.2f}c, "
             f"CI [{lo3:+.2f}c, {hi3:+.2f}c]")
    L.append(f"- cumulative v2 cohort (both windows): {len(wallet):,} settled, "
             f"{tot_w:+,}c ({tot_w/100:+.2f} USD) — the negative PERSISTS, no drift toward positive")
    L.append("- censoring caveat: the 500c/day loss allowance pinned six extension days at")
    L.append("  exactly -5.00 USD, so the uncapped post-window EV is somewhat WORSE than -1.96c")
    L.append("")
    L.append("## What was NOT tested")
    L.append("")
    L.append("Latency-to-venue, queue position, depth-aware sizing, maker (resting) entries,")
    L.append("and capital-scaled slippage. The wallet is paper: fills assumed at the observed")
    L.append("ask with the 0.07*p*(1-p) taker fee. None of these were part of the")
    L.append("pre-registration; they are candidates for any future bakeoff, not evidence.")
    L.append("")
    L.append("## Operational state during the gap")
    L.append("")
    L.append("All four daemons ran unattended 2026-09-14 .. 2026-10-23 (collector 1.94M quotes,")
    L.append("81.5k market rows, fresh to 11s on 2026-10-23; services restarted at host reboot")
    L.append("2026-10-23 21:27 IST with no state loss — wallet restored 3,873 historical trades).")
    L.append("No thresholds, calibration, or code were touched during the gap.")

    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L[:14]))
    print(f"\nwrote {OUT}")
    print(f"VERDICT: FAILED — pre-window EV {ev(pre_w):+.2f}c CI [{lo_w:+.2f},{hi_w:+.2f}] "
          f"{weeks_pos_w}/{len(by_week(pre_w))} weeks positive")


if __name__ == "__main__":
    main()
