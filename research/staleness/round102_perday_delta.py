"""Round 102: per-day EV breakdown + side-separated delta fit.

Step 3: publish the per-day EV table for the v2_ewma gated test span
(the pooled CI's day-level composition was unpublished).

Step 4: re-run the (delta, lambda) joint fit with market side carried
through honestly — market side joined from collector.db markets table
(suffix '-0' = Up, '-1' = Down), the same convention as audit.py.
Settles the round-59 interpretation question with the join chain shown.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from research.staleness.retest_logspace import (  # noqa: E402
    FEE_RATE, PARQUET, SPLIT_MS, fit_lambda, sigmoid,
)

OUT = REPO / "research" / "staleness" / "ROUND102_PERDAY_DELTA.md"


def main() -> None:
    df = pl.read_parquet(str(PARQUET)).filter(pl.col("cfg") == "v2_ewma").sort("ts_ms")
    tr = df.filter(pl.col("ts_ms") < SPLIT_MS)
    te = df.filter(pl.col("ts_ms") >= SPLIT_MS)
    z_tr, won_tr = tr["z"].to_numpy(), tr["won"].to_numpy().astype(float)
    lam = fit_lambda(z_tr, won_tr)
    iso = IsotonicRegression(out_of_bounds="clip").fit(sigmoid(z_tr / lam), won_tr)
    te = te.with_columns((pl.col("z") / lam).alias("z_l"))
    te = te.with_columns(pl.Series("prob", iso.predict(sigmoid(te["z_l"].to_numpy()))))
    te = te.with_columns((FEE_RATE * pl.col("ask") * (1 - pl.col("ask"))).alias("fee"))
    gated = te.filter((pl.col("prob") - pl.col("ask")) > pl.col("fee")).with_columns(
        pl.when(pl.col("won") == 1)
        .then(1 - pl.col("ask") - pl.col("fee"))
        .otherwise(-pl.col("ask") - pl.col("fee"))
        .alias("ev")
    )

    lines = ["# Round 102: per-day EV breakdown + side-separated delta fit", ""]
    lines.append(f"config v2_ewma, lambda(train)={lam:.2f}, gated n={gated.height:,}")
    lines.append("")
    lines.append("## 1. Per-day EV (test span, gated trades)")
    lines.append("")
    lines.append("| UTC date | n | EV/trade (c) | win rate |")
    lines.append("|---|---|---|---|")
    g = gated.with_columns(
        (pl.col("ts_ms") // 86_400_000 * 86_400_000).alias("day")
    )
    import datetime
    for row in sorted(g.select("day").unique().to_dicts(), key=lambda r: r["day"]):
        day = row["day"]
        s = g.filter(pl.col("day") == day)
        ev = float(s["ev"].mean()) * 100
        wr = float(s["won"].mean())
        dstr = datetime.datetime.fromtimestamp(day / 1000, tz=datetime.timezone.utc).date().isoformat()
        lines.append(f"| {dstr} | {s.height:,} | {ev:+.2f} | {wr:.3f} |")
    lines.append("")

    # side-separated delta fit
    lines.append("## 2. Side-separated (delta, lambda) fit on full fair population")
    lines.append("")
    conn = sqlite3.connect(str(REPO / "data" / "collector.db"))
    m = pl.read_database("SELECT market_id FROM markets", conn)
    conn.close()
    m = m.with_columns(pl.col("market_id").str.slice(-1).alias("suffix"))
    m = m.with_columns((pl.col("suffix") == "0").alias("is_up"))
    dup = m.group_by("market_id").len().filter(pl.col("len") > 1)
    lines.append(f"markets table: {m.height:,} rows, suffix mix: {m['suffix'].value_counts().to_dicts()}")
    lines.append(f"duplicate market rows: {dup.height} (join is 1:1 per side-suffixed id)")
    lines.append("")
    full = df.join(m.select(["market_id", "is_up"]), on="market_id", how="left")
    missing = full.filter(pl.col("is_up").is_null()).height
    lines.append(f"parquet rows without market match: {missing} (of {full.height:,})")
    lines.append("")
    lines.append("| side | n | delta* | lambda* | Brier | Brier (delta=0) |")
    lines.append("|---|---|---|---|---|---|")
    for flag, name in ((True, "UP (-0 markets)"), (False, "DOWN (-1 markets)")):
        dd = full.filter(pl.col("is_up") == flag)
        if dd.height < 100:
            lines.append(f"| {name} | {dd.height:,} | — | — | — | — |")
            continue
        z = dd["z"].to_numpy()
        won = dd["won"].to_numpy().astype(float)
        best = None
        for delta in np.arange(-2.0, 2.001, 0.05):
            for l in np.arange(1.0, 3.51, 0.05):
                b = float(((sigmoid((z + delta) / l) - won) ** 2).mean())
                if best is None or b < best[2]:
                    best = (float(delta), float(l), b)
        d, l, b = best
        b0 = float(((sigmoid(z / l) - won) ** 2).mean())
        lines.append(f"| {name} | {dd.height:,} | {d:+.2f} | {l:.2f} | {b:.4f} | {b0:.4f} |")
    lines.append("")

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
