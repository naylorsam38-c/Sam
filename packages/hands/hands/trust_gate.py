"""The Trust Gate — backend-enforced.

A frontend button alone is not authorisation. The gate is a query against
the real database, made by the engine at the moment of execution, and it
passes only when there is an APPROVED decision that:

  * belongs to this session and this action,
  * carries the hash of exactly the payload about to be executed,
  * has not expired, and
  * has not already been used.

So approving "fill the name field with SAM NAYLOR" does not authorise
filling it with anything else, and one approval authorises one execution.
A DECLINED decision is honoured as a real customer outcome, not retried.
"""

import hashlib
import json
import time
import uuid

from . import config, session as sess

APPROVED = "APPROVED"
DECLINED = "DECLINED"


class GateHeld(Exception):
    """Execution stopped because the customer has not approved this exact
    action yet. Carries what they are being asked to approve."""

    def __init__(self, action, payload, payload_hash):
        super().__init__(f"ACTION REQUIRED: {action} awaits the customer's approval")
        self.action = action
        self.payload = payload
        self.payload_hash = payload_hash


class GateDeclined(Exception):
    """The customer declined. Not an error in the system — an outcome."""

    def __init__(self, action, payload_hash):
        super().__init__(f"declined by the customer: {action}")
        self.action = action
        self.payload_hash = payload_hash


def payload_hash(action, payload):
    """A stable hash over exactly what will be executed. Any change to the
    payload changes the hash, which invalidates an approval given for the
    older payload."""
    canonical = json.dumps({"action": action, "payload": payload}, sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def request(conn, session_id, action, payload):
    """Records that the customer is being asked, and moves the session to
    ACTION_REQUIRED. Returns the hash they will be approving."""
    digest = payload_hash(action, payload)
    sess.log(conn, session_id, "action_required",
             {"action": action, "payload": payload, "payload_hash": digest})
    state = sess.get(conn, session_id)["state"]
    if state != sess.ACTION_REQUIRED:
        sess.transition(conn, session_id, sess.ACTION_REQUIRED)
    return digest


def decide(conn, session_id, action, digest, decision, decided_by):
    """Writes the customer's real decision. This is the only thing that
    can open the gate — and writing it is not the same as passing it: the
    engine still re-checks at execution time."""
    if decision not in (APPROVED, DECLINED):
        raise ValueError(f"decision must be {APPROVED} or {DECLINED}, got {decision!r}")
    asked = [e for e in sess.trail(conn, session_id)
             if e["kind"] == "action_required"
             and e["detail"]["action"] == action and e["detail"]["payload_hash"] == digest]
    if not asked:
        raise ValueError(
            "no approval was requested for that payload — a customer can only decide on something "
            "the engine actually showed them")
    approval_id = f"AP-{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO approvals (id, session_id, action, payload_hash, decision, decided_by, decided_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (approval_id, session_id, action, digest, decision, decided_by, time.time()))
    conn.commit()
    sess.log(conn, session_id, "approval_recorded",
             {"action": action, "decision": decision, "payload_hash": digest, "by": decided_by})
    return approval_id


def check(conn, session_id, action, payload, consume=True):
    """The enforcement point. Called by the engine immediately before it
    acts, with the payload it is actually about to act on."""
    digest = payload_hash(action, payload)
    row = conn.execute(
        "SELECT id, decision, decided_at, consumed_at FROM approvals "
        "WHERE session_id = ? AND action = ? AND payload_hash = ? "
        "ORDER BY decided_at DESC LIMIT 1",
        (session_id, action, digest)).fetchone()

    if row is None:
        raise GateHeld(action, payload, digest)
    if row["decision"] == DECLINED:
        raise GateDeclined(action, digest)
    if row["consumed_at"] is not None:
        raise GateHeld(action, payload, digest)
    age = time.time() - row["decided_at"]
    if age > config.APPROVAL_TTL_SECONDS:
        raise GateHeld(action, payload, digest)

    if consume:
        # Conditional update, so two concurrent executions cannot both spend
        # the same approval: exactly one of them changes a row.
        cursor = conn.execute(
            "UPDATE approvals SET consumed_at = ? WHERE id = ? AND consumed_at IS NULL",
            (time.time(), row["id"]))
        conn.commit()
        if cursor.rowcount != 1:
            raise GateHeld(action, payload, digest)
    sess.log(conn, session_id, "approval_used", {"action": action, "payload_hash": digest})
    return row["id"]


def pending(conn, session_id):
    """What the customer is currently being asked to approve, if anything."""
    events = [e for e in sess.trail(conn, session_id) if e["kind"] == "action_required"]
    if not events:
        return None
    latest = events[-1]["detail"]
    decided = conn.execute(
        "SELECT decision FROM approvals WHERE session_id = ? AND payload_hash = ?",
        (session_id, latest["payload_hash"])).fetchone()
    if decided is not None:
        return None
    return latest
