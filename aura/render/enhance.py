"""
Enhancement policy (spec §13). DO NOT run a face restorer on every frame.

Strategy:
  - Restore the SOURCE portrait ONCE at preprocessing (offline), preserving
    identity, and cache it.
  - At runtime, apply only *targeted* restoration to the re-rendered mouth
    region when a quality check flags softness — never the whole face, never
    every frame — to avoid teeth/eye shimmer and identity drift.

LICENSING: default enhancer is GFPGAN (permissive). CodeFormer is S-Lab
NON-COMMERCIAL and must not be enabled for commercial deployments — see
docs/LICENSING_REGISTER.md. This module refuses CodeFormer unless a flag
explicitly acknowledges a separate commercial licence.
"""
from __future__ import annotations

import os


class Enhancer:
    def __init__(self, engine: str = "gfpgan", allow_noncommercial: bool = False):
        if engine == "codeformer" and not allow_noncommercial:
            raise ValueError(
                "CodeFormer is NON-COMMERCIAL (S-Lab License 1.0). Refusing to "
                "enable for commercial use. Set allow_noncommercial=True only if "
                "you hold a separate licence. Prefer 'gfpgan'.")
        self.engine = engine
        self._model = None

    def restore_source_once(self, image_path: str, out_path: str) -> str:
        """One-time identity-preserving restoration of the portrait.
        GPU seam: load GFPGAN here. On CPU/offline this is a no-op copy."""
        if self._model is None and self.engine == "gfpgan":
            try:
                # from gfpgan import GFPGANer; self._model = GFPGANer(...)
                pass  # GPU integration point
            except Exception:
                self._model = None
        if self._model is None:
            import shutil
            shutil.copyfile(image_path, out_path)   # offline no-op
            return out_path
        # ... run self._model.enhance(...) and write out_path ...
        return out_path

    def touch_up_region(self, frame, mask, strength: float = 0.5):
        """Targeted, masked restoration only where flagged. No-op without GPU."""
        return frame
