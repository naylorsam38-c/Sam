"""The execution engine.

It receives a session bound to a defined Workflow and drives it through
the lifecycle. It never receives an instruction from the customer: the
customer supplies information and makes approval decisions, and this
module decides what may happen next by reading the workflow and the
database.

The three things it will not do, enforced rather than documented:
  * act outside the workflow's permitted actions;
  * fill anything whose provenance is MISSING (it asks instead);
  * perform a gated action without a matching, unused, unexpired approval
    for exactly the payload it is about to execute.
"""

from . import config, documents, fields as field_detection
from . import provenance as prov
from . import session as sess, trust_gate, workflow


class NotPermitted(RuntimeError):
    """The workflow does not permit this action, so the engine will not do it."""


def _wf(conn, session_id):
    return workflow.get(sess.get(conn, session_id)["workflow_id"])


def _require_permitted(wf, action):
    if not wf.permits(action):
        raise NotPermitted(
            f"{wf.workflow_id} does not permit {action!r} "
            f"(permitted: {list(wf.permitted_actions)}, prohibited: {list(wf.prohibited_actions)})")


# ---------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------

def intake(conn, session_id, filename, data, known_values=None, root=None):
    """Stores the customer's document, reads its real fields, and records
    each one with a provenance. Returns the session's new state."""
    wf = _wf(conn, session_id)
    _require_permitted(wf, "read_document")
    sess.transition(conn, session_id, sess.INTAKE)

    document_id = documents.store_original(conn, session_id, filename, data, root=root)
    path = documents.get_document(conn, document_id)["path"]

    detected = field_detection.detect(path)
    classified = field_detection.classify(detected, known_values=known_values)
    for field in classified:
        sess.put_field(conn, session_id, field["name"], field["label"], field["rect"],
                       field["value"], field["provenance"], field["source"])
    sess.log(conn, session_id, "fields_detected",
             {"count": len(classified),
              "missing": [f["name"] for f in classified if f["provenance"] == prov.MISSING],
              "gated": [f["name"] for f in classified if f["provenance"] == prov.REQUIRES_APPROVAL]})
    return evaluate(conn, session_id), document_id


def supply(conn, session_id, name, value, supplied_by):
    """The customer answers one question. A value supplied for a field
    that makes a declaration in their name stays gated — supplying it is
    not the same as approving it."""
    existing = {f["name"]: f for f in sess.fields(conn, session_id)}
    if name not in existing:
        raise NotPermitted(f"{name!r} is not a field in this document — nothing is invented")
    field = existing[name]
    if config.is_declaration_field(name):
        provenance, source = prov.REQUIRES_APPROVAL, f"supplied by {supplied_by}, declaration"
    else:
        provenance, source = prov.SUPPLIED_BY_CUSTOMER, supplied_by
    sess.put_field(conn, session_id, name, field["label"], field["rect"], value, provenance, source)
    sess.log(conn, session_id, "information_supplied", {"field": name, "by": supplied_by})
    return evaluate(conn, session_id)


def waive(conn, session_id, name, waived_by):
    """The customer says a field stays empty. Recorded, not assumed."""
    existing = {f["name"]: f for f in sess.fields(conn, session_id)}
    if name not in existing:
        raise NotPermitted(f"{name!r} is not a field in this document")
    field = existing[name]
    sess.put_field(conn, session_id, name, field["label"], field["rect"], "", prov.MISSING,
                   None, waived=True)
    sess.log(conn, session_id, "field_waived", {"field": name, "by": waived_by})
    return evaluate(conn, session_id)


def evaluate(conn, session_id):
    """Decides whether the session can execute yet, and moves it. Pure
    consequence of what is in the database — no judgement call."""
    current = sess.get(conn, session_id)
    if current["state"] in sess.TERMINAL:
        return current["state"]

    blocking = sess.blocking_fields(conn, session_id)
    missing = [f["name"] for f in blocking if f["provenance"] == prov.MISSING]

    if current["state"] == sess.WAITING_FOR_INFORMATION and not missing:
        sess.transition(conn, session_id, sess.INTAKE)
        current = sess.get(conn, session_id)

    if missing:
        if current["state"] != sess.WAITING_FOR_INFORMATION:
            sess.transition(conn, session_id, sess.WAITING_FOR_INFORMATION)
            sess.log(conn, session_id, "information_required", {"fields": missing})
        return sess.WAITING_FOR_INFORMATION

    if config.REQUIRE_PRICE_LOCK and current["price_locked_at"] is None:
        sess.log(conn, session_id, "price_lock_required",
                 {"reason": "the price is shown and locked before anything executes"})
        return current["state"]

    if current["state"] in (sess.INTAKE, sess.WAITING_FOR_INFORMATION):
        sess.transition(conn, session_id, sess.READY)
    return sess.get(conn, session_id)["state"]


# ---------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------

