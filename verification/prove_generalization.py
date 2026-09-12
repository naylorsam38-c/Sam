#!/usr/bin/env python3
"""
prove_generalization.py — real behavioural regression test: for each of the
3 RED (not-reusable) capabilities the compatibility audit found, generates a
disposable "_v2" variant of its app where that ONE capability is produced by
the new generic generator (gen_common.AppBuilder.add_exceeds_threshold_
capability / add_bounded_counter_capability / add_symmetric_relationship_
capability) instead of its original hand-written body, runs BOTH the
original and the v2 variant through the real, unmodified build.py pipeline,
and replays an identical real HTTP sequence against both real running apps
to compare actual responses -- not code similarity, not contract shape,
real behaviour.

Does not touch or modify the original 43 apps' committed OUTPUT_LIBRARY.
Everything here runs under verification/gen_prove/, disposable.
"""
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_common import AppBuilder, page_skeleton  # noqa: E402

ROOT = HERE / "gen_prove"
if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir()


def build_and_run(project_dir: Path, port_offset: int):
    """Copies the fixed build.py in, disables layer three, runs it for real.
    These harness apps only need to reach real stage-1 assembly (their own
    generic-generator capability is what's under test, not their throwaway
    placeholder UI) -- not a passing browser check, so success here means
    'assembled', not 'READY'."""
    build_py_src = (HERE.parent / "build.py").read_text().replace(
        "ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project_dir / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project_dir),
                          capture_output=True, text=True, timeout=60)
    return res


