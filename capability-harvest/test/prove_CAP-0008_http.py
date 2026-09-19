#!/usr/bin/env python3
"""
prove_CAP-0008_http.py — real HTTP proof for CAP-0008 (award badge),
harvested from shaikayan2084/Bounty-Simulator.

No mocks. Against the real running composed app (build.py start --cap
CAP-0008): registers a real user, submits two real correct flags via the
real /submit endpoint (JWT-authenticated), crossing the real 100-XP
"First Blood" badge threshold, then confirms the badge via the real
/api/profile response -- and confirms it is NOT awarded again on a third
correct submission (the real idempotency check in check_badges()).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0008"
# Real seeded challenges (backend/seed.py) -- known flags, 50 XP each.
CHALLENGE_1 = {"id": 1, "flag": "FLAG{sql_injection_master}"}
CHALLENGE_2 = {"id": 2, "flag": "FLAG{xss_reflected}"}
CHALLENGE_3 = {"id": 3, "flag": "FLAG{idor_patient_data}"}


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    stamp = int(datetime.now(timezone.utc).timestamp())
    username = f"harvestproof{stamp}"
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    r = requests.post(f"{base_url}/api/register", json={
        "username": username, "email": f"{username}@example.test", "password": "CorrectHorseBattery9!",
    })
    record("register", r)
    assert r.status_code in (200, 201), r.text
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{base_url}/api/profile", headers=headers)
    record("profile_before", r)
    assert r.json()["badges"] == [], f"expected no badges yet, got {r.json()['badges']}"

    for challenge in (CHALLENGE_1, CHALLENGE_2):
        r = requests.post(f"{base_url}/api/challenges/{challenge['id']}/submit", json={"flag": challenge["flag"]}, headers=headers)
        record(f"submit_challenge_{challenge['id']}", r)
        assert r.status_code == 200, r.text

    r = requests.get(f"{base_url}/api/profile", headers=headers)
    record("profile_after_100xp", r, {"badges": r.json().get("badges")})
    badge_names = [b["badge_name"] if isinstance(b, dict) else b for b in r.json()["badges"]]
    assert "First Blood" in badge_names, f"expected 'First Blood' badge after crossing 100 XP, got {badge_names}"
    first_badge_count = len(badge_names)

    # Idempotency: a third correct submission (still under the 300 XP
    # "Learning Hacker" threshold) must not duplicate "First Blood".
    r = requests.post(f"{base_url}/api/challenges/{CHALLENGE_3['id']}/submit", json={"flag": CHALLENGE_3["flag"]}, headers=headers)
    record("submit_challenge_3", r)
    r = requests.get(f"{base_url}/api/profile", headers=headers)
    badge_names_after = [b["badge_name"] if isinstance(b, dict) else b for b in r.json()["badges"]]
    assert badge_names_after.count("First Blood") == 1, f"badge duplicated on repeat check: {badge_names_after}"

    evidence["badge_names_after_100xp"] = badge_names
    evidence["badge_names_after_200xp"] = badge_names_after
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real badges after 100 XP: {badge_names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
