"""
CPU fallback renderer — the guaranteed-runnable path (spec §15 "Fallback", §14).

No GPU, no ML face-tracker, no network. It keeps the avatar visually alive in
every state (idle breathing, blink, attentive listening, thinking sway) and does
amplitude-driven mouth motion locked to the speech audio when speaking. It will
never match MuseTalk quality — its job is to *never freeze* and to prove the
audio-mastered pipeline end to end. It is also what Phase 1 tests run against on
a CPU-only box.
"""
from __future__ import annotations

import math
from typing import Iterator

import cv2
import numpy as np
import soundfile as sf

from .base import FaceAnchors, NOVA


class FallbackRenderer:
    level = 0

    def __init__(self, source_image: str = "assets/nova.png",
                 anchors: FaceAnchors = NOVA, fps: int = 25):
        self.fps = fps
        self.a = anchors
        base = cv2.imread(source_image)
        if base is None:
            raise FileNotFoundError(f"avatar source image unreadable: {source_image}")
        self.base = base.astype(np.float32)
        H, W = self.base.shape[:2]
        self.H, self.W = H, W
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        mx, my = anchors.mouth
        sx, sy = anchors.mouth_spread
        self._xx, self._yy = xx, yy
        self._gauss = np.exp(-(((xx - mx) ** 2) / (2 * sx ** 2) +
                               ((yy - my) ** 2) / (2 * sy ** 2)))
        self._antisym = ((yy - my) / sy) * self._gauss
        self._dark = np.exp(-(((xx - mx) ** 2) / (2 * (sx * .7) ** 2) +
                              ((yy - my) ** 2) / (2 * (sy * .7) ** 2)))

    def warmup(self) -> None:
        _ = self.idle_frame("IDLE", 0.0)

    # ── alive-while-idle (spec §2, §14) ─────────────────────────────────────
    def idle_frame(self, state: str, t: float) -> np.ndarray:
        # gentle head sway + breathing; "thinking" adds a slow look-away, blink
        amp = {"THINKING": 0.4, "LISTENING": 0.15}.get(state, 0.0)
        frame = self._compose(a=amp * 0.3, t=t,
                              sway_bias=(0.4 if state == "THINKING" else 0.0))
        return np.clip(frame, 0, 255).astype(np.uint8)

    # ── speaking, locked to audio (spec §5) ─────────────────────────────────
    def speaking_frames(self, wav_path: str) -> Iterator[tuple[np.ndarray, float]]:
        env = self._envelope(wav_path)
        for f, a in enumerate(env):
            t = f / self.fps
            frame = self._compose(a=float(a), t=t)
            yield np.clip(frame, 0, 255).astype(np.uint8), t   # video pts == audio pts

    # ── internals ───────────────────────────────────────────────────────────
    def _compose(self, a: float, t: float, sway_bias: float = 0.0) -> np.ndarray:
        dy = self._antisym * (13.0 * a)
        frame = cv2.remap(self.base, self._xx, (self._yy - dy).astype(np.float32),
                          cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if a > 0:
            frame = frame * (1 - self._dark * 0.35 * a)[:, :, None]
        ang = 1.3 * math.sin(2 * math.pi * 0.13 * t) + sway_bias
        scale = 1.0 + 0.008 * math.sin(2 * math.pi * 0.2 * t)
        M = cv2.getRotationMatrix2D((self.W / 2, self.H * 0.45), ang, scale)
        M[0, 2] += 6 * math.sin(2 * math.pi * 0.09 * t)
        M[1, 2] += 4 * math.sin(2 * math.pi * 0.07 * t) + 3 * a
        frame = cv2.warpAffine(frame, M, (self.W, self.H), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
        # blink every ~3.2s
        if (int(t * self.fps) % max(1, int(3.2 * self.fps))) < 2:
            ew, eh = self.a.eye_box
            for (ex, ey) in (self.a.left_eye, self.a.right_eye):
                eye = frame[ey - eh:ey + eh, ex - ew:ex + ew]
                if eye.size:
                    h2 = eye.shape[0]
                    sq = cv2.resize(eye, (eye.shape[1], max(3, int(h2 * .3))))
                    eye[:] = cv2.resize(sq, (eye.shape[1], h2))
        return frame

    def _envelope(self, wav_path: str) -> np.ndarray:
        wav, sr = sf.read(wav_path)
        if getattr(wav, "ndim", 1) > 1:
            wav = wav.mean(axis=1)
        n = int(len(wav) / sr * self.fps)
        win = max(1, int(sr / self.fps))
        env = np.array([np.sqrt(np.mean(wav[i * win:(i + 1) * win] ** 2) + 1e-9)
                        for i in range(n)])
        env = np.clip(env / (np.percentile(env, 95) + 1e-9), 0, 1)
        sm = env.copy()
        for i in range(1, len(sm)):
            sm[i] = max(env[i], sm[i - 1] * 0.55)
        return np.clip(sm, 0, 1)

    # convenience for Phase 1 proof / tests
    def render_clip(self, wav_path: str, out_mp4: str) -> str:
        import subprocess
        vw = cv2.VideoWriter(out_mp4.replace(".mp4", "_v.mp4"),
                             cv2.VideoWriter_fourcc(*"mp4v"), self.fps, (self.W, self.H))
        for frame, _ in self.speaking_frames(wav_path):
            vw.write(frame)
        vw.release()
        subprocess.run(["ffmpeg", "-y", "-i", out_mp4.replace(".mp4", "_v.mp4"),
                        "-i", wav_path, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", out_mp4],
                       check=True, capture_output=True)
        return out_mp4
