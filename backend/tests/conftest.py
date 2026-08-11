"""Pytest configuration: make `app`'s modules importable as they are internally.

Code under backend/app/ imports itself as top-level packages (e.g. `from
models.models import ...`, not `from app.models.models import ...`), so tests
need `backend/app/` itself on sys.path rather than the repo root.
"""

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
