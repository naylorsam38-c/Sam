"""Defect Report Generator (packages/defect-report): the Live Playwright
Tester's real reports -> defects tied to numbered spec ids.

Runs the real Builder and the real Playwright tester (same fixtures as
tests/test_playwright_tester.py) to produce real report JSON, then checks
the defect report against it — a clean run reports zero defects, and a real,
engineered defect (the wrong on_unavailable message, same scenario
test_playwright_tester.py already proves the tester itself catches) produces
exactly one defect naming the right numbered id with the right evidence.
Nothing here is a hand-written fake report.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEFECT = ROOT / "packages" / "defect-report"
TESTER = ROOT / "packages" / "playwright-tester"
BUILDER = ROOT / "packages" / "builder"

sys.path.insert(0, str(DEFECT))
sys.path.insert(0, str(BUILDER))
import defect_report as dr  # noqa: E402
import builder as bl        # noqa: E402


class RunningServer:
    def __init__(self, app_dir, port, env=None):
        self.app_dir, self.port, self.env = str(app_dir), port, env or {}

    def __enter__(self):
        env = dict(os.environ)
        env["PORT"] = str(self.port)
        env.update(self.env)
        self.proc = subprocess.Popen(["python3", "app.py"], cwd=self.app_dir, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(30):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=1)
                return self
            except Exception:
                time.sleep(0.2)
        self.proc.terminate()
        raise RuntimeError("server did not come up")

    def __exit__(self, *exc):
        self.proc.terminate()
        try:
            self.proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture
def command_desk_spec():
    good_spec = (ROOT / "packages" / "specgate" / "examples" / "good.spec.yaml").read_text()
    assert "status: approved" in good_spec
    return {
        "spec_id": "SPEC-014-DEFECTTEST", "title": "Linked Services (defect report test)",
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
        },
    }


def _run_normal(spec, app_dir, port, tmp_path, extra_env=None):
    bl.build(spec, str(app_dir), port=port)
    spec_path = tmp_path / f"SPEC-{port}.json"
    spec_path.write_text(json.dumps(spec))
    env = {"GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com"}
    env.update(extra_env or {})
    with RunningServer(app_dir, port, env=env):
        out_dir = tmp_path / f"report-{port}"
        r = subprocess.run(
            [sys.executable, str(TESTER / "live_test.py"), str(spec_path),
             "--base-url", f"http://127.0.0.1:{port}", "--mode", "normal", "-o", str(out_dir)],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((out_dir / "report_normal.json").read_text())


def _run_backend_down(spec, app_dir, port, tmp_path, corrupt_db=True):
    spec_path = tmp_path / f"SPEC-down-{port}.json"
    spec_path.write_text(json.dumps(spec))
    with RunningServer(app_dir, port, env={"GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com"}):
        if corrupt_db:
            (app_dir / "app.db").write_bytes(b"not a sqlite database")
        out_dir = tmp_path / f"report-down-{port}"
        r = subprocess.run(
            [sys.executable, str(TESTER / "live_test.py"), str(spec_path),
             "--base-url", f"http://127.0.0.1:{port}", "--mode", "backend-down", "-o", str(out_dir)],
            capture_output=True, text=True, timeout=30,
        )
    return json.loads((out_dir / "report_backend_down.json").read_text())


def test_clean_run_reports_zero_defects(command_desk_spec, tmp_path):
    app_dir = tmp_path / "cd_app_clean"
    normal = _run_normal(command_desk_spec, app_dir, 8980, tmp_path)
    down = _run_backend_down(command_desk_spec, app_dir, 8980, tmp_path)

    defects = dr.build(command_desk_spec, normal, down)
    assert defects == []

    md = dr.render_markdown(command_desk_spec, defects)
    assert "No defects" in md


def test_real_defect_is_reported_with_the_right_spec_id_and_evidence(command_desk_spec, tmp_path):
    """The same wrong-message scenario test_playwright_tester.py proves the
    tester catches — this checks the defect reporter turns that real,
    already-failing report into exactly one correctly-attributed defect."""
    wrong = dict(command_desk_spec)
    wrong["build_model"] = dict(command_desk_spec["build_model"])
    wrong["build_model"]["integrations"] = {"Gmail": dict(command_desk_spec["build_model"]["integrations"]["Gmail"])}
    wrong["build_model"]["integrations"]["Gmail"]["on_unavailable"] = {"message": "This message will never appear"}

    app_dir = tmp_path / "cd_app_wrong"
    bl.build(wrong, str(app_dir), port=8981)
    # the tester is handed the ORIGINAL spec, so it checks for the message
    # the real, approved spec actually declares, not what this build used
    down = _run_backend_down(command_desk_spec, app_dir, 8981, tmp_path)
    assert down["screens"][0]["passed"] is False  # sanity: the report really is a failure

    defects = dr.build(command_desk_spec, {"screens": []}, down)
    assert len(defects) == 1
    d = defects[0]
    assert d["spec_ref"] == "SCR-001"
    assert d["kind"] == "unavailable_state_wrong"
    assert d["expected"] == "Cannot reach server"
    assert d["observed"] == "This message will never appear"

    md = dr.render_markdown(command_desk_spec, defects)
    assert "SCR-001" in md and "This message will never appear" in md


def test_cli_exit_code_reflects_defect_count(command_desk_spec, tmp_path):
    app_dir = tmp_path / "cd_app_cli"
    normal = _run_normal(command_desk_spec, app_dir, 8982, tmp_path)
    spec_path = tmp_path / "SPEC.json"
    spec_path.write_text(json.dumps(command_desk_spec))
    normal_path = tmp_path / "normal.json"
    normal_path.write_text(json.dumps(normal))

    out_dir = tmp_path / "defects_out"
    r = subprocess.run(
        [sys.executable, str(DEFECT / "defect_report.py"), str(spec_path),
         "--normal", str(normal_path), "-o", str(out_dir)],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (out_dir / "DEFECTS.json").exists()
    assert json.loads((out_dir / "DEFECTS.json").read_text()) == []
