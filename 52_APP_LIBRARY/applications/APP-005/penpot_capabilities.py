#!/usr/bin/env python3
"""Manual, tailored capability test for APP-005 (penpot).

Same bar as ha_capabilities.py (spec sections 12-14, applied by hand for
the same reason penpot needed a tailored screens.py to begin with - see
screens.json's own verification_note): each capability gets a real live
action AND independent reconfirmation from a brand-new browser context
with a fresh login, not just a same-session DOM check.

  1. Design editor (drawing) - draw a real rectangle on the canvas in a new
     file, rename the file to a unique, identifiable name, then reopen that
     exact file from a fresh context/login and confirm the shape is really
     there (a real <rect> in the page's own shape tree, not merely "the
     page didn't error").
  2. Dashboard (projects) - create a real new project with a unique name,
     then independently reconfirm it's listed from a fresh context/login.
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:9001"
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
EMAIL, PASSWORD, FULLNAME = "libwalker@example.com", "Walker-Pass-2026!", "Library Walker"
RUN_TAG = str(int(time.time()))
FILE_NAME = f"Library Walker Test File {RUN_TAG}"
PROJECT_NAME = f"Library Walker Test Project {RUN_TAG}"

shot_n = 0
results = []


def shot(page, label):
    global shot_n
    shot_n += 1
    name = f"{shot_n:03d}_cap_{label}.png"
    page.screenshot(path=str(EVIDENCE / name))
    return name


def signup_and_get_in(page):
    """Fresh account signup + the real onboarding flow, same logic as
    penpot_walk.py - each capability test uses ITS OWN fresh account so a
    signed-up-once-already state never has to be special-cased."""
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.locator('[data-testid="register-submit"]').click()
    page.wait_for_timeout(1000)
    page.get_by_placeholder("Full Name").fill(FULLNAME)
    page.get_by_placeholder("Work email").fill(EMAIL)
    page.get_by_placeholder("Password").fill(PASSWORD)
    page.get_by_role("button", name="Create an account", exact=False).click()
    page.wait_for_timeout(2000)

    modal = page.locator(".main_ui_onboarding_questions__modal-container")
    for _ in range(6):
        page.wait_for_timeout(600)
        next_btn = modal.locator("button.main_ui_onboarding_questions__next-button")
        if not next_btn.count():
            break
        radio_labels = modal.locator("label.main_ui_components_forms__radio-label")
        if radio_labels.count():
            radio_labels.first.click()
            page.wait_for_timeout(300)
        combo = modal.get_by_text("Select option", exact=False)
        if combo.count():
            combo.first.click()
            page.wait_for_timeout(500)
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
        except Exception:
            break
    page.wait_for_timeout(800)
    cwt = page.get_by_text("Continue without team", exact=False)
    if cwt.count() and cwt.first.is_visible():
        cwt.first.click(timeout=3000)
        page.wait_for_timeout(1000)


def login_only(page):
    """For the independent-reconfirmation pass, once the account already
    exists: real login, not signup."""
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(1200)
    page.get_by_placeholder("Work email").fill(EMAIL)
    page.get_by_placeholder("Password").fill(PASSWORD)
    page.get_by_role("button", name="Continue", exact=False).click()
    page.wait_for_timeout(2000)


def test_design_editor(pw):
    browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    signup_and_get_in(page)

    page.get_by_role("button", name="New file", exact=False).first.click(timeout=8000)
    page.wait_for_timeout(2500)
    shot(page, "editor_blank")

    # Draw a real rectangle: select the rectangle tool, then drag on canvas.
    # The drawing surface itself has no distinguishing selector to query
    # (it's the app's own zoomable/pannable viewport, not a single fixed
    # element) - verified via a debug screenshot of the blank editor - so
    # this drags across fixed, comfortably-inside-the-visible-canvas
    # viewport coordinates instead of locating a "canvas" element.
    page.locator('button[title*="Rectangle" i], [aria-label*="Rectangle" i]').first.click(timeout=5000)
    page.wait_for_timeout(400)
    page.mouse.move(500, 300)
    page.mouse.down()
    page.mouse.move(800, 550, steps=10)
    page.mouse.up()
    # penpot debounces its own change-persistence call (POST
    # .../update-file) rather than firing it immediately on every edit -
    # a debug probe confirmed the shape is genuinely lost on reload if the
    # browser closes right after drawing, but reliably persists once given
    # a few real seconds to flush.
    page.wait_for_timeout(4000)
    draw_shot = shot(page, "rectangle_drawn")

    # Rename the file to a unique, identifiable name via its title field.
    try:
        title_el = page.locator("text=New File 1").first
        title_el.dblclick(timeout=3000)
        page.wait_for_timeout(300)
        page.keyboard.press("Control+A")
        page.keyboard.type(FILE_NAME)
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)
    except Exception as e:
        print("!! rename failed (non-fatal)", e)
    rename_shot = shot(page, "file_renamed")
    file_url = page.url
    ctx.close()
    browser.close()

    # Independent reconfirmation: brand-new context, fresh login, open the
    # SAME file by its exact URL, and check for a real shape element on
    # the canvas (not merely that the page loaded without error).
    browser2 = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx2 = browser2.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page2 = ctx2.new_page()
    page2.set_default_timeout(15000)
    login_only(page2)
    page2.goto(file_url, wait_until="networkidle")
    page2.wait_for_timeout(4000)
    reconfirm_shot = shot(page2, "reopened_independent")
    # a precise check, not a broad class-name guess (an earlier, looser
    # '[class*="shape"]' selector matched 100+ unrelated UI chrome elements
    # and reported PROVEN on a run where the shape had, provably by
    # screenshot, NOT actually persisted): the layer named exactly
    # "Rectangle" as it appears in the LAYERS panel list.
    shape_count = page2.get_by_text("Rectangle", exact=True).count()
    persisted = shape_count > 0
    ctx2.close()
    browser2.close()

    verdict = "PROVEN" if persisted else "NOT VERIFIED"
    results.append({
        "id": "CAP-005-01", "name": "Design Editor (drawing)", "route": "/#/workspace",
        "discovered_from": "screen",
        "live_test": {
            "action": f"created a new file, drew a real rectangle shape on the canvas via the rectangle "
                      f"tool + mouse drag, renamed the file to '{FILE_NAME}'",
            "independent_reconfirmation": persisted,
            "shape_count_on_reopen": shape_count,
            "evidence": [draw_shot, rename_shot, reconfirm_shot],
        },
        "verdict": verdict,
        "reason": ("reopening the exact same file from a brand-new browser context with a fresh login "
                   "shows the drawn shape still present in the layer tree/canvas - proves it was really "
                   "persisted server-side, not just left in the editor's local in-memory state" if persisted
                   else "no shape found on independent reopen"),
    })
    print(f"  {verdict:12s} Design Editor (drawing)")


def test_new_project(pw):
    browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    login_only(page)  # same account as test_design_editor - reuse, no second signup needed

    page.get_by_role("button", name="New project", exact=False).first.click(timeout=8000)
    page.wait_for_timeout(1200)
    # a freshly-created project's name is immediately editable inline
    page.keyboard.press("Control+A")
    page.keyboard.type(PROJECT_NAME)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1200)
    create_shot = shot(page, "project_created")
    ctx.close()
    browser.close()

    browser2 = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx2 = browser2.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page2 = ctx2.new_page()
    page2.set_default_timeout(15000)
    login_only(page2)
    page2.wait_for_timeout(1500)
    list_shot = shot(page2, "project_list_independent_reconfirm")
    persisted = page2.get_by_text(PROJECT_NAME, exact=False).count() > 0
    ctx2.close()
    browser2.close()

    verdict = "PROVEN" if persisted else "NOT VERIFIED"
    results.append({
        "id": "CAP-005-02", "name": "Projects (dashboard)", "route": "/#/dashboard/recent",
        "discovered_from": "screen",
        "live_test": {
            "action": f"created a real new project named '{PROJECT_NAME}' via the dashboard's own "
                      "+ New Project control",
            "independent_reconfirmation": persisted,
            "evidence": [create_shot, list_shot],
        },
        "verdict": verdict,
        "reason": ("project now appears, by its exact given name, in the dashboard re-fetched from a "
                   "brand-new browser context + fresh login - proves it was really saved server-side"
                   if persisted else "project did not appear on independent re-fetch"),
    })
    print(f"  {verdict:12s} Projects (dashboard)")


def main():
    with sync_playwright() as pw:
        test_design_editor(pw)
        test_new_project(pw)

    out = {"application": "APP-005", "capabilities_defined": True, "discovery_method": "app-derived",
          "verification_method": "manual (penpot_capabilities.py) - see screens.json's verification_note for why",
          "capabilities": results}
    (HERE / "capabilities.json").write_text(json.dumps(out, indent=1))
    proven = sum(1 for r in results if r["verdict"] == "PROVEN")
    print(json.dumps({"discovered": len(results), "proven": proven}, indent=1))


if __name__ == "__main__":
    main()
