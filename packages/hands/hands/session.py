"""The session lifecycle, enforced.

CREATED -> INTAKE -> WAITING_FOR_INFORMATION -> READY -> EXECUTING ->
ACTION_REQUIRED -> REVIEW -> COMPLETED, with DECLINED / CANCELLED / FAILED
as the other terminal outcomes. The transition table below is the only way
a session's state changes; anything else raises. A declined approval lands
in DECLINED, which is a real outcome of the product, not a failure.
"""

import json
import time
import uuid

from . import provenance as prov
from . import shelf, store, workflow

CREATED = "CREATED"
INTAKE = "INTAKE"
WAITING_FOR_INFORMATION = "WAITING_FOR_INFORMATION"
READY = "READY"
EXECUTING = "EXECUTING"
ACTION_REQUIRED = "ACTION_REQUIRED"
REVIEW = "REVIEW"
COMPLETED = "COMPLETED"
DECLINED = "DECLINED"
CANCELLED = "CANCELLED"
FAILED = "FAILED"

TERMINAL = (COMPLETED, DECLINED, CANCELLED, FAILED)

TRANSITIONS = {
    CREATED: (INTAKE, CANCELLED),
    INTAKE: (WAITING_FOR_INFORMATION, READY, CANCELLED, FAILED),
    WAITING_FOR_INFORMATION: (INTAKE, READY, CANCELLED, FAILED),
    READY: (EXECUTING, CANCELLED),
    EXECUTING: (ACTION_REQUIRED, WAITING_FOR_INFORMATION, REVIEW, DECLINED, FAILED),
    ACTION_REQUIRED: (EXECUTING, DECLINED, CANCELLED, FAILED),
    REVIEW: (COMPLETED, EXECUTING, ACTION_REQUIRED, DECLINED, CANCELLED, FAILED),
    COMPLETED: (),
    DECLINED: (),
    CANCELLED: (),
    FAILED: (),
}


class LifecycleError(RuntimeError):
    """An attempt to move a session somewhere the lifecycle does not go."""


def create(conn, workflow_id, customer):
    """Opens a real session in CREATED against a defined workflow. An
    unknown workflow id is refused here — the engine never accepts a
    free-form instruction."""
    wf = workflow.get(workflow_id)
    session_id = f"HS-{uuid.uuid4().hex[:12]}"
    now = time.time()
    conn.execute(
        "INSERT INTO sessions (id, workflow_id, customer, state, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, wf.workflow_id, customer, CREATED, now, now))
    conn.commit()
    shelf.audit_trail.record(conn, "sessions", session_id, "create", None,
                             {"workflow_id": wf.workflow_id, "customer": customer, "state": CREATED})
    log(conn, session_id, "session_created", {"workflow_id": wf.workflow_id, "customer": customer})
    return session_id


def get(conn, session_id):
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise LifecycleError(f"no such session {session_id!r}")
    return dict(row)


def transition(conn, session_id, to_state, outcome=None, failure_reason=None):
    """The only writer of sessions.state. Refuses any move the table above
    does not allow, and refuses to move a terminal session at all."""
    current = get(conn, session_id)
    from_state = current["state"]
    if from_state in TERMINAL:
        raise LifecycleError(
            f"{session_id} is already {from_state} — a terminal session cannot move to {to_state}")
    if to_state not in TRANSITIONS[from_state]:
        raise LifecycleError(
            f"{session_id}: {from_state} -> {to_state} is not a lifecycle transition "
            f"(from {from_state} you may go to {list(TRANSITIONS[from_state])})")
    now = time.time()
    conn.execute(
        "UPDATE sessions SET state = ?, outcome = COALESCE(?, outcome), "
        "failure_reason = COALESCE(?, failure_reason), updated_at = ? WHERE id = ?",
        (to_state, outcome, failure_reason, now, session_id))
    conn.commit()
    shelf.audit_trail.record(conn, "sessions", session_id, "edit",
                             {"state": from_state}, {"state": to_state})
    log(conn, session_id, "state_change", {"from": from_state, "to": to_state,
                                           "failure_reason": failure_reason})
    return to_state


def log(conn, session_id, kind, detail):
    """One line of the customer-visible audit trail, timestamped for real."""
    conn.execute("INSERT INTO events (session_id, at, kind, detail) VALUES (?, ?, ?, ?)",
                 (session_id, time.time(), kind, json.dumps(detail, sort_keys=True)))
    conn.commit()


def trail(conn, session_id):
    rows = conn.execute(
        "SELECT at, kind, detail FROM events WHERE session_id = ? ORDER BY id ASC",
        (session_id,)).fetchall()
    return [{"at": r["at"], "kind": r["kind"], "detail": json.loads(r["detail"])} for r in rows]


# ---------------------------------------------------------------------
# Price, locked before execution
# ---------------------------------------------------------------------

def lock_price(conn, session_id, price_cents, scope):
    """Locks the quoted price against a named scope. Execution checks this
    lock; it is not decoration."""
    if price_cents is None or price_cents < 0:
        raise LifecycleError("a locked price must be a real, non-negative amount")
    now = time.time()
    conn.execute("UPDATE sessions SET price_cents = ?, price_scope = ?, price_locked_at = ?, "
                 "updated_at = ? WHERE id = ?", (int(price_cents), scope, now, now, session_id))
    conn.commit()
    log(conn, session_id, "price_locked", {"price_cents": int(price_cents), "scope": scope})


def requote(conn, session_id, new_price_cents, new_scope, reason):
    """Scope changed materially mid-session: stop, show the revised scope
    and price, and wait. Never a silent increase."""
    current = get(conn, session_id)
    log(conn, session_id, "requote_required",
        {"was_cents": current["price_cents"], "now_cents": int(new_price_cents),
         "was_scope": current["price_scope"], "now_scope": new_scope, "reason": reason})
    conn.execute("UPDATE sessions SET price_cents = NULL, price_scope = ?, price_locked_at = NULL, "
                 "updated_at = ? WHERE id = ?", (new_scope, time.time(), session_id))
    conn.commit()


# ---------------------------------------------------------------------
# Fields
# ---------------------------------------------------------------------

def put_field(conn, session_id, name, label, rect, value, provenance, source=None, waived=False):
    """Writes one field's real state. Provenance is validated before the
    row lands, so an unaccountable value cannot be stored at all."""
    prov.check(provenance, value, source)
    conn.execute(
        "INSERT INTO fields (session_id, name, label, rect, value, provenance, source, waived, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(session_id, name) DO UPDATE SET label=excluded.label, rect=excluded.rect, "
        "value=excluded.value, provenance=excluded.provenance, source=excluded.source, "
        "waived=excluded.waived, updated_at=excluded.updated_at",
        (session_id, name, label, json.dumps(rect), value or "", provenance, source,
         1 if waived else 0, time.time()))
    conn.commit()


def fields(conn, session_id):
    rows = conn.execute(
        "SELECT name, label, rect, value, provenance, source, waived FROM fields "
        "WHERE session_id = ? ORDER BY rowid ASC", (session_id,)).fetchall()
    return [{"name": r["name"], "label": r["label"], "rect": json.loads(r["rect"]),
             "value": r["value"], "provenance": r["provenance"], "source": r["source"],
             "waived": bool(r["waived"])} for r in rows]


def blocking_fields(conn, session_id):
    """Everything that stops execution: still MISSING, or a declaration
    the customer has to approve. Waived fields do not block."""
    return [f for f in fields(conn, session_id)
            if not f["waived"] and prov.blocks_execution(f["provenance"])]
