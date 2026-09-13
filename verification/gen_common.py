#!/usr/bin/env python3
"""
gen_common.py — shared, reusable machinery for generating real, non-fixture
build.py projects, factored out of gen_real_todo_app.py's own proven pattern
(round 7) so each additional real app type (of Sam's real 43-item
canonical_app_types.py list) is a declarative capability/template spec
instead of ~350 lines of hand-duplicated boilerplate per app.

Every record shape below (cap_record/impl_record/slot) is copied verbatim
from gen_real_todo_app.py, which itself copied gen_fixtures.py's shapes —
not reinvented, so the contract build.py actually validates stays identical
across every generated app. The host app (Flask + dynamic route-module
loader) is the same proven CAP-0100 convention, parameterized only by which
data file it points at and which HTML it serves.

This file has no import-time side effects — it only defines functions used
by per-app generator scripts.
"""
import json
import shutil
from pathlib import Path


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, obj):
    write(path, json.dumps(obj, indent=2))


CONTRACT_VERSION = "2.0"


def cap_record(cap_id, name, category, impl_ids, output_fields=(), required_input=(),
               side_effects=(), approval_ref="APPROVAL-CAP-REAL", dependencies=(),
               error_codes=(), data_access=(), requires_auth=False, context_fields=()):
    """The Common Capability Contract v2 record. §3.6's CAP_RECORD_KEYS is an
    EXACT top-level key match enforced by build.py's verify_registry_invariants
    -- so the new contract fields (data_access, context_fields, contract
    version) live nested inside the already free-form data_shape dict, never
    as new top-level keys, and error_codes populates the existing (previously
    always-empty) error_contract.error_codes field. No top-level shape change,
    so this is fully backward compatible with build.py's own pre-existing
    internal proving-table fixtures, which never populate these nested
    fields and are validated exactly as before."""
    return {
        "id": cap_id,
        "name": name,
        "category": category,
        "status": "active",
        "data_shape": {
            "input": {"required": list(required_input), "types": {}},
            "output": {"fields": list(output_fields), "types": {}},
            "nullable": [],
            "requires_auth": requires_auth,
            "security_constraints": {},
            "contract_version": CONTRACT_VERSION,
            # Which named entity/store this capability directly reads or
            # writes, and how -- declared, not hidden, so a real static
            # cross-check (verification/audit_dependency_graph.py) can catch
            # a capability that touches a file it never declared.
            "data_access": [dict(a) for a in data_access],
            # Identity/context fields this capability actually reads off the
            # real ctx object the host loader passes to any 2-arg handler
            # (see gen_common.py's _make_ctx()) -- e.g. "role" for a
            # required_role-gated capability. Empty for capabilities that
            # don't need identity at all, which is still most of them.
            "context_fields": list(context_fields),
        },
        # Real, checked dependencies on another capability's data/behaviour --
        # not decorative: build.py's stage1_assemble() refuses to build an
        # app that requires this capability without also requiring everything
        # listed here (found by real audit: a capability that silently reads
        # a sibling's data file with no declared dependency produces empty or
        # wrong output when reused without that sibling, instead of failing).
        # Every capability generated via AppBuilder.add_capability() declares
        # CAP-0000 (the shared storage/error library) here automatically,
        # since its generated code now imports it rather than duplicating it.
        "dependencies": list(dependencies),
        "permissions": [],
        "side_effects": list(side_effects),
        # Real declared error codes this capability can actually return,
        # derived from its own real input/lookup shape (see add_capability),
        # not a description of behaviour that doesn't exist.
        "error_contract": {"error_codes": list(error_codes)},
        "implementations": list(impl_ids),
        "qualification": {"status": "approved", "approved_by": "Sam", "approval_ref": approval_ref},
    }


def impl_record(impl_id, cap_id, entrypoint, status="active", version="1.0.0",
                 approval_ref="APPROVAL-IMPL-REAL"):
    return {
        "id": impl_id,
        "capability_id": cap_id,
        "status": status,
        "release": {"version": version, "commit": "gen_common.py", "approved": True,
                     "approval_ref": approval_ref},
        "source": {"repository": "shelf", "path": impl_id, "entrypoint": entrypoint},
        "dependencies": [],
        "tests": [],
        "rollback": {"previous_version": None},
    }


def slot(slot_id, target_cap, name, selector, side_effects=()):
    return {
        "slot_id": slot_id, "name": name, "target_capability": target_cap, "selector": selector,
        "expected_contract": {
            "required_input_fields": [], "input_types": {}, "output_fields": [],
            "output_types": {}, "nullable_fields": [], "permissions": [], "requires_auth": False,
            "dependencies": [], "handled_errors": [], "security_constraints": {},
            "side_effects": list(side_effects),
            "min_version": "1.0.0",
        },
    }


SHARED_LIB_CAP_ID = "CAP-0000"

# Cross-App Isolation Contract (CANONICAL_SPEC.md Part C.4): filenames that
# are exclusively internal state for CAP-0000's own primitive functions --
# create_session()/validate_session()/invalidate_session() ("auth_sessions.json")
# and save_blob()/load_blob()'s own default index ("blobs.json") -- and are
# NEVER passed as any capability's own data_filename by any generic engine
# in this file today (verified: zero occurrences). A domain capability that
# declares its own data_filename equal to one of these would silently share
# physical storage with a CAP-0000 primitive whose row shape it doesn't
# control, exactly the real, historical bug this project found the hard way
# (see B.8/C.4): a plain capability's "sessions.json" collided with the auth
# engine's own session store once "auth_sessions.json" existed, invisible
# until the full-library merge test forced them into one shared data/
# directory. This does NOT include "api_keys.json"/"share_tokens.json" --
# those ARE legitimately a capability's own data_filename, declared by their
# own owning engine (add_api_key_capability/add_share_token_capability) --
# blocking those would break real, working capabilities.
RESERVED_SHARED_LIB_FILENAMES = frozenset({"auth_sessions.json", "blobs.json"})

