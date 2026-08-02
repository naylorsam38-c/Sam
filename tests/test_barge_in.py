"""Barge-in: user speaks while avatar is SPEAKING -> everything downstream is
cancelled/drained, Command Desk is told, and we return to LISTENING (spec §3)."""
import asyncio

from aura.bus import Bus
from aura.config import Config
from aura.protocol import Event, State
from aura.session import Session


class FakeWorker:
    def __init__(self):
        self.q = asyncio.Queue()
        self.cancelled = False
        self.submitted = []

    def cancel_current(self):
        self.cancelled = True

    async def submit(self, item):
        self.submitted.append(item)


async def test_barge_in_cancels_and_recovers():
    events = []

    async def send(env):
        events.append(env)

    workers = {"tts": FakeWorker(), "render": FakeWorker(), "brain": FakeWorker()}
    session = Session("s1", Config(), Bus(), send, workers)

    # queue some in-flight audio/frames
    workers["tts"].q.put_nowait("phrase-audio")
    workers["render"].q.put_nowait("frame-batch")

    # drive to SPEAKING via a legal path
    session.sm.to(State.THINKING)
    session.sm.to(State.STARTING_SPEECH)
    session.sm.to(State.SPEAKING)
    session._speaking_turn = "turn-1"

    await session.barge_in()

    # 1-3: current work cancelled + queues drained
    assert workers["tts"].cancelled and workers["render"].cancelled
    assert workers["tts"].q.empty() and workers["render"].q.empty()
    # 4: Command Desk notified the previous response was interrupted
    assert any(m.get("interrupted") for m in workers["brain"].submitted)
    # client got an INTERRUPTED event
    assert any(e.type == Event.INTERRUPTED for e in events)
    # 5: back to attentive listening
    assert session.sm.state == State.LISTENING
    await asyncio.sleep(0)   # let state-emit tasks settle
