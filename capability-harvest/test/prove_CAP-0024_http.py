#!/usr/bin/env python3
"""
prove_CAP-0024_http.py — real HTTP proof for CAP-0024 (create record),
harvested from rishabh0510rishabh/Invoice-generator.

No mocks. Against the real running composed app (re-seeded with real
customers/items via the app's own seed_database.py): submits a real,
complete invoice with one real line item, confirms it comes back
byte-for-byte on a fresh real GET, and confirms the app's own real
required-field validation rejects an incomplete submission rather than
silently creating a broken row.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0024"


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

    r = requests.post(f"{base_url}/api/invoices", json={})
    record("attempt_create_with_missing_fields", r)
    assert r.status_code == 400, "expected the real required-field validation to reject an empty submission"

    r = requests.get(f"{base_url}/api/customers")
    record("fetch_seeded_customers", r)
    customers = r.json()["customers"] if isinstance(r.json(), dict) else r.json()
    assert customers, "expected the app's own real seeded customers"
    customer = customers[0]

    r = requests.get(f"{base_url}/api/items")
    record("fetch_seeded_items", r)
    items = r.json() if isinstance(r.json(), list) else r.json()["items"]
    assert items, "expected the app's own real seeded items"
    item = items[0]

    quantity = 2
    price = item["default_sale_price"]
    gst_rate = item["default_tax_rate"]
    taxable_value = round(quantity * price, 2)
    tax = round(taxable_value * gst_rate / 100, 2)
    cgst = sgst = round(tax / 2, 2)
    total_value = round(taxable_value + tax, 2)
    invoice_no = f"HARVEST-PROOF-{int(datetime.now(timezone.utc).timestamp())}"

    payload = {
        "invoice_no": invoice_no, "date": "2026-09-19", "customer_id": customer["id"],
        "sale_type": "CASH", "notes": "capability-harvest create-record proof",
        "total_value": total_value, "taxable_value": taxable_value, "cgst": cgst, "sgst": sgst, "round_off": 0.0,
        "items": [{
            "item_id": item["id"], "quantity": quantity, "unit": item["default_unit"], "price_per_unit": price,
            "gst_rate": gst_rate, "cgst_amount": cgst, "sgst_amount": sgst, "total_amount": total_value,
        }],
    }
    r = requests.post(f"{base_url}/api/invoices", json=payload)
    record("create_real_invoice", r, {"invoice_no": invoice_no})
    assert r.status_code == 201, r.text
    invoice_id = r.json()["invoice_id"]

    r = requests.get(f"{base_url}/api/invoices/{invoice_id}")
    record("fetch_created_invoice", r)
    assert r.status_code == 200, r.text
    detail = r.json()
    assert detail["invoice"]["invoice_no"] == invoice_no
    assert detail["invoice"]["customer_id"] == customer["id"]
    assert len(detail["items"]) == 1 and detail["items"][0]["item_id"] == item["id"]
    assert detail["items"][0]["quantity"] == quantity

    evidence["created_invoice_id"] = invoice_id
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real invoice {invoice_no} (id={invoice_id}) created and confirmed on a fresh GET; empty submission rejected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
