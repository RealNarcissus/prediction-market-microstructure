"""RL environment: minute-level trading of Jupiter-style TWAP epochs.

Each epoch (5m or 15m window) is one episode. The agent observes the market
once per completed 1m bar and may enter ONCE per episode (buy_up / buy_down
/ skip). At window close the TWAP outcome settles the position:

    reward = win ? (1 - p_entry) - fee : -p_entry - fee

Entry price assumption: the model-free Asian-digital fair value at decision
time (Levy moments, quantbtc.fairvalue) — edge therefore comes from timing
and direction, not from assumed mispricing. Fees use the exact Jupiter
formula. NO LOOKAHEAD: state at minute t uses bars <= t; the label is only
realized at close.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from quantbtc.fairvalue import AsianDigital
from quantbtc.fees import order_fee
from quantbtc.twapbars import AGG_MIN


def load_1m_bars(parquet_path: str | Path) -> pl.DataFrame:
    df = pl.read_parquet(parquet_path).sort("open_time")
    if df.schema["open_time"].time_zone is None:
        df = df.with_columns(pl.col("open_time").dt.replace_time_zone("UTC"))
    return df


def build_windows(
    bars_1m: pl.DataFrame,
    horizon_s: int,
    seal: str = "2026-01-01",
    ewma_alpha: float = 0.02,
) -> list[dict]:
    """One dict per epoch with minute-by-minute decision states + outcome.

    State features at elapsed minute k (k=0..m-1), all computable from bars
    up to that minute:
      f0 fair_up   : AsianDigital.prob_up(close_k, elapsed, running_avg)
      f1 dist_avg  : ln(running_avg / strike)
      f2 dist_spot : ln(close_k / strike)
      f3 imb       : taker-buy imbalance of bar k
      f4 mom5      : log return over last 5 bars
      f5 vol_z     : z-scored 1m |return| vs trailing 240 bars (vol regime)
      f6 frac_left : remaining fraction of window
      f7 r1        : last 1m log return
    """
    m = AGG_MIN[f"{'15m' if horizon_s == 900 else '5m'}"]
    seal_ts = np.datetime64(seal)
    b = bars_1m.with_columns(
        (pl.col("open_time").dt.epoch("ms") // (horizon_s * 1000)).alias("widx")
    )
    b = b.filter(pl.col("open_time") < pl.lit(seal_ts))
    closes = b["close"].to_numpy()
    opens = b["open"].to_numpy()
    vols = b["volume"].to_numpy()
    tbv = b["taker_buy_base_volume"].to_numpy()
    widx = b["widx"].to_numpy()
    times = b["open_time"].dt.epoch("ms").to_numpy()

    # EWMA vol of 1m returns. r1 is a PER-MINUTE log return, so its
    # variance scale is sigma_ann^2 / 525,600 (~3.85e-7 for 45% ann).
    # BUGFIX: earlier init was 1e-14 and sigma was divided by sqrt(60)
    # a second time, collapsing prob_up into a {0,1} step function.
    r1 = np.full(len(closes), np.nan)
    r1[1:] = np.log(closes[1:] / closes[:-1])
    ewma_var = np.full(len(closes), 0.45**2 / (365.25 * 24 * 360))
    for i in range(1, len(closes)):
        if np.isfinite(r1[i]):
            ewma_var[i] = (1 - ewma_alpha) * ewma_var[i - 1] + ewma_alpha * r1[i] ** 2
    roll_abs = (
        pl.DataFrame({"a": np.abs(r1)})
        .with_columns(pl.col("a").rolling_mean(240).alias("v"))
        .to_numpy().T[0]
    )

    av = AsianDigital(strike=1.0, total_s=float(horizon_s), sigma=1.0)
    episodes = []
    boundaries = np.flatnonzero(np.diff(widx, prepend=widx[0] - 1)) 
    starts = np.append(boundaries, len(b))
    for s_i in range(len(starts) - 1):
        s0, s1 = starts[s_i], starts[s_i + 1]
        if s1 - s0 != m:  # complete windows only
            continue
        strike = opens[s0]
        twap = float(np.mean(closes[s0:s1]))
        y_up = 1 if twap >= strike else 0
        steps = []
        cum_vol = 0.0
        run_sum = 0.0
        for k in range(s0, s1):
            j = k - s0
            elapsed = j * 60.0
            run_sum += closes[k]
            running_avg = run_sum / (j + 1)
            # r1 is per-minute -> per-SECOND sd = sd_1m / sqrt(60)
            # (variance scales linearly with time; BUGFIX: was /60, which
            # understated vol ~7.75x and collapsed prob_up to a step)
            sigma_1s = float(np.sqrt(max(ewma_var[k], 1e-12)) / np.sqrt(60.0))
            sigma_1s = min(max(sigma_1s, 1e-8), 1e-4)
            av2 = AsianDigital(strike=strike, total_s=float(horizon_s), sigma=sigma_1s)
            fair = av2.prob_up(float(closes[k]), elapsed, running_avg)
            imb = (
                2.0 * tbv[k] / vols[k] - 1.0
                if vols[k] > 0 else 0.0
            )
            mom5 = (
                float(np.log(closes[k] / closes[k - 5]))
                if k >= 5 and closes[k - 5] > 0 and closes[k] > 0 else 0.0
            )
            volz = (
                float(abs(r1[k]) / roll_abs[k]) if np.isfinite(roll_abs[k]) and roll_abs[k] > 0 else 1.0
            )
            steps.append(
                {
                    "t_ms": int(times[k]),
                    "feat": np.array([
                        fair,
                        float(np.log(max(running_avg, 1e-9) / max(strike, 1e-9))),
                        float(np.log(max(closes[k], 1e-9) / max(strike, 1e-9))),
                        imb, mom5, min(volz, 10.0),
                        (m - 1 - j) / max(1, m - 1),
                        float(r1[k]) if np.isfinite(r1[k]) else 0.0,
                    ]),
                    "fair": fair,
                }
            )
            cum_vol += vols[k]
        fee_per = order_fee(0.5, 1)  # reference; actual fee uses entry fair
        episodes.append(
            {
                "steps": steps,
                "y_up": y_up,
                "strike": strike,
                "twap": twap,
                "open_time_ms": int(times[s0]),
                "close_time_ms": int(times[s1 - 1] + 60_000),
                "fee_ref": fee_per,
                "avg_abs_move": float(np.mean(np.abs(r1[s0:s1]))),
            }
        )
    return episodes


def episode_reward(action: str, entry_price: float, y_enter_side_won: bool,
                   contracts: int = 1) -> float:
    """Realized per-contract PnL after exact Jupiter fees."""
    fee = order_fee(entry_price, contracts) / contracts
    gross = contracts * (1.0 - entry_price) if y_enter_side_won else -contracts * entry_price
    return gross / contracts - fee


@dataclass
class StepResult:
    done: bool
    reward: float
