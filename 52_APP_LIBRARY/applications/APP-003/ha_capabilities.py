#!/usr/bin/env python3
"""Manual, tailored capability test for APP-003 (Home Assistant).

Mirrors capabilities.py's own bar (spec sections 12-14: discover a real
capability from a real screen, find its attach point in the app's own
source, then LIVE-exercise it and require positive evidence something
actually happened - never "no error" alone) but drives it by hand, the same
reason ha_walk.py exists instead of screens.py: HA's frontend renders
entirely inside nested OPEN shadow roots, and the generic tooling's
page-level text extraction (page.inner_text("body")) does not reliably see
into it, so PASS/FAIL judging that depends on scanning that text for a
success marker or a persisted typed value would misjudge working
capabilities as unproven. This script proves two real capabilities with a
fresh login (a separate browser context from ha_walk.py, exactly like
capabilities.py's own separation from screens.py) and independent,
after-the-fact confirmation:

  1. Shopping list (To-do lists) - add a real item, reload the list in a
     THIRD, completely fresh context and independently confirm the exact
     item text is present. This is the strongest possible proof: not just
     "the DOM changed after I clicked", but "the server still has this,
     read back from scratch".
  2. Automations - create a real time-triggered automation via the UI editor,
     save it, and confirm it now appears (by the exact name given) in the
     Automations list.
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8123"
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
USERNAME, PASSWORD = "libwalker", "Walker-Pass-2026!"
RUN_TAG = str(int(time.time()))
ITEM_TEXT = f"Library Walker Test Item {RUN_TAG}"
AUTOMATION_NAME = f"Library Walker Test Automation {RUN_TAG}"

shot_n = 0
results = []


def shot(page, label):
    global shot_n
    shot_n += 1
    name = f"{shot_n:03d}_cap_{label}.png"
    page.screenshot(path=str(EVIDENCE / name))
    return name


def login(page):
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(1200)
    # already-onboarded instance -> straight to the login form
    page.locator('input[name="username"]').fill(USERNAME)
    page.locator('input[name="password"]').fill(PASSWORD)
    page.get_by_role("button", name="Log in", exact=False).click()
    page.wait_for_timeout(2500)


def test_shopping_list(pw):
    ctx = pw.chromium.launch(executable_path=CHROMIUM, headless=True).new_context(
        viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    login(page)

    page.goto(BASE + "/todo?entity_id=todo.shopping_list", wait_until="networkidle")
    page.wait_for_timeout(1200)
    before_shot = shot(page, "todo_before")

    add_input = page.locator('input[placeholder="Add item"], ha-list input, input[type="text"]').first
    add_input.click()
    add_input.fill(ITEM_TEXT)
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    after_shot = shot(page, "todo_after_add")
    item_visible_immediately = page.get_by_text(ITEM_TEXT, exact=False).count() > 0

    page.context.browser.close()

    # Independent confirmation: a THIRD, completely fresh browser+context,
    # fresh login, re-navigate to the same list from scratch.
    ctx2 = pw.chromium.launch(executable_path=CHROMIUM, headless=True).new_context(
        viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page2 = ctx2.new_page()
    page2.set_default_timeout(15000)
    login(page2)
    page2.goto(BASE + "/todo?entity_id=todo.shopping_list", wait_until="networkidle")
    page2.wait_for_timeout(1200)
    confirm_shot = shot(page2, "todo_independent_reconfirm")
    persisted = page2.get_by_text(ITEM_TEXT, exact=False).count() > 0
    page2.context.browser.close()

    verdict = "PROVEN" if persisted else "NOT VERIFIED"
    results.append({
        "id": "CAP-003-01", "name": "To-do lists (shopping list)", "route": "/todo",
        "discovered_from": "screen",
        "live_test": {
            "action": f"added item '{ITEM_TEXT}' via the list's own Add-item input + Enter",
            "immediate_dom_evidence": item_visible_immediately,
            "independent_reconfirmation": persisted,
            "evidence": [before_shot, after_shot, confirm_shot],
        },
        "verdict": verdict,
        "reason": ("item added, then independently re-confirmed present via a brand-new browser "
                   "context + fresh login + fresh navigation (not merely 'still in the DOM of the "
                   "same page') - proves it was really persisted server-side" if persisted else
                   "item did not reappear on independent re-fetch"),
    })
    print(f"  {verdict:12s} To-do lists (shopping list)")


def test_automation(pw):
    ctx = pw.chromium.launch(executable_path=CHROMIUM, headless=True).new_context(
        viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    login(page)

    page.goto(BASE + "/config/automation/edit/new", wait_until="networkidle")
    page.wait_for_timeout(1500)
    shot(page, "automation_editor_blank")

    # Add a trigger: Time. The "Add trigger" dialog's left rail lists
    # CATEGORIES ("Time and sun") - clicking the category only filters the
    # right-hand Triggers panel, it doesn't add anything. The actual add
    # action is the trigger CARD's own text ("Triggers at a specific time,
    # or on a specific date.") or its + button.
    page.get_by_text("Add trigger", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(1000)
    # left rail: select the "Time" category first to populate the right
    # panel with its trigger cards (nothing shows there until a category is
    # picked - "Select a target" is the dialog's own initial placeholder).
    page.get_by_text("Time", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(1000)
    page.get_by_text("Triggers at a specific time, or on a specific date.", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(1500)
    # HA's time trigger renders "At time" as three separate <input type=number>
    # boxes (hh / mm / ss, no placeholder/aria-label distinguishing them -
    # verified via a debug input dump of the live panel), not one text field.
    time_boxes = page.locator('input[type="number"]')
    time_boxes.nth(0).fill("6")
    time_boxes.nth(1).fill("30")
    time_boxes.nth(2).fill("0")
    shot(page, "automation_trigger_added")

    # Add an action: Notify (persistent notification is always available,
    # no external service needed). The dialog's search box is a plain
    # <input type=text> (same as the trigger dialog's), not a placeholder
    # named "Search action" - verified via a debug screenshot of the live
    # dialog (evidence/debug_action_search.png).
    page.get_by_text("Add action", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(1000)
    action_search = page.locator('input[type="text"]').first
    action_search.fill("notify")
    page.wait_for_timeout(1000)
    page.get_by_text("Send a persistent notification", exact=True).first.click(timeout=5000)
    page.wait_for_timeout(1000)
    shot(page, "automation_action_added")

    # Save
    page.get_by_text("Save", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(1000)
    # Save prompts for a name on a brand-new automation. Two elements both
    # expose an accessible name "Save" - the page's own floating action
    # button (behind the dialog, not the one to click) and the Save dialog's
    # own confirm button, which - verified via a debug enumeration of the
    # live page - is the LAST match in DOM order (dialogs are appended at
    # the end of <body>), not the first.
    name_input = page.locator('input[type="text"]').last
    try:
        name_input.fill(AUTOMATION_NAME)
        page.get_by_role("button", name="Save", exact=False).last.click(timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    save_shot = shot(page, "automation_saved")
    url_after_save = page.url
    page.context.browser.close()

    # Independent confirmation: fresh context, fresh login, automations list
    ctx2 = pw.chromium.launch(executable_path=CHROMIUM, headless=True).new_context(
        viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page2 = ctx2.new_page()
    page2.set_default_timeout(15000)
    login(page2)
    page2.goto(BASE + "/config/automation/dashboard", wait_until="networkidle")
    page2.wait_for_timeout(1200)
    list_shot = shot(page2, "automation_list_independent_reconfirm")
    persisted = page2.get_by_text(AUTOMATION_NAME, exact=False).count() > 0
    page2.context.browser.close()

    verdict = "PROVEN" if persisted else "NOT VERIFIED"
    results.append({
        "id": "CAP-003-02", "name": "Automations & scenes", "route": "/config/automation/dashboard",
        "discovered_from": "screen",
        "live_test": {
            "action": f"created a real time-triggered automation named '{AUTOMATION_NAME}' "
                      "(trigger: time 06:30:00, action: send a persistent notification) via the "
                      "app's own visual automation editor and saved it",
            "url_after_save": url_after_save,
            "independent_reconfirmation": persisted,
            "evidence": [save_shot, list_shot],
        },
        "verdict": verdict,
        "reason": ("automation now appears, by its exact given name, in the Automations list re-fetched "
                   "from a brand-new browser context + fresh login - proves it was really saved "
                   "server-side, not just left in an editor's local state" if persisted else
                   "automation did not appear in the list on independent re-fetch"),
    })
    print(f"  {verdict:12s} Automations & scenes")


def main():
    with sync_playwright() as pw:
        test_shopping_list(pw)
        test_automation(pw)

    out = {"application": "APP-003", "capabilities_defined": True, "discovery_method": "app-derived",
          "verification_method": "manual (ha_capabilities.py) - see screens.json's verification_note for why",
          "capabilities": results}
    (HERE / "capabilities.json").write_text(json.dumps(out, indent=1))
    proven = sum(1 for r in results if r["verdict"] == "PROVEN")
    print(json.dumps({"discovered": len(results), "proven": proven}, indent=1))


if __name__ == "__main__":
    main()
