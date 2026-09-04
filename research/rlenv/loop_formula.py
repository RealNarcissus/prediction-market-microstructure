"""Non-naive formula RL — long-horizon arXiv loop.

Harness mapping:
  step    = per-paper-formula weight update (long — you tune with it)
  chunk   = next N=2 papers in arXiv sweep
  episode = probe at signal scores (reviewer T2: weight-aware)
  epoch   = walk-forward fold (seal = H1-2026 holdout, untouched)
  session = wall-clock until you stop (explicit halt wins)

Evaluation is regime-conditional (vol tercile + session), bucket-specific
costs, Holm-corrected as its own family (separate from Phase-A R1-R12).

Venue caveat (user-authored, do not relax):
  VPIN/Amihud/Quarter-Hour were RESET not because microstructure phenomena
  are false, but because formulas were built for continuous LOB spot/futures
  with unbounded linear payout — our venue is bounded-payout binary
  (Jupiter/Polymarket) with TWAP settlement, discrete depth, and EV =
  q - (p+fee). Naive porting is weak evidence. Revisiting M3/M8-class ideas
  (OFI, micro-price, Hawkes) requires depth/tick from the actual venue,
  not just the equation.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))

from rlenv.harness import Budget, Lifecycle

LOG = REPO / "research" / "rlenv" / "OBSERVATIONS.jsonl"
LIFECYCLE_DIR = REPO / "research" / "rlenv"


def _sanitize(obj):
    """Recursively replace NaN/Inf floats with None for strict JSON."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize(v) for v in obj)
    return obj


def _is_deferred(paper: dict) -> tuple[bool, str]:
    """Check whether a paper's data_needed is satisfied."""
    data_needed = paper.get("data_needed", "minute_bar")
    if data_needed in ("depth_gated",):
        # need ~14d of depth20 files
        depth_glob = list((REPO / "data" / "raw").glob("*/depth20/*.parquet"))
        # also check legacy location
        if len(depth_glob) < 200:
            # estimate coverage: count hour-files
            return True, f"awaiting depth20 >=14d (have {len(depth_glob)} hour-files)"
    if data_needed in ("tick_gated",):
        tick_glob = list((REPO / "data" / "raw").glob("*/aggTrade/*.parquet"))
        if len(tick_glob) < 200:
            return True, f"awaiting aggTrade >=14d (have {len(tick_glob)} hour-files)"
    return False, ""


