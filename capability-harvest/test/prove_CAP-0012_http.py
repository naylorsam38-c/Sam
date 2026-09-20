#!/usr/bin/env python3
"""
prove_CAP-0012_http.py — real HTTP proof for CAP-0012 (rate item),
harvested from RyLaney/zinny-api.

No mocks. Against the real running composed app (build.py start --cap
CAP-0012, which auto-seeds real bundled title/survey data via its own
create_app()): posts a real rating for a real seeded title, confirms it
via GET, then posts a DIFFERENT rating for the same title/survey pair and
confirms the real `ON CONFLICT ... DO UPDATE` upsert changed the existing
row rather than creating a second one.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0012"


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

    r = requests.get(f"{base_url}/api/v1/titles/")
    record("fetch_seeded_titles", r)
    titles = r.json()
    assert titles, "expected the app's own real seeded titles, got none"
    title_id = titles[0]["id"]
    title_name = titles[0]["name"]

    r = requests.get(f"{base_url}/api/v1/surveys/")
    record("fetch_seeded_surveys", r)
    surveys = r.json()
    assert surveys, "expected the app's own real seeded surveys, got none"
    survey_id = surveys[0]["id"]

    r = requests.post(f"{base_url}/api/v1/ratings/", json={
        "title_id": title_id, "survey_id": survey_id, "ratings": {"emotion": 6, "authenticity": 7}, "comments": "first pass",
    })
    record("initial_rating", r, {"title_id": title_id, "survey_id": survey_id})
    assert r.status_code == 201, r.text

    r = requests.get(f"{base_url}/api/v1/ratings/", params={"title_id": title_id, "survey_id": survey_id})
    record("fetch_initial_rating", r)
    assert r.json()["ratings"] == {"emotion": 6, "authenticity": 7}
    assert r.json()["comments"] == "first pass"
    first_rating_id = r.json()["id"]

    # Upsert: same (title_id, survey_id) pair, different values.
    r = requests.post(f"{base_url}/api/v1/ratings/", json={
        "title_id": title_id, "survey_id": survey_id, "ratings": {"emotion": 9, "authenticity": 10}, "comments": "revised after rewatch",
    })
    record("updated_rating", r)
    assert r.status_code == 201, r.text

    r = requests.get(f"{base_url}/api/v1/ratings/", params={"title_id": title_id, "survey_id": survey_id})
    record("fetch_updated_rating", r)
    assert r.json()["ratings"] == {"emotion": 9, "authenticity": 10}, f"real upsert did not change the stored ratings: {r.json()}"
    assert r.json()["comments"] == "revised after rewatch"
    assert r.json()["id"] == first_rating_id, "upsert created a second row instead of updating the real existing one"

    evidence["title_rated"] = title_name
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Rated '{title_name}': (6,7) -> upserted to (9,10), same row id={first_rating_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
