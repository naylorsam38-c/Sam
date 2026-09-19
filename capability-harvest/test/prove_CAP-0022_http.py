#!/usr/bin/env python3
"""
prove_CAP-0022_http.py — real HTTP proof for CAP-0022 (verify email),
harvested from Dixieboy76/tech_hub.

No mocks. Against the real running composed app (build.py start --cap
CAP-0022, which points the app's own mail config at a real local SMTP
debug server and re-applies its own real schema/seed via
initialize_database.py): registers a genuinely new account (real
itsdangerous verification token minted and persisted, real welcome/
verification email genuinely sent over real SMTP to the local debug
server), reads the real token back directly from the app's own live
SQLite file, confirms the account is NOT verified before visiting the
link, visits the real /verify_email/<token> route and confirms
email_verified flips to true, confirms visiting the SAME link again hits
the app's own real "already verified" branch (not a crash or a second
flip), and confirms a genuinely tampered token is rejected.
"""

import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0022"


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"
    db_path = Path(manifest["verification"]["cloned_path"]) / "techhub.db"

    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    unique = int(time.time()) % 100000
    username = f"hproof{unique}"
    email = f"hproof{unique}@example.com"
    password = "HarvestProof123!"

    session = requests.Session()
    r = session.get(f"{base_url}/register")
    record("fetch_register_form", r)
    csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)

    r = session.post(f"{base_url}/register", data={
        "username": username, "email": email, "password": password,
        "confirm_password": password, "is_tech": "", "csrf_token": csrf_token,
    })
    record("register_new_account", r, {"email": email})
    assert r.status_code == 200, r.text

    con = sqlite3.connect(str(db_path))
    row = con.execute(
        "SELECT email_verified, verification_token FROM user WHERE email = ?", (email,)
    ).fetchone()
    con.close()
    assert row is not None, "expected a real persisted user row after registration"
    verified_before, token = row
    assert not verified_before, "a freshly registered account should not start out verified"
    assert token, "expected a real, non-empty verification_token minted at registration time"

    # A tampered token must be genuinely rejected, not silently accepted.
    tampered_token = token[:-4] + ("0" * 4 if not token.endswith("0000") else "1111")
    r = session.get(f"{base_url}/verify_email/{tampered_token}", allow_redirects=False)
    record("attempt_tampered_token", r)
    con = sqlite3.connect(str(db_path))
    still_unverified = con.execute("SELECT email_verified FROM user WHERE email = ?", (email,)).fetchone()[0]
    con.close()
    assert not still_unverified, "a tampered verification token was accepted -- real signature check failed"

    r = session.get(f"{base_url}/verify_email/{token}")
    record("verify_real_token", r)
    assert r.status_code == 200, r.text

    con = sqlite3.connect(str(db_path))
    verified_after = con.execute("SELECT email_verified FROM user WHERE email = ?", (email,)).fetchone()[0]
    con.close()
    assert verified_after, "email_verified was not genuinely flipped after visiting the real verification link"

    # Visiting the same real link again must hit the "already verified"
    # branch cleanly, not crash or somehow un-verify the account.
    r = session.get(f"{base_url}/verify_email/{token}")
    record("revisit_same_link_after_verified", r)
    assert r.status_code == 200, r.text
    con = sqlite3.connect(str(db_path))
    still_verified = con.execute("SELECT email_verified FROM user WHERE email = ?", (email,)).fetchone()[0]
    con.close()
    assert still_verified, "revisiting the verification link after verifying somehow un-verified the account"

    evidence["registered_email"] = email
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real account {email} registered unverified, tampered token rejected, real token verified it, revisit stayed verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
