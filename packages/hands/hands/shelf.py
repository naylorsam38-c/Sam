"""Loads the Builder's parts shelf from its real location.

Shelf policy is reuse before rewrite, and a part is real running code at
its real location — so Hands imports these modules out of
`packages/builder/engines/` rather than keeping a copy. If the shelf moves
this fails loudly at import, which is the point: a silently vendored copy
would drift, and a drifted copy is exactly the "passes its own tests,
breaks at the seam" failure PLAN.md names.
"""

import importlib.util
import sys
from pathlib import Path

ENGINES_DIR = (Path(__file__).resolve().parents[2] / "builder" / "engines")


def _load(module_name):
    path = ENGINES_DIR / f"{module_name}.py"
    if not path.exists():
        raise ImportError(
            f"parts shelf engine {module_name!r} not found at {path} — Hands reuses the shelf's "
            f"real code and does not keep a copy of it")
    if str(ENGINES_DIR) not in sys.path:
        # the engines import each other by bare name (pdf_form_filling imports
        # document_generation), so their own directory has to be importable
        sys.path.insert(0, str(ENGINES_DIR))
    spec = importlib.util.spec_from_file_location(f"_hands_shelf_{module_name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pdf_form_filling = _load("pdf_form_filling")
document_signing = _load("document_signing")
audit_trail = _load("audit_trail")

# The exact part_ids this reuse binds to, for the shelf's own bookkeeping.
REUSED_PART_IDS = ("pdf_form_filling", "document_signing", "audit_trail")
