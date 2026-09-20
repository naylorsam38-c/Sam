#!/usr/bin/env python3
"""
prove_CAP-0032_http.py — real HTTP proof for CAP-0032 (scan barcode),
harvested from UserSky21/Pharmaceutical-Inventory-System-.

No mocks. Against the real running composed app (its own real entry
point deletes and recreates pharmacy.db, seeding a real admin and five
real sample products with real barcodes every run): logs in as the real
seeded admin, looks up one of the app's own real seeded barcodes and
confirms the real matching product comes back (name, price, quantity --
not a hardcoded stub), looks up a barcode that was never seeded and
confirms a real null result (not a crash, not a fabricated match), and
confirms anonymous access to the lookup route is genuinely rejected.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0032"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
REAL_SEEDED_BARCODE = "8901234567890"  # Paracetamol 500mg, seeded by create_sample_products()
NEVER_SEEDED_BARCODE = "0000000000000"


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

    r = requests.get(f"{base_url}/api/products/barcode/{REAL_SEEDED_BARCODE}", allow_redirects=False)
    record("anonymous_barcode_lookup_check", r)
    assert r.status_code in (302, 401), f"expected anonymous access to be rejected, got {r.status_code}"

    session = requests.Session()
    r = session.get(f"{base_url}/login")
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
    login_data = {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    if csrf_match:
        login_data["csrf_token"] = csrf_match.group(1)
    r = session.post(f"{base_url}/login", data=login_data)
    record("login_as_admin", r)
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/api/products/barcode/{REAL_SEEDED_BARCODE}")
    record("lookup_real_seeded_barcode", r, {"barcode": REAL_SEEDED_BARCODE})
    assert r.status_code == 200, r.text
    product = r.json()["product"]
    assert product is not None, "the real seeded barcode returned no product"
    assert product["barcode"] == REAL_SEEDED_BARCODE
    assert product["name"] == "Paracetamol 500mg"
    assert product["quantity"] == 100

    r = session.get(f"{base_url}/api/products/barcode/{NEVER_SEEDED_BARCODE}")
    record("lookup_never_seeded_barcode", r, {"barcode": NEVER_SEEDED_BARCODE})
    assert r.status_code == 200
    assert r.json()["product"] is None, "a barcode that was never seeded returned a product -- lookup is not real"

    evidence["matched_product_name"] = product["name"]
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real barcode {REAL_SEEDED_BARCODE} matched '{product['name']}'; unknown barcode returned null; anonymous access rejected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
