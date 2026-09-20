#!/usr/bin/env python3
"""
prove_CAP-0009_http.py — real HTTP proof for CAP-0009 (show leaderboard),
harvested from shaikayan2084/Bounty-Simulator (same app as CAP-0008, a
different real attach point: leaderboard() vs check_badges()).

No mocks. Against the real running composed app (build.py start --cap
CAP-0009): registers two real users, gives each a different, real amount
of XP by submitting real correct flags, then confirms the real
/api/leaderboard response (a genuine `ORDER BY xp DESC LIMIT 50` query)
actually orders them by XP -- not just returns them in insertion order.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0009"
CHALLENGE_LOW = {"id": 1, "flag": "FLAG{sql_injection_master}"}  # 50 XP
CHALLENGE_HIGH = {"id": 3, "flag": "FLAG{idor_patient_data}"}    # 100 XP


def register(base_url, username):
    r = requests.post(f"{base_url}/api/register", json={
        "username": username, "email": f"{username}@example.test", "password": "CorrectHorseBattery9!",
    })
    assert r.status_code == 200, r.text
    return r.json()["token"]


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    stamp = int(datetime.now(timezone.utc).timestamp())
    low_user = f"harvestlow{stamp}"
    high_user = f"harvesthigh{stamp}"
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    low_token = register(base_url, low_user)
    high_token = register(base_url, high_user)

    r = requests.post(f"{base_url}/api/challenges/{CHALLENGE_LOW['id']}/submit", json={"flag": CHALLENGE_LOW["flag"]},
                       headers={"Authorization": f"Bearer {low_token}"})
    record("low_user_submits_50xp", r)
    assert r.status_code == 200

    r = requests.post(f"{base_url}/api/challenges/{CHALLENGE_HIGH['id']}/submit", json={"flag": CHALLENGE_HIGH["flag"]},
                       headers={"Authorization": f"Bearer {high_token}"})
    record("high_user_submits_100xp", r)
    assert r.status_code == 200

    r = requests.get(f"{base_url}/api/leaderboard")
    record("fetch_leaderboard", r)
    assert r.status_code == 200
    board = r.json()

    names = [entry["username"] for entry in board]
    assert low_user in names and high_user in names, f"both real users should appear on the real leaderboard: {names}"
    low_rank = names.index(low_user)
    high_rank = names.index(high_user)
    assert high_rank < low_rank, (
        f"expected the 100-XP user ({high_user}) to rank above the 50-XP user ({low_user}), "
        f"got order {names}"
    )

    evidence["leaderboard_excerpt"] = [e for e in board if e["username"] in (low_user, high_user)]
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real leaderboard order confirms {high_user} (100xp) ranks above {low_user} (50xp)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
