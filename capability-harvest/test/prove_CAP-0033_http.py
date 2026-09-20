#!/usr/bin/env python3
"""
prove_CAP-0033_http.py — real HTTP proof for CAP-0033 (close auction),
harvested from arpannookala12/BuyMe---Online-Auction-System.

No mocks. Against the real running composed app (seeded with one real
category/item, four real users, and one real auction via the app's own
real SQLAlchemy models): logs in two real bidders and places two real
bids via the app's own real POST /auction/<id>/bid route, confirms a
real bidder (non-admin, non-customer-rep) is genuinely rejected (403)
when attempting to end the auction, then logs in the seeded customer
rep and ends the auction via the app's own real POST /auction/<id>/end
route. Confirms the real committed row afterward -- both through the
rendered page (the real winner's username appears) and directly against
the real sqlite database (winner_id set to the real highest bidder's
id, is_active flipped to 0) -- proving the app's own real
determine_winner() reserve-price-checked logic actually ran, not that
the route merely returned 200.
"""

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0033"
SELLER = {"username": "harvestseller", "password": "SellerPass123!"}
BIDDER1 = {"username": "harvestbidder1", "password": "BidderPass123!"}
BIDDER2 = {"username": "harvestbidder2", "password": "BidderPass123!"}
REP = {"username": "harvestrep", "password": "RepPass123!"}
AUCTION_ID = 1
BIDDER1_AMOUNT = 12.0
BIDDER2_AMOUNT = 15.0  # the real highest bid -- must be the real winner


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

    def login(creds):
        s = requests.Session()
        r = s.post(f"{base_url}/auth/login", data={"username": creds["username"], "password": creds["password"]})
        record(f"login_{creds['username']}", r)
        assert r.status_code == 200 and r.url.rstrip("/") == base_url, f"real login for {creds['username']} did not reach the real home page: {r.url}"
        return s

    bidder1 = login(BIDDER1)
    bidder2 = login(BIDDER2)

    r = bidder1.post(f"{base_url}/auction/{AUCTION_ID}/bid", data={"bid_amount": str(BIDDER1_AMOUNT)})
    record("bidder1_places_real_bid", r, {"amount": BIDDER1_AMOUNT})
    assert r.status_code == 200, r.text

    r = bidder2.post(f"{base_url}/auction/{AUCTION_ID}/bid", data={"bid_amount": str(BIDDER2_AMOUNT)})
    record("bidder2_places_real_bid", r, {"amount": BIDDER2_AMOUNT})
    assert r.status_code == 200, r.text

    r = bidder1.post(f"{base_url}/auction/{AUCTION_ID}/end", allow_redirects=False)
    record("non_admin_bidder_attempts_end", r)
    assert r.status_code == 403, f"expected a real bidder to be rejected ending the auction, got {r.status_code}"

    rep = login(REP)
    r = rep.post(f"{base_url}/auction/{AUCTION_ID}/end")
    record("customer_rep_ends_real_auction", r)
    assert r.status_code == 200, r.text

    r = rep.get(f"{base_url}/auction/{AUCTION_ID}")
    record("fetch_ended_auction_page", r)
    assert BIDDER2["username"] in r.text, "the real highest bidder's username does not appear on the auction page"

    db_path = Path(manifest["db_path"])
    assert db_path.exists(), f"expected the real build sqlite database at {db_path}"

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT is_active, winner_id FROM auctions WHERE id = ?", (AUCTION_ID,))
    row = cur.fetchone()
    cur.execute("SELECT id, username FROM users WHERE username = ?", (BIDDER2["username"],))
    bidder2_row = cur.fetchone()
    conn.close()

    assert row is not None, "the real auction row is missing after ending it"
    assert row["is_active"] == 0, f"expected the real auction to be flipped inactive, is_active={row['is_active']}"
    assert row["winner_id"] == bidder2_row["id"], (
        f"expected winner_id to be the real highest bidder's id ({bidder2_row['id']}), got {row['winner_id']}"
    )

    evidence["winner_id"] = row["winner_id"]
    evidence["is_active_after_end"] = row["is_active"]
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real auction closed: winner_id={row['winner_id']} (bidder2), is_active={row['is_active']}; non-admin rejected with 403.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
