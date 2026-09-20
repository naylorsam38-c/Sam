#!/usr/bin/env python3
"""Manual, tailored capability test for APP-019 (Apache Airflow, substituted
for Airbyte - see app.json's manual_override_reason).

Same bar as ha_capabilities.py/penpot_capabilities.py: a real live action,
then independent reconfirmation from a brand-new browser context with a
fresh login, never a same-session DOM check alone.

  1. DAG trigger (the core capability of a workflow orchestrator) - manually
     trigger a real example DAG run via the UI's own Trigger button, then
     independently reconfirm a new DagRun really exists for it (queried via
     the app's own `airflow dags list-runs` CLI inside the container - the
     single most authoritative, independent source of truth available,
     equivalent in spirit to the "brand-new browser context" pattern used
     for the other apps, but for a fact that lives in the scheduler's own
     database rather than in any one screen).
  2. Variables (Admin) - create a real Airflow Variable with a unique
     key/value via the UI, then independently reconfirm it's listed from a
     brand-new browser context with a fresh login.
"""
import json
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
CONTAINER = "lib-app019-airflow"
RUN_TAG = str(int(time.time()))
VAR_KEY = f"library_walker_test_key_{RUN_TAG}"
VAR_VALUE = f"library_walker_test_value_{RUN_TAG}"

shot_n = 0
results = []


def shot(page, label):
    global shot_n
    shot_n += 1
    name = f"{shot_n:03d}_cap_{label}.png"
    page.screenshot(path=str(EVIDENCE / name))
    return name


def get_admin_password():
    out = subprocess.run(["docker", "logs", CONTAINER], capture_output=True, text=True, timeout=30)
    for line in (out.stdout + out.stderr).splitlines():
        if "Password for user 'admin'" in line:
            return line.rsplit(":", 1)[-1].strip()
    raise RuntimeError("admin password not found in container logs")


def login(page, password):
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_timeout(1000)
    page.get_by_label("Username").fill("admin")
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_timeout(1800)


def dag_run_count(dag_id):
    # dag_id is a positional argument in this Airflow version's CLI, not
    # -d/--dag-id (an older syntax that silently fails over to the help
    # text instead of erroring, which is what first hid this).
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "airflow", "dags", "list-runs", dag_id, "-o", "json"],
        capture_output=True, text=True, timeout=30)
    try:
        return len(json.loads(out.stdout))
    except Exception:
        return 0


def test_dag_trigger(pw, password):
    dag_id = "example_bash_operator"
    before_runs = dag_run_count(dag_id)

    browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    login(page, password)

    page.goto(f"{BASE}/dags/{dag_id}", wait_until="networkidle")
    page.wait_for_timeout(1200)
    before_shot = shot(page, "dag_before_trigger")
    page.get_by_role("button", name="Trigger", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(800)
    # a confirm dialog opens with its OWN "Trigger" button - matching by
    # role+name alone hits 2 elements (the page header's button behind the
    # dialog too), so this scopes to the dialog itself (verified via a
    # debug probe of the live modal).
    page.locator("[role=dialog]").get_by_role("button", name="Trigger", exact=True).click(timeout=5000)
    page.wait_for_timeout(3000)
    after_shot = shot(page, "dag_after_trigger")
    ctx.close()
    browser.close()

    # Independent confirmation: not a browser check at all, but the
    # scheduler's own database, queried fresh via the CLI inside the
    # container - the strongest possible proof that a real DagRun object
    # was created, not just that a button animated.
    after_runs = dag_run_count(dag_id)
    persisted = after_runs > before_runs

    verdict = "PROVEN" if persisted else "NOT VERIFIED"
    results.append({
        "id": "CAP-019-01", "name": "DAG Trigger (workflow execution)", "route": f"/dags/{dag_id}",
        "discovered_from": "screen",
        "live_test": {
            "action": f"manually triggered a real run of the example DAG '{dag_id}' via the UI's own Trigger button",
            "dag_runs_before": before_runs, "dag_runs_after": after_runs,
            "independent_reconfirmation": persisted,
            "evidence": [before_shot, after_shot],
        },
        "verdict": verdict,
        "reason": (f"`airflow dags list-runs` inside the container - the scheduler's own database, queried "
                   f"independently of the browser session that triggered it - shows {after_runs} runs "
                   f"where there were {before_runs} before, proving a real DagRun was created server-side"
                   if persisted else "no new DagRun found after triggering"),
    })
    print(f"  {verdict:12s} DAG Trigger (workflow execution)")


def test_variable(pw, password):
    browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(15000)
    login(page, password)

    page.goto(f"{BASE}/variables", wait_until="networkidle")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Add Variable", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(800)
    page.get_by_label("Key", exact=False).first.fill(VAR_KEY)
    page.get_by_label("Value", exact=False).first.fill(VAR_VALUE)
    create_shot_pre = shot(page, "variable_form_filled")
    page.get_by_role("button", name="Save", exact=False).first.click(timeout=5000)
    page.wait_for_timeout(1500)
    create_shot = shot(page, "variable_created")
    ctx.close()
    browser.close()

    browser2 = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
    ctx2 = browser2.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
    page2 = ctx2.new_page()
    page2.set_default_timeout(15000)
    login(page2, password)
    page2.goto(f"{BASE}/variables", wait_until="networkidle")
    page2.wait_for_timeout(1200)
    list_shot = shot(page2, "variable_list_independent_reconfirm")
    persisted = page2.get_by_text(VAR_KEY, exact=False).count() > 0
    ctx2.close()
    browser2.close()

    verdict = "PROVEN" if persisted else "NOT VERIFIED"
    results.append({
        "id": "CAP-019-02", "name": "Admin - Variables", "route": "/variables",
        "discovered_from": "screen",
        "live_test": {
            "action": f"created a real Airflow Variable (key='{VAR_KEY}', value='{VAR_VALUE}') via the "
                      "Admin > Variables 'Add Variable' form",
            "independent_reconfirmation": persisted,
            "evidence": [create_shot_pre, create_shot, list_shot],
        },
        "verdict": verdict,
        "reason": ("variable now appears, by its exact given key, in the Variables list re-fetched from a "
                   "brand-new browser context + fresh login - proves it was really saved server-side" if persisted
                   else "variable did not appear on independent re-fetch"),
    })
    print(f"  {verdict:12s} Admin - Variables")


def main():
    password = get_admin_password()
    with sync_playwright() as pw:
        test_dag_trigger(pw, password)
        test_variable(pw, password)

    out = {"application": "APP-019", "capabilities_defined": True, "discovery_method": "app-derived",
          "verification_method": "manual (airflow_capabilities.py) - see screens.json's verification_note for why",
          "capabilities": results}
    (HERE / "capabilities.json").write_text(json.dumps(out, indent=1))
    proven = sum(1 for r in results if r["verdict"] == "PROVEN")
    print(json.dumps({"discovered": len(results), "proven": proven}, indent=1))


if __name__ == "__main__":
    main()