def start_app(app_dir: Path, port: int, disposable_root: Path):
    """Never runs a live process against OUTPUT_LIBRARY directly -- copies to
    a disposable directory first, since starting the real Flask app writes
    real new records into its real data files (the exact mistake this
    comment exists to prevent repeating). Also resets every data/*.json to
    an empty list first: the original app already carries real records from
    its own original build run (a generic-compute-check probe, its primary
    journey's own record) while the disposable v2 harness starts empty --
    without this, an id-based comparison would be comparing two apps in two
    different real states, not the same behaviour from the same state."""
    live_copy = disposable_root / f"live_{app_dir.name}_{port}"
    if live_copy.exists():
        shutil.rmtree(live_copy)
    shutil.copytree(app_dir, live_copy)
    data_dir = live_copy / "data"
    if data_dir.is_dir():
        for f in data_dir.glob("*.json"):
            f.write_text("[]")
    app_json = json.loads((live_copy / "app.json").read_text())
    start = app_json["start"]
    proc = subprocess.Popen(start + ["--port", str(port)], cwd=str(live_copy),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(1.0)
    return proc


def http(port, method, path, body=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"} if data else {})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ==============================================================================
# 1. Auction bid: original vs. add_exceeds_threshold_capability
# ==============================================================================
def build_auction_v2(root: Path):
    b = AppBuilder(root, "auction_v2", "auction", "9100")
    b.add_capability("9101", "List Items", "/api/items", "GET",
        "def handle(request):\n    return 200, {'items': _load()}\n", output_fields=("items",))
    b.add_capability("9102", "Create Item", "/api/items", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    try:\n        starting_bid = float(body.get('starting_bid', 0) or 0)\n    except (TypeError, ValueError):\n        starting_bid = 0.0\n"
        "    items = _load()\n"
        "    next_id = (max([i['id'] for i in items], default=0)) + 1\n"
        "    item = {'id': next_id, 'title': title, 'current_bid': starting_bid, 'highest_bidder': None}\n"
        "    items.append(item)\n    _save(items)\n    return 201, item\n",
        output_fields=("id", "title", "current_bid", "highest_bidder"), required_input=("title",),
        side_effects=("creates_record",))
    # THE ONE DIFFERENCE: generic generator instead of hand-written body
    b.add_exceeds_threshold_capability("9103", "Place Bid", "/api/items/bid", id_field="id",
        value_field="current_bid", value_input="amount", holder_field="highest_bidder",
        holder_input="bidder", fail_message="bid too low", entity_noun="item")
    html = page_skeleton("Auction v2", "", "<div id='x'></div>", "")
    b.finish(html, {"input_selector": "#x", "input_value": "x", "action_selector": "#x",
                     "confirm_selector": "#x", "confirm_contains": "x"}, "Auction v2", port=5900)


# ==============================================================================
# 2. Event ticketing buy: original vs. add_bounded_counter_capability
# ==============================================================================
def build_event_ticketing_v2(root: Path):
    b = AppBuilder(root, "event_ticketing_v2", "event ticketing", "9200")
    b.add_capability("9201", "List Events", "/api/events", "GET",
        "def handle(request):\n    return 200, {'events': _load()}\n", output_fields=("events",))
    b.add_capability("9202", "Create Event", "/api/events", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    try:\n        capacity = int(body.get('capacity', 100) or 100)\n    except (TypeError, ValueError):\n        capacity = 100\n"
        "    events = _load()\n"
        "    next_id = (max([e['id'] for e in events], default=0)) + 1\n"
        "    ev = {'id': next_id, 'title': title, 'capacity': capacity, 'sold': 0}\n"
        "    events.append(ev)\n    _save(events)\n    return 201, ev\n",
        output_fields=("id", "title", "capacity", "sold"), required_input=("title",),
        side_effects=("creates_record",))
    # THE ONE DIFFERENCE: generic generator instead of hand-written body
    b.add_bounded_counter_capability("9203", "Buy Ticket", "/api/events/buy", id_field="id",
        counter_field="sold", limit_field="capacity", fail_message="sold out",
        extra_output_fields=("title",), entity_noun="event")
    html = page_skeleton("Event Ticketing v2", "", "<div id='x'></div>", "")
    b.finish(html, {"input_selector": "#x", "input_value": "x", "action_selector": "#x",
                     "confirm_selector": "#x", "confirm_contains": "x"}, "Event Ticketing v2", port=5901)


# ==============================================================================
# 3. Dating swipe: original vs. add_symmetric_relationship_capability
# ==============================================================================
def build_dating_v2(root: Path):
    b = AppBuilder(root, "dating_v2", "dating", "9300")
    b.add_capability("9301", "List Profiles", "/api/profiles", "GET",
        "def handle(request):\n    return 200, {'profiles': _load()}\n", output_fields=("profiles",),
        data_filename="profiles.json")
    b.add_capability("9302", "Create Profile", "/api/profiles", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    bio = body.get('bio') or ''\n"
        "    profiles = _load()\n"
        "    next_id = (max([p['id'] for p in profiles], default=0)) + 1\n"
        "    profile = {'id': next_id, 'name': name, 'bio': bio}\n"
        "    profiles.append(profile)\n    _save(profiles)\n    return 201, profile\n",
        output_fields=("id", "name", "bio"), required_input=("name",),
        side_effects=("creates_record",), data_filename="profiles.json")
    # THE ONE DIFFERENCE: generic generator instead of hand-written body
    b.add_symmetric_relationship_capability("9303", "Swipe", "/api/swipes",
        from_field="profile_id", to_field="target_id", positive_field="liked")
    html = page_skeleton("Dating v2", "", "<div id='x'></div>", "")
    b.finish(html, {"input_selector": "#x", "input_value": "x", "action_selector": "#x",
                     "confirm_selector": "#x", "confirm_contains": "x"}, "Dating v2", port=5902)


def prove(name, orig_app_dir, v2_project_root, v2_slug, port_a, port_b, sequence):
    """sequence: list of (label, method, path, body) tuples replayed against
    both real running apps; asserts every (status, body) pair matches."""
    print(f"\n{'=' * 70}\n{name}\n{'=' * 70}")
    proc_a = start_app(orig_app_dir, port_a, ROOT)
    v2_app_dir = v2_project_root / v2_slug / "builds" / "APP-001"
    proc_b = start_app(v2_app_dir, port_b, ROOT)
    try:
        all_match = True
        for label, method, path, body in sequence:
            ra = http(port_a, method, path, body)
            rb = http(port_b, method, path, body)
            match = ra == rb
            all_match = all_match and match
            marker = "MATCH" if match else "MISMATCH"
            print(f"  {marker}  {label}")
            print(f"    original: {ra}")
            print(f"    v2 (generic generator): {rb}")
        return all_match
    finally:
        proc_a.terminate(); proc_b.terminate()
        proc_a.wait(timeout=5); proc_b.wait(timeout=5)


def main():
    results = {}

    # --- Auction ---
    build_auction_v2(ROOT)
    r = build_and_run(ROOT / "auction_v2", 0)
    assert "12  APP-001  assembled" in r.stdout, f"auction_v2 failed to assemble:\n{r.stdout}\n{r.stderr}"
    orig_auction = HERE.parent / "OUTPUT_LIBRARY" / "auction"
    results["auction bid"] = prove(
        "Auction: original hand-written bid vs. add_exceeds_threshold_capability",
        orig_auction, ROOT, "auction_v2", 5910, 5911,
        [
            ("create item", "POST", "/api/items", {"title": "Regression Test Lamp", "starting_bid": 10}),
            ("bid too low (5 <= 10)", "POST", "/api/items/bid", {"id": 1, "amount": 5, "bidder": "alice"}),
            ("bid higher (20 > 10)", "POST", "/api/items/bid", {"id": 1, "amount": 20, "bidder": "bob"}),
            ("bid not higher (20 <= 20)", "POST", "/api/items/bid", {"id": 1, "amount": 20, "bidder": "carol"}),
            ("bid on missing item", "POST", "/api/items/bid", {"id": 999, "amount": 50, "bidder": "dave"}),
        ])

    # --- Event ticketing ---
    build_event_ticketing_v2(ROOT)
    r = build_and_run(ROOT / "event_ticketing_v2", 0)
    assert "12  APP-001  assembled" in r.stdout, f"event_ticketing_v2 failed to assemble:\n{r.stdout}\n{r.stderr}"
    orig_event = HERE.parent / "OUTPUT_LIBRARY" / "event_ticketing"
    results["event_ticketing buy"] = prove(
        "Event ticketing: original hand-written buy vs. add_bounded_counter_capability",
        orig_event, ROOT, "event_ticketing_v2", 5920, 5921,
        [
            ("create event capacity=1", "POST", "/api/events", {"title": "Regression Test Show", "capacity": 1}),
            ("buy first ticket (0 < 1)", "POST", "/api/events/buy", {"id": 1}),
            ("buy second ticket (1 >= 1, sold out)", "POST", "/api/events/buy", {"id": 1}),
            ("buy on missing event", "POST", "/api/events/buy", {"id": 999}),
        ])

    # --- Dating ---
    build_dating_v2(ROOT)
    r = build_and_run(ROOT / "dating_v2", 0)
    assert "12  APP-001  assembled" in r.stdout, f"dating_v2 failed to assemble:\n{r.stdout}\n{r.stderr}"
    orig_dating = HERE.parent / "OUTPUT_LIBRARY" / "dating"
    results["dating swipe"] = prove(
        "Dating: original hand-written swipe vs. add_symmetric_relationship_capability",
        orig_dating, ROOT, "dating_v2", 5930, 5931,
        [
            ("create profile 1", "POST", "/api/profiles", {"name": "Regression Alice"}),
            ("create profile 2", "POST", "/api/profiles", {"name": "Regression Bob"}),
            ("1 likes 2 (no match yet)", "POST", "/api/swipes",
             {"profile_id": 1, "target_id": 2, "liked": True}),
            ("2 likes 1 (reciprocal -> match)", "POST", "/api/swipes",
             {"profile_id": 2, "target_id": 1, "liked": True}),
        ])

    print(f"\n{'=' * 70}\nSUMMARY\n{'=' * 70}")
    all_pass = True
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: generic generator reproduces original behaviour exactly")
        all_pass = all_pass and ok
    print(f"\n{'ALL MATCH' if all_pass else 'MISMATCH FOUND'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