def execute(conn, session_id, root=None):
    """Runs the workflow as far as it can go without the customer.

    Returns a dict describing where it stopped and why. It stops for
    exactly three reasons: information is missing, an approval is needed,
    or the work is finished and waiting for review.
    """
    wf = _wf(conn, session_id)
    state = sess.get(conn, session_id)["state"]

    if state == sess.READY:
        sess.transition(conn, session_id, sess.EXECUTING)
    elif state == sess.ACTION_REQUIRED:
        sess.transition(conn, session_id, sess.EXECUTING)
    elif state != sess.EXECUTING:
        raise NotPermitted(f"a session in {state} cannot execute — it must be READY first")

    current = sess.fields(conn, session_id)
    missing = [f["name"] for f in current if f["provenance"] == prov.MISSING and not f["waived"]]
    if missing:
        sess.transition(conn, session_id, sess.WAITING_FOR_INFORMATION)
        sess.log(conn, session_id, "information_required", {"fields": missing})
        return {"stopped": "WAITING_FOR_INFORMATION", "missing": missing}

    _require_permitted(wf, "fill_field")
    gated = [f for f in current if f["provenance"] == prov.REQUIRES_APPROVAL and not f["waived"]]

    payload = {"fields": [{"name": f["name"], "value": f["value"], "provenance": f["provenance"]}
                          for f in current if not f["waived"]],
               "declarations": [f["name"] for f in gated]}

    _require_permitted(wf, "generate_completed")
    try:
        trust_gate.check(conn, session_id, "generate_completed", payload)
    except trust_gate.GateHeld as held:
        trust_gate.request(conn, session_id, held.action, held.payload)
        return {"stopped": "ACTION_REQUIRED", "action": held.action,
                "payload": held.payload, "payload_hash": held.payload_hash}
    except trust_gate.GateDeclined as declined:
        sess.transition(conn, session_id, sess.DECLINED, outcome="DECLINED")
        sess.log(conn, session_id, "declined_by_customer", {"action": declined.action})
        return {"stopped": "DECLINED", "action": declined.action}

    original = documents.documents_for(conn, session_id, role="original")[0]
    for field in current:
        sess.log(conn, session_id, "field_filled",
                 {"field": field["name"], "provenance": field["provenance"],
                  "source": field["source"], "waived": field["waived"]})
    completed_id = documents.write_completed(conn, session_id, original["id"], current,
                                             title=original["filename"], root=root)
    sess.transition(conn, session_id, sess.REVIEW)
    return {"stopped": "REVIEW", "completed_document_id": completed_id}


def finalise(conn, session_id):
    """The customer has reviewed the completed copy. Attesting it is its
    own gated action over that copy's real bytes, so an approval given for
    a different document cannot finish this one."""
    wf = _wf(conn, session_id)
    state = sess.get(conn, session_id)["state"]
    if state not in (sess.REVIEW, sess.ACTION_REQUIRED):
        raise NotPermitted(f"a session in {state} has nothing to finalise")

    completed = documents.documents_for(conn, session_id, role="completed")
    if not completed:
        raise NotPermitted("there is no completed copy to finalise")
    document = completed[-1]
    payload = {"document_id": document["id"], "sha256": document["sha256"]}

    _require_permitted(wf, "sign_completed")
    try:
        trust_gate.check(conn, session_id, "sign_completed", payload)
    except trust_gate.GateHeld as held:
        trust_gate.request(conn, session_id, held.action, held.payload)
        return {"stopped": "ACTION_REQUIRED", "action": held.action,
                "payload": held.payload, "payload_hash": held.payload_hash}
    except trust_gate.GateDeclined as declined:
        sess.transition(conn, session_id, sess.DECLINED, outcome="DECLINED")
        sess.log(conn, session_id, "declined_by_customer", {"action": declined.action})
        return {"stopped": "DECLINED", "action": declined.action}

    if state == sess.ACTION_REQUIRED:
        sess.transition(conn, session_id, sess.EXECUTING)
        sess.transition(conn, session_id, sess.REVIEW)

    documents.attest(conn, document["id"])
    conditions = verify_completion(conn, session_id)
    if not all(conditions.values()):
        sess.transition(conn, session_id, sess.FAILED, outcome="FAILED",
                        failure_reason=f"completion conditions not met: {conditions}")
        return {"stopped": "FAILED", "conditions": conditions}

    sess.transition(conn, session_id, sess.COMPLETED, outcome="COMPLETED")
    return {"stopped": "COMPLETED", "conditions": conditions,
            "completed_document_id": document["id"]}


def cancel(conn, session_id, by):
    sess.log(conn, session_id, "cancelled", {"by": by})
    return sess.transition(conn, session_id, sess.CANCELLED, outcome="CANCELLED")


def verify_completion(conn, session_id):
    """Checks the workflow's own completion conditions against the real
    files and the real database. This is what 'done' means here."""
    wf = _wf(conn, session_id)
    current = sess.fields(conn, session_id)
    completed = documents.documents_for(conn, session_id, role="completed")
    originals = documents.documents_for(conn, session_id, role="original")

    results = {}
    for condition in wf.completion_conditions:
        if condition.startswith("every detected field"):
            results[condition] = all(f["waived"] or f["value"] for f in current)
        elif condition.startswith("a completed copy exists"):
            results[condition] = bool(completed) and all(
                c["path"] != o["path"] for c in completed for o in originals)
        elif condition.startswith("the original document"):
            results[condition] = documents.original_intact(conn, session_id)
        elif condition.startswith("the completed copy carries an attestation"):
            results[condition] = bool(completed) and documents.attestation_valid(conn, completed[-1]["id"])
        elif condition.startswith("every field in the document has been listed"):
            listed = [e for e in sess.trail(conn, session_id) if e["kind"] == "fields_detected"]
            results[condition] = bool(listed) and listed[-1]["detail"]["count"] == len(current)
        else:  # a condition nobody wrote code for must not silently pass
            results[condition] = False
    return results
