#!/usr/bin/env python3
"""
prove_CAP-0002_http.py — real HTTP proof for CAP-0002 (manage inventory),
harvested from Antoh254/Inventory-Tracker.

No mocks. Against the real running composed app (build.py start --cap
CAP-0002): adds a real product via POST /add, sells one unit via
POST /update/<id> (action=sell), restocks two units (action=restock), and
parses the real rendered HTML of / after each step to confirm the real
quantity in the real SQLite-backed products table actually changed.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0002"


def _extract_row(html: str, product_name: str):
    # Real table row, from templates/index.html:
    #   <tr><td>#{{ item[0] }}</td><td ...>{{ item[1] }}</td>
    #       <td><span class="qty-display ...">{{ item[2] }}</span> ...
    pattern = (
        rf"<td>#(\d+)</td>\s*<td[^>]*>{re.escape(product_name)}</td>\s*"
        rf'<td>\s*<span class="qty-display[^"]*">\s*(\d+)\s*</span>'
    )
    match = re.search(pattern, html, re.DOTALL)
    assert match, f"could not find a row for {product_name!r} in the real page HTML"
    return int(match.group(1)), int(match.group(2))  # (id, quantity)


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    session = requests.Session()
    stamp = int(datetime.now(timezone.utc).timestamp())
    product_name = f"HarvestProofWidget{stamp}"
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    r = session.post(f"{base_url}/add", data={"name": product_name, "quantity": "10", "reorder_level": "3"}, allow_redirects=True)
    record("add_product", r)
    assert r.status_code == 200
    product_id, quantity_after_add = _extract_row(r.text, product_name)
    assert quantity_after_add == 10, f"expected quantity 10 after add, got {quantity_after_add}"

    r = session.post(f"{base_url}/update/{product_id}", data={"action": "sell"}, allow_redirects=True)
    record("sell_one", r, {"product_id": product_id})
    _, quantity_after_sell = _extract_row(r.text, product_name)
    assert quantity_after_sell == 9, f"expected quantity 9 after selling one, got {quantity_after_sell}"

    r = session.post(f"{base_url}/update/{product_id}", data={"action": "restock"}, allow_redirects=True)
    r = session.post(f"{base_url}/update/{product_id}", data={"action": "restock"}, allow_redirects=True)
    record("restock_two", r, {"product_id": product_id})
    _, quantity_after_restock = _extract_row(r.text, product_name)
    assert quantity_after_restock == 11, f"expected quantity 11 after restocking two, got {quantity_after_restock}"

    evidence["quantities_observed"] = {
        "after_add": quantity_after_add, "after_sell": quantity_after_sell, "after_restock": quantity_after_restock,
    }
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real quantity trail: 10 (added) -> {quantity_after_sell} (sold one) -> {quantity_after_restock} (restocked two)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
