"""Shared test setup: put the repo root on sys.path so `import aura...` works
when pytest is run from the repo root (or anywhere)."""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
