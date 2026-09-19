#!/usr/bin/env python3
"""
discover_applications.py — Application Discovery + Application Repository.

Clones real open-source applications into SOURCE_ROOT, resolves the exact
commit fetched, and reads licence from the repository's OWN LICENSE file
(never from a description, a topic tag, or any other metadata). Writes
REPOSITORY_SOURCE (discovery/applications.json) as the source of truth every
later stage reads from.

Run: python3 discovery/discover_applications.py
(paths are resolved by config.py, not by cwd — run this from anywhere)
"""

import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

# ----------------------------------------------------------------------------
# CONFIG — edit this block to change what gets discovered. Walking-skeleton
# scope: exactly one real application. Add more entries to widen discovery;
# each needs a real, reachable git URL. Licence is NEVER read from this list —
# it is read from the cloned repo's own LICENSE file below, every time.
# ----------------------------------------------------------------------------
APPLICATION_MANIFEST = [
    {
        "slug": "monthly-expenses-tracker",
        "clone_url": "https://github.com/NHasan143/monthly-expenses-tracker.git",
        "ref": None,  # None = default branch HEAD at clone time; set a commit sha to pin it
        "category": "personal-finance",
        "why_selected": (
            "Real, working Flask app (flask-login auth + flask-sqlalchemy models, "
            "SQLite dev fallback so no external DB is required) with a genuine CSV "
            "export route (GET /export, app/routes.py) protected by @login_required. "
            "13 stars, actively maintained, MIT-licensed per its own LICENSE file."
        ),
    },
]
# Common LICENSE filenames to look for, in priority order.
LICENSE_FILENAMES = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt"]
# ----------------------------------------------------------------------------


def _run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result.stdout.strip()


def _clone_or_update(entry: dict, dest: Path) -> None:
    if dest.exists():
        print(f"  [{entry['slug']}] checkout already present at {dest}, fetching latest")
        _run(["git", "fetch", "origin"], cwd=dest)
        ref = entry["ref"] or "origin/HEAD"
        _run(["git", "checkout", ref], cwd=dest)
    else:
        print(f"  [{entry['slug']}] cloning {entry['clone_url']} -> {dest}")
        _run(["git", "clone", entry["clone_url"], str(dest)])
        if entry["ref"]:
            _run(["git", "checkout", entry["ref"]], cwd=dest)


def _detect_licence(dest: Path):
    for name in LICENSE_FILENAMES:
        candidate = dest / name
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8", errors="replace")
            for marker, licence_id in config.ALLOWED_LICENCE_MARKERS.items():
                if marker in text:
                    return {
                        "licence_id": licence_id,
                        "licence_file": name,
                        "marker_matched": marker,
                        "flagged": licence_id in config.LICENCES_REQUIRING_SIGN_OFF,
                    }
            return {
                "licence_id": None,
                "licence_file": name,
                "marker_matched": None,
                "flagged": False,
                "blocked_reason": f"{name} present but did not match any allowed licence marker — not guessed, recorded as blocked",
            }
    return {
        "licence_id": None,
        "licence_file": None,
        "marker_matched": None,
        "flagged": False,
        "blocked_reason": "no LICENSE file found in the repository root",
    }


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    config.ensure_dirs()
    config.print_roots(__file__)

    records = []
    for entry in APPLICATION_MANIFEST:
        dest = config.SOURCE_ROOT / entry["slug"]
        _clone_or_update(entry, dest)

        commit = _run(["git", "rev-parse", "HEAD"], cwd=dest)
        licence = _detect_licence(dest)

        record = {
            "slug": entry["slug"],
            "clone_url": entry["clone_url"],
            "category": entry["category"],
            "why_selected": entry["why_selected"],
            "resolved_commit": commit,
            "cloned_path": str(dest),
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "licence": licence,
            "blocked": licence["licence_id"] is None,
        }
        if licence["licence_file"]:
            record["licence"]["file_sha256"] = _sha256_of_file(dest / licence["licence_file"])

        status = "BLOCKED" if record["blocked"] else f"OK ({licence['licence_id']})"
        print(f"  [{entry['slug']}] commit={commit[:12]} licence={status}")
        records.append(record)

    config.write_json(config.REPOSITORY_SOURCE, {"applications": records})
    print(f"Wrote {config.REPOSITORY_SOURCE}")

    blocked = [r for r in records if r["blocked"]]
    if blocked:
        print(f"WARNING: {len(blocked)} application(s) blocked on licence — see discovery/applications.json for reasons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
