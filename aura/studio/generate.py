"""
Avatar studio — builds the assets the live avatar runs on.

    prompt (or your own photo)
        -> portrait.png          identity, one frame
        -> driving.mp4           short loop of head motion to inpaint onto
        -> bundle.json           provenance + hashes for every file

The bundle is what `config.avatar.source_image` / `driving_video` point at, and
what the licence gate checks. Building it here rather than buying it from an
avatar vendor is the whole point: you own the identity, and nobody bills you per
minute for using your own face.

Backends degrade the same way the runtime providers do — GPU models when they
are present, a dependency-free procedural path when they are not — so this
produces a usable bundle on any machine.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..config import StudioCfg
from ..providers.base import ProviderUnavailable
from ..worker import log
from . import backends as B
from .provenance import Provenance, sha256_file, write_manifest


@dataclass
class Bundle:
    directory: str
    portrait: str
    driving_video: str
    manifest: str
    image_backend: str
    video_backend: str
    notes: list[str]

    def summary(self) -> dict:
        return {"directory": self.directory, "portrait": self.portrait,
                "driving_video": self.driving_video,
                "image_backend": self.image_backend,
                "video_backend": self.video_backend, "notes": self.notes}


async def _pick(order: list[str], table: dict, skipped: list[str], **kwargs):
    """First backend in `order` whose requirements are met and which starts."""
    for name in order:
        cls = table.get(name)
        if cls is None:
            skipped.append(f"{name}: not registered")
            continue
        try:
            inst = cls(**kwargs)
        except Exception as e:
            skipped.append(f"{name}: construction failed: {e!r}")
            continue
        missing = inst.info.requires.missing()
        if missing:
            skipped.append(f"{name}: missing " + ", ".join(missing))
            continue
        try:
            await inst.setup()
        except ProviderUnavailable as e:
            skipped.append(f"{name}: {e}")
            continue
        except Exception as e:
            skipped.append(f"{name}: setup failed: {e!r}")
            continue
        return name, inst
    raise RuntimeError("no usable backend. Tried: " + "; ".join(skipped))


class AvatarStudio:
    def __init__(self, cfg: StudioCfg | None = None, fps: int = 25):
        self.cfg = cfg or StudioCfg()
        self.fps = fps

    async def build(self, *, prompt: str = "", name: str = "avatar",
                    source_image: str | None = None,
                    subject: str | None = None,
                    consent_reference: str | None = None,
                    seconds: float | None = None,
                    seed: int | None = None) -> Bundle:
        """Build one avatar bundle.

        Supply `prompt` to generate a synthetic face, or `source_image` to use a
        portrait you already own. A real person's likeness additionally requires
        `subject` and `consent_reference` — the manifest will refuse to validate
        without them, which is the point.
        """
        seconds = seconds if seconds is not None else self.cfg.driving_seconds
        seed = seed if seed is not None else self.cfg.seed
        out = os.path.join(self.cfg.out_dir, name)
        os.makedirs(out, exist_ok=True)
        notes: list[str] = []

        # ── 1. portrait ─────────────────────────────────────────────────────
        portrait = os.path.join(out, "portrait.png")
        image_order = (["existing"] if source_image else
                       [b for b in B.IMAGE_ORDER if b != "existing"] +
                       (["existing"] if source_image else []))
        if not source_image and not prompt:
            raise ValueError("supply either `prompt` (generate) or `source_image`")

        skipped: list[str] = []
        img_name, img_backend = await _pick(
            image_order, B.IMAGE_BACKENDS, skipped, source=source_image)
        notes += [f"image: skipped {s}" for s in skipped]
        await img_backend.generate(prompt, portrait, seed=seed)
        log("studio", "info", "portrait built", backend=img_name, path=portrait)

        # ── 2. driving loop ─────────────────────────────────────────────────
        driving = os.path.join(out, "driving.mp4")
        skipped = []
        vid_name, vid_backend = await _pick(
            B.VIDEO_ORDER, B.VIDEO_BACKENDS, skipped, fps=self.fps)
        notes += [f"video: skipped {s}" for s in skipped]
        try:
            await vid_backend.generate(portrait, driving, seconds=seconds,
                                       fps=self.fps, prompt=prompt, seed=seed)
        except NotImplementedError as e:
            # a GPU backend that loaded but is not wired must not sink the build
            notes.append(f"video: {vid_name} not wired ({e}); using procedural")
            vid_name = "procedural"
            vid_backend = B.ProceduralLoop(fps=self.fps)
            await vid_backend.setup()
            await vid_backend.generate(portrait, driving, seconds=seconds,
                                       fps=self.fps)
        log("studio", "info", "driving loop built", backend=vid_name, path=driving)

        if vid_name == "procedural":
            notes.append(
                "driving loop is procedural — synthesised head motion, not real "
                "footage. Good enough to beat a frozen still; record ~20s of the "
                "real subject when you want commercial-grade output.")

        # ── 3. provenance ───────────────────────────────────────────────────
        if source_image:
            portrait_rec = Provenance(
                asset="portrait.png", kind="portrait", origin="photographed",
                sha256=sha256_file(portrait), subject=subject,
                consent_reference=consent_reference)
        else:
            portrait_rec = Provenance(
                asset="portrait.png", kind="portrait", origin="generated",
                sha256=sha256_file(portrait), model=img_backend.info.name,
                model_licence=img_backend.info.licence, prompt=prompt, seed=seed)

        driving_rec = Provenance(
            asset="driving.mp4", kind="driving_video", origin="derived",
            sha256=sha256_file(driving), derived_from="portrait.png",
            model=vid_backend.info.name, model_licence=vid_backend.info.licence)

        manifest = write_manifest(out, [portrait_rec, driving_rec])
        log("studio", "info", "bundle complete", directory=out, manifest=manifest)

        return Bundle(directory=out, portrait=portrait, driving_video=driving,
                      manifest=manifest, image_backend=img_name,
                      video_backend=vid_name, notes=notes)
