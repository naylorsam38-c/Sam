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
        # build.py's runner: this app exposes create_app(); DB/mail config is
        # entirely env-var driven (the app's own designed extension point),
        # so build.py can point it at a fresh SQLite file and a local SMTP
        # debug server without touching the app's source at all.
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "needs_smtp": True,
            "readiness_path": "/login",
            "env": {
                "DATABASE_URL": "sqlite:///{db_path}",
                "FLASK_SECRET_KEY": "capability-harvest-build-run",
                "MAIL_SERVER": "{smtp_host}",
                "MAIL_PORT": "{smtp_port}",
                "MAIL_USE_TLS": "false",
                "MAIL_USE_SSL": "false",
            },
        },
    },
    {
        "slug": "inventory-tracker",
        "clone_url": "https://github.com/Antoh254/Inventory-Tracker.git",
        "ref": None,
        "category": "inventory",
        "why_selected": (
            "Single-file Flask + raw sqlite3 app, MIT licensed, one runtime "
            "dependency (flask only), no auth. Genuine stock adjustment: "
            "UPDATE products SET quantity = quantity +/- 1 gated by a real "
            "reorder_level column and an `action` form field (sell/restock)."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "app",
            "app_attr": "app",
            # init_db() runs at module import time (module-level call, not
            # gated behind __main__), so importing the module is enough to
            # get a fresh schema once the stale db file is removed.
            "reset_globs": ["inventory.db"],
            "readiness_path": "/",
        },
    },
    {
        "slug": "hostelfix",
        "clone_url": "https://github.com/makona-OG/hostelFix.git",
        "ref": None,
        "category": "hostel-booking",
        "why_selected": (
            "Real Flask + SQLAlchemy + SQLite student-hostel-booking app "
            "(live Render deployment linked in its own README), MIT "
            "licensed. Its GET /search route runs a genuine SQLAlchemy "
            "`.filter(Hostel.name.ilike(...))` query against a real Hostel "
            "model -- not a client-side filter -- and needs no auth."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "app",
            "app_attr": "app",
            "reset_globs": ["hostelfix.db", "instance/hostelfix.db"],
            # Unlike inventory-tracker, this app's table creation and demo
            # data are NOT side effects of importing app.py -- they're in
            # init_db.py / dummy_data.py, which the app's own README
            # documents running before first use. Running the app's own
            # scripts is not us inventing data; it's the fixture set the
            # app ships to be usable at all.
            "setup_scripts": ["init_db.py", "dummy_data.py"],
            "readiness_path": "/",
        },
    },
    {
        "slug": "habit-tracker",
        "clone_url": "https://github.com/batrisyiasafri/habit_tracker.git",
        "ref": None,
        "category": "habit-tracking",
        "why_selected": (
            "Single-file Flask + Flask-SQLAlchemy habit tracker, MIT "
            "licensed, no real auth (session user id hardcoded per the "
            "app's own 'demo purposes' comment/README). Genuine consecutive"
            "-day streak calculation (calculate_streaks) over real "
            "HabitLog.date rows, not a stub."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "app",
            "app_attr": "app",
            # Flask-SQLAlchemy resolves the relative sqlite:///habits.db
            # URI against the app's instance path, not the process cwd --
            # confirmed by inspecting which file actually holds the
            # habit/habit_log tables after a real run.
            "reset_globs": ["habits.db", "instance/habits.db", "instance/database.db"],
            "readiness_path": "/",
        },
    },
    {
        "slug": "flask-messenger",
        "clone_url": "https://github.com/jgoney/flask-messenger.git",
        "ref": None,
        "category": "messaging",
        "why_selected": (
            "Small Flask + raw sqlite3 message board with both a "
            "server-rendered form and an unauthenticated REST API, MIT "
            "licensed. _add_message() performs a genuine persisted INSERT, "
            "confirmed live (POST then GET returns the same row)."
        ),
        "runner": {
            # This app's schema creation is gated behind
            # `if __name__ == '__main__':` in messenger.py itself, so it
            # must be run as a script, not imported as a module -- we run
            # the app exactly the way its own author runs it, rather than
            # replicating that setup logic ourselves.
            "kind": "script_entrypoint",
            "entry_script": "messenger.py",
            "known_host": "127.0.0.1",
            "known_port": 5000,
            "reset_globs": ["main.db"],  # settings/settings_common.py: DB_NAME = 'main.db'
            "readiness_path": "/",
        },
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
            "runner": entry["runner"],
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
