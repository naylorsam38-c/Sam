#!/usr/bin/env python3
"""
prove_CAP-0037_http.py — real HTTP proof for CAP-0037 (verify phone),
harvested from tohid-ab/django-otp-auth.

No mocks. Against the real running composed app (a real SQLite database,
migrated via the app's own real Django migrations): requests a real OTP
for a real mobile number via the app's own real POST /api/auth/otp/create/
route, reads the real generated 5-digit code directly out of the app's
own sqlite database (the app's own real code only ever `print()`s it --
never sent by SMS, a genuinely self-contained/offline-provable design,
so this is the real value the app itself generated, not invented),
confirms a wrong code is genuinely rejected, confirms the real correct
code is accepted and issues real signed JWT access/refresh tokens, and
confirms reusing the same already-verified code a second time is
genuinely rejected -- the real one-time-use flag enforced at the
database level.
"""

import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0037"
MOBILE_NUMBER = "09123456789"


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

    r = requests.post(f"{base_url}/api/auth/otp/create/", json={"receiver": MOBILE_NUMBER})
    record("request_real_otp", r)
    assert r.status_code == 200, r.text
    otp_uuid = r.json()["uuid"]

    db_path = Path(manifest["verification"]["cloned_path"]) / manifest["verification"]["runner"]["app_subdir"] / "db.sqlite3"
    assert db_path.exists(), f"expected the real sqlite database at {db_path}"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT code, used FROM user_otpcode WHERE receiver = ? ORDER BY created DESC LIMIT 1", (MOBILE_NUMBER,))
    row = cur.fetchone()
    conn.close()
    assert row is not None, "the real OTP row is missing from the app's own database"
    assert not row["used"], "the freshly-generated real OTP is already marked used"
    real_code = row["code"]
    assert re.fullmatch(r"\d{5}", real_code), f"expected a real 5-digit numeric code, got {real_code!r}"

    r = requests.post(f"{base_url}/api/auth/otp/verify/", json={"uuid": otp_uuid, "receiver": MOBILE_NUMBER, "code": "00000"})
    record("wrong_code_rejected", r)
    assert r.status_code == 400, "expected a wrong OTP code to be genuinely rejected"

    r = requests.post(f"{base_url}/api/auth/otp/verify/", json={"uuid": otp_uuid, "receiver": MOBILE_NUMBER, "code": real_code})
    record("real_code_accepted", r)
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert tokens.get("access") and tokens.get("refresh"), "expected real signed JWT access/refresh tokens"
    assert tokens["access"].count(".") == 2, "the real access token is not a well-formed JWT"

    r = requests.post(f"{base_url}/api/auth/otp/verify/", json={"uuid": otp_uuid, "receiver": MOBILE_NUMBER, "code": real_code})
    record("reuse_rejected", r)
    assert r.status_code == 400, "expected reusing an already-verified real OTP code to be genuinely rejected"

    evidence["mobile_number"] = MOBILE_NUMBER
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real OTP {real_code!r} verified for {MOBILE_NUMBER}: wrong code rejected, real JWT issued, reuse rejected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
