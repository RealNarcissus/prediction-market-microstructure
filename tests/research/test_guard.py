"""Guard integrity: tampering with locked/ must fail the verify."""
import pytest

import guard  # noqa: E402  (path set by conftest)

RESEARCH = guard.RESEARCH_DIR


def test_guard_passes_on_intact_tree():
    guard.verify()  # raises if anything drifted


def test_guard_fails_on_tamper(monkeypatch):
    victim = RESEARCH / "locked" / "metrics.py"
    original = victim.read_text()
    try:
        victim.write_text(original + "\n# tampered\n")
        with pytest.raises(RuntimeError, match="LOCKED HARNESS MODIFIED"):
            guard.verify()
    finally:
        victim.write_text(original)
    guard.verify()  # restored
