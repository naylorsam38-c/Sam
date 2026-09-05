"""The parts shelf's lifecycle: status is earned, bytes are pinned, freeze is
one-time, and every rule refuses rather than guesses.

These run against a throwaway shelf pointing at throwaway source files under
a temp root, so they can tamper with "qualified" code and watch the shelf
notice — something the real shelf must never have done to it in a test.
The real shelf's own state is checked by test_the_real_shelf_is_in_order.
"""

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "builder"))
sys.path.insert(0, str(ROOT / "packages" / "requirements-engine"))

import shelf as shelf_lib  # noqa: E402
import check_capability_bindings  # noqa: E402


BROWSER_PASS = [{"journey": "j", "result": "PASS", "browser_verified": True, "steps": []}]


@pytest.fixture
def tiny(tmp_path):
    """A one-part shelf whose part lives in tmp_path/src/part.py."""
    src = tmp_path / "src" / "part.py"
    src.parent.mkdir()
    src.write_text("def do():\n    return 1\n\n\ndef other():\n    return 2\n")
    shelf_path = tmp_path / "parts_shelf.json"
    shelf = {"schema_version": 1, "policy": {}, "parts": [{
        "part_id": "p", "kind": ["x"], "what_it_does": "x", "location": ["src/part.py::do"],
        "reused_from": "x", "evidence": "tests/x.py",
        "version": "1.0.0", "status": "TESTED", "qualified_revision": None,
        "provenance": {"read_from": ["Asana"], "implementation": "original", "licence": "all rights reserved"},
    }]}
    json.dump(shelf, open(shelf_path, "w"))
    return {"root": str(tmp_path), "shelf": str(shelf_path), "src": src}


def part(t):
    return shelf_lib.part_by_id(shelf_lib.load_shelf(t["shelf"]), "p")


def test_the_revision_follows_the_named_symbol_only(tiny):
    r0 = shelf_lib.source_revision(part(tiny), tiny["root"])
    tiny["src"].write_text("def do():\n    return 1\n\n\ndef other():\n    return 3\n")
    assert shelf_lib.source_revision(part(tiny), tiny["root"]) == r0, "a change outside the part must not move it"
    tiny["src"].write_text("def do():\n    return 11\n\n\ndef other():\n    return 3\n")
    assert shelf_lib.source_revision(part(tiny), tiny["root"]) != r0


def test_a_location_that_points_at_nothing_is_refused_not_hashed_around(tiny):
    p = part(tiny)
    p["location"] = ["src/part.py::nope"]
    with pytest.raises(shelf_lib.ShelfError, match="symbol not found"):
        shelf_lib.source_revision(p, tiny["root"])


def test_qualification_needs_the_current_bytes_and_a_browser_pass(tiny):
    rev = shelf_lib.source_revision(part(tiny), tiny["root"])
    with pytest.raises(shelf_lib.ShelfError, match="claims revision"):
        shelf_lib.record_qualification("p", "0000000000000000", BROWSER_PASS, "http://x", tiny["shelf"], tiny["root"])
    with pytest.raises(shelf_lib.ShelfError, match="no browser-verified PASS"):
        shelf_lib.record_qualification("p", rev, [{"result": "PASS", "browser_verified": False}], "http://x",
                                       tiny["shelf"], tiny["root"])
    assert part(tiny)["status"] == "TESTED", "a refused qualification changes nothing"
    receipt = shelf_lib.record_qualification("p", rev, BROWSER_PASS, "http://x", tiny["shelf"], tiny["root"])
    assert receipt["revision"] == rev
    assert part(tiny)["status"] == "PRODUCT_QUALIFIED"
    assert part(tiny)["qualified_revision"] == rev
    assert os.path.exists(shelf_lib.receipt_path("p", "1.0.0", tiny["shelf"]))
    assert shelf_lib.check_shelf(shelf_path=tiny["shelf"], root=tiny["root"]) == []


def test_changing_a_qualified_part_makes_the_shelf_say_so(tiny):
    rev = shelf_lib.source_revision(part(tiny), tiny["root"])
    shelf_lib.record_qualification("p", rev, BROWSER_PASS, "http://x", tiny["shelf"], tiny["root"])
    tiny["src"].write_text("def do():\n    return 'changed'\n\n\ndef other():\n    return 2\n")
    problems = shelf_lib.check_shelf(shelf_path=tiny["shelf"], root=tiny["root"])
    assert any("changed after it was qualified" in p for p in problems), problems


