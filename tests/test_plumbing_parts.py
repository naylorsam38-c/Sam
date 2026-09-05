"""The three parts that close Command Desk's remaining plumbing gaps,
tested against real running systems.

The form part is exercised the way it will actually be used: a real HTTP
server renders it, real Chromium loads it, a person's real typing and a
real submit put a real row in a real sqlite database. The other two run
against a real database and are checked by reading the rows and the audit
log back, never by inspecting the call.
"""

import sqlite3
import sys
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ENGINES = Path(__file__).resolve().parents[1] / "packages" / "builder" / "engines"
if str(ENGINES) not in sys.path:
    sys.path.insert(0, str(ENGINES))

import audit_trail  # noqa: E402
import custom_action_execution as custom  # noqa: E402
import form_render_submit as forms  # noqa: E402
import system_triggered_transition as auto  # noqa: E402

JOB_TRANSITIONS = [
    {"from": "queued", "to": "running", "mover": "automatic", "event": "the agent picks the job up"},
    {"from": "running", "to": "done", "mover": "automatic",
     "event": "the agent finishes and writes a real result"},
    {"from": "running", "to": "failed", "mover": "automatic",
     "event": "the agent errors or stops before finishing"},
]

AGENT_FIELDS = [
    {"name": "Name", "type": "short_text", "required": "yes", "unique": "yes"},
    {"name": "Role", "type": "short_text", "required": "yes", "unique": "no"},
    {"name": "Model", "type": "short_text", "required": "yes", "unique": "no"},
    {"name": "Instructions", "type": "long_text", "required": "yes", "unique": "no"},
    {"name": "Is on", "type": "yes_no", "required": "yes", "unique": "no"},
]


@pytest.fixture
def db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "desk.db"), timeout=10)
    conn.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, ask TEXT, result TEXT, "
                 "finished_at TEXT, stage TEXT)")
    conn.execute("CREATE TABLE agents (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT, "
                 "model TEXT, instructions TEXT, is_on INTEGER, stage TEXT)")
    audit_trail.ensure_table(conn)
    yield conn
    conn.close()


# =====================================================================
# system_triggered_transition — the automatic half of every lifecycle
# =====================================================================

def test_the_job_lifecycle_runs_on_its_own_declared_events(db):
    db.execute("INSERT INTO jobs VALUES ('J-1', 'draft the reply', NULL, NULL, 'queued')")
    db.commit()

    assert auto.fire(db, "jobs", "J-1", "stage", JOB_TRANSITIONS,
                     "the agent picks the job up") == ("queued", "running")
    assert auto.fire(db, "jobs", "J-1", "stage", JOB_TRANSITIONS,
                     "the agent finishes and writes a real result") == ("running", "done")
    assert db.execute("SELECT stage FROM jobs WHERE id = 'J-1'").fetchone()[0] == "done"

    log = audit_trail.history_for(db, "jobs", "J-1")
    assert [(e["before"]["stage"], e["after"]["stage"]) for e in log] == \
        [("queued", "running"), ("running", "done")]


def test_the_same_row_can_take_the_other_declared_branch(db):
    db.execute("INSERT INTO jobs VALUES ('J-2', 'search', NULL, NULL, 'queued')")
    db.commit()
    auto.fire(db, "jobs", "J-2", "stage", JOB_TRANSITIONS, "the agent picks the job up")
    auto.fire(db, "jobs", "J-2", "stage", JOB_TRANSITIONS,
              "the agent errors or stops before finishing")
    assert db.execute("SELECT stage FROM jobs WHERE id = 'J-2'").fetchone()[0] == "failed"


def test_an_undeclared_event_moves_nothing(db):
    db.execute("INSERT INTO jobs VALUES ('J-3', 'search', NULL, NULL, 'queued')")
    db.commit()
    with pytest.raises(auto.NoSuchEvent) as err:
        auto.fire(db, "jobs", "J-3", "stage", JOB_TRANSITIONS, "someone felt like it")
    assert "no automatic edge leaves 'queued'" in str(err.value)
    assert db.execute("SELECT stage FROM jobs WHERE id = 'J-3'").fetchone()[0] == "queued"
    assert audit_trail.history_for(db, "jobs", "J-3") == []


