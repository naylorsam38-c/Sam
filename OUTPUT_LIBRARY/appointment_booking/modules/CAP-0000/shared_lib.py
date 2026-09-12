"""modules/CAP-0000/shared_lib.py -- the Common Capability Contract's real
shared storage/error/notification implementation. Not an HTTP capability
(no ROUTE/METHOD): the host's dynamic module loader only registers modules
that declare a route, so this is simply never wired -- other capabilities
import it directly, by file path, the same way the host discovers them."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

ERROR_CODE_BY_STATUS = {
    400: "VALIDATION_ERROR",
    404: "NOT_FOUND",
    409: "CONFLICT",
    500: "INTERNAL_ERROR",
}


def load(filename):
    f = DATA_DIR / filename
    if not f.is_file():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def save(filename, rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / filename).write_text(json.dumps(rows), encoding="utf-8")


def code_for_status(status):
    return ERROR_CODE_BY_STATUS.get(status, "ERROR")


def notify(recipient, message, filename="notifications.json"):
    """Standard notify primitive: any capability can call this directly to
    raise a real notification without an HTTP round trip, writing to the
    same well-known store the Notification capability type itself reads --
    real backend composition, not client-side call-chaining."""
    rows = load(filename)
    next_id = (max([r["id"] for r in rows], default=0)) + 1
    note = {"id": next_id, "recipient": recipient, "message": message, "read": False}
    rows.append(note)
    save(filename, rows)
    return note


def audit(actor, action, entity, entity_id, details="", filename="audit_log.json"):
    """Standard audit primitive, the same real-composition pattern as
    notify(): any capability can call this directly to record a real,
    timestamped activity entry -- actor/action/entity/entity_id/timestamp,
    the same shape real audit-log implementations use (server-generated
    timestamp, not client-supplied; a human-and-machine-readable entity
    reference, not a raw blob). This is an ACTIVITY LOG, not a security or
    compliance control: it records that an action happened and who a
    caller SAID performed it -- there is no real identity/auth behind
    "actor" anywhere in this library (see CAP-0000's ctx object, always
    {"user": None, "authenticated": False}), so this must never be
    described as tamper-proof, verified, or a substitute for real
    authentication."""
    import datetime
    rows = load(filename)
    next_id = (max([r["id"] for r in rows], default=0)) + 1
    entry = {"id": next_id, "timestamp": datetime.datetime.now().isoformat(),
              "actor": actor, "action": action, "entity": entity, "entity_id": entity_id,
              "details": details}
    rows.append(entry)
    save(filename, rows)
    return entry