def test_freeze_is_one_time_and_only_for_qualified_current_bytes(tiny):
    with pytest.raises(shelf_lib.ShelfError, match="only PRODUCT_QUALIFIED"):
        shelf_lib.freeze("p", tiny["shelf"], tiny["root"])
    rev = shelf_lib.source_revision(part(tiny), tiny["root"])
    shelf_lib.record_qualification("p", rev, BROWSER_PASS, "http://x", tiny["shelf"], tiny["root"])
    frozen = shelf_lib.freeze("p", tiny["shelf"], tiny["root"])
    assert frozen["status"] == "FROZEN" and frozen["frozen_revision"] == rev
    with pytest.raises(shelf_lib.ShelfError, match="one-time"):
        shelf_lib.freeze("p", tiny["shelf"], tiny["root"])
    assert shelf_lib.check_shelf(shelf_path=tiny["shelf"], root=tiny["root"]) == []


def test_a_frozen_part_that_changes_is_caught_and_cannot_be_requalified_in_place(tiny):
    rev = shelf_lib.source_revision(part(tiny), tiny["root"])
    shelf_lib.record_qualification("p", rev, BROWSER_PASS, "http://x", tiny["shelf"], tiny["root"])
    shelf_lib.freeze("p", tiny["shelf"], tiny["root"])
    tiny["src"].write_text("def do():\n    return 'tampered'\n\n\ndef other():\n    return 2\n")
    problems = shelf_lib.check_shelf(shelf_path=tiny["shelf"], root=tiny["root"])
    assert any("frozen part changed without a version bump" in p for p in problems), problems
    new_rev = shelf_lib.source_revision(part(tiny), tiny["root"])
    with pytest.raises(shelf_lib.ShelfError, match="bump the version"):
        shelf_lib.record_qualification("p", new_rev, BROWSER_PASS, "http://x", tiny["shelf"], tiny["root"])
    # the sanctioned route: a new version starts at TESTED and earns its own receipt
    bumped = shelf_lib.bump("p", "1.1.0", tiny["shelf"])
    assert bumped["status"] == "TESTED" and bumped["qualified_revision"] is None and "frozen_revision" not in bumped
    assert not shelf_lib.meets(part(tiny))
    shelf_lib.record_qualification("p", new_rev, BROWSER_PASS, "http://x", tiny["shelf"], tiny["root"])
    assert part(tiny)["status"] == "PRODUCT_QUALIFIED"
    assert os.path.exists(shelf_lib.receipt_path("p", "1.0.0", tiny["shelf"])), "the old version's receipt is history, not deleted"
    assert os.path.exists(shelf_lib.receipt_path("p", "1.1.0", tiny["shelf"]))
    assert shelf_lib.check_shelf(shelf_path=tiny["shelf"], root=tiny["root"]) == []


def test_bump_refuses_a_version_that_does_not_go_forward(tiny):
    with pytest.raises(shelf_lib.ShelfError, match="greater than"):
        shelf_lib.bump("p", "1.0.0", tiny["shelf"])
    with pytest.raises(shelf_lib.ShelfError, match="MAJOR.MINOR.PATCH"):
        shelf_lib.bump("p", "2", tiny["shelf"])


def test_missing_provenance_or_status_is_a_problem_not_a_default(tiny):
    shelf = shelf_lib.load_shelf(tiny["shelf"])
    del shelf["parts"][0]["provenance"]["licence"]
    shelf["parts"][0]["status"] = "GOOD"
    problems = shelf_lib.check_shelf(shelf, tiny["shelf"], tiny["root"])
    assert any("licence" in p for p in problems) or any("status 'GOOD'" in p for p in problems), problems


def test_init_lifecycle_is_one_time_and_invents_no_provenance(tmp_path):
    shelf_path = tmp_path / "parts_shelf.json"
    json.dump({"parts": [{"part_id": "not_on_the_provenance_list", "location": [], "evidence": "x"}]}, open(shelf_path, "w"))
    with pytest.raises(shelf_lib.ShelfError, match="no provenance recorded"):
        shelf_lib.init_lifecycle(str(shelf_path))
    with pytest.raises(shelf_lib.ShelfError, match="already initialised"):
        shelf_lib.init_lifecycle()  # the real shelf


