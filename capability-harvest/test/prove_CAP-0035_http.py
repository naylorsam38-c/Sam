#!/usr/bin/env python3
"""
prove_CAP-0035_http.py — real HTTP proof for CAP-0035 (show map),
harvested from moustafa-shaaban/Django_and_Folium.

No mocks. Against the real running composed app (a real PostgreSQL
database, migrated via the app's own real Django migrations and seeded
with one real user and two real Feature rows at two genuinely different
coordinates via the app's own real ORM models): fetches the real index
page and confirms both real features' exact names and lat/lng values
appear in the rendered Folium map -- not a static demo map, and not a
single hardcoded marker, since both a first and a genuinely different
second feature must show up distinctly. Also confirms a feature that was
never seeded does NOT appear, so the map is provably driven by what's
actually in the database rather than always rendering the same content.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0035"
FEATURE_1_NAME = "Harvest Landmark"
FEATURE_1_LAT = "47.6062"
FEATURE_1_LNG = "-122.3321"
FEATURE_2_NAME = "Second Harvest Marker"
FEATURE_2_LAT = "40.7128"
FEATURE_2_LNG = "-74.006"
NEVER_SEEDED_NAME = "Definitely Not A Real Seeded Feature"


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

    r = requests.get(f"{base_url}/")
    record("fetch_map_page", r)
    assert r.status_code == 200, r.text
    body = r.text

    for label, value in [
        ("feature_1_name", FEATURE_1_NAME), ("feature_1_lat", FEATURE_1_LAT), ("feature_1_lng", FEATURE_1_LNG),
        ("feature_2_name", FEATURE_2_NAME), ("feature_2_lat", FEATURE_2_LAT), ("feature_2_lng", FEATURE_2_LNG),
    ]:
        assert value in body, f"expected real seeded {label}={value!r} in the rendered map page"

    assert NEVER_SEEDED_NAME not in body, "a feature that was never seeded appeared on the map -- not database-driven"

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real map rendered both real seeded features ({FEATURE_1_NAME!r}, {FEATURE_2_NAME!r}) with their real coordinates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
