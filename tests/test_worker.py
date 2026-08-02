import asyncio

from aura.worker import BaseWorker


class Collector(BaseWorker):
    name = "collector"

    def __init__(self, **kw):
        super().__init__(**kw)
        self.seen = []
        self.cancelled = 0

    async def handle(self, item):
        if item == "slow":
            await asyncio.sleep(5)
        self.seen.append(item)

    async def on_cancelled(self, item):
        self.cancelled += 1


async def test_processes_items():
    w = Collector(maxsize=8)
    await w.start()
    await w.submit("a"); await w.submit("b")
    await asyncio.sleep(0.05)
    assert w.seen == ["a", "b"]
    assert w.metrics.processed >= 2
    assert w.healthy()
    await w.stop()


async def test_drop_oldest_backpressure():
    w = Collector(maxsize=2, on_full="drop_oldest")
    # do not start the loop, so the queue fills and eviction happens on submit
    await w.submit("1"); await w.submit("2"); await w.submit("3")
    assert w.metrics.dropped >= 1
    assert w.q.qsize() == 2


async def test_cancel_current_barge_in():
    w = Collector(maxsize=4, item_timeout=10)
    await w.start()
    await w.submit("slow")
    await asyncio.sleep(0.05)
    w.cancel_current()
    await asyncio.sleep(0.05)
    assert w.cancelled == 1
    await w.stop()
