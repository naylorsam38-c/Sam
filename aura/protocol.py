"""
Aura wire + internal protocol.

Defines: session states, the internal presentation request (what Command Desk
sends the avatar), and the event envelope pushed to the client over the WebRTC
data channel. Pure data — no I/O — so every worker and test can share it.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


# ── Deterministic session states (spec §"session states") ──────────────────
class State(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    USER_SPEAKING = "USER_SPEAKING"
    THINKING = "THINKING"
    STARTING_SPEECH = "STARTING_SPEECH"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    RECOVERING = "RECOVERING"
    ERROR = "ERROR"


# ── Internal API: Command Desk -> avatar presentation service ───────────────
@dataclass
class PresentationRequest:
    """One thing for the avatar to say/perform. `text` may arrive in a stream
    of these (phrase chunks) sharing a session_id + turn_id."""
    session_id: str
    text: str
    turn_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    avatar: str = "nova"
    voice: str = "nova"
    emotion: str = "neutral"          # reassuring | happy | serious | ...
    intensity: float = 0.35           # 0..1 expression strength
    gesture: Optional[str] = None     # small_nod | head_tilt | ...
    interruptible: bool = True
    final: bool = True                # last chunk of this turn?

    def validate(self) -> "PresentationRequest":
        if not self.session_id:
            raise ValueError("session_id required")
        self.intensity = max(0.0, min(1.0, float(self.intensity)))
        if len(self.text) > 20000:
            raise ValueError("text too long")
        return self


# ── Events pushed to the client (data channel) ──────────────────────────────
class Event(str, Enum):
    STATE = "state"                   # {state}
    PARTIAL_TRANSCRIPT = "partial_transcript"
    FINAL_TRANSCRIPT = "final_transcript"
    RESPONSE_TEXT = "response_text"    # text the avatar is about to speak
    TIMING = "timing"                 # per-turn metric samples
    DRIFT = "drift"                   # measured av drift ms
    QUALITY = "quality"               # current quality level
    INTERRUPTED = "interrupted"
    ERROR = "error"


@dataclass
class Envelope:
    """Everything sent to the client is one of these (JSON over data channel)."""
    type: str
    session_id: str
    turn_id: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def json(self) -> dict:
        return asdict(self)


# ── Control messages: client -> gateway ─────────────────────────────────────
class Control(str, Enum):
    INTERRUPT = "interrupt"           # barge-in via UI button
    MUTE = "mute"
    UNMUTE = "unmute"
    SET_AVATAR = "set_avatar"
    TEXT_INPUT = "text_input"         # typed input instead of mic
    END_SESSION = "end_session"
