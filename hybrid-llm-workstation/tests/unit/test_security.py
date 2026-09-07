"""Unit tests for workstation_core.security (spec section 15)."""

import time

import pytest

from workstation_core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_agent_request,
    verify_password,
)
from workstation_core.security import InvalidTokenError
from workstation_core.security import sign_agent_request


def test_password_hash_is_not_plaintext_and_verifies():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong-password", hashed)


def test_password_over_72_bytes_is_rejected_not_silently_truncated():
    with pytest.raises(ValueError):
        hash_password("x" * 100)


def test_jwt_round_trip():
    token = create_access_token("user-1", "sam")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["username"] == "sam"


def test_jwt_tampering_is_rejected():
    token = create_access_token("user-1", "sam")
    tampered = token[:-4] + ("0" if token[-4] != "0" else "1") + token[-3:]
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


def test_jwt_garbage_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-jwt-at-all")


def test_agent_request_signature_round_trip():
    now = int(time.time())
    sig = sign_agent_request("req-1", "read_file", now, "secret")
    ok, reason = verify_agent_request("req-1", "read_file", now, sig, "secret")
    assert ok, reason


def test_agent_request_signature_rejects_wrong_secret():
    now = int(time.time())
    sig = sign_agent_request("req-1", "read_file", now, "secret-a")
    ok, _ = verify_agent_request("req-1", "read_file", now, sig, "secret-b")
    assert not ok


def test_agent_request_signature_rejects_tampered_operation():
    now = int(time.time())
    sig = sign_agent_request("req-1", "read_file", now, "secret")
    ok, _ = verify_agent_request("req-1", "run_command", now, sig, "secret")
    assert not ok


def test_agent_request_signature_rejects_stale_timestamp():
    sig = sign_agent_request("req-1", "read_file", 1, "secret")
    ok, reason = verify_agent_request("req-1", "read_file", 1, sig, "secret")
    assert not ok
    assert "timestamp" in reason


def test_agent_request_signature_accepts_current_timestamp():
    now = int(time.time())
    sig = sign_agent_request("req-1", "read_file", now, "secret")
    ok, _ = verify_agent_request("req-1", "read_file", now, sig, "secret")
    assert ok
