#!/usr/bin/env python3
"""
prove_CAP-0005_http.py — real HTTP proof for CAP-0005 (send message),
harvested from jgoney/flask-messenger.

No mocks. Against the real running composed app (build.py start --cap
CAP-0005): posts a real message via the server-rendered POST / form and
confirms it comes back via the app's own real JSON REST endpoint
(GET /messages/api), proving the write actually persisted to the real
sqlite3-backed messages table rather than just rendering back the input.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0005"


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"

    stamp = int(datetime.now(timezone.utc).timestamp())
    message_text = f"Capability-harvest proof message {stamp}"
    sender = f"harvest-proof-{stamp}"
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    r = requests.post(f"{base_url}/", data={"message": message_text, "username": sender}, allow_redirects=True)
    record("send_message", r, {"message": message_text, "sender": sender})
    assert r.status_code == 200

    r = requests.get(f"{base_url}/messages/api")
    record("fetch_via_rest_api", r)
    assert r.status_code == 200
    messages = r.json()["messages"]
    matching = [m for m in messages if m.get("message") == message_text and m.get("sender") == sender]
    assert matching, f"sent message not found via the real REST API -- messages were: {messages}"

    evidence["messages_observed"] = messages
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real persisted message: {matching[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
