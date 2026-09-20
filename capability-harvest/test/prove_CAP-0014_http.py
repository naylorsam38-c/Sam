#!/usr/bin/env python3
"""
prove_CAP-0014_http.py — real HTTP proof for CAP-0014 (book slot),
harvested from Raviraj0001/Hospital_Management_Real.

No mocks. Against the real running composed app (build.py start --cap
CAP-0014, which resets the repo's own committed instance/hospital.db and
re-seeds real demo doctors/patients at import time): logs in as the real
seeded demo patient, books a real appointment slot, then attempts to book
the SAME doctor/slot a second time and confirms the app's own real
conflict check rejects it (no second row persisted), then books a
DIFFERENT slot for the same doctor and confirms both real, distinct
appointments persist independently.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0014"
PATIENT_EMAIL = "patient@hospital.local"  # the app's own seeded demo patient
PATIENT_PASSWORD = "Patient@123"
DOCTOR_ID = 1  # Dr. Ananya Sharma, the app's own seeded demo doctor


def _count_scheduled(html: str, time_label: str) -> int:
    # The portal renders each appointment as its own <tr>...</tr> row;
    # count how many contain this exact time label alongside "Scheduled".
    return sum(
        1 for row in html.split("<tr>")
        if time_label in row and "Scheduled" in row
    )


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

    # Anonymous access to the patient portal must not work -- real access
    # control, checked adversarially before proving the authenticated path.
    r = session.get(f"{base_url}/patient", allow_redirects=False)
    record("anonymous_portal_check", r)
    assert r.status_code == 302, f"expected an anonymous redirect, got {r.status_code}"

    r = session.post(f"{base_url}/patient/login", data={"email": PATIENT_EMAIL, "password": PATIENT_PASSWORD})
    record("patient_login", r)
    assert r.status_code == 200, r.text
    assert "Patient Portal" in r.text, "login did not reach the real patient portal"

    slot_1 = "2027-03-15T10:00"
    slot_1_label = "15 Mar 2027 10:00 AM"
    r = session.post(f"{base_url}/patient/book", data={
        "doctor_id": DOCTOR_ID, "appointment_date": slot_1, "reason": "Capability-harvest proof booking",
    })
    record("book_first_slot", r, {"doctor_id": DOCTOR_ID, "appointment_date": slot_1})
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/patient")
    record("portal_after_first_booking", r)
    assert _count_scheduled(r.text, slot_1_label) == 1, (
        f"expected exactly one real Scheduled row for {slot_1_label} after the first booking"
    )

    # Real conflict check: same doctor, same exact slot, second attempt.
    r = session.post(f"{base_url}/patient/book", data={
        "doctor_id": DOCTOR_ID, "appointment_date": slot_1, "reason": "Duplicate attempt -- must be rejected",
    })
    record("attempt_duplicate_slot", r)
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/patient")
    record("portal_after_duplicate_attempt", r)
    duplicate_count = _count_scheduled(r.text, slot_1_label)
    assert duplicate_count == 1, (
        f"real conflict check failed to reject a double-booking -- found {duplicate_count} "
        f"Scheduled rows for {slot_1_label}, expected exactly 1"
    )

    # A genuinely different slot for the same doctor must still succeed --
    # proving the rejection above was about the specific slot, not the doctor.
    slot_2 = "2027-03-15T10:30"
    slot_2_label = "15 Mar 2027 10:30 AM"
    r = session.post(f"{base_url}/patient/book", data={
        "doctor_id": DOCTOR_ID, "appointment_date": slot_2, "reason": "Second real slot, different time",
    })
    record("book_second_distinct_slot", r)
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/patient")
    record("portal_after_second_booking", r)
    assert _count_scheduled(r.text, slot_1_label) == 1, "first booking should still be present, unaffected"
    assert _count_scheduled(r.text, slot_2_label) == 1, "second, distinct real slot did not persist"

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real double-booking rejected for {slot_1_label}; distinct slot {slot_2_label} booked independently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
