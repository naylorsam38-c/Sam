"""Builder (packages/builder): the assembled numbered spec -> a real running
application.

Every test here builds a real app from real facts and, where a server is
needed, actually starts it and makes real HTTP requests against it — no
mocked responses, no stubbed handlers. Two real-data sources:

  * pm-teamwork's real records/access grants (via the Assembly Engine's own
    derive()/build_model(), the same functions tests/test_assembly_engine.py
    already proves are correct against real data) — for the record/CRUD path.
  * Command Desk's own already-approved spec
    (packages/specgate/examples/good.spec.yaml) — for the OAuth integration
    path. The provider, env var names, routes and behaviour asserted below
    are copied from that real, approved document, not invented.

The OAuth tests make a real outbound request to Google's real, live OAuth
endpoints (accounts.google.com, oauth2.googleapis.com). If that is not
reachable from this environment they are skipped, with the reason stated —
never silently mocked to a green result.
"""

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "packages" / "builder"
ASSEMBLY = ROOT / "packages" / "assembly-engine"
ENGINE = ROOT / "packages" / "requirements-engine"

sys.path.insert(0, str(BUILDER))
sys.path.insert(0, str(ASSEMBLY))
sys.path.insert(0, str(ENGINE))
import builder as bl       # noqa: E402
import assemble as ae      # noqa: E402
import graph_lib           # noqa: E402


def _google_reachable():
    try:
        socket.create_connection(("accounts.google.com", 443), timeout=3).close()
        return True
    except OSError:
        return False


NEEDS_GOOGLE = pytest.mark.skipif(not _google_reachable(), reason="accounts.google.com not reachable from this environment")


class RunningServer:
    """Starts a generated app.py for real, on a real port, and tears it down."""

    def __init__(self, app_dir, port, env=None):
        self.app_dir = app_dir
        self.port = port
        self.env = env or {}

    def __enter__(self):
        import os
        env = dict(os.environ)
        env["PORT"] = str(self.port)
        env.update(self.env)
        self.proc = subprocess.Popen(["python3", "app.py"], cwd=self.app_dir, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(30):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        else:
            self.proc.terminate()
            raise RuntimeError("server did not come up: " + (self.proc.stdout.read() if self.proc.stdout else ""))
        return self

    def __exit__(self, *exc):
        self.proc.terminate()
        try:
            self.out, _ = self.proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.out = ""

    def get(self, path):
        return urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10)

    def request(self, method, path, body=None, follow_redirects=True):
        data = json.dumps(body).encode() if body is not None else b""
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        opener = urllib.request.build_opener() if follow_redirects else _no_redirect_opener()
        return opener.open(req, timeout=10)


def _no_redirect_opener():
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            fp.status, fp.headers = code, headers
            return fp
        http_error_301 = http_error_303 = http_error_307 = http_error_302
    return urllib.request.build_opener(NoRedirect)


@pytest.fixture(scope="module")
def graph():
    g = graph_lib.load_graph(str(ENGINE / "question_graph_v3.json"))
    g["_q"] = {q["id"]: q for q in g["questions"]}
    return g


@pytest.fixture(scope="module")
def pm_records_spec(graph):
    """pm-teamwork's real records/access data, scoped to what the Builder
    supports today (list/detail/CRUD) — report screens are a real, documented,
    refused gap (test_builder_refuses_on_report_screens below), excluded here
    so this fixture can build, not because the data is fabricated."""
    inst = json.loads((ENGINE / "templates" / "pm-teamwork.json").read_text())
    derived = ae.derive(graph, inst)
    bm = ae.build_model(inst, derived)
    bm["screens_inventory"] = [s for s in bm["screens_inventory"] if s["kind"] != "report"]
    bm["reports"] = {}
    return {"spec_id": "SPEC-TEST-PM", "title": "pm-teamwork (records/CRUD path)",
            "graph_version": graph["version"], "source_template": inst["template"],
            "numbered_fields": [], "build_model": bm}


@pytest.fixture(scope="module")
def pm_full_spec(graph):
    """The same real data, unscoped — used only to prove the refusal path."""
    inst = json.loads((ENGINE / "templates" / "pm-teamwork.json").read_text())
    derived = ae.derive(graph, inst)
    bm = ae.build_model(inst, derived)
    return {"spec_id": "SPEC-TEST-PM-FULL", "title": "pm-teamwork (unscoped)",
            "graph_version": graph["version"], "source_template": inst["template"],
            "numbered_fields": [], "build_model": bm}


