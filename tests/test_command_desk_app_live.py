"""Command Desk, built by the Builder and proven against the real running app.

Nothing here inspects generated source. The app is assembled from the real
answers, built to disk, started as a real server process, and driven over
real HTTP — and the form screen is driven in real Chromium. Every assertion
reads what the running system actually did.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for package in ("assembly-engine", "requirements-engine", "builder"):
    path = str(ROOT / "packages" / package)
    if path not in sys.path:
        sys.path.insert(0, path)

import assemble as ae  # noqa: E402
import builder as bl  # noqa: E402
import check_template  # noqa: E402

TEMPLATE = ROOT / "packages" / "requirements-engine" / "templates" / "command-desk.json"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class App:
    """The built app, running for real."""

    def __init__(self, out_dir, port):
        self.base = f"http://127.0.0.1:{port}"
        env = dict(os.environ, APP_DB=str(Path(out_dir) / "app.db"))
        self.proc = subprocess.Popen([sys.executable, "app.py"], cwd=out_dir, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                self.get("/api/agents")
                return
            except Exception:
                if self.proc.poll() is not None:
                    raise RuntimeError("the app exited:\n" + self.proc.stdout.read().decode())
                time.sleep(0.15)
        raise RuntimeError("the app never came up")

    def request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as err:
            raw = err.read()
            return err.code, (json.loads(raw) if raw else None)

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body=None):
        return self.request("POST", path, body or {})

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Assemble the real spec from the real answers and build the real app."""
    graph = check_template.load_graph()
    inst = json.loads(TEMPLATE.read_text())
    spec = ae.assemble(graph, inst, "command-desk-1", "Command Desk")
    # Sam's own orb artwork (orb-glyph.png / orb-rotor.png) is not in this
    # repository, so this build uses the starter library's mark. Stated here
    # rather than hidden: it is the only thing in the built app that is not
    # from Sam's own answers.
    spec["build_model"]["brand"] = {"mode": "premade", "logo_id": "orbit"}
    out = tmp_path_factory.mktemp("command-desk-app")
    result = bl.build(spec, str(out), port=_free_port())
    return spec, str(out), result


@pytest.fixture(scope="module")
def app(built):
    spec, out_dir, _ = built
    port = _free_port()
    # the port is baked into app.py at build time, so rebuild at the real port
    shutil.rmtree(out_dir + "-run", ignore_errors=True)
    bl.build(spec, out_dir + "-run", port=port)
    server = App(out_dir + "-run", port)
    yield server
    server.stop()


def test_the_builder_built_every_numbered_screen(built):
    spec, out_dir, result = built
    assert result["screens_built"] == len(spec["build_model"]["screens_inventory"]) == 23
    static = Path(out_dir) / "static"
    for screen in spec["build_model"]["screens_inventory"]:
        assert (static / (screen["id"].replace("/", "__") + ".html")).exists(), screen["id"]


def test_the_generated_app_runs_the_shelf_engines_not_a_copy(built):
    """The vendored engines must be byte-identical to the shelf's own files."""
    _, out_dir, _ = built
    shelf = ROOT / "packages" / "builder" / "engines"
    for module in bl.VENDORED_ENGINES:
        assert (Path(out_dir) / "engines" / f"{module}.py").read_bytes() == \
            (shelf / f"{module}.py").read_bytes(), module


def test_a_record_with_a_lifecycle_starts_in_its_declared_initial_stage(app):
    status, job = app.post("/api/jobs", {"What was asked": "draft the reply", "Agent": "A-1"})
    assert status in (200, 201), job
    status, row = app.get(f"/api/jobs/{job['id']}")
    assert row["stage"] == "queued"


def test_the_form_creates_a_real_record_and_refuses_an_undeclared_field(app):
    status, created = app.post("/api/forms/add_an_agent", {
        "name": "research", "role": "web research", "model": "qwen2.5",
        "instructions": "find things and cite them", "tools_it_may_use": "tavily",
        "is_on": "on", "reports_to": "hub"})
    assert status == 201, created

    status, rows = app.get("/api/agents")
    assert any(r["name"] == "research" for r in rows)

    status, refused = app.post("/api/forms/add_an_agent", {
        "name": "sneaky", "role": "r", "model": "m", "instructions": "i",
        "tools_it_may_use": "", "is_on": "on", "reports_to": "hub", "salary": "100"})
    assert status == 400 and "not a field of this record" in refused["error"]


