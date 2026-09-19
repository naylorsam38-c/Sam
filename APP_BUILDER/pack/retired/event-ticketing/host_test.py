#!/usr/bin/env python3
"""
host_test.py -- proves the host against the real thing.

Written to THE SCRIPT STANDARD (locked 2026-09-08, god mode
ACTIVE/active_standards/SCRIPT_STANDARD.md).

  §1.1  real database, real cache, real browser. Nothing substituted.
  §1.2  the host runs as a real process on its own port and is driven from
        the outside. A person would click the log in page, so the test
        clicks it.
  §1.3  config block above all logic, one comment per setting.
  §5    one line per check, PASS / FAIL / SKIP, verdict and count last.
        SKIP is not PASS.
  §6    working directory and database rebuilt fresh every run; the process
        is shut down at the end, including on failure.

  Usage:
      INDICO_CONFIG=/tmp/indico_real.conf python3 host_test.py

  Exit 0  every check passed
  Exit 1  one or more checks failed
  Exit 2  the system could not be started -- no checks are claimed
  Exit 3  no level-1 check ran, so nothing here proves a person can use it
"""

# =====================================================================
# RULES / CONFIG  --  edit these. Nothing below this block needs changing.
# =====================================================================

TEST_PORT = 8000
# Port the host is started on. It must match the port in the source
# application's own BASE_URL. The source sets Flask's SERVER_NAME from that
# URL, and Flask refuses any request whose Host header does not match, so
# testing on a different port makes every route 404 for the wrong reason.

TEST_HOST_HEADER = "localhost:8000"
# Host header sent with every request. Must equal the source application's
# SERVER_NAME, for the same reason as above.

BOOT_TIMEOUT_SECONDS = 180
# How long to wait for the host to answer on its socket before giving up and
# exiting 2. A large source application takes a while to build its stack.

REQUEST_TIMEOUT_SECONDS = 30
# Per-request timeout once the host is answering.

START_SERVICES = True
# True  = start PostgreSQL and Redis if they are not already running. If one
#         cannot be started the run exits 2 and names it, rather than
#         substituting anything for it (Standard §1.1, §1.4).
# False = assume they are already up. The run still dies if they are not.

REBUILD_DATABASE = True
# True  = drop and recreate every table before the run, so no check can pass
#         on data left behind by a previous run (Standard §6).
# False = run against whatever is in the database. Faster, and worth less.

REBUILD_STORAGE_DIR = True
# True = delete and recreate the file storage directory before the run, for
#        the same reason as the database.

SOURCE_SCRATCH_DIRS = ("CACHE_DIR", "TEMP_DIR")
# Settings on the source application's own config naming directories it writes
# to at run time. These are deleted and recreated with the storage directory.
# Indico generates javascript into CACHE_DIR on demand and raises
# FileNotFoundError if it is missing, which costs the landing page its scripts
# without costing it its status code. Add a setting name here if a source
# application writes somewhere else.

BROWSER_CHECK = True
# True  = drive a real browser through a real human journey at level 1 and
#         report javascript errors on the page.
# False = the level-1 check reports SKIP and the run exits 3. A run with no
#         level-1 check has not proved a person can use the thing, so it is
#         never allowed to report an overall pass.

BROWSER_JOURNEY_PATH = "/login/"
# The page the level-1 journey opens. A person arriving at this app lands on
# log in, so that is the journey.

BROWSER_EXPECT_SELECTOR = "input[type=password]"
# What must actually be on that page for a person to use it. If the page
# renders 200 but this is missing, the journey failed.