def _ofi_augmented_predictions(symbol: str, hz: str, w: float) -> dict[int, float]:
    """Return {open_ms -> p(up)} for s023 blended with OFI proxy weight w."""
    import polars as pl
    from quantbtc.twapbars import aggregate_windows
    from strategies.s023_lgbm_pos_lag23 import build_features as s023_feats
    from strategies.s002_lgbm_base import new_model as cm

    p_kl = REPO / f"data/klines/{symbol}_1m.parquet"
    bars = pl.read_parquet(str(p_kl)).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
    )
    agg = aggregate_windows(bars, hz)
    agg = agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next")).drop_nulls(["y_next"])
    X = s023_feats(agg)
    y = agg["y_next"].to_numpy().astype(int)
    opens = agg["open_time"].dt.epoch("ms").to_numpy()
    fin = np.isfinite(X).all(axis=1)
    SEAL_MS = int(np.datetime64("2026-01-01").astype("datetime64[ms]").astype(int))
    train_mask = fin & (opens < SEAL_MS)
    mdl = cm()
    mdl.fit(X[train_mask], y[train_mask])
    p_s023 = mdl.predict_proba(X)[:, list(mdl.classes_).index(1)]

    v = agg["volume"].to_numpy()
    tbv = agg["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2 * tbv / v - 1, 0.0)
    rng = (agg["high"] - agg["low"]).to_numpy().astype(float)
    rng_norm = rng / (float(np.nanmean(rng)) + 1e-9)
    ofi_proxy = imb * rng_norm
    mu = float(np.nanmean(ofi_proxy[train_mask]))
    sd = float(np.nanstd(ofi_proxy[train_mask])) + 1e-9
    ofi_z = (ofi_proxy - mu) / sd

    eps = 1e-6
    p_clip = np.clip(p_s023, eps, 1 - eps)
    logit = np.log(p_clip / (1 - p_clip))
    logit_blended = logit + w * ofi_z
    p_blended = 1 / (1 + np.exp(-logit_blended))

    out: dict[int, float] = {}
    for o, pb, f_ok in zip(opens, p_blended, fin):
        if f_ok:
            try:
                ts = int(o)
            except (TypeError, ValueError):
                ts = int(np.datetime64(o).astype("datetime64[ms]").astype(int))
            out[ts] = float(pb)
    return out


def _lambda_augmented_predictions(symbol: str, hz: str, w: float) -> dict[int, float]:
    """Privacy-subsidy lambda (2605.15746): flow per vol. Proxy = ofi_proxy / r24."""
    import polars as pl
    from quantbtc.twapbars import aggregate_windows
    from strategies.s023_lgbm_pos_lag23 import build_features as s023_feats
    from strategies.s002_lgbm_base import new_model as cm

    p_kl = REPO / f"data/klines/{symbol}_1m.parquet"
    bars = pl.read_parquet(str(p_kl)).with_columns(
        pl.col("open_time").cast(pl.Int64).cast(pl.Datetime("ms", "UTC"))
    )
    agg = aggregate_windows(bars, hz)
    agg = agg.with_columns(pl.col("y_twap").shift(-1).alias("y_next")).drop_nulls(["y_next"])
    X = s023_feats(agg)
    y = agg["y_next"].to_numpy().astype(int)
    opens = agg["open_time"].dt.epoch("ms").to_numpy()
    fin = np.isfinite(X).all(axis=1)
    SEAL_MS = int(np.datetime64("2026-01-01").astype("datetime64[ms]").astype(int))
    train_mask = fin & (opens < SEAL_MS)
    mdl = cm()
    mdl.fit(X[train_mask], y[train_mask])
    p_s023 = mdl.predict_proba(X)[:, list(mdl.classes_).index(1)]

    v = agg["volume"].to_numpy()
    tbv = agg["taker_buy_base_volume"].to_numpy()
    imb = np.where(v > 0, 2 * tbv / v - 1, 0.0)
    rng = (agg["high"] - agg["low"]).to_numpy().astype(float)
    rng_norm = rng / (float(np.nanmean(rng)) + 1e-9)
    ofi_proxy = imb * rng_norm

    absr1 = (agg["close"] / agg["close"].shift(1)).log().abs().to_numpy()
    r24 = np.full(len(absr1), np.nan)
    for i in range(24, len(absr1)):
        w2 = absr1[i - 24 : i]
        if np.isfinite(w2).all():
            r24[i] = float(np.mean(w2))
        else:
            r24[i] = float(np.nanmean(w2)) if np.isfinite(np.nanmean(w2)) else np.nan
    r24 = np.where(np.isfinite(r24) & (r24 > 1e-9), r24, 1e-4)
    lam_proxy = ofi_proxy / r24

    mu = float(np.nanmean(lam_proxy[train_mask]))
    sd = float(np.nanstd(lam_proxy[train_mask])) + 1e-9
    lam_z = (lam_proxy - mu) / sd

    eps = 1e-6
    p_clip = np.clip(p_s023, eps, 1 - eps)
    logit = np.log(p_clip / (1 - p_clip))
    logit_blended = logit + w * lam_z
    p_blended = 1 / (1 + np.exp(-logit_blended))

    out: dict[int, float] = {}
    for o, pb, f_ok in zip(opens, p_blended, fin):
        if f_ok:
            try:
                ts = int(o)
            except (TypeError, ValueError):
                ts = int(np.datetime64(o).astype("datetime64[ms]").astype(int))
            out[ts] = float(pb)
    return out


def _augmented_for_paper(paper_id: str, symbol: str, hz: str, w: float) -> dict[int, float]:
    """Dispatch to the right proxy for a paper id."""
    if paper_id in ("W_0", "1011.6402", "ofi-ml-ofi", "queue-imbalance-spot"):
        return _ofi_augmented_predictions(symbol, hz, w)
    if paper_id in ("privacy-lambda", "2605.15746", "amihud-regime"):
        return _lambda_augmented_predictions(symbol, hz, w)
    # default for minute_bar candidates: use OFI proxy as generic venue-aware blend
    return _ofi_augmented_predictions(symbol, hz, w)


def _atomic_append_jsonl(path: Path, record: dict) -> None:
    """Append one JSON line atomically (sanitized, flush+fsync, strict)."""
    line = json.dumps(_sanitize(record), allow_nan=False) + "\n"
    # validate round-trips
    json.loads(line)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def run_step(lifecycle: Lifecycle, formula_id: str) -> dict:
    """Run one formula through the regime-conditional evaluator (weight-aware)."""
    from rlenv.evaluator import evaluate_all as _eval_all
    import rlenv.evaluator as ev

    # deferred gate
    try:
        from rlenv.arxiv_chunk import load_queue
        queue = load_queue()
        paper = next((p for p in queue if p.get("id") == formula_id), None)
    except Exception:
        paper = None

    if paper is not None:
        deferred, reason = _is_deferred(paper)
        if deferred:
            return {
                "formula": formula_id,
                "status": "DEFERRED",
                "deferred_reason": reason,
                "total_trades": 0,
                "buckets": [],
                "verdict": "DEFERRED",
                "any_promote": False,
                "step": lifecycle.step_count,
                "session_s": round(lifecycle.elapsed_session(), 1),
                "condition": lifecycle.evaluate().value,
                "naive_port": False,
            }

    aug_fn = _lambda_augmented_predictions if formula_id == "privacy-lambda" else _ofi_augmented_predictions
    # allow generic dispatch
    if formula_id not in ("W_0", "privacy-lambda", "noise-subsidy λ"):
        def _generic(symbol, hz, _w, _fid=formula_id):
            return _augmented_for_paper(_fid, symbol, hz, _w)
        aug_fn = _generic

    if formula_id in ("W_0", "privacy-lambda", "noise-subsidy λ", "1011.6402", "ofi-ml-ofi"):
        best = None
        best_w = None
        for w in [0.0, 0.5, 1.0]:
            orig = ev.champ_predictions
            def _patched(symbol, hz, _w=w, _fn=aug_fn):
                return _fn(symbol, hz, _w)
            ev.champ_predictions = _patched
            try:
                summary = _eval_all()
            finally:
                ev.champ_predictions = orig
            summary["ofi_weight"] = w
            cands = [b for b in summary["buckets"] if b["N"] >= 10]
            score = max((b["EV"] for b in cands), default=float("-inf"))
            best_score = max((b["EV"] for b in best["buckets"] if b["N"] >= 10), default=float("-inf")) if best is not None else float("-inf")
            if best is None or score > best_score:
                best = summary
                best_w = w
        assert best is not None
        best["formula"] = formula_id
        best["best_ofi_weight"] = best_w
        best["step"] = lifecycle.step_count
        best["session_s"] = round(lifecycle.elapsed_session(), 1)
        best["condition"] = lifecycle.evaluate().value
        best["status"] = best.get("verdict", "RESET")
        return best

    # single-w sweep for other minute_bar papers
    best = None
    best_w = None
    for w in [0.0, 0.5, 1.0]:
        orig = ev.champ_predictions
        def _patched2(symbol, hz, _w=w):
            return _augmented_for_paper(formula_id, symbol, hz, _w)
        ev.champ_predictions = _patched2
        try:
            summary = _eval_all()
        finally:
            ev.champ_predictions = orig
        summary["ofi_weight"] = w
        cands = [b for b in summary["buckets"] if b["N"] >= 10]
        score = max((b["EV"] for b in cands), default=float("-inf"))
        best_score = max((b["EV"] for b in best["buckets"] if b["N"] >= 10), default=float("-inf")) if best is not None else float("-inf")
        if best is None or score > best_score:
            best = summary
            best_w = w
    assert best is not None
    best["formula"] = formula_id
    best["best_ofi_weight"] = best_w
    best["step"] = lifecycle.step_count
    best["session_s"] = round(lifecycle.elapsed_session(), 1)
    best["condition"] = lifecycle.evaluate().value
    best["status"] = best.get("verdict", "RESET")
    return best


def _load_lifecycle(budget: Budget) -> Lifecycle:
    lc = Lifecycle.load(LIFECYCLE_DIR, budget)
    if lc is not None:
        # reuse wall clock from now but keep counters
        lc.session_start = time.monotonic() - lc.to_dict().get("session_elapsed_s", 0)
        return lc
    # infer from OBSERVATIONS.jsonl if lifecycle.json missing
    last_step = 0
    papers_swept = 0
    helpful = 0
    try:
        with open(LOG) as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                    probe = j.get("probe", {})
                    s = probe.get("step") or j.get("lifecycle", {}).get("step") or 0
                    last_step = max(last_step, int(s))
                    # count new-format probes as papers swept (chunk=2 legacy: each step ~1 paper)
                    if probe.get("formula"):
                        papers_swept += 1
                    if probe.get("verdict") == "KEEP" or probe.get("status") == "KEEP":
                        helpful += 1
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    lc2 = Lifecycle(budget=budget, step_count=last_step, papers_swept=papers_swept, helpful_count=helpful)
    return lc2


def main() -> None:
    # import guard lazily (research path)
    try:
        import guard
        guard.verify()
    except Exception as e:
        print(f"guard.verify failed: {e}", file=sys.stderr)
        raise

    from rlenv.arxiv_chunk import load_queue, papers_target, helpful_target, CHUNK_SIZE

    budget = Budget(
        papers_target=papers_target(),
        helpful_target=helpful_target(),
    )
    lifecycle = _load_lifecycle(budget)
    # reconcile step vs papers_swept for chunk size
    queue = load_queue()
    if lifecycle.is_goal_complete():
        print(json.dumps({"lifecycle": lifecycle.to_dict(), "status": "GOAL_COMPLETE"}, indent=2))
        lifecycle.write_atomically(LIFECYCLE_DIR)
        return

    cond = lifecycle.evaluate()
    if cond.value in ("end", "knowledge_stopped") and not lifecycle.is_goal_complete():
        print(json.dumps({"lifecycle": lifecycle.to_dict(), "status": f"parked:{cond.value}"}, indent=2))
        lifecycle.write_atomically(LIFECYCLE_DIR)
        return

    lifecycle.bump_step()
    # pick next paper(s) in queue
    # papers_swept tracks how many papers have been swept; chunk by CHUNK_SIZE
    # legacy steps 1-2 already swept W_0 and privacy-lambda (2 papers)
    idx = lifecycle.papers_swept  # start index in queue
    chunk = queue[idx : idx + CHUNK_SIZE] if idx < len(queue) else queue[lifecycle.step_count % len(queue) : lifecycle.step_count % len(queue) + 1]
    # fallback single-paper per step if queue shorter
    if not chunk:
        chunk = [queue[lifecycle.step_count % len(queue)]]

    results = []
    for paper in chunk:
        fid = paper.get("id", "unknown")
        # dedup: skip if this (step,fid) already logged
        try:
            if LOG.exists():
                for line in LOG.read_text().splitlines():
                    try:
                        j = json.loads(line)
                        if j.get("probe", {}).get("step") == lifecycle.step_count and j.get("probe", {}).get("formula") == fid:
                            raise StopIteration
                    except StopIteration:
                        raise
                    except Exception:
                        pass
                else:
                    pass
        except StopIteration:
            print(f"skip duplicate step {lifecycle.step_count} {fid}")
            continue
        obs = run_step(lifecycle, fid)
        results.append(obs)
        lifecycle.papers_swept += 1
        lifecycle.note_result(obs.get("status", obs.get("verdict", "RESET")))

    # aggregate chunk probe
    probe = results[0] if len(results) == 1 else {"chunk": results, "step": lifecycle.step_count}
    if len(results) == 1:
        probe = results[0]
    else:
        probe = {"formulas": [r.get("formula") for r in results], "chunk_results": results, "step": lifecycle.step_count, "verdict": "CHUNK", "status": "CHUNK"}

    lifecycle.write_atomically(LIFECYCLE_DIR)
    rec = {"ts": time.time(), "lifecycle": lifecycle.to_dict(), "probe": probe}
    print(json.dumps(_sanitize(rec), indent=2, allow_nan=False))
    _atomic_append_jsonl(LOG, rec)


if __name__ == "__main__":
    main()
