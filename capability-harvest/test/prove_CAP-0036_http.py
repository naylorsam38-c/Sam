#!/usr/bin/env python3
"""
prove_CAP-0036_http.py — real HTTP proof for CAP-0036 (import data),
harvested from moustafa-shaaban/Django_and_Folium.

No mocks. Against the real running composed app (a real PostgreSQL
database, migrated via the app's own real Django migrations and seeded
with one real, already-verified user): confirms anonymous access to
the import route is genuinely rejected, logs in as the real seeded user
via the app's own real allauth login form, uploads a real CSV file
through the app's own real POST /import-data/ route (django-import-export's
real dry-run-then-commit path), and confirms the newly imported feature
row is genuinely persisted -- it appears on the real map page afterward,
which is only possible if it was actually written to the database, not
merely accepted and discarded.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0036"
USER_EMAIL = "harvestuser1@example.com"
USER_PASSWORD = "HarvestPass123!"


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

    r = requests.get(f"{base_url}/import-data/", allow_redirects=False)
    record("anonymous_import_page_check", r)
    assert r.status_code in (302, 401, 403), f"expected anonymous access to /import-data/ to be rejected, got {r.status_code}"

    session = requests.Session()
    r = session.get(f"{base_url}/accounts/login/")
    record("fetch_login_form", r)
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    assert csrf_match, "expected a real csrfmiddlewaretoken field on the login form"

    r = session.post(
        f"{base_url}/accounts/login/",
        data={"login": USER_EMAIL, "password": USER_PASSWORD, "csrfmiddlewaretoken": csrf_match.group(1)},
        headers={"Referer": f"{base_url}/accounts/login/"},
    )
    record("login_as_real_user", r)
    assert r.status_code == 200 and "/accounts/login" not in r.url, f"real login did not succeed: {r.url}"

    marker = f"HarvestImportedFeature{int(datetime.now(timezone.utc).timestamp())}"
    csv_content = f"id,name,description,type,latitude,longitude\n,{marker},imported via real CSV upload,POI,12.34,56.78\n"

    r = session.get(f"{base_url}/import-data/")
    record("fetch_import_form", r)
    csrf_match2 = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    assert csrf_match2, "expected a real csrfmiddlewaretoken field on the import form"

    r = session.post(
        f"{base_url}/import-data/",
        files={"importData": ("features.csv", csv_content, "text/csv")},
        data={"csrfmiddlewaretoken": csrf_match2.group(1)},
        headers={"Referer": f"{base_url}/import-data/"},
    )
    record("upload_real_csv", r, {"marker": marker})
    assert r.status_code == 200, r.text
    assert "Data Imported Successfully" in r.text, "expected the app's own real import-success message"

    r = session.get(f"{base_url}/")
    record("fetch_map_after_import", r)
    assert marker in r.text, "the imported feature does not appear on the real map -- import did not actually persist"
    assert "12.34" in r.text and "56.78" in r.text, "the imported feature's real coordinates do not appear on the map"

    evidence["imported_marker"] = marker
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real CSV upload imported and persisted feature {marker!r}; anonymous access rejected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
