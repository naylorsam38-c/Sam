"""
Automatic quality ladder (spec §15).

Degrade *visuals* before ever sacrificing speech, timing, stability or the
session. The controller watches drift, dropped frames, render latency and GPU
memory, and steps down/up a level with hysteresis.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Level:
    n: int
    width: int
    height: int
    fps: int
    enhancement: str      # full | reduced | none
    motion: str           # full | essential | lipsync_only
    note: str


LADDER = {
    3: Level(3, 720, 1280, 30, "full", "full", "full motion + enhancement"),
    2: Level(2, 720, 1280, 25, "reduced", "full", "reduced enhancement"),
    1: Level(1, 512, 910, 25, "none", "essential", "lip sync + essential motion"),
    0: Level(0, 512, 910, 25, "none", "lipsync_only",
             "pre-rendered idle loop + lightweight local mouth/viseme"),
}


class QualityController:
    def __init__(self, start: int = 3, drift_budget_ms: int = 80):
        self.level = start
        self.drift_budget = drift_budget_ms
        self._cooldown = 0

    def observe(self, *, drift_ms: float, dropped_frames: int,
                render_latency_ms: float, gpu_mem_frac: float) -> int:
        """Return the (possibly changed) level. Speech/timing are never touched;
        only resolution/fps/enhancement move."""
        if self._cooldown > 0:
            self._cooldown -= 1
            return self.level
        stressed = (abs(drift_ms) > self.drift_budget or dropped_frames > 2
                    or render_latency_ms > (1000 / max(1, LADDER[self.level].fps))
                    or gpu_mem_frac > 0.92)
        relaxed = (abs(drift_ms) < self.drift_budget * 0.5 and dropped_frames == 0
                   and gpu_mem_frac < 0.7)
        if stressed and self.level > 0:
            self.level -= 1
            self._cooldown = 5 * LADDER[self.level].fps      # ~5s hysteresis
        elif relaxed and self.level < 3:
            self.level += 1
            self._cooldown = 5 * LADDER[self.level].fps
        return self.level

    @property
    def current(self) -> Level:
        return LADDER[self.level]
