#!/usr/bin/env python3
"""
host_test_challenge_platform.py -- proves the host against the real CTFd,
mirroring host_test.py's structure and the Script Standard, adapted for a
second app on the shelf.

  Usage:
      DATABASE_URL=... REDIS_URL=... SECRET_KEY=... python3 host_test_challenge_platform.py

  Exit 0  every check passed
  Exit 1  one or more checks failed
  Exit 2  the system could not be started -- no checks are claimed
  Exit 3  no level-1 check ran, so nothing here proves a person can use it
"""

# =====================================================================
# RULES / CONFIG  --  edit these. Nothing below this block needs changing.
# =====================================================================

TEST_PORT = 8001
# Port the host is started on for this app (kept off 8000 so both apps'
# host_test scripts can be run without colliding on the port event-ticketing
# used).

TEST_HOST_HEADER = "localhost:8001"
# Host header sent with every request.

BOOT_TIMEOUT_SECONDS = 180
REQUEST_TIMEOUT_SECONDS = 30

START_SERVICES = True
# True = start PostgreSQL and Redis if not already running.

REBUILD_DATABASE = True
# True = drop and recreate the whole 'public' schema before the run (CTFd's
# own create_app() then runs its real Alembic migrations against the fresh
# schema), so no check can pass on data left behind by a previous run.

BROWSER_CHECK = True
BROWSER_JOURNEY_PATH = "/login"
BROWSER_EXPECT_SELECTOR = "input[type=password]"

SHELF_REQUESTS = [
    ("CAP-0002", "a person can open the log in page",
     "GET", "/login"),
    ("CAP-0003", "logging out sends the person onward",
     "GET", "/logout"),
    ("CAP-0001", "a person can open the register page",
     "GET", "/register"),
    ("CAP-0011", "the challenge list answers (empty board is a real answer)",
     "GET", "/api/v1/challenges"),
    ("CAP-0013", "the scoreboard answers (empty board is a real answer)",
     "GET", "/api/v1/scoreboard"),
]
# The two team routes (CAP-0014/0015) are POST-only self-service actions with
# no meaningful GET -- not included here as a GET probe; their bind result is
# still recorded by the binding check below, which runs regardless.

REFUSED_REQUESTS = [
    ("the admin panel the shelf never admitted stays gone", "/admin/"),
    ("the CTFd file-upload area the shelf never admitted stays gone", "/files"),
]

EXPECT_REFUSED_STATUS = 404
STAMP_HEADER = "X-Shelf-Capability"
FOLLOW_REDIRECTS = False
WRITE_RUN_RECORD = True

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import sys
import time
import shutil
import logging
import warnings
import threading
import subprocess
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import host as H
import run_record

H.HOST_PORT = TEST_PORT
H.APP_SLUG = "challenge-platform"

RESULTS = []
LEVEL1_RAN = False
SERVER = None
RUN = run_record.RunRecord("host_test_challenge_platform.py") if WRITE_RUN_RECORD else None


def record(state, claim, detail="", capability=None):
    RESULTS.append((state, claim, detail))
    if RUN:
        RUN.check(f"CHK-{len(RESULTS):03d}",
                  1 if "real browser" in claim else 0,
                  state, claim, detail, capability=capability)
    print(f"{state:<5} {claim}")
    if detail:
        print(f"      {detail}")


def shutdown():
    global SERVER
    if RUN and SERVER is not None:
        RUN.environment(process_stopped=True)
    if SERVER is not None:
        try:
            SERVER.shutdown()
        except Exception:
            pass
        SERVER = None


def die(code, why):
    print(f"\nCOULD NOT RUN: {why}")
    print("0 checks claimed -- UNPROVEN")
    shutdown()
    if RUN:
        RUN.environment(could_not_start=why)
        RUN.write("COULD_NOT_START", code)
    sys.exit(code)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def get(path):
    url = f"http://127.0.0.1:{TEST_PORT}{path}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Host", TEST_HOST_HEADER)
    opener = (urllib.request.build_opener() if FOLLOW_REDIRECTS
              else urllib.request.build_opener(_NoRedirect))
    try:
        with opener.open(req, timeout=REQUEST_TIMEOUT_SECONDS) as r:
            return r.status, r.headers.get(STAMP_HEADER), None
    except urllib.error.HTTPError as e:
        try:
            e.read()
        except Exception:
            pass
        return e.code, e.headers.get(STAMP_HEADER), None
    except Exception as e:
        return None, None, str(e)[:70]


