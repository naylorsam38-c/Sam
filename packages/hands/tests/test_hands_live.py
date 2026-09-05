"""Hands, tested against a real running system.

Every test here starts the real HTTP server in a real socket-listening
process thread, talks to it over real HTTP, and works on real PDF files
written to a real temporary directory with a real sqlite database behind
them. Nothing is mocked, stubbed or simulated: there is no fake provider
to fake, because the engine calls no model — field detection reads the
document's actual bytes.
"""

import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from hands import api, config, documents, engine, fields  # noqa: E402
from hands import provenance as prov  # noqa: E402
from hands import session as sess, shelf, store, trust_gate, workflow  # noqa: E402

TOKEN = "test-token-not-a-secret"

#: The real document every journey test starts from: a real PDF with three
#: real AcroForm fields — one already filled, one blank, one that makes a
#: declaration in the worker's name.
FORM_SPEC = [
    {"name": "worker_name", "label": "Worker name", "value": "", "rect": [150, 700, 400, 715]},
    {"name": "site_address", "label": "Site address", "value": "12 Rundle St, Adelaide",
     "rect": [150, 660, 400, 675]},
    {"name": "induction_complete_declaration", "label": "Induction declaration", "value": "",
     "rect": [150, 620, 400, 635]},
]


class Client:
    def __init__(self, base_url, token=TOKEN):
        self.base_url = base_url
        self.token = token

    def request(self, method, path, body=None, raw=False):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = response.read()
                if raw:
                    return response.status, payload
                return response.status, json.loads(payload.decode("utf-8"))
        except urllib.error.HTTPError as err:
            payload = err.read()
            if raw:
                return err.code, payload
            return err.code, json.loads(payload.decode("utf-8"))

    def get(self, path, raw=False):
        return self.request("GET", path, raw=raw)

    def post(self, path, body=None):
        return self.request("POST", path, body or {})


@pytest.fixture
def live(tmp_path):
    """A real server on a real port, over a real data directory."""
    root = tmp_path / "hands-data"
    httpd, _thread = api.serve(host="127.0.0.1", port=0, data_root=str(root), token=TOKEN)
    host, port = httpd.server_address[0], httpd.server_address[1]
    client = Client(f"http://{host}:{port}")
    status, health = client.get("/api/health")
    assert status == 200 and health["ok"] is True, "the server must actually be up before a test runs"
    yield client, str(root)
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def form_pdf(tmp_path):
    """A real PDF on disk, built by the shelf's own pdf_form_filling part."""
    path = tmp_path / "site-induction.pdf"
    shelf.pdf_form_filling.render_pdf_with_form(str(path), "Site induction", FORM_SPEC)
    return path


def upload(client, session_id, pdf_path, known_values=None):
    return client.post(f"/api/sessions/{session_id}/document", {
        "filename": pdf_path.name,
        "content_base64": base64.b64encode(pdf_path.read_bytes()).decode("ascii"),
        "known_values": known_values or {},
    })


def start(client, workflow_id="document_completion", customer="sam"):
    status, body = client.post("/api/sessions", {"workflow_id": workflow_id, "customer": customer})
    assert status == 201, body
    return body["session_id"]


# =====================================================================
# The part-level proof, run for real
# =====================================================================

def test_field_detection_proves_itself_against_a_real_pdf():
    evidence = fields.prove()
    assert evidence["part"] == "document_field_detection"
    assert [f["name"] for f in evidence["observed"]["detected"]] == [
        "worker_name", "site_address", "induction_complete_declaration"]


# =====================================================================
# The full document-completion journey, live
# =====================================================================

