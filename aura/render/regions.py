"""
Region ownership + conflict prevention (spec §11, §12).

Exactly one controller may write each facial region per frame. The compositor
blends their outputs with masks + temporal smoothing + identity locking so two
models never fight over the same pixels (which causes teeth/eye shimmer).
"""
from __future__ import annotations

from dataclasses import dataclass

# Region -> owning controller. Enforced by the compositor.
OWNERSHIP = {
    "jaw":        "lipsync",     # mouth/jaw: lip-sync renderer only
    "mouth":      "lipsync",
    "eyes":       "expression",  # eyes/eyelids: expression controller only
    "eyelids":    "expression",
    "eyebrows":   "expression",
    "head_pose":  "motion",      # head pose: motion controller only
    "shoulders":  "idle",        # shoulders/breathing: idle layer
    "background": "fixed",       # fixed unless explicitly animated
}


@dataclass
class StabilizerCfg:
    landmark_ema: float = 0.6        # landmark stabilisation (anti-jitter)
    temporal_ema: float = 0.5        # frame-to-frame smoothing on blend seams
    identity_lock: float = 0.85      # blend toward the enhanced source identity
    transition_ms: int = 120         # cross-fade when a controller hands over


class Compositor:
    """Blends per-region layers with masks + smoothing. GPU renderer supplies
    real masks; the CPU fallback owns all regions itself so no blending needed."""
    def __init__(self, cfg: StabilizerCfg = StabilizerCfg()):
        self.cfg = cfg
        self._prev = None

    def blend(self, layers: dict[str, "np.ndarray"], masks: dict[str, "np.ndarray"]):
        import numpy as np
        out = layers.get("base")
        if out is None:
            raise ValueError("compositor needs a base layer")
        out = out.astype(np.float32)
        for region, owner in OWNERSHIP.items():
            layer = layers.get(owner)
            mask = masks.get(region)
            if layer is None or mask is None:
                continue
            m = mask[..., None].astype(np.float32)
            out = out * (1 - m) + layer.astype(np.float32) * m
        if self._prev is not None:                    # temporal smoothing
            e = self.cfg.temporal_ema
            out = out * (1 - e) + self._prev * e
        self._prev = out
        return out.clip(0, 255).astype("uint8")
