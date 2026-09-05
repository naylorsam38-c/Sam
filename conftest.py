"""Make both packages importable so `pytest` from the repo root runs all suites."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for package in ("specgate", "spec-writer", "hands"):
    sys.path.insert(0, str(ROOT / "packages" / package))
