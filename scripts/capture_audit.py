"""One-shot capture-quality audit (correct column handling)."""
import sqlite3
import sys
import time

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0

conn = sqlite3.connect("data/collector.db")
now = int(time.time() * 1000)
start = now - int(HOURS * 3600 * 1000)

rows = conn.execute(
    """
    SELECT m.market_id, m.asset, m.horizon_s, m.open_time_ms,
           m.close_time_ms,
           (SELECT COUNT(*) FROM quotes q WHERE q.market_id = m.market_id) AS nq,
           EXISTS (SELECT 1 FROM resolutions r WHERE r.market_id = m.market_id) AS resolved
    FROM markets m
    WHERE m.market_id LIKE '%-0' AND m.open_time_ms > ?
    """,
    (start,),
).fetchall()

closed = [r for r in rows if r[4] + 15 * 60_000 < now]
print(f"window: last {HOURS}h | epochs seen: {len(rows)} | closed(>=15m ago): {len(closed)}")

by = {}
for market_id, asset, hz, open_ms, close_ms, nq, resolved in closed:
    s = by.setdefault((asset, hz), {"n": 0, "zero": 0, "tq": 0, "res": 0})
    s["n"] += 1
    s["zero"] += nq == 0
    s["tq"] += nq
    s["res"] += resolved
for k in sorted(by):
    s = by[k]
    print(
        f"{k[0]:4s} {k[1]:4d}s: {s['n']:3d} epochs | zero-quote {s['zero']:3d} "
        f"| total quotes {s['tq']:5d} (avg {s['tq']/max(1,s['n']):5.1f}) "
        f"| resolved {s['res']}"
    )

all_nq = sorted(r[5] for r in closed)
if all_nq:
    print(
        f"\nALL closed: median quotes/epoch {all_nq[len(all_nq)//2]} | "
        f"zero {sum(1 for q in all_nq if q == 0)}/{len(all_nq)}"
    )
last = conn.execute("SELECT MAX(ts_ms) FROM quotes").fetchone()[0] or 0
print(f"last quote {round((now - last)/1000)}s ago")
