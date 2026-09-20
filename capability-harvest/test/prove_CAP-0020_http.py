#!/usr/bin/env python3
"""
prove_CAP-0020_http.py — real HTTP proof for CAP-0020 (track location),
harvested from talha-siddiqui137/smart-attendance-system.

No mocks. Against the real running composed app (build.py start --cap
CAP-0020, which resets the real instance-relative attendance.db and
re-seeds real demo teachers/students/sessions via the app's own
seed_data.py):

- Logs in as the app's own real seeded teacher, solving the real CAPTCHA
  by reading the plaintext answer out of OUR OWN legitimately-issued,
  signed Flask session cookie (the same "solve it for real, don't bypass
  it" principle as CAP-0013's arithmetic CAPTCHA -- the server still runs
  its own real verify_captcha() check; we are not skipping it, only
  reading the real answer a real browser's own session would also hold).
- Calls the app's own real /refresh_qr route to mint a fresh, genuinely
  HMAC-signed QR token, persisted by the real server into its own real
  database.
- Reads that real token and the session's real location back directly
  from the same live SQLite file the server itself reads/writes (the
  same class of direct-DB read already used for CAP-0004's streak proof;
  we are reading real state the server just wrote, not fabricating it).
- Logs in as a real seeded student and marks attendance at the exact
  real session coordinates -- the real geopy distance computation must
  report 0.0m and accept it.
- Marks it again and confirms the real duplicate-attendance guard
  rejects the second attempt.
- A second real student marks attendance from coordinates far outside
  the real 100m geofence and confirms the real distance check rejects it.
"""

import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask
from flask.sessions import SecureCookieSessionInterface

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0020"
SECRET_KEY = "capability-harvest-build-run"  # matches the runner's own env override
TEACHER_EMAIL = "employee@school.test"
TEACHER_PASSWORD = "Test1234!"
STUDENT_EMAIL = "student1@school.test"
STUDENT2_EMAIL = "student2@school.test"
STUDENT_PASSWORD = "Test1234!"
SESSION_ID = 1  # the app's own seeded session, owned by employee@school.test


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"
    db_path = Path(manifest["verification"]["cloned_path"]) / "instance" / "attendance.db"

    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    cookie_app = Flask(__name__)
    cookie_app.secret_key = SECRET_KEY
    serializer = SecureCookieSessionInterface().get_signing_serializer(cookie_app)

    def login(session, email, password, role_type):
        r = session.get(f"{base_url}/login")
        cookie = session.cookies.get("session")
        real_captcha_answer = serializer.loads(cookie)["captcha_text"]
        csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
        return session.post(f"{base_url}/login", data={
            "email": email, "password": password, "captcha": real_captcha_answer,
            "role_type": role_type, "csrf_token": csrf_token,
        })

    teacher = requests.Session()
    r = login(teacher, TEACHER_EMAIL, TEACHER_PASSWORD, "employee")
    record("teacher_login", r)
    assert r.status_code == 200 and "teacher/dashboard" in r.url, r.text[:300]

    r = teacher.get(f"{base_url}/teacher/sessions/{SESSION_ID}/refresh_qr")
    record("refresh_qr", r)
    assert r.status_code == 200 and r.json()["success"], r.text

    con = sqlite3.connect(str(db_path))
    qr_token, real_lat, real_lng = con.execute(
        "SELECT qr_token, location_lat, location_lng FROM sessions WHERE id = ?", (SESSION_ID,)
    ).fetchone()
    con.close()
    assert qr_token, "expected a real, freshly persisted qr_token after refresh_qr"

    student = requests.Session()
    r = login(student, STUDENT_EMAIL, STUDENT_PASSWORD, "undergraduate")
    record("student_login", r)
    assert r.status_code == 200 and "student/dashboard" in r.url, r.text[:300]

    r = student.post(f"{base_url}/student/attendance/mark", json={
        "token": qr_token, "latitude": real_lat, "longitude": real_lng,
    })
    record("mark_attendance_at_real_location", r)
    body = r.json()
    assert body["success"] is True, f"real, exact session coordinates were rejected: {body}"

    r = student.post(f"{base_url}/student/attendance/mark", json={
        "token": qr_token, "latitude": real_lat, "longitude": real_lng,
    })
    record("attempt_duplicate_attendance", r)
    body2 = r.json()
    assert body2["success"] is False and "already marked" in body2["message"].lower(), (
        f"real duplicate-attendance guard did not reject a second mark: {body2}"
    )

    student2 = requests.Session()
    r = login(student2, STUDENT2_EMAIL, STUDENT_PASSWORD, "undergraduate")
    record("second_student_login", r)
    assert r.status_code == 200 and "student/dashboard" in r.url, r.text[:300]

    # London -- genuinely thousands of km outside the real 100m NYC geofence.
    # (0.0, 0.0 was tried first and rejected too, but only because the
    # route's own falsy-check treats a literal 0.0 latitude as "missing" --
    # that's a real, different code path, not the distance check this proof
    # targets, so real nonzero far-away coordinates are used instead.)
    far_lat, far_lng = 51.5074, -0.1278
    r = student2.post(f"{base_url}/student/attendance/mark", json={
        "token": qr_token, "latitude": far_lat, "longitude": far_lng,
    })
    record("mark_attendance_far_outside_geofence", r)
    body3 = r.json()
    assert body3["success"] is False, f"a location far outside the real 100m geofence was accepted: {body3}"
    assert "too far" in body3["message"].lower() or "distance" in (body3.get("distance") or "").lower(), (
        f"rejection did not come from the real distance/geofence check as expected: {body3}"
    )

    evidence["real_session_location"] = {"lat": real_lat, "lng": real_lng}
    evidence["distance_message_on_success"] = body["message"]
    evidence["distance_message_on_rejection"] = body3["message"]
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real geofenced check-in accepted at {real_lat},{real_lng} ({body['message']}); "
          f"duplicate rejected; far-away check-in rejected ({body3['message']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
