"""Gateway authentication.

The original build issued a valid signed token to anyone who set an `x-user-id`
header — self-asserted identity. These tests pin the fix: credentials are
required, the user id comes from the credential, and an unsafe signing secret
stops the process at startup rather than at incident-review time.
"""
import pytest

from aura.gateway import auth


# ── signing secret ──────────────────────────────────────────────────────────
def test_default_secret_refuses_to_start():
    with pytest.raises(auth.InsecureConfiguration, match="default"):
        auth.validate_secret(auth.DEFAULT_SECRET)


def test_empty_secret_refuses_to_start():
    with pytest.raises(auth.InsecureConfiguration):
        auth.validate_secret("")


def test_short_secret_refuses_to_start():
    with pytest.raises(auth.InsecureConfiguration, match="chars"):
        auth.validate_secret("tooshort")


def test_strong_secret_accepted():
    s = "a" * 64
    assert auth.validate_secret(s) == s


def test_dev_mode_bypasses_secret_validation():
    """Local development must still run — but only under an explicit flag."""
    assert auth.validate_secret("", dev=True) == ""


# ── client authentication ───────────────────────────────────────────────────
def test_header_alone_is_not_identity(monkeypatch):
    monkeypatch.setenv("AURA_API_KEYS", "key-abc:alice")
    with pytest.raises(auth.AuthError, match="missing API key"):
        auth.authenticate_client(None, "alice")


def test_valid_key_returns_its_mapped_user(monkeypatch):
    monkeypatch.setenv("AURA_API_KEYS", "key-abc:alice,key-def:bob")
    assert auth.authenticate_client("key-abc", None) == "alice"
    assert auth.authenticate_client("key-def", None) == "bob"


def test_key_cannot_impersonate_another_user(monkeypatch):
    monkeypatch.setenv("AURA_API_KEYS", "key-abc:alice")
    with pytest.raises(auth.AuthError, match="authorised for 'alice'"):
        auth.authenticate_client("key-abc", "bob")


def test_invalid_key_rejected(monkeypatch):
    monkeypatch.setenv("AURA_API_KEYS", "key-abc:alice")
    with pytest.raises(auth.AuthError, match="invalid API key"):
        auth.authenticate_client("wrong", None)


def test_no_configured_credentials_fails_closed(monkeypatch):
    """An unconfigured gateway must refuse everyone, not admit everyone."""
    monkeypatch.delenv("AURA_API_KEYS", raising=False)
    with pytest.raises(auth.AuthError, match="no client credentials"):
        auth.authenticate_client("anything", "alice")


def test_dev_mode_trusts_the_header(monkeypatch):
    monkeypatch.delenv("AURA_API_KEYS", raising=False)
    assert auth.authenticate_client(None, "alice", dev=True) == "alice"


# ── token claims ────────────────────────────────────────────────────────────
def test_token_carries_required_claims():
    secret = "s" * 64
    tok = auth.issue(secret, "alice", ttl_s=60)
    payload = auth.verify(secret, tok["token"])
    assert payload["uid"] == "alice"
    assert payload["room"] == tok["room"]
    assert payload["jti"]


def test_token_with_stripped_claims_is_rejected():
    """A token whose payload verifies but lacks claims must not be trusted."""
    import base64
    import hashlib
    import hmac
    import json

    secret = "s" * 64
    body = base64.urlsafe_b64encode(
        json.dumps({"exp": 2 ** 31}).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    with pytest.raises(auth.TokenError, match="missing claim"):
        auth.verify(secret, f"{body}.{sig}")


def test_garbage_payload_rejected():
    secret = "s" * 64
    import base64
    import hashlib
    import hmac
    body = base64.urlsafe_b64encode(b"not json").decode().rstrip("=")
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    ).decode().rstrip("=")
    with pytest.raises(auth.TokenError, match="malformed payload"):
        auth.verify(secret, f"{body}.{sig}")