def test_the_job_lifecycle_moves_on_its_own_events_and_stops_at_the_gate(app):
    status, job = app.post("/api/jobs", {"What was asked": "send the reply", "Agent": "A-1"})
    job_id = job["id"]

    status, moved = app.post(f"/api/events/jobs/{job_id}", {"event": "the agent picks the job up"})
    # the move response also carries "effects": what the workflow's declared
    # transition effects did on entering the stage (none are declared here)
    assert status == 200 and {k: moved[k] for k in ("from", "to")} == {"from": "queued", "to": "running"}
    assert moved["effects"] == []

    # 'running' is the gated stage: the system may not move it on unattended
    status, blocked = app.post(f"/api/events/jobs/{job_id}",
                               {"event": "the agent finishes and writes a real result"})
    assert status == 409, blocked
    assert blocked.get("waiting_for_approval") is True
    status, row = app.get(f"/api/jobs/{job_id}")
    assert row["stage"] == "running", "nothing may have moved while it waits"

    status, decided = app.post(f"/api/approvals/jobs/{job_id}",
                               {"decision": "APPROVED", "by": "Sam", "reason": "send it"})
    assert status == 200 and decided["decision"] == "APPROVED"

    status, moved = app.post(f"/api/events/jobs/{job_id}",
                             {"event": "the agent finishes and writes a real result"})
    assert status == 200 and {k: moved[k] for k in ("from", "to")} == {"from": "running", "to": "done"}


def test_a_declined_approval_sends_the_job_where_the_workflow_says(app):
    status, job = app.post("/api/jobs", {"What was asked": "pay the invoice", "Agent": "A-1"})
    job_id = job["id"]
    app.post(f"/api/events/jobs/{job_id}", {"event": "the agent picks the job up"})

    status, decided = app.post(f"/api/approvals/jobs/{job_id}",
                               {"decision": "DECLINED", "by": "Sam", "reason": "wrong recipient"})
    assert status == 200
    assert decided == {"decision": "DECLINED", "stage": "failed"}, decided
    status, row = app.get(f"/api/jobs/{job_id}")
    assert row["stage"] == "failed"


def test_an_undeclared_event_is_refused_by_the_running_app(app):
    status, job = app.post("/api/jobs", {"What was asked": "x", "Agent": "A-1"})
    status, refused = app.post(f"/api/events/jobs/{job['id']}", {"event": "just do it"})
    assert status == 400 and "no automatic edge leaves 'queued'" in refused["error"]


def test_a_person_moved_edge_needs_one_of_its_own_roles(app):
    status, project = app.post("/api/projects", {"Name": "Command Desk", "Goal": "ship it"})
    project_id = project["id"]
    status, moved = app.post(f"/api/moves/projects/{project_id}", {"to": "paused", "role": "Sam"})
    assert status == 200, moved
    status, row = app.get(f"/api/projects/{project_id}")
    assert row["stage"] == "paused"

    status, refused = app.post(f"/api/moves/projects/{project_id}", {"to": "active", "role": "Nova"})
    assert status == 409, refused
    status, row = app.get(f"/api/projects/{project_id}")
    assert row["stage"] == "paused", "a role the transition does not name moved it anyway"


def test_pause_and_retry_really_run(app):
    status, agent = app.post("/api/forms/add_an_agent", {
        "name": "builder", "role": "builds", "model": "qwen2.5", "instructions": "build",
        "tools_it_may_use": "", "is_on": "on", "reports_to": "hub"})
    agent_id = agent["id"]

    status, result = app.post(f"/api/actions/agents/{agent_id}/Pause", {"role": "Sam"})
    assert status == 200, result
    status, row = app.get(f"/api/agents/{agent_id}")
    assert row["is_on"] == 0 and row["stage"] == "stopped-and-reported"

    status, refused = app.post(f"/api/actions/agents/{agent_id}/Pause", {"role": "Nova"})
    assert status == 403, refused

    status, job = app.post("/api/jobs", {"What was asked": "retry me", "Agent": agent_id})
    job_id = job["id"]
    app.post(f"/api/events/jobs/{job_id}", {"event": "the agent picks the job up"})
    app.post(f"/api/approvals/jobs/{job_id}", {"decision": "APPROVED", "by": "Sam"})
    app.post(f"/api/events/jobs/{job_id}", {"event": "the agent errors or stops before finishing"})
    status, row = app.get(f"/api/jobs/{job_id}")
    assert row["stage"] == "failed"

    status, result = app.post(f"/api/actions/jobs/{job_id}/Retry", {"role": "Sam"})
    assert status == 200, result
    status, row = app.get(f"/api/jobs/{job_id}")
    assert row["stage"] == "queued" and row["result"] is None


