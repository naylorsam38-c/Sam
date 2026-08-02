"""
Per-turn metrics (spec §19). One TurnMetrics per response turn; the session
finalizes it and can push a TIMING event to the client and a Prometheus line.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Optional


def _now() -> float:
    return time.time()


@dataclass
class TurnMetrics:
    session_id: str
    turn_id: str
    vad_start: Optional[float] = None
    vad_end: Optional[float] = None
    stt_start: Optional[float] = None
    stt_final: Optional[float] = None
    brain_request: Optional[float] = None
    first_token: Optional[float] = None
    first_tts_audio: Optional[float] = None
    first_rendered_frame: Optional[float] = None
    first_published_frame: Optional[float] = None
    dropped_frames: int = 0
    max_queue_depth: int = 0
    gpu_util: float = 0.0
    gpu_mem_mb: float = 0.0
    av_drift_ms: float = 0.0
    interruptions: int = 0
    reconnects: int = 0
    error_source: Optional[str] = None

    def mark(self, field_name: str) -> None:
        setattr(self, field_name, _now())

    @property
    def total_latency_ms(self) -> Optional[float]:
        if self.vad_end and self.first_published_frame:
            return round((self.first_published_frame - self.vad_end) * 1000, 1)
        return None

    def summary(self) -> dict:
        d = asdict(self)
        d["total_latency_ms"] = self.total_latency_ms
        return d


class DriftMeter:
    """Continuously compares the audio master clock against the video PTS."""
    def __init__(self, budget_ms: int = 80):
        self.budget_ms = budget_ms
        self.samples: list[float] = []

    def sample(self, audio_pts_s: float, video_pts_s: float) -> float:
        drift = (video_pts_s - audio_pts_s) * 1000.0
        self.samples.append(drift)
        if len(self.samples) > 300:
            self.samples.pop(0)
        return round(drift, 1)

    @property
    def current(self) -> float:
        return round(self.samples[-1], 1) if self.samples else 0.0

    @property
    def over_budget(self) -> bool:
        return abs(self.current) > self.budget_ms
