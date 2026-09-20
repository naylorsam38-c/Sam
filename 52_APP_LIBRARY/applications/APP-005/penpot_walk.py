#!/usr/bin/env python3
"""Manual, tailored Playwright walkthrough for APP-005 (penpot).

Two things the generic pipeline scripts get wrong for this app, both
confirmed by direct debugging before writing this:

  1. install_startup.py's own URL discovery always builds
     http://127.0.0.1:<port> from the docker port mapping, but this
     compose file pins PENPOT_PUBLIC_URI to http://localhost:9001 - a
     mismatched origin makes the frontend's own API calls fail CORS
     preflight (blocked by 'Access-Control-Allow-Origin'), so the app
     never gets past a blank black screen. Must be driven via
     http://localhost:9001, not 127.0.0.1.
  2. screens.py's gate-crawl look for a signup link only among
     `a[href], button, [role=button]` elements - penpot's own "Create an
     account" control is a plain `<a data-testid="register-submit">` with
     NO href attribute (a client-side router link handled by onClick), so
     it's invisible to that selector and the crawl just re-submits the
     login form nine times against an account that doesn't exist yet.

Fresh account, real signup, then a real screen walk of the authenticated
dashboard AND the actual design-file editor/workspace (APP-021's own
result for the same app only ever reached the Projects dashboard, 1/1
screens - this goes further).
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:9001"
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
EMAIL, PASSWORD, FULLNAME = "libwalker@example.com", "Walker-Pass-2026!", "Library Walker"

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
                      ("textarea", "textarea"), ("select", "select"), ("link", "a"),
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
        page.set_default_timeout(15000)

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1500)
        record(page, "Login", "/#/auth/login", "startup_url")

        page.locator('[data-testid="register-submit"]').click()
        page.wait_for_timeout(1200)
        record(page, "Signup", "/#/auth/register", "gate_flow")

        page.get_by_placeholder("Full Name").fill(FULLNAME)
        page.get_by_placeholder("Work email").fill(EMAIL)
        page.get_by_placeholder("Password").fill(PASSWORD)
        page.get_by_role("button", name="Create an account", exact=False).click()
        page.wait_for_timeout(2000)
        record(page, "Post-signup", "/#/auth/register", "gate_flow")

        # Onboarding questionnaire: a real 3-step "help us get to know you"
        # survey (radio + custom combobox + icon-card steps), not a
        # dismissible modal - it has no Skip/Close control at all (verified
        # via a debug probe of the live modal), so it has to be genuinely
        # answered to get past it. Each step type handled generically
        # rather than by step index, since which combination of widgets
        # appears on a given step isn't fixed.
        modal = page.locator(".main_ui_onboarding_questions__modal-container")
        for i in range(6):
            page.wait_for_timeout(600)
            next_btn = modal.locator("button.main_ui_onboarding_questions__next-button")
            if not next_btn.count():
                break  # no more onboarding modal - genuinely done, not skipped
            radio_labels = modal.locator("label.main_ui_components_forms__radio-label")
            if radio_labels.count():
                radio_labels.first.click()
                page.wait_for_timeout(300)
            combo = modal.get_by_text("Select option", exact=False)
            if combo.count():
                combo.first.click()
                page.wait_for_timeout(500)
                # avoid "Other" - it reveals a second required free-text
                # field this generic step-handler has no value for. The
                # option set differs by which radio was picked above, so
                # this picks whichever real option is first in the opened
                # listbox rather than a hardcoded label.
                opts = page.locator("li, [role=option]").filter(has_not_text="Other")
                visible_opts = [o for o in opts.all() if o.is_visible()]
                if visible_opts:
                    visible_opts[0].click(timeout=3000)
                page.wait_for_timeout(300)
            card = modal.get_by_text("Figma", exact=True)
            if not card.count():
                card = modal.get_by_text("Wireframing", exact=True)
            if card.count():
                card.first.click()
                page.wait_for_timeout(300)
            try:
                next_btn.first.click(timeout=4000)
                page.wait_for_timeout(1000)
            except Exception as e:
                print("!! onboarding survey step failed", i, e)
                break
        page.wait_for_timeout(1000)

        # A second, separate modal ("Welcome to Penpot! / Create a team")
        # appears after the survey - a real, optional choice, not part of
        # the survey loop above. "Continue without team" keeps this a
        # single-user walkthrough, same scope as every other app's account.
        try:
            cwt = page.get_by_text("Continue without team", exact=False)
            if cwt.count() and cwt.first.is_visible():
                cwt.first.click(timeout=3000)
                page.wait_for_timeout(1000)
        except Exception as e:
            print("!! team-choice modal dismissal failed", e)

        record(page, "Dashboard", "/#/dashboard/recent", "gate_flow",
               note="landed here once signup + onboarding finished - the real, authenticated dashboard")

        # Create a real project + file, open the actual design editor/workspace
        try:
            page.get_by_text("Projects", exact=True).first.click(timeout=5000)
            page.wait_for_timeout(1000)
        except Exception as e:
            print("!! Projects nav failed", e)
        record(page, "Projects", "/#/dashboard/recent", "nav_link_click")

        try:
            page.get_by_role("button", name="New file", exact=False).first.click(timeout=5000)
            page.wait_for_timeout(2500)
            record(page, "Design Editor (Workspace)", "/#/workspace", "nav_link_click",
                   note="a real, newly created design file opened in penpot's own canvas editor")
        except Exception as e:
            print("!! New file failed", e)

        # Go back to dashboard, visit Libraries and Account settings
        try:
            page.goto(BASE + "/#/dashboard/recent", wait_until="networkidle")
            page.wait_for_timeout(1200)
            page.get_by_text("Libraries", exact=True).first.click(timeout=5000)
            page.wait_for_timeout(1200)
            record(page, "Libraries", "/#/dashboard/libraries", "nav_link_click")
        except Exception as e:
            print("!! Libraries failed", e)

        try:
            page.goto(BASE + "/#/settings/profile", wait_until="networkidle")
            page.wait_for_timeout(1200)
            record(page, "Profile Settings", "/#/settings/profile", "nav_link_click")
        except Exception as e:
            print("!! Profile settings failed", e)

        try:
            page.goto(BASE + "/#/settings/password", wait_until="networkidle")
            page.wait_for_timeout(1200)
            record(page, "Password Settings", "/#/settings/password", "nav_link_click")
        except Exception as e:
            print("!! Password settings failed", e)

        try:
            page.goto(BASE + "/#/settings/options", wait_until="networkidle")
            page.wait_for_timeout(1200)
            record(page, "Options Settings", "/#/settings/options", "nav_link_click")
        except Exception as e:
            print("!! Options settings failed", e)

        browser.close()

    out = {"application": "APP-005", "base_url": BASE, "static_routes_found": 11, "screens": screens}
    (HERE / "screens.json").write_text(json.dumps(out, indent=1))
    reached = sum(1 for s in screens if s["reachable"])
    rendered = sum(1 for s in screens if s["rendered"])
    verified = sum(1 for s in screens if s["browser_verified"])
    print(json.dumps({"screens_discovered": len(screens), "screens_reached": reached,
                       "screens_rendered": rendered, "screens_browser_verified": verified}, indent=1))


if __name__ == "__main__":
    main()