def start_services():
    if not START_SERVICES:
        return
    subprocess.run(["service", "postgresql", "start"], capture_output=True, timeout=180)
    subprocess.run(["redis-server", "--daemonize", "yes"], capture_output=True, timeout=60)
    time.sleep(2)
    try:
        ready = subprocess.run(["pg_isready"], capture_output=True, timeout=30)
        if ready.returncode != 0:
            die(2, "PostgreSQL is not accepting connections")
    except FileNotFoundError:
        die(2, "pg_isready is not installed -- cannot confirm PostgreSQL is real")
    try:
        ping = subprocess.run(["redis-cli", "ping"], capture_output=True, timeout=30)
        if b"PONG" not in ping.stdout:
            die(2, "Redis did not answer PING")
    except FileNotFoundError:
        die(2, "redis-cli is not installed -- cannot confirm Redis is real")
    if RUN:
        RUN.datastore("postgresql", True, "pg_isready answered")
        RUN.datastore("redis", True, "redis-cli PING answered PONG")


BOOTSTRAP_ADMIN_NAME = "harvest_admin"
BOOTSTRAP_ADMIN_EMAIL = "harvest_admin@example.test"
BOOTSTRAP_ADMIN_PASSWORD = "Harvest-Eval-2026!"
# CTFd refuses to serve ANY page other than /setup until an admin completes
# its one-time instance-setup wizard -- config.is_setup() gates it with a
# global before_request redirect. /setup is not one of the eight harvested
# capabilities (it is CTFd's own one-time deployment bootstrap, the same
# category of action as creating the Postgres database itself), so the
# shelf-restricted host correctly refuses it once BIND_SHELF_PARTS/restrict()
# are in effect. This completes that one-time bootstrap against an
# UNRESTRICTED CTFd app instance (real code, real DB writes, no shelf
# involved) immediately after every fresh migration, so the actual shelf-
# governed run underneath can be judged on the 8 real capabilities rather
# than blocked by an unrelated deployment gate.


def rebuild_database_schema():
    """CTFd's own create_app() runs real Alembic migrations (or db.create_all()
    for sqlite) as part of building the app -- so 'rebuild fresh' here means
    dropping the whole schema first, over a throwaway connection, and letting
    create_app() migrate it back up from nothing every run (Standard §6)."""
    if not REBUILD_DATABASE:
        return
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"].replace("postgresql+psycopg2", "postgresql"))
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    cur.close()
    conn.close()


def bootstrap_ctfd_setup():
    """Complete CTFd's one-time /setup wizard on a real, unrestricted instance
    of the real app -- outside shelf governance, the same as creating the
    Postgres role/database was. Real CTFd code path (CTFd.views.setup),
    real database writes. Never touches the shelf-restricted app."""
    from CTFd import create_app as _create_app
    boot_app = _create_app()
    with boot_app.test_client() as c:
        c.get("/setup")  # establishes session["nonce"], CTFd's own CSRF token
        with c.session_transaction() as sess:
            nonce = sess.get("nonce")
        r = c.post("/setup", data={
            "nonce": nonce,
            "ctf_name": "Harvest Eval CTF",
            "ctf_description": "Bootstrap instance for the harvest/chain evaluation.",
            "user_mode": "teams",
            "name": BOOTSTRAP_ADMIN_NAME,
            "email": BOOTSTRAP_ADMIN_EMAIL,
            "password": BOOTSTRAP_ADMIN_PASSWORD,
        }, follow_redirects=False)
        if r.status_code not in (200, 302):
            die(2, f"CTFd /setup bootstrap failed: HTTP {r.status_code}")
    with boot_app.app_context():
        from CTFd.utils import config as _cfgutil
        if not _cfgutil.is_setup():
            die(2, "CTFd /setup bootstrap ran but config.is_setup() is still False")
        boot_app.db.session.remove()
        boot_app.db.engine.dispose()
    # This bootstrap app and the shelf-restricted app built next are two
    # independent SQLAlchemy engines against the same database, in the same
    # process. Without disposing this one's pooled connections first, a
    # connection left open here can hold a lock that deadlocks the next
    # app's own plugin migrations (ALTER TABLE waiting on an idle-in-
    # transaction session) -- hit for real while building this script; see
    # evidence/TWO_MORE_APPS.md.


