"""Pytest configuration: make `src`'s modules importable as they are internally.

Code under src/ imports itself as top-level packages (e.g. `from models.models
import ...`, not `from src.models.models import ...`), so tests need `src/`
itself on sys.path rather than the repo root.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