def test_document_completion_end_to_end_over_real_http(live, form_pdf):
    client, root = live
    session_id = start(client)

    # 1. upload the real document; the engine reads its real fields
    status, body = upload(client, session_id, form_pdf)
    assert status == 200, body
    by_name = {f["name"]: f for f in body["fields"]}
    assert by_name["site_address"]["provenance"] == prov.KNOWN
    assert by_name["site_address"]["value"] == "12 Rundle St, Adelaide"
    assert by_name["worker_name"]["provenance"] == prov.MISSING
    assert by_name["induction_complete_declaration"]["provenance"] == prov.MISSING
    assert body["state"] == sess.WAITING_FOR_INFORMATION

    # 2. price is locked before anything executes
    status, body = client.post(f"/api/sessions/{session_id}/price",
                               {"price_cents": 5000, "scope": "one document, up to 4 modules"})
    assert status == 200
    assert body["state"] == sess.WAITING_FOR_INFORMATION, "a locked price does not unblock missing info"

    # 3. the customer supplies what was missing
    status, body = client.post(f"/api/sessions/{session_id}/information",
                               {"field": "worker_name", "value": "Sam Naylor"})
    assert status == 200
    assert body["state"] == sess.WAITING_FOR_INFORMATION, "the declaration is still missing"

    status, body = client.post(f"/api/sessions/{session_id}/information",
                               {"field": "induction_complete_declaration",
                                "value": "I have completed the site induction"})
    assert status == 200
    assert body["state"] == sess.READY
    supplied = {f["name"]: f for f in body["fields"]}
    assert supplied["worker_name"]["provenance"] == prov.SUPPLIED_BY_CUSTOMER
    assert supplied["induction_complete_declaration"]["provenance"] == prov.REQUIRES_APPROVAL, \
        "supplying a declaration is not the same as approving it"

    # 4. executing stops at the Trust Gate
    status, body = client.post(f"/api/sessions/{session_id}/execute")
    assert status == 200
    assert body["result"]["stopped"] == "ACTION_REQUIRED"
    assert body["state"] == sess.ACTION_REQUIRED
    digest = body["result"]["payload_hash"]
    assert "induction_complete_declaration" in body["result"]["payload"]["declarations"]

    status, view = client.get(f"/api/sessions/{session_id}")
    assert view["pending_approval"]["payload_hash"] == digest

    # 5. the customer approves exactly what they were shown
    status, body = client.post(f"/api/sessions/{session_id}/approval",
                               {"action": "generate_completed", "payload_hash": digest,
                                "decision": "APPROVED"})
    assert status == 200

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    assert status == 200, body
    assert body["result"]["stopped"] == "REVIEW"
    completed_id = body["result"]["completed_document_id"]

    # 6. review, then the second gate over the completed copy's real bytes
    status, body = client.post(f"/api/sessions/{session_id}/finalise")
    assert status == 200
    assert body["result"]["stopped"] == "ACTION_REQUIRED"
    sign_digest = body["result"]["payload_hash"]

    status, _ = client.post(f"/api/sessions/{session_id}/approval",
                            {"action": "sign_completed", "payload_hash": sign_digest,
                             "decision": "APPROVED"})
    assert status == 200

    status, body = client.post(f"/api/sessions/{session_id}/finalise")
    assert status == 200, body
    assert body["result"]["stopped"] == "COMPLETED"
    assert body["state"] == sess.COMPLETED
    assert all(body["result"]["conditions"].values()), body["result"]["conditions"]

    # 7. the completed copy really is a separate, correctly filled file
    status, pdf_bytes = client.get(f"/api/sessions/{session_id}/documents/{completed_id}", raw=True)
    assert status == 200
    assert pdf_bytes.startswith(b"%PDF-"), "a real PDF came back over real HTTP"

    downloaded = tmp = Path(root) / "downloaded.pdf"
    tmp.write_bytes(pdf_bytes)
    filled = {f["name"]: f["value"] for f in fields.detect(str(downloaded))}
    assert filled == {"worker_name": "Sam Naylor",
                      "site_address": "12 Rundle St, Adelaide",
                      "induction_complete_declaration": "I have completed the site induction"}

    # 8. the original is untouched, byte for byte
    conn = store.connect(root)
    try:
        original = documents.documents_for(conn, session_id, role="original")[0]
        assert Path(original["path"]).read_bytes() == form_pdf.read_bytes()
        assert documents.original_intact(conn, session_id) is True
        assert original["path"] != documents.documents_for(conn, session_id, role="completed")[0]["path"]
    finally:
        conn.close()

    # 9. the audit trail records what actually happened, in order
    status, view = client.get(f"/api/sessions/{session_id}")
    kinds = [e["kind"] for e in view["audit_trail"]]
    for expected in ("session_created", "original_stored", "fields_detected", "price_locked",
                     "information_supplied", "action_required", "approval_recorded",
                     "approval_used", "completed_copy_written", "completed_copy_attested"):
        assert expected in kinds, f"{expected} missing from the audit trail: {kinds}"
    assert kinds.index("action_required") < kinds.index("completed_copy_written"), \
        "the gate must be recorded before the work it gates"


