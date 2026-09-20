#!/usr/bin/env python3
"""
prove_CAP-0015_http.py — real HTTP proof for CAP-0015 (generate invoice),
harvested from rishabh0510rishabh/Invoice-generator.

No mocks. Against the real running composed app (build.py start --cap
CAP-0015, which re-applies the app's own real schema.sql and its own
seed_database.py -- real customers/items/invoices with real per-item GST
tax split, not data we invented): fetches one of the app's own real
generated invoices, requests its real PDF, and confirms the response is a
genuine PDF document (real %PDF- file signature, a plausible minimum
size, and the app's own real Content-Disposition filename derived from
the real invoice number) -- not a stub or an HTML error page.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0015"


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

    r = requests.get(f"{base_url}/api/invoices")
    record("fetch_seeded_invoices", r)
    invoices = r.json()
    assert invoices, "expected the app's own real seeded invoices, got none"
    invoice_id = invoices[0]["id"]
    invoice_no = invoices[0]["invoice_no"]

    r = requests.get(f"{base_url}/api/invoices/{invoice_id}")
    record("fetch_invoice_details", r, {"invoice_id": invoice_id})
    assert r.status_code == 200, r.text
    details = r.json()
    assert details["items"], "expected real persisted invoice line items, got none"

    r = requests.get(f"{base_url}/api/invoices/{invoice_id}/pdf")
    record("generate_invoice_pdf", r, {"invoice_id": invoice_id, "invoice_no": invoice_no})
    assert r.status_code == 200, (
        f"expected a real PDF response, got {r.status_code}: {r.text[:300]}"
    )
    assert r.headers.get("Content-Type") == "application/pdf", r.headers.get("Content-Type")
    assert r.content.startswith(b"%PDF-"), f"response is not a genuine PDF: starts with {r.content[:20]!r}"
    assert len(r.content) > 2000, f"PDF suspiciously small ({len(r.content)} bytes) to be a real rendered invoice"

    expected_filename_fragment = invoice_no.replace("/", "-")
    content_disposition = r.headers.get("Content-Disposition", "")
    assert expected_filename_fragment in content_disposition, (
        f"real invoice number {invoice_no!r} not reflected in Content-Disposition {content_disposition!r} "
        f"-- looks like a generic/stub PDF, not one genuinely built from this invoice's own data"
    )

    # A second, different theme must also render as a genuine, distinct PDF
    # -- proving the theme parameter genuinely selects a different real
    # template, not an ignored no-op.
    r_modern = requests.get(f"{base_url}/api/invoices/{invoice_id}/pdf", params={"theme": "modern"})
    record("generate_invoice_pdf_modern_theme", r_modern)
    assert r_modern.status_code == 200, r_modern.text
    assert r_modern.content.startswith(b"%PDF-")
    assert r_modern.content != r.content, "modern-theme PDF is byte-identical to the default theme -- theme parameter looks like a no-op"

    evidence["invoice_no"] = invoice_no
    evidence["default_pdf_bytes"] = len(r.content)
    evidence["modern_theme_pdf_bytes"] = len(r_modern.content)
    evidence["line_item_count"] = len(details["items"])
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real invoice {invoice_no}: {len(details['items'])} line items, "
          f"default PDF {len(r.content)} bytes, modern-theme PDF {len(r_modern.content)} bytes (distinct)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