@pytest.fixture(scope="module")
def command_desk_oauth_spec():
    """Command Desk's real, already-approved Gmail-connection feature —
    packages/specgate/examples/good.spec.yaml, status: approved. Every fact
    here (provider, env var names, route shape, the missing-credential and
    unreachable-server messages) is copied from that document, not invented;
    it predates this Builder and was approved for a different reason (as a
    specgate example)."""
    good_spec = (ROOT / "packages" / "specgate" / "examples" / "good.spec.yaml").read_text()
    assert "status: approved" in good_spec
    assert "Google OAuth 2.0" in good_spec
    assert "GOOGLE_CLIENT_ID" in good_spec and "GOOGLE_CLIENT_SECRET" in good_spec
    assert "Cannot reach server" in good_spec

    return {
        "spec_id": "SPEC-014-REBUILT", "title": "Linked Services (Command Desk, real facts)",
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


# --------------------------------------------------------------------------- record/CRUD path
def test_builder_refuses_on_a_screen_kind_it_has_no_rule_for(pm_full_spec, tmp_path):
    with pytest.raises(bl.BuildRefused, match="no screen rendering rule for kind 'report'"):
        bl.build(pm_full_spec, str(tmp_path / "out"), port=0)


def test_builder_builds_real_crud_and_it_works_against_a_live_server(pm_records_spec, tmp_path):
    out = tmp_path / "pm_app"
    result = bl.build(pm_records_spec, str(out), port=8951)
    assert set(result["records_built"]) == {"Project", "Task", "Comment"}

    import py_compile
    py_compile.compile(str(out / "app.py"), doraise=True)

    with RunningServer(str(out), 8951) as srv:
        rows = json.loads(srv.get("/api/projects").read())
        assert rows == []

        created = json.loads(srv.request("POST", "/api/projects",
                              {"Name": "Website relaunch", "Description": "real test", "Owner": "Sam"}).read())
        rid = created["id"]

        rows = json.loads(srv.get("/api/projects").read())
        assert len(rows) == 1 and rows[0]["name"] == "Website relaunch"

        got = json.loads(srv.get(f"/api/projects/{rid}").read())
        assert got["id"] == rid

        srv.request("PUT", f"/api/projects/{rid}", {"Name": "v2", "Description": "updated", "Owner": "Sam"})
        got = json.loads(srv.get(f"/api/projects/{rid}").read())
        assert got["name"] == "v2"

        assert srv.get("/SCR-001.html").status == 200          # real list page
        assert srv.get(f"/SCR-002.html?id={rid}").status == 200  # real detail page

        deleted = json.loads(srv.request("DELETE", f"/api/projects/{rid}").read())
        assert deleted["deleted"] is True
        assert json.loads(srv.get("/api/projects").read()) == []

        try:
            srv.get("/api/nope")
            assert False, "expected 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404


# --------------------------------------------------------------------------- OAuth integration path
def test_builder_resolves_gmail_to_the_google_provider(command_desk_oauth_spec):
    """Gmail really is a Google product on Google's real OAuth infrastructure
    -- a factual alias, checked here so it cannot silently regress into a
    refusal (it did once, before PROVIDER_ALIASES existed)."""
    flx = command_desk_oauth_spec["build_model"]["integrations"]["Gmail"]
    assert bl._resolve_provider("Gmail", flx) == "google"


def test_builder_builds_the_real_command_desk_oauth_feature(command_desk_oauth_spec, tmp_path):
    out = tmp_path / "cd_app"
    result = bl.build(command_desk_oauth_spec, str(out), port=8952)
    assert result["integrations_built"] == ["Gmail"]

    import py_compile
    py_compile.compile(str(out / "app.py"), doraise=True)
    schema = (out / "schema.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS connections" in schema
    for col in ("provider", "state", "access_token", "refresh_token", "expires_at", "scopes"):
        assert col in schema


def test_builder_start_route_fails_gracefully_without_credentials(command_desk_oauth_spec, tmp_path):
    """AC-03-shaped: a real, running server with no client id configured
    responds with a real error, and stays alive to serve the next request —
    it does not crash."""
    out = tmp_path / "cd_app_nocreds"
    bl.build(command_desk_oauth_spec, str(out), port=8953)
    with RunningServer(str(out), 8953, env={"GOOGLE_CLIENT_ID": ""}) as srv:
        try:
            srv.request("POST", "/api/connections/google/start")
            assert False, "expected an error without credentials"
        except urllib.error.HTTPError as e:
            assert e.code == 500
        assert srv.get("/").status == 200  # the server is still up


@NEEDS_GOOGLE
def test_builder_start_route_redirects_to_the_real_google_endpoint(command_desk_oauth_spec, tmp_path):
    """AC-01-shaped, against Command Desk's real, approved spec: 'Clicking
    Connect issues POST .../start and the response is 302 to
    accounts.google.com'. No mock — this is the actual generated route,
    running for real, redirecting to the actual, live Google endpoint."""
    out = tmp_path / "cd_app_start"
    bl.build(command_desk_oauth_spec, str(out), port=8954)
    with RunningServer(str(out), 8954, env={"GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com"}) as srv:
        r = srv.request("POST", "/api/connections/google/start", follow_redirects=False)
        assert r.status == 302
        location = r.headers.get("Location")
        assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=test-client-id" in location
        assert "state=" in location

        # follow it for real: proves the endpoint is genuinely live, not just a
        # plausible-looking URL string
        real = urllib.request.urlopen(location, timeout=10)
        assert real.status == 200
        assert "accounts.google.com" in real.url


@NEEDS_GOOGLE
def test_builder_callback_hits_googles_real_token_endpoint_and_handles_rejection(command_desk_oauth_spec, tmp_path):
    """No stub anywhere: a bogus code sent to the real callback route makes a
    real request to Google's real token endpoint, which really rejects it
    (401 — no such authorization ever happened), and the generated app turns
    that into a real 502 rather than crashing. This is the honest edge of
    what automation can prove without a live human consenting on Google's own
    screen — that step has no automatable substitute, and this repo does not
    pretend otherwise."""
    out = tmp_path / "cd_app_callback"
    bl.build(command_desk_oauth_spec, str(out), port=8955)
    with RunningServer(str(out), 8955,
                        env={"GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
                             "GOOGLE_CLIENT_SECRET": "test-secret"}) as srv:
        try:
            srv.get("/api/connections/google/callback?code=fake-code-123&state=abc")
            assert False, "a bogus code must not succeed"
        except urllib.error.HTTPError as e:
            assert e.code == 502
            assert b"token exchange failed" in e.read()
