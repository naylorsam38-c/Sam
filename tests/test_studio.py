"""Avatar studio: it must produce a usable bundle on a machine with no GPU, and
it must refuse to certify an asset it cannot clear for commercial use."""
import json
import os
import shutil

import pytest

from aura.config import StudioCfg
from aura.studio import AvatarStudio, verify_bundle
from aura.studio.provenance import (Provenance, ProvenanceError, sha256_file,
                                    write_manifest)

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"),
                                reason="ffmpeg not installed")


# ── provenance rules ────────────────────────────────────────────────────────
def test_generated_asset_needs_a_commercially_licensed_model():
    ok = Provenance(asset="p.png", kind="portrait", origin="generated",
                    sha256="x" * 64, model="flux-schnell",
                    model_licence="Apache-2.0")
    ok.validate()

    bad = Provenance(asset="p.png", kind="portrait", origin="generated",
                     sha256="x" * 64, model="flux-dev",
                     model_licence="flux-1-dev non-commercial")
    with pytest.raises(ProvenanceError, match="forbids commercial use"):
        bad.validate()


def test_generated_asset_with_unknown_model_licence_is_refused():
    p = Provenance(asset="p.png", kind="portrait", origin="generated",
                   sha256="x" * 64, model="mystery", model_licence="Custom v3")
    with pytest.raises(ProvenanceError, match="not on the approved list"):
        p.validate()


def test_real_person_needs_subject_and_consent():
    p = Provenance(asset="p.png", kind="portrait", origin="photographed",
                   sha256="x" * 64)
    with pytest.raises(ProvenanceError, match="consent_reference"):
        p.validate()

    p.subject, p.consent_reference = "A Person", "release-123"
    p.validate()


def test_missing_hash_is_refused():
    p = Provenance(asset="p.png", kind="portrait", origin="generated",
                   model="flux-schnell", model_licence="Apache-2.0")
    with pytest.raises(ProvenanceError, match="sha256"):
        p.validate()


def test_manifest_refuses_to_certify_an_invalid_record(tmp_path):
    bad = Provenance(asset="p.png", kind="portrait", origin="photographed",
                     sha256="x" * 64)
    with pytest.raises(ProvenanceError):
        write_manifest(str(tmp_path), [bad])
    assert not os.path.exists(tmp_path / "bundle.json")


# ── end-to-end build, no GPU ────────────────────────────────────────────────
async def test_builds_a_bundle_with_no_gpu(tmp_path):
    studio = AvatarStudio(StudioCfg(out_dir=str(tmp_path), driving_seconds=1.0))
    bundle = await studio.build(
        name="t", source_image="assets/nova.png",
        subject="synthetic character", consent_reference="test-only")

    assert os.path.exists(bundle.portrait)
    assert os.path.exists(bundle.driving_video)
    # no GPU here, so the video must come from the dependency-free path
    assert bundle.video_backend == "procedural"
    assert any("procedural" in n for n in bundle.notes)
    assert verify_bundle(bundle.directory) == []


async def test_driving_loop_actually_moves_and_is_longer_than_one_frame(tmp_path):
    import cv2
    import numpy as np
    studio = AvatarStudio(StudioCfg(out_dir=str(tmp_path), driving_seconds=1.0))
    bundle = await studio.build(name="t", source_image="assets/nova.png",
                                subject="s", consent_reference="c")

    cap = cv2.VideoCapture(bundle.driving_video)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()

    assert len(frames) > 10
    # the whole point of a driving loop is that the head is NOT static
    delta = np.mean(np.abs(frames[5].astype(float) - frames[0].astype(float)))
    assert delta > 0.1, "driving loop is a frozen still — no motion to inpaint onto"


async def test_bundle_detects_tampering(tmp_path):
    studio = AvatarStudio(StudioCfg(out_dir=str(tmp_path), driving_seconds=1.0))
    bundle = await studio.build(name="t", source_image="assets/nova.png",
                                subject="s", consent_reference="c")
    assert verify_bundle(bundle.directory) == []

    with open(bundle.portrait, "ab") as f:
        f.write(b"tampered")
    problems = verify_bundle(bundle.directory)
    assert any("sha256 mismatch" in p for p in problems)


async def test_refuses_a_real_likeness_without_consent(tmp_path):
    studio = AvatarStudio(StudioCfg(out_dir=str(tmp_path), driving_seconds=1.0))
    with pytest.raises(ProvenanceError, match="consent_reference"):
        await studio.build(name="t", source_image="assets/nova.png")


async def test_requires_a_prompt_or_an_image(tmp_path):
    studio = AvatarStudio(StudioCfg(out_dir=str(tmp_path)))
    with pytest.raises(ValueError, match="prompt"):
        await studio.build(name="t")


def test_hash_is_stable(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"aura")
    assert sha256_file(str(p)) == sha256_file(str(p))
    assert len(sha256_file(str(p))) == 64
