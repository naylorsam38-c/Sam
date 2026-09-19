#!/usr/bin/env python3
"""
prove_CAP-0007_http.py — real HTTP proof for CAP-0007 (generate report),
harvested from vedpatel-real-ai/Fintrack-Flask-CS50-Final-Project.

No mocks. Against the real running composed app (build.py start --cap
CAP-0007): logs into the app's own real one-click /demo workspace (freshly
reseeded with real expense/income data on every visit), fetches the real
CSRF token Flask-WTF requires, and POSTs to /generate_report for both
"pdf" and "excel" report types -- verifying each response is a genuine,
non-empty file of the right type (a real PDF signature / a real xlsx
zip signature), not an error page or an empty stub.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0007"


def _extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert match, "could not find a csrf_token field in the real rendered report form"
    return match.group(1)


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    session = requests.Session()
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    # Adversarial check first: the report route must genuinely require
    # login, not just happen to work because we always test it authenticated.
    anon = requests.get(f"{base_url}/generate_report", allow_redirects=False)
    record("anonymous_access_check", anon)
    assert anon.status_code in (302, 303), f"expected /generate_report to redirect anonymous requests, got {anon.status_code}"

    r = session.get(f"{base_url}/demo", allow_redirects=True)
    record("demo_login", r)
    assert r.status_code == 200

    r = session.get(f"{base_url}/generate_report")
    record("fetch_report_form", r)
    assert r.status_code == 200
    csrf_token = _extract_csrf_token(r.text)

    r = session.post(f"{base_url}/generate_report", data={
        "report_type": "pdf", "report_currency": "USD", "csrf_token": csrf_token,
    })
    record("generate_pdf", r, {"content_type": r.headers.get("Content-Type"), "content_length": len(r.content)})
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-", f"expected a real PDF file signature, got {r.content[:20]!r}"
    assert len(r.content) > 500, "PDF report suspiciously small for real expense data"

    r = session.post(f"{base_url}/generate_report", data={
        "report_type": "excel", "report_currency": "USD", "csrf_token": csrf_token,
    })
    record("generate_excel", r, {"content_type": r.headers.get("Content-Type"), "content_length": len(r.content)})
    assert r.status_code == 200
    # .xlsx is a real zip archive; PK\x03\x04 is the real zip local-file-header signature.
    assert r.content[:4] == b"PK\x03\x04", f"expected a real xlsx (zip) file signature, got {r.content[:20]!r}"
    assert len(r.content) > 1000, "Excel report suspiciously small for real expense data"

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