# =====================================================================
# The Trust Gate, enforced in the backend
# =====================================================================

def test_an_approval_does_not_authorise_a_different_payload(live, form_pdf):
    """The whole point of hashing the payload: approve these values, and
    only these values may be executed."""
    client, root = live
    session_id = start(client)
    upload(client, session_id, form_pdf)
    client.post(f"/api/sessions/{session_id}/price", {"price_cents": 5000, "scope": "one document"})
    client.post(f"/api/sessions/{session_id}/information", {"field": "worker_name", "value": "Sam Naylor"})
    client.post(f"/api/sessions/{session_id}/information",
                {"field": "induction_complete_declaration", "value": "I have completed the site induction"})

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    digest = body["result"]["payload_hash"]
    client.post(f"/api/sessions/{session_id}/approval",
                {"action": "generate_completed", "payload_hash": digest, "decision": "APPROVED"})

    # the customer now changes their name — the approved payload is stale
    client.post(f"/api/sessions/{session_id}/information",
                {"field": "worker_name", "value": "Someone Else Entirely"})

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    assert status == 200
    assert body["result"]["stopped"] == "ACTION_REQUIRED", \
        "an approval for the old values must not authorise the new ones"
    assert body["result"]["payload_hash"] != digest

    conn = store.connect(root)
    try:
        assert documents.documents_for(conn, session_id, role="completed") == [], \
            "nothing may have been written for an unapproved payload"
    finally:
        conn.close()


def test_an_approval_is_single_use(live, form_pdf):
    client, root = live
    session_id = start(client)
    upload(client, session_id, form_pdf, known_values={"worker_name": "Sam Naylor"})
    client.post(f"/api/sessions/{session_id}/price", {"price_cents": 5000, "scope": "one document"})
    client.post(f"/api/sessions/{session_id}/information",
                {"field": "induction_complete_declaration", "value": "I have completed the site induction"})

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    digest = body["result"]["payload_hash"]

    conn = store.connect(root)
    try:
        payload = trust_gate.pending(conn, session_id)["payload"]
        trust_gate.decide(conn, session_id, "generate_completed", digest, "APPROVED", "sam")
        assert trust_gate.check(conn, session_id, "generate_completed", payload)
        with pytest.raises(trust_gate.GateHeld):
            trust_gate.check(conn, session_id, "generate_completed", payload)
    finally:
        conn.close()


def test_declining_is_a_real_outcome_not_an_error(live, form_pdf):
    client, root = live
    session_id = start(client)
    upload(client, session_id, form_pdf, known_values={"worker_name": "Sam Naylor"})
    client.post(f"/api/sessions/{session_id}/price", {"price_cents": 5000, "scope": "one document"})
    client.post(f"/api/sessions/{session_id}/information",
                {"field": "induction_complete_declaration", "value": "I have completed the site induction"})

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    digest = body["result"]["payload_hash"]
    client.post(f"/api/sessions/{session_id}/approval",
                {"action": "generate_completed", "payload_hash": digest, "decision": "DECLINED"})

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    assert status == 200
    assert body["result"]["stopped"] == "DECLINED"
    assert body["state"] == sess.DECLINED

    conn = store.connect(root)
    try:
        assert documents.documents_for(conn, session_id, role="completed") == []
    finally:
        conn.close()

    # a terminal session cannot be restarted
    status, body = client.post(f"/api/sessions/{session_id}/execute")
    assert status == 409
    assert "DECLINED" in body["error"]


def test_a_customer_cannot_approve_something_they_were_never_shown(live, form_pdf):
    """Pre-approving a payload the engine never asked about would let a
    caller open the gate before the gate exists."""
    client, _ = live
    session_id = start(client)
    upload(client, session_id, form_pdf, known_values={"worker_name": "Sam Naylor"})
    client.post(f"/api/sessions/{session_id}/price", {"price_cents": 5000, "scope": "one document"})
    client.post(f"/api/sessions/{session_id}/information",
                {"field": "induction_complete_declaration", "value": "I have completed the site induction"})

    invented = trust_gate.payload_hash("generate_completed", {"fields": [], "declarations": []})
    status, body = client.post(f"/api/sessions/{session_id}/approval",
                               {"action": "generate_completed", "payload_hash": invented,
                                "decision": "APPROVED"})
    assert status == 400
    assert "never" in body["error"] or "only decide" in body["error"]


