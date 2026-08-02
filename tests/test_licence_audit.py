"""The licence gate must actually catch violations (spec §22-23 + correction)."""
import importlib.util
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "licence_audit", os.path.join(_ROOT, "scripts", "licence_audit.py"))
la = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(la)

BASE = {
    "approved_code_licences": ["MIT", "Apache-2.0", "BSD-3-Clause"],
    "approved_weight_licences": ["MIT", "Apache-2.0", "commercial-use-allowed"],
    "forbidden": ["codeformer", "xtts", "wav2lip", "insightface"],
}


def _lock(components):
    d = dict(BASE)
    d["components"] = components
    return d


def test_dynamic_unverified_download_fails(tmp_path):
    lock = _lock([{"name": "gfpgan-weights", "kind": "model_weight",
                   "licence": "Apache-2.0", "weight_licence": "Apache-2.0",
                   "dynamic_download": True, "download_source": "unverified",
                   "commit": "abc", "sha256": "x"}])
    fails, _ = la.audit(lock, str(tmp_path))
    assert any(f.startswith("R3") for f in fails)


def test_missing_licence_fails(tmp_path):
    lock = _lock([{"name": "mystery", "kind": "code", "licence": None,
                   "commit": "abc"}])
    fails, _ = la.audit(lock, str(tmp_path))
    assert any(f.startswith("R1") for f in fails)


def test_noncommercial_test_asset_shipped_fails(tmp_path):
    lock = _lock([{"name": "some-testdata", "kind": "test_asset",
                   "licence": "non-commercial", "ship": True, "commit": "abc"}])
    fails, _ = la.audit(lock, str(tmp_path))
    assert any(f.startswith("R4") for f in fails)


def test_forbidden_in_requirements_fails(tmp_path):
    (tmp_path / "requirements.txt").write_text("numpy\nxtts==0.1\n")
    lock = _lock([])
    fails, _ = la.audit(lock, str(tmp_path))
    assert any(f.startswith("R6") for f in fails)


def test_clean_manifest_has_no_hard_fails(tmp_path):
    lock = _lock([{"name": "kokoro-weights", "kind": "model_weight",
                   "licence": "Apache-2.0", "weight_licence": "Apache-2.0",
                   "dynamic_download": False, "download_source": "verified",
                   "commit": "abc123", "sha256": "deadbeef"}])
    fails, pendings = la.audit(lock, str(tmp_path))
    assert fails == []
