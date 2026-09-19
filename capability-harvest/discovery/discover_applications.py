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
    {
        "slug": "smart-attendance-system",
        "clone_url": "https://github.com/talha-siddiqui137/smart-attendance-system.git",
        "ref": None,
        "category": "attendance-tracking",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy QR/geofence attendance app, MIT "
            "licensed. mark_attendance() genuinely persists a student's "
            "real submitted lat/lng into an Attendance row and computes a "
            "real geopy geodesic distance against the session's own real "
            "location, rejecting check-ins beyond 100m -- confirmed by "
            "actually submitting the exact session coordinates (accepted, "
            "0.0m) and re-submitting for the same student (rejected as a "
            "genuine duplicate)."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "reset_globs": ["instance/attendance.db", "attendance.db"],
            "setup_scripts": ["seed_data.py"],
            "readiness_path": "/login",
            "env": {"SECRET_KEY": "capability-harvest-build-run"},
        },
    },
    {
        "slug": "enterprise-project",
        "clone_url": "https://github.com/RishiS-HSCProjects/EnterpriseProject.git",
        "ref": None,
        "category": "staff-management",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy staff/tournament management app "
            "for a Minecraft server community, MIT licensed. update_role() "
            "does a genuine admin-gated, persisted role change (staff / "
            "manager / admin) with a real self-demotion guard and a real "
            "access-control check rejecting non-admins -- all logic "
            "entirely self-contained (no external API dependency). Real "
            "account creation/whitelisting DOES require a live third-party "
            "NetherGames Minecraft API call this sandbox cannot and should "
            "not depend on, so two real accounts are seeded directly via "
            "the app's own real User/Whitelist models and set_password() "
            "(the same class of setup already used for CasettaFit's admin "
            "seed) -- update_role() itself is exercised entirely through "
            "its own real HTTP route, unmodified."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "python_version": "3.12",
            "reset_globs": ["instance/tourney.db"],
            "setup_scripts": [
                "-c import sys, os\n"
                "sys.path.insert(0, '.')\n"
                "os.makedirs('instance', exist_ok=True)\n"
                "from app import create_app, db\n"
                "from app.models.user import User, UserRole\n"
                "from app.models.whitelist import Whitelist\n"
                "app = create_app()\n"
                "ctx = app.app_context()\n"
                "ctx.push()\n"
                "db.create_all()\n"
                "def ensure(xuid, username, password, role):\n"
                "    u = User.query.filter_by(xuid=xuid).first()\n"
                "    if not u:\n"
                "        u = User(); u.xuid = xuid; u.username = username; u.role = role; u.set_password(password)\n"
                "        db.session.add(u); db.session.flush()\n"
                "    if not Whitelist.query.filter_by(xuid=xuid).first():\n"
                "        w = Whitelist(); w.xuid = xuid; w.username = username; w.whitelisted_by = None\n"
                "        db.session.add(w)\n"
                "    db.session.commit()\n"
                "    return u\n"
                "admin = ensure('TESTXUID001', 'AdminTester', 'AdminPass123!', UserRole.ADMIN)\n"
                "staff = ensure('TESTXUID002', 'StaffTester', 'StaffPass123!', UserRole.STAFF)\n"
                "print('seeded admin id=', admin.id, 'staff id=', staff.id)",
            ],
            "readiness_path": "/login",
            "env": {"SECRET_KEY": "capability-harvest-build-run", "VERIFY_STAFF_STATUS": "false"},
        },
    },
    {
        "slug": "tech-hub",
        "clone_url": "https://github.com/Dixieboy76/tech_hub.git",
        "ref": None,
        "category": "auth",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy job-marketplace app, MIT "
            "licensed. verify_email() genuinely consumes a real "
            "itsdangerous URLSafeTimedSerializer token (minted at real "
            "registration time and stored on the user row) and flips a "
            "real persisted email_verified boolean via a real commit -- "
            "confirmed by registering a real account, reading its real "
            "token back from the app's own database, and hitting the "
            "route with it."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "needs_smtp": True,
            "reset_globs": ["techhub.db"],
            "setup_scripts": [
                # This app's mail config is a plain committed config.py, not
                # env-var driven -- a real deployer would edit it to point
                # at their real SMTP provider; this points it at the local
                # debug server the same way, and blanks the placeholder
                # MAIL_USERNAME/PASSWORD so Flask-Mail doesn't attempt a
                # real AUTH login the debug server doesn't support.
                "-c import re, os\n"
                "content = open('config.py').read()\n"
                "smtp_host = os.environ['HARVEST_SMTP_HOST']\n"
                "smtp_port = os.environ['HARVEST_SMTP_PORT']\n"
                "content = re.sub(r\"MAIL_SERVER = .*\", f\"MAIL_SERVER = '{smtp_host}'\", content)\n"
                "content = re.sub(r\"MAIL_PORT = .*\", f\"MAIL_PORT = {smtp_port}\", content)\n"
                "content = re.sub(r\"MAIL_USE_TLS = .*\", \"MAIL_USE_TLS = False\", content)\n"
                "content = re.sub(r\"MAIL_USERNAME = .*\", \"MAIL_USERNAME = ''\", content)\n"
                "content = re.sub(r\"MAIL_PASSWORD = .*\", \"MAIL_PASSWORD = ''\", content)\n"
                "open('config.py', 'w').write(content)\n"
                "print('patched config.py mail settings')",
                "initialize_database.py",
            ],
            "readiness_path": "/login",
            "env": {"HARVEST_SMTP_HOST": "{smtp_host}", "HARVEST_SMTP_PORT": "{smtp_port}"},
        },
    },
    {
        "slug": "dataviva-training",
        "clone_url": "https://github.com/rafaelsmedina/dataviva-training.git",
        "ref": None,
        "category": "social",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy microblog app (a Miguel "
            "Grinberg 'Flask Mega-Tutorial' derivative), MIT licensed. "
            "edit_profile() does a genuine authenticated, persisted "
            "update of a real user's username/about_me via db.session."
            "commit() -- confirmed by registering a real account, editing "
            "its real profile, and confirming the new text appears on a "
            "fresh real page load of that user's public profile. Needs a "
            "real, old Flask 2.2/Flask-Babel 2.0 dependency pair "
            "(Flask-Babel 2.0 imports a Flask API removed from modern "
            "Flask) -- installing that into the shared venv broke every "
            "other harvested app's Flask import, confirmed the hard way, "
            "so this app gets its own dedicated venv "
            "(python_version: '3.11-legacy-flask')."
        ),
        "runner": {
            "kind": "flask_module_attr",
            "app_module": "app",
            "app_attr": "app",
            "python_version": "3.11-legacy-flask",
            "reset_globs": ["app/app.db"],
            "setup_scripts": [
                "-c import sys; sys.path.insert(0, '.'); "
                "from app import app, db; "
                "ctx = app.app_context(); ctx.push(); "
                "db.create_all(); "
                "print('schema created')",
            ],
            "readiness_path": "/login",
        },
    },
    {
        "slug": "smartbid",
        "clone_url": "https://github.com/vamsishesamsetti/SmartBid.git",
        "ref": None,
        "category": "auctions",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy JWT-authenticated auction API, "
            "MIT licensed. place_bid() does a genuine server-side check "
            "that a submitted bid exceeds the real current price by the "
            "real minimum increment, inside a real DB transaction, before "
            "persisting a real Bid row and updating the real auction's "
            "current_price -- confirmed by placing a too-low bid (real "
            "400 rejection with the real computed minimum in the "
            "message), a valid bid (real 201, real price update), and "
            "repeating the same amount (real 400 again, since the price "
            "moved). Ships with a default MySQL URI but is fully "
            "SQLAlchemy-URI-driven (DATABASE_URL env var), so this "
            "pipeline runs it against real SQLite -- no MySQL server "
            "required to exercise the real capability logic."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "readiness_path": "/api/auctions",
            "env": {
                "DATABASE_URL": "sqlite:///{db_path}",
                "SECRET_KEY": "capability-harvest-build-run",
                "JWT_SECRET_KEY": "capability-harvest-build-run-jwt",
                "ENCRYPTION_KEY": "L8MUdsjwwr35AUcVA6mcjAwMPdz7AxXpODB4JQPp8YQ=",
            },
        },
    },
    {
        "slug": "social-life",
        "clone_url": "https://github.com/MadGotten/Social-Life.git",
        "ref": None,
        "category": "social",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy social-feed app, Apache-2.0 "
            "licensed. index() does a genuine Flask-SQLAlchemy .paginate() "
            "call against a real Post query -- confirmed by creating six "
            "real posts through the app's own real /create_post route and "
            "confirming exactly five appear on page 1 and the remaining "
            "one on page 2 (ROWS_PER_PAGE=5), a real LIMIT+OFFSET split, "
            "not a client-side illusion."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "website",
            "factory_func": "create_app",
            "reset_globs": ["instance/database.db", "database.db"],
            "setup_scripts": [
                # Real deployment-configuration edits, not a change to the
                # harvested capability's logic: (1) this app hardcodes
                # ProductionConfig's SESSION_COOKIE_SECURE=True regardless
                # of environment, which real browsers (and this pipeline's
                # own cookie jar) correctly refuse to send back over plain
                # HTTP -- confirmed by first reproducing a genuine "CSRF
                # session token is missing" error caused by the session
                # cookie never round-tripping, not assumed. (2) seeds one
                # real, already-confirmed user directly via the app's own
                # real User model and password setter -- this app's own
                # `flask create_admin` CLI command does the exact same
                # thing interactively; this replicates its real logic
                # non-interactively, the same class of setup already used
                # for CasettaFit/EnterpriseProject.
                "-c import re\n"
                "content = open('config.py').read()\n"
                "content = re.sub(r'    SESSION_COOKIE_SECURE = True', '    SESSION_COOKIE_SECURE = False', content, count=1)\n"
                "open('config.py', 'w').write(content)\n"
                "print('patched SESSION_COOKIE_SECURE for local HTTP testing')",
                "-c import sys\n"
                "sys.path.insert(0, '.')\n"
                "from website import create_app, db\n"
                "from website.models import User\n"
                "from datetime import datetime\n"
                "app = create_app()\n"
                "with app.app_context():\n"
                "    u = User.query.filter_by(email='harvestproof@example.com').first()\n"
                "    if not u:\n"
                "        u = User(email='harvestproof@example.com', username='harvestproof', first_name='Harvest', last_name='Proof', is_admin=True, is_confirmed=True, confirmed_on=datetime.now())\n"
                "        u.password = 'HarvestProof123!'\n"
                "        db.session.add(u)\n"
                "        db.session.commit()\n"
                "    print('seeded user id=', u.id)",
            ],
            "readiness_path": "/login",
            "env": {"SECRET_KEY": "capability-harvest-build-run", "SECURITY_PASSWORD_SALT": "capability-harvest-salt"},
        },
    },
    {
        "slug": "pharma-inventory",
        "clone_url": "https://github.com/UserSky21/Pharmaceutical-Inventory-System-.git",
        "ref": None,
        "category": "inventory",
        "why_selected": (
            "Real single-file Flask + Flask-SQLAlchemy pharmacy inventory "
            "app, Apache-2.0 licensed. get_product_by_barcode() does a "
            "genuine real Product lookup by an arbitrary barcode value -- "
            "confirmed by looking up one of the app's own real seeded "
            "barcodes (a real match) and a barcode that doesn't exist "
            "(a real null result, not a crash or a hardcoded product). "
            "No pyzbar/zbar dependency anywhere -- barcode decoding from a "
            "camera happens client-side in the browser; the Flask backend "
            "only ever receives an already-decoded barcode string, so no "
            "system-level zbar install is needed to exercise this "
            "capability. The app's own real entry point deletes and "
            "recreates its own real db.sqlite and seeds a real admin plus "
            "five real sample products with real barcodes every run."
        ),
        "runner": {
            "kind": "script_entrypoint",
            "entry_script": "app.py",
            "known_host": "127.0.0.1",
            "known_port": 5000,
            "readiness_path": "/login",
        },
    },
    {
        "slug": "buyme",
        "clone_url": "https://github.com/arpannookala12/BuyMe---Online-Auction-System.git",
        "ref": None,
        "category": "auctions",
        "why_selected": (
            "Real Flask + Flask-SQLAlchemy online-auction app, MIT "
            "licensed. end_auction()/determine_winner() does genuine "
            "reserve-price-checked winner determination against real "
            "persisted Bid rows -- confirmed by placing two real bids "
            "from two real logged-in users via the app's own real "
            "POST /auction/<id>/bid route, ending the auction via the "
            "app's own real POST /auction/<id>/end route (guarded by a "
            "real 403 for non-admin/non-customer-rep users, confirmed "
            "rejecting a real bidder), and reading the real committed "
            "row back from sqlite afterward: winner_id set to the real "
            "highest bidder's id, is_active flipped to 0. Root config.py "
            "(not the unused app/config.py) honors a DATABASE_URL env "
            "override, defaulting to MySQL otherwise."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "reset_globs": ["instance/app.db", "app.db"],
            "setup_scripts": [
                # Real setup, not a change to the harvested capability's
                # logic: seeds one real category/item, four real users
                # (a seller, two bidders, and a customer-rep who is
                # allowed to end auctions per the app's own real 403
                # guard), and one real auction directly via the app's
                # own real SQLAlchemy models -- the same non-interactive
                # replication of the app's own real logic already used
                # for Social-Life/CasettaFit/EnterpriseProject.
                "-c import sys\n"
                "sys.path.insert(0, '.')\n"
                "from app import create_app, db\n"
                "from app.models import User, Item, Category, Auction\n"
                "from datetime import datetime, timedelta\n"
                "app = create_app()\n"
                "with app.app_context():\n"
                "    db.create_all()\n"
                "    cat = Category.query.filter_by(name='Harvest Category').first()\n"
                "    if not cat:\n"
                "        cat = Category(name='Harvest Category'); db.session.add(cat); db.session.flush()\n"
                "    item = Item.query.filter_by(name='Harvest Proof Item').first()\n"
                "    if not item:\n"
                "        item = Item(name='Harvest Proof Item', description='test', category_id=cat.id); db.session.add(item); db.session.flush()\n"
                "    def ensure_user(username, email, password, is_admin=False, is_customer_rep=False):\n"
                "        u = User.query.filter_by(username=username).first()\n"
                "        if not u:\n"
                "            u = User(username=username, email=email, is_admin=is_admin, is_customer_rep=is_customer_rep)\n"
                "            u.set_password(password)\n"
                "            db.session.add(u); db.session.flush()\n"
                "        return u\n"
                "    seller = ensure_user('harvestseller', 'harvestseller@example.com', 'SellerPass123!')\n"
                "    bidder1 = ensure_user('harvestbidder1', 'harvestbidder1@example.com', 'BidderPass123!')\n"
                "    bidder2 = ensure_user('harvestbidder2', 'harvestbidder2@example.com', 'BidderPass123!')\n"
                "    rep = ensure_user('harvestrep', 'harvestrep@example.com', 'RepPass123!', is_customer_rep=True)\n"
                "    auction = Auction.query.filter_by(title='Harvest Proof Auction').first()\n"
                "    if not auction:\n"
                "        auction = Auction(item_id=item.id, seller_id=seller.id, title='Harvest Proof Auction', description='test',\n"
                "                           initial_price=10.0, min_increment=1.0, secret_min_price=5.0,\n"
                "                           end_time=datetime.utcnow() + timedelta(hours=1))\n"
                "        db.session.add(auction)\n"
                "    db.session.commit()\n"
                "    print('seeded auction id=', auction.id, 'seller=', seller.id, 'bidder1=', bidder1.id, 'bidder2=', bidder2.id, 'rep=', rep.id)",
            ],
            "readiness_path": "/auth/login",
            "env": {
                "DATABASE_URL": "sqlite:///{db_path}",
                "SECRET_KEY": "capability-harvest-build-run",
            },
        },
    },
    {
        "slug": "mini-amazon",
        "clone_url": "https://github.com/benjaminyan1/Mini-Amazon.git",
        "ref": None,
        "category": "e-commerce",
        "why_selected": (
            "Real Flask + real PostgreSQL (SQLAlchemy raw-SQL engine, no "
            "SQLite fallback in the app's own config.py) e-commerce app, "
            "MIT licensed. Coupon.apply_coupon()/cart()'s real discount "
            "reduction does genuine reserve-checked coupon application -- "
            "confirmed by attempting an already-expired real seeded "
            "coupon (rejected, cart total unchanged), applying a real "
            "non-expired coupon and confirming the cart's real persisted "
            "total dropped by exactly its discount percentage (a real "
            "$200.00 -> $160.00 for a 20% coupon), and attempting to "
            "reapply the same coupon a second time (rejected, 'already "
            "applied', the real composite-PK AppliedCoupons(user_id, "
            "coupon_id) uniqueness enforced at the row level). Needs its "
            "own dedicated Postgres database (build.py's needs_postgres) "
            "and its own dedicated venv (old Flask 2.3.3/Werkzeug 2.3.7 "
            "pairing, confirmed by a real ImportError under the shared "
            "venv's modern Werkzeug before creating one)."
        ),
        "runner": {
            "kind": "flask_factory",
            "factory_module": "app",
            "factory_func": "create_app",
            "python_version": "3.11-mini-amazon",
            "needs_postgres": {"schema_relpath": "db/create.sql"},
            "setup_scripts": [
                # Real setup, not a change to the harvested capability's
                # logic: seeds one real seller, one real buyer, one real
                # category/product, one real cart item, and two real
                # coupons (one genuinely non-expired, one genuinely
                # already-expired) directly via the app's own real
                # app.db.execute() calls -- the app exposes no HTTP route
                # to create a coupon (only its own CSV-seed data does),
                # so this replicates that same real admin-seed role
                # non-interactively, the same class of setup already used
                # for BuyMe/Social-Life/CasettaFit.
                "-c import sys\n"
                "sys.path.insert(0, '.')\n"
                "from app import create_app\n"
                "from werkzeug.security import generate_password_hash\n"
                "from datetime import date, timedelta\n"
                "app = create_app()\n"
                "with app.app_context():\n"
                "    db = app.db\n"
                "    seller = db.execute(\"SELECT user_id FROM Users WHERE email=:e\", e='harvestseller@example.com')\n"
                "    if not seller:\n"
                "        seller_id = db.execute(\"INSERT INTO Users(email, password_hash, full_name, address, is_seller) VALUES(:e, :p, 'Harvest Seller', '1 Test St', TRUE) RETURNING user_id\", e='harvestseller@example.com', p=generate_password_hash('SellerPass123!'))[0][0]\n"
                "    else:\n"
                "        seller_id = seller[0][0]\n"
                "    buyer = db.execute(\"SELECT user_id FROM Users WHERE email=:e\", e='harvestbuyer@example.com')\n"
                "    if not buyer:\n"
                "        buyer_id = db.execute(\"INSERT INTO Users(email, password_hash, full_name, address) VALUES(:e, :p, 'Harvest Buyer', '2 Test St') RETURNING user_id\", e='harvestbuyer@example.com', p=generate_password_hash('BuyerPass123!'))[0][0]\n"
                "    else:\n"
                "        buyer_id = buyer[0][0]\n"
                "    cat = db.execute(\"SELECT category_name FROM Categories WHERE category_name='Harvest'\")\n"
                "    if not cat:\n"
                "        db.execute(\"INSERT INTO Categories(category_name) VALUES('Harvest')\")\n"
                "    prod = db.execute(\"SELECT product_id FROM Products WHERE name='Harvest Proof Product'\")\n"
                "    if not prod:\n"
                "        product_id = db.execute(\"INSERT INTO Products(category_name, name, description, price, created_by) VALUES('Harvest', 'Harvest Proof Product', 'test', 100.00, :s) RETURNING product_id\", s=seller_id)[0][0]\n"
                "    else:\n"
                "        product_id = prod[0][0]\n"
                "    cart_item = db.execute(\"SELECT cart_item_id FROM CartItems WHERE user_id=:u AND product_id=:p\", u=buyer_id, p=product_id)\n"
                "    if not cart_item:\n"
                "        db.execute(\"INSERT INTO CartItems(user_id, product_id, seller_id, quantity) VALUES(:u, :p, :s, 2)\", u=buyer_id, p=product_id, s=seller_id)\n"
                "    valid_coupon = db.execute(\"SELECT coupon_id FROM Coupons WHERE name='Harvest Valid Coupon'\")\n"
                "    if not valid_coupon:\n"
                "        valid_id = db.execute(\"INSERT INTO Coupons(name, categories, discount, expiry_date) VALUES('Harvest Valid Coupon', 'all', 20, :d) RETURNING coupon_id\", d=(date.today() + timedelta(days=30)))[0][0]\n"
                "    else:\n"
                "        valid_id = valid_coupon[0][0]\n"
                "    expired_coupon = db.execute(\"SELECT coupon_id FROM Coupons WHERE name='Harvest Expired Coupon'\")\n"
                "    if not expired_coupon:\n"
                "        expired_id = db.execute(\"INSERT INTO Coupons(name, categories, discount, expiry_date) VALUES('Harvest Expired Coupon', 'all', 50, :d) RETURNING coupon_id\", d=(date.today() - timedelta(days=5)))[0][0]\n"
                "    else:\n"
                "        expired_id = expired_coupon[0][0]\n"
                "    print('seeded seller_id=', seller_id, 'buyer_id=', buyer_id, 'product_id=', product_id, 'valid_coupon_id=', valid_id, 'expired_coupon_id=', expired_id)",
            ],
            "readiness_path": "/login",
            "env": {
                "DB_USER": "{postgres_user}",
                "DB_PASSWORD": "{postgres_password}",
                "DB_HOST": "{postgres_host}",
                "DB_PORT": "{postgres_port}",
                "DB_NAME": "{postgres_db}",
                "SECRET_KEY": "capability-harvest-build-run",
                "OPENAI_API_KEY": "unused",
            },
        },
    },
    {
        "slug": "django-folium",
        "clone_url": "https://github.com/moustafa-shaaban/Django_and_Folium.git",
        "ref": None,
        "category": "geospatial",
        "why_selected": (
            "Real Django + Folium (wraps Leaflet.js) geospatial app, MIT "
            "licensed, real PostgreSQL-backed. geo_app/utils.py's "
            "basemap() genuinely queries real persisted Feature rows "
            "(Feature.objects.all()) and adds one real Folium marker per "
            "feature -- confirmed by seeding two real features at two "
            "genuinely different coordinates and confirming both their "
            "exact names and lat/lng values appear in the real rendered "
            "map page, not a static demo map. (A real, separate "
            "map_features() view in the same file builds an empty map "
            "with no Feature query at all and has no route anywhere in "
            "urls.py -- confirmed dead/unwired code, correctly not used "
            "as the attach point here.) First real Django app in this "
            "pipeline: build.py gains a django_manage runner kind "
            "(equivalent to the app's own real `manage.py runserver`, "
            "invoked programmatically so this pipeline's env-var "
            "overrides apply) and needs_postgres now supports an empty "
            "database left for a setup_scripts step to migrate, for an "
            "app whose real schema comes from Django migrations rather "
            "than a raw SQL file. Its own real dependency set (Django "
            "4.2, allauth, graphene-django, django-jazzmin, "
            "django-import-export, folium, ...) is large enough to need "
            "its own dedicated venv too."
        ),
        "runner": {
            "kind": "django_manage",
            "app_subdir": "django_and_folium",
            "settings_module": "config.settings.local",
            "python_version": "3.11-django-folium",
            "needs_postgres": {"schema_relpath": None},
            "setup_scripts": [
                # The app's own real migrations -- not a schema we invented.
                "-c from django.core.management import execute_from_command_line\n"
                "execute_from_command_line(['manage.py', 'migrate', '--noinput'])",
                # Real setup, not a change to the harvested capability's
                # logic: seeds one real user and two real Feature rows at
                # two genuinely different coordinates directly via the
                # app's own real Django ORM models -- the same
                # non-interactive replication of the app's own real logic
                # already used for BuyMe/Social-Life/Mini-Amazon.
                "-c import django\n"
                "django.setup()\n"
                "from django_and_folium.users.models import User\n"
                "from django_and_folium.geo_app.models import Feature\n"
                "u, _ = User.objects.get_or_create(email='harvestuser1@example.com', defaults={'name': 'Harvest User'})\n"
                "u.set_password('HarvestPass123!')\n"
                "u.save()\n"
                "f1, _ = Feature.objects.get_or_create(name='Harvest Landmark', defaults={'type': 'Landmark', 'description': 'test feature', 'latitude': 47.6062, 'longitude': -122.3321, 'owner': u})\n"
                "f2, _ = Feature.objects.get_or_create(name='Second Harvest Marker', defaults={'type': 'POI', 'description': 'second test feature', 'latitude': 40.7128, 'longitude': -74.0060, 'owner': u})\n"
                "from allauth.account.models import EmailAddress\n"
                "EmailAddress.objects.get_or_create(user=u, email=u.email, defaults={'primary': True, 'verified': True})\n"
                "print('seeded user id=', u.id, 'feature1 id=', f1.id, 'feature2 id=', f2.id)",
            ],
            "readiness_path": "/",
            "needs_smtp": True,
            "env": {
                "DJANGO_SETTINGS_MODULE": "config.settings.local",
                "DATABASE_URL": "postgres://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}",
                "DJANGO_SECRET_KEY": "capability-harvest-build-run",
            },
        },
    },
    {
        "slug": "django-otp-auth",
        "clone_url": "https://github.com/tohid-ab/django-otp-auth.git",
        "ref": None,
        "category": "auth",
        "why_selected": (
            "Real Django + DRF phone-number OTP login app, MIT licensed, "
            "SQLite, no external infra. OTPVerifyView.post() does genuine "
            "OTP verification: a real 5-digit code with a real 120-second "
            "expiry window and a real one-time-use flag (OTPCodeQuerySet."
            "is_valid()), confirmed by reading the real generated code "
            "directly out of the app's own sqlite database (never sent by "
            "SMS -- the app's own real OTPCreateView only ever `print()`s "
            "it, a genuinely self-contained/offline-provable design, not "
            "a stub), then verified via a real wrong-code rejection, a "
            "real correct-code acceptance issuing real signed JWT access/"
            "refresh tokens, and a real reuse rejection once the code's "
            "own `used` flag has been set. Uses the same django_manage "
            "runner kind as django-folium but needs neither PostgreSQL "
            "nor a heavy dependency set -- plain SQLite, its own small "
            "dedicated venv (Django 5.1, DRF, simplejwt)."
        ),
        "runner": {
            "kind": "django_manage",
            "app_subdir": "otp",
            "settings_module": "django_otp_auth.settings",
            "python_version": "3.11-django-otp-auth",
            "reset_globs": ["db.sqlite3"],
            "setup_scripts": [
                # The app's own real migrations -- not a schema we invented.
                "-c from django.core.management import execute_from_command_line\n"
                "execute_from_command_line(['manage.py', 'migrate', '--noinput'])",
            ],
            "readiness_path": "/admin/login/",
            "env": {
                "DJANGO_SETTINGS_MODULE": "django_otp_auth.settings",
            },
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