# The real, single-source implementation of load/save, error-code mapping,
# and the notify primitive -- written ONCE per app (as CAP-0000, a real
# shelf capability with no HTTP route of its own) and dynamically imported
# by every other capability's route.py, the same technique the host loader
# already uses to discover sibling modules. Before this, every capability
# duplicated its own copy of this exact code (proven byte-identical except
# the data filename); now there is one real copy per app, not N.
SHARED_LIB_SOURCE = '''"""modules/CAP-0000/shared_lib.py -- the Common Capability Contract's real
shared storage/error/notification implementation. Not an HTTP capability
(no ROUTE/METHOD): the host's dynamic module loader only registers modules
that declare a route, so this is simply never wired -- other capabilities
import it directly, by file path, the same way the host discovers them."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SECRETS_DIR = Path(__file__).resolve().parents[2] / "secrets"

ERROR_CODE_BY_STATUS = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
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


def save_blob(raw_bytes, content_type="application/octet-stream", filename_hint="", index_filename="blobs.json"):
    """Real binary storage, deliberately separate from the JSON-array data
    store every other capability uses: raw bytes are written to their own
    file under data/blobs/<id>, never base64-stuffed into a JSON array
    (which would force every unrelated load()/save() of that file to
    parse megabytes of base64 it doesn't need). A small JSON index record
    (id/content_type/filename/size/created_at) is kept in index_filename
    so a listing capability can show what exists without ever reading
    blob bytes. This closes the real, evidenced gap
    COVERAGE_EXPANSION_REPORT.md Part 5.4 named (recruitment CV upload,
    medical/government document submission, AI studio asset storage) --
    that report deferred it specifically because it needed a new storage
    primitive beside the JSON-file store, not because it couldn't be
    built; this is that primitive, built for real, not simulated."""
    blob_id = _secrets.token_urlsafe(16)
    blobs_dir = DATA_DIR / "blobs"
    blobs_dir.mkdir(parents=True, exist_ok=True)
    (blobs_dir / blob_id).write_bytes(raw_bytes)
    index = load(index_filename)
    record = {"id": blob_id, "content_type": content_type, "filename": filename_hint,
              "size": len(raw_bytes), "created_at": _datetime.datetime.now().isoformat()}
    index.append(record)
    save(index_filename, index)
    return record


def load_blob(blob_id, index_filename="blobs.json"):
    """Returns (raw_bytes, metadata_record), or (None, None) for an
    unknown id -- a real 404, not a silent empty file."""
    index = load(index_filename)
    record = next((r for r in index if r["id"] == blob_id), None)
    if record is None:
        return None, None
    blob_path = DATA_DIR / "blobs" / blob_id
    if not blob_path.is_file():
        return None, None
    return blob_path.read_bytes(), record


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
    reference, not a raw blob). This is an ACTIVITY LOG, not itself a
    security or compliance control: the `actor` string is whatever the
    calling capability passes in -- if that capability wants a VERIFIED
    actor rather than a claimed one, it must resolve it from a real ctx
    (see validate_session() below) and pass that, not trust a client-
    supplied name. This primitive does not do that resolution itself."""
    import datetime
    rows = load(filename)
    next_id = (max([r["id"] for r in rows], default=0)) + 1
    entry = {"id": next_id, "timestamp": datetime.datetime.now().isoformat(),
              "actor": actor, "action": action, "entity": entity, "entity_id": entity_id,
              "details": details}
    rows.append(entry)
    save(filename, rows)
    return entry


# ============================================================================
# Real identity/auth primitives. Built for the coverage-expansion round's
# authentication work package -- passwords are salted and hashed with
# PBKDF2-HMAC-SHA256 (stdlib `hashlib`, 200,000 iterations; no new
# dependency, matching every other primitive here), never stored or
# returned in plaintext. Sessions are random, unguessable tokens
# (`secrets.token_urlsafe`) with a real, server-checked expiry -- not a
# client-trusted claim. Stated plainly, not glossed over: this is real
# password/session security for a single-process, JSON-file-backed
# library, not a production identity platform -- there is no TLS, no
# rate-limiting on login attempts, no CSRF protection, and the session
# store itself is plain JSON on local disk (tokens are the only secret in
# it, and are only ever compared, never listed back to a caller). See
# COVERAGE_EXPANSION_REPORT.md's Part 4 findings for what a hardened
# version of this would still need.
# ============================================================================
import hashlib as _hashlib
import hmac as _hmac
import secrets as _secrets
import datetime as _datetime

_PBKDF2_ITERATIONS = 200_000


def hash_password(password):
    """Real salted password hash -- PBKDF2-HMAC-SHA256, a fresh random salt
    per password, stdlib only. Returns "salt$hash", both hex -- never the
    plaintext, and nothing here or anywhere else in this library stores
    the original password."""
    salt = _secrets.token_hex(16)
    digest = _hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"),
                                   _PBKDF2_ITERATIONS).hex()
    return f"{salt}${digest}"


# NIST SP 800-63B requires rejecting known-common/breached passwords, not
# just enforcing a minimum length -- a length gate alone still lets
# "password1" or "12345678" through. A production system would check
# against a real breached-password corpus (e.g. a k-anonymity lookup
# against Have I Been Pwned's range API); this local, illustrative list
# closes the structural requirement without taking on a new network
# dependency this library has never needed elsewhere. All entries are
# >= 8 characters so the check is actually reachable past the length gate.
_COMMON_PASSWORDS = frozenset({
    "password", "12345678", "123456789", "1234567890", "qwerty123",
    "qwertyuiop", "letmein12", "welcome123", "welcome1234", "password1",
    "abc123456", "iloveyou1", "admin1234", "changeme1", "trustno1x",
    "monkey123", "dragon123", "football1", "sunshine12", "letmeinplease",
})


def is_common_password(password):
    """True if `password` is on the common/breached-password blocklist
    (case-insensitive) -- see _COMMON_PASSWORDS' docstring for scope."""
    return password.lower() in _COMMON_PASSWORDS


def verify_password(password, stored):
    """Constant-time comparison (hmac.compare_digest) against a hash
    produced by hash_password() -- never a plain == on the digest, which
    would leak timing information about how much of the hash matched."""
    try:
        salt, digest = stored.split("$", 1)
    except (ValueError, AttributeError):
        return False
    check = _hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"),
                                   _PBKDF2_ITERATIONS).hex()
    return _hmac.compare_digest(check, digest)


def create_session(user_id, extra=None, ttl_minutes=60, filename="auth_sessions.json", role_source=None):
    """Real session: a random, unguessable token (256 bits from
    secrets.token_urlsafe, not a predictable or sequential id), a real
    server-computed expiry (the caller cannot extend or forge it), and
    whatever additional claims (e.g. a role) the capability creating the
    session wants attached -- resolved from the caller's own real data,
    never from client input.

    filename defaults to "auth_sessions.json", not the more obvious
    "sessions.json" -- found, by the full-library stress test actually
    merging every app into one shared data/ directory, to collide with
    two real, unrelated, pre-existing capabilities that already used
    "sessions.json" for their own domain concept of "session" (course_
    enrollment_hub's class sessions, multiplayer_game's game sessions):
    a genuine cross-capability DATA-FILE collision, the same class of bug
    _namespace_route() already fixes for URLs, just not yet for filenames.
    "auth_sessions.json" is unambiguous enough not to recur.

    role_source: optional (data_filename, id_field) pair naming where this
    user's LIVE role can be re-read from on every validate_session() call,
    instead of trusting extra['role'] as a static claim frozen at login
    time for the session's whole lifetime. Closes a real gap named by
    OWASP's Authorization Cheat Sheet ("Role Maintenance": when a role
    changes, earlier access must be revoked, not left valid until the
    holder's current session happens to expire on its own) -- see
    validate_session()."""
    token = _secrets.token_urlsafe(32)
    sessions = load(filename)
    expires_at = (_datetime.datetime.now() + _datetime.timedelta(minutes=ttl_minutes)).isoformat()
    session = {"token": token, "user_id": user_id, "expires_at": expires_at}
    if extra:
        session.update(extra)
    if role_source:
        session["_role_source"] = {"data_filename": role_source[0], "id_field": role_source[1]}
    sessions.append(session)
    save(filename, sessions)
    return token


def is_expired(expires_at_iso):
    """Real lazy-evaluation expiry check, computed fresh against the
    actual current time on every call -- no background timer, no
    scheduled job. This library has no mechanism to run code independent
    of an incoming HTTP request (real background/scheduled execution is a
    recorded, separate foundational gap -- see COVERAGE_EXPANSION_REPORT.md
    Part 5.3); this is the deliberately-scoped, buildable slice of that
    gap the report itself recommended investigating first: "did a
    deadline pass" is answered correctly on every read/write without any
    real-time infrastructure. A missing timestamp means "does not expire"
    (False); an unparsable one fails closed (treated as already expired,
    not as "never expires")."""
    if not expires_at_iso:
        return False
    try:
        return _datetime.datetime.fromisoformat(expires_at_iso) < _datetime.datetime.now()
    except (TypeError, ValueError):
        return True


def validate_session(token, filename="auth_sessions.json"):
    """Real, server-side validation: looks the token up, and genuinely
    checks its expiry against the current time -- an expired session is
    rejected here, not just documented as something that should happen.
    Returns the real session dict (user_id + any extra claims) or None.

    If this session was created with a role_source, the returned role is
    re-resolved from the LIVE user record on every call, never trusted as
    the value frozen in at login -- a role change (or account deletion)
    takes effect on the very next request using this token, not only
    after it naturally expires. See create_session()'s docstring for the
    OWASP citation behind this."""
    if not token:
        return None
    sessions = load(filename)
    for s in sessions:
        if _hmac.compare_digest(s["token"], token):
            # unlike share tokens/API keys, a session ALWAYS carries a real
            # expires_at (create_session() sets one unconditionally) -- a
            # missing one here is anomalous, not a deliberate "never
            # expires" choice, so it fails closed rather than falling
            # through to is_expired()'s "no timestamp means no expiry".
            if "expires_at" not in s or is_expired(s.get("expires_at")):
                return None
            role_source = s.get("_role_source")
            if role_source:
                live_rows = load(role_source["data_filename"])
                id_field = role_source["id_field"]
                live_user = next((r for r in live_rows if r.get(id_field) == s["user_id"]), None)
                if live_user is None:
                    return None  # the account no longer exists -- fail closed
                s = {**s, "role": live_user.get("role")}
            return s
    return None


def invalidate_session(token, filename="auth_sessions.json"):
    """Real logout: removes the session row entirely, so the exact same
    token used again after this genuinely fails validate_session() -- not
    a soft "marked inactive" flag a client could ignore."""
    sessions = load(filename)
    remaining = [s for s in sessions if not _hmac.compare_digest(s["token"], token)]
    save(filename, remaining)
    return len(remaining) != len(sessions)


def generate_api_key(service_name, filename="api_keys.json", ttl_minutes=None):
    """Real service/machine credential -- a random key, stored as a salted
    hash (the same PBKDF2 primitive as passwords, so a stolen data file
    still doesn't hand over usable keys), returned to the caller ONCE in
    plaintext (the only time it ever exists outside this call), exactly
    like every real API-key system (Stripe, GitHub, AWS) hands out a
    secret once and stores only a verifier.

    ttl_minutes: optional real expiry (lazy-evaluated by validate_api_key
    via is_expired(), same mechanism as sessions) -- None means the key
    never expires on its own (still revocable via `revoked`), matching
    this function's original, still-supported behavior."""
    raw_key = _secrets.token_urlsafe(32)
    keys = load(filename)
    next_id = (max([k["id"] for k in keys], default=0)) + 1
    expires_at = ((_datetime.datetime.now() + _datetime.timedelta(minutes=ttl_minutes)).isoformat()
                  if ttl_minutes else None)
    keys.append({"id": next_id, "service_name": service_name, "key_hash": hash_password(raw_key),
                  "created_at": _datetime.datetime.now().isoformat(), "expires_at": expires_at,
                  "revoked": False})
    save(filename, keys)
    return raw_key


def validate_api_key(raw_key, filename="api_keys.json"):
    """Real verification against the stored hash -- a revoked OR expired
    key genuinely fails, not just a documented convention."""
    if not raw_key:
        return None
    keys = load(filename)
    for k in keys:
        if (not k.get("revoked") and not is_expired(k.get("expires_at"))
                and verify_password(raw_key, k["key_hash"])):
            return k
    return None


def generate_share_token(resource_type, resource_id, filename="share_tokens.json", ttl_minutes=None):
    """Real guest/anonymous access primitive: an unguessable token scoped
    to exactly one resource, requiring no account or password at all --
    the same real shape as a real shared-document link. Never expires by
    default (a share link outliving the session that created it is often
    the whole point), but is scoped -- it only ever resolves the one
    resource it was made for, checked by validate_share_token(), not
    trusted from client-supplied resource ids.

    ttl_minutes: optional real expiry (lazy-evaluated by
    validate_share_token via is_expired()) for the real cases where a
    share link SHOULD stop working after a while -- None preserves the
    original, still-supported "never expires" behavior."""
    token = _secrets.token_urlsafe(24)
    tokens = load(filename)
    expires_at = ((_datetime.datetime.now() + _datetime.timedelta(minutes=ttl_minutes)).isoformat()
                  if ttl_minutes else None)
    tokens.append({"token": token, "resource_type": resource_type, "resource_id": resource_id,
                    "created_at": _datetime.datetime.now().isoformat(), "expires_at": expires_at})
    save(filename, tokens)
    return token


def validate_share_token(token, resource_type, filename="share_tokens.json"):
    """Real validation: the token must exist, match the resource type the
    caller expects, and not be expired -- a share link minted for one
    resource type can never be replayed against a different one, and one
    minted with a real ttl_minutes genuinely stops working afterward."""
    if not token:
        return None
    tokens = load(filename)
    for t in tokens:
        if (_hmac.compare_digest(t["token"], token) and t["resource_type"] == resource_type
                and not is_expired(t.get("expires_at"))):
            return t["resource_id"]
    return None


def _master_key(key_filename="master_key.bin"):
    """Real key management, honestly scoped: a single local, random,
    256-bit key generated on first use and persisted OUTSIDE data/ (so it
    is never swept up by a data-reset, a data export, or a share/backup of
    the data/ directory) with owner-only file permissions. This is a real
    key -- unguessable, never derived from anything predictable, never
    hardcoded -- but it is deliberately NOT a real KMS: single key, no
    rotation, no per-tenant separation, held on the same disk as the
    ciphertext it protects. For a genuinely multi-tenant or
    compliance-grade deployment this is the honestly-recorded next gap
    (same category as every other "what this does NOT claim" note in this
    library), not something to oversell as solved."""
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    path = SECRETS_DIR / key_filename
    if path.is_file():
        return bytes.fromhex(path.read_text().strip())
    key = _secrets.token_bytes(32)
    path.write_text(key.hex())
    try:
        import os as _os
        _os.chmod(path, 0o600)
    except Exception:
        pass
    return key


def encrypt_value(plaintext, key_filename="master_key.bin"):
    """Real encryption at rest: AES-256-GCM (authenticated encryption --
    tampering with the returned token is detected, not silently accepted)
    via the `cryptography` library (Python's stdlib has no vetted symmetric
    cipher; hand-rolling one instead of adding a real, audited dependency
    would be exactly the fake-security shortcut this project's standard
    forbids). A fresh random 96-bit nonce is generated per call -- the
    same plaintext encrypts differently every time -- and stored alongside
    the ciphertext+tag in the single returned string, base64-encoded, so
    callers can store one opaque value with no extra columns."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import base64
    key = _master_key(key_filename)
    nonce = _secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def decrypt_value(token, key_filename="master_key.bin"):
    """Reverses encrypt_value(). Raises ValueError on a tampered or
    corrupt token (wrong key, flipped bit, truncated data) -- a real
    integrity failure is surfaced as a real error, never swallowed into a
    silently-wrong plaintext or an empty string that looks like success."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag
    import base64
    key = _master_key(key_filename)
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        nonce, ct = raw[:12], raw[12:]
        pt = AESGCM(key).decrypt(nonce, ct, None)
    except Exception as e:
        raise ValueError(f"cannot decrypt: invalid or tampered ciphertext ({type(e).__name__})") from e
    return pt.decode("utf-8")
'''


