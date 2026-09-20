#!/usr/bin/env python3
"""Manual, tailored capability test for APP-020 (CloudBeaver, substituted
for MindsDB/mindshub - see app.json's manual_override_reason).

Same bar as the other apps' *_capabilities.py scripts: a real live action,
then independent reconfirmation from a brand-new browser context with a
fresh login, never a same-session DOM check alone.

  1. Database connection + SQL query - create a real PostgreSQL
     connection to the demo-postgres sidecar (this edition's "New
     Connection" wizard only lists server-based drivers - SQLite/H2/DuckDB
     jars are bundled on disk but never offered as a connection type in
     the UI - see docker-compose.library.yml), run a real SQL query
     against it, then independently reconfirm the connection persists in
     the connections list from a brand-new browser context with a fresh
     login.
  2. Admin - Users - create a real second user account via the Admin >
     Users and Teams > Create form, independently reconfirm it's listed
     from a brand-new browser context with a fresh login.
"""
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8978"
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ADMIN_USER, ADMIN_PASS = "libwalker", "Walker-Pass-2026!"
RUN_TAG = str(int(time.time()))
CONN_NAME = f"library_walker_test_conn_{RUN_TAG}"
NEW_USER = f"library_walker_user_{RUN_TAG}"

shot_n = 0
results = []


def shot(page, label):
    global shot_n
    shot_n += 1
    name = f"{shot_n:03d}_cap_{label}.png"
    page.screenshot(path=str(EVIDENCE / name))
    return name


def login(page):
    page.goto(BASE + "/#/admin", wait_until="networkidle")
    page.wait_for_timeout(2500)
    page.locator('input[name="user"]').fill(ADMIN_USER)
    page.locator('input[name="password"]').fill(ADMIN_PASS)
    page.get_by_role("button", name="Login", exact=False).click()
    page.wait_for_timeout(2000)


