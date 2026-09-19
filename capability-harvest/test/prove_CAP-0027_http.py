#!/usr/bin/env python3
"""
prove_CAP-0027_http.py — real HTTP proof for CAP-0027 (view record
detail), harvested from rishabh0510rishabh/Invoice-generator.

No mocks. Against the real running composed app: creates a real invoice
with a real customer and a real line item, then fetches its detail view
and confirms the real joined customer record and real joined item name
(via a real SQL JOIN, not just the raw foreign-key ids) both appear --
proving get_invoice_details() genuinely aggregates related real rows,
not just echoing the Invoices table row back. Also confirms a
never-existed id 404s cleanly.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0027"


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

    r = requests.get(f"{base_url}/api/invoices/999999999")
    record("fetch_nonexistent_invoice", r)
    assert r.status_code == 404

    customer = requests.get(f"{base_url}/api/customers").json()["customers"][0]
    item = requests.get(f"{base_url}/api/items").json()[0]
    price, gst_rate = item["default_sale_price"], item["default_tax_rate"]
    taxable = round(2 * price, 2)
    tax = round(taxable * gst_rate / 100, 2)
    half = round(tax / 2, 2)
    total = round(taxable + tax, 2)
    invoice_no = f"HARVEST-PROOF-{int(datetime.now(timezone.utc).timestamp())}"

    r = requests.post(f"{base_url}/api/invoices", json={
        "invoice_no": invoice_no, "date": "2026-09-19", "customer_id": customer["id"], "sale_type": "CASH",
        "notes": "view-detail proof", "total_value": total, "taxable_value": taxable, "cgst": half, "sgst": half,
        "round_off": 0.0, "items": [{
            "item_id": item["id"], "quantity": 2, "unit": item["default_unit"], "price_per_unit": price,
            "gst_rate": gst_rate, "cgst_amount": half, "sgst_amount": half, "total_amount": total,
        }],
    })
    record("create_invoice_for_detail_view", r)
    assert r.status_code == 201, r.text
    invoice_id = r.json()["invoice_id"]

    r = requests.get(f"{base_url}/api/invoices/{invoice_id}")
    record("fetch_invoice_detail", r)
    assert r.status_code == 200, r.text
    detail = r.json()

    assert detail["customer"]["id"] == customer["id"]
    assert detail["customer"]["name"] == customer["name"], "real joined customer name missing from detail view"
    assert detail["invoice"]["invoice_no"] == invoice_no
    assert len(detail["items"]) == 1
    assert detail["items"][0]["item_name"] == item["name"], (
        "real joined item name (from the Items table, not just the raw item_id) missing from detail view"
    )
    assert detail["items"][0]["quantity"] == 2

    evidence["invoice_id"] = invoice_id
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real invoice {invoice_id} detail view shows real joined customer ({customer['name']}) and item ({item['name']}) names.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