def _shared_lib_import_bootstrap() -> str:
    """The one, real dynamic-import bootstrap every capability's route.py
    gets, loading CAP-0000's real module by path -- identical to how the
    host loader already discovers sibling capabilities, just done from a
    capability's own file instead of the host's."""
    return '''
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)
'''


def store_helpers(data_filename: str) -> str:
    """_load()/_save(rows) now real thin wrappers over CAP-0000's shared,
    single-source implementation -- kept as the same call surface every
    existing handler_body string already uses, so upgrading the underlying
    storage interface required zero changes to any of them."""
    return _shared_lib_import_bootstrap() + f'''
DATA_FILE_NAME = "{data_filename}"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)
'''


HOST_APP_PY_TEMPLATE = '''#!/usr/bin/env python3
"""modules/CAP-{host_num}/app.py -- real host: home page, health check, and a
dynamic loader for sibling capability modules (modules/<CAP-id>/route.py) --
the same proven convention as CAP-0001's fixture host and the round-7 real
todo app's CAP-0100 host. Now also the one place that normalizes every
capability's error response into the Common Capability Contract's standard
shape and passes a standard identity/context object to any handler that
declares it wants one -- both done centrally here, so upgrading either
never required touching a single capability's own handler code."""
import argparse
import importlib.util
import inspect
from pathlib import Path
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

_shared_lib_path = MODULES_ROOT / "CAP-0000" / "shared_lib.py"
_spec = importlib.util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

INDEX_HTML = %(index_html)r


@app.route("/health")
def health():
    return jsonify({{"ok": True}}), 200


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


ROUTE_HANDLERS = {{}}
HANDLER_WANTS_CTX = {{}}


def load_modules():
    if not MODULES_ROOT.is_dir():
        return
    for entry in sorted(MODULES_ROOT.iterdir()):
        if not entry.is_dir() or entry.name in ("CAP-{host_num}", "CAP-0000"):
            continue
        route_file = entry / "route.py"
        if not route_file.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"mod_{{entry.name}}", route_file)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"module {{entry.name}} failed to load: {{e}}")
            continue
        route = getattr(mod, "ROUTE", None)
        method = getattr(mod, "METHOD", "GET")
        handler = getattr(mod, "handle", None)
        if route and handler:
            key = (method, route)
            ROUTE_HANDLERS[key] = handler
            # Standard identity/context passing: a handler that declares a
            # second parameter gets a real ctx object (see _make_ctx()) --
            # real session/role/service-key resolution, not a placeholder.
            # A handler that doesn't declare it is called exactly as before.
            HANDLER_WANTS_CTX[key] = len(inspect.signature(handler).parameters) >= 2


load_modules()


def _make_ctx(request):
    """Real identity resolution, not a stub: a Bearer token in the real
    Authorization header is checked against a real, server-side session
    (expiry genuinely enforced -- see CAP-0000's validate_session()); an
    X-API-Key header is checked against a real, hashed service credential.
    Neither is trusted from client-supplied user/role fields in the request
    body -- ctx["user"]/ctx["role"] only ever come from what the server's
    own session store says, and the raw token is carried through so a
    capability like logout can invalidate the exact session that made the
    request."""
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    session = _shared.validate_session(token) if token else None
    api_key_header = request.headers.get("X-API-Key")
    api_key_record = _shared.validate_api_key(api_key_header) if api_key_header else None
    ctx = {{"user": None, "authenticated": False, "role": None, "token": token, "service": None}}
    if session:
        ctx["user"] = session.get("user_id")
        ctx["authenticated"] = True
        ctx["role"] = session.get("role")
    if api_key_record:
        ctx["service"] = api_key_record.get("service_name")
        ctx["authenticated"] = True
    return ctx


def _error_body(status, message):
    return {{"error": {{"code": _shared.code_for_status(status), "message": message}}}}


@app.route("/<path:subpath>", methods=["GET", "POST"])
def dispatch(subpath):
    path = "/" + subpath
    key = (request.method, path)
    handler = ROUTE_HANDLERS.get(key)
    if handler is None:
        return jsonify(_error_body(404, "not found")), 404
    try:
        if HANDLER_WANTS_CTX.get(key):
            status, body = handler(request, _make_ctx(request))
        else:
            status, body = handler(request)
    except Exception as e:
        return jsonify(_error_body(500, f"handler raised {{type(e).__name__}}: {{e}}")), 500
    # Real binary responses (CAP-0000's save_blob()/load_blob(), the real
    # document-storage primitive): a handler that wants to serve raw bytes
    # with a real Content-Type returns {{"__binary__": True, "data": <bytes>,
    # "content_type": <str>}} instead of a plain JSON-able dict. Checked by
    # a sentinel key no pre-existing handler_body ever returns, so every
    # handler predating this stays on the jsonify() path unchanged.
    if isinstance(body, dict) and body.get("__binary__"):
        return Response(body["data"], mimetype=body.get("content_type", "application/octet-stream"), status=status)
    # Standard error shape: any handler that still returns the older bare
    # {{"error": "<string>"}} shape (every handler_body string predating this
    # contract) gets it normalized here, once, centrally -- so the wire
    # contract is uniform without having rewritten 187 handler bodies.
    if status >= 400 and isinstance(body, dict) and isinstance(body.get("error"), str):
        body = _error_body(status, body["error"])
    return jsonify(body), status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port)
'''


def page_skeleton(title: str, extra_style: str, body_inner: str, script_body: str) -> str:
    """A real, minimal HTML page shell shared across generated apps: standard
    chrome (title, base styles, a centered card) with the actual UI markup
    and the actual wiring JS supplied per app -- not templated behavior, only
    templated layout."""
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 700px; margin: 40px auto;
  color: #222; background: #f7f7f7; }}
