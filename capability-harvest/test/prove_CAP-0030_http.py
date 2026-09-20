#!/usr/bin/env python3
"""
prove_CAP-0030_http.py — real HTTP proof for CAP-0030 (place bid),
harvested from vamsishesamsetti/SmartBid.

No mocks. Against the real running composed app: registers two real
users (seller, bidder), creates a real auction, then confirms
place_bid()'s real server-side validation: a bid that doesn't clear the
current price by the real minimum increment is genuinely rejected (400,
with the real computed minimum in the message), a valid bid is genuinely
accepted (201) and the auction's real current_price updates, and
repeating that exact same amount afterward is rejected again since the
real price has moved -- not a bid that's accepted unconditionally.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0030"


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

    unique = int(datetime.now(timezone.utc).timestamp())
    seller_email, bidder_email = f"seller{unique}@example.com", f"bidder{unique}@example.com"

    r = requests.post(f"{base_url}/api/auth/register", json={"username": f"seller{unique}", "email": seller_email, "password": "SellerPass123!"})
    record("register_seller", r)
    assert r.status_code == 201, r.text
    r = requests.post(f"{base_url}/api/auth/register", json={"username": f"bidder{unique}", "email": bidder_email, "password": "BidderPass123!"})
    record("register_bidder", r)
    assert r.status_code == 201, r.text

    r = requests.post(f"{base_url}/api/auth/login", json={"email": seller_email, "password": "SellerPass123!"})
    record("login_seller", r)
    seller_headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r = requests.post(f"{base_url}/api/auth/login", json={"email": bidder_email, "password": "BidderPass123!"})
    record("login_bidder", r)
    bidder_headers = {"Authorization": f"Bearer {r.json()['token']}"}

    end_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    r = requests.post(f"{base_url}/api/auctions", json={
        "title": "Harvest Proof Item", "description": "capability-harvest proof", "starting_price": 100,
        "min_increment": 5, "end_time": end_time,
    }, headers=seller_headers)
    record("create_auction", r)
    assert r.status_code == 201, r.text
    auction_id = r.json()["auction"]["id"]

    r = requests.post(f"{base_url}/api/auctions/{auction_id}/bid", json={"amount": 100}, headers=bidder_headers)
    record("bid_not_enough", r)
    assert r.status_code == 400, "a bid equal to the current price (no real increment) was wrongly accepted"
    assert "105" in r.json()["error"], "real computed minimum bid not present in the rejection message"

    r = requests.post(f"{base_url}/api/auctions/{auction_id}/bid", json={"amount": 110}, headers=bidder_headers)
    record("bid_valid", r)
    assert r.status_code == 201, r.text
    assert r.json()["new_current_price"] == 110.0

    r = requests.post(f"{base_url}/api/auctions/{auction_id}/bid", json={"amount": 110}, headers=bidder_headers)
    record("bid_repeat_same_amount_now_invalid", r)
    assert r.status_code == 400, "repeating the exact same amount after the real price moved was wrongly accepted"

    r = requests.get(f"{base_url}/api/auctions/{auction_id}", headers=bidder_headers)
    record("fetch_auction_after_bids", r)
    assert r.json()["auction"]["current_price"] == 110.0, "real current_price did not persist the accepted bid"

    evidence["auction_id"] = auction_id
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real auction {auction_id}: bid below minimum rejected, valid bid accepted (price -> 110.0), repeat rejected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