def test_the_reports_return_real_numbers_from_real_rows(app):
    status, before = app.get("/api/reports/activity_per_agent")
    assert status == 200, before

    status, agent = app.post("/api/forms/add_an_agent", {
        "name": "reporter", "role": "reports", "model": "qwen2.5", "instructions": "x",
        "tools_it_may_use": "", "is_on": "on", "reports_to": "hub"})
    agent_id = agent["id"]
    status, job = app.post("/api/jobs", {"What was asked": "count me", "Agent": agent_id,
                                         "Cost": 1.25})
    job_id = job["id"]
    app.post(f"/api/events/jobs/{job_id}", {"event": "the agent picks the job up"})
    app.post(f"/api/approvals/jobs/{job_id}", {"decision": "APPROVED", "by": "Sam"})
    app.post(f"/api/events/jobs/{job_id}", {"event": "the agent finishes and writes a real result"})

    status, after = app.get("/api/reports/activity_per_agent")
    done = after["jobs done per agent per week"]
    assert done.get(agent_id, 0) == before["jobs done per agent per week"].get(agent_id, 0) + 1

    status, cost = app.get("/api/reports/cost")
    assert status == 200
    assert cost["spend on hosted model calls"][agent_id] == pytest.approx(1.25)


def test_a_pasted_api_key_is_stored_and_never_echoed(app):
    status, saved = app.post("/api/connections/tavily_search/key", {"key": "tvly-real-key-value"})
    assert status == 200, saved
    assert saved == {"provider": "Tavily search", "state": "connected"}
    assert "tvly-real-key-value" not in json.dumps(saved)

    status, refused = app.post("/api/connections/tavily_search/key", {})
    assert status == 400


def test_the_form_screen_works_in_a_real_browser(app, built):
    sync_playwright = pytest.importorskip(
        "playwright.sync_api", reason="Playwright is required for the browser test").sync_playwright
    spec, _, _ = built
    screen = next(s for s in spec["build_model"]["screens_inventory"]
                  if s["kind"] == "form" and s["form"] == "Add an agent")
    url = f"{app.base}/static/{screen['id'].replace('/', '__')}.html"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        assert page.inner_text("h1") == "Agent"
        page.fill("#name", "browser-made")
        page.fill("#role", "typed by a real browser")
        page.fill("#model", "qwen2.5")
        page.fill("#instructions", "real typing")
        page.fill("#tools_it_may_use", "none")
        page.check("#is_on")
        # 'Reports to' is a real link field: its options are the target
        # record's own real rows, fetched by the page from the running app
        page.wait_for_function("document.querySelectorAll('#reports_to option').length > 0")
        page.select_option("#reports_to", index=0)
        page.click("button[type=submit]")
        page.wait_for_function("document.getElementById('result').textContent.startsWith('saved')")
        browser.close()

    status, rows = app.get("/api/agents")
    assert any(r["name"] == "browser-made" for r in rows), "the browser's submission is not in the database"


def test_the_built_app_carries_a_manifest_of_the_exact_parts_it_uses(built):
    """MANIFEST.json names every shelf part this app exercises, at the exact
    source revision vendored — read from the shelf's own identity function,
    and it must match the shelf right now."""
    _, out_dir, _ = built
    sys.path.insert(0, str(ROOT / "packages" / "builder"))
    import shelf as shelf_lib
    manifest = json.loads((Path(out_dir) / "MANIFEST.json").read_text())
    shelf = {p["part_id"]: p for p in shelf_lib.load_shelf()["parts"]}
    used = {p["part_id"] for p in manifest["parts"]}
    # Command Desk declares forms, reports, person-moved and system-moved
    # edges, an approval gate, custom actions, OAuth and pasted-key services
    assert {"crud_list_detail", "form_render_submit", "reporting_engine", "workflow_executor",
            "system_triggered_transition", "stage_approval_gate", "custom_action_execution",
            "oauth_connect", "api_key_connect", "audit_trail"} <= used
    for pin in manifest["parts"] + manifest["vendored"]:
        assert pin["revision"] == shelf_lib.source_revision(shelf[pin["part_id"]]), pin
        assert pin["status"] == shelf[pin["part_id"]]["status"]
    assert manifest["required_status_for_deployable"] == shelf_lib.REQUIRED_STATUS_FOR_DEPLOYABLE
