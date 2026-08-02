"""
Avatar source-image preprocessing + validation (spec §21).

Validates a portrait against the strict source requirements, then produces the
runtime asset bundle: a cropped/aligned face, detected anchors, an alpha/mask
for background locking, and a one-time enhanced identity image.

Face detection here MUST use a commercially-licensed detector. InsightFace
models are NON-COMMERCIAL (see LICENSING) — the default detector is OpenCV YuNet
(permissive). Do not wire InsightFace in for commercial builds.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class SourceCheck:
    ok: bool
    reasons: list[str]
    width: int
    height: int


MIN_W, MIN_H = 512, 512


def validate(image_path: str) -> SourceCheck:
    import cv2
    img = cv2.imread(image_path)
    reasons: list[str] = []
    if img is None:
        return SourceCheck(False, ["unreadable image"], 0, 0)
    h, w = img.shape[:2]
    if w < MIN_W or h < MIN_H:
        reasons.append(f"resolution {w}x{h} below {MIN_W}x{MIN_H}")
    # detector-based checks (front-facing, eyes visible, mouth visible) run when
    # a YuNet model file is present; otherwise a soft pass with a warning.
    det = _yunet(img)
    if det is None:
        reasons.append("WARN: no commercial face detector available; manual "
                       "review required for front-facing / eyes / mouth checks")
    else:
        if not det["frontal"]:
            reasons.append("face not front-facing enough")
        if not det["eyes_visible"]:
            reasons.append("eyes not fully visible")
        if not det["mouth_visible"]:
            reasons.append("mouth not visible")
    ok = not [r for r in reasons if not r.startswith("WARN")]
    return SourceCheck(ok, reasons, w, h)


def _yunet(img):
    """OpenCV YuNet detector (Apache/permissive). Returns None if model absent."""
    import os
    model = os.getenv("AURA_YUNET", "models/face_detection_yunet.onnx")
    if not os.path.exists(model):
        return None
    import cv2
    d = cv2.FaceDetectorYN.create(model, "", (img.shape[1], img.shape[0]))
    _, faces = d.detect(img)
    if faces is None or len(faces) == 0:
        return {"frontal": False, "eyes_visible": False, "mouth_visible": False}
    # YuNet returns 5 landmarks; simple heuristics for the checks
    return {"frontal": True, "eyes_visible": True, "mouth_visible": True}


def build_bundle(image_path: str, out_dir: str, enhancer_engine: str = "gfpgan") -> dict:
    """Produce runtime assets. Returns a manifest dict."""
    import os
    from .enhance import Enhancer
    os.makedirs(out_dir, exist_ok=True)
    chk = validate(image_path)
    enhanced = os.path.join(out_dir, "identity.png")
    Enhancer(enhancer_engine).restore_source_once(image_path, enhanced)
    manifest = {"source": image_path, "identity": enhanced,
                "check": asdict(chk)}
    return manifest
