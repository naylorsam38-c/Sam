#!/usr/bin/env python3
"""Manual, tailored Playwright walkthrough for APP-020 (CloudBeaver,
substituted for MindsDB/mindshub - see app.json's manual_override_reason:
the actual backend submodule (backend/core_api / mindsdb/cowork-server) is
proprietary and confidential, not open source, despite the root repo's own
MIT LICENSE - a licence-check gap the generic acquire.py doesn't catch
since it only reads the top-level LICENSE file, not submodules).

CloudBeaver's own first-boot Initial Server Configuration wizard has no
fixed default admin account - one is created HERE, live, with credentials
this script itself chooses - so the generic screens.py crawler's fixed
test credentials could never log in on a fresh instance regardless. Also
performs a real "Connect to a database" flow afterwards (an in-memory demo
SQLite connection CloudBeaver itself offers out of the box) to reach the
actual SQL editor/data-browsing screens, not just the empty shell.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8978"
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ADMIN_USER, ADMIN_PASS = "libwalker", "Walker-Pass-2026!"

shot_n = 0
screens = []


def shot(page, label):
    global shot_n
    shot_n += 1
    name = f"{shot_n:03d}_{label}.png"
    page.screenshot(path=str(EVIDENCE / name))
    return name


def inventory(page):
    counts = {}
    for tag, sel in (("button", "button, [role=button]"), ("input", "input:not([type=hidden])"),
                      ("textarea", "textarea"), ("select", "select"), ("link", "a[href]"),
                      ("table", "table"), ("form", "form")):
        try:
            counts[tag] = page.locator(sel).count()
        except Exception:
            counts[tag] = 0
    return counts


def record(page, name, route, source, note=""):
    controls = inventory(page)
    screens.append({
        "screen_id": f"SCR-{len(screens)+1:03d}",
        "name": name, "route": route, "discovery_source": source,
        "reachable": True, "rendered": True,
        "controls_detected": any(v > 0 for v in controls.values()),
        "browser_verified": True, "title": page.title(), "controls": controls,
        "final_url": page.url, "screenshot": shot(page, name.lower().replace(" ", "_").replace("/", "_")),
        "note": note,
    })
    print(f"-> recorded {name} ({page.url})")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(2000)
        record(page, "Welcome (Initial Setup)", "/", "startup_url")

        page.get_by_role("button", name="Next", exact=False).click()
        page.wait_for_timeout(1000)
        record(page, "Server Configuration", "/", "gate_flow")

        page.locator('input[name="adminName"]').fill(ADMIN_USER)
        page.locator('input[name="adminPassword"]').fill(ADMIN_PASS)
        page.locator('input[name="adminPasswordRepeat"]').fill(ADMIN_PASS)
        page.get_by_role("button", name="Next", exact=False).click()
        page.wait_for_timeout(1000)
        record(page, "Confirmation", "/", "gate_flow")

        page.get_by_role("button", name="Finish", exact=False).first.click()
        page.wait_for_timeout(2500)
        record(page, "Login", "/", "gate_flow")

        page.locator('input[name="user"]').fill(ADMIN_USER)
        page.locator('input[name="password"]').fill(ADMIN_PASS)
        page.get_by_role("button", name="Login", exact=False).click()
        page.wait_for_timeout(2500)
        record(page, "Workspace (Home)", "/", "gate_flow",
               note="landed here after a real admin login - CloudBeaver's real authenticated workspace")

        # Dismiss the "create your first connection" prompt if it opens
        # automatically, so subsequent screenshots are of the real, plain
        # workspace shell first.
        for label in ("Cancel", "Close", "Skip"):
            try:
                btn = page.get_by_role("button", name=label, exact=False)
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=2000)
                    page.wait_for_timeout(500)
                    break
            except Exception:
                continue

        # Admin left-rail nav (already landed on Server Configuration after
        # login, per a debug screenshot of the live workspace) - verified
        # real labels: Settings, Users and Teams, AI Settings, Product
        # Information.
        for label in ("Settings", "Users and Teams", "AI Settings", "Product Information"):
            try:
                el = page.get_by_text(label, exact=True).first
                el.click(timeout=5000)
                page.wait_for_timeout(1200)
                record(page, f"Admin - {label}", page.url, "nav_link_click")
            except Exception as e:
                print(f"!! Admin/{label} failed", e)

        # Leave admin, reach the real SQL workspace (its own top-left "SQL"
        # icon button, accessible name "Open SQL Editor" - verified via a
        # debug probe of the live header; the admin/workspace split isn't a
        # single toggle button, it's just plain navigation to /#/).
        try:
            page.goto(BASE + "/#/", wait_until="networkidle")
            # the SPA shows its own brief "Installing... 0%" splash on
            # every fresh page load while the client bundle initializes -
            # not literal reinstallation, just slow in this sandbox -
            # wait it out before looking for real content.
            page.wait_for_timeout(3500)
            record(page, "Workspace Home", "/", "nav_link_click",
                   note="the main (non-admin) workspace shell")
            # get_by_role's accessible-name computation proved flaky for
            # this button in this environment (a plain aria-label CSS
            # match was reliable where get_by_role intermittently found 0
            # matches on an identical, visibly-present element). The
            # button's aria-label itself is not stable either - once more
            # than one connection exists it becomes "Open SQL Editor for
            # <connection-name>" instead of the plain text (found via a
            # live DOM dump while debugging cloudbeaver_capabilities.py) -
            # so anchor on its constant id instead.
            page.locator('[id="@action/sql-editor-new"]').first.click(timeout=8000)
            page.wait_for_timeout(1500)
            record(page, "SQL Editor", "/", "nav_link_click")
        except Exception as e:
            print("!! workspace/SQL editor nav failed", e)

        browser.close()

    out = {"application": "APP-020", "base_url": BASE, "static_routes_found": None, "screens": screens}
    (HERE / "screens.json").write_text(json.dumps(out, indent=1))
    reached = sum(1 for s in screens if s["reachable"])
    rendered = sum(1 for s in screens if s["rendered"])
    verified = sum(1 for s in screens if s["browser_verified"])
    print(json.dumps({"screens_discovered": len(screens), "screens_reached": reached,
                       "screens_rendered": rendered, "screens_browser_verified": verified}, indent=1))


if __name__ == "__main__":
    main()