# ------------------------------------------------------------- the real shelf
def test_the_real_shelf_is_in_order():
    problems = shelf_lib.check_shelf()
    assert problems == [], "\n".join(problems)
    shelf = shelf_lib.load_shelf()
    for p in shelf["parts"]:
        assert p["status"] in shelf_lib.LIFECYCLE
        assert p["provenance"]["read_from"] and p["provenance"]["licence"]
        if p["status"] in ("PRODUCT_QUALIFIED", "FROZEN"):
            receipt = shelf_lib.read_receipt(p["part_id"], p["version"])
            assert receipt["revision"] == shelf_lib.source_revision(p)
            assert any(j["result"] == "PASS" and j["browser_verified"] for j in receipt["journeys"]), \
                f"{p['part_id']} is qualified without a browser-verified PASS in its receipt"


def test_no_part_is_qualified_by_anything_but_a_receipt():
    """The lifecycle rule in one assertion: the set of qualified parts equals
    the set of parts with a receipt at their current bytes."""
    shelf = shelf_lib.load_shelf()
    with_receipt = {p["part_id"] for p in shelf["parts"]
                    if (r := shelf_lib.read_receipt(p["part_id"], p["version"])) and r["revision"] == shelf_lib.source_revision(p)}
    qualified = {p["part_id"] for p in shelf["parts"] if p["status"] in ("PRODUCT_QUALIFIED", "FROZEN")}
    assert qualified == with_receipt


# ------------------------------------------------------------- pins + drift
BOUND = ROOT / "packages" / "requirements-engine" / "build"


def test_every_bound_spec_pins_the_exact_part_bytes():
    for spec_path in sorted(BOUND.glob("*/BOUND_SPEC.json")):
        spec = json.load(open(spec_path))
        shelf = {p["part_id"]: p for p in shelf_lib.load_shelf()["parts"]}
        seen = 0
        for scr in spec["build_model"]["screens_inventory"]:
            for pin in scr["part_bindings"]["pins"]:
                assert pin["revision"] == shelf_lib.source_revision(shelf[pin["part_id"]]), (spec_path, pin)
                seen += 1
        assert seen > 0, spec_path


def test_the_checker_reports_drift_when_the_shelf_moves_on(tmp_path):
    spec_path = BOUND / "pm-teamwork" / "BOUND_SPEC.json"
    spec = json.load(open(spec_path))
    scr = spec["build_model"]["screens_inventory"][0]
    scr["part_bindings"]["pins"][0]["revision"] = "0000000000000000"
    drifted = tmp_path / "BOUND_SPEC.json"
    json.dump(spec, open(drifted, "w"))
    text = check_capability_bindings.check_spec(str(drifted))
    assert "CLEAN" in text.split("QUALIFICATION CHECK")[0], "binding is still complete"
    assert f"DRIFT {scr['part_bindings']['pins'][0]['part_id']}" in text
    assert "QUALIFICATION NOT CLEAN" in text


def test_the_checker_separates_binding_from_qualification():
    text = check_capability_bindings.check_spec(str(BOUND / "command-desk" / "BOUND_SPEC.json"))
    binding, qualification = text.split("QUALIFICATION CHECK")
    assert "99/99 PASS" in binding and "\nCLEAN" in binding
    assert "parts qualified at their pinned revision" in qualification
    # unqualified parts are named, one per line, never folded into the binding verdict
    for line in qualification.splitlines():
        if line.startswith("UNQUALIFIED"):
            assert "status " in line


def test_seam_journeys_on_the_shelf_mirror_the_tester_exactly():
    sys.path.insert(0, str(ROOT / "packages" / "playwright-tester"))
    from seams import JOURNEYS
    shelf = shelf_lib.load_shelf()
    mirrored = {(j, p["part_id"]) for p in shelf["parts"] for j in p.get("seam_journeys", [])}
    declared = {(j, pid) for j, pids in JOURNEYS.items() for pid in pids}
    assert mirrored == declared
    for p in shelf["parts"]:
        if not p.get("seam_journeys"):
            assert p["status"] not in ("PRODUCT_QUALIFIED", "FROZEN"), \
                f"{p['part_id']} is qualified but no journey can have driven it"
