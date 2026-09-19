#!/usr/bin/env python3
"""
record_journey.py -- data-dashboard (Redash). Step 7 of
HARVEST_TWO_MORE_APPS.md: a real browser, through Playwright, against the
host actually serving this app, recording video of the journey_cap_id
capability (log in) end to end.

This drives the REAL host.py in its real, unmodified serving mode
(`python3 host.py --app data-dashboard`, no --check, no host_test
workaround). host.py refuses to start when a shelf capability cannot be
bound to its own part (FAIL_ON_UNRESOLVED = True, unchanged), which this
app's host --check run already showed happens for CAP-0001/0002/0003/0017 --
so this script's job is to show, on video, exactly what a person's browser
actually experiences when that is the app's real state.

  Usage:
      REDASH_DATABASE_URL=... REDASH_REDIS_URL=... REDASH_COOKIE_SECRET=... \
      REDASH_SECRET_KEY=... PYTHONPATH=<redash clone> python3 record_journey.py
"""

# =====================================================================
# CONFIG  -- one comment per setting, above all logic.
# =====================================================================

RECORD_VIDEO_DIR = "."
HEADLESS = True
BASE_URL = "http://127.0.0.1:8002"
# Matches this app's host_test script's TEST_PORT, so both apps' evidence
# can be produced without a port collision (host.py's own default is 8000).

JOURNEY_PATH = "/login"
EXPECT_SELECTOR = "input[type=password]"
TIMEOUT_MS = 20000
CHROMIUM_EXECUTABLE = "/opt/pw-browsers/chromium"

HOST_PY = "../../4_host/host.py"
HOST_ARGS = ["--app", "data-dashboard"]
HOST_BOOT_WAIT_SECONDS = 15

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
    for needed in ("REDASH_DATABASE_URL", "REDASH_REDIS_URL", "REDASH_COOKIE_SECRET",
                   "REDASH_SECRET_KEY"):
        if not os.environ.get(needed):
            print(f"REFUSED: {needed} is not set -- no real config to run "
                  f"the source application against")
            sys.exit(2)

    host_py = (HERE / HOST_PY).resolve()
    env = os.environ.copy()
    env["HOST_PORT"] = "8002" if False else env.get("HOST_PORT", "")
    proc = subprocess.Popen(
        [sys.executable, str(host_py), *HOST_ARGS],
        cwd=str(host_py.parent.parent), env=os.environ.copy(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    print(f"started host.py pid={proc.pid}, waiting up to "
          f"{HOST_BOOT_WAIT_SECONDS}s to see whether it starts or refuses")
    deadline = time.time() + HOST_BOOT_WAIT_SECONDS
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    host_output = []
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

    # host.py's own default port (HOST_PORT = 8000 in its config block) is
    # what it will actually bind to if it gets that far -- this app's form
    # was never told to use 8002, so drive the browser at host.py's real
    # default rather than a port nothing is listening on.
    target_base = "http://127.0.0.1:8000" if not host_refused else BASE_URL

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
        url = target_base + JOURNEY_PATH
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
            try:
                page.goto("about:blank")
                page.wait_for_timeout(1500)
            except Exception:
                pass

        if journey_ok:
            try:
                page.fill("input[name=email]", "harvest_admin@example.test")
                page.fill("input[name=password]", "Harvest-Eval-2026!")
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
