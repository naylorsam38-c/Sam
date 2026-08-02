import importlib.util
import os

import numpy as np

from aura.render.idle import IdleAnimator, CATALOGUE

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_required_animation_set_present():
    req = set(IdleAnimator.required())
    must = {"neutral", "breathing", "blink", "listening", "thinking", "smile",
            "transition_in", "transition_out", "failure_loop"}
    assert must.issubset(req)


def test_idle_frames_stable_size():
    a = IdleAnimator("assets/nova.png", fps=25)
    shapes = {f.shape for f in a.frames("listening", 0.2)}
    assert len(shapes) == 1                       # never changes size / never empty
    assert next(iter(shapes))[2] == 3


# ---- perceptual QA harness ----
_spec = importlib.util.spec_from_file_location(
    "perceptual_qa", os.path.join(_ROOT, "scripts", "perceptual_qa.py"))
qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qa)


def test_ssim_identical_is_high_and_shifted_is_lower():
    img = (np.random.rand(80, 80) * 255).astype("uint8")
    assert qa.ssim(img, img) > 0.99
    shifted = np.roll(img, 8, axis=0)
    assert qa.ssim(img, shifted) < qa.ssim(img, img)


def test_verdict_pass_and_fail():
    good = {"size_stable": True, "identity_ssim_mean": 0.9, "identity_ssim_p05": 0.7,
            "identity_drift_slope": 0.0, "mouth_motion_mean": 4.0, "mouth_flicker_p95": 10}
    assert qa.verdict(good)[0] is True
    bad = dict(good, identity_drift_slope=-0.01, mouth_flicker_p95=90)
    ok, reasons = qa.verdict(bad)
    assert ok is False and reasons
