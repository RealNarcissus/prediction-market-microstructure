import pytest
from pathlib import Path

@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
