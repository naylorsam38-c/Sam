#!/usr/bin/env python3
"""
prove_CAP-0021_http.py — real HTTP proof for CAP-0021 (set permissions),
harvested from RishiS-HSCProjects/EnterpriseProject.

No mocks. Against the real running composed app (build.py start --cap
CAP-0021, which seeds two real accounts -- an admin and a staff member --
directly via the app's own real User/Whitelist models, since the app's
own real registration/whitelisting path requires a live third-party
NetherGames Minecraft API this sandbox cannot and should not depend on;
update_role() itself is exercised entirely through its own real,
unmodified HTTP route):

- Logs in as the real seeded admin and promotes the real seeded staff
  account to Manager, confirming the change is genuinely persisted (shows
  up on a fresh GET of the real admin panel).
- Confirms the app's own real self-demotion guard rejects an admin
  changing their own role.
- Confirms the app's own real access-control guard rejects a non-admin
  (even the just-promoted Manager) from calling the route at all.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0021"
ADMIN_USERNAME = "AdminTester"
ADMIN_PASSWORD = "AdminPass123!"
STAFF_USERNAME = "StaffTester"
STAFF_PASSWORD = "StaffPass123!"
STAFF_WHITELIST_ENTRY_ID = 2  # seeded second, after the admin's own entry (id 1)
ADMIN_WHITELIST_ENTRY_ID = 1


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

    def login(session, username, password):
        r = session.get(f"{base_url}/login")
        csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
        return session.post(f"{base_url}/login", data={"username": username, "password": password, "csrf_token": csrf_token})

    admin = requests.Session()
    r = login(admin, ADMIN_USERNAME, ADMIN_PASSWORD)
    record("admin_login", r)
    assert r.status_code == 200, r.text

    r = admin.post(f"{base_url}/admin/update_role/{STAFF_WHITELIST_ENTRY_ID}", json={"role": "manager"})
    record("promote_staff_to_manager", r)
    body = r.json()
    assert body["success"] is True, f"real role change was rejected unexpectedly: {body}"

    r = admin.get(f"{base_url}/admin/")
    record("fetch_admin_panel_after_promotion", r)
    assert r.status_code == 200 and "Manager" in r.text, "promoted role does not appear on a fresh real page load"

    r = admin.post(f"{base_url}/admin/update_role/{ADMIN_WHITELIST_ENTRY_ID}", json={"role": "staff"})
    record("attempt_self_demotion", r)
    self_body = r.json()
    assert r.status_code == 403 and self_body["success"] is False, (
        f"real self-demotion guard did not reject the admin changing their own role: {self_body}"
    )

    manager = requests.Session()
    r = login(manager, STAFF_USERNAME, STAFF_PASSWORD)
    record("promoted_manager_login", r)
    assert r.status_code == 200, r.text

    r = manager.post(f"{base_url}/admin/update_role/{ADMIN_WHITELIST_ENTRY_ID}", json={"role": "staff"}, allow_redirects=False)
    record("non_admin_attempts_role_change", r)
    assert r.status_code == 302, (
        f"a non-admin (Manager) was not redirected away from the admin-only route -- got {r.status_code}"
    )

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print("Real role change persisted (Staff -> Manager); self-demotion rejected (403); non-admin access rejected (302).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
