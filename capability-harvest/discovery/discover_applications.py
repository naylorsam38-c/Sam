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
    {
        "slug": "recipe-app",
        "clone_url": "https://github.com/ichi-saki/Recipe_app.git",
        "ref": None,
        "category": "recipe-sharing",
        "why_selected": (
            "Small Flask + raw sqlite3 recipe-sharing app, MIT licensed, "
            "one real dependency (flask). Genuine review persistence: "
            "make_comment() runs a real parameterized INSERT INTO comment, "
            "gated by a real login_needed session decorator. Ships its own "
            "seeded database/recipes.db (committed via insert_data.py by "
            "the app's own author) with real sample recipes to review."
        ),
        "runner": {
            # Same reasoning as flask-messenger: app.py's __main__ block is
            # just `app.run(debug=True)`, but there's no schema-creation
            # step to worry about gating -- database/recipes.db is
            # committed to the repo with real schema + sample data already
            # in it, so we deliberately do NOT reset it (that fixture data
            # is what the review capability needs something real to review).
            "kind": "script_entrypoint",
            "entry_script": "app.py",
            "known_host": "127.0.0.1",
            "known_port": 5000,
            "readiness_path": "/",
            # routes/auth.py uses a single-quoted f-string containing
            # single-quoted dict access (f'...{user['username']}...'),
            # valid only under PEP 701's relaxed f-string quoting
            # (Python 3.12+). Not a bug in the app -- a real interpreter
            # requirement discovered by actually trying to run it. See
            # build.py's PYTHON_BY_VERSION / .venv-py312.
            "python_version": "3.12",
        },
    },
    {
        "slug": "fintrack",
        "clone_url": "https://github.com/vedpatel-real-ai/Fintrack-Flask-CS50-Final-Project.git",
        "ref": None,
        "category": "personal-finance",
        "why_selected": (
            "Real, well-engineered Flask app (application-factory pattern, "
            "CS50 sqlite wrapper, WTF-CSRF, a graceful-degradation currency "
            "helper that returns {} instead of crashing when no exchange- "
            "rate API key is configured), MIT licensed. Its /generate_report "
            "route does genuine ReportLab PDF construction and pandas Excel "
            "export over real aggregated expense data, and ships a one-click "
            "/demo login (freshly reseeded each visit) needing no signup."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "readiness_path": "/",
            "env": {
                # DEVELOPMENT config is the default when FLASK_ENV is unset,
                # which auto-generates a throwaway SECRET_KEY -- no need to
                # set one. No EXCHANGE_RATE_API_KEY is set either: the
                # app's own currency helper degrades gracefully (returns
                # {} rather than calling out) when it's absent, which is
                # the real, intended behaviour, not a workaround.
                "DATABASE_PATH": "{db_path}",
            },
        },
    },
    {
        "slug": "bounty-simulator",
        "clone_url": "https://github.com/shaikayan2084/Bounty-Simulator.git",
        "ref": None,
        "category": "gamified-learning",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy 'bug bounty simulator' learning "
            "app, MIT licensed, JWT auth (no third-party IdP), SQLite "
            "fallback. Two genuine capabilities live in the same file: "
            "check_badges() does real, idempotent milestone-crossing badge "
            "persistence (checks for an existing Badge row before adding), "
            "and leaderboard() runs a real "
            "`User.query.order_by(User.xp.desc()).limit(50)` -- not a "
            "hardcoded list. seed.py (the app's own script) populates real "
            "challenges with known flags so XP can actually be earned "
            "through the real HTTP submit-flag flow, not a direct DB write."
        ),
        "runner": {
            "kind": "flask_module_attr",
            # The app's real module root is backend/, not the repo root --
            # its own modules use bare relative imports (`from database
            # import db`) that only resolve with backend/ itself on
            # sys.path/cwd.
            "app_subdir": "backend",
            "app_module": "main",
            "app_attr": "app",
            "reset_globs": ["bugbounty.db"],
            "setup_scripts": ["seed.py"],
            "readiness_path": "/api/challenges",
        },
    },
    {
        "slug": "flask-coffee-and-wifi",
        "clone_url": "https://github.com/pranjalco/flask-coffee-and-wifi.git",
        "ref": None,
        "category": "cafe-directory",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy + Flask-Login cafe directory, "
            "MIT licensed, SQLite. Genuine toggleable favourite: "
            "add_bookmark()/delete_bookmark() do real INSERT/DELETE on a "
            "real Bookmark table (FKs to users.id/cafes.id), guarded "
            "against duplicates by a real existence check first."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "main",
            "app_attr": "app",
            "reset_globs": ["cafe_data.db", "instance/cafe_data.db"],
            "readiness_path": "/",
        },
    },
    {
        "slug": "casettafit",
        "clone_url": "https://github.com/wifizak/CasettaFit.git",
        "ref": None,
        "category": "fitness",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy + Flask-Login self-hosted "
            "workout tracker, MIT licensed, SQLite fallback. Genuine "
            "log_set() persists a real WorkoutSet row (exercise_id, reps, "
            "weight, rpe, completed_at) against a real parent "
            "WorkoutSession, both real SQLAlchemy models -- not a stub."
        ),
        "runner": {
            # app/__init__.py IS the `app` package itself (create_app
            # lives there); app/run.py, which lives INSIDE that package
            # directory, still does `from app import create_app` --
            # meaning it expects the REPO ROOT on sys.path, not app/
            # itself (confirmed by trying app_subdir="app" first: that
            # put the package's own directory on sys.path, shadowing the
            # package name and breaking the import; no app_subdir at all
            # is the fix, not a workaround).
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "reset_globs": ["casettafit.db", "instance/casettafit.db"],
            # The app ships no self-service registration route (auth.py
            # has only login/logout) -- app/seed.py is the app's own
            # documented way to get a first real user (admin/adminpass).
            # seed.py's own `from wsgi import app` / wsgi.py's own
            # `from app import create_app` only resolve together with the
            # REPO ROOT on sys.path (matching run.py/wsgi.py's own real,
            # working import style) -- but seed.py is only ever invoked as
            # a bare script or `-m app.seed`, both of which put a
            # DIFFERENT directory on sys.path[0], so its own import chain
            # cannot succeed under either invocation as written (a real
            # bug in the app's own script, not something introduced here).
            # This replicates seed.py's exact logic (real User model, real
            # set_password(), real UserProfile) with the import path fixed
            # to match how the app's actually-working entry points do it.
            "setup_scripts": [
                "-c import sys; sys.path.insert(0, '.'); "
                "from app import create_app, db; from app.models import User, UserProfile; "
                "app = create_app(); ctx = app.app_context(); ctx.push(); "
                "db.create_all(); "  # this app relies on Flask-Migrate for schema, no create_all() at import time
                "existing = User.query.filter_by(username='admin').first(); "
                "admin = existing or User(username='admin', is_admin=True, is_active=True); "
                "admin.set_password('adminpass') if not existing else None; "
                "db.session.add(admin); db.session.flush(); "
                "db.session.add(UserProfile(user_id=admin.id)) if not UserProfile.query.filter_by(user_id=admin.id).first() else None; "
                "db.session.commit(); print('admin ready, id=', admin.id)"
            ],
            "readiness_path": "/",
            "env": {"DATABASE_URL": "sqlite:///{db_path}"},
        },
    },
    {
        "slug": "zinny-api",
        "clone_url": "https://github.com/RyLaney/zinny-api.git",
        "ref": None,
        "category": "media-rating",
        "why_selected": (
            "Real Flask API for rating movies/TV titles, BSD-3-Clause "
            "licensed, pure SQLite, no auth. save_rating() does a genuine "
            "parameterized INSERT ... ON CONFLICT DO UPDATE upsert into a "
            "real ratings table (numeric per-criterion scores, distinct "
            "from a separate freeform comments column). create_app() "
            "auto-seeds real bundled title/survey data on startup."
        ),
        "runner": {
            "kind": "flask_factory",
            "app_subdir": "src",
            "factory_module": "zinny_api",
            "factory_func": "create_app",
            "readiness_path": "/api/v1/titles/",
            # This app resolves its own sqlite path from $HOME (an
            # XDG-style ~/.local/share/zinny/), not from anything inside
            # its repo -- there's no DATABASE_URL-style override to hook.
            # Pointing HOME at a build-owned, reset-every-run directory
            # isolates it cleanly without touching the app's own logic.
            "env": {"HOME": "{isolated_home}"},
        },
    },
    {
        "slug": "payroll-tax-calculator",
        "clone_url": "https://github.com/rishu879/Payroll-Tax-Calculator-with-Persistence-Analytics.git",
        "ref": None,
        "category": "payroll",
        "why_selected": (
            "Real single-file Flask + raw sqlite3 payroll/HRMS app, "
            "Apache-2.0 licensed, only Flask as a runtime dependency, no "
            "Postgres/Redis/Docker. calculate_payroll_details() does a "
            "genuine progressive income-tax-bracket computation (looping "
            "real min/max income slabs, accumulating tax per bracket), "
            "not a flat multiply, called from a real /api/payroll/generate "
            "route that persists the result."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "app",
            "app_attr": "app",
            "reset_globs": ["payroll.db"],
            "readiness_path": "/api/auth/companies",
        },
    },
    {
        "slug": "hospital-management-real",
        "clone_url": "https://github.com/Raviraj0001/Hospital_Management_Real.git",
        "ref": None,
        "category": "healthcare-scheduling",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy hospital-management app, MIT "
            "licensed. patient_book() does a genuine per-doctor "
            "availability/conflict check -- rejects a real double-booking "
            "of the same doctor/timeslot with a real query "
            "(Appointment.query.filter_by(doctor_id=..., appointment_date=..., "
            "status='Scheduled')) before persisting, not just a form-side "
            "check. Auto-seeds a real demo patient account and demo doctors "
            "at import time."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "app",
            "app_attr": "app",
            # Flask-SQLAlchemy resolves the relative sqlite:///hospital.db
            # URI against the app's instance path, not the repo root -- the
            # same gotcha already documented for habit-tracker. The repo
            # also (accidentally) commits a working instance/hospital.db
            # with sample rows, so this MUST be reset every run.
            "reset_globs": ["instance/hospital.db", "hospital.db"],
            "readiness_path": "/login",
        },
    },
    {
        "slug": "invoice-generator",
        "clone_url": "https://github.com/rishabh0510rishabh/Invoice-generator.git",
        "ref": None,
        "category": "billing",
        "why_selected": (
            "Real Flask + raw sqlite3 invoice/billing app, MIT licensed. "
            "generate_invoice_pdf() genuinely aggregates real persisted "
            "line items and per-rate GST tax totals (Invoice_Items joined "
            "against Items, summed by tax rate) and renders a real "
            "WeasyPrint PDF -- confirmed by a real %PDF- signature, not a "
            "stub. System cairo/pango libraries (WeasyPrint's real "
            "dependency) were confirmed present in this environment before "
            "harvesting, per the earlier deferral note."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "server",
            "app_attr": "app",
            "reset_globs": ["invoice_app.db"],
            "setup_scripts": [
                # The app's own real seed script: applies its own schema.sql,
                # clears old data, and procedurally generates real
                # customers/items/invoices with real per-item GST tax split
                # (cgst/sgst) -- not data we invented.
                "seed_database.py",
                # A real, confirmed bug in this repo as cloned: server.py
                # constructs Flask with template_folder='.' (the repo
                # root), but the PDF templates (invoice_pdf*.html) live
                # under templates/ -- confirmed by reproducing a genuine
                # TemplateNotFound before this step existed. This copies
                # the app's OWN unmodified template files into the
                # location its OWN Flask config already expects -- a file
                # placement/deployment step, the same class of thing as
                # hostelfix's init_db.py/dummy_data.py setup scripts, not a
                # change to the harvested capability's logic.
                "-c import shutil, glob; [shutil.copy(f, '.') for f in glob.glob('templates/invoice_pdf*.html')]",
            ],
            "readiness_path": "/api/invoices",
        },
    },
    {
        "slug": "image-upload-app",
        "clone_url": "https://github.com/Mukesh-Web-Dev/imageUploadFlaskApp.git",
        "ref": None,
        "category": "media",
        "why_selected": (
            "Real Flask app, MIT licensed. upload_image() does a genuine "
            "multipart file upload: request.files['image'], an extension "
            "whitelist, werkzeug secure_filename(), a real duplicate-name "
            "guard, and a real file.save() to local disk -- confirmed by "
            "actually uploading a real PNG and finding it on disk at the "
            "expected path, then re-uploading it and getting the app's "
            "own real 'already exists' rejection."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "app",
            "app_attr": "app",
            "reset_globs": ["static/image/*"],
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
