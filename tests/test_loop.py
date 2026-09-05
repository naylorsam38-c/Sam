"""Fix-and-retest loop + Definition of Done gate (packages/loop/run_chain.py).

Every cycle here runs the real Builder, starts a real server, runs the real
Playwright tester in both modes, and runs the real defect reporter — the
same components the other test files already prove correct individually.
This file tests the *loop's own* control flow: does a clean run report
`done: True`; does a real, persistent defect get reported and correctly
stop the loop instead of retrying forever; does `_same_defects` do its job.

The one place this deliberately breaks something on purpose: a temporary,
clearly-labelled copy of builder.py with one line changed, to prove the
loop detects a real defect and does not paper over it by looping past it.
Same pattern this whole repository's own tests already use (validate_graph.py
and check_template.py both break a real, working thing on purpose to prove
their checkers catch it) — not a stand-in for a real product's answers.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LOOP = ROOT / "packages" / "loop"
BUILDER_DIR = ROOT / "packages" / "builder"

sys.path.insert(0, str(LOOP))
import run_chain as rc  # noqa: E402


@pytest.fixture
def command_desk_spec_path(tmp_path):
    good_spec = (ROOT / "packages" / "specgate" / "examples" / "good.spec.yaml").read_text()
    assert "status: approved" in good_spec
    spec = {
        "spec_id": "SPEC-014-LOOPTEST", "title": "Linked Services (loop test)",
        "graph_version": "3.0", "source_template": None, "numbered_fields": [],
        "build_model": {
            "records": {}, "roles": {}, "super_role": None, "workflows": {},
            "notifications": {}, "reports": {}, "forms": {},
            "integrations": {"Gmail": {
                "purpose": "user consents; we exchange the code for tokens",
                "sends": "OAuth authorization request", "receives": "access token + refresh token",
                "timing": {"kind": "manual", "who": ["Sam"]},
                "connection_scope": "one connection for Sam's own account",
                "on_unavailable": {"message": "Cannot reach server"},
            }},
            "auth": {}, "screens_inventory": [{"id": "SCR-001", "kind": "integration_status", "integration": "Gmail"}],
            "navigation": ["SCR-001"], "landing_per_role": {},
            "actions_inventory": [{"id": "ACT-001", "kind": "connect", "integration": "Gmail", "roles": ["Sam"]}],
            "recurring_ops": [], "qa_generated_tests": [],
            "brand": {"app_name": "Command Desk", "assets": {"mode": "design_for_me"}},
        },
    }
    p = tmp_path / "SPEC.json"
    p.write_text(json.dumps(spec))
    return p


def test_same_defects_compares_by_id_kind_and_observed():
    a = [{"id": "DEFECT-SCR-001-UNAVAILABLE-STATE", "kind": "unavailable_state_wrong", "observed": "wrong text"}]
    b = [{"id": "DEFECT-SCR-001-UNAVAILABLE-STATE", "kind": "unavailable_state_wrong", "observed": "wrong text"}]
    c = [{"id": "DEFECT-SCR-001-UNAVAILABLE-STATE", "kind": "unavailable_state_wrong", "observed": "different text"}]
    assert rc._same_defects(a, b) is True
    assert rc._same_defects(a, c) is False
    assert rc._same_defects([], []) is True
    assert rc._same_defects(a, []) is False


def test_clean_spec_reaches_done_in_one_cycle(command_desk_spec_path, tmp_path):
    result = rc.run_to_done(str(command_desk_spec_path), str(tmp_path / "out"), port=8993, iterations=3,
                             oauth_env={"GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com"})
    assert result["done"] is True
    assert result["cycles_run"] == 1
    assert result["history"][0]["defects"] == []


def test_cli_exit_codes_and_definition_of_done(command_desk_spec_path, tmp_path):
    out = tmp_path / "cli_out"
    r = subprocess.run(
        [sys.executable, str(LOOP / "run_chain.py"), str(command_desk_spec_path),
         "-o", str(out), "--port", "8994", "--oauth-client-id", "test-client.apps.googleusercontent.com"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "DONE in 1 cycle" in r.stdout
    result = json.loads((out / "RUN_RESULT.json").read_text())
    assert result["done"] is True


@pytest.fixture
def builder_with_a_real_bug(tmp_path):
    """A real, working copy of builder.py with one deliberate, labelled break:
    the integration screen ignores the spec's real on_unavailable message.
    Points run_chain.BUILDER at it for the duration of one test, restoring
    the real path afterwards."""
    broken_dir = tmp_path / "broken_builder"
    shutil.copytree(BUILDER_DIR, broken_dir)
    src = (broken_dir / "builder.py").read_text()
    marker = 'error_text = unavailable.get("message") or "Cannot reach server"'
    assert marker in src, "builder.py's shape changed; update this fault-injection point"
    src = src.replace(marker, 'error_text = "a defect this test deliberately injected"')
    (broken_dir / "builder.py").write_text(src)

    original = rc.BUILDER
    rc.BUILDER = str(broken_dir / "builder.py")
    try:
        yield
    finally:
        rc.BUILDER = original


def test_a_real_persistent_defect_is_reported_and_stops_the_loop(
        builder_with_a_real_bug, command_desk_spec_path, tmp_path):
    result = rc.run_to_done(str(command_desk_spec_path), str(tmp_path / "out"), port=8995, iterations=3,
                             oauth_env={"GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com"})
    assert result["done"] is False
    assert result["cycles_run"] == 2, "must stop as soon as two consecutive cycles agree, not run all 3"
    assert "identical defects" in result["reason"]
    defects = result["history"][-1]["defects"]
    # Two defects, and both are real. The injected text is the screen defect.
    # The second is the shelf gate doing its job: the fault was injected into
    # _render_integration_screen, which is part of oauth_connect's source, so
    # the app was built from bytes that are not the shelf's qualified bytes —
    # exactly how 42f7cf6c shipped (markup changed after qualification).
    assert len(defects) == 2, defects
    by_kind = {d["kind"]: d for d in defects}
    assert by_kind["unavailable_state_wrong"]["spec_ref"] == "SCR-001"
    assert by_kind["unavailable_state_wrong"]["observed"] == "a defect this test deliberately injected"
    assert by_kind["part_drift"]["evidence"]["part_id"] == "oauth_connect"