SHELF_REQUESTS = [
    ("CAP-0002", "a person can open the log in page",
     "GET", "/login/"),
    ("CAP-0003", "logging out sends the person onward",
     "GET", "/logout/"),
    ("CAP-0001", "a person can open the register page",
     "GET", "/register/"),
    ("CAP-0004", "a search with no valid query is rejected, not crashed",
     "GET", "/search/api/search?q="),
    ("CAP-0008", "scanning a ticket that does not exist says so",
     "GET", "/api/checkin/ticket/6f1e2c34-5a7b-4c8d-9e0f-1a2b3c4d5e6f"),
]
# Capabilities on the shelf that must answer. The claim is written as the job
# a person is doing, not as the screen, so a gap fails itself into view.
# A 404 from CAP-0008 is the capability working: the record genuinely is not
# there. What proves it ran is the stamp header, not the status code.

REFUSED_REQUESTS = [
    ("the admin area the shelf never admitted stays gone",      "/admin/"),
    ("the category browser the shelf never admitted stays gone", "/categories/"),
    ("the about page the shelf never admitted stays gone",       "/about/"),
]
# Real routes the source application ships that are NOT on the shelf. Each
# must be refused. This is the half that proves the shelf governs the app
# rather than the source application simply running.

EXPECT_REFUSED_STATUS = 404
# What a refused route returns.

STAMP_HEADER = "X-Shelf-Capability"
# The header the host stamps on anything a shelf capability served. This, not
# the status code, is the evidence the handler ran. A handler answering "no
# such record" is the capability working; the host refusing a route is not.
# Only the first carries this header.

FOLLOW_REDIRECTS = False
# False = a redirect counts as the capability answering. Following it lands on
#         a route that is not on the shelf, which is then correctly refused,
#         and a working capability would be reported as failed.

WRITE_RUN_RECORD = True
# True  = the run writes a record under run_record.RUNS_DIR so watch.py can
#         audit it afterwards.
# False = no record is written, and this run cannot be audited. A run that
#         cannot be audited is not BUILT, so leave this on.

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

RESULTS = []       # (state, claim, detail)
LEVEL1_RAN = False
SERVER = None
RUN = run_record.RunRecord("host_test.py") if WRITE_RUN_RECORD else None


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
    """Standard §6 -- the process is shut down at the end, including on failure."""
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
    """Standard §5 -- a run that could not start claims no checks at all."""
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
    """Drive the host from outside over a real socket (Standard §1.2)."""
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
    """Start the real datastores. Never substitute anything for them (§1.1)."""
    if not START_SERVICES:
        return
    subprocess.run(["service", "postgresql", "start"],
                   capture_output=True, timeout=180)
    subprocess.run(["redis-server", "--daemonize", "yes"],
                   capture_output=True, timeout=60)
    time.sleep(3)
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


def rebuild_environment(app):
    """
    Fresh every run (Standard §6), so no check can pass on something left
    behind by a previous run.
    """
    if REBUILD_STORAGE_DIR:
        for backend in (app.config.get("STORAGE_BACKENDS") or {}).values():
            if isinstance(backend, str) and backend.startswith("fs:"):
                path = backend[3:]
                shutil.rmtree(path, ignore_errors=True)
                os.makedirs(path, exist_ok=True)

        # The source application's own scratch directories. Indico generates
        # per-version javascript into CACHE_DIR at request time; if the
        # directory is absent the asset view raises FileNotFoundError and the
        # page a person lands on loses its scripts. Rebuilt here rather than
        # assumed to exist, so the run cannot depend on a directory some
        # earlier run happened to leave behind (Standard §6).
        with app.app_context():
            from indico.core.config import config
            for name in SOURCE_SCRATCH_DIRS:
                path = getattr(config, name, None)
                if not path:
                    continue
                shutil.rmtree(str(path), ignore_errors=True)
                os.makedirs(str(path), exist_ok=True)

    if REBUILD_DATABASE:
        from indico.core.db import db
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.commit()


