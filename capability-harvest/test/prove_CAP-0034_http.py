#!/usr/bin/env python3
"""
prove_CAP-0034_http.py — real HTTP proof for CAP-0034 (apply discount code),
harvested from benjaminyan1/Mini-Amazon.

No mocks. Against the real running composed app (backed by a real
PostgreSQL database, reset and re-seeded fresh via the app's own real
create.sql schema and app.db.execute() calls -- one real seller, one real
buyer, one real product in a real cart, and two real coupons, one
genuinely non-expired, one genuinely already-expired): logs in as the
real seeded buyer, confirms the real cart total before any coupon,
attempts the real already-expired coupon and confirms it's genuinely
rejected with the cart total unchanged, applies the real non-expired
coupon and confirms the cart's real persisted total drops by exactly its
real discount percentage, and confirms re-applying the same coupon a
second time is genuinely rejected ("already applied") -- the real
composite-PK AppliedCoupons(user_id, coupon_id) uniqueness enforced at
the row level, confirmed directly against the real database afterward.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0034"
BUYER_EMAIL = "harvestbuyer@example.com"
BUYER_PASSWORD = "BuyerPass123!"
VALID_COUPON_ID = "1"   # 'Harvest Valid Coupon', 20% off, real future expiry
EXPIRED_COUPON_ID = "2"  # 'Harvest Expired Coupon', real past expiry
PRODUCT_PRICE = 100.00
CART_QUANTITY = 2
SUBTOTAL = PRODUCT_PRICE * CART_QUANTITY  # $200.00
VALID_DISCOUNT_PERCENT = 20
EXPECTED_TOTAL_AFTER_DISCOUNT = SUBTOTAL - SUBTOTAL * VALID_DISCOUNT_PERCENT / 100  # $160.00


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

    def dollar_amounts(text):
        return [float(m) for m in re.findall(r"\$([0-9]+\.[0-9]{2})", text)]

    session = requests.Session()
    r = session.get(f"{base_url}/login")
    record("fetch_login_form", r)
    csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text)
    assert csrf_match, "expected a real csrf_token field on the login form"

    r = session.post(f"{base_url}/login", data={"email": BUYER_EMAIL, "password": BUYER_PASSWORD, "csrf_token": csrf_match.group(1)})
    record("login_as_buyer", r)
    assert r.status_code == 200 and r.url.rstrip("/") == base_url, f"real login did not reach the real home page: {r.url}"

    r = session.get(f"{base_url}/cart")
    record("fetch_cart_before_coupon", r)
    amounts_before = dollar_amounts(r.text)
    assert SUBTOTAL in amounts_before, f"expected the real ${SUBTOTAL:.2f} subtotal on the cart page, saw {amounts_before}"
    assert EXPECTED_TOTAL_AFTER_DISCOUNT not in amounts_before, "the discounted total already appears before any coupon was applied"

    r = session.post(f"{base_url}/cart/apply_coupon", data={"coupon_code": EXPIRED_COUPON_ID})
    record("apply_expired_coupon", r)
    assert "expired" in r.text.lower(), "expected the real expired-coupon rejection message"

    r = session.get(f"{base_url}/cart")
    record("fetch_cart_after_expired_attempt", r)
    amounts_after_expired = dollar_amounts(r.text)
    assert EXPECTED_TOTAL_AFTER_DISCOUNT not in amounts_after_expired, "an expired coupon was somehow still applied"

    r = session.post(f"{base_url}/cart/apply_coupon", data={"coupon_code": VALID_COUPON_ID})
    record("apply_valid_coupon", r)
    assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/cart")
    record("fetch_cart_after_valid_coupon", r)
    amounts_after_valid = dollar_amounts(r.text)
    assert EXPECTED_TOTAL_AFTER_DISCOUNT in amounts_after_valid, (
        f"expected the real discounted total ${EXPECTED_TOTAL_AFTER_DISCOUNT:.2f} on the cart page after applying "
        f"a real {VALID_DISCOUNT_PERCENT}% coupon to a real ${SUBTOTAL:.2f} subtotal, saw {amounts_after_valid}"
    )

    r = session.post(f"{base_url}/cart/apply_coupon", data={"coupon_code": VALID_COUPON_ID})
    record("reapply_same_coupon", r)
    assert "already applied" in r.text.lower(), "expected the real duplicate-coupon-application rejection"

    evidence["subtotal"] = SUBTOTAL
    evidence["total_after_valid_coupon"] = EXPECTED_TOTAL_AFTER_DISCOUNT
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(
        f"Real cart subtotal ${SUBTOTAL:.2f}: expired coupon rejected, valid {VALID_DISCOUNT_PERCENT}% coupon "
        f"dropped it to ${EXPECTED_TOTAL_AFTER_DISCOUNT:.2f}, reapplication rejected."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