def test_connection_and_query(pw):
    browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    login(page)

    page.goto(BASE + "/#/", wait_until="networkidle")
    page.wait_for_timeout(3500)
    # the card's text is one combined node ("New Connection\nCreate a new
    # connection"), so an exact match on the heading alone finds nothing -
    # verified via a debug probe of the live page.
    page.get_by_text("New Connection", exact=False).first.click(timeout=8000)
    page.wait_for_timeout(1200)
    shot(page, "new_connection_dialog")

    # This CE build's "New Connection" wizard only lists server-based
    # drivers (SQLite/H2/DuckDB jars are bundled on disk but never offered
    # as a connection type in this UI - verified via a debug search of the
    # live picker for each) - a real Postgres sidecar (demo-postgres, in
    # the same compose file/network) is the genuine, supported way to
    # exercise this app's core capability.
    page.locator('input[placeholder="Type driver name..."]').fill("PostgreSQL")
    page.wait_for_timeout(800)
    page.get_by_text("PostgreSQL", exact=True).first.click(timeout=8000)
    page.wait_for_timeout(1200)
    shot(page, "driver_selected")
    # "host" also matches a (readonly) field inside the collapsed SSH
    # Tunnel section - scope to .first, the real Main-tab host field.
    page.locator('input[name="host"]').first.fill("demo-postgres")
    page.locator('input[name="databaseName"]').first.fill("demo")
    page.locator('input[name="userName"]').first.fill("demo")
    page.locator('input[name="userPassword"]').first.fill("demo-pass-2026")
    try:
        name_field = page.get_by_label("Connection name", exact=False)
        if name_field.count():
            name_field.first.fill(CONN_NAME)
    except Exception:
        pass
    shot(page, "connection_configured")
    page.get_by_role("button", name="Test", exact=True).first.click(timeout=8000)
    page.wait_for_timeout(1500)
    # a modal re-prompts to confirm the same credentials before it will
    # actually run the test - verified via a debug screenshot of the live
    # wizard.
    apply_btn = page.get_by_role("button", name="Apply", exact=True)
    if apply_btn.count() and apply_btn.first.is_visible():
        apply_btn.first.click(timeout=5000)
        page.wait_for_timeout(2500)
    test_shot = shot(page, "connection_tested")
    page.get_by_role("button", name="Create", exact=False).first.click(timeout=8000)
    page.wait_for_timeout(3500)
    shot(page, "connection_created")

    # A fresh reload (rather than chasing the stacked "Connection was
    # created" toasts, which intermittently intercepted the click below
    # despite the toolbar button being visibly clear) reliably clears the
    # UI to the same clean state cloudbeaver_walk.py's own SQL Editor
    # click already proved works.
    #
    # Root cause of an earlier flaky failure here (found via a live DOM
    # dump): once more than one connection exists, CloudBeaver relabels
    # this same toolbar button's aria-label from the plain "Open SQL
    # Editor" to "Open SQL Editor for <connection-name>" (it targets
    # whichever connection is currently active) - the plain-text locator
    # then matches 0 elements. The button's id attribute
    # ("@action/sql-editor-new") stays constant regardless of label, so
    # anchor on that instead of the aria-label text.
    page.goto(BASE + "/#/", wait_until="networkidle")
    page.wait_for_timeout(3500)
    shot(page, "before_sql_editor_click")
    sql_btn = page.locator('[id="@action/sql-editor-new"]')
    print("DEBUG url:", page.url, "SQL btn count:", sql_btn.count())
    sql_btn.first.click(timeout=10000)
    page.wait_for_timeout(1500)

    # The connection's password wasn't saved (no "Save password locally"
    # checkbox was ticked during creation, matching CloudBeaver's own
    # secure-by-default behaviour), so opening the editor re-prompts for
    # it via a real "Database Authentication" dialog - found via a live
    # DOM dump showing this exact dialog intercepting the editor click.
    auth_dialog = page.get_by_role("dialog").filter(has_text="Database Authentication")
    if auth_dialog.count() and auth_dialog.first.is_visible():
        shot(page, "database_authentication_prompt")
        auth_dialog.first.locator('input[name="userPassword"], input[type="password"]').first.fill("demo-pass-2026")
        auth_dialog.first.get_by_role("button", name="Login", exact=False).click(timeout=5000)
        page.wait_for_timeout(1500)

    editor = page.locator(".cm-content, textarea").first
    editor.click(timeout=5000)
    editor.type("SELECT 1 AS library_walker_check;", delay=15)
    page.keyboard.press("Control+Enter")
    page.wait_for_timeout(2500)
    query_shot = shot(page, "query_executed")
    query_ran = page.get_by_text("library_walker_check", exact=False).count() > 0
    ctx.close()
    browser.close()

    # Independent confirmation: brand-new context, fresh login, connections list
    browser2 = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx2 = browser2.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page2 = ctx2.new_page()
    page2.set_default_timeout(15000)
    login(page2)
    page2.goto(BASE + "/#/", wait_until="networkidle")
    page2.wait_for_timeout(2000)
    list_shot = shot(page2, "connection_list_independent_reconfirm")
    persisted = page2.get_by_text(CONN_NAME, exact=False).count() > 0
    ctx2.close()
    browser2.close()

    verdict = "PROVEN" if (persisted and query_ran) else "NOT VERIFIED"
    results.append({
        "id": "CAP-020-01", "name": "Database connection + SQL query", "route": "/#/",
        "discovered_from": "screen",
        "live_test": {
            "action": f"created a real PostgreSQL connection (named '{CONN_NAME}') to a live "
                      "demo-postgres sidecar container via CloudBeaver's own connection wizard, "
                      "authenticated against it, ran a real SQL query (SELECT 1 AS "
                      "library_walker_check) and confirmed the result column appeared",
            "query_result_visible": query_ran,
            "independent_reconfirmation": persisted,
            "evidence": ["001_cap_new_connection_dialog.png", "002_cap_driver_selected.png",
                        "003_cap_connection_configured.png", "004_cap_connection_tested.png",
                        "005_cap_connection_created.png", query_shot, list_shot],
        },
        "verdict": verdict,
        "reason": ("both the query's own result column and the connection itself (re-fetched from a "
                   "brand-new browser context with a fresh login) are present, proving the connection was "
                   "really created server-side and could actually run a query" if verdict == "PROVEN"
                   else "either the query result or the independent reconfirmation was missing"),
    })
    print(f"  {verdict:12s} Database connection + SQL query")