def test_the_system_cannot_fire_an_edge_a_person_owns(db):
    transitions = JOB_TRANSITIONS + [
        {"from": "done", "to": "archived", "mover": "roles", "roles": ["Sam"],
         "event": "Sam archives it"}]
    db.execute("INSERT INTO jobs VALUES ('J-4', 'search', NULL, NULL, 'done')")
    db.commit()
    with pytest.raises(auto.IllegalTransition) as err:
        auto.fire(db, "jobs", "J-4", "stage", transitions, "Sam archives it")
    assert "not by the system" in str(err.value)
    assert db.execute("SELECT stage FROM jobs WHERE id = 'J-4'").fetchone()[0] == "done"


def test_an_ambiguous_workflow_is_refused_rather_than_guessed(db):
    ambiguous = [
        {"from": "queued", "to": "running", "mover": "automatic", "event": "go"},
        {"from": "queued", "to": "failed", "mover": "automatic", "event": "go"},
    ]
    db.execute("INSERT INTO jobs VALUES ('J-5', 'search', NULL, NULL, 'queued')")
    db.commit()
    with pytest.raises(auto.IllegalTransition) as err:
        auto.fire(db, "jobs", "J-5", "stage", ambiguous, "go")
    assert "will not choose" in str(err.value)
    assert db.execute("SELECT stage FROM jobs WHERE id = 'J-5'").fetchone()[0] == "queued"


# =====================================================================
# custom_action_execution — Pause and Retry
# =====================================================================

PAUSE = {"name": "Pause", "who": ["Sam"], "result_location": "the agent's own screen",
         "effect": {"op": "set_fields", "fields": {"is_on": 0, "stage": "stopped-and-reported"}}}
RETRY = {"name": "Retry", "who": ["Sam"], "result_location": "the job's own screen",
         "effect": {"op": "reset_to_stage", "stage_column": "stage", "stage": "queued",
                    "clear": ["result", "finished_at"]}}


def test_pause_really_stops_a_running_agent(db):
    db.execute("INSERT INTO agents (name, role, model, instructions, is_on, stage) "
               "VALUES ('research', 'web research', 'qwen2.5', 'find things', 1, 'running')")
    db.commit()
    agent_id = db.execute("SELECT id FROM agents WHERE name = 'research'").fetchone()[0]

    custom.run(db, PAUSE, "agents", agent_id, "Sam")
    assert db.execute("SELECT is_on, stage FROM agents WHERE id = ?", (agent_id,)).fetchone() \
        == (0, "stopped-and-reported")
    log = audit_trail.history_for(db, "agents", agent_id)
    assert log[-1]["action"] == "custom:Pause"
    assert log[-1]["before"]["is_on"] == 1


def test_retry_puts_a_failed_job_back_and_clears_what_it_declares(db):
    db.execute("INSERT INTO jobs VALUES ('J-6', 'draft the reply', 'no answer', "
               "'2026-09-04T10:00', 'failed')")
    db.commit()
    custom.run(db, RETRY, "jobs", "J-6", "Sam")
    assert db.execute("SELECT stage, result, finished_at FROM jobs WHERE id = 'J-6'").fetchone() \
        == ("queued", None, None)
    assert db.execute("SELECT ask FROM jobs WHERE id = 'J-6'").fetchone()[0] == "draft the reply", \
        "retry must keep what was asked"


def test_a_role_the_action_does_not_name_cannot_press_it(db):
    db.execute("INSERT INTO jobs VALUES ('J-7', 'x', 'r', 't', 'failed')")
    db.commit()
    with pytest.raises(custom.NotAllowed):
        custom.run(db, RETRY, "jobs", "J-7", "Nova")
    assert db.execute("SELECT stage FROM jobs WHERE id = 'J-7'").fetchone()[0] == "failed"


def test_an_effect_with_no_code_is_refused_not_approximated(db):
    db.execute("INSERT INTO jobs VALUES ('J-8', 'x', NULL, NULL, 'failed')")
    db.commit()
    with pytest.raises(custom.UnknownOperation):
        custom.run(db, {"name": "Escalate", "who": ["Sam"], "effect": {"op": "escalate"}},
                   "jobs", "J-8", "Sam")


