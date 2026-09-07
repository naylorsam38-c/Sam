"""HMAC request verification — this agent's independent copy of the check
in workstation_core.security.verify_agent_request. Deliberately duplicated
rather than imported (see workstation_core/__init__.py's note and
docs/SECURITY.md): the agent must not depend on control-plane code for its
own enforcement, so a bug or compromise in the control plane's copy can
never silently weaken the agent's.
"""

from __future__ import annotations

import hashlib
import hmac
import time


def sign(request_id: str, operation: str, timestamp: int, token: str) -> str:
    message = f"{request_id}:{operation}:{timestamp}".encode()
    return hmac.new(token.encode(), message, hashlib.sha256).hexdigest()


def verify(
    request_id: str, operation: str, timestamp: int, signature: str, token: str, max_age_seconds: int,
) -> tuple[bool, str]:
    if abs(time.time() - timestamp) > max_age_seconds:
        return False, "request timestamp outside allowed window (possible replay)"
    expected = sign(request_id, operation, timestamp, token)
    if not hmac.compare_digest(expected, signature):
        return False, "invalid signature"
    return True, "ok"
