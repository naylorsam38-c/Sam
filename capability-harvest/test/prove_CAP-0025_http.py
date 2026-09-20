#!/usr/bin/env python3
"""
prove_CAP-0025_http.py — real HTTP proof for CAP-0025 (edit record),
harvested from rishabh0510rishabh/Invoice-generator.

No mocks. Against the real running composed app: creates a real invoice
with one real line item, then PUTs a genuine edit that both changes the
invoice's own fields (notes) and replaces its line items (a different
quantity), then confirms both changes are reflected on a fresh real GET
-- proving update_invoice() genuinely rewrites persisted state within a
real transaction, not silently ignoring the new data.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0025"


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

    customer = requests.get(f"{base_url}/api/customers").json()["customers"][0]
    item = requests.get(f"{base_url}/api/items").json()[0]

    def line_item(qty):
        price = item["default_sale_price"]
        gst_rate = item["default_tax_rate"]
        taxable = round(qty * price, 2)
        tax = round(taxable * gst_rate / 100, 2)
        half = round(tax / 2, 2)
        total = round(taxable + tax, 2)
        return taxable, half, total, {
            "item_id": item["id"], "quantity": qty, "unit": item["default_unit"], "price_per_unit": price,
            "gst_rate": gst_rate, "cgst_amount": half, "sgst_amount": half, "total_amount": total,
        }

    invoice_no = f"HARVEST-PROOF-{int(datetime.now(timezone.utc).timestamp())}"
    taxable, half, total, item_payload = line_item(1)
    create_payload = {
        "invoice_no": invoice_no, "date": "2026-09-19", "customer_id": customer["id"],
        "sale_type": "CASH", "notes": "original notes", "total_value": total, "taxable_value": taxable,
        "cgst": half, "sgst": half, "round_off": 0.0, "items": [item_payload],
    }
    r = requests.post(f"{base_url}/api/invoices", json=create_payload)
    record("create_invoice_to_edit", r)
    assert r.status_code == 201, r.text
    invoice_id = r.json()["invoice_id"]

    taxable2, half2, total2, item_payload2 = line_item(4)
    edit_payload = dict(create_payload)
    edit_payload.update({
        "notes": "edited by harvest proof", "total_value": total2, "taxable_value": taxable2,
        "cgst": half2, "sgst": half2, "items": [item_payload2],
    })
    r = requests.put(f"{base_url}/api/invoices/{invoice_id}", json=edit_payload)
    record("edit_invoice", r)
    assert r.status_code == 200, r.text

    r = requests.get(f"{base_url}/api/invoices/{invoice_id}")
    record("fetch_after_edit", r)
    detail = r.json()
    assert detail["invoice"]["notes"] == "edited by harvest proof", "edited notes did not persist"
    assert len(detail["items"]) == 1, "expected exactly one item after edit, not old items appended to new ones"
    assert detail["items"][0]["quantity"] == 4, "edited quantity did not persist"

    evidence["invoice_id"] = invoice_id
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real invoice {invoice_id} edited: notes and line items both genuinely replaced, not appended.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
