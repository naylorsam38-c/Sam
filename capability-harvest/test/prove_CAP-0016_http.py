#!/usr/bin/env python3
"""
prove_CAP-0016_http.py — real HTTP proof for CAP-0016 (register account),
harvested from Raviraj0001/Hospital_Management_Real.

No mocks. Against the real running composed app: submits a real patient
self-registration form, then proves the account is real (not a no-op) by
immediately logging in with the EXACT password just submitted -- a real
round trip through the real password hash, not just trusting the
registration response. (This app's own base.html only renders flashed
messages on the authenticated-shell layout, never on the public patient
pages -- confirmed by reading the template -- so this proof deliberately
does not depend on flash text, only on real, directly observable
before/after login behaviour.) Also proves the app's own real
already-exists guard: a second registration attempt with the same email
but a different password does not overwrite the original account.
"""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0016"


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

    unique = int(time.time())
    email = f"harvest-proof-{unique}@example.test"
    password = f"HarvestProof!{unique}"

    session = requests.Session()
    r = session.post(f"{base_url}/patient/register", data={
        "name": "Harvest Proof Patient", "age": "29", "gender": "Other",
        "phone": f"9{unique % 1000000000}", "email": email, "blood_group": "O+", "password": password,
    })
    record("register_new_patient", r, {"email": email})
    assert r.status_code == 200, r.text

    # Real round-trip: log in with exactly the credentials just submitted.
    r = session.post(f"{base_url}/patient/login", data={"email": email, "password": password})
    record("login_with_new_credentials", r)
    assert r.status_code == 200, r.text
    assert "Patient Portal" in r.text, "newly registered account could not log in with its own real submitted password"
    assert "Harvest Proof Patient" in r.text, "portal did not reflect the real registered patient's own name"

    # A second registration attempt for the SAME email with a DIFFERENT
    # password must not silently overwrite the original account.
    other_session = requests.Session()
    other_session.post(f"{base_url}/patient/register", data={
        "name": "Duplicate Attempt", "age": "40", "gender": "Other",
        "phone": "9000000000", "email": email, "blood_group": "A+", "password": "WrongPassword123",
    })
    r = other_session.post(f"{base_url}/patient/login", data={"email": email, "password": "WrongPassword123"})
    record("attempt_login_with_duplicate_registration_password", r)
    assert "Patient Portal" not in r.text, (
        "logging in with the DUPLICATE registration's password succeeded -- "
        "the real already-exists guard did not prevent overwriting the original account"
    )

    r = session.post(f"{base_url}/patient/login", data={"email": email, "password": password})
    record("original_credentials_still_work", r)
    assert "Patient Portal" in r.text, "original account's real password stopped working after the duplicate attempt"

    evidence["registered_email"] = email
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real account registered ({email}) and immediately logged in with its own submitted password; duplicate registration did not overwrite it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