.card {{ background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.15); border-radius: 6px; padding: 20px; margin-bottom: 16px; }}
h1 {{ font-size: 22px; }}
input, select, textarea {{ font-size: 15px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
button {{ font-size: 14px; padding: 8px 14px; border: none; border-radius: 4px; background: #2f6f9f; color: #fff;
  cursor: pointer; }}
button.danger {{ background: #af2f2f; }}
button.secondary {{ background: #888; }}
ul {{ list-style: none; margin: 0; padding: 0; }}
li {{ border-bottom: 1px solid #eee; padding: 10px 4px; }}
.row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
{extra_style}
</style>
</head>
<body>
<h1>{title}</h1>
{body_inner}
<script>
{script_body}
</script>
</body>
</html>
'''


class AppBuilder:
    """Accumulates one real app-type's shelf + template, then writes it out
    under <root>/<slug>/ in exactly the layout build.py expects (shelf/,
    templates/, APPS_LIST.md, choice.json) -- one call per real app type."""

    def __init__(self, root: Path, slug: str, app_type: str, host_num: str):
        self.dir = root / slug
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.slug = slug
        self.app_type = app_type
        self.host_num = host_num  # e.g. "0200" -> CAP-0200 is this app's host
        self.caps = self.dir / "shelf" / "capabilities"
        self.impls = self.dir / "shelf" / "implementations"
        self.templates = self.dir / "templates"
        for d in (self.caps, self.impls, self.templates):
            d.mkdir(parents=True)
        self.required_caps = [f"CAP-{host_num}"]
        self.slots = []
        self.data_filename = f"{slug}.json"
        self._routes_seen = {}
        self._add_shared_library()

    def host_cap_id(self):
        return f"CAP-{self.host_num}"

    def _add_shared_library(self):
        """Writes CAP-0000 -- the real, single-source storage/error/notify
        implementation every other capability in this app imports rather
        than duplicates. Written once per app, always required; every
        capability add_capability() generates from here on declares a real
        dependency on it, enforced by build.py's stage1_assemble()."""
        cap_id = SHARED_LIB_CAP_ID
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, "Shared Capability Library", "library", [f"{cap_id}/IMPL-01"],
                              error_codes=("INTERNAL_ERROR",)))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/shared_lib.py"))
        write(self.impls / cap_id / "IMPL-01" / cap_id / "shared_lib.py", SHARED_LIB_SOURCE)
        self.required_caps.append(cap_id)

    def add_host(self, index_html: str):
        cap_id = self.host_cap_id()
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, f"{self.app_type.title()} Host", "ui", [f"{cap_id}/IMPL-01"],
                              dependencies=(SHARED_LIB_CAP_ID,), error_codes=("NOT_FOUND", "INTERNAL_ERROR")))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/app.py"))
        host_py = HOST_APP_PY_TEMPLATE.format(host_num=self.host_num) % {"index_html": index_html}
        write(self.impls / cap_id / "IMPL-01" / cap_id / "app.py", host_py)

    def _namespace_route(self, route: str) -> str:
        """The real architectural fix for cross-app URL collisions (found by
        full_library_stress_test.py merging the whole library into one
        system: 15 different apps independently chose the same natural
        path -- e.g. "/api/events" -- for their own feature, and the host's
        loader silently let the last-loaded one win, making 23 capabilities
        unreachable). Every app's own slug is already guaranteed globally
        unique -- it's the actual OUTPUT_LIBRARY/NEW_APPS_FROM_LIBRARY
        directory name -- so namespacing every ROUTE under it makes cross-app
        collision structurally impossible, not merely unlikely, without
        touching a single handler_body: this is the one place every route
        string is written, so every existing and future capability gets it
        automatically. A capability copied verbatim into another app via
        reuse_capability_verbatim() keeps the ORIGINAL app's namespace
        (correct: it is still, honestly, that app's real, single-sourced
        implementation and data file, just mounted into a second app)."""
        assert route.startswith("/api/"), f"expected a route starting with /api/, got {route!r}"
        return f"/api/{self.slug}{route[len('/api'):]}"

    def add_capability(self, num: str, name: str, route: str, method: str, handler_body: str,
                        output_fields=(), required_input=(), side_effects=(), slot_id=None,
                        selector=None, data_filename=None, dependencies=(), extra_error_codes=(),
                        extra_data_access=(), required_role=None, context_fields_override=None):
        """num is the 4-digit suffix, e.g. '0201' -> CAP-0201. handler_body is
        the real Python source of the route module's own logic (ROUTE/METHOD
        already added); data_filename defaults to this app's single JSON
        store, overridable per-capability for apps with more than one entity.
        dependencies: real capability ids this one's handler_body reads/writes
        via a sibling data file rather than its own (besides CAP-0000, which
        every capability depends on automatically) -- must also be required
        by this app (build.py enforces this at assembly time).

        extra_data_access: additional {"entity", "access"} entries for a
        capability that -- like payroll's "Run Payroll" -- reads or writes a
        SECOND entity beyond its own data_filename, always via the shared
        library's own _shared.load()/_shared.save() (already in scope from
        store_helpers()'s bootstrap), never a hand-rolled path -- that second
        entity must be declared here or build.py's compatibility gate
        rejects the capability for undeclared data access.

        required_role: if set, wraps handler_body (which must be a plain
        "def handle(request): ..." string, the convention every generic
        engine already uses) so the REAL function called by the host is
        ctx-aware and checks ctx['role'] -- resolved server-side from a
        real, validated session (see gen_common.py's _make_ctx()), never
        from a client-supplied field -- before running the original logic
        at all. A role mismatch returns a real 403, the original body never
        runs. This is real authorization, not a documented convention: see
        COVERAGE_EXPANSION_REPORT.md's Part 3 security tests for the live
        proof of a non-admin genuinely being rejected.

        context_fields_override: for a handler_body you author directly as
        "def handle(request, ctx): ..." (rather than going through
        required_role's wrapping), declare which real ctx fields it reads
        -- e.g. ("authenticated", "token") for a logout capability. Ignored
        when required_role is set (that path declares ("role",) itself).

        error_codes and data_access are derived here, automatically, from
        real facts already passed in (required_input's shape, side_effects,
        data_filename) -- not hand-typed per capability, so they can't drift
        from what the generated code actually does."""
        cap_id = f"CAP-{num}"
        df = data_filename or self.data_filename
        if df in RESERVED_SHARED_LIB_FILENAMES:
            raise AssertionError(
                f"{cap_id} in app {self.slug!r} declares data_filename={df!r}, which is reserved "
                f"for CAP-0000's own internal primitive state (see RESERVED_SHARED_LIB_FILENAMES) "
                f"-- a domain capability must never share physical storage with a shared-library "
                f"primitive whose row shape it doesn't control. This is the generation-time guard "
                f"for the Cross-App Isolation Contract (CANONICAL_SPEC.md Part C.4): pick a "
                f"different data_filename for this capability's own entity.")
        error_codes = ["INTERNAL_ERROR"]
        if required_input:
            error_codes.append("VALIDATION_ERROR")
        if any(f.lower() == "id" or f.lower().endswith("_id") for f in required_input):
            error_codes.append("NOT_FOUND")
        if required_role:
            error_codes.append("FORBIDDEN")
        error_codes.extend(extra_error_codes)
        access = "read_write" if side_effects else "read"
        data_access = [{"entity": df, "access": access}] + [dict(a) for a in extra_data_access]
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, name, "compute", [f"{cap_id}/IMPL-01"],
                              output_fields=output_fields, required_input=required_input,
                              side_effects=side_effects,
                              dependencies=(SHARED_LIB_CAP_ID, *dependencies),
                              error_codes=error_codes,
                              data_access=data_access,
                              requires_auth=bool(required_role or context_fields_override),
                              context_fields=("role",) if required_role
                              else tuple(context_fields_override or ())))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/route.py"))
        namespaced_route = self._namespace_route(route)
        route_key = (namespaced_route, method)
        if route_key in self._routes_seen:
            raise AssertionError(
                f"route collision within app {self.slug!r}: {method} {namespaced_route} is "
                f"already registered by {self._routes_seen[route_key]!r}, now also claimed by "
                f"{cap_id!r} -- the second capability would silently shadow the first in the "
                f"host's dispatch table (this is exactly the same-app version of the "
                f"cross-app collision _namespace_route() already fixes; give it a distinct "
                f"route, e.g. via add_auth_capabilities()'s route_prefix)")
        self._routes_seen[route_key] = cap_id
        if required_role:
            assert handler_body.startswith("def handle(request):"), \
                "required_role needs a plain 'def handle(request): ...' body to wrap"
            inner = handler_body.replace("def handle(request):", "def _handle_inner(request):", 1)
            handler_body = (
                inner + "\n\n"
                "def handle(request, ctx):\n"
                f"    if ctx.get('role') != {required_role!r}:\n"
                f"        return 403, {{'error': 'requires role {required_role}'}}\n"
                "    return _handle_inner(request)\n"
            )
        body = store_helpers(df) + f'\nROUTE = {namespaced_route!r}\nMETHOD = {method!r}\n\n\n' + handler_body
        write(self.impls / cap_id / "IMPL-01" / cap_id / "route.py", body)
        self.required_caps.append(cap_id)
        if slot_id:
            self.slots.append(slot(slot_id, cap_id, name, selector or f"#{slot_id}",
                                    side_effects=side_effects))

    def add_exceeds_threshold_capability(self, num: str, name: str, route: str, id_field: str,
                                          value_field: str, value_input: str, holder_field=None,
                                          holder_input=None, fail_message="proposed value does not exceed the current value",
                                          entity_noun="record", slot_id=None, selector=None):
        """Generic capability: a proposed value only takes effect if it exceeds
        the matched record's current value in `value_field`, optionally also
        recording who proposed it (`holder_field`/`holder_input`). This is the
        real shape behind auction's 'place a higher bid' rule, generalized so
        any domain with the same rule (a raise that must exceed current pay, a
        score that must beat a high score, a reservation deposit that must
        exceed the current one) reuses this generator instead of a fresh
        hand-written comparison. Proven behaviourally identical to the
        original hand-written auction capability by direct regression test
        (see verification/prove_generalization.py)."""
        holder_line = ""
        if holder_field and holder_input:
            holder_line = f"            rec['{holder_field}'] = body.get('{holder_input}') or 'anonymous'\n"
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    try:\n        proposed = float(body.get('{value_input}', 0) or 0)\n"
            "    except (TypeError, ValueError):\n        proposed = 0.0\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            if proposed <= rec.get('{value_field}', 0):\n"
            f"                return 400, {{'error': {fail_message!r}}}\n"
            f"            rec['{value_field}'] = proposed\n"
            f"{holder_line}"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, value_field) + ((holder_field,) if holder_field else ())
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field, value_input), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector)

    def add_bounded_counter_capability(self, num: str, name: str, route: str, id_field: str,
                                        counter_field: str, limit_field: str, fail_message: str,
                                        increment: int = 1, extra_output_fields=(),
                                        entity_noun="record", slot_id=None, selector=None,
                                        data_filename=None):
        """Generic capability: increments `counter_field` on a matched record
        only while it stays below `limit_field` on the SAME record. This is
        the real shape behind event_ticketing's capacity check, generalized
        so any bounded-counter rule (seats left, stock on hand, a rate limit)
        reuses this generator. Proven behaviourally identical to the original
        hand-written event_ticketing capability by direct regression test."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            if rec['{counter_field}'] >= rec['{limit_field}']:\n"
            f"                return 400, {{'error': {fail_message!r}}}\n"
            f"            rec['{counter_field}'] += {increment}\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, counter_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field,), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_unbounded_counter_capability(self, num: str, name: str, route: str, id_field: str,
                                          counter_field: str, increment: int = 1,
                                          extra_output_fields=(), entity_noun="record",
                                          slot_id=None, selector=None, data_filename=None):
        """Generic capability: increments `counter_field` on a matched record
        by a fixed amount, with no upper bound. This is the real shape found,
        by real audit, hand-written six separate times across the pre-fix
        43-app library -- social_feed's "Like Post" (likes), photo_sharing's
        "Like Photo" (likes), short_video_feed's "View Video" and
        video_streaming's "Watch Video" (views), music_streaming's "Play
        Track" and podcast's "Play Episode" (plays) -- and never generalized
        until this coverage-testing round found the same shape recurring six
        times with zero shared engine behind it. Proven behaviourally
        identical to social_feed's original hand-written capability by direct
        regression test, the same methodology as add_bounded_counter_
        capability was proven against event_ticketing."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            rec['{counter_field}'] += {increment}\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, counter_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field,), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_status_transition_capability(self, num: str, name: str, route: str, id_field: str,
                                          status_field: str, status_input: str, default_status: str,
                                          extra_output_fields=(), entity_noun="record",
                                          extra_body_lines="", slot_id=None, selector=None,
                                          data_filename=None):
        """Generic capability: sets `status_field` on a matched record to a
        value taken from the request body (falling back to `default_status`
        if omitted), unconditionally -- no allowed-value validation, matching
        every real precedent this generalizes, none of which validated the
        incoming value either. This is the real shape found, by real audit,
        hand-written five separate times across the pre-fix 43-app library --
        crm's "Update Contact Stage", project_management's "Update Task
        Status", ride_hailing's "Update Ride Status", invoicing's "Mark
        Invoice Paid" (a fixed-value special case), and parcel_tracking's
        "Update Parcel Status" (the one variant that also appends to a
        history list, supported here via extra_body_lines rather than forking
        the shape). Proven behaviourally identical to crm's original
        hand-written capability by direct regression test."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    new_status = body.get('{status_input}') or {default_status!r}\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            rec['{status_field}'] = new_status\n"
            f"{extra_body_lines}"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, status_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field,), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_bounded_decrement_capability(self, num: str, name: str, route: str, id_field: str,
                                          balance_field: str, amount_input: str,
                                          fail_message: str = "insufficient balance",
                                          entity_noun: str = "record", extra_output_fields=(),
                                          slot_id=None, selector=None, data_filename=None):
        """Generic capability: decrements `balance_field` on a matched record
        by a caller-supplied amount, rejecting if that would take the balance
        below zero -- the mirror image of add_bounded_counter_capability
        (which increments toward a cap), for the equally real and equally
        common "spend down a pool" shape (a budget envelope, a stock count
        sold from, a benefit balance drawn down). This is the simple,
        single-step form of the widely-used inventory-reservation pattern
        (reject a debit when it would exceed the available balance; see
        COVERAGE_EXPANSION_REPORT.md for the real references compared before
        building this) -- deliberately not the full reserve/confirm/release
        lifecycle real high-concurrency inventory systems use, which is a
        different, larger problem (concurrent reservations across
        in-flight, uncommitted orders) this single-process, single-request
        library has no real concurrency story for anyway. No existing
        hand-written precedent in this library to regression-test against;
        proven by real build + browser + functional test instead."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    try:\n        amount = float(body.get('{amount_input}', 0) or 0)\n"
            "    except (TypeError, ValueError):\n        amount = 0.0\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            if amount > rec['{balance_field}']:\n"
            f"                return 400, {{'error': {fail_message!r}}}\n"
            f"            rec['{balance_field}'] -= amount\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, balance_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field, amount_input), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_validated_status_transition_capability(self, num: str, name: str, route: str,
                                                     id_field: str, status_field: str, status_input: str,
                                                     allowed_transitions: dict, extra_output_fields=(),
                                                     entity_noun: str = "record", slot_id=None,
                                                     selector=None, data_filename=None):
        """Generic capability: the validated sibling of add_status_transition_
        capability. That engine faithfully reproduced its five real
        precedents' behaviour, all of which accept ANY string as the new
        status. Real workflow requests (a purchase-order approval chain, an
        editorial review pipeline, a government case's approval gates) need
        the opposite: an explicit allow-list of legal source -> destination
        transitions, rejecting anything else -- the standard state-machine
        pattern (see COVERAGE_EXPANSION_REPORT.md for the real references
        compared before building this: an explicit table of legal
        transitions, checked before the state changes, not after).
        `allowed_transitions` is a real dict, e.g.
        {"draft": ["submitted"], "submitted": ["approved", "rejected"]} --
        a status with no entry, or a destination not listed for the current
        status, is rejected with a 400, not silently allowed. No existing
        hand-written precedent to regression-test against (every existing
        status-setting capability in this library is deliberately
        unvalidated); proven by real build + browser + functional test,
        including a real, asserted-rejected illegal transition."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    new_status = body.get('{status_input}')\n"
            f"    allowed = {allowed_transitions!r}\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            current = rec.get('{status_field}')\n"
            "            legal = allowed.get(current, [])\n"
            "            if new_status not in legal:\n"
            "                return 400, {'error': f'cannot transition from ' + repr(current)"
            " + ' to ' + repr(new_status)}\n"
            f"            rec['{status_field}'] = new_status\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, status_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field, status_input), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_search_capability(self, num: str, name: str, route: str, search_field: str,
                               match: str = "substring", data_filename=None):
        """Generic capability: a real GET-with-query-param search/filter,
        the standard REST pattern (a query parameter per filterable field,
        matched against the resource's own records -- see
        COVERAGE_EXPANSION_REPORT.md for the real references compared
        before building this). `match` is "substring" (case-insensitive
        contains, for free-text fields like a title) or "exact" (for
        category/status-like fields). An empty or missing query returns
        every record, matching every existing "List X" capability's
        behaviour when no filter is requested -- this is a strict addition,
        not a change to any existing capability. No existing hand-written
        precedent to regression-test against (nothing in the pre-existing
        library filters at all -- every "List" capability returns
        everything, unconditionally); proven by real build + browser +
        functional test."""
        if match == "exact":
            cond = f"str(rec.get({search_field!r}, '')) == q"
        else:
            cond = f"q.lower() in str(rec.get({search_field!r}, '')).lower()"
        body = (
            "def handle(request):\n"
            "    q = (request.args.get('q') or '').strip()\n"
            "    rows = _load()\n"
            "    if not q:\n        return 200, {'results': rows}\n"
            f"    matches = [rec for rec in rows if {cond}]\n"
            "    return 200, {'results': matches}\n"
        )
        self.add_capability(num, name, route, "GET", body, output_fields=("results",),
                             data_filename=data_filename)

    def add_audit_log_capability(self, num: str, route: str = "/api/audit_log"):
        """A real "List Audit Log" viewer capability, through the same
        add_capability() choke point every other capability uses -- reading
        the same audit_log.json file CAP-0000's real audit() primitive (see
        SHARED_LIB_SOURCE) writes to. Any OTHER capability that needs to
        record a real audit entry calls `_shared.audit(...)` directly in its
        own handler body -- the same real-composition pattern already
        established for notify(), not a new mechanism. This capability
        itself only ever reads; it never writes an entry on its own, so its
        side_effects are deliberately empty and its access is read-only."""
        self.add_capability(num, "List Audit Log", route, "GET",
            "def handle(request):\n    return 200, {'entries': _load()}\n",
            output_fields=("entries",), data_filename="audit_log.json")

    def add_auth_capabilities(self, register_num: str, login_num: str, logout_num: str, me_num: str,
                               data_filename="users.json", default_role=None, extra_fields=(),
                               register_slot_id=None, register_selector=None, route_prefix=""):
        """Generic capability set: real register/login/logout/who-am-i --
        the STANDARD INDIVIDUAL ACCOUNT identity type, and (reused a second
        time with a different data_filename/default_role in the same app)
        the TWO-SIDED PEER ACCOUNT type, proving the same engine covers
        both by real reuse, not a special case per identity type.

        Real security, not simulated: passwords are hashed with
        CAP-0000's hash_password() (PBKDF2-HMAC-SHA256, salted) and NEVER
        stored or returned in plaintext -- Register's own response strips
        password_hash before returning the created record. Register also
        rejects a password shorter than 8 characters (NIST SP 800-63B's
        required minimum) or on CAP-0000's common-password blocklist (the
        same standard's requirement to screen against known-common/
        breached passwords, not just enforce a length floor). Login verifies
        with a constant-time comparison and issues a real, expiring,
        unguessable session token (CAP-0000's create_session()). Logout
        genuinely invalidates that exact token server-side. "Me" requires a
        real, currently-valid session and returns only what the session
        itself resolved -- never a client-supplied user id.

        Login passes role_source=(data_filename, 'id') to create_session(),
        so ctx['role'] is re-resolved from the LIVE user record on every
        single request for the life of the session, not frozen at login
        time -- a role change (or the account being deleted) takes effect
        on the very next request, closing the OWASP Authorization Cheat
        Sheet's "Role Maintenance" requirement (earlier access must be
        revoked when a role changes, not left valid until the session
        happens to expire naturally).

        Every security-relevant event is now audited via CAP-0000's real
        audit() primitive (the same one add_audit_log_capability() reads
        from -- any app that pairs the two gets a real, queryable trail
        with zero extra wiring): register, login success, login failure,
        and logout. Login failure's actor is explicitly the CLAIMED email,
        not a verified one (there is no valid session to resolve an actor
        from when the attempt fails) -- recorded that way in the entry
        itself, not glossed over, consistent with audit()'s own docstring
        distinction between a claimed and a verified actor. This closes a
        real gap this round's own security work surfaced: before this,
        nothing in the library recorded who logged in, who failed to, or
        who logged out -- the exact kind of security-relevant activity an
        audit trail exists for, and the #1-ranked criterion (security
        impact) for this round's next-five-capabilities selection.

        default_role: every account registered through this instance gets
        this role baked in server-side (e.g. "admin" for one instance,
        None/"member" for another) -- a real ROLE-BASED PRIVILEGED ACCOUNT
        is exactly this generic engine called with a role, paired with
        add_capability(..., required_role=...)-gated capabilities elsewhere
        in the same app; there is no separate "make an admin" engine to
        keep in sync, and no way for a registering client to grant itself
        a role by passing one in the request body.

        route_prefix: REQUIRED to be distinct whenever this engine is
        called more than once in the same app. Routes are namespaced by
        app slug (_namespace_route()) but NOT by call, so two calls with
        the same route_prefix (the default "") would both register at
        literally the same path (e.g. /api/<slug>/auth/register) and the
        second call's route.py would silently shadow the first's in the
        host's dispatch table -- found by security_tests.py actually
        calling the standard-account register endpoint and observing it
        answer with the THIRD (client) call's data_filename/role instead:
        a real, reproduced collision, not a hypothetical one. Pass e.g.
        route_prefix="admin" for a second call so it lands at
        /api/<slug>/admin/auth/register instead."""
        prefix = f"/{route_prefix}" if route_prefix else ""
        extra_lines = "".join(f"    {f}_val = body.get({f!r}) or ''\n" for f in extra_fields)
        extra_assign = "".join(f"    user[{f!r}] = {f}_val\n" for f in extra_fields)
        extra_output = tuple(extra_fields)

        register_body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    email = (body.get('email') or '').strip().lower()\n"
            "    password = body.get('password') or ''\n"
            "    if not email or not password:\n"
            "        return 400, {'error': 'email and password are required'}\n"
            "    if len(password) < 8:\n"
            "        return 400, {'error': 'password must be at least 8 characters'}\n"
            "    if _shared.is_common_password(password):\n"
            "        return 400, {'error': 'this password is too common; choose a less predictable one'}\n"
            "    users = _load()\n"
            "    if any(u['email'] == email for u in users):\n"
            "        return 409, {'error': 'an account with this email already exists'}\n"
            "    next_id = (max([u['id'] for u in users], default=0)) + 1\n"
            f"    user = {{'id': next_id, 'email': email, "
            f"'password_hash': _shared.hash_password(password), 'role': {default_role!r}}}\n"
            + extra_lines + extra_assign +
            "    users.append(user)\n    _save(users)\n"
            f"    _shared.audit(email, 'register', {data_filename!r}, next_id, "
            f"'role=' + repr({default_role!r}))\n"
            "    return 201, {k: v for k, v in user.items() if k != 'password_hash'}\n"
        )
        self.add_capability(register_num, "Register", f"/api{prefix}/auth/register", "POST", register_body,
                             output_fields=("id", "email", "role") + extra_output,
                             required_input=("email", "password"), side_effects=("creates_record",),
                             data_filename=data_filename,
                             extra_data_access=[{"entity": "audit_log.json", "access": "read_write"}],
                             slot_id=register_slot_id, selector=register_selector)

        login_body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    email = (body.get('email') or '').strip().lower()\n"
            "    password = body.get('password') or ''\n"
            "    users = _load()\n"
            "    for user in users:\n"
            "        if user['email'] == email and _shared.verify_password(password, user['password_hash']):\n"
            f"            token = _shared.create_session(user['id'], extra={{'role': user.get('role')}}, "
            f"role_source=({data_filename!r}, 'id'))\n"
            f"            _shared.audit(email, 'login_success', {data_filename!r}, user['id'])\n"
            "            return 200, {'token': token, 'user_id': user['id'], 'role': user.get('role')}\n"
            f"    _shared.audit(email, 'login_failure', {data_filename!r}, None, "
            "'invalid credentials -- actor is the CLAIMED email, not a verified identity')\n"
            "    return 401, {'error': 'invalid email or password'}\n"
        )
        self.add_capability(login_num, "Login", f"/api{prefix}/auth/login", "POST", login_body,
                             output_fields=("token", "user_id", "role"),
                             required_input=("email", "password"), data_filename=data_filename,
                             extra_error_codes=("UNAUTHORIZED",),
                             extra_data_access=[{"entity": "auth_sessions.json", "access": "read_write"},
                                                 {"entity": "audit_log.json", "access": "read_write"}])

        logout_body = (
            "def handle(request, ctx):\n"
            "    if not ctx.get('authenticated'):\n"
            "        return 401, {'error': 'not authenticated'}\n"
            "    _shared.invalidate_session(ctx['token'])\n"
            f"    _shared.audit(ctx['user'], 'logout', {data_filename!r}, ctx['user'])\n"
            "    return 200, {'logged_out': True}\n"
        )
        self.add_capability(logout_num, "Logout", f"/api{prefix}/auth/logout", "POST", logout_body,
                             output_fields=("logged_out",), data_filename=data_filename,
                             extra_error_codes=("UNAUTHORIZED",),
                             extra_data_access=[{"entity": "auth_sessions.json", "access": "read_write"},
                                                 {"entity": "audit_log.json", "access": "read_write"}],
                             context_fields_override=("authenticated", "token", "user"))

        me_body = (
            "def handle(request, ctx):\n"
            "    if not ctx.get('authenticated'):\n"
            "        return 401, {'error': 'not authenticated'}\n"
            "    return 200, {'user_id': ctx.get('user'), 'role': ctx.get('role')}\n"
        )
        self.add_capability(me_num, "Who Am I", f"/api{prefix}/auth/me", "GET", me_body,
                             output_fields=("user_id", "role"), data_filename=data_filename,
                             extra_error_codes=("UNAUTHORIZED",),
                             context_fields_override=("authenticated", "user", "role"))

    def add_share_token_capability(self, generate_num: str, resolve_num: str, resource_type: str,
                                    generate_route: str, resolve_route: str,
                                    resource_data_filename: str, id_field="id", ttl_minutes=None):
        """Generic capability pair: the GUEST/ANONYMOUS SHARED-ACCESS
        identity type. generate_num mints a real, unguessable token scoped
        to one specific resource (CAP-0000's generate_share_token());
        resolve_num looks a resource up BY THAT TOKEN alone, with no
        account, password, or session of any kind -- exactly a real
        shared-link's behavior. resolve_num genuinely 404s for an unknown,
        wrong-resource-type, or genuinely EXPIRED token (lazy-evaluated,
        see CAP-0000's is_expired()), not a silent empty response.

        ttl_minutes: optional real expiry baked into every link this
        capability instance mints -- None (the default) preserves the
        original "never expires" behavior; a real number closes the real
        gap this session's own new share-link mechanism first shipped
        with (see COVERAGE_EXPANSION_REPORT.md Part 5.3 and this round's
        Part 4 next-five-capabilities selection)."""
        gen_body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get({id_field!r})\n"
            f"    if rid is None:\n        return 400, {{'error': {id_field!r} + ' is required'}}\n"
            f"    token = _shared.generate_share_token({resource_type!r}, rid, ttl_minutes={ttl_minutes!r})\n"
            "    return 201, {'token': token}\n"
        )
        self.add_capability(generate_num, "Generate Share Link", generate_route, "POST", gen_body,
                             output_fields=("token",), required_input=(id_field,),
                             side_effects=("creates_record",), data_filename="share_tokens.json")

        resolve_body = (
            "def handle(request):\n"
            "    token = request.args.get('token')\n"
            f"    rid = _shared.validate_share_token(token, {resource_type!r})\n"
            "    if rid is None:\n        return 404, {'error': 'invalid or unknown share link'}\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec[{id_field!r}] == rid:\n            return 200, rec\n"
            "    return 404, {'error': 'the shared resource no longer exists'}\n"
        )
        self.add_capability(resolve_num, "Open Shared Link", resolve_route, "GET", resolve_body,
                             data_filename=resource_data_filename,
                             extra_data_access=[{"entity": "share_tokens.json", "access": "read"}])

    def add_api_key_capability(self, num: str, route="/api/service_keys", ttl_minutes=None):
        """Generic capability: the SERVICE/SYSTEM ACCOUNT identity type --
        a real, hashed API key (CAP-0000's generate_api_key()) for a
        non-human caller, returned in plaintext exactly once at creation
        (the only time it ever exists outside the hash), the same real
        pattern as Stripe/GitHub/AWS key issuance. A capability elsewhere
        in the same app that wants to require this key checks
        ctx.get('service') (populated by the host's real X-API-Key
        validation in _make_ctx()), the same ctx mechanism every other
        identity type in this library uses.

        ttl_minutes: optional real expiry (lazy-evaluated, see CAP-0000's
        is_expired()) -- None (the default) preserves the original
        "never expires on its own, only via revoked" behavior; a real
        number gives every key this capability instance issues a genuine
        shelf life, on top of (not instead of) manual revocation."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    service_name = (body.get('service_name') or '').strip()\n"
            "    if not service_name:\n        return 400, {'error': 'service_name is required'}\n"
            f"    raw_key = _shared.generate_api_key(service_name, ttl_minutes={ttl_minutes!r})\n"
            "    return 201, {'service_name': service_name, 'api_key': raw_key}\n"
        )
        self.add_capability(num, "Generate Service API Key", route, "POST", body,
                             output_fields=("service_name", "api_key"),
                             required_input=("service_name",), side_effects=("creates_record",),
                             data_filename="api_keys.json")

    def add_document_storage_capabilities(self, upload_num: str, download_num: str, list_num: str,
                                           upload_route: str, download_route: str, list_route: str,
                                           index_filename="documents.json", max_bytes=10 * 1024 * 1024):
        """Real binary/document storage (Upload/Download/List), the
        foundational gap COVERAGE_EXPANSION_REPORT.md Part 5.4 named
        (recruitment CV upload, medical/government document submission, AI
        studio asset storage) -- built for real on CAP-0000's save_blob()/
        load_blob(), not the string-in-JSON `content` field
        file_storage_and_sync used, which that report explicitly called
        "real but impractical for genuine files".

        Real multipart/form-data upload (request.files), not a base64-in-
        JSON workaround -- the real shape every genuine file upload uses.
        Download serves the real bytes with the real stored Content-Type
        via the host's new binary-response path (see HOST_APP_PY_TEMPLATE's
        dispatch()), not JSON-wrapped-as-text.

        Honest limitation: because this is real multipart upload rather
        than a text field, it CANNOT be the target of this library's
        auto-generated primary browser-journey slot (the same structural
        reason an authenticated capability can't be either -- the generic
        journey driver only knows how to type text and click, not attach
        a file); never pass slot_id/selector for the upload capability.
        A real max_bytes limit is enforced -- rejected with a real 400,
        not silently truncated or accepted into memory unbounded."""
        upload_body = (
            "def handle(request):\n"
            "    f = request.files.get('file')\n"
            "    if f is None or not f.filename:\n"
            "        return 400, {'error': 'a file is required (multipart/form-data field \\'file\\')'}\n"
            "    raw = f.read()\n"
            f"    if len(raw) > {max_bytes}:\n"
            f"        return 400, {{'error': 'file exceeds the {max_bytes}-byte limit'}}\n"
            f"    record = _shared.save_blob(raw, f.mimetype or 'application/octet-stream', f.filename, "
            f"index_filename={index_filename!r})\n"
            "    return 201, record\n"
        )
        self.add_capability(upload_num, "Upload Document", upload_route, "POST", upload_body,
                             output_fields=("id", "content_type", "filename", "size", "created_at"),
                             side_effects=("creates_record",), data_filename=index_filename,
                             extra_error_codes=("VALIDATION_ERROR",))

        download_body = (
            "def handle(request):\n"
            "    blob_id = request.args.get('id')\n"
            f"    raw, record = _shared.load_blob(blob_id, index_filename={index_filename!r})\n"
            "    if raw is None:\n        return 404, {'error': f'no document with id ' + repr(blob_id)}\n"
            "    return 200, {'__binary__': True, 'content_type': record['content_type'], 'data': raw}\n"
        )
        self.add_capability(download_num, "Download Document", download_route, "GET", download_body,
                             data_filename=index_filename, extra_error_codes=("NOT_FOUND",))

        list_body = "def handle(request):\n    return 200, {'documents': _load()}\n"
        self.add_capability(list_num, "List Documents", list_route, "GET", list_body,
                             output_fields=("documents",), data_filename=index_filename)

    def add_ranking_capability(self, num: str, name: str, route: str, rank_field: str,
                                data_filename=None, descending=True, default_limit=10,
                                limit_param="limit"):
        """Real Rankings/leaderboard: sort the whole collection by
        rank_field (real, computed on every request -- not a cached or
        precomputed column that could drift) and return the top N with a
        real 1-based `rank` assigned, not just the raw sorted rows. Closes
        the missing-capability register's #1 entry in
        COVERAGE_EXPANSION_REPORT.md Part 4 (real evidence: multiplayer_
        game's own player scores and personal_finance's statements both
        needed exactly this, independently, in the prior round -- the same
        two-real-uses bar that justified every other engine that round,
        judged just under the bar for a same-round 5th new engine and
        explicitly recorded rather than dropped; this round's own next-
        five-capabilities selection closes it for real).

        A non-numeric or missing rank_field value sorts as 0, not a
        crash -- real, messy data (an unscored player, a blank statement
        total) degrades gracefully to the bottom/top of the list rather
        than a 500."""
        limit_default_literal = repr(default_limit)
        body = (
            "def handle(request):\n"
            "    rows = _load()\n"
            f"    try:\n        limit = max(1, min(1000, int(request.args.get({limit_param!r}, "
            f"{limit_default_literal}) or {limit_default_literal})))\n"
            f"    except (TypeError, ValueError):\n        limit = {limit_default_literal}\n"
            "    def _rank_value(row):\n"
            f"        v = row.get({rank_field!r}, 0)\n"
            "        return v if isinstance(v, (int, float)) else 0\n"
            f"    ranked = sorted(rows, key=_rank_value, reverse={descending!r})[:limit]\n"
            "    ranked = [{**r, 'rank': i} for i, r in enumerate(ranked, start=1)]\n"
            "    return 200, {'rankings': ranked}\n"
        )
        self.add_capability(num, name, route, "GET", body,
                             output_fields=("rankings",), data_filename=data_filename)

    def reuse_capability_verbatim(self, source_shelf_dir: Path, cap_id: str, slot_id=None,
                                    selector=None, side_effects=()):
        """Copies another app's real capability -- its shelf record AND its
        real implementation payload -- byte-for-byte unmodified into this
        app's own shelf, same capability id. This is exactly the mechanism
        the compatibility audit's Test A proved works live (a foreign
        capability file, dropped unmodified into a different app's modules/
        folder, runs correctly through the same host loader); this method
        does it for real, at generation time, for a capability this app
        actually ships with, not a disposable experiment."""
        src_cap_json = source_shelf_dir / "capabilities" / f"{cap_id}.json"
        src_impl_dir = source_shelf_dir / "implementations" / cap_id
        dst_cap_json = self.caps / f"{cap_id}.json"
        dst_impl_dir = self.impls / cap_id
        shutil.copy2(src_cap_json, dst_cap_json)
        if dst_impl_dir.exists():
            shutil.rmtree(dst_impl_dir)
        shutil.copytree(src_impl_dir, dst_impl_dir)
        self.required_caps.append(cap_id)
        if slot_id:
            cap = json.loads(src_cap_json.read_text())
            self.slots.append(slot(slot_id, cap_id, cap["name"], selector or f"#{slot_id}",
                                    side_effects=side_effects))

    def add_notification_capabilities(self, list_num: str, create_num: str, mark_read_num: str,
                                       list_route="/api/notifications",
                                       create_route="/api/notifications",
                                       mark_read_route="/api/notifications/read",
                                       data_filename="notifications.json"):
        """Generic Notification capability pair -- create + list + mark-read --
        that does not exist ANYWHERE in the original 43-app library (real
        audit finding). Any other capability that wants to notify someone
        appends to the same data file and MUST declare a dependency on
        `create_num`'s capability id (build.py now enforces this, see
        stage1_assemble's dependency check). Returns the create capability's
        id so callers can declare it as a dependency."""
        self.add_capability(list_num, "List Notifications", list_route, "GET",
            "def handle(request):\n"
            "    recipient = request.args.get('recipient')\n"
            "    rows = _load()\n"
            "    if recipient:\n        rows = [r for r in rows if r['recipient'] == recipient]\n"
            "    return 200, {'notifications': rows}\n",
            output_fields=("notifications",), data_filename=data_filename)

        self.add_capability(create_num, "Create Notification", create_route, "POST",
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    recipient = (body.get('recipient') or '').strip()\n"
            "    message = (body.get('message') or '').strip()\n"
            "    if not recipient or not message:\n        return 400, {'error': 'recipient and message are required'}\n"
            "    rows = _load()\n"
            "    next_id = (max([r['id'] for r in rows], default=0)) + 1\n"
            "    note = {'id': next_id, 'recipient': recipient, 'message': message, 'read': False}\n"
            "    rows.append(note)\n    _save(rows)\n    return 201, note\n",
            output_fields=("id", "recipient", "message", "read"),
            required_input=("recipient", "message"), side_effects=("creates_record",),
            data_filename=data_filename)

        self.add_capability(mark_read_num, "Mark Notification Read", mark_read_route, "POST",
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    nid = body.get('id')\n    rows = _load()\n"
            "    for r in rows:\n"
            "        if r['id'] == nid:\n            r['read'] = True\n            _save(rows)\n            return 200, r\n"
            "    return 404, {'error': f'no notification with id ' + repr(nid)}\n",
            output_fields=("id", "read"), required_input=("id",), side_effects=("updates_record",),
            data_filename=data_filename)
        return f"CAP-{create_num}"

    def add_calendar_event_capabilities(self, list_num: str, create_num: str, delete_num: str,
                                         list_route="/api/events", create_route="/api/events",
                                         delete_route="/api/events/delete",
                                         data_filename=None, slot_id=None, selector=None,
                                         extra_fields=()):
        """Generic Calendar/Event capability -- does not exist anywhere in the
        original 43-app library either (real audit finding): both
        calendar_and_scheduling and appointment_booking store a raw,
        unvalidated date string with no shared date-handling logic. This
        engine actually validates real ISO-8601 timestamps (rejecting
        garbage with a 400, not silently storing it) -- a genuine
        capability upgrade, not just a rename. Returns the create
        capability's id.

        extra_fields: additional record fields beyond title/start/end, each
        a dict {"name", "input_key" (None = not read from the request body,
        just a literal default), "default", "cast" ("int"/"float"/None)} --
        e.g. a capacity field an RSVP capability elsewhere will read/adjust,
        or an "attendees" counter that always starts at its default."""
        df = data_filename or self.data_filename
        self.add_capability(list_num, "List Events", list_route, "GET",
            "def handle(request):\n    return 200, {'events': _load()}\n",
            output_fields=("events",), data_filename=df)

        extra_lines = []
        for f in extra_fields:
            if f.get("input_key"):
                cast = {"int": "int", "float": "float"}.get(f.get("cast"), "")
                if cast:
                    extra_lines.append(
                        f"    try:\n        {f['name']}_val = {cast}(body.get('{f['input_key']}', {f['default']!r}) or {f['default']!r})\n"
                        f"    except (TypeError, ValueError):\n        {f['name']}_val = {f['default']!r}\n")
                else:
                    extra_lines.append(f"    {f['name']}_val = body.get('{f['input_key']}', {f['default']!r})\n")
            else:
                extra_lines.append(f"    {f['name']}_val = {f['default']!r}\n")
        extra_assigns = "".join(f"    ev[{f['name']!r}] = {f['name']}_val\n" for f in extra_fields)
        extra_output = tuple(f["name"] for f in extra_fields)

        self.add_capability(create_num, "Create Event", create_route, "POST",
            "import datetime\n"
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    title = (body.get('title') or '').strip()\n"
            "    if not title:\n        return 400, {'error': 'title is required'}\n"
            "    start_raw = body.get('start') or ''\n"
            "    try:\n        start_dt = datetime.datetime.fromisoformat(start_raw)\n"
            "    except (TypeError, ValueError):\n        return 400, {'error': f'start is not a valid ISO-8601 timestamp: {start_raw!r}'}\n"
            "    end_raw = body.get('end') or ''\n"
            "    end_dt = None\n"
            "    if end_raw:\n"
            "        try:\n            end_dt = datetime.datetime.fromisoformat(end_raw)\n"
            "        except (TypeError, ValueError):\n            return 400, {'error': f'end is not a valid ISO-8601 timestamp: {end_raw!r}'}\n"
            "        if end_dt < start_dt:\n            return 400, {'error': 'end must not be before start'}\n"
            + "".join(extra_lines) +
            "    events = _load()\n"
            "    next_id = (max([e['id'] for e in events], default=0)) + 1\n"
            "    ev = {'id': next_id, 'title': title, 'start': start_dt.isoformat(),\n"
            "          'end': end_dt.isoformat() if end_dt else None}\n"
            + extra_assigns +
            "    events.append(ev)\n    _save(events)\n    return 201, ev\n",
            output_fields=("id", "title", "start", "end") + extra_output,
            required_input=("title", "start"),
            side_effects=("creates_record",), data_filename=df, slot_id=slot_id, selector=selector)

        self.add_capability(delete_num, "Delete Event", delete_route, "POST",
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    eid = body.get('id')\n    events = _load()\n"
            "    remaining = [e for e in events if e['id'] != eid]\n"
            "    if len(remaining) == len(events):\n        return 404, {'error': f'no event with id ' + repr(eid)}\n"
            "    _save(remaining)\n    return 200, {'id': eid, 'deleted': True}\n",
            output_fields=("id", "deleted"), required_input=("id",),
            side_effects=("deletes_record",), data_filename=df)
        return f"CAP-{create_num}"

    def add_symmetric_relationship_capability(self, num: str, name: str, route: str,
                                               from_field: str, to_field: str, positive_field: str,
                                               match_field: str = "match", slot_id=None, selector=None):
        """Generic capability: records a one-way proposal (from -> to, positive
        or not) and reports whether the reverse proposal (to -> from, positive)
        already exists -- a mutual-interest/reciprocity check. This is the
        real shape behind dating's swipe/match rule, generalized so any
        mutual-connection domain (a follow-back, a connection request, a
        trade offer both sides must accept) reuses this generator instead of
        a fresh reciprocity search. Proven behaviourally identical to the
        original hand-written dating capability by direct regression test."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    from_id = body.get('{from_field}')\n    to_id = body.get('{to_field}')\n"
            f"    if from_id is None or to_id is None:\n"
            f"        return 400, {{'error': '{from_field} and {to_field} are required'}}\n"
            f"    positive = bool(body.get('{positive_field}', True))\n"
            "    rows = _load()\n"
            f"    rows.append({{'{from_field}': from_id, '{to_field}': to_id, '{positive_field}': positive}})\n"
            "    _save(rows)\n"
            f"    mutual = any(r['{from_field}'] == to_id and r['{to_field}'] == from_id and r['{positive_field}']\n"
            "                 for r in rows) and positive\n"
            f"    return 200, {{'{from_field}': from_id, '{to_field}': to_id, '{positive_field}': positive, "
            f"'{match_field}': mutual}}\n"
        )
        output_fields = (from_field, to_field, positive_field, match_field)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(from_field, to_field), side_effects=("creates_record",),
                             slot_id=slot_id, selector=selector)

    def build_py_slug(self) -> str:
        """Exactly build.py's own choice.json/app_type -> template-filename
        algorithm (build.py:618/1520: app_type.lower().replace(' ', '_')
        .replace('/', '_')) -- NOT necessarily the same as this app's project
        directory slug (e.g. app_type 'e-commerce storefront' keeps its
        hyphen: 'e-commerce_storefront', while the project directory here is
        named 'e_commerce_storefront'). Using the wrong one here is exactly
        the 'BROKEN template not found' failure this comment is here to
        prevent regressing."""
        return self.app_type.lower().replace(" ", "_").replace("/", "_")

    def write_template(self, primary_journey: dict, port: int = 5000):
        template = {
            "accepted": True,
            "app_type": self.app_type,
            "required_capabilities": self.required_caps,
            "interface_slots": self.slots,
            "entry_route": "/",
            "entry_screen_name": "Home",
            "start_command": ["python3", f"modules/{self.host_cap_id()}/app.py"],
            "port": port,
            "health_endpoint": "/health",
            "test_command": ["python3", "-c",
                              f"print('real {self.app_type} app -- no template-level tests declared "
                              f"beyond build.py\\'s own proving run')"],
            "primary_journey": primary_journey,
        }
        write_json(self.templates / f"{self.build_py_slug()}.json", template)

    def write_choice(self, branding_name: str, color: str = "#2f6f9f"):
        write(self.dir / "APPS_LIST.md", f"# Approved app types\n\n- {self.app_type}\n")
        write_json(self.dir / "choice.json", {
            "app_type": self.app_type,
            "skin_id": "skin-001",
            "skin_version": "1.0.0",
            "arrangement": [{"slot": s["slot_id"], "position": "center"} for s in self.slots],
            "branding": {"name": branding_name, "color": color},
        })

    def finish(self, index_html: str, primary_journey: dict, branding_name: str, port: int = 5000):
        self.add_host(index_html)
        self.write_template(primary_journey, port=port)
        self.write_choice(branding_name)
        print(f"{self.app_type!r} fixtures written under {self.dir}")
