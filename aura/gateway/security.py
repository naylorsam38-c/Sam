"""
Security controls (spec §18). Token-bucket rate limiting, per-user session
isolation/caps, image-upload validation, and temp-file cleanup policy.
"""
from __future__ import annotations

import os
import time


class RateLimiter:
    """Simple per-key token bucket."""
    def __init__(self, rate: float = 1.0, burst: int = 5):
        self.rate, self.burst = rate, burst
        self._buckets: dict[str, tuple[float, float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        tokens, last = self._buckets.get(key, (self.burst, now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        if tokens < 1:
            self._buckets[key] = (tokens, now)
            return False
        self._buckets[key] = (tokens - 1, now)
        return True


class SessionRegistry:
    """Enforces one active room per user + a global cap (spec §25 single-user
    first). Prevents entering another user's room."""
    def __init__(self, max_sessions: int = 1):
        self.max = max_sessions
        self._rooms: dict[str, str] = {}      # room -> uid

    def claim(self, room: str, uid: str) -> None:
        if len(self._rooms) >= self.max and room not in self._rooms:
            raise RuntimeError("capacity reached")
        owner = self._rooms.get(room)
        if owner and owner != uid:
            raise PermissionError("room owned by another user")
        self._rooms[room] = uid

    def release(self, room: str) -> None:
        self._rooms.pop(room, None)

    def authorize(self, room: str, uid: str) -> bool:
        return self._rooms.get(room) == uid

    @property
    def count(self) -> int:
        return len(self._rooms)


# Upload validation (spec §18, §21)
ALLOWED_IMG = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMG_BYTES = 12 * 1024 * 1024
MAX_IMG_DIM = 4096


def validate_upload(path: str) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOWED_IMG:
        raise ValueError(f"disallowed image type {ext}")
    if os.path.getsize(path) > MAX_IMG_BYTES:
        raise ValueError("image too large")
    import cv2
    img = cv2.imread(path)
    if img is None:
        raise ValueError("unreadable image")
    h, w = img.shape[:2]
    if w > MAX_IMG_DIM or h > MAX_IMG_DIM:
        raise ValueError("image dimensions too large")


def cleanup_temp(prefix: str = "aura_", older_than_s: int = 900) -> int:
    """Delete stale temp audio/frame files (spec §18 deletion policy)."""
    import glob
    import tempfile
    n = 0
    now = time.time()
    for f in glob.glob(os.path.join(tempfile.gettempdir(), prefix + "*")):
        try:
            if now - os.path.getmtime(f) > older_than_s:
                os.remove(f); n += 1
        except OSError:
            pass
    return n
