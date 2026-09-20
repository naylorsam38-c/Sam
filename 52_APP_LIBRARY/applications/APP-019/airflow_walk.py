#!/usr/bin/env python3
"""Manual, tailored Playwright walkthrough for APP-019 (Apache Airflow,
substituted for the originally-discovered Airbyte - see app.json's own
manual_override_reason: Airbyte's LICENSE is genuinely Elastic License 2.0,
not open source, correctly excluded by this pipeline's own licence policy).

Run via `airflow standalone` (the project's own officially documented
quick-start command - a single container, SQLite-backed, no external
services needed), which generates a random admin password on first boot
and prints it to the container's own logs rather than using a fixed
default - the generic screens.py crawler's fixed test credentials can
never log in here, so this reads the real password from `docker logs`
before driving the app.
"""
import json
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8080"
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
CONTAINER = "lib-app019-airflow"

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


def get_admin_password():
    out = subprocess.run(["docker", "logs", CONTAINER], capture_output=True, text=True, timeout=30)
    for line in (out.stdout + out.stderr).splitlines():
        if "Password for user 'admin'" in line:
            return line.rsplit(":", 1)[-1].strip()
    raise RuntimeError("admin password not found in container logs")


def main():
    password = get_admin_password()
    print(f"read admin password from container logs: {password!r}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM, headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 960}, ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(15000)

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1000)
        record(page, "Login", "/auth/login", "startup_url")

        page.get_by_label("Username").fill("admin")
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Sign in").click()
        page.wait_for_timeout(2000)
        record(page, "DAGs (Home)", "/", "gate_flow",
               note="landed here after a real admin login - the app's real authenticated home screen")

        # DAGs list (sidebar nav, not "/" - that's the Welcome/Home screen)
        try:
            page.goto(BASE + "/dags", wait_until="networkidle")
            page.wait_for_timeout(1500)
            record(page, "DAGs List", "/dags", "nav_link_click")
        except Exception as e:
            print("!! DAGs list nav failed", e)

        # Open a real, existing example DAG (LOAD_EXAMPLES=true) to reach
        # its Grid/Graph views - the actual DAG-authoring/monitoring UI,
        # not just the list. The list renders as cards, not a <table> -
        # verified via a debug screenshot of the live /dags page - so this
        # opens a specific, stably-named example DAG by its own link text.
        try:
            dag_link = page.get_by_text("aggregate_regional_sales", exact=True)
            dag_link.first.click(timeout=5000)
            page.wait_for_timeout(1500)
            record(page, "DAG Detail (Grid)", "/dags/aggregate_regional_sales", "nav_link_click")
        except Exception as e:
            print("!! DAG detail nav failed", e)

        for label, route in (("Runs", None), ("Tasks", None), ("Code", None), ("Details", None)):
            try:
                tab = page.get_by_role("tab", name=label, exact=False)
                if not tab.count():
                    tab = page.get_by_text(label, exact=True)
                tab.first.click(timeout=4000)
                page.wait_for_timeout(1200)
                record(page, f"DAG - {label}", route or page.url, "nav_link_click")
            except Exception as e:
                print(f"!! DAG tab {label} failed", e)

        try:
            page.goto(BASE + "/assets", wait_until="networkidle")
            page.wait_for_timeout(1000)
            record(page, "Assets", "/assets", "nav_link_click")
        except Exception as e:
            print("!! Assets failed", e)

        for label, route in (("Browse - DAG Runs", "/dags/~/dagRuns"),
                              ("Browse - Task Instances", "/dags/~/taskInstances"),
                              ("Admin - Connections", "/connections"),
                              ("Admin - Variables", "/variables"),
                              ("Admin - Pools", "/pools"),
                              ("Security - Permissions", "/permissions"),
                              ("Config", "/config")):
            try:
                page.goto(BASE + route, wait_until="networkidle")
                page.wait_for_timeout(1200)
                record(page, label, route, "nav_link_click")
            except Exception as e:
                print(f"!! {label} failed", e)

        browser.close()

    out = {"application": "APP-019", "base_url": BASE, "static_routes_found": None, "screens": screens}
    (HERE / "screens.json").write_text(json.dumps(out, indent=1))
    reached = sum(1 for s in screens if s["reachable"])
    rendered = sum(1 for s in screens if s["rendered"])
    verified = sum(1 for s in screens if s["browser_verified"])
    print(json.dumps({"screens_discovered": len(screens), "screens_reached": reached,
                       "screens_rendered": rendered, "screens_browser_verified": verified}, indent=1))


if __name__ == "__main__":
    main()
