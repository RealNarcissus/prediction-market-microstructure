"""Smoke: one loop step is deterministic and writes valid JSON."""
import json
import sys
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "research"))

from rlenv.harness import Budget, Lifecycle
from rlenv.loop_formula import _sanitize, run_step


def test_sanitize_nan_to_null():
    raw = {"a": float("nan"), "b": [1, float("inf"), 2], "c": {"d": float("-inf")}}
    clean = _sanitize(raw)
    assert clean["a"] is None
    assert clean["b"] == [1, None, 2]
    assert clean["c"]["d"] is None
    # strict JSON round-trips
    line = json.dumps(clean, allow_nan=False)
    assert json.loads(line) == clean
    assert "NaN" not in line


def test_lifecycle_atomic_write(tmp_path: Path):
    lc = Lifecycle(budget=Budget(papers_target=20, helpful_target=3))
    lc.bump_step()
    lc.papers_swept = 2
    lc.write_atomically(tmp_path)
    assert (tmp_path / "lifecycle.json").exists()
    loaded = Lifecycle.load(tmp_path, Budget(papers_target=20, helpful_target=3))
    assert loaded is not None
    assert loaded.step_count == 1
    assert loaded.papers_swept == 2


def test_lifecycle_goal_complete():
    b = Budget(papers_target=2, helpful_target=1)
    lc = Lifecycle(budget=b)
    assert not lc.is_goal_complete()
    lc.papers_swept = 2
    assert not lc.is_goal_complete()
    lc.helpful_count = 1
    assert lc.is_goal_complete()
    # open-ended never completes
    assert not Lifecycle(budget=Budget()).is_goal_complete()


def test_knowledge_stopped():
    b = Budget(papers_target=20, helpful_target=3)
    lc = Lifecycle(budget=b, knowledge_stall_steps=3)
    lc.note_result("RESET")
    lc.note_result("RESET")
    assert lc.evaluate().value == "learning_progress"
    lc.note_result("RESET")
    assert lc.evaluate().value == "knowledge_stopped"
    lc.note_result("KEEP")
    assert lc.evaluate().value == "learning_progress"
    assert lc.helpful_count == 1
