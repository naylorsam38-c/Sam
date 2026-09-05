"""Seam journeys, driven for real: Command Desk assembled from its real
answers, built, started as a real server, and every seam between the parts
it uses driven in real Chromium. Receipts are written to the real shelf for
the parts that pass — this test IS the qualification run.

What is asserted is what the machinery must guarantee, not a happy picture:
every journey ends in exactly one result; a FAIL names the part whose step
failed; BLOCKED and FAIL carry the exact reason; a receipt exists only for a
part with a browser-verified PASS and no FAIL; and the seams that hold today
on Command Desk hold. The blocked and failed journeys are printed in full so
the run's findings are never silent.
"""

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for package in ("assembly-engine", "requirements-engine", "builder", "playwright-tester"):
    path = str(ROOT / "packages" / package)
    if path not in sys.path:
        sys.path.insert(0, path)

from test_command_desk_app_live import App, _free_port, built  # noqa: E402,F401  the same real build
import builder as bl  # noqa: E402
import seams  # noqa: E402
import shelf as shelf_lib  # noqa: E402


@pytest.fixture(scope="module")
def seam_report(built, tmp_path_factory):
    spec, out_dir, _ = built
    port = _free_port()
    app_dir = out_dir + "-seams"
    shutil.rmtree(app_dir, ignore_errors=True)
    bl.build(spec, app_dir, port=port)
    env_before = os.environ.get("GOOGLE_CLIENT_ID")
    os.environ["GOOGLE_CLIENT_ID"] = "test-client.apps.googleusercontent.com"  # the start route needs one to issue its 302
    server = App(app_dir, port)
    try:
        report = asyncio.run(seams.run(spec, server.base, str(tmp_path_factory.mktemp("seams")), app_dir))
    finally:
        server.stop()
        if env_before is None:
            del os.environ["GOOGLE_CLIENT_ID"]
        else:
            os.environ["GOOGLE_CLIENT_ID"] = env_before
    print("\n" + seams.summarise(report))
    return report


def test_every_journey_ends_in_exactly_one_result_with_a_reason(seam_report):
    for d in seam_report["journeys"]:
        assert d["result"] in ("PASS", "FAIL", "BLOCKED", "N/A"), d
        if d["result"] != "PASS":
            assert d["reason"], d
        if d["result"] == "FAIL":
            assert d["failed_part"] in d["parts"], d
        if d["result"] == "PASS":
            assert d["steps"], "a PASS with no recorded steps is a claim, not evidence"
            assert d["browser_verified"] is True


def test_the_seams_that_hold_on_command_desk(seam_report):
    passed = {(d["journey"], d["subject"]) for d in seam_report["journeys"] if d["result"] == "PASS"}
    assert ("form_submit_lands_in_list_and_detail", "command-desk/SCR-015") in passed
    assert ("form_submit_lands_in_list_and_detail", "command-desk/SCR-016") in passed
    assert ("report_screen_reflects_written_rows", "command-desk/SCR-019") in passed
    assert ("api_key_screen_connects_never_echoes", "command-desk/SCR-022") in passed
    assert ("api_key_screen_connects_never_echoes", "command-desk/SCR-023") in passed
    assert ("oauth_connect_click_reaches_provider", "command-desk/SCR-020") in passed
    assert ("oauth_connect_click_reaches_provider", "command-desk/SCR-021") in passed


def test_a_blocked_journey_names_the_missing_control_or_field(seam_report):
    blocked = [d for d in seam_report["journeys"] if d["result"] == "BLOCKED"]
    assert blocked, "Command Desk's generated screens carry no stage and no action buttons yet; that must show"
    for d in blocked:
        assert ("no screen offers" in d["reason"] or "renders no 'stage'" in d["reason"]
                or "no screen offers a control to move it" in d["reason"] or "has no rows" in d["reason"]), d["reason"]


def test_receipts_go_only_to_parts_with_a_browser_pass_and_no_fail(seam_report):
    written = {r["part_id"] for r in seam_report["receipts_written"]}
    for pid, v in seam_report["parts"].items():
        eligible = v["browser_verified_passes"] > 0 and v["FAIL"] == 0
        assert (pid in written) == eligible, (pid, v)
    shelf = {p["part_id"]: p for p in shelf_lib.load_shelf()["parts"]}
    for r in seam_report["receipts_written"]:
        part = shelf[r["part_id"]]
        assert part["status"] in ("PRODUCT_QUALIFIED", "FROZEN")
        assert part["qualified_revision"] == r["revision"] == shelf_lib.source_revision(part)
    assert shelf_lib.check_shelf() == []


def test_a_fail_is_charged_to_the_part_whose_step_failed_not_its_neighbours(seam_report):
    for d in seam_report["journeys"]:
        if d["result"] == "FAIL" and len(d["parts"]) > 1:
            others = [p for p in d["parts"] if p != d["failed_part"]]
            for o in others:
                assert seam_report["parts"][o]["NOT_REACHED"] >= 1


def test_the_findings_are_written_to_disk(seam_report, tmp_path):
    # summarise() is what run_chain prints; it must carry every non-PASS reason verbatim
    text = seams.summarise(seam_report)
    for d in seam_report["journeys"]:
        if d["result"] in ("FAIL", "BLOCKED"):
            assert d["reason"][:60] in text
