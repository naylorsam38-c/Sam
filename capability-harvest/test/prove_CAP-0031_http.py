#!/usr/bin/env python3
"""
prove_CAP-0031_http.py — real HTTP proof for CAP-0031 (paginate list),
harvested from MadGotten/Social-Life.

No mocks. Against the real running composed app (re-seeded with one
real, already-confirmed user via the app's own real User model/password
setter, since this app's own account-creation path always requires real
email confirmation): logs in, creates six real posts through the app's
own real /create_post route, then confirms index()'s real
Flask-SQLAlchemy .paginate() call genuinely splits them -- exactly five
(ROWS_PER_PAGE) on page 1, the remaining one on page 2, and none left on
page 3 -- a real LIMIT+OFFSET split, not a client-side illusion.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0031"
EMAIL = "harvestproof@example.com"  # seeded, already-confirmed account
PASSWORD = "HarvestProof123!"
ROWS_PER_PAGE = 5


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

    session = requests.Session()
    r = session.get(f"{base_url}/login")
    record("fetch_login_form", r)
    csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)

    r = session.post(f"{base_url}/login", data={"email": EMAIL, "password": PASSWORD, "csrf_token": csrf_token})
    record("login", r)
    assert r.status_code == 200 and r.url.rstrip("/") == base_url, f"real login did not reach the real feed: {r.url}"

    marker = f"harvest-proof-{int(datetime.now(timezone.utc).timestamp())}"
    num_posts = ROWS_PER_PAGE + 1
    for i in range(num_posts):
        r = session.get(f"{base_url}/create_post")
        csrf_token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', r.text).group(1)
        r = session.post(f"{base_url}/create_post", data={"text": f"{marker} post {i}", "csrf_token": csrf_token})
        record(f"create_real_post_{i}", r)
        assert r.status_code == 200, r.text

    r = session.get(f"{base_url}/", params={"page": 1})
    record("fetch_page_1", r)
    count_page1 = r.text.count(marker)

    r = session.get(f"{base_url}/", params={"page": 2})
    record("fetch_page_2", r)
    count_page2 = r.text.count(marker)

    r = session.get(f"{base_url}/", params={"page": 3})
    record("fetch_page_3", r)
    count_page3 = r.text.count(marker)

    assert count_page1 == ROWS_PER_PAGE, (
        f"expected exactly {ROWS_PER_PAGE} real posts on page 1 (the real per_page limit), got {count_page1}"
    )
    assert count_page2 == num_posts - ROWS_PER_PAGE, (
        f"expected exactly {num_posts - ROWS_PER_PAGE} real post(s) on page 2, got {count_page2}"
    )
    assert count_page3 == 0, f"expected no real posts on page 3, got {count_page3} -- pagination is not real"

    evidence["posts_created"] = num_posts
    evidence["page1_count"] = count_page1
    evidence["page2_count"] = count_page2
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real {num_posts} posts split by real pagination: page1={count_page1}, page2={count_page2}, page3={count_page3}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
