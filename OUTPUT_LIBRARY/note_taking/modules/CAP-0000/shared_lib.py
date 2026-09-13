"""modules/CAP-0000/shared_lib.py -- the Common Capability Contract's real
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
