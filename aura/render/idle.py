"""
Fallback animation catalogue (spec §14, §11) — the "alive while not speaking"
states, provided by the CPU renderer so the avatar is never a frozen photo.

Required set: neutral idle · breathing · blink · attentive listening · thinking ·
faint smile · transition into speech · transition out of speech · renderer-failure
loop. Each maps to motion/expression parameters over the FallbackRenderer; on a
GPU host LivePortrait refines these, but the set exists with no GPU.
"""
from __future__ import annotations

from typing import Iterator

import numpy as np

from .fallback import FallbackRenderer

# state -> (mouth amplitude, sway bias, smile) tuning
CATALOGUE = {
    "neutral":        (0.00, 0.0, 0.0),
    "breathing":      (0.00, 0.0, 0.0),
    "blink":          (0.00, 0.0, 0.0),   # blink handled inside compose()
    "listening":      (0.02, 0.1, 0.05),  # tiny attentive motion
    "thinking":       (0.00, 0.5, 0.0),   # slow look-away sway
    "smile":          (0.00, 0.0, 0.35),  # faint smile
    "transition_in":  (0.05, 0.0, 0.1),   # settle before speech
    "transition_out": (0.02, 0.0, 0.1),   # ease out of speech
    "failure_loop":   (0.00, 0.0, 0.0),   # last-resort gentle idle
}


class IdleAnimator:
    def __init__(self, source_image: str = "assets/nova.png", fps: int = 25):
        self.r = FallbackRenderer(source_image, fps=fps)
        self.fps = fps

    def frames(self, state: str, seconds: float) -> Iterator[np.ndarray]:
        """Yield alive frames for a named idle state."""
        amp, bias, smile = CATALOGUE.get(state, CATALOGUE["neutral"])
        n = int(seconds * self.fps)
        for f in range(n):
            t = f / self.fps
            frame = self.r._compose(a=amp, t=t, sway_bias=bias)
            if smile:                              # faint upward mouth-corner lift
                frame = self._smile(frame, smile)
            yield np.clip(frame, 0, 255).astype(np.uint8)

    def _smile(self, frame, strength: float):
        # subtle brightening of the mouth-corner region as a lightweight smile
        mx, my = self.r.a.mouth
        y0, y1 = my - 6, my + 10
        x0, x1 = mx - 40, mx + 40
        frame[y0:y1, x0:x1] = np.clip(frame[y0:y1, x0:x1] * (1 + 0.05 * strength), 0, 255)
        return frame

    @staticmethod
    def required() -> list[str]:
        return list(CATALOGUE.keys())
