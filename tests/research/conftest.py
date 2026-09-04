import sys
from pathlib import Path

# research/ is not an installed package; make guard/locked/strategies importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "research"))