def test_an_effect_that_changes_nothing_is_refused_not_run_as_broken_sql(db):
    """Command Desk ACT-024 shipped as clear_fields [] and the running app
    answered 500 'near "WHERE": syntax error' — caught by the seam journeys."""
    db.execute("INSERT INTO jobs VALUES ('J-9', 'x', NULL, NULL, 'failed')")
    db.commit()
    with pytest.raises(custom.UnknownOperation, match="change nothing"):
        custom.run(db, {"name": "Open", "who": ["Sam"], "effect": {"op": "clear_fields", "fields": []}},
                   "jobs", "J-9", "Sam")
    assert db.execute("SELECT stage FROM jobs WHERE id='J-9'").fetchone()[0] == "failed"


def test_an_action_cannot_touch_a_column_the_table_does_not_have(db):
    db.execute("INSERT INTO jobs VALUES ('J-9', 'x', NULL, NULL, 'failed')")
    db.commit()
    with pytest.raises(ValueError) as err:
        custom.run(db, {"name": "Bill", "who": ["Sam"],
                        "effect": {"op": "set_fields", "fields": {"invoice_total": 10}}},
                   "jobs", "J-9", "Sam")
    assert "no column" in str(err.value)


# =====================================================================
# form_render_submit — driven in a real browser
# =====================================================================

def _server(db_path):
    """A real HTTP server that serves the rendered form and writes the real
    submission through the part under test."""
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _send(self, status, body, ctype="text/html; charset=utf-8"):
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            self._send(200, "<!doctype html><meta charset='utf-8'>" +
                       forms.render_form("Agent", AGENT_FIELDS, "/agents"))

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8")
            values = {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}
            conn = sqlite3.connect(db_path, timeout=10)
            try:
                row_id = forms.submit(conn, "agents", AGENT_FIELDS, values)
                self._send(200, f"<h1 id='saved'>saved {row_id}</h1>")
            except (forms.FieldNotDeclared, forms.MissingRequired, forms.NotUnique) as err:
                self._send(400, f"<h1 id='refused'>{err}</h1>")
            finally:
                conn.close()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


@pytest.fixture
def live_form(tmp_path):
    db_path = str(tmp_path / "forms.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE agents (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT, "
                 "model TEXT, instructions TEXT, is_on INTEGER)")
    conn.commit()
    conn.close()
    httpd = _server(db_path)
    yield f"http://{httpd.server_address[0]}:{httpd.server_address[1]}", db_path
    httpd.shutdown()
    httpd.server_close()


def test_a_person_can_really_fill_the_generated_form_in_a_real_browser(live_form):
    sync_playwright = pytest.importorskip(
        "playwright.sync_api", reason="Playwright is required for the browser test").sync_playwright
    base_url, db_path = live_form

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)

        assert page.inner_text("h1") == "Agent"
        page.fill("#name", "research")
        page.fill("#role", "web research")
        page.fill("#model", "qwen2.5")
        page.fill("#instructions", "find things and cite them")
        page.check("#is_on")
        page.click("button[type=submit]")
        page.wait_for_selector("#saved")
        browser.close()

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT name, role, model, instructions, is_on FROM agents").fetchall()
    finally:
        conn.close()
    assert row == [("research", "web research", "qwen2.5", "find things and cite them", 1)]


def test_the_browser_itself_blocks_a_required_field_left_empty(live_form):
    sync_playwright = pytest.importorskip(
        "playwright.sync_api", reason="Playwright is required for the browser test").sync_playwright
    base_url, db_path = live_form

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.fill("#name", "half done")
        page.click("button[type=submit]")
        # the required attribute the part rendered is real: the browser refuses
        assert page.evaluate("document.querySelector('#role').validity.valueMissing") is True
        assert page.url.rstrip("/") == base_url.rstrip("/"), "the form must not have submitted"
        browser.close()

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 0
    finally:
        conn.close()


def test_the_server_refuses_a_field_the_record_does_not_declare(live_form):
    base_url, db_path = live_form
    body = urllib.parse.urlencode({
        "name": "sneaky", "role": "r", "model": "m", "instructions": "i",
        "is_on": "on", "salary": "100"}).encode()
    request = urllib.request.Request(base_url + "/agents", data=body, method="POST")
    try:
        urllib.request.urlopen(request, timeout=10)
        raise AssertionError("the server should have refused this")
    except urllib.error.HTTPError as err:
        assert err.code == 400
        assert "not a field of this record" in err.read().decode("utf-8")

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 0
    finally:
        conn.close()
