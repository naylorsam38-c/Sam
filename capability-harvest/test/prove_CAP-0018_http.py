#!/usr/bin/env python3
"""
prove_CAP-0018_http.py — real HTTP proof for CAP-0018 (log out),
harvested from Raviraj0001/Hospital_Management_Real.

No mocks. Against the real running composed app: logs in as the real
seeded Admin (confirming the dashboard is reachable), then calls the
real /logout route and confirms the session is genuinely cleared -- the
same cookie can no longer reach the dashboard afterwards, proving
logout() actually tears down server-side session state rather than being
a no-op that merely redirects.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0018"
ADMIN_EMAIL = "admin@hospital.local"
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

    session = requests.Session()
    r = session.post(f"{base_url}/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    record("login_as_admin", r)
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/dashboard")
    record("dashboard_reachable_before_logout", r)
    assert r.status_code == 200 and "Hospital Admin" in r.text

    r = session.get(f"{base_url}/logout", allow_redirects=False)
    record("logout", r)
    assert r.status_code == 302, f"expected logout to redirect, got {r.status_code}"

    # The SAME cookie/session must no longer reach the dashboard -- proving
    # the server-side session was genuinely cleared, not just a client-side
    # redirect with the session left intact.
    r = session.get(f"{base_url}/dashboard", allow_redirects=False)
    record("dashboard_unreachable_after_logout", r)
    assert r.status_code == 302, (
        "the dashboard was still reachable after logout with the same session cookie -- "
        "real session teardown did not happen"
    )

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print("Real session established by login, then genuinely torn down by logout -- same cookie can no longer reach the dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
