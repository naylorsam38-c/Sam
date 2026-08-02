"""
MuseTalk lip-sync adapter (GPU integration seam).

MuseTalk owns ONLY the jaw/mouth region (spec §11). It renders mouth frames from
the enhanced identity image + the TTS audio, in real time on GPU, and emits a
per-frame mouth layer + mask for the compositor. Audio remains the master clock:
frames are indexed by audio timestamp.

LICENSING (per current official MuseTalk repo): code = MIT; trained model =
commercial use allowed. BUT: every bundled dependency must be audited + pinned
separately, and MuseTalk's supplied TEST DATA is non-commercial and must NOT be
shipped or reused. Not "commercial-safe" until the dependency lock + audit gate
(scripts/licence_audit.py) passes. See docs/LICENSING_REGISTER.md and
config/dependency_lock.yaml.

This file defines the contract and the load/warm-up seam. Real inference is
enabled on the GPU host where the weights are installed; on a CPU box the worker
falls back to FallbackRenderer automatically (spec §15).
"""
from __future__ import annotations

from typing import Iterator

import numpy as np


class MuseTalkRenderer:
    level = 3

    def __init__(self, identity_image: str, fps: int = 25, device: str = "cuda:0",
                 mem_budget_mb: int = 6000):
        self.identity_image = identity_image
        self.fps = fps
        self.device = device
        self.mem_budget_mb = mem_budget_mb
        self._ready = False

    def warmup(self) -> None:
        """Load VAE + UNet + whisper feature extractor onto `device`, run one
        dummy forward so first real frame isn't cold. GPU-only.

        NOTE: the model load below is the integration seam. Until it is wired on
        a GPU host, warm-up leaves the renderer UNAVAILABLE so the worker uses the
        CPU fallback (never a frozen face). On the GPU host, uncomment the load
        and set self._ready = True only on a successful dummy forward."""
        self._ready = False
        try:
            # import torch; self.models = load_musetalk(self.device, self.mem_budget_mb)
            # _ = self.models.infer_dummy()
            # self._ready = True
            pass
        except Exception:
            self._ready = False

    @property
    def available(self) -> bool:
        return self._ready

    def speaking_layers(self, wav_path: str) -> Iterator[tuple[np.ndarray, np.ndarray, float]]:
        """Yield (mouth_layer_bgr, mouth_mask, audio_pts_s). GPU integration
        point — raises if called without the models loaded so the worker knows
        to use the fallback."""
        if not self._ready:
            raise RuntimeError("MuseTalk not loaded; use fallback renderer")
        # for chunk in audio_chunks(wav_path, self.fps):
        #     mouth, mask = self.models.infer(chunk)
        #     yield mouth, mask, chunk.pts
        raise NotImplementedError("enable on GPU host with MuseTalk weights")
