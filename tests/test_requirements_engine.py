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
ASSEMBLY = Path(__file__).resolve().parents[1] / "packages" / "assembly-engine"
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
    assert len(TEMPLATES) == 6   # the five reverse-engineered templates + command-desk (the agent-app one)
    for path in TEMPLATES:
        assert f"{path.stem}" in r.stdout
    assert "FAIL" not in r.stdout


def test_template_checker_selftest_catches_every_break():
    r = run("check_template.py", "--selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SELFTEST PASS" in r.stdout
    assert r.stdout.count("[caught]") == 7   # six original breaks + one executable-block break


@pytest.mark.parametrize("script", sorted(GENERATED))
def test_generated_artifacts_are_reproducible(script, tmp_path):
    """Regenerating from source must not change a byte.

    Run in a copy so a broken generator cannot damage the tracked files.
    build_templates.py now also locks each template's numbered structure as
    part of regenerating it (lock_structure.py, reusing the Assembly Engine's
    own derive()/build_model() rather than a second copy of that logic) --
    a real, intentional dependency on the sibling package, so the copy must
    preserve that same real layout (../assembly-engine next to
    requirements-engine), not just requirements-engine on its own.
    """
    packages = tmp_path / "packages"
    work = packages / "requirements-engine"
    shutil.copytree(ENGINE, work, ignore=shutil.ignore_patterns("__pycache__"))
    if script == "build_templates.py":
        shutil.copytree(ASSEMBLY, packages / "assembly-engine", ignore=shutil.ignore_patterns("__pycache__"))

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


def test_every_template_is_already_locked():
    """Every one of the six real templates must carry a frozen "structure"
    block -- the whole point of lock_structure.py is that assemble.py never
    derives one on the fly, so nothing may ship without one already locked."""
    for path in TEMPLATES:
        t = json.loads(path.read_text())
        assert t.get("structure"), f"{path.name} has no locked structure"
        s = t["structure"]
        assert s["screens_inventory"], f"{path.name}: locked structure has no screens"
        assert s["actions_inventory"], f"{path.name}: locked structure has no actions"


def test_locked_ids_are_unique_and_prefixed_with_their_own_template():
    """Every numbered id in a template's locked structure must be prefixed
    with that template's own name (so combining templates can never collide
    two numbers) and unique within the template."""
    for path in TEMPLATES:
        t = json.loads(path.read_text())
        s = t["structure"]
        ids = ([x["id"] for x in s["screens_inventory"]] + [x["id"] for x in s["actions_inventory"]]
               + [x["id"] for x in s["recurring_ops"]] + [x["id"] for x in s["qa_generated_tests"]]
               + [n["id"] for n in s["notifications"].values()] + [r["id"] for r in s["reports"].values()])
        for w in s["workflows"].values():
            ids += [st["id"] for st in w["stages"]] + [tr["id"] for tr in w["transitions"]]
        assert ids, f"{path.name}: no numbered ids found at all"
        assert len(ids) == len(set(ids)), f"{path.name}: duplicate id in its own locked structure"
        for id_ in ids:
            assert id_.startswith(f"{t['template']}/"), f"{path.name}: id {id_} not prefixed with its own template"


def test_locking_is_idempotent_on_every_real_template(tmp_path):
    """Re-locking an already-locked template must not change a single id --
    the whole point of freezing structure once. Runs against copies so a
    broken lock step cannot damage the tracked templates."""
    sys.path.insert(0, str(ENGINE))
    import graph_lib
    import lock_structure
    graph = graph_lib.load_graph(str(GRAPH))
    for path in TEMPLATES:
        before = path.read_bytes()
        copy_path = tmp_path / path.name
        copy_path.write_bytes(before)
        lock_structure.lock_one(graph, str(copy_path))
        assert copy_path.read_bytes() == before, f"{path.name}: re-locking changed already-frozen ids"


def test_locking_survives_inventory_reorder_without_renumbering(tmp_path):
    """Permanence, not just no-op reruns: reordering a template's own
    inventory list must not change any id already assigned to an item that
    is still there -- only the item's position moved, not its identity."""
    sys.path.insert(0, str(ENGINE))
    import graph_lib
    import lock_structure
    graph = graph_lib.load_graph(str(GRAPH))
    pm_path = ENGINE / "templates" / "pm-teamwork.json"
    t = json.loads(pm_path.read_text())
    before_ids = {(s["kind"], s.get("record")): s["id"] for s in t["structure"]["screens_inventory"]}
    assert t["inventory"]["records"] == ["Project", "Task", "Comment"], "fixture assumption"
    t["inventory"]["records"] = ["Task", "Project", "Comment"]
    copy_path = tmp_path / "pm-teamwork-reordered.json"
    copy_path.write_text(json.dumps(t))
    lock_structure.lock_one(graph, str(copy_path))
    after = json.loads(copy_path.read_text())
    after_ids = {(s["kind"], s.get("record")): s["id"] for s in after["structure"]["screens_inventory"]}
    assert after_ids == before_ids, "reordering the inventory must not renumber any existing screen"


def test_visual_questions_claim_matches_the_graph():
    """VISUAL_QUESTIONS.md claims 40 of the 122 questions carry a widget, from a
    20-entry vocabulary. Check it against the actual graph, not the prose."""
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    widget_questions = [q for q in graph["questions"] if q.get("widget")]
    vocab = graph["config"]["widget_vocab"]
    assert len(widget_questions) == 40
    assert len(vocab) == 20
    for q in widget_questions:
        assert q["widget"] in vocab, f"{q['id']} uses undeclared widget {q['widget']!r}"
    claim = (ENGINE / "VISUAL_QUESTIONS.md").read_text(encoding="utf-8")
    assert "40 of the 122 questions" in claim
    assert "20 widgets" in claim


def test_templates_declare_what_the_customer_is_still_asked():
    """The point of a template is that the builder configures, not redesigns.

    Each one must name its source app, its modules, and the questions that
    survive for the customer.
    """
    for path in TEMPLATES:
        t = json.loads(path.read_text(encoding="utf-8"))
        assert t["source_app"], f"{path.stem} names no source app"
        assert t["modules"], f"{path.stem} declares no modules"
        if t["template"] == "command-desk":
            # not a reverse-engineered template to configure: it is Sam's own
            # product, fully answered, which is why it can actually assemble
            assert t["ask_customer"] == [], "command-desk is answered; nothing is left open"
        else:
            assert t["ask_customer"], f"{path.stem} asks the customer nothing"
        assert t["features"], f"{path.stem} maps no features to answers"
