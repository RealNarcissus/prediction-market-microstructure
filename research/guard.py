"""Guard: the locked harness must be byte-identical to its committed hash.

The loop CANNOT change folds, labels, metrics, or the seal. Any change here
requires a deliberate human commit that refreshes research/.locked-hash.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent
LOCKED_DIR = RESEARCH_DIR / "locked"
HASH_FILE = RESEARCH_DIR / ".locked-hash"


def locked_tree_hash() -> str:
    sha = hashlib.sha256()
    for path in sorted(LOCKED_DIR.rglob("*.py")):
        sha.update(str(path.relative_to(LOCKED_DIR)).encode())
        sha.update(path.read_bytes())
        sha.update(b"\x00")
    return sha.hexdigest()


def write_hash() -> None:
    HASH_FILE.write_text(locked_tree_hash() + "\n")


def verify(expect_hash: str | None = None) -> None:
    expected = (expect_hash or HASH_FILE.read_text().strip()) if HASH_FILE.exists() else None
    actual = locked_tree_hash()
    if expected is None:
        raise RuntimeError("no recorded hash: run `python research/guard.py --write` first")
    if actual != expected:
        raise RuntimeError(
            "LOCKED HARNESS MODIFIED — refusing to run. If this change is a "
            "deliberate human decision, refresh the hash with "
            "`python research/guard.py --write` and commit it explicitly."
        )


if __name__ == "__main__":
    if "--write" in sys.argv:
        write_hash()
        print(f"locked-hash refreshed: {locked_tree_hash()}")
    else:
        verify()
        print("locked harness intact:", locked_tree_hash())
