"""
In-process async event bus connecting workers within one session.

Deliberately tiny and swappable: today it's asyncio callbacks; to split workers
across processes/GPUs (spec §9) replace `publish` with a ZeroMQ/Redis Streams
transport — the worker code does not change because it only calls bus.publish /
subscribes via handlers.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, Any

Handler = Callable[[Any], Awaitable[None]]


class Bus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = defaultdict(list)

    def on(self, topic: str, handler: Handler) -> None:
        self._subs[topic].append(handler)

    async def publish(self, topic: str, payload: Any) -> None:
        """Fan out to every subscriber. A handler that raises is logged and
        isolated: with return_exceptions=False one bad subscriber killed the
        publishing worker's loop and took the whole turn with it."""
        handlers = self._subs.get(topic, [])
        if not handlers:
            return
        results = await asyncio.gather(*(h(payload) for h in handlers),
                                       return_exceptions=True)
        for h, r in zip(handlers, results):
            if isinstance(r, asyncio.CancelledError):
                raise r                     # cancellation must still propagate
            if isinstance(r, BaseException):
                from .worker import log
                log("bus", "error", "subscriber failed", topic=topic,
                    handler=getattr(h, "__qualname__", repr(h)), error=repr(r))


# Canonical topics (keep in one place so workers never disagree on strings)
class Topic:
    USER_AUDIO = "user_audio"          # raw frames from mic
    VAD = "vad"                        # speech start/stop
    TRANSCRIPT_PARTIAL = "tx_partial"
    TRANSCRIPT_FINAL = "tx_final"
    BRAIN_REQUEST = "brain_request"    # final transcript -> Command Desk
    RESPONSE_PHRASE = "response_phrase"  # streamed phrase chunk -> TTS
    TTS_AUDIO = "tts_audio"            # audio chunk -> renderer + publisher
    RENDER_FRAME = "render_frame"      # video frame -> publisher
    BARGE_IN = "barge_in"              # cancel everything downstream
    STATE = "state"
