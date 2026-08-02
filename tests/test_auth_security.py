import time

import pytest

from aura.gateway import auth
from aura.gateway.security import RateLimiter, SessionRegistry

SECRET = "test-secret"


def test_issue_and_verify():
    tok = auth.issue(SECRET, "sam", ttl_s=60)
    payload = auth.verify(SECRET, tok["token"])
    assert payload["uid"] == "sam" and payload["room"] == tok["room"]


def test_tampered_token_rejected():
    tok = auth.issue(SECRET, "sam")
    body, sig = tok["token"].split(".")
    with pytest.raises(auth.TokenError):
        auth.verify(SECRET, body + "x." + sig)


def test_expired_token_rejected():
    tok = auth.issue(SECRET, "sam", ttl_s=-1)
    with pytest.raises(auth.TokenError):
        auth.verify(SECRET, tok["token"])


def test_wrong_secret_rejected():
    tok = auth.issue(SECRET, "sam")
    with pytest.raises(auth.TokenError):
        auth.verify("other", tok["token"])


def test_rate_limiter_blocks_after_burst():
    rl = RateLimiter(rate=0.0, burst=3)
    assert [rl.allow("k") for _ in range(4)] == [True, True, True, False]


def test_session_isolation():
    reg = SessionRegistry(max_sessions=1)
    reg.claim("room-a", "sam")
    assert reg.authorize("room-a", "sam")
    with pytest.raises(PermissionError):
        reg.claim("room-a", "mallory")          # cannot enter another user's room
    with pytest.raises(RuntimeError):
        reg.claim("room-b", "sam")              # capacity reached
    reg.release("room-a")
    reg.claim("room-b", "sam")                  # freed
