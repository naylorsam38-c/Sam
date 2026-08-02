"""
Command Desk connector (spec: brain is EXTERNAL, never rebuilt).

Sends the final transcript to the existing Command Desk endpoint, streams the
response back, and forwards it as phrase-chunked PresentationRequests to the
session. Also POSTs an "interrupted" notice when a turn is barged-in (spec §3).

The Command Desk brain, agents, memory and oversight are untouched — this worker
only transports text in and streamed text out.
"""
from __future__ import annotations

from typing import Awaitable, Callable

from ..config import BrainCfg
from ..protocol import PresentationRequest
from ..worker import BaseWorker, log

Present = Callable[[PresentationRequest], Awaitable[None]]


class BrainConnector(BaseWorker):
    name = "brain"

    def __init__(self, cfg: BrainCfg, present: Present, **kw):
        super().__init__(maxsize=8, item_timeout=cfg.timeout_s + 5, **kw)
        self.cfg = cfg
        self.present = present

    async def handle(self, item: dict) -> None:
        if item.get("interrupted"):
            await self._notify_interrupt(item)
            return
        await self._stream_response(item)

    async def _stream_response(self, item: dict) -> None:
        sid, tid, text = item["session_id"], item["turn_id"], item["text"]
        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.cfg.timeout_s) as c:
                async with c.stream("POST", self.cfg.endpoint,
                                    json={"session_id": sid, "text": text,
                                          "stream": True}) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_text():
                        if chunk:
                            await self.present(PresentationRequest(
                                session_id=sid, turn_id=tid, text=chunk, final=False))
            await self.present(PresentationRequest(
                session_id=sid, turn_id=tid, text="", final=True))
        except Exception as e:  # Command Desk timeout/unreachable (spec §20)
            log(self.name, "error", "command desk failed", error=repr(e))
            await self.present(PresentationRequest(
                session_id=sid, turn_id=tid,
                text="Sorry, I lost my connection for a second. Could you say that again?",
                final=True))

    async def _notify_interrupt(self, item: dict) -> None:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as c:
                await c.post(self.cfg.endpoint.rstrip("/") + "/interrupted",
                             json={"session_id": item["session_id"],
                                   "turn_id": item.get("turn_id")})
        except Exception as e:
            log(self.name, "warn", "interrupt notice failed", error=repr(e))

    async def on_timeout(self, item: dict) -> None:
        log(self.name, "warn", "brain timeout", turn=item.get("turn_id"))