def browser_journey():
    global LEVEL1_RAN
    if not BROWSER_CHECK:
        record("SKIP", "a person can use the app in a real browser",
               "BROWSER_CHECK is off -- nothing about a real person was proved")
        return
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        record("SKIP", "a person can use the app in a real browser",
               f"playwright is not available: {str(e)[:60]}")
        return

    js_errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            page = browser.new_page()
            page.on("pageerror", lambda e: js_errors.append(str(e)[:120]))
            page.on("console",
                    lambda m: js_errors.append(m.text[:120]) if m.type == "error" else None)
            url = f"http://{TEST_HOST_HEADER}{BROWSER_JOURNEY_PATH}"
            resp = page.goto(url, timeout=REQUEST_TIMEOUT_SECONDS * 1000)
            status = resp.status if resp else None
            visible = page.locator(BROWSER_EXPECT_SELECTOR).count() > 0
            title = page.title()
            browser.close()
    except Exception as e:
        LEVEL1_RAN = True
        record("FAIL", "a person can use the app in a real browser",
               f"the browser could not complete the journey: {str(e)[:90]}")
        return

    LEVEL1_RAN = True
    if RUN:
        RUN.level1(ran=True, driver="chromium", path=BROWSER_JOURNEY_PATH,
                   javascript_errors=len(js_errors),
                   passed=(status == 200 and visible and not js_errors))

    if status != 200:
        record("FAIL", "a person can use the app in a real browser",
               f"{BROWSER_JOURNEY_PATH} answered {status}, not 200")
    elif not visible:
        record("FAIL", "a person can use the app in a real browser",
               f"the page rendered but {BROWSER_EXPECT_SELECTOR} was not on it")
    else:
        record("PASS", "a person can use the app in a real browser",
               f"opened {BROWSER_JOURNEY_PATH} in chromium, page title {title!r}")

    if js_errors:
        record("FAIL", "the page a person lands on throws no javascript errors",
               f"{len(js_errors)} error(s), first: {js_errors[0]}")
    else:
        record("PASS", "the page a person lands on throws no javascript errors")


