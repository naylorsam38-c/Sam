#!/usr/bin/env python3
"""adapt_and_verify.py -- Phase 2 (ADAPT TO THE SYSTEM) of the skin
generation command.

For every category and every skin generate_skins.py produced, this proves
two separate things against DISPOSABLE COPIES of the real app (never
OUTPUT_LIBRARY or NEW_APPS_FROM_LIBRARY itself -- same rule
functional_tests.py already follows in this repo):

  TRACK A ("full skin"): the complete design-token skin (typography,
  spacing, radius, shadows, multi-tone palette, interactive states) is
  applied to the app's own CSS and the app is loaded in a real, running
  Flask process with a real headless browser (Playwright, the same
  PLAYWRIGHT_CHROMIUM_EXECUTABLE / favicon / primary_journey convention
  already proven in build.py's own chk_browser) -- screenshot taken,
  computed colors asserted, and the app's own declared primary_journey
  re-run to prove the skin did not break functionality.

  TRACK B ("existing-mechanism adaptation"): only the ONE visual dimension
  the real choice.json -> build.py -> skin.json pipeline already threads
  through with ZERO builder-side code changes -- branding.color, a single
  accent hex baked verbatim into the generated CSS -- is swapped to this
  skin's primary color, the same substitution the real generator already
  performs today, and verified the same way.

FAIL_ON_UNADAPTED governs both: a skin whose either track fails is
reported FAILED for that track, never shipped as if it had passed.

This script starts real subprocesses and a real browser. No mocks. It
never modifies OUTPUT_LIBRARY, NEW_APPS_FROM_LIBRARY, build.py,
gen_common.py, or any existing skin -- only files under a scratch
directory, deleted as it goes.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_tokens as dt

# ==============================================================================
# RULES BLOCK -- change these, not the logic below
# ==============================================================================

SKIN_LIBRARY_PATH = "skins_library"
# Must match generate_skins.py's own setting -- this script reads what
# that one wrote.

ADAPT_TO_SYSTEM = True
# Whether Track B (the existing-mechanism color adaptation) runs at all.
# Leave true; Track A (full-skin visual proof) always runs regardless,
# since it is the standing "verified live, not by static review" rule.

FAIL_ON_UNADAPTED = True
# If true, this script exits non-zero when any (category, skin, track)
# combination fails, and REPORT.md marks that skin FAILED for that track
# rather than "partially working."

SCRATCH_DIR = Path(os.environ.get(
    "SKIN_VERIFY_SCRATCH",
    "/tmp/claude-0/-home-user-Sam/0d40ef0d-4784-5ae9-a65d-6aeb8bdb90f7/scratchpad/skin_verify",
))
# Where disposable app copies are booted from. Never OUTPUT_LIBRARY itself.

PORT_BASE = 25100
# First TCP port used for booted scratch apps; each run uses one port at a
# time and releases it before the next, so this only needs to avoid
# clashing with anything else already listening.

PLAYWRIGHT_CHROMIUM_EXECUTABLE = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE", "")
# Same env var build.py's own chk_browser already reads (see build.py's
# use of os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")) -- set this if
# the installed Playwright package's expected browser revision doesn't
# match what's actually on disk.

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_LIBRARY = REPO_ROOT / "OUTPUT_LIBRARY"
LIBRARY_DIR = REPO_ROOT / SKIN_LIBRARY_PATH
EVIDENCE_DIR = LIBRARY_DIR / "_verification_evidence"

# ==============================================================================
# END OF RULES BLOCK
# ==============================================================================

FAMILY_CHECKS = {
    # selector/property/token-key pairs used to assert the skin actually
    # rendered, distinct per CSS family (see render_css.py) -- never a
    # selector that isn't proven, by generate_skins.py's own family
    # detection, to exist in the app under test.
    "shared_card": [("body", "background-color", "background"), ("button", "background-color", "primary")],
    "todomvc": [("body", "background-color", "background"), ("#new-todo", "border-bottom-color", "border")],
}


def hex_to_css_rgb(hexcolor: str) -> str:
    r, g, b = dt.hex_to_rgb(hexcolor)
    return f"rgb({r}, {g}, {b})"


def escape_for_single_quoted_py_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def fresh_copy(slug: str, tag: str) -> Path:
    dest = SCRATCH_DIR / f"{slug}__{tag}"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(OUTPUT_LIBRARY / slug, dest)
    data_dir = dest / "data"
    if data_dir.is_dir():
        for f in data_dir.glob("*.json"):
            f.write_text("[]", encoding="utf-8")
    return dest


def patch_full_skin(app_dir: Path, host_rel: str, css_text: str) -> None:
    host = app_dir / host_rel
    src = host.read_text(encoding="utf-8")
    escaped = escape_for_single_quoted_py_str(css_text)
    new_src, n = re.subn(r"<style>.*?</style>", lambda m: f"<style>{escaped}</style>", src, count=1)
    if n != 1:
        raise RuntimeError(f"{host}: expected exactly one <style> block, patched {n}")
    host.write_text(new_src, encoding="utf-8")


def patch_color_only(app_dir: Path, host_rel: str, old_hex: str, new_hex: str) -> int:
    host = app_dir / host_rel
    src = host.read_text(encoding="utf-8")
    new_src, n = re.subn(re.escape(old_hex), new_hex, src)
    host.write_text(new_src, encoding="utf-8")
    return n


def wait_for_health(port: int, timeout=8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.25)
    return False


def start_app(app_dir: Path, start_cmd, port: int):
    # Run the app with the SAME Python interpreter this verifier itself
    # runs under (which has Flask installed), regardless of what "python3"
    # resolves to on PATH -- app.json's own "start" command names an
    # interpreter generically (see e.g. OUTPUT_LIBRARY/crm/app.json), and
    # substituting sys.executable here changes nothing about what gets
    # run, only which interpreter runs it.
    cmd = [sys.executable] + list(start_cmd[1:]) if start_cmd and start_cmd[0] == "python3" else list(start_cmd)
    return subprocess.Popen(cmd + ["--port", str(port)], cwd=str(app_dir),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def stop_app(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _camel(css_prop: str) -> str:
    parts = css_prop.split("-")
    return parts[0] + "".join(p.title() for p in parts[1:])


def run_browser_check(browser, base_url, journey, family_checks, expected_tokens, screenshot_path):
    """Real Playwright page: loads the app, drives its own declared
    primary_journey (if any -- exact same convention as build.py's
    chk_browser), asserts the family's expected computed colors, and
    saves a real screenshot. Returns (ok: bool, detail: str)."""
    page = browser.new_page()
    console_errors = []
    page.route("**/favicon.ico", lambda route: route.fulfill(status=204, body=""))
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))
    try:
        page.goto(base_url + "/", timeout=10000)

        color_mismatches = []
        for selector, prop, token_key in family_checks:
            try:
                actual = page.eval_on_selector(selector, f"(el) => getComputedStyle(el).{_camel(prop)}")
            except Exception as e:
                color_mismatches.append(f"{selector}: could not read {prop} ({e})")
                continue
            expected = hex_to_css_rgb(expected_tokens[token_key])
            if actual != expected:
                color_mismatches.append(f"{selector}.{prop}: expected {expected}, saw {actual}")

        journey_detail = ""
        if journey:
            if journey.get("input_selector"):
                page.fill(journey["input_selector"], journey.get("input_value", ""))
            if journey.get("action_key"):
                page.press(journey["input_selector"], journey["action_key"], timeout=5000)
            else:
                page.click(journey["action_selector"], timeout=5000)
            confirm_selector = journey.get("confirm_selector", "body")
            page.wait_for_selector(confirm_selector, timeout=5000)
            text = page.inner_text(confirm_selector)
            expected_text = journey.get("confirm_contains", "")
            if expected_text not in text:
                journey_detail = f"primary_journey did not produce expected result (saw: {text!r})"

        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path))

        problems = []
        if console_errors:
            problems.append(f"javascript errors: {console_errors}")
        if color_mismatches:
            problems.append(f"color mismatches: {color_mismatches}")
        if journey_detail:
            problems.append(journey_detail)
        return (len(problems) == 0), "; ".join(problems)
    finally:
        page.close()


def main():
    from playwright.sync_api import sync_playwright

    index = json.loads((LIBRARY_DIR / "_index.json").read_text(encoding="utf-8"))
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    report = {}
    port = PORT_BASE
    launch_kwargs = {"executable_path": PLAYWRIGHT_CHROMIUM_EXECUTABLE} if PLAYWRIGHT_CHROMIUM_EXECUTABLE else {}

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        try:
            for slug, cat in sorted(index["categories"].items()):
                if cat["result"]["status"] != "GENERATED":
                    report[slug] = {"status": "SKIPPED", "reason": cat["result"].get("reason", "not generated")}
                    continue

                family = cat["family"]
                host_rel = cat["host_app_py"]
                start_cmd = cat["start"]
                app_json_path = OUTPUT_LIBRARY / slug / "app.json"
                app_json = json.loads(app_json_path.read_text(encoding="utf-8"))
                journey = app_json.get("primary_journey")
                old_color = cat["branding"]["color"]
                family_checks = FAMILY_CHECKS[family]

                cat_report = {"status": "OK", "skins": {}}

                for skin_id in cat["result"]["skins"]:
                    skin_def = json.loads((LIBRARY_DIR / slug / f"{skin_id}.json").read_text(encoding="utf-8"))
                    css_text = (LIBRARY_DIR / slug / f"{skin_id}.css").read_text(encoding="utf-8")
                    tokens = skin_def["design_tokens"]
                    skin_report = {}

                    # ---- Track A: full skin, live-rendered, verified ----
                    port += 1
                    app_dir = fresh_copy(slug, f"{skin_id}__full")
                    proc = None
                    try:
                        patch_full_skin(app_dir, host_rel, css_text)
                        proc = start_app(app_dir, start_cmd, port)
                        if not wait_for_health(port):
                            out = proc.stdout.read() if proc.stdout else ""
                            skin_report["full_skin"] = {"status": "FAILED", "reason": f"app never became healthy: {out[-500:]}"}
                        else:
                            shot = EVIDENCE_DIR / slug / f"{skin_id}_full.png"
                            ok, detail = run_browser_check(
                                browser, f"http://127.0.0.1:{port}", journey, family_checks, tokens, shot
                            )
                            skin_report["full_skin"] = {
                                "status": "PASS" if ok else "FAILED",
                                "detail": detail,
                                "screenshot": str(shot.relative_to(REPO_ROOT)),
                            }
                    except Exception as e:
                        skin_report["full_skin"] = {"status": "FAILED", "reason": f"exception: {e}"}
                    finally:
                        if proc:
                            stop_app(proc)
                        shutil.rmtree(app_dir, ignore_errors=True)

                    # ---- Track B: existing-mechanism color-only adaptation ----
                    if ADAPT_TO_SYSTEM:
                        port += 1
                        app_dir = fresh_copy(slug, f"{skin_id}__color")
                        proc = None
                        try:
                            new_color = tokens["primary"]
                            n = patch_color_only(app_dir, host_rel, old_color, new_color)
                            if n < 1:
                                skin_report["color_adaptation"] = {
                                    "status": "FAILED",
                                    "reason": f"existing color {old_color!r} not found anywhere in {host_rel} "
                                              f"to substitute -- cannot confirm this app's real generator "
                                              f"actually bakes branding.color the way CRM's does",
                                }
                            else:
                                proc = start_app(app_dir, start_cmd, port)
                                if not wait_for_health(port):
                                    out = proc.stdout.read() if proc.stdout else ""
                                    skin_report["color_adaptation"] = {"status": "FAILED", "reason": f"app never became healthy: {out[-500:]}"}
                                else:
                                    shot = EVIDENCE_DIR / slug / f"{skin_id}_color.png"
                                    color_check = [c for c in family_checks if c[2] == "primary"] or family_checks[:1]
                                    ok, detail = run_browser_check(
                                        browser, f"http://127.0.0.1:{port}", journey,
                                        color_check, {**tokens, "primary": new_color}, shot,
                                    )
                                    skin_report["color_adaptation"] = {
                                        "status": "PASS" if ok else "FAILED",
                                        "detail": detail,
                                        "substitutions": n,
                                        "screenshot": str(shot.relative_to(REPO_ROOT)),
                                    }
                        except Exception as e:
                            skin_report["color_adaptation"] = {"status": "FAILED", "reason": f"exception: {e}"}
                        finally:
                            if proc:
                                stop_app(proc)
                            shutil.rmtree(app_dir, ignore_errors=True)

                    cat_report["skins"][skin_id] = skin_report
                    any_failed = any(v.get("status") == "FAILED" for v in skin_report.values())
                    if any_failed:
                        cat_report["status"] = "PARTIAL_FAILURE"

                report[slug] = cat_report
        finally:
            browser.close()

    (LIBRARY_DIR / "_verification_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    report = main()
    n_categories = len(report)
    n_clean = sum(1 for r in report.values() if r.get("status") == "OK")
    total_fail = 0
    for slug, r in report.items():
        for skin_id, sr in r.get("skins", {}).items():
            for track, res in sr.items():
                if res.get("status") == "FAILED":
                    total_fail += 1
                    print(f"FAILED  {slug}  {skin_id}  {track}: {res.get('reason') or res.get('detail')}")
    print(f"\n{n_clean}/{n_categories} categories fully clean, {total_fail} individual track failures")
    sys.exit(1 if (total_fail and FAIL_ON_UNADAPTED) else 0)
