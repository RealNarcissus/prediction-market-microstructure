"""Settlement inspection: does Jupiter settle the way our math assumes?

Compares every official resolution (collector db) against:
  1. TWAP proxy from Binance spot 1m bars: mean(1m closes in window) >= first open
  2. Endpoint proxy: last 1m close >= first open

Agreement rates per asset/horizon quantify the basis risk between our
exchange-data proxies and Jupiter's Chainlink TWAP oracle.

Usage: python research/phase_a5/settlement_check.py
"""
from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from quantbtc.paper import load_spot_1m  # noqa: E402


def main() -> None:
    coll = sqlite3.connect(REPO / "data/collector.db")
    coll.row_factory = sqlite3.Row
    rows = coll.execute(
        """SELECT r.market_id, r.outcome, m.asset, m.horizon_s,
                  m.open_time_ms, m.close_time_ms
           FROM resolutions r JOIN markets m USING (market_id)
           WHERE m.open_time_ms IS NOT NULL AND m.open_time_ms > 0
             AND r.market_id LIKE '%-0'"""
    ).fetchall()
    # NOTE: only Up-market (-0) rows count. The poller mirrors the outcome
    # onto the Down-market (-1) row (its outcome names the DOWN side's
    # result), which inverts the comparison if joined naively.

    bars = {}
    stats = defaultdict(lambda: {"n": 0, "twap_agree": 0, "end_agree": 0,
                                 "twap_end_disagree": 0})
    for r in rows:
        asset = r["asset"]
        if asset not in bars:
            bars[asset] = load_spot_1m(REPO / "data/raw", f"{asset}USDT")
        b = bars[asset]
        if b.is_empty():
            continue
        win = b.filter(
            (pl.col("open_time").dt.epoch("ms") >= r["open_time_ms"])
            & (pl.col("open_time").dt.epoch("ms") < r["close_time_ms"])
        )
        if win.height < 3:  # incomplete local data for this window
            continue
        first_open = win["open"][0]
        twap_up = win["close"].mean() >= first_open
        end_up = win["close"][-1] >= first_open
        official_up = r["outcome"] == "up"
        key = (asset, r["horizon_s"])
        s = stats[key]
        s["n"] += 1
        s["twap_agree"] += int(twap_up == official_up)
        s["end_agree"] += int(end_up == official_up)
        s["twap_end_disagree"] += int(twap_up != end_up)

    lines = [
        "# Settlement inspection: oracle vs proxies",
        "",
        "Official Jupiter resolutions vs Binance-spot-derived labels.",
        "",
        "| asset | horizon | n | TWAP-proxy agree | endpoint agree | twap!=endpoint |",
        "|---|---|---|---|---|---|",
    ]
    for (asset, hz), s in sorted(stats.items()):
        lines.append(
            f"| {asset} | {hz}s | {s['n']} | {s['twap_agree']}/{s['n']}"
            f" ({s['twap_agree']/s['n']:.0%}) | "
            f"{s['end_agree']}/{s['n']} ({s['end_agree']/s['n']:.0%}) | "
            f"{s['twap_end_disagree']} |"
        )
    total = sum(s["n"] for s in stats.values())
    twap = sum(s["twap_agree"] for s in stats.values())
    end = sum(s["end_agree"] for s in stats.values())
    lines += [
        "",
        f"**Overall: TWAP-proxy agrees with the oracle {twap}/{total}"
        f" ({twap/max(1,total):.1%}); endpoint {end}/{total}"
        f" ({end/max(1,total):.1%}).**",
        "",
        "Basis risk = 1 - agreement. Every disagreement point is edge lost",
        "or mislabeled training data for TWAP-proxy models; if the endpoint",
        "rate is materially lower, the TWAP approximation is earning its keep.",
    ]
    out = REPO / "research/phase_a5/settlement_check.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
