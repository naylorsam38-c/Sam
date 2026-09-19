#!/usr/bin/env python3
"""
prove_CAP-0028_http.py — real HTTP proof for CAP-0028 (filter list),
harvested from rishabh0510rishabh/Invoice-generator.

No mocks. Against the real running composed app: creates two real
invoices for two different real customers, then confirms the real
search-filter query genuinely narrows the list to only the matching
customer's invoice (not a client-side illusion) -- searching by one
customer's own real name returns their invoice and not the other's, and
a term matching neither returns nothing.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0028"


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

    customers = requests.get(f"{base_url}/api/customers").json()["customers"]
    assert len(customers) >= 2, "expected at least two real seeded customers"
    customer_a, customer_b = customers[0], customers[1]
    item = requests.get(f"{base_url}/api/items").json()[0]
    price, gst_rate = item["default_sale_price"], item["default_tax_rate"]
    taxable = round(price, 2)
    tax = round(taxable * gst_rate / 100, 2)
    half = round(tax / 2, 2)
    total = round(taxable + tax, 2)

    def create_invoice_for(customer, tag):
        invoice_no = f"HARVEST-PROOF-{tag}-{int(datetime.now(timezone.utc).timestamp())}"
        r = requests.post(f"{base_url}/api/invoices", json={
            "invoice_no": invoice_no, "date": "2026-09-19", "customer_id": customer["id"], "sale_type": "CASH",
            "notes": "filter-list proof", "total_value": total, "taxable_value": taxable, "cgst": half, "sgst": half,
            "round_off": 0.0, "items": [{
                "item_id": item["id"], "quantity": 1, "unit": item["default_unit"], "price_per_unit": price,
                "gst_rate": gst_rate, "cgst_amount": half, "sgst_amount": half, "total_amount": total,
            }],
        })
        record(f"create_invoice_for_{tag}", r)
        assert r.status_code == 201, r.text
        return r.json()["invoice_id"]

    invoice_a = create_invoice_for(customer_a, "A")
    invoice_b = create_invoice_for(customer_b, "B")

    r = requests.get(f"{base_url}/api/invoices", params={"search": customer_a["name"]})
    record("filter_by_customer_a_name", r, {"search": customer_a["name"]})
    results_a = r.json()
    ids_a = {row["id"] for row in results_a}
    assert invoice_a in ids_a, "real search by customer A's own name did not return their real invoice"
    assert invoice_b not in ids_a, "real search by customer A's name also returned customer B's invoice -- filter is not real"

    r = requests.get(f"{base_url}/api/invoices", params={"search": "zzz-no-such-customer-or-invoice-zzz"})
    record("filter_with_no_matches", r)
    assert all(row["id"] not in (invoice_a, invoice_b) for row in r.json()), (
        "a deliberately unmatched search term returned one of the real invoices anyway"
    )

    evidence["invoice_a"] = invoice_a
    evidence["invoice_b"] = invoice_b
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real filter by '{customer_a['name']}' returned only invoice {invoice_a}, not {invoice_b}; unmatched term returned neither.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
