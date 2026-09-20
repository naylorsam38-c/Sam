#!/usr/bin/env python3
"""
prove_CAP-0023_http.py — real HTTP proof for CAP-0023 (edit profile),
harvested from rafaelsmedina/dataviva-training.

No mocks. Against the real running composed app: registers a genuinely
new account, logs in, confirms an anonymous request to /edit_profile is
rejected, edits the real profile's about_me text, and confirms the new
text appears on a fresh real GET of that user's own public profile page
-- proving a real persisted update, not a form that silently no-ops.
"""

import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0023"


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

    r = requests.get(f"{base_url}/edit_profile", allow_redirects=False)
    record("anonymous_edit_profile_check", r)
    assert r.status_code == 302, f"expected an anonymous redirect, got {r.status_code}"

    unique = int(time.time()) % 100000
    username = f"hproof{unique}"
    email = f"{username}@example.com"
    password = "HarvestProof123!"

    session = requests.Session()
    r = session.get(f"{base_url}/register")
    record("fetch_register_form", r)
    csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)

    r = session.post(f"{base_url}/register", data={
        "username": username, "email": email, "password": password, "password2": password, "csrf_token": csrf_token,
    })
    record("register_new_account", r, {"username": username})
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/login")
    csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
    r = session.post(f"{base_url}/login", data={"username": username, "password": password, "csrf_token": csrf_token})
    record("login", r)
    assert r.status_code == 200, r.text

    about_me = f"Real about-me text written by the harvest proof at {datetime.now(timezone.utc).isoformat()}."
    r = session.get(f"{base_url}/edit_profile")
    record("fetch_edit_profile_form", r)
    csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)

    r = session.post(f"{base_url}/edit_profile", data={
        "username": username, "about_me": about_me, "csrf_token": csrf_token,
    })
    record("submit_edit_profile", r)
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/user/{username}")
    record("fetch_public_profile_after_edit", r)
    assert r.status_code == 200
    assert about_me in r.text, "the real submitted about_me text does not appear on a fresh page load -- update did not persist"

    evidence["username"] = username
    evidence["about_me"] = about_me
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real profile edit for {username} persisted and confirmed on a fresh page load.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
