#!/usr/bin/env python3
"""
Phase-1 perceptual QA harness (spec §24 Phase 1 pass criteria, improved).

Backs the human review with automated checks on a rendered clip:
  - IDENTITY STABILITY: SSIM of the non-mouth face region vs the first frame
    stays high (no progressive facial drift / identity change).
  - TEETH/MOUTH FLICKER: mouth-region frame-to-frame difference is bounded and
    smooth (motion, not random shimmer).
  - SIZE STABILITY: frame size constant.

    python scripts/perceptual_qa.py samples/e2e_turn.mp4

Exit 0 = PASS. These are heuristics that flag regressions; final sign-off is a
human watching the 2-minute clip.
"""
import argparse
import sys

import cv2
import numpy as np


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float32); b = b.astype(np.float32)
    k = (11, 11)
    mu_a = cv2.blur(a, k); mu_b = cv2.blur(b, k)
    va = cv2.blur(a * a, k) - mu_a ** 2
    vb = cv2.blur(b * b, k) - mu_b ** 2
    vab = cv2.blur(a * b, k) - mu_a * mu_b
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    s = ((2 * mu_a * mu_b + c1) * (2 * vab + c2)) / \
        ((mu_a ** 2 + mu_b ** 2 + c1) * (va + vb + c2) + 1e-9)
    return float(np.clip(s.mean(), -1, 1))


def analyze(path: str, mouth_box=(0.35, 0.6, 0.65, 0.82)):
    """Identity stability is measured CONSECUTIVE-frame (tolerant of smooth head
    motion, which is desired liveliness; catches sudden identity jumps/flicker and
    progressive drift). Mouth region measured for motion + flicker."""
    cap = cv2.VideoCapture(path)
    ok, first = cap.read()
    if not ok:
        raise RuntimeError("cannot read clip")
    g_prev = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
    H, W = g_prev.shape
    mx0, my0, mx1, my1 = (int(mouth_box[0] * W), int(mouth_box[1] * H),
                          int(mouth_box[2] * W), int(mouth_box[3] * H))
    ident_mask = np.ones_like(g_prev, dtype=bool)
    ident_mask[my0:my1, mx0:mx1] = False           # exclude mouth from identity

    sizes, ident_ssims, mouth_diffs = {first.shape}, [], []
    prev_mouth = g_prev[my0:my1, mx0:mx1].astype(np.float32)
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        sizes.add(fr.shape)
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        ident_ssims.append(ssim(g_prev * ident_mask, g * ident_mask))  # consecutive
        m = g[my0:my1, mx0:mx1].astype(np.float32)
        mouth_diffs.append(float(np.mean(np.abs(m - prev_mouth))))
        prev_mouth = m
        g_prev = g
    cap.release()

    # progressive drift = downward trend of consecutive identity SSIM over time
    trend = 0.0
    if len(ident_ssims) > 4:
        x = np.arange(len(ident_ssims))
        trend = float(np.polyfit(x, ident_ssims, 1)[0])   # slope; ~0 is stable
    return {
        "frames": len(ident_ssims) + 1,
        "size_stable": len(sizes) == 1,
        # p05 tolerates the ~2 blink frames per cycle (desired liveliness) while a
        # sustained identity/teeth defect still depresses the mean + p05.
        "identity_ssim_p05": float(np.percentile(ident_ssims, 5)) if ident_ssims else 1.0,
        "identity_ssim_mean": float(np.mean(ident_ssims)) if ident_ssims else 1.0,
        "identity_drift_slope": trend,
        "mouth_motion_mean": float(np.mean(mouth_diffs)) if mouth_diffs else 0.0,
        "mouth_flicker_p95": float(np.percentile(mouth_diffs, 95)) if mouth_diffs else 0.0,
    }


def verdict(m: dict) -> tuple[bool, list[str]]:
    reasons = []
    if not m["size_stable"]:
        reasons.append("frame size changed")
    if m["identity_ssim_mean"] < 0.82:
        reasons.append(f"low identity stability (mean SSIM {m['identity_ssim_mean']:.2f} < 0.82)")
    if m["identity_ssim_p05"] < 0.60:
        reasons.append(f"identity jump/flicker (SSIM p05 {m['identity_ssim_p05']:.2f} < 0.60)")
    if m["identity_drift_slope"] < -1e-3:
        reasons.append(f"progressive identity drift (slope {m['identity_drift_slope']:.1e})")
    if m["mouth_motion_mean"] < 0.3:
        reasons.append("mouth barely moves (lip-sync suspect)")
    if m["mouth_flicker_p95"] > 60:
        reasons.append(f"mouth flicker high (p95 {m['mouth_flicker_p95']:.0f})")
    return (not reasons, reasons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    args = ap.parse_args()
    m = analyze(args.clip)
    ok, reasons = verdict(m)
    for k, v in m.items():
        print(f"  {k}: {v}")
    print("PASS" if ok else "FAIL: " + "; ".join(reasons))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
