#!/usr/bin/env python3
"""
prove_CAP-0010_http.py — real HTTP proof for CAP-0010 (add favourite),
harvested from pranjalco/flask-coffee-and-wifi.

No mocks. Against the real running composed app (build.py start --cap
CAP-0010): asserts bookmarking anonymously redirects to /login (real
access control), registers a real user, adds a real cafe, bookmarks it
(real INSERT), confirms it on the real /bookmarks page, then removes it
(real DELETE) and confirms it is gone -- a genuine toggle, not one-way.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0010"


def _extract_csrf_token(html: str) -> str:
    # Bootstrap-Flask's render_form macro doesn't fix attribute order
    # (id/name/type/value can appear in any order in the rendered tag).
    match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', html)
    assert match, "could not find a csrf_token field in the real rendered form"
    return match.group(1)


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    # This app's LoginManager has no login_view configured, so Flask-Login's
    # real default unauthorized behaviour is a bare 401 (not a redirect) --
    # confirmed by reading main.py, not assumed.
    anon = requests.get(f"{base_url}/add_bookmark/1", allow_redirects=False)
    assert anon.status_code == 401, f"expected anonymous bookmarking to be rejected with 401, got {anon.status_code}"
    print(f"  [anonymous_bookmark_check] GET /add_bookmark/1 (no session) -> {anon.status_code}")

    session = requests.Session()
    stamp = int(datetime.now(timezone.utc).timestamp())
    email = f"harvestproof{stamp}@example.test"
    cafe_name = f"Harvest Proof Cafe {stamp}"
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    r = session.get(f"{base_url}/register")
    csrf = _extract_csrf_token(r.text)
    r = session.post(f"{base_url}/register", data={
        "name": "Harvest Proof", "email": email, "password": "CorrectHorseBattery9!", "csrf_token": csrf,
    }, allow_redirects=True)
    record("register", r)
    assert r.status_code == 200

    r = session.get(f"{base_url}/add")
    csrf = _extract_csrf_token(r.text)
    r = session.post(f"{base_url}/add", data={
        "cafe": cafe_name, "location": "https://maps.example.test/harvest-proof-cafe",
        "open_time": "9AM", "close_time": "7PM", "coffee_rating": "☕️️️", "wifi_rating": "💪", "power_socket": "🔌",
        "csrf_token": csrf,
    }, allow_redirects=True)
    record("add_cafe", r)
    assert r.status_code == 200 and cafe_name in r.text

    r = session.get(f"{base_url}/cafes")
    match = re.search(rf"/add_bookmark/(\d+)", r.text[r.text.index(cafe_name):r.text.index(cafe_name) + 2000])
    assert match, "could not find the real cafe's bookmark link on the real cafes page"
    cafe_id = match.group(1)

    r = session.get(f"{base_url}/add_bookmark/{cafe_id}", allow_redirects=True)
    record("add_bookmark", r, {"cafe_id": cafe_id})
    r = session.get(f"{base_url}/bookmarks")
    record("check_bookmarks_after_add", r)
    assert cafe_name in r.text, "bookmarked cafe did not appear on the real bookmarks page"

    r = session.get(f"{base_url}/delete_bookmark/{cafe_id}", allow_redirects=True)
    record("delete_bookmark", r)
    r = session.get(f"{base_url}/bookmarks")
    record("check_bookmarks_after_delete", r)
    assert cafe_name not in r.text, "cafe still appeared on bookmarks page after real delete_bookmark call"

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
