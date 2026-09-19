#!/usr/bin/env python3
"""
record_journey.py -- challenge-platform (CTFd). Step 7 of
HARVEST_TWO_MORE_APPS.md: a real browser, through Playwright, against the
host actually serving this app, recording video of the journey_cap_id
capability (log in) end to end.

This drives the REAL host.py in its real, unmodified serving mode
(`python3 host.py --app challenge-platform`, no --check, no host_test
workaround) -- the same entry point a real deployment would use. host.py
refuses to start when a shelf capability cannot be bound to its own part
(FAIL_ON_UNRESOLVED = True, unchanged), which this app's host --check run
already showed happens for CAP-0001/0002/0003/0014/0015 -- so this script's
job is to show, on video, exactly what a person's browser actually
experiences when that is the app's real state: nothing to connect to.

  Usage:
      DATABASE_URL=... REDIS_URL=... SECRET_KEY=... PYTHONPATH=<ctfd clone> \
      python3 record_journey.py
"""

# =====================================================================
# CONFIG  -- one comment per setting, above all logic.
# =====================================================================

RECORD_VIDEO_DIR = "."
# Where the video is written. The final file is renamed to journey.webm in
# this directory after the browser context closes (Playwright names video
# files itself while a context is open).

HEADLESS = True
# True for a machine (this run). False to watch it happen on a desktop.

BASE_URL = "http://127.0.0.1:8001"
# The host's address -- must match HOST_BIND/HOST_PORT the real host.py
# would use. host.py's own HOST_PORT default is 8000; this app's host_test
# script (and this recording) use 8001 so both apps' evidence can be
# produced without a port collision.

JOURNEY_PATH = "/login"
# The route being driven -- this app's journey_cap_id, CAP-0002 (log in).

EXPECT_SELECTOR = "input[type=password]"
# The element that proves the real page rendered.

TIMEOUT_MS = 20000
# How long before a step is called failed.

CHROMIUM_EXECUTABLE = "/opt/pw-browsers/chromium"
# Pre-installed Chromium in this environment (see the session's own
# PLAYWRIGHT_BROWSERS_PATH). Launching by explicit path rather than letting
# Playwright resolve its pinned revision, which is not the one installed
# here.

HOST_PY = "../../4_host/host.py"
HOST_ARGS = ["--app", "challenge-platform"]
HOST_BOOT_WAIT_SECONDS = 12
# How long to give host.py to either start listening or refuse and exit,
# before driving the browser at it regardless.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    for needed in ("DATABASE_URL", "REDIS_URL", "SECRET_KEY"):
        if not os.environ.get(needed):
            print(f"REFUSED: {needed} is not set -- no real config to run "
                  f"the source application against")
            sys.exit(2)

    host_py = (HERE / HOST_PY).resolve()
    proc = subprocess.Popen(
        [sys.executable, str(host_py), *HOST_ARGS],
        cwd=str(host_py.parent.parent), env=os.environ.copy(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    print(f"started host.py pid={proc.pid}, waiting up to "
          f"{HOST_BOOT_WAIT_SECONDS}s to see whether it starts or refuses")
    deadline = time.time() + HOST_BOOT_WAIT_SECONDS
    host_output = []
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    # Drain whatever host.py printed either way -- this is the ground truth
    # for whether it refused, and why.
    try:
        remaining, _ = proc.communicate(timeout=2)
        if remaining:
            host_output.append(remaining)
    except subprocess.TimeoutExpired:
        pass

    host_refused = proc.poll() is not None
    print(f"host.py exit status: "
          f"{'exited ' + str(proc.returncode) if host_refused else 'still running'}")
    if host_output:
        print("host.py output:")
        print("".join(host_output)[-3000:])

    from playwright.sync_api import sync_playwright

    video_dir = (HERE / RECORD_VIDEO_DIR).resolve()
    video_dir.mkdir(parents=True, exist_ok=True)
    journey_ok = False
    failure_reason = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, executable_path=CHROMIUM_EXECUTABLE)
        context = browser.new_context(record_video_dir=str(video_dir),
                                       record_video_size={"width": 1280, "height": 800})
        page = context.new_page()
        url = BASE_URL + JOURNEY_PATH
        try:
            resp = page.goto(url, timeout=TIMEOUT_MS)
            status = resp.status if resp else None
            print(f"navigated to {url} -> status {status}")
            if status != 200:
                failure_reason = f"{url} answered {status}, not 200"
            elif page.locator(EXPECT_SELECTOR).count() == 0:
                failure_reason = f"{EXPECT_SELECTOR} was not on the page"
            else:
                journey_ok = True
        except Exception as e:
            failure_reason = f"the browser could not reach {url}: {str(e)[:200]}"
            print(f"FAILED: {failure_reason}")
            # Leave something visible in the recording even on a hard
            # connection failure, rather than a blank tab for the whole clip.
            try:
                page.goto("about:blank")
                page.wait_for_timeout(1500)
            except Exception:
                pass

        if journey_ok:
            # End to end: submit the real bootstrap admin credentials this
            # app's chain runs create, and confirm the journey completes
            # (redirected off /login).
            try:
                page.fill("#name", "harvest_admin")
                page.fill("#password", "Harvest-Eval-2026!")
                page.click("[type=submit]")
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
                print("submitted login, landed on:", page.url)
            except Exception as e:
                failure_reason = f"login form submit did not complete: {str(e)[:200]}"
                journey_ok = False

        page.wait_for_timeout(1000)
        video_path = page.video.path() if page.video else None
        context.close()
        browser.close()

    if video_path and Path(video_path).is_file():
        final = video_dir / "journey.webm"
        shutil.move(video_path, final)
        print(f"video saved to {final}")
    else:
        final = None
        print("no video was produced")

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    if journey_ok:
        print("JOURNEY OK")
        sys.exit(0)
    else:
        print(f"JOURNEY FAILED: {failure_reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
