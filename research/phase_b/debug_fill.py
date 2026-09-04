"""Debug why maker bids never fill: inspect one decided epoch end-to-end."""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))
sys.path.insert(0, str(REPO / "research" / "rlenv"))

import numpy as np  # noqa: E402

import maker_backtest as mb  # noqa: E402
from env import build_windows  # noqa: E402

DATA = mb.DATA


def main() -> None:
    bars = pl.read_parquet(mb.DATA / "btcusdt_spot_1m_janmar.parquet")
    p_by_open = mb.champion_predictions(bars, "5m")

    decided = [
        (open_ms, p)
        for open_ms, p in sorted(p_by_open.items())
        if abs(p - 0.5) > 0.05 and open_ms >= mb.TRAIN_CUTOFF_MS
    ]
    print(f"decided epochs: {len(decided)}")
    open_ms, p = decided[0]
    side_up = p >= 0.5
    print(f"epoch open {open_ms} | p {p:.3f} | side {'up' if side_up else 'down'}")

    eps = build_windows(
        bars.filter(pl.col("open_time").dt.epoch("ms") >= open_ms - 3_600_000),
        horizon_s=300,
        seal="2026-04-01",
    )
    ep = next((e for e in eps if e["open_time_ms"] == open_ms), None)
    fair = None
    for st in ep["steps"]:
        if (st["t_ms"] - ep["open_time_ms"]) >= 60_000:
            fair = float(st["feat"][0])
            break
    bid = float(np.clip(fair - 0.02, 0.01, 0.99)) if fair else None
    print(f"fair@+60s {fair:.3f} -> bid {bid:.3f}")

    epochs = pl.read_parquet(DATA / "epochs_bridge_quotes.parquet").filter(
        pl.col("open_time_utc").dt.epoch("ms") == open_ms
    )
    print("bridge row:", epochs.height)

    day = __import__("datetime").datetime.fromtimestamp(
        open_ms / 1000, __import__("datetime").timezone.utc
    ).strftime("%Y-%m-%d")
    ob = pl.read_parquet(DATA / f"orderbooks_{day}.parquet").filter(
        pl.col("market_id")
        == epochs["market_id"][0] if epochs.height else pl.lit(False)
    ) if False else None
    ob_all = pl.read_parquet(DATA / f"orderbooks_{day}.parquet")
    slug = (
        epochs["market_id"][0]
        if epochs.height
        else None
    )
    obm = ob_all.filter(pl.col("market_id") == slug) if slug else pl.DataFrame()
    print("book tokens:", obm["token_id"].unique().to_list() if obm.height else "none")

    tr = pl.read_parquet(DATA / f"trades_{day}.parquet")
    for tok in (obm["token_id"].unique().to_list() if obm.height else []):
        tt = tr.filter(
            (pl.col("token_id") == tok)
            & (pl.col("timestamp").dt.epoch("ms") >= open_ms + 60_000)
        ).sort("timestamp")
        prints = [
            (str(r["timestamp"])[11:19], round(r["price"], 3), round(r["size"], 1))
            for r in tt.head(10).iter_rows(named=True)
        ]
        q = obm.filter(pl.col("token_id") == tok)
        bb = q["best_bid"][0] if q.height else None
        ba = q["best_ask"][0] if q.height else None
        print(f"token ...{str(tok)[-8:]} first-snap bid {bb} ask {ba}")
        print(f"   prints(+60s..): {prints}")


if __name__ == "__main__":
    main()