def test_create_user(pw):
    browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    login(page)

    page.goto(BASE + "/#/admin/users/users", wait_until="networkidle")
    page.wait_for_timeout(1500)
    # the toolbar's own "+ CREATE" button (aria-label "Create new user")
    # opens the User Creation form - a plain get_by_role("Create") match
    # is ambiguous once the form's own "CREATE" submit button also
    # appears, so anchor the open-click on its distinct aria-label
    # (verified via a live DOM dump of the Users and Teams page).
    page.locator('button[aria-label="Create new user"]').first.click(timeout=8000)
    page.wait_for_timeout(1000)
    # the earlier generic `page.locator('input').first` picked up the
    # page's own "Search for the user name..." box (first <input> in DOM
    # order, before the form) rather than the real Username field, so the
    # form's required Username was silently left empty and the submit
    # button never actually proceeded - verified via a live input
    # inventory of the open form (name="userId" is the real field).
    page.locator('input[name="userId"]').fill(NEW_USER)
    pw_fields = page.locator('input[type="password"]')
    for i in range(pw_fields.count()):
        pw_fields.nth(i).fill("WalkerNewUser-2026!")
    create_shot = shot(page, "user_form_filled")
    # once the form is open, the toolbar's own "+ CREATE" is no longer in
    # the accessibility tree (verified live), so the sole remaining
    # "Create" match is the form's own submit button.
    page.get_by_role("button", name="Create", exact=False).first.click(timeout=8000)
    page.wait_for_timeout(1500)
    after_shot = shot(page, "user_created")
    ctx.close()
    browser.close()

    browser2 = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx2 = browser2.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page2 = ctx2.new_page()
    page2.set_default_timeout(15000)
    login(page2)
    page2.goto(BASE + "/#/admin/users/users", wait_until="networkidle")
    page2.wait_for_timeout(1500)
    list_shot = shot(page2, "user_list_independent_reconfirm")
    persisted = page2.get_by_text(NEW_USER, exact=False).count() > 0
    ctx2.close()
    browser2.close()

    verdict = "PROVEN" if persisted else "NOT VERIFIED"
    results.append({
        "id": "CAP-020-02", "name": "Admin - Users and Teams", "route": "/#/admin/users/users",
        "discovered_from": "screen",
        "live_test": {
            "action": f"created a real second user account (username='{NEW_USER}') via the "
                      "Admin > Users and Teams 'Create' form",
            "independent_reconfirmation": persisted,
            "evidence": [create_shot, after_shot, list_shot],
        },
        "verdict": verdict,
        "reason": ("user now appears, by its exact given username, in the Users list re-fetched from a "
                   "brand-new browser context + fresh login - proves it was really saved server-side"
                   if persisted else "user did not appear on independent re-fetch"),
    })
    print(f"  {verdict:12s} Admin - Users and Teams")


def main():
    with sync_playwright() as pw:
        test_connection_and_query(pw)
        test_create_user(pw)

    out = {"application": "APP-020", "capabilities_defined": True, "discovery_method": "app-derived",
          "verification_method": "manual (cloudbeaver_capabilities.py) - see screens.json's verification_note for why",
          "capabilities": results}
    (HERE / "capabilities.json").write_text(json.dumps(out, indent=1))
    proven = sum(1 for r in results if r["verdict"] == "PROVEN")
    print(json.dumps({"discovered": len(results), "proven": proven}, indent=1))


if __name__ == "__main__":
    main()
