#!/usr/bin/env python3
"""
prove_CAP-0017_http.py — real HTTP proof for CAP-0017 (log in),
harvested from Raviraj0001/Hospital_Management_Real.

No mocks. Against the real running composed app: confirms a wrong
password is genuinely rejected (stays on the same real login page, no
session established, no redirect to the dashboard), then logs in with the
app's own real seeded Admin credentials and confirms the real
authenticated dashboard becomes reachable -- proving the credential check
and session establishment are real, not decorative.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0017"
ADMIN_EMAIL = "admin@hospital.local"  # the app's own seeded demo admin
ADMIN_PASSWORD = "Admin@123"


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    # Anonymous access to the dashboard must not work before any login.
    anon = requests.Session()
    r = anon.get(f"{base_url}/dashboard", allow_redirects=False)
    record("anonymous_dashboard_check", r)
    assert r.status_code == 302, f"expected an anonymous redirect, got {r.status_code}"

    wrong = requests.Session()
    r = wrong.post(f"{base_url}/login", data={"email": ADMIN_EMAIL, "password": "definitely-wrong-password"})
    record("login_with_wrong_password", r)
    assert r.status_code == 200, r.text
    assert "Sign in" in r.text, "expected to stay on the real login page after a wrong password"

    r = wrong.get(f"{base_url}/dashboard", allow_redirects=False)
    record("dashboard_still_unreachable_after_failed_login", r)
    assert r.status_code == 302, "a session was established despite the wrong password -- real credential check failed"

    session = requests.Session()
    r = session.post(f"{base_url}/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    record("login_with_real_admin_credentials", r)
    assert r.status_code == 200, r.text
    assert "Dashboard" in r.text or "dashboard" in r.request.url, "real login did not reach the dashboard"

    r = session.get(f"{base_url}/dashboard")
    record("fetch_dashboard_after_login", r)
    assert r.status_code == 200
    assert "Hospital Admin" in r.text, "dashboard did not reflect the real logged-in admin's own name"

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print("Wrong password rejected (no session, dashboard unreachable); real admin credentials established a real session.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
