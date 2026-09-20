#!/usr/bin/env python3
"""
prove_CAP-0006_http.py — real HTTP proof for CAP-0006 (write review),
harvested from ichi-saki/Recipe_app.

No mocks. Against the real running composed app (build.py start --cap
CAP-0006): asserts the review route genuinely requires login (real access
control, checked adversarially), then signs up a real user, logs in, and
posts a real comment on one of the app's own real seeded recipes
(database/recipes.db, committed by the app's author via insert_data.py) --
confirming the comment appears on the real rendered recipe page afterward.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0006"
RECIPE_ID = 1  # "Classic Chocolate Chip Cookies" -- real seeded fixture data


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

    # Adversarial check first: posting a comment anonymously must redirect
    # to login, not silently succeed.
    anon = requests.post(f"{base_url}/recipe/{RECIPE_ID}/comment", data={"comment_text": "should not persist"}, allow_redirects=False)
    record("anonymous_comment_check", anon)
    assert anon.status_code == 302 and "/login" in anon.headers.get("Location", ""), \
        f"expected an anonymous comment POST to redirect to /login, got {anon.status_code} {anon.headers.get('Location')}"

    session = requests.Session()
    stamp = int(datetime.now(timezone.utc).timestamp())
    username = f"harvestproof{stamp}"
    comment_text = f"Capability-harvest proof review {stamp} -- these were fantastic!"

    r = session.post(f"{base_url}/signup", data={
        "username": username, "email": f"{username}@example.test",
        "password": "CorrectHorseBattery9!", "confirm_password": "CorrectHorseBattery9!",
    }, allow_redirects=True)
    record("signup", r)
    assert r.status_code == 200

    r = session.post(f"{base_url}/login", data={"username": username, "password": "CorrectHorseBattery9!"}, allow_redirects=True)
    record("login", r)
    assert r.status_code == 200

    r = session.post(f"{base_url}/recipe/{RECIPE_ID}/comment", data={"comment_text": comment_text}, allow_redirects=True)
    record("write_review", r)
    assert r.status_code == 200
    assert comment_text in r.text, "posted comment did not appear on the real recipe page after redirect"

    # Confirm the anonymous attempt from the top of this test never made it
    # into the real database, on the same real page.
    assert "should not persist" not in r.text

    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
