#!/usr/bin/env python3
"""
prove_capability_http.py — real HTTP proof for CAP-0001 (export data).

No mocks, no canned responses. Against the REAL running composed app
(started by build.py), this script:
  1. Registers a brand-new real user via POST /register
  2. Logs in via POST /login (real session cookie)
  3. Adds a real expense via POST /add
  4. Requests GET /export with that real session
  5. Parses the real CSV response body and asserts the expense is in it

Writes shelf/<app-slug>/<CAP-ID>/evidence/TEST_EVIDENCE.json with the real
request/response evidence -- status codes, headers, and the actual CSV rows
observed, not a description of what should happen.

Run (after `python3 build.py start`):
    ./.venv/bin/python3 test/prove_capability_http.py
"""

import csv
import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

BASE_URL = "http://127.0.0.1:5057"
CAP_ID = "CAP-0001"


def main():
    config.print_roots(__file__)

    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    # Adversarial check first: /export must genuinely require login, not
    # just happen to work because we always test it authenticated.
    anon = requests.get(f"{base_url}/export", allow_redirects=False)
    assert anon.status_code == 302 and "/login" in anon.headers.get("Location", ""), \
        f"expected /export to redirect anonymous requests to /login, got {anon.status_code} {anon.headers.get('Location')}"
    evidence_anon_check = {"status_code": anon.status_code, "location": anon.headers.get("Location")}
    print(f"  [anonymous_export_check] GET /export (no session) -> {anon.status_code} -> {anon.headers.get('Location')}")

    session = requests.Session()
    stamp = int(time.time())
    username = f"harvest-proof-{stamp}"
    email = f"harvest-proof-{stamp}@example.test"
    password = "CorrectHorseBattery9!"

    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": [], "anonymous_access_check": evidence_anon_check}

    def record(step, response, extra=None):
        entry = {
            "step": step,
            "method": response.request.method,
            "url": response.request.url,
            "status_code": response.status_code,
        }
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    # 1. Register a real new user
    r = session.post(f"{base_url}/register", data={
        "username": username, "email": email, "password": password, "confirm_password": password,
    }, allow_redirects=True)
    record("register", r)
    assert r.status_code == 200, f"register failed unexpectedly: {r.status_code}"

    # 2. Log in
    r = session.post(f"{base_url}/login", data={"email": email, "password": password}, allow_redirects=True)
    record("login", r)
    assert r.status_code == 200 and ("Dashboard" in r.text or "dashboard" in r.text.lower()), \
        "login did not appear to succeed (expected dashboard content)"

    # 3. Add a real expense
    expense = {
        "description": "Capability-harvest proof expense",
        "expense_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "category": "HarvestProof",
        "amount": "42.42",
    }
    r = session.post(f"{base_url}/add", data=expense, allow_redirects=True)
    record("add_expense", r, {"expense": expense})
    assert r.status_code == 200, f"add expense failed: {r.status_code}"

    # 4. Exercise the harvested capability for real: GET /export
    r = session.get(f"{base_url}/export")
    record("export", r, {"content_type": r.headers.get("Content-Type"), "content_disposition": r.headers.get("Content-Disposition")})
    assert r.status_code == 200, f"export failed: {r.status_code}"
    assert "text/csv" in r.headers.get("Content-Type", ""), "export did not return text/csv"

    # 5. Parse the REAL csv body and assert our real expense is in it
    rows = list(csv.reader(io.StringIO(r.text)))
    matching = [row for row in rows if expense["description"] in row]
    assert matching, f"harvested expense not found in exported CSV -- rows were: {rows}"

    evidence["csv_rows_observed"] = rows
    evidence["expense_found_in_export"] = True
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()
    evidence["result"] = "PASS"

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Observed CSV rows:\n" + "\n".join(",".join(row) for row in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
