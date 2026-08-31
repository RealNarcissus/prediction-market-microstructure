"""5-state harness lifecycle + budget instrumentation.

State mapping (per user design — explicit fifth state added):
  step    = outer iteration weights update (long, you tune with it)
  episode = prediction window (single 5m/15m horizon)
  epoch   = walk-forward split (expanding-window folds, seal = holdout gate)
  chunk   = batch of what the loop reads (vol/time-of-day slice, or N papers)
  session = total wall-clock (the "until I stop" budget)

Conditions (exposed per turn):
  learning_progress  — running, still traversing
  knowledge_stopped  — halted on same data (no forward progress condition met)
  end                — session or step budget exhausted
  Your explicit halt always wins — none of the above overrides it.

Invariant: budget_exhausted never implies correctness. It only signals the
tool should keep running; only your marking GOAL_COMPLETE is completion.
Loop with hard budget: papers_target + helpful_target govern GOAL_COMPLETE.
END from Budget does not imply success — only both targets met does.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Condition(Enum):
    LEARNING_PROGRESS = "learning_progress"
    KNOWLEDGE_STOPPED = "knowledge_stopped"
    END = "end"  # budget exhausted, not success


@dataclass
class Budget:
    step_budget: int | None = None
    session_wall_seconds: float | None = None
    papers_target: int | None = None
    helpful_target: int | None = None  # how many KEEP promotions to find


@dataclass
class Lifecycle:
    budget: Budget
    step_count: int = 0
    session_start: float = field(default_factory=time.monotonic)
    papers_swept: int = 0
    helpful_count: int = 0
    rlenv_steps_taken: int = 0
    last_progress_at: float = field(default_factory=time.monotonic)
    knowledge_stall_steps: int = 8
    _stall_counter: int = 0  # consecutive RESET+DEFERRED with no KEEP

    def elapsed_session(self) -> float:
        return time.monotonic() - self.session_start

    def evaluate(self) -> Condition:
        if self.budget.session_wall_seconds is not None:
            if self.elapsed_session() >= self.budget.session_wall_seconds:
                return Condition.END
        if self.budget.step_budget is not None:
            if self.step_count >= self.budget.step_budget:
                return Condition.END
        if self._stall_counter >= self.knowledge_stall_steps:
            return Condition.KNOWLEDGE_STOPPED
        return Condition.LEARNING_PROGRESS

    def is_goal_complete(self) -> bool:
        """GOAL_COMPLETE only when both paper sweep and helpful targets met.
        If targets are None (unbounded loop), never completes on its own —
        human halt wins.
        """
        papers_ok = (
            self.budget.papers_target is None
            or self.papers_swept >= self.budget.papers_target
        )
        helpful_ok = (
            self.budget.helpful_target is None
            or self.helpful_count >= self.budget.helpful_target
        )
        # if both targets are None, loop is open-ended — never GOAL_COMPLETE
        if self.budget.papers_target is None and self.budget.helpful_target is None:
            return False
        return papers_ok and helpful_ok

    def note_result(self, status: str) -> None:
        """Call after each step with status RESET|DEFERRED|KEEP|NEAR_PROMOTE."""
        if status in ("KEEP", "NEAR_PROMOTE"):
            self.helpful_count += 1
            self._stall_counter = 0
            self.note_progress()
        elif status in ("RESET", "DEFERRED"):
            self._stall_counter += 1
        else:
            self._stall_counter += 1
        self.rlenv_steps_taken += 1

    def bump_step(self) -> None:
        self.step_count += 1

    def note_progress(self) -> None:
        self.last_progress_at = time.monotonic()

    def to_dict(self) -> dict:
        return {
            "step": self.step_count,
            "papers_swept": self.papers_swept,
            "helpful_count": self.helpful_count,
            "rlenv_steps_taken": self.rlenv_steps_taken,
            "session_elapsed_s": round(self.elapsed_session(), 1),
            "condition": self.evaluate().value,
            "goal_complete": self.is_goal_complete(),
            "stall_counter": self._stall_counter,
            "budget": {
                "step_budget": self.budget.step_budget,
                "session_wall_seconds": self.budget.session_wall_seconds,
                "papers_target": self.budget.papers_target,
                "helpful_target": self.budget.helpful_target,
            },
        }

    def state_path(self, base: Path) -> Path:
        return base / "lifecycle.json"

    def write_atomically(self, base: Path) -> None:
        """Write lifecycle.json atomically (tmp + fsync + rename)."""
        import os
        import tempfile

        p = self.state_path(base)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(self.to_dict(), indent=2)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".lifecycle.")
        try:
            with open(fd, "w") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.rename(tmp, p)
        finally:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass

    @classmethod
    def load(cls, base: Path, budget: Budget | None = None) -> "Lifecycle | None":
        p = base / "lifecycle.json"
        if not p.exists():
            return None
        try:
            raw = json.loads(p.read_text())
            lc = cls(
                budget=budget or Budget(),
                step_count=int(raw.get("step", 0)),
                papers_swept=int(raw.get("papers_swept", 0)),
                helpful_count=int(raw.get("helpful_count", 0)),
                rlenv_steps_taken=int(raw.get("rlenv_steps_taken", 0)),
            )
            lc._stall_counter = int(raw.get("stall_counter", 0))
            return lc
        except Exception:
            return None
