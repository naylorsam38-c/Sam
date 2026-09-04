"""The requirements engine's own claims, enforced on every run.

`packages/requirements-engine` ships two validators and a README full of
checkable numbers. Its state was previously a claim in a bundle; these tests
make it a fact that CI (or a bare `pytest`) re-establishes.
"""

import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "packages" / "requirements-engine"
GRAPH = ENGINE / "question_graph_v3.json"
TEMPLATES = sorted((ENGINE / "templates").glob("*.json"))

# Every generated artifact, and the script that must reproduce it exactly.
GENERATED = {
    "build_graph.py": ["question_graph_v3.json", "INTERVIEW_v3.md"],
    "build_templates.py": ["CONFIG_MAP.md"] + [f"templates/{p.name}" for p in TEMPLATES],
}


def run(*args, cwd=ENGINE):
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, text=True, capture_output=True
    )


def test_graph_validates():
    r = run("validate_graph.py", "question_graph_v3.json")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "VERDICT PASS" in r.stdout


def test_graph_validator_selftest_catches_every_break():
    """A validator that passes everything proves nothing."""
    r = run("validate_graph.py", "--selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SELFTEST PASS" in r.stdout
    assert r.stdout.count("[caught]") == 8


def test_every_template_fits_the_graph():
    r = run("check_template.py", "--all")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(TEMPLATES) == 5
    for path in TEMPLATES:
        assert f"{path.stem}" in r.stdout
    assert "FAIL" not in r.stdout


def test_template_checker_selftest_catches_every_break():
    r = run("check_template.py", "--selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SELFTEST PASS" in r.stdout
    assert r.stdout.count("[caught]") == 6


@pytest.mark.parametrize("script", sorted(GENERATED))
def test_generated_artifacts_are_reproducible(script, tmp_path):
    """Regenerating from source must not change a byte.

    Run in a copy so a broken generator cannot damage the tracked files.
    """
    work = tmp_path / "engine"
    shutil.copytree(ENGINE, work, ignore=shutil.ignore_patterns("__pycache__"))

    before = {rel: hashlib.sha256((work / rel).read_bytes()).hexdigest()
              for rel in GENERATED[script]}

    r = run(script, cwd=work)
    assert r.returncode == 0, r.stdout + r.stderr

    for rel, digest in before.items():
        after = hashlib.sha256((work / rel).read_bytes()).hexdigest()
        assert after == digest, f"{script} did not reproduce {rel} byte-for-byte"


def test_readme_question_counts_match_the_graph():
    """The README's headline numbers are checkable, so check them.

    They were wrong on arrival: it claimed 60 fixed / 62 per-instance where the
    graph has 61 / 61.
    """
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    questions = graph["questions"]
    fixed = sum(1 for q in questions if not q.get("per"))
    per_instance = len(questions) - fixed

    claim = (ENGINE / "README.md").read_text(encoding="utf-8")
    assert f"{len(questions)} questions ({fixed} fixed, {per_instance} per-instance)" in claim


def test_templates_declare_what_the_customer_is_still_asked():
    """The point of a template is that the builder configures, not redesigns.

    Each one must name its source app, its modules, and the questions that
    survive for the customer.
    """
    for path in TEMPLATES:
        t = json.loads(path.read_text(encoding="utf-8"))
        assert t["source_app"], f"{path.stem} names no source app"
        assert t["modules"], f"{path.stem} declares no modules"
        assert t["ask_customer"], f"{path.stem} asks the customer nothing"
        assert t["features"], f"{path.stem} maps no features to answers"
