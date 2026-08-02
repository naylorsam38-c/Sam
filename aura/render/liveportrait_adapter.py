"""
LivePortrait motion adapter (GPU integration seam).

Owns head pose + eyes/eyelids/eyebrows + subtle expression (spec §11), driven by
emotion/intensity/gesture from the PresentationRequest and by idle-motion
templates while not speaking. Emits per-region layers + masks for the compositor;
it must NOT touch the jaw/mouth (that is MuseTalk's region) — enforced by masks.

LICENSING — IMPORTANT: LivePortrait *code* is MIT (commercial ok), BUT it ships
with InsightFace detection models that are NON-COMMERCIAL research only. For a
commercial build you MUST replace the InsightFace detector with a permissively
licensed one (e.g. OpenCV YuNet / a RetinaFace weight under a commercial
licence). This adapter refuses to use InsightFace unless explicitly acknowledged.
See docs/LICENSING_REGISTER.md.
"""
from __future__ import annotations

import numpy as np


class LivePortraitMotion:
    def __init__(self, identity_image: str, device: str = "cuda:0",
                 detector: str = "yunet"):
        if detector == "insightface":
            raise ValueError(
                "InsightFace models are NON-COMMERCIAL. Use detector='yunet' (or "
                "another commercially-licensed detector) for commercial builds.")
        self.identity_image = identity_image
        self.device = device
        self.detector = detector
        self._ready = False

    def warmup(self) -> None:
        try:
            # load LivePortrait motion model + the commercial detector here
            self._ready = True
        except Exception:
            self._ready = False

    def motion_layers(self, state: str, t: float, emotion: str, intensity: float,
                      gesture: str | None):
        """Return {region: layer}, {region: mask} for eyes/brows/head_pose.
        GPU integration point."""
        if not self._ready:
            raise RuntimeError("LivePortrait not loaded; fallback owns motion")
        raise NotImplementedError("enable on GPU host")
