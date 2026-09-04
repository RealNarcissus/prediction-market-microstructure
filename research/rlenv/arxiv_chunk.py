"""arXiv chunk index + regime-conditional evaluator (bucket-specific costs, Holm scope)."""
from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
QUEUE_PATH = REPO / "research" / "rlenv" / "paper_queue.yaml"

CHUNK_SIZE = 2
EPOCH_SEAL = "sealed_holdout_2026_H1"  # never touched here; epoch gate


def load_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        # fallback hardcoded queue (6) for offline runs
        return [
            {"id": "1306.6188", "title": "VPIN"},
            {"id": "2602.00776", "title": "crypto microstructure"},
            {"id": "2607.09426-imb-lag", "title": "Quarter-Hour imb lag"},
            {"id": "2605.04004", "title": "intraday momentum falsification"},
            {"id": "privacy-lambda", "title": "privacy-subsidy lambda"},
            {"id": "W_0", "title": "Cont OFI"},
        ]
    raw = yaml.safe_load(QUEUE_PATH.read_text()) or {}
    papers = raw.get("papers", [])
    # CHUNK_SIZE override from yaml config
    cfg = raw.get("config", {})
    global CHUNK_SIZE  # noqa: PLW0603
    if "chunk_size" in cfg:
        CHUNK_SIZE = int(cfg["chunk_size"])
    return papers


def _papers() -> list[dict]:
    return load_queue()


def next_chunk(chunk_idx: int) -> list[dict]:
    papers = _papers()
    s = chunk_idx * CHUNK_SIZE
    return papers[s : s + CHUNK_SIZE]


def regime_buckets(hz: str) -> list[dict]:
    vols = ["low", "mid", "high"]
    sessions = ["00-06", "06-12", "12-18", "18-24"]
    return [{"vol": v, "session": s, "hz": hz} for v in vols for s in sessions]


def total_cells() -> int:
    import math
    n = len(_papers())
    return math.ceil(n / CHUNK_SIZE) if n else 0


def papers_target() -> int:
    raw = yaml.safe_load(QUEUE_PATH.read_text()) if QUEUE_PATH.exists() else {}
    return int((raw or {}).get("config", {}).get("papers_target", len(_papers())))


def helpful_target() -> int:
    raw = yaml.safe_load(QUEUE_PATH.read_text()) if QUEUE_PATH.exists() else {}
    return int((raw or {}).get("config", {}).get("helpful_target", 3))
