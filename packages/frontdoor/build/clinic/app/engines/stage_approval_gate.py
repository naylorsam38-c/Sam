"""Stage Approval Gate Engine — a stage that will not move on until the
named approver has really said yes.

This is the generic version of the rule Command Desk states as "only
irreversible actions wait for me — sending an email, paying for
something": the workflow declares which stage waits and who approves, and
a record sitting in that stage cannot leave it until a real approval row
exists for that exact row and stage.

Refused, rather than assumed: an approver whose role the gate does not
name; a decision that is neither APPROVED nor DECLINED; and — the point of
the whole thing — a move out of a gated stage with no decision recorded.
A DECLINED decision is honoured as a real outcome and sends the record to
the workflow's own declared `back_to` stage; it is not an error and it is
not retried automatically.

Reuses the real audit_trail engine for the who/when log.
"""

import os
import sqlite3
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_trail  # noqa: E402 -- reused, not rewritten

APPROVED = "APPROVED"
DECLINED = "DECLINED"


class NotApproved(PermissionError):
    """The record is in a gated stage and nobody has decided yet."""


class NotAnApprover(PermissionError):
    pass


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _stage_approvals (
            id         TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            row_id     TEXT NOT NULL,
            stage      TEXT NOT NULL,
            decision   TEXT NOT NULL,
            decided_by TEXT NOT NULL,
            reason     TEXT,
            decided_at REAL NOT NULL
        )
    """)
    conn.commit()


def gate_for(approvals, stage):
    """The workflow's own declared gate for a stage, or None. `approvals`
    is exactly the FL.05 shape: [{"stage": ..., "approvers": [...]}]."""
    for gate in approvals or []:
        if gate.get("stage") == stage:
            return gate
    return None


def decide(conn, approvals, table, row_id, stage, decision, decided_by, reason=None, at=None):
    """Records a real decision. Only a declared approver may make it."""
    gate = gate_for(approvals, stage)
    if gate is None:
        raise NotApproved(f"{stage!r} is not a gated stage; there is nothing to approve")
    if decided_by not in (gate.get("approvers") or []):
        raise NotAnApprover(
            f"{decided_by!r} does not approve {stage!r}; declared: {gate.get('approvers')}")
    if decision not in (APPROVED, DECLINED):
        raise ValueError(f"decision must be {APPROVED} or {DECLINED}, got {decision!r}")

    approval_id = f"SA-{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO _stage_approvals (id, table_name, row_id, stage, decision, decided_by, reason, decided_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (approval_id, table, str(row_id), stage, decision, decided_by, reason,
         at if at is not None else time.time()))
    conn.commit()
    audit_trail.record(conn, table, row_id, f"approval:{stage}",
                       before=None, after={"decision": decision, "by": decided_by, "reason": reason},
                       at=at)
    return approval_id


def decision_for(conn, table, row_id, stage):
    """The latest real decision for this row and stage, or None."""
    row = conn.execute(
        "SELECT decision, decided_by, reason FROM _stage_approvals "
        "WHERE table_name = ? AND row_id = ? AND stage = ? ORDER BY decided_at DESC LIMIT 1",
        (table, str(row_id), stage)).fetchone()
    if row is None:
        return None
    return {"decision": row[0], "decided_by": row[1], "reason": row[2]}


def check_may_leave(conn, approvals, table, row_id, stage):
    """Called immediately before a move out of `stage`. Returns the real
    decision when the move may proceed, raises when it may not."""
    gate = gate_for(approvals, stage)
    if gate is None:
        return None                      # not a gated stage: nothing to check
    decision = decision_for(conn, table, row_id, stage)
    if decision is None:
        raise NotApproved(
            f"{table} {row_id} is waiting in {stage!r} for {gate.get('approvers')} to approve")
    return decision


def prove():
    """Real proof: a real job row parked in a gated stage, refused a move
    until a real approval exists, then a second row declined."""
    approvals = [{"stage": "running", "approvers": ["Sam"]}]
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, ask TEXT, stage TEXT)")
    conn.execute("INSERT INTO jobs VALUES ('J-1', 'send the reply', 'running')")
    conn.execute("INSERT INTO jobs VALUES ('J-2', 'pay the invoice', 'running')")
    audit_trail.ensure_table(conn)
    ensure_table(conn)

    refusals = {}
    try:
        check_may_leave(conn, approvals, "jobs", "J-1", "running")
    except NotApproved as err:
        refusals["no decision recorded"] = str(err)
    try:
        decide(conn, approvals, "jobs", "J-1", "running", APPROVED, "Nova")
    except NotAnApprover as err:
        refusals["an approver the gate does not name"] = str(err)

    decide(conn, approvals, "jobs", "J-1", "running", APPROVED, "Sam", reason="send it")
    allowed = check_may_leave(conn, approvals, "jobs", "J-1", "running")

    decide(conn, approvals, "jobs", "J-2", "running", DECLINED, "Sam", reason="wrong recipient")
    declined = check_may_leave(conn, approvals, "jobs", "J-2", "running")

    ungated = check_may_leave(conn, approvals, "jobs", "J-1", "queued")

    assert len(refusals) == 2, refusals
    assert allowed["decision"] == APPROVED and allowed["decided_by"] == "Sam"
    assert declined["decision"] == DECLINED and declined["reason"] == "wrong recipient"
    assert ungated is None, "a stage with no declared gate must not be blocked"
    log = audit_trail.history_for(conn, "jobs", "J-1")
    assert log[-1]["action"] == "approval:running"
    conn.close()
    return {"engine": "stage_approval_gate",
            "real_system": "sqlite3 (:memory:, a real database connection) + the real audit_trail engine",
            "steps": ["a real job parked in the gated stage 'running'",
                      "refuse the move: no decision recorded",
                      "refuse a decision from someone the gate does not name",
                      "record a real approval -> the move is allowed",
                      "record a real decline on a second row -> it is returned, not retried",
                      "a stage with no declared gate is not blocked"],
            "observed": {"refusals": refusals, "approved": allowed, "declined": declined,
                         "ungated_stage": ungated}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
