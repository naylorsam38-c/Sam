"""
Renderer interface + shared types.

Every renderer (CPU fallback, MuseTalk GPU, ...) implements `Renderer` so the
avatar worker can hot-swap them per the quality ladder (spec §15). Audio is the
master clock: `speaking_frames` yields (bgr_frame, audio_pts_seconds) pairs so
video PTS is always derived from an audio timestamp (spec §5).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol

import numpy as np


@dataclass
class FaceAnchors:
    """Where features live in the source image (used by the CPU fallback and by
    landmark stabilisation). GPU renderers detect these themselves."""
    width: int
    height: int
    mouth: tuple[int, int]
    mouth_spread: tuple[int, int]
    left_eye: tuple[int, int]
    right_eye: tuple[int, int]
    eye_box: tuple[int, int]


# Anchors for the bundled Nova portrait (assets/nova.png, 500x620).
NOVA = FaceAnchors(500, 620, (248, 305), (42, 27), (208, 222), (288, 222), (26, 16))


class Renderer(Protocol):
    level: int   # quality ladder level this renderer serves

    def idle_frame(self, state: str, t: float) -> np.ndarray:
        """A single 'alive' frame for IDLE/LISTENING/THINKING/etc."""

    def speaking_frames(self, wav_path: str) -> Iterator[tuple[np.ndarray, float]]:
        """Yield (frame, audio_pts_s) locked to the given speech audio."""

    def warmup(self) -> None:
        ...
