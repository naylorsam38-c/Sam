#!/usr/bin/env python3
"""
prove_CAP-0003_http.py — real HTTP proof for CAP-0003 (search records),
harvested from makona-OG/hostelFix.

No mocks. Against the real running composed app (build.py start --cap
CAP-0003, which runs the app's OWN init_db.py + dummy_data.py to get real
seed data): queries GET /search with a real substring of a real seeded
hostel name and confirms it comes back, then queries with a nonsense
string and confirms the app's own real "No results found" branch fires --
proving the query genuinely reaches the database rather than always
returning the same page.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0003"


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

    # Positive case: search for a substring of the app's own real seed data
    # (dummy_data.py creates "Hostel A".."Hostel J" -- see setup_scripts in
    # discovery/discover_applications.py). "Hostel A" must be a genuine,
    # case-insensitive substring match (the route uses .ilike(f'%{q}%')).
    r = requests.get(f"{base_url}/search", params={"query": "hostel a"})
    record("search_positive", r, {"query": "hostel a"})
    assert r.status_code == 200
    assert "Hostel A" in r.text, "expected the real seeded 'Hostel A' record in the search results page"

    # Negative control: a query with no match must hit the app's own real
    # "no results" branch, proving the search genuinely queries the
    # database rather than unconditionally returning the same page.
    r = requests.get(f"{base_url}/search", params={"query": "NoSuchPlaceXYZ999"})
    record("search_negative", r, {"query": "NoSuchPlaceXYZ999"})
    assert r.status_code == 200
    assert "No results found" in r.text, "expected the app's own real 'No results found' message for a non-matching query"
    assert "Hostel A" not in r.text

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
