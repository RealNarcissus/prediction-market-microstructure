"""Queue-aware maker backtest: realistic fills using orderbook depth."""
import json, re, sys
from pathlib import Path
import numpy as np, polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "research"))
from quantbtc.twapbars import aggregate_windows
from strategies.s002_lgbm_base import new_model as cm
from strategies.s023_lgbm_pos_lag23 import build_features as cf

DATA = REPO / "data/polymarket"
HERDR = Path("/home/charleton/Desktop/agentProjects/Herdr/quant-btc/data/raw/btcusdt-usdtm-1m.parquet")
THETAS = [0.05, 0.08, 0.10, 0.12, 0.15]
OUR_SIZE = 10.0


def parse_levels(raw):
    if isinstance(raw, bytes): return json.loads(raw.decode())
    if isinstance(raw, str): return json.loads(raw)
    return raw or []


def main():
    epochs = pl.read_parquet(str(DATA / "epochs_bridge_quotes.parquet")).filter(
        pl.col("outcome").is_not_null() & pl.col("entry_ask_up").is_not_null())

    all_trades = pl.concat([
        pl.read_parquet(f) for f in sorted(DATA.glob("trades_2026-03-*.parquet"))
    ]).with_columns(pl.col("timestamp").dt.epoch("ms").alias("ts_ms"))

    results = []  # one entry per (epoch, theta) where filled
    n_epochs = n_filled = n_won = 0

    for symbol, asset in [("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"), ("SOLUSDT", "SOL")]:
        kl_path = REPO / "data/klines" / f"{symbol}_1m.parquet"
        if not kl_path.exists():
            continue
        bars = pl.read_parquet(str(kl_path)).with_columns(
            pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC")))

        for tf_file, hz in [("5-minute", "5m"), ("15-minute", "15m")]:
            sec = 300 if hz == "5m" else 900
            agg = aggregate_windows(bars, hz)
            agg = agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next")).drop_nulls(["y_next"])
            X = cf(agg); y = agg["y_next"].to_numpy().astype(int)
            fin = np.isfinite(X).all(axis=1)
            opens = agg["open_time"].dt.epoch("ms").to_numpy()
            model = cm(); model.fit(X[fin & (opens < 1785400000000)], y[fin & (opens < 1785400000000)])
            probs = model.predict_proba(X)[:, list(model.classes_).index(1)]
            p_by_open = {int(o): float(p) for o, p in zip(opens[fin], probs[fin])}

            e_sub = epochs.filter((pl.col("asset") == asset) & (pl.col("horizon") == hz))

            # load orderbooks + trades for this day set
            ob_days = {}
            for r_e in e_sub.iter_rows(named=True):
                oms = int(re.search(r"-(\d{10})$", r_e["market_id"]).group(1)) * 1000
                d = __import__("datetime").datetime.fromtimestamp(oms / 1000, tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%d")
                if d not in ob_days:
                    fp = DATA / f"orderbooks_{d}.parquet"
                    if fp.exists():
                        df = pl.read_parquet(str(fp)).with_columns(
                            pl.col("timestamp").dt.epoch("ms").alias("_ts"))
                        ob_days[d] = df

            tr_days = {}
            for d in list(ob_days.keys()):
                fp = DATA / f"trades_{d}.parquet"
                if fp.exists():
                    tr_days[d] = pl.read_parquet(str(fp)).with_columns(
                        pl.col("timestamp").dt.epoch("ms").alias("_ts"))

            for r_e in e_sub.iter_rows(named=True):
                slug = r_e["market_id"]
                mm = re.search(r"-(\d{10})$", slug)
                if not mm: continue
                oms = int(mm.group(1)) * 1000
                prev_open_ms = oms - sec * 1000
                p = p_by_open.get(prev_open_ms)
                if p is None or abs(p - 0.5) <= THETAS[0]:
                    continue
                close_s_val = int(r_e.get("close_time_utc", {}).timestamp() if hasattr(r_e.get("close_time_utc",""), 'timestamp') else 0)
                d_ms = oms + 60_000
                close_ms = oms + sec * 1000

                side_up = p >= 0.5
                won_up = r_e["outcome"] == "Up"
                won = won_up == side_up

                # find first orderbook snapshot after decision
                d_str = __import__("datetime").datetime.fromtimestamp(oms/1000, tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%d")
                ob_day = ob_days.get(d_str)
                if ob_day is None:
                    continue
                snap = ob_day.filter(
                    (pl.col("market_id") == slug)
                    & (pl.col("question").str.contains("(?i)up"))
                    & (pl.col("_ts") >= d_ms)
                ).sort("_ts")
                if snap.height == 0:
                    continue
                row = snap.row(0, named=True)
                bids_raw = row.get("bid_levels")
                bids = json.loads(bids_raw.decode()) if isinstance(bids_raw, bytes) else (
                    json.loads(bids_raw) if isinstance(bids_raw, str) else [])
                bids.sort(key=lambda x: x["price"], reverse=True)

                # rest one tick below best bid
                best_bid = bids[0]["price"] if bids else 0.50
                rest_px = max(0.02, round(best_bid - 0.01, 2))
                q_ahead = sum(lvl["size"] for lvl in bids if lvl["price"] >= rest_px)

                # determine our token id (up or down)
                tok = row.get("token_id", "")
                won_tok = won  # our side wins?

                # walk trades on this token after decision
                tr_day = tr_days.get(d_str)
                if tr_day is None:
                    continue
                tok_trades = tr_day.filter(
                    (pl.col("market_id") == slug)
                    & (pl.col("token_id") == tok)
                    & (pl.col("_ts") >= d_ms)
                ).sort("_ts")

                consumed = 0.0
                filled = False
                fill_px = rest_px
                for tr_r in tok_trades.iter_rows(named=True):
                    tp = float(tr_r["price"]); tsz = float(tr_r["size"])
                    if tp <= rest_px:
                        consumed += tsz
                        if consumed >= q_ahead + OUR_SIZE:
                            filled = True
                            break

                if not filled:
                    continue
                fee = 0.07 * fill_px * (1 - fill_px)
                pnl = ((1 - fill_px) - fee) if won else (-fill_px - fee)

                n_filled += 1; n_won += int(won); n_epochs += 1

                month = __import__("datetime").datetime.fromtimestamp(oms/1000, tz=__import__("datetime").timezone.utc).strftime("%Y-%m")
                for th in THETAS:
                    if abs(p - 0.5) > th:
                        results.append({"theta": th, "month": month,
                            "asset": asset, "hz": hz, "won": won, "pnl": pnl})

        print(f"  {asset} done")

    print(f"\nqueue-aware fills: {n_filled}, wins: {n_won} ({n_won/max(1,n_filled):.1%})")
    df = pl.DataFrame(results)
    if df.is_empty():
        print("no results"); return

    print("\n=== EV BY CONFIDENCE THRESHOLD ===")
    agg_t = df.group_by("theta").agg(
        pl.len().alias("fills"), pl.col("won").mean(),
        pl.col("pnl").mean().alias("ev"), pl.col("pnl").sum().alias("tot")
    ).sort("theta")
    lines = ["| theta | fills | win | EV/trade | total PnL |", "|---|---|---|---|---|"]
    for r in agg_t.iter_rows(named=True):
        marker = " <- POSITIVE" if r["ev"] > 0 else ""
        print(f"theta={r['theta']:.2f}: n={r['fills']}, win={r['won']:.1%}, EV={r['ev']:+.4f}{marker}")
        lines.append(f"| {r['theta']:.2f} | {r['fills']} | {r['won']:.1%} | {r['ev']:+.4f} | {r['tot']:+.2f} |")

    out_md = REPO / "research" / "phase_b" / "QUEUE_AWARE_RESULTS.md"
    Path(out_md).write_text("\n".join(lines) + "\n")
    print(f"wrote {out_md}")


if __name__ == "__main__":
    main()