def test_two_concurrent_executions_spend_one_approval_once(live, form_pdf):
    """A single approval must authorise a single execution even when two
    real requests race for it."""
    import threading

    client, root = live
    # The race window is small, so run it over several real sessions: one
    # double-spend anywhere is a failure.
    for attempt in range(8):
        session_id = start(client)
        pdf = form_pdf.with_name(f"induction-{attempt}.pdf")
        pdf.write_bytes(form_pdf.read_bytes())
        upload(client, session_id, pdf, known_values={"worker_name": "Sam Naylor"})
        client.post(f"/api/sessions/{session_id}/price", {"price_cents": 5000, "scope": "one document"})
        client.post(f"/api/sessions/{session_id}/information",
                    {"field": "induction_complete_declaration",
                     "value": "I have completed the site induction"})
        status, body = client.post(f"/api/sessions/{session_id}/execute")
        digest = body["result"]["payload_hash"]
        client.post(f"/api/sessions/{session_id}/approval",
                    {"action": "generate_completed", "payload_hash": digest, "decision": "APPROVED"})

        results = []
        barrier = threading.Barrier(2)

        def fire():
            barrier.wait()
            results.append(client.post(f"/api/sessions/{session_id}/execute"))

        threads = [threading.Thread(target=fire) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        conn = store.connect(root)
        try:
            completed = documents.documents_for(conn, session_id, role="completed")
        finally:
            conn.close()
        assert len(completed) == 1, \
            f"attempt {attempt}: one approval produced {len(completed)} completed copies: {results}"


# =====================================================================
# Workflow containment
# =====================================================================

def test_a_read_only_workflow_cannot_fill_anything(live, form_pdf):
    client, root = live
    session_id = start(client, workflow_id="read_only_review")
    status, body = upload(client, session_id, form_pdf,
                          known_values={"worker_name": "Sam Naylor"})
    assert status == 200
    client.post(f"/api/sessions/{session_id}/price", {"price_cents": 0, "scope": "review only"})
    client.post(f"/api/sessions/{session_id}/waive", {"field": "induction_complete_declaration"})

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    assert status == 409
    assert "does not permit 'fill_field'" in body["error"]

    conn = store.connect(root)
    try:
        assert documents.documents_for(conn, session_id, role="completed") == []
    finally:
        conn.close()


def test_the_engine_refuses_a_workflow_that_is_not_defined(live):
    client, _ = live
    status, body = client.post("/api/sessions", {"workflow_id": "do_whatever_i_say", "customer": "sam"})
    assert status == 400
    assert "no such workflow" in body["error"]


@pytest.mark.parametrize("kwargs, expected", [
    (dict(workflow_id="w", name="w", permitted_actions=("teleport",),
          completion_conditions=("x",)), "no code performs those actions"),
    (dict(workflow_id="w", name="w", permitted_actions=("fill_field",),
          prohibited_actions=("fill_field",), completion_conditions=("x",)),
     "both permitted and prohibited"),
    (dict(workflow_id="w", name="w", permitted_actions=("fill_field",),
          completion_conditions=()), "can never be proven done"),
])
def test_an_inconsistent_workflow_is_refused_at_definition_time(kwargs, expected):
    with pytest.raises(workflow.WorkflowError) as err:
        workflow.Workflow(**kwargs)
    assert expected in str(err.value)


# =====================================================================
# Lifecycle, price, storage
# =====================================================================

def test_execution_is_refused_before_the_price_is_locked(live, form_pdf):
    client, _ = live
    session_id = start(client)
    upload(client, session_id, form_pdf, known_values={"worker_name": "Sam Naylor"})
    client.post(f"/api/sessions/{session_id}/information",
                {"field": "induction_complete_declaration", "value": "I have completed the site induction"})

    status, view = client.get(f"/api/sessions/{session_id}")
    assert view["session"]["state"] != sess.READY
    assert view["session"]["price_cents"] is None

    status, body = client.post(f"/api/sessions/{session_id}/execute")
    assert status == 409
    assert "must be READY" in body["error"]


def test_an_original_is_write_once(live, form_pdf):
    client, _ = live
    session_id = start(client)
    assert upload(client, session_id, form_pdf)[0] == 200
    status, body = upload(client, session_id, form_pdf)
    assert status == 409
    assert "write-once" in body["error"]


@pytest.mark.parametrize("filename", ["../../escaped.pdf", "/etc/passwd.pdf", "sub/dir.pdf",
                                      "..\\windows.pdf"])
def test_a_filename_cannot_escape_the_session_directory(live, form_pdf, filename, tmp_path):
    client, root = live
    session_id = start(client)
    status, body = client.post(f"/api/sessions/{session_id}/document", {
        "filename": filename,
        "content_base64": base64.b64encode(form_pdf.read_bytes()).decode("ascii")})
    assert status == 409, body
    assert "not a filename" in body["error"]
    written = [p for p in Path(root).rglob("*") if p.is_file() and p.suffix == ".pdf"]
    assert written == [], f"nothing may have been written: {written}"


def test_an_oversized_document_is_refused_before_it_is_stored(live, monkeypatch):
    client, root = live
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1024)
    session_id = start(client)
    status, body = client.post(f"/api/sessions/{session_id}/document", {
        "filename": "big.pdf",
        "content_base64": base64.b64encode(b"%PDF-1.4\n" + b"x" * 4096).decode("ascii")})
    assert status == 409
    assert "MAX_UPLOAD_BYTES" in body["error"]
    assert list((Path(root) / "sessions" / session_id).rglob("*.pdf")) == []


