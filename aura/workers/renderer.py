"""
Avatar-rendering worker. Consumes TTS_AUDIO, produces video frames locked to the
audio clock, and publishes RENDER_FRAME {frame, audio_pts, video_pts}.

The renderer lives behind a provider (`aura/providers/avatar.py`) resolved from
the configured policy. Two safety properties matter more than which one wins:

  1. The provider only claims availability after a real forward pass. A renderer
     that says "ready" and then raises produces a frozen face.
  2. A mid-turn failure falls back within the same turn. The avatar degrades in
     quality; it never stops moving.

While no audio is playing it emits idle "alive" frames.
"""
from __future__ import annotations

import asyncio

from ..bus import Bus, Topic
from ..config import AvatarCfg, ProvidersCfg
from ..providers import registry
from ..render.fallback import FallbackRenderer
from ..render.quality import QualityController
from ..worker import BaseWorker, log


class RendererWorker(BaseWorker):
    name = "render"

    def __init__(self, bus: Bus, cfg: AvatarCfg, quality: QualityController,
                 providers: ProvidersCfg | None = None, **kw):
        super().__init__(maxsize=4, item_timeout=15.0, on_full="drop_oldest", **kw)
        self.bus = bus
        self.cfg = cfg
        self.quality = quality
        self.pcfg = providers or ProvidersCfg()
        self.provider = None            # resolved primary (may be GPU or API)
        self.resolution = None
        self.fallback: FallbackRenderer | None = None
        self._idle_task: asyncio.Task | None = None
        self._busy = False
        self._idle_off = False
        self.idle_state = "LISTENING"   # session updates this via set_idle_state

    def disable_idle(self) -> None:
        """Stop idle-frame emission (used by the offline capture demo so only
        speaking frames are recorded)."""
        self._idle_off = True
        if self._idle_task:
            self._idle_task.cancel()

    async def setup(self) -> None:
        # The CPU fallback is always constructed, even when a GPU provider wins:
        # it is the in-turn safety net, not just the last resort at startup.
        self.fallback = FallbackRenderer(self.cfg.source_image, fps=self.cfg.output_fps)
        self.fallback.warmup()

        self.provider, self.resolution = await registry.resolve(
            "avatar", policy=self.pcfg.policy, engine=self.pcfg.avatar_engine,
            commercial=self.pcfg.commercial,
            source_image=self.cfg.source_image,
            driving_video=self.cfg.driving_video, fps=self.cfg.output_fps)

        self._idle_task = asyncio.create_task(self._idle_loop())
        log(self.name, "info", "ready", renderer=self.resolution.chosen,
            tier=self.resolution.info.tier,
            driving_video=self.cfg.driving_video)

    async def teardown(self) -> None:
        if self._idle_task:
            self._idle_task.cancel()
        if self.provider is not None:
            await self.provider.close()

    def set_idle_state(self, state: str) -> None:
        self.idle_state = state

    def _idle_source(self):
        """Provider idle motion if it has any, else the CPU fallback's."""
        if self.provider is not None:
            try:
                return self.provider.idle_frame
            except Exception:
                pass
        return self.fallback.idle_frame

    async def _idle_loop(self) -> None:
        """Emit breathing/blinking idle frames while not speaking so the avatar
        is never a frozen photo (spec §2, §11). Idle frames carry equal a/v PTS
        so they don't perturb speaking drift."""
        import time
        period = 1.0 / self.cfg.output_fps
        t0 = None
        while True:
            await asyncio.sleep(period)
            if self._idle_off:
                return
            if self._busy or not self.q.empty() or self.fallback is None:
                continue
            t0 = t0 or time.monotonic()
            t = time.monotonic() - t0
            try:
                frame = self._idle_source()(self.idle_state, t)
            except Exception:
                frame = self.fallback.idle_frame(self.idle_state, t)
            await self.bus.publish(Topic.RENDER_FRAME,
                                   {"frame": frame, "audio_pts": t, "video_pts": t})

    async def handle(self, item: dict) -> None:
        wav = item["wav_path"]
        self._busy = True
        try:
            if self.provider is not None and self.resolution.chosen != "fallback":
                try:
                    for frame, pts in self.provider.speaking_frames(wav):
                        await self._emit(frame, pts)
                        await asyncio.sleep(0)      # cooperative; cancellable
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    # Primary renderer died mid-turn. Tell the quality ladder it
                    # is stressed, then finish THIS turn on the CPU path so the
                    # face keeps moving.
                    self.quality.observe(drift_ms=999, dropped_frames=99,
                                         render_latency_ms=9999, gpu_mem_frac=0.99)
                    log(self.name, "warn", "primary renderer failed; CPU fallback",
                        renderer=self.resolution.chosen, error=repr(e))
            for frame, pts in self.fallback.speaking_frames(wav):
                await self._emit(frame, pts)
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log(self.name, "error", "render failed", error=repr(e))
        finally:
            self._busy = False

    async def _emit(self, frame, audio_pts: float) -> None:
        await self.bus.publish(Topic.RENDER_FRAME, {
            "frame": frame, "audio_pts": audio_pts, "video_pts": audio_pts})

    async def on_cancelled(self, item: dict) -> None:
        log(self.name, "info", "render cancelled (barge-in)")
