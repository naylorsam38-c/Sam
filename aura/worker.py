"""
BaseWorker — the contract every Aura worker obeys (spec §8).

Each worker is an asyncio task with:
  - a bounded input queue (backpressure: drop-oldest or block, configurable)
  - health checks (last_beat + alive)
  - per-item timeout
  - cooperative cancellation (barge-in cancels in-flight work)
  - structured JSON logs
  - metrics counters
  - supervised restart with backoff

Workers are transport-agnostic and run in one process today; each can be moved
to its own process/GPU later (spec §9) because they only touch queues.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any


def log(worker: str, level: str, msg: str, **kv: Any) -> None:
    """Structured single-line JSON log."""
    rec = {"ts": round(time.time(), 3), "worker": worker, "level": level, "msg": msg, **kv}
    sys.stdout.write(json.dumps(rec) + "\n")
    sys.stdout.flush()


@dataclass
class WorkerMetrics:
    processed: int = 0
    errors: int = 0
    dropped: int = 0
    restarts: int = 0
    last_latency_ms: float = 0.0
    queue_depth: int = 0
    extra: dict[str, float] = field(default_factory=dict)


class BaseWorker:
    name = "worker"

    def __init__(self, *, maxsize: int = 8, item_timeout: float = 10.0,
                 on_full: str = "drop_oldest"):
        self.q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.item_timeout = item_timeout
        self.on_full = on_full            # "drop_oldest" | "block"
        self.metrics = WorkerMetrics()
        self._task: asyncio.Task | None = None
        self._current: asyncio.Task | None = None
        self._beat = time.time()
        self._stop = asyncio.Event()

    # ── lifecycle ──────────────────────────────────────────────────────────
    async def start(self) -> None:
        await self.setup()
        self._task = asyncio.create_task(self._run(), name=self.name)
        log(self.name, "info", "started")

    async def setup(self) -> None:
        """Warm-up / model load. Override. Must be idempotent."""

    async def teardown(self) -> None:
        """Release resources. Override."""

    async def stop(self) -> None:
        self._stop.set()
        self.cancel_current()
        if self._task:
            self._task.cancel()
        await self.teardown()
        log(self.name, "info", "stopped")

    # ── input / backpressure ───────────────────────────────────────────────
    async def submit(self, item: Any) -> bool:
        if self.q.full():
            if self.on_full == "drop_oldest":
                try:
                    self.q.get_nowait()
                    self.metrics.dropped += 1
                except asyncio.QueueEmpty:
                    pass
            else:  # block
                await self.q.put(item)
                return True
        self.q.put_nowait(item)
        return True

    def cancel_current(self) -> None:
        """Barge-in hook: abort the item being processed right now."""
        if self._current and not self._current.done():
            self._current.cancel()

    # ── health ─────────────────────────────────────────────────────────────
    def healthy(self, max_silence: float = 30.0) -> bool:
        return (time.time() - self._beat) < max_silence and (
            self._task is not None and not self._task.done())

    # ── main loop with supervised restart ──────────────────────────────────
    async def _run(self) -> None:
        backoff = 0.5
        while not self._stop.is_set():
            try:
                await self._loop()
            except asyncio.CancelledError:
                break
            except Exception as e:  # noqa: BLE001 — supervisor
                self.metrics.errors += 1
                self.metrics.restarts += 1
                log(self.name, "error", "loop crashed; restarting",
                    error=repr(e), backoff=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8.0)
            else:
                backoff = 0.5

    async def _loop(self) -> None:
        while not self._stop.is_set():
            item = await self.q.get()
            self._beat = time.time()
            self.metrics.queue_depth = self.q.qsize()
            t0 = time.time()
            self._current = asyncio.create_task(
                asyncio.wait_for(self.handle(item), self.item_timeout))
            try:
                await self._current
                self.metrics.processed += 1
            except asyncio.TimeoutError:
                self.metrics.errors += 1
                log(self.name, "warn", "item timeout", timeout=self.item_timeout)
                await self.on_timeout(item)
            except asyncio.CancelledError:
                log(self.name, "info", "item cancelled (barge-in)")
                await self.on_cancelled(item)
            finally:
                self.metrics.last_latency_ms = round((time.time() - t0) * 1000, 1)
                self._current = None

    # ── override these ──────────────────────────────────────────────────────
    async def handle(self, item: Any) -> None:
        raise NotImplementedError

    async def on_timeout(self, item: Any) -> None:
        pass

    async def on_cancelled(self, item: Any) -> None:
        pass
