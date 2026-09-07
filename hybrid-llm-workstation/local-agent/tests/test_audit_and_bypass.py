"""Spec section 21 Phase D acceptance items: verify the audit trail, and
verify a malicious/compromised caller (standing in for 'the cloud LLM')
cannot bypass policy just by attaching an approval_token or by knowing the
operation name without the shared secret.
"""

from agent.audit.store import AuditStore
from conftest import signed_request


def test_every_call_is_audited_regardless_of_outcome(client, settings, workspace):
    client.post("/execute", json=signed_request("read_file", {"path": str(workspace)}))  # denied, no token
    (workspace / "f.txt").write_text("x")
    client.post("/execute", json=signed_request("read_file", {"path": str(workspace / "f.txt")},
                                                approval_token="a"))  # completed
    bad = signed_request("read_file", {"path": str(workspace)})
    bad["signature"] = "deadbeef"
    client.post("/execute", json=bad)  # denied, bad auth

    records = AuditStore(settings.audit_db_path).all_records()
    assert len(records) == 3
    decisions = {r["decision"] for r in records}
    assert decisions == {"DENIED", "COMPLETED"}
    assert all(r["operation"] == "read_file" for r in records)


def test_forged_approval_token_cannot_bypass_the_signature_check(client, workspace):
    """An attacker without EXECUTION_AGENT_TOKEN cannot produce a valid
    signature no matter what else they attach to the request."""
    (workspace / "secret.txt").write_text("top secret")
    body = {
        "request_id": "attacker-1",
        "operation": "read_file",
        "parameters": {"path": str(workspace / "secret.txt")},
        "requested_by": "attacker",
        "timestamp": 1_900_000_000,
        "signature": "0" * 64,
        "approval_token": "i-approve-myself",
    }
    resp = client.post("/execute", json=body)
    assert resp.json()["status"] == "DENIED"


def test_approval_token_cannot_bypass_restricted_path_boundary(client, tmp_path):
    """Even a genuinely valid signature and a non-empty approval_token
    cannot get an out-of-bounds path past the RESTRICTED check — this is
    the literal 'defense in depth' the agent exists to provide."""
    outside = tmp_path.parent / "outside-workspace" / "passwd"
    body = signed_request("read_file", {"path": str(outside)}, approval_token="fully-approved-by-control-plane")
    resp = client.post("/execute", json=body)
    assert resp.json()["status"] == "DENIED"
    assert "outside allowed_paths" in resp.json()["stderr"]
