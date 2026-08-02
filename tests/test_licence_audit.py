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


def test_audit_licence_table_loads_without_the_runtime_package():
    """The audit is a BUILD GATE — it runs in the Dockerfile and in CI, sometimes
    before the runtime dependencies exist.

    Regression: the shared licence table was reached via `aura.providers.licences`,
    which executes `aura/providers/__init__.py` and therefore imports every
    provider module — numpy, cv2, httpx. That made the gate unable to start on a
    bare checkout, and a gate that cannot start is a gate that does not gate.
    """
    import subprocess
    import sys
    import textwrap

    # Run in a subprocess with the aura package made unimportable, proving the
    # table is loaded by path rather than as a package import.
    code = textwrap.dedent("""
        import sys, os
        class _Block:
            def find_module(self, name, path=None):
                if name == "aura" or name.startswith("aura."):
                    raise ImportError(f"blocked: {name}")
                return None
        sys.meta_path.insert(0, _Block())
        sys.path.insert(0, "scripts")
        from licence_audit import FORBIDDEN_COMPONENTS, _noncommercial
        assert "insightface" in FORBIDDEN_COMPONENTS
        assert "codeformer" in FORBIDDEN_COMPONENTS
        assert _noncommercial("CC-BY-NC-4.0")
        assert not _noncommercial("MIT")
        print("OK")
    """)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"audit cannot start without the aura package:\n{r.stderr}"
    assert "OK" in r.stdout


def test_forbidden_list_is_shared_with_the_runtime():
    """The build gate and the runtime registry must ban exactly the same set —
    otherwise a component is refused at runtime but shipped in the image."""
    import sys
    sys.path.insert(0, "scripts")
    from licence_audit import FORBIDDEN_COMPONENTS
    from aura.providers.licences import FORBIDDEN_COMPONENTS as RUNTIME
    assert FORBIDDEN_COMPONENTS == RUNTIME