def main():
    global SERVER

    warnings.filterwarnings("ignore")
    logging.disable(logging.ERROR)

    for needed in ("DATABASE_URL", "REDIS_URL", "SECRET_KEY"):
        if not os.environ.get(needed):
            die(2, f"{needed} is not set -- the source application has no real "
                   f"config to run against, and this script will not substitute "
                   f"a testing one")

    start_services()
    rebuild_database_schema()
    bootstrap_ctfd_setup()
    if RUN:
        RUN.environment(working_directory_rebuilt=bool(REBUILD_DATABASE))

    form, _ = H.read_form(H.APP_SLUG)
    if form is None:
        die(2, f"no filled form for app slug {H.APP_SLUG!r}")

    try:
        app = H.build_source_app(form)
    except Exception as e:
        die(2, f"the source application would not build: {str(e)[:200]}")

    resolved, unresolved = H.resolve(app, form)

    if H.BIND_SHELF_PARTS:
        bound, skipped = H.bind_shelf_parts(app, resolved, H.APP_SLUG, form)
        for cap_id, why in skipped:
            record("FAIL", f"{cap_id} is served by its own part on the shelf",
                   why, capability=cap_id)
        for cap_id in bound:
            record("PASS", f"{cap_id} is served by its own part on the shelf",
                   "bound from the shelf", capability=cap_id)

    kept, refused = H.restrict(app, resolved)

    if RUN:
        import json as _json
        from pathlib import Path as _P
        shelf_app = _P(H.SHELF_DIR) / H.APP_SLUG
        for cap_id in sorted({r["cap_id"] for r in resolved}):
            prov = shelf_app / cap_id / "PROVENANCE.json"
            if prov.is_file():
                try:
                    d = _json.loads(prov.read_text())
                    RUN.part(cap_id, "harvested", d.get("repo_name") or "")
                except Exception:
                    RUN.part(cap_id, "unknown", "provenance unreadable")
            else:
                RUN.part(cap_id, "unknown", "no PROVENANCE.json")

    from werkzeug.serving import make_server
    try:
        SERVER = make_server("127.0.0.1", TEST_PORT, app, threaded=True)
    except Exception as e:
        die(2, f"could not bind port {TEST_PORT}: {str(e)[:90]}")
    threading.Thread(target=SERVER.serve_forever, daemon=True).start()
    if RUN:
        RUN.environment(process_started=True, port=TEST_PORT)

    deadline = time.time() + BOOT_TIMEOUT_SECONDS
    while time.time() < deadline:
        code, _, _ = get("/")
        if code is not None:
            break
        time.sleep(1)
    else:
        die(2, "the host never answered on its socket")

    print(f"host on 127.0.0.1:{TEST_PORT}  --  shelf admits {len(resolved)} "
          f"capabilities, {kept} routes kept, {refused} refused\n")

    on_shelf = H.read_shelf_caps(H.APP_SLUG)
    if len(resolved) == len(on_shelf) and not unresolved:
        record("PASS", "every capability on the shelf reached a live route",
               f"{len(resolved)} of {len(on_shelf)}")
    else:
        record("FAIL", "every capability on the shelf reached a live route",
               f"{len(unresolved)} did not: "
               + ", ".join(u["cap_id"] for u in unresolved))

    for cap_id, claim, _method, path in SHELF_REQUESTS:
        code, stamp, err = get(path)
        if err:
            record("FAIL", claim, f"the request did not complete: {err}", capability=cap_id)
        elif stamp == cap_id:
            record("PASS", claim, f"{code}, served by {stamp}", capability=cap_id)
        elif stamp:
            record("FAIL", claim, f"answered by {stamp}, expected {cap_id}", capability=cap_id)
        else:
            record("FAIL", claim,
                   f"{code} with no {STAMP_HEADER} -- the host refused it rather "
                   f"than {cap_id} serving it", capability=cap_id)

    for claim, path in REFUSED_REQUESTS:
        code, stamp, err = get(path)
        if err:
            record("FAIL", claim, f"the request did not complete: {err}")
        elif stamp:
            record("FAIL", claim, f"served by {stamp} -- it should not exist on this app")
        elif code == EXPECT_REFUSED_STATUS:
            record("PASS", claim, f"{code}, refused")
        else:
            record("FAIL", claim, f"answered {code}, expected {EXPECT_REFUSED_STATUS}")

    browser_journey()
    shutdown()

    passed = sum(1 for s, _, _ in RESULTS if s == "PASS")
    failed = sum(1 for s, _, _ in RESULTS if s == "FAIL")
    skipped = sum(1 for s, _, _ in RESULTS if s == "SKIP")
    total = len(RESULTS)

    def _finish(verdict, code):
        if RUN:
            path = RUN.write(verdict, code)
            print(f"      run record: {path}")
        sys.exit(code)

    print()
    if not LEVEL1_RAN:
        print(f"{passed}/{total} checks passed, {skipped} skipped -- UNPROVEN: "
              f"no level-1 check ran, so nothing here proves a person can use "
              f"the app")
        _finish("UNPROVEN", 3)
    if failed:
        print(f"{passed}/{total} checks passed -- FAIL, {failed} failed")
        _finish("FAIL", 1)
    print(f"{passed}/{total} checks passed -- PASS, the shelf governs the app "
          f"and a person can use it")
    _finish("PASS", 0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        shutdown()
        raise
