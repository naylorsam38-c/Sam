#!/usr/bin/env python3
"""
host_test_data_dashboard.py -- proves the host against the real Redash,
mirroring host_test.py's structure and the Script Standard, adapted for a
third app on the shelf.

  Usage:
      REDASH_DATABASE_URL=... REDASH_REDIS_URL=... REDASH_COOKIE_SECRET=... \
      REDASH_SECRET_KEY=... python3 host_test_data_dashboard.py

  Exit 0  every check passed
  Exit 1  one or more checks failed
  Exit 2  the system could not be started -- no checks are claimed
  Exit 3  no level-1 check ran, so nothing here proves a person can use it
"""

# =====================================================================
# RULES / CONFIG  --  edit these. Nothing below this block needs changing.
# =====================================================================

TEST_PORT = 8002
TEST_HOST_HEADER = "localhost:8002"
BOOT_TIMEOUT_SECONDS = 180
REQUEST_TIMEOUT_SECONDS = 30

START_SERVICES = True
REBUILD_DATABASE = True
# True = drop and recreate the whole 'public' schema, then call Redash's own
# db.create_all() (the same call its 'manage.py database create_tables' CLI
# command makes) against the fresh schema, every run (Standard §6).

BOOTSTRAP_ORG = True
# Redash gates EVERY page behind its own '/setup' wizard until an
# Organization exists (see redash/handlers/authentication.py:login --
# "if current_org == None and not settings.MULTI_ORG: return redirect
# ('/setup')"). '/setup' is itself CAP-0001 on this app's shelf (the closest
# real equivalent to 'register account' -- see forms/data-dashboard.form.json
# 'unresolved'), so completing it once is exercising a real capability, not
# bypassing the shelf -- done here, before the boot-wait loop, the same way
# CTFd's genuinely-separate /setup bootstrap was done for challenge-platform.

BROWSER_CHECK = True
BROWSER_JOURNEY_PATH = "/login"
BROWSER_EXPECT_SELECTOR = "input[type=password]"

SHELF_REQUESTS = [
    ("CAP-0002", "a person can open the log in page",
     "GET", "/login"),
    ("CAP-0003", "logging out sends the person onward",
     "GET", "/logout"),
    ("CAP-0016", "the data sources list answers",
     "GET", "/api/data_sources"),
]
# The remaining four (run query / create visualisation / add to dashboard /
# share dashboard) are all POST-only actions with no meaningful GET probe --
# not included here as a GET request; their bind result is still recorded by
# the binding check below, which runs regardless.

REFUSED_REQUESTS = [
    ("the admin/org-settings area the shelf never admitted stays gone", "/admin/status"),
    ("a nonsense path stays gone", "/this-route-does-not-exist-in-redash"),
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
H.APP_SLUG = "data-dashboard"

RESULTS = []
LEVEL1_RAN = False
SERVER = None
RUN = run_record.RunRecord("host_test_data_dashboard.py") if WRITE_RUN_RECORD else None


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


def rebuild_database_schema():
    if not REBUILD_DATABASE:
        return
    import psycopg2
    conn = psycopg2.connect(os.environ["REDASH_DATABASE_URL"])
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    cur.close()
    conn.close()


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

    for needed in ("REDASH_DATABASE_URL", "REDASH_REDIS_URL", "REDASH_COOKIE_SECRET",
                   "REDASH_SECRET_KEY"):
        if not os.environ.get(needed):
            die(2, f"{needed} is not set -- the source application has no real "
                   f"config to run against, and this script will not substitute "
                   f"a testing one")

    start_services()
    rebuild_database_schema()

    form, _ = H.read_form(H.APP_SLUG)
    if form is None:
        die(2, f"no filled form for app slug {H.APP_SLUG!r}")

    try:
        app = H.build_source_app(form)
    except Exception as e:
        die(2, f"the source application would not build: {str(e)[:200]}")

    with app.app_context():
        from redash.models import db as _db
        _db.create_all()
    if RUN:
        RUN.environment(working_directory_rebuilt=bool(REBUILD_DATABASE))

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

    if BOOTSTRAP_ORG:
        with app.test_client() as c:
            r = c.post("/setup", data={
                "name": "Harvest Admin",
                "email": "harvest_admin@example.test",
                "password": "Harvest-Eval-2026!",
                "org_name": "Harvest Eval Org",
                "security_notifications": "y",
                "newsletter": "",
            }, follow_redirects=False)
            if r.status_code not in (200, 302):
                die(2, f"Redash /setup bootstrap failed: HTTP {r.status_code}")
        with app.app_context():
            from redash.models import Organization
            if Organization.query.count() == 0:
                die(2, "Redash /setup bootstrap ran but no Organization row exists")

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
        code, _, _ = get("/ping")
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
