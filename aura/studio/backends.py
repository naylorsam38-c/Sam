"""
Generation backends for avatar assets.

Same pattern as the runtime providers: each backend declares its licence and its
requirements, and the studio picks the best one that can actually run here.

IMAGE
  flux-schnell  FLUX.1-schnell, Apache-2.0. The commercial-safe Flux.
                FLUX.1-dev is NON-COMMERCIAL and is refused by name — the two
                are one string apart and produce identical-looking PNGs.
  qwen-image    Qwen-Image, Apache-2.0. Alternative, strong at faces.
  existing      use a portrait you already own. Needs consent details.

VIDEO (the driving loop)
  wan           Wan 2.2, Apache-2.0 — genuinely open, image-to-video.
  procedural    no GPU, no model, no download. Synthesises a breathing/blinking
                loop from the still using the CPU renderer's idle motion.
                Not photoreal, but it gives the lip-sync model varying head pose
                instead of one frozen frame, and it runs anywhere.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from ..providers.base import ProviderUnavailable, Requires
from ..worker import log


@dataclass(frozen=True)
class BackendInfo:
    name: str
    licence: str                  # licence of the MODEL — what governs the output
    requires: Requires
    note: str = ""


# ── image backends ──────────────────────────────────────────────────────────
class FluxSchnellImage:
    info = BackendInfo(
        name="flux-schnell", licence="Apache-2.0",
        requires=Requires(packages=("torch", "diffusers"), gpu=True),
        note="FLUX.1-schnell only. FLUX.1-dev shares the architecture and is "
             "non-commercial — never swap the repo id without re-checking.",
    )
    REPO = "black-forest-labs/FLUX.1-schnell"

    def __init__(self, **_: object) -> None:
        self._pipe = None

    async def setup(self) -> None:
        try:
            import torch
            from diffusers import FluxPipeline
        except Exception as e:
            raise ProviderUnavailable(f"diffusers/torch unavailable: {e!r}") from e
        self._pipe = await asyncio.to_thread(
            FluxPipeline.from_pretrained, self.REPO, torch_dtype=torch.bfloat16)
        await asyncio.to_thread(self._pipe.to, "cuda")

    async def generate(self, prompt: str, out_path: str, *, seed: int = 0,
                       width: int = 768, height: int = 960) -> str:
        if self._pipe is None:
            raise ProviderUnavailable("flux not loaded")

        def _run() -> str:
            import torch
            g = torch.Generator("cuda").manual_seed(seed)
            img = self._pipe(prompt, width=width, height=height,
                             num_inference_steps=4, guidance_scale=0.0,
                             generator=g).images[0]
            img.save(out_path)
            return out_path

        return await asyncio.to_thread(_run)


class ExistingImage:
    """Use a portrait you already have. The honest default when the avatar is a
    real person — generation cannot manufacture their consent."""
    info = BackendInfo(
        name="existing", licence="owner-supplied",
        requires=Requires(),
        note="You must supply consent details; the studio refuses to build a "
             "shippable bundle for a real likeness without a release reference.",
    )

    def __init__(self, source: str | None = None, **_: object) -> None:
        self.source = source

    async def setup(self) -> None:
        if not self.source or not os.path.exists(self.source):
            raise ProviderUnavailable(f"source image not found: {self.source!r}")

    async def generate(self, prompt: str, out_path: str, **_: object) -> str:
        import shutil
        shutil.copyfile(self.source, out_path)
        return out_path


# ── video backends ──────────────────────────────────────────────────────────
class WanVideo:
    info = BackendInfo(
        name="wan", licence="Apache-2.0",
        requires=Requires(packages=("torch", "diffusers"), gpu=True),
        note="Wan 2.2 image-to-video. Apache-2.0 on code and weights, which is "
             "rare among video models — most carry field-of-use restrictions.",
    )
    REPO = "Wan-AI/Wan2.2-I2V-A14B-Diffusers"

    def __init__(self, **_: object) -> None:
        self._pipe = None

    async def setup(self) -> None:
        try:
            import torch  # noqa: F401
            from diffusers import WanImageToVideoPipeline
        except Exception as e:
            raise ProviderUnavailable(f"diffusers/torch unavailable: {e!r}") from e
        self._pipe = await asyncio.to_thread(
            WanImageToVideoPipeline.from_pretrained, self.REPO)
        await asyncio.to_thread(self._pipe.to, "cuda")

    async def generate(self, image_path: str, out_path: str, *, seconds: float,
                       fps: int, prompt: str = "", seed: int = 0) -> str:
        if self._pipe is None:
            raise ProviderUnavailable("wan not loaded")
        raise NotImplementedError(
            "wire Wan's I2V call here on the GPU host — see docs/AVATAR_STUDIO.md. "
            "Until then the studio falls through to the procedural backend.")


class ProceduralLoop:
    """Driving loop with no model, no GPU and no download.

    Reuses the CPU renderer's idle motion — head sway, breathing scale, periodic
    blink — to turn one still into a seamless ping-ponged loop. It will not pass
    for real footage, but it gives the lip-sync stage a *moving* head to inpaint
    onto instead of one frozen frame, which is most of the perceptual gap. It
    also means this pipeline produces something useful on any machine.
    """
    info = BackendInfo(
        name="procedural", licence="MIT",
        requires=Requires(packages=("cv2",), binaries=("ffmpeg",)),
        note="Always available. Quality floor, not a substitute for real footage.",
    )

    def __init__(self, fps: int = 25, **_: object) -> None:
        self.fps = fps

    async def setup(self) -> None: ...

    async def generate(self, image_path: str, out_path: str, *, seconds: float,
                       fps: int, prompt: str = "", seed: int = 0) -> str:
        def _run() -> str:
            import subprocess
            import cv2
            from ..render.fallback import FallbackRenderer

            r = FallbackRenderer(image_path, fps=fps)
            n = max(2, int(seconds * fps))
            frames = [r.idle_frame("LISTENING", i / fps) for i in range(n)]
            frames += frames[-2:0:-1]          # ping-pong so the loop seams

            raw = out_path.replace(".mp4", "_raw.mp4")
            h, w = frames[0].shape[:2]
            vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
            for f in frames:
                vw.write(f)
            vw.release()
            # re-encode to H.264 so every downstream decoder accepts it
            subprocess.run(["ffmpeg", "-y", "-i", raw, "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", out_path],
                           check=True, capture_output=True)
            os.remove(raw)
            log("studio.procedural", "info", "driving loop built",
                frames=len(frames), seconds=round(len(frames) / fps, 2))
            return out_path

        return await asyncio.to_thread(_run)


IMAGE_BACKENDS = {"flux-schnell": FluxSchnellImage, "existing": ExistingImage}
VIDEO_BACKENDS = {"wan": WanVideo, "procedural": ProceduralLoop}

# Preference order; first that can run wins. Both end in something dependable.
IMAGE_ORDER = ["flux-schnell", "existing"]
VIDEO_ORDER = ["wan", "procedural"]