def test_a_corrupt_upload_is_a_client_error_not_a_crash(live):
    client, _ = live
    session_id = start(client)
    status, body = client.post(f"/api/sessions/{session_id}/document",
                               {"filename": "x.pdf", "content_base64": "not base64 at all!!"})
    assert status == 400
    assert "base64" in body["error"]


def test_illegal_lifecycle_moves_are_refused(live):
    client, root = live
    session_id = start(client)
    conn = store.connect(root)
    try:
        with pytest.raises(sess.LifecycleError) as err:
            sess.transition(conn, session_id, sess.COMPLETED)
        assert "not a lifecycle transition" in str(err.value)
    finally:
        conn.close()


def test_a_value_without_a_source_cannot_be_stored(live):
    client, root = live
    session_id = start(client)
    conn = store.connect(root)
    try:
        with pytest.raises(prov.ProvenanceError):
            sess.put_field(conn, session_id, "f", "F", [0, 0, 1, 1], "a value", prov.DERIVED)
        with pytest.raises(prov.ProvenanceError):
            sess.put_field(conn, session_id, "f", "F", [0, 0, 1, 1], "a value", prov.MISSING)
    finally:
        conn.close()


# =====================================================================
# The API refuses what it should
# =====================================================================

def test_the_api_refuses_an_unauthenticated_request(live):
    client, _ = live
    anonymous = Client(client.base_url, token=None)
    status, body = anonymous.get("/api/health")
    assert status == 401
    assert body["error"] == "unauthorised"


def test_the_server_refuses_to_start_without_a_token(monkeypatch):
    monkeypatch.delenv(config.API_TOKEN_ENV_VAR, raising=False)
    with pytest.raises(RuntimeError) as err:
        api.serve(host="127.0.0.1", port=0, data_root=None, token=None)
    assert "refusing to serve an open API" in str(err.value)


def test_state_survives_a_server_restart(live, form_pdf, tmp_path):
    """The engine holds no session state in memory: a second server over
    the same data root sees exactly the same session."""
    client, root = live
    session_id = start(client)
    upload(client, session_id, form_pdf, known_values={"worker_name": "Sam Naylor"})
    status, before = client.get(f"/api/sessions/{session_id}")

    httpd, _ = api.serve(host="127.0.0.1", port=0, data_root=root, token=TOKEN)
    try:
        second = Client(f"http://{httpd.server_address[0]}:{httpd.server_address[1]}")
        status, after = second.get(f"/api/sessions/{session_id}")
        assert status == 200
        assert after["session"] == before["session"]
        assert after["fields"] == before["fields"]
    finally:
        httpd.shutdown()
        httpd.server_close()
