"""
Session orchestrator — one per connected user.

Owns the state machine, the drift meter, the per-turn metrics, and the barge-in
logic. It wires worker outputs (via the Bus) into state transitions and client
events. Workers are injected so the orchestrator stays testable and transport-
agnostic.
"""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

from .bus import Bus, Topic
from .config import Config
from .metrics import DriftMeter, TurnMetrics
from .phrasing import PhraseChunker
from .protocol import Envelope, Event, PresentationRequest, State
from .state import StateMachine
from .worker import log

Sender = Callable[[Envelope], Awaitable[None]]   # push event to client data channel


class Session:
    def __init__(self, session_id: str, cfg: Config, bus: Bus, send: Sender,
                 workers: dict):
        self.id = session_id
        self.cfg = cfg
        self.bus = bus
        self.send = send
        self.workers = workers          # {"tts":..., "render":..., "brain":..., ...}
        self.drift = DriftMeter(cfg.drift_budget_ms)
        self.chunker = PhraseChunker()
        self.turn: TurnMetrics | None = None
        self.sm = StateMachine(on_change=self._emit_state_sync)
        self._speaking_turn: str | None = None
        self._loop = asyncio.get_event_loop()
        self._wire()

    # ── event emission ──────────────────────────────────────────────────────
    def _emit_state_sync(self, prev: State, cur: State) -> None:
        log("session", "info", "state", session=self.id, prev=prev.value, cur=cur.value)
        r = self.workers.get("render")           # keep idle animation in sync w/ state
        if r is not None and hasattr(r, "set_idle_state"):
            r.set_idle_state(cur.value)
        asyncio.create_task(self.send(Envelope(
            type=Event.STATE, session_id=self.id,
            turn_id=self.turn.turn_id if self.turn else None,
            data={"prev": prev.value, "state": cur.value})))

    async def emit(self, etype: Event, **data) -> None:
        await self.send(Envelope(type=etype, session_id=self.id,
                                 turn_id=self.turn.turn_id if self.turn else None,
                                 data=data))

    # ── bus wiring ──────────────────────────────────────────────────────────
    def _wire(self) -> None:
        self.bus.on(Topic.VAD, self._on_vad)
        self.bus.on(Topic.TRANSCRIPT_PARTIAL, self._on_partial)
        self.bus.on(Topic.TRANSCRIPT_FINAL, self._on_final)
        self.bus.on(Topic.RESPONSE_PHRASE, self._on_phrase)
        self.bus.on(Topic.RENDER_FRAME, self._on_frame)

    # ── inbound: user speech ────────────────────────────────────────────────
    async def _on_vad(self, ev: dict) -> None:
        if ev["kind"] == "start":
            # barge-in if we're mid-speech and this turn is interruptible
            if self.sm.state in (State.SPEAKING, State.STARTING_SPEECH):
                await self.barge_in()
            self.turn = TurnMetrics(self.id, turn_id=_tid())
            self.turn.mark("vad_start")
            self.sm.to(State.USER_SPEAKING)
        elif ev["kind"] == "stop":
            if self.turn:
                self.turn.mark("vad_end")
            self.sm.to(State.THINKING)

    async def _on_partial(self, ev: dict) -> None:
        await self.emit(Event.PARTIAL_TRANSCRIPT, text=ev["text"])

    async def _on_final(self, ev: dict) -> None:
        if self.turn:
            self.turn.mark("stt_final")
        await self.emit(Event.FINAL_TRANSCRIPT, text=ev["text"])
        # hand to Command Desk (external brain) — never rebuilt here
        if self.turn:
            self.turn.mark("brain_request")
        await self.workers["brain"].submit(
            {"session_id": self.id, "turn_id": self.turn.turn_id if self.turn else _tid(),
             "text": ev["text"]})

    # ── inbound: brain response (streamed phrases) ──────────────────────────
    async def present(self, req: PresentationRequest) -> None:
        """Entry the brain connector calls for each streamed chunk."""
        req.validate()
        if self.turn and self.turn.first_token is None:
            self.turn.mark("first_token")
        self._speaking_turn = req.turn_id
        if self.sm.state == State.THINKING:
            self.sm.to(State.STARTING_SPEECH)
        await self.emit(Event.RESPONSE_TEXT, text=req.text)
        for phrase in self.chunker.feed(req.text):
            await self._speak(phrase, req)
        if req.final:
            rest = self.chunker.flush()
            if rest:
                await self._speak(rest, req)

    async def _speak(self, phrase: str, req: PresentationRequest) -> None:
        if self.sm.state == State.STARTING_SPEECH:
            self.sm.to(State.SPEAKING)
        await self.workers["tts"].submit({
            "session_id": self.id, "turn_id": req.turn_id, "text": phrase,
            "voice": req.voice, "emotion": req.emotion, "intensity": req.intensity,
            "gesture": req.gesture})

    async def _on_phrase(self, ev: dict) -> None:  # reserved for external drivers
        pass

    # ── inbound: rendered frames ────────────────────────────────────────────
    async def _on_frame(self, ev: dict) -> None:
        if self.turn and self.turn.first_rendered_frame is None:
            self.turn.mark("first_rendered_frame")
        d = self.drift.sample(ev["audio_pts"], ev["video_pts"])
        if self.drift.over_budget:
            await self.emit(Event.DRIFT, drift_ms=d, over_budget=True)

    # ── barge-in (spec §3) ──────────────────────────────────────────────────
    async def barge_in(self) -> None:
        self.sm.to(State.INTERRUPTED)
        # 1) stop TTS generation, 2) discard unplayed audio, 3) cancel frames
        for w in ("tts", "render"):
            self.workers[w].cancel_current()
            _drain(self.workers[w].q)
        await self.bus.publish(Topic.BARGE_IN, {"session_id": self.id})
        # 4) notify Command Desk the previous response was interrupted
        await self.workers["brain"].submit(
            {"session_id": self.id, "turn_id": self._speaking_turn,
             "interrupted": True})
        if self.turn:
            self.turn.interruptions += 1
        await self.emit(Event.INTERRUPTED, turn_id=self._speaking_turn)
        self.sm.to(State.RECOVERING)
        self.chunker.flush()
        self.sm.to(State.LISTENING)      # 5) back to attentive listening

    async def close(self) -> None:
        if self.turn:
            self.turn.mark("first_published_frame")  # finalize whatever we have


def _tid() -> str:
    import uuid
    return uuid.uuid4().hex[:12]


def _drain(q: asyncio.Queue) -> None:
    try:
        while True:
            q.get_nowait()
    except asyncio.QueueEmpty:
        pass
