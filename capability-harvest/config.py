"""
config.py — path resolution for the capability harvest pipeline.

Every other script in this pipeline imports this module for its paths and
calls print_roots(__file__) at startup. No script in this pipeline hardcodes
a path or assumes the current working directory — that was the root cause
identified in the prior handoff ("the recent problem with the 52-category
script being aimed at the wrong location"). Fixing that class of bug is the
whole job of this file.

----------------------------------------------------------------------------
CONFIG — the only thing you'd normally change here.
----------------------------------------------------------------------------
Set CAPABILITY_HARVEST_ROOT in the environment to point this whole pipeline
at a different project root (e.g. to run it against a second, parallel
harvest tree). Leave it unset to use "the directory this file lives in",
which is the default and normal case.
"""

import json
import os
from pathlib import Path


def _project_root() -> Path:
    override = os.environ.get("CAPABILITY_HARVEST_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parent


PROJECT_ROOT = _project_root()

# SOURCE_ROOT / APPLICATION_ROOT: where real cloned application checkouts
# land. Gitignored — these are fetched at runtime from the real open-source
# pool, never vendored into this repo wholesale.
SOURCE_ROOT = PROJECT_ROOT / "application_pool"
APPLICATION_ROOT = SOURCE_ROOT

# CATEGORY_SOURCE: the category taxonomy this run of discovery works from.
CATEGORY_SOURCE = PROJECT_ROOT / "categories" / "categories.json"

# REPOSITORY_SOURCE: the discovery stage's own output — which real repos
# were fetched, at which commit, under which licence. Every later stage
# reads this file rather than re-deriving it.
REPOSITORY_SOURCE = PROJECT_ROOT / "discovery" / "applications.json"

# OUTPUT_ROOT: general per-run output (attach-point records, build manifests,
# server logs from live test runs).
OUTPUT_ROOT = PROJECT_ROOT / "output"

# SHELF_ROOT / REGISTRY_ROOT: the harvested-capability shelf and the
# registry built from it. These ARE committed — they are the proof.
SHELF_ROOT = PROJECT_ROOT / "shelf"
REGISTRY_ROOT = PROJECT_ROOT / "capabilities"

# TEST_TARGET: where live-proof scripts and their recorded evidence live.
TEST_TARGET = PROJECT_ROOT / "test"

HARVEST_REQUESTS_ROOT = PROJECT_ROOT / "harvest_requests"

ALL_ROOTS = {
    "PROJECT_ROOT": PROJECT_ROOT,
    "SOURCE_ROOT": SOURCE_ROOT,
    "APPLICATION_ROOT": APPLICATION_ROOT,
    "CATEGORY_SOURCE": CATEGORY_SOURCE,
    "REPOSITORY_SOURCE": REPOSITORY_SOURCE,
    "OUTPUT_ROOT": OUTPUT_ROOT,
    "SHELF_ROOT": SHELF_ROOT,
    "REGISTRY_ROOT": REGISTRY_ROOT,
    "TEST_TARGET": TEST_TARGET,
    "HARVEST_REQUESTS_ROOT": HARVEST_REQUESTS_ROOT,
}

# Licence identifiers this pipeline will harvest from, and the literal text
# marker checked for in the repo's OWN LICENSE file (never npm/PyPI
# metadata, never a README badge). MPL-2.0 is included but every script
# that consults this table must treat it as `flagged`, not silently
# accepted — see discovery/discover_applications.py.
ALLOWED_LICENCE_MARKERS = {
    "MIT License": "MIT",
    "Apache License": "Apache-2.0",
    "BSD 2-Clause": "BSD-2-Clause",
    "BSD 3-Clause": "BSD-3-Clause",
    "ISC License": "ISC",
    "Mozilla Public License": "MPL-2.0",
}
LICENCES_REQUIRING_SIGN_OFF = {"MPL-2.0"}


def print_roots(caller: str) -> None:
    print(f"[{caller}] resolved paths (PROJECT_ROOT={PROJECT_ROOT}):")
    for name, path in ALL_ROOTS.items():
        exists = "exists" if Path(path).exists() else "missing"
        print(f"  {name:20s} = {path}  [{exists}]")


def ensure_dirs() -> None:
    for name in ("SOURCE_ROOT", "OUTPUT_ROOT", "SHELF_ROOT", "REGISTRY_ROOT", "TEST_TARGET", "HARVEST_REQUESTS_ROOT"):
        ALL_ROOTS[name].mkdir(parents=True, exist_ok=True)
    CATEGORY_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    REPOSITORY_SOURCE.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    ensure_dirs()
    print_roots("config.py")