def browser_journey():
    """
    Level 1. A person opens the app in a real browser and can use it.
    Standard §1.2 -- if a human would click it, the test clicks it.
    """
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
            browser = p.chromium.launch()
            page = browser.new_page()
            page.on("pageerror", lambda e: js_errors.append(str(e)[:120]))
            page.on("console",
                    lambda m: js_errors.append(m.text[:120])
                    if m.type == "error" else None)
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

    if not os.environ.get("INDICO_CONFIG"):
        die(2, "INDICO_CONFIG is not set -- the source application has no real "
               "config to run against, and this script will not substitute a "
               "testing one")

    start_services()

    form, _ = H.read_form(H.APP_SLUG)
    if form is None:
        die(2, f"no filled form for app slug {H.APP_SLUG!r}")

    try:
        app = H.build_source_app(form)
    except Exception as e:
        die(2, f"the source application would not build: {str(e)[:110]}")

    try:
        rebuild_environment(app)
    except Exception as e:
        die(2, f"the working environment could not be rebuilt fresh: {str(e)[:110]}")
    if RUN:
        RUN.environment(working_directory_rebuilt=bool(REBUILD_DATABASE
                                                       and REBUILD_STORAGE_DIR))

    resolved, unresolved = H.resolve(app, form)

    # The shelf's own copy of each part becomes the code that serves its
    # route, exactly as the host does it. Testing an app whose routes were
    # served by anything else would be testing something the shelf does not
    # govern.
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
        # Origin is read off each part's own PROVENANCE.json, never inferred.
        # A part with no provenance file is recorded as unknown, which the
        # audit fails on -- it does not quietly become "harvested".
        import json as _json
        from pathlib import Path as _P
        shelf_app = _P(H.SHELF_DIR) / H.APP_SLUG
        for cap_id in sorted({r["cap_id"] for r in resolved}):
            prov = shelf_app / cap_id / "PROVENANCE.json"
            if prov.is_file():
                try:
                    d = _json.loads(prov.read_text())
                    RUN.part(cap_id, "harvested",
                             d.get("repo_name") or d.get("source") or "")
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
        code, _, _ = get("/logout/")
        if code is not None:
            break
        time.sleep(1)
    else:
        die(2, "the host never answered on its socket")

    print(f"host on 127.0.0.1:{TEST_PORT}  --  shelf admits {len(resolved)} "
          f"capabilities, {kept} routes kept, {refused} refused\n")

    # -- the shelf resolved whole ------------------------------------
    on_shelf = H.read_shelf_caps(H.APP_SLUG)
    if len(resolved) == len(on_shelf) and not unresolved:
        record("PASS", "every capability on the shelf reached a live route",
               f"{len(resolved)} of {len(on_shelf)}")
    else:
        record("FAIL", "every capability on the shelf reached a live route",
               f"{len(unresolved)} did not: "
               + ", ".join(u["cap_id"] for u in unresolved))

    # -- the shelf's capabilities answer ------------------------------
    for cap_id, claim, _method, path in SHELF_REQUESTS:
        code, stamp, err = get(path)
        # Each of these checks drives one named capability, so the record says
        # which. That is what lets layer three know where a part would go
        # instead of guessing.
        if err:
            record("FAIL", claim, f"the request did not complete: {err}",
                   capability=cap_id)
        elif stamp == cap_id:
            record("PASS", claim, f"{code}, served by {stamp}",
                   capability=cap_id)
        elif stamp:
            record("FAIL", claim, f"answered by {stamp}, expected {cap_id}",
                   capability=cap_id)
        else:
            record("FAIL", claim,
                   f"{code} with no {STAMP_HEADER} -- the host refused it "
                   f"rather than {cap_id} serving it", capability=cap_id)

    # -- what the shelf never admitted is refused ---------------------
    for claim, path in REFUSED_REQUESTS:
        code, stamp, err = get(path)
        if err:
            record("FAIL", claim, f"the request did not complete: {err}")
        elif stamp:
            record("FAIL", claim,
                   f"served by {stamp} -- it should not exist on this app")
        elif code == EXPECT_REFUSED_STATUS:
            record("PASS", claim, f"{code}, refused")
        else:
            record("FAIL", claim,
                   f"answered {code}, expected {EXPECT_REFUSED_STATUS}")

    # -- level 1 -------------------------------------------------------
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
