"""Live Playwright Tester (packages/playwright-tester): the numbered spec's
screens/actions, verified against a real running app in a real browser.

Every check here drives an actual generated server with an actual Chromium
instance (the same pinned install packages/crawler.py already proves works
in this environment). No mocked pages, no stubbed responses. The one
real-world constraint this suite works around, not hides: this sandbox's
egress policy denies a headless browser's own onward connection to
accounts.google.com (confirmed via the proxy's own status endpoint — a real
403 policy denial, not a bug, and not something to retry past). The OAuth
click is therefore verified against the redirect response's own Location
header, produced entirely by the real generated server answering the real
click, rather than against where the browser eventually lands — proving the
same real behaviour without depending on whether this particular sandbox may
complete the trip onward. Two other tests (in tests/test_builder.py) already
prove that trip is real when made directly, without a browser in the way.
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
TESTER = ROOT / "packages" / "playwright-tester"
BUILDER = ROOT / "packages" / "builder"
ASSEMBLY = ROOT / "packages" / "assembly-engine"
ENGINE = ROOT / "packages" / "requirements-engine"

for p in (TESTER, BUILDER, ASSEMBLY, ENGINE):
    sys.path.insert(0, str(p))
import live_test as lt     # noqa: E402
import builder as bl       # noqa: E402
import assemble as ae      # noqa: E402
import graph_lib           # noqa: E402


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
        raise RuntimeError("server did not come up: " + (self.proc.stdout.read() if self.proc.stdout else ""))

    def stop(self):
        self.proc.terminate()
        try:
            self.out, _ = self.proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.out = ""

    def __exit__(self, *exc):
        self.stop()


@pytest.fixture(scope="module")
def graph():
    g = graph_lib.load_graph(str(ENGINE / "question_graph_v3.json"))
    g["_q"] = {q["id"]: q for q in g["questions"]}
    return g


@pytest.fixture
def command_desk_spec():
    """Same real facts as tests/test_builder.py's fixture of the same name —
    Command Desk's own already-approved spec, not invented here."""
    good_spec = (ROOT / "packages" / "specgate" / "examples" / "good.spec.yaml").read_text()
    assert "status: approved" in good_spec and "Google OAuth 2.0" in good_spec
    return {
        "spec_id": "SPEC-014-PWTEST", "title": "Linked Services (Playwright)",
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


def test_normal_mode_proves_the_real_click_reaches_the_real_provider(command_desk_spec, tmp_path):
    app_dir = tmp_path / "cd_app"
    bl.build(command_desk_spec, str(app_dir), port=8970)
    spec_path = tmp_path / "SPEC.json"
    spec_path.write_text(json.dumps(command_desk_spec))

    with RunningServer(app_dir, 8970, env={"GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com"}):
        out_dir = tmp_path / "report"
        r = subprocess.run(
            [sys.executable, str(TESTER / "live_test.py"), str(spec_path),
             "--base-url", "http://127.0.0.1:8970", "--mode", "normal", "-o", str(out_dir)],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        report = json.loads((out_dir / "report_normal.json").read_text())

    screen = report["screens"][0]
    assert screen["status"] == 200
    assert screen["empty_state_observed"] is True, "fresh db must show the MISSING/empty state"

    verified = {v["action_id"]: v for v in report["actions_verified"]}
    assert verified["ACT-001"]["verified"] is True
    assert "accounts.google.com" in verified["ACT-001"]["evidence"]

    control = screen["controls"][0]
    assert control["response_status"] == 302
    assert control["location_header"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=test-client" in control["location_header"]


def test_backend_down_mode_proves_the_real_error_text(command_desk_spec, tmp_path):
    """AC-03-shaped: 'with the backend stopped, clicking Connect shows...' —
    the real spec's own wording implies the page still loads and the *API*
    fails. That is what this reproduces for real: the server process is up
    (so the page really loads), and the connections table is genuinely
    unreadable (APP_DB pointed at a directory, so sqlite3 genuinely cannot
    open it), so the real status query really errors and the real frontend
    catch path really renders the message. Stopping the whole process
    instead makes Page.goto itself fail with ERR_CONNECTION_REFUSED before
    the page (or its error banner) ever exists to check — a different, less
    faithful failure than the one the real spec describes, found by trying
    it first. A plain chmod does not work here since these tests can run as
    root, for whom file permissions are not enforced. The database is
    broken only after the server has finished its own startup schema
    creation (which needs a real, working db file) by overwriting it with
    non-database bytes, so the *running* server's *next query* is what
    fails, the same shape a real outage would take."""
    app_dir = tmp_path / "cd_app_down"
    bl.build(command_desk_spec, str(app_dir), port=8971)
    spec_path = tmp_path / "SPEC.json"
    spec_path.write_text(json.dumps(command_desk_spec))

    with RunningServer(app_dir, 8971, env={"GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com"}):
        (app_dir / "app.db").write_bytes(b"not a sqlite database")
        out_dir = tmp_path / "report_down"
        r = subprocess.run(
            [sys.executable, str(TESTER / "live_test.py"), str(spec_path),
             "--base-url", "http://127.0.0.1:8971", "--mode", "backend-down", "-o", str(out_dir)],
            capture_output=True, text=True, timeout=30,
        )
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads((out_dir / "report_backend_down.json").read_text())
    assert report["screens"][0]["passed"] is True
    assert report["screens"][0]["observed_text"] == "Cannot reach server"


def test_backend_down_mode_fails_a_wrong_message_honestly(command_desk_spec, tmp_path):
    """The refusal path: if the declared message does not match what actually
    renders, the tester must say so, not pass anyway. Built with a different
    on_unavailable message than the spec file the tester is given, so a real
    server, with a real (broken-db) failure, renders real but wrong text."""
    wrong = dict(command_desk_spec)
    wrong["build_model"] = dict(command_desk_spec["build_model"])
    wrong["build_model"]["integrations"] = {"Gmail": dict(command_desk_spec["build_model"]["integrations"]["Gmail"])}
    wrong["build_model"]["integrations"]["Gmail"]["on_unavailable"] = {"message": "This message will never appear"}
    app_dir = tmp_path / "cd_app_wrong"
    bl.build(wrong, str(app_dir), port=8972)
    spec_path = tmp_path / "SPEC.json"
    spec_path.write_text(json.dumps(command_desk_spec))  # tester checks against the ORIGINAL expected message

    with RunningServer(app_dir, 8972, env={"GOOGLE_CLIENT_ID": "test-client.apps.googleusercontent.com"}):
        (app_dir / "app.db").write_bytes(b"not a sqlite database")
        out_dir = tmp_path / "report_wrong"
        r = subprocess.run(
            [sys.executable, str(TESTER / "live_test.py"), str(spec_path),
             "--base-url", "http://127.0.0.1:8972", "--mode", "backend-down", "-o", str(out_dir)],
            capture_output=True, text=True, timeout=30,
        )
    assert r.returncode == 1
    report = json.loads((out_dir / "report_backend_down.json").read_text())
    assert report["screens"][0]["passed"] is False
    assert report["screens"][0]["observed_text"] == "This message will never appear"  # proves it really rendered, just doesn't match


def test_records_screens_load_cleanly_in_a_real_browser(graph, tmp_path):
    """The CRUD path, using pm-teamwork's real records — the same real data
    tests/test_builder.py already proves the generated server handles
    correctly over HTTP; this proves the generated pages load in a real
    browser with no console or page errors."""
    inst = json.loads((ENGINE / "templates" / "pm-teamwork.json").read_text())
    derived = ae.derive(graph, inst)
    bm = ae.build_model(inst, derived)
    bm["screens_inventory"] = [s for s in bm["screens_inventory"] if s["kind"] != "report"]
    bm["reports"] = {}
    spec = {"spec_id": "SPEC-TEST-PM-PW", "title": "pm-teamwork records", "graph_version": graph["version"],
            "source_template": inst["template"], "numbered_fields": [], "build_model": bm}

    app_dir = tmp_path / "pm_app"
    bl.build(spec, str(app_dir), port=8973)
    spec_path = tmp_path / "SPEC.json"
    spec_path.write_text(json.dumps(spec))

    with RunningServer(app_dir, 8973):
        out_dir = tmp_path / "report_pm"
        r = subprocess.run(
            [sys.executable, str(TESTER / "live_test.py"), str(spec_path),
             "--base-url", "http://127.0.0.1:8973", "--mode", "normal", "-o", str(out_dir)],
            capture_output=True, text=True, timeout=60,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        report = json.loads((out_dir / "report_normal.json").read_text())

    assert len(report["screens"]) == len(bm["screens_inventory"])
    for screen in report["screens"]:
        assert screen["status"] == 200, f"{screen['screen_id']} did not load"
        assert screen["console_errors"] == [], f"{screen['screen_id']}: {screen['console_errors']}"
        assert screen["page_errors"] == [], f"{screen['screen_id']}: {screen['page_errors']}"
