"""Paper ledger report: the 48-72h baseline monitor.

Answers the questions that matter during the observation window:
- How many epochs did we decide on? How often did the entry cap block us?
- Of cap-blocked entries, how often would the model's side have WON?
  (counterfactual, using official resolutions)
- Executed trades: win rate, mean PnL per contract, cumulative PnL.
- Model calibration: bucketed p_model vs realized outcomes.
- Quote regime at decision time (how far books drift from 0.50 by entry).

Usage: python -m quantbtc.paper_report  ->  reports/paper-YYYYMMDD.md
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path


def _intended_side(p_model: float) -> str:
    return "up" if p_model >= 0.5 else "down"


def build_report(collector_db: str, paper_db: str, now_ms: int) -> str:
    coll = sqlite3.connect(collector_db)
    coll.row_factory = sqlite3.Row
    p = sqlite3.connect(paper_db)
    p.row_factory = sqlite3.Row
    trades = p.execute(
        "SELECT * FROM paper_trades ORDER BY id"
    ).fetchall()

    res = {
        r["market_id"]: r["outcome"]
        for r in coll.execute("SELECT market_id, outcome FROM resolutions")
    }

    lines = [
        "# Paper trader baseline report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now_ms / 1000))} UTC",
        f"Total ledger rows: {len(trades)}",
        "",
    ]

    executed, blocked, theta_skipped, no_quote = [], [], [], []
    for t in trades:
        if t["action"].startswith("buy"):
            executed.append(t)
        elif t["notes"].startswith("ask>"):
            blocked.append(t)
        elif t["notes"].startswith("|p-0.5|"):
            theta_skipped.append(t)

    # --- executed trades ---
    lines += ["## Executed trades", ""]
    if executed:
        settled = [t for t in executed if t["outcome"] is not None]
        wins = [t for t in settled if t["outcome"] == "won"]
        pnl = sum(t["pnl"] or 0.0 for t in settled)
        n_contracts = sum(t["contracts"] for t in settled)
        lines += [
            f"- executed: **{len(executed)}** (settled: {len(settled)}, "
            f"pending: {len(executed) - len(settled)})",
            f"- win rate: **{len(wins)}/{len(settled)}"
            + (f" = {len(wins)/len(settled):.1%}\"" if settled else "\""),
            f"- cumulative PnL: **${pnl:+.2f}** on {n_contracts} contracts"
            + (f" ({pnl/n_contracts:+.4f}/contract)" if n_contracts else ""),
            "",
            "| epoch | action | p | entry | contracts | outcome | pnl |",
            "|---|---|---|---|---|---|---|",
        ]
        for t in executed[-20:]:
            lines.append(
                f"| {t['market_id']} | {t['action']} | "
                f"{t['p_model']:.3f} | {t['entry_price']:.2f} | "
                f"{t['contracts']} | {t['outcome'] or 'pending'} | "
                f"{t['pnl'] if t['pnl'] is not None else ''} |"
            )
    else:
        lines += ["- none yet", ""]

    # --- cap-blocked counterfactuals ---
    lines += ["## Entry-cap blocked (ask > cap) — counterfactual", ""]
    if blocked:
        known = [t for t in blocked if t["market_id"] in res and t["p_model"] is not None]
        would_win = sum(
            1
            for t in known
            if res[t["market_id"]] == _intended_side(t["p_model"])
        )
        lines += [
            f"- blocked epochs: **{len(blocked)}** "
            f"({len(blocked)/(len(blocked)+len(executed)+len(theta_skipped)+1e-9):.0%} "
            "of decided epochs)"
            if blocked
            else "",
            f"- counterfactual win rate if we HAD entered at the ask: "
            f"**{would_win}/{len(known)}"
            + (f" = {would_win/len(known):.1%}\"" if known else " (no resolutions yet)\""),
            f"- avg blocked ask: "
            f"{sum(t['entry_price'] for t in blocked if t['entry_price'])/max(1,len([t for t in blocked if t['entry_price']])):.3f}",
            "",
            "| epoch | p | intended | ask | actual outcome | would-have |",
            "|---|---|---|---|---|---|",
        ]
        for t in blocked[-15:]:
            outcome = res.get(t["market_id"], "?")
            would = (
                "WIN"
                if t["market_id"] in res and t["p_model"] is not None
                and outcome == _intended_side(t["p_model"])
                else "lose"
            )
            lines.append(
                f"| {t['market_id']} | {t['p_model']:.3f} | "
                f"{_intended_side(t['p_model'])} | {t['entry_price']:.2f} | "
                f"{outcome} | {would} |"
                if t["p_model"] is not None
                else f"| {t['market_id']} | ? | ? | ? | {outcome} | ? |"
            )
    else:
        lines += ["- none", ""]

    # --- theta skips & calibration ---
    lines += ["## Theta skips (model unsure)", ""]
    lines += [f"- count: {len(theta_skipped)}", ""]

    lines += ["## Model calibration (decided epochs with known outcome)", ""]
    cal = [
        t
        for t in list(executed) + list(blocked)
        if t["p_model"] is not None and t["market_id"] in res
    ]
    if cal:
        buckets = {}
        for t in cal:
            b = round(t["p_model"] * 10) / 10  # 0.1 buckets
            up_won = res[t["market_id"]] == "up"
            buckets.setdefault(b, []).append(up_won)
        lines += [
            "| p bucket | n | realized up-rate |", "|---|---|---|"
        ]
        for b in sorted(buckets):
            obs = buckets[b]
            lines.append(
                f"| {b:.1f} | {len(obs)} | {sum(obs)/len(obs):.2f} |"
            )
    else:
        lines += ["- no decided+resolved epochs yet", ""]

    coll.close()
    p.close()
    return "\n".join(lines) + "\n"


def main() -> None:
    from quantbtc.config import load_config

    cfg = load_config()
    now = int(time.time() * 1000)
    md = build_report(cfg.storage.sqlite_path, "data/paper.db", now)
    out = Path("reports")
    out.mkdir(exist_ok=True)
    path = out / f"paper-{time.strftime('%Y%m%d')}.md"
    path.write_text(md)
    print(md)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
