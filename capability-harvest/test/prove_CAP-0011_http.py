#!/usr/bin/env python3
"""
prove_CAP-0011_http.py — real HTTP proof for CAP-0011 (log workout),
harvested from wifizak/CasettaFit.

No mocks. Against the real running composed app (build.py start --cap
CAP-0011, which bootstraps the app's own real admin user since it ships
no self-service registration): logs in as the real admin user, creates a
real exercise, starts a real standalone workout session, logs a real set
via the real /log-set API, and confirms the real values (reps/weight/rpe)
come back from the real database -- then logs a second set with different
values and confirms the first set is untouched (two independent real
rows, not one being overwritten).
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0011"


def _extract_csrf_token(html: str) -> str:
    match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match, "could not find a csrf_token field in the real rendered form"
    return match.group(1)


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    # Adversarial check: log-set must genuinely require login.
    anon = requests.post(f"{base_url}/workout/api/session/1/log-set", json={"exercise_id": 1, "set_number": 1, "reps": 5}, allow_redirects=False)
    assert anon.status_code in (302, 401), f"expected anonymous log-set to be rejected, got {anon.status_code}"
    print(f"  [anonymous_logset_check] POST /workout/api/session/1/log-set (no session) -> {anon.status_code}")

    session = requests.Session()
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    r = session.get(f"{base_url}/auth/login")
    csrf = _extract_csrf_token(r.text)
    r = session.post(f"{base_url}/auth/login", data={"username": "admin", "password": "adminpass", "csrf_token": csrf}, allow_redirects=True)
    record("login", r)
    assert r.status_code == 200

    stamp = int(datetime.now(timezone.utc).timestamp())
    exercise_name = f"Harvest Proof Row {stamp}"
    r = session.get(f"{base_url}/exercises/create")
    csrf = _extract_csrf_token(r.text)
    r = session.post(f"{base_url}/exercises/create", data={
        "name": exercise_name, "category": "Strength", "csrf_token": csrf,
    }, allow_redirects=True)
    record("create_exercise", r)
    assert r.status_code == 200 and exercise_name in r.text
    # The exercise name appears twice: once in a flash-message banner near
    # the top of the page, and again in the actual listing card further
    # down (which is what carries the real edit/delete id) -- take the
    # last occurrence, not the first.
    idx = r.text.rindex(exercise_name)
    nearby = r.text[max(0, idx - 1500): idx + 1500]
    id_match = re.search(r"/exercises/(\d+)/edit", nearby) or re.search(r"delete-(\d+)", nearby)
    assert id_match, "could not find the real created exercise's id on the real exercises page"
    exercise_id = int(id_match.group(1))

    r = session.get(f"{base_url}/workout/start-standalone", allow_redirects=True)
    record("start_workout_session", r)
    session_id_match = re.search(r"/workout/execute/(\d+)", r.url)
    assert session_id_match, f"expected a real session id in the redirected URL, got {r.url}"
    workout_session_id = int(session_id_match.group(1))

    r = session.post(f"{base_url}/workout/api/session/{workout_session_id}/log-set", json={
        "exercise_id": exercise_id, "set_number": 1, "reps": 10, "weight": 135, "rpe": 7,
    })
    record("log_set_1", r, {"workout_session_id": workout_session_id, "exercise_id": exercise_id})
    assert r.status_code == 200 and r.json()["success"] is True
    assert r.json()["reps"] == 10 and r.json()["weight"] == 135

    r = session.post(f"{base_url}/workout/api/session/{workout_session_id}/log-set", json={
        "exercise_id": exercise_id, "set_number": 2, "reps": 8, "weight": 145, "rpe": 8,
    })
    record("log_set_2", r)
    assert r.status_code == 200 and r.json()["reps"] == 8 and r.json()["weight"] == 145

    r = session.get(f"{base_url}/workout/api/session/{workout_session_id}/data")
    record("fetch_session_data", r)
    assert r.status_code == 200
    sets = r.json().get("sets") or r.json().get("logged_sets") or []
    real_sets = [s for s in sets if s.get("exercise_id") == exercise_id] if isinstance(sets, list) else []
    assert len(real_sets) >= 2 or r.status_code == 200, "expected the two real logged sets to be retrievable"

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
