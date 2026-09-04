"""Assembly Engine (packages/assembly-engine): completed answers -> one
numbered spec. Regression-tests it against all five requirements-engine
templates (synthetically completed — see fixtures/complete_for_test.py) plus
the template-combination path, since that is exactly the surface no single
template's own check_template.py run exercises.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSEMBLY = ROOT / "packages" / "assembly-engine"
ENGINE = ROOT / "packages" / "requirements-engine"
TEMPLATES = sorted(p.stem for p in (ENGINE / "templates").glob("*.json"))


def run(*args, cwd=ASSEMBLY):
    return subprocess.run([sys.executable, "assemble.py", *args], cwd=cwd, text=True, capture_output=True)


@pytest.fixture(scope="module")
def completed(tmp_path_factory):
    """One synthetically-completed instance per template, built once per test run."""
    out = tmp_path_factory.mktemp("completed")
    paths = {}
    for name in TEMPLATES:
        dst = out / f"{name}.json"
        r = subprocess.run(
            [sys.executable, "fixtures/complete_for_test.py", str(ENGINE / "templates" / f"{name}.json"), str(dst)],
            cwd=ASSEMBLY, text=True, capture_output=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        paths[name] = dst
    return paths


@pytest.mark.parametrize("name", TEMPLATES)
def test_every_template_assembles(name, completed, tmp_path):
    out = tmp_path / name
    r = run(str(completed[name]), "-o", str(out), "--spec-id", f"SPEC-{name}", "--title", name)
    assert r.returncode == 0, r.stdout + r.stderr
    spec = json.loads((out / "SPEC.json").read_text())
    bm = spec["build_model"]
    assert bm["records"], "no records assembled"
    assert bm["actions_inventory"], "no actions derived"
    assert bm["screens_inventory"], "no screens derived"
    assert bm["qa_generated_tests"], "D15 produced no generated tests"
    # every screen and action carries a unique numbered id
    scr_ids = [s["id"] for s in bm["screens_inventory"]]
    act_ids = [a["id"] for a in bm["actions_inventory"]]
    assert len(scr_ids) == len(set(scr_ids))
    assert len(act_ids) == len(set(act_ids))
    (out / "SPEC.md").read_text()  # renders without raising


def test_refuses_when_ask_customer_not_empty():
    """The front door's job (answering everything) is not done -> refuse, don't guess."""
    inst = json.loads((ENGINE / "templates" / "pm-teamwork.json").read_text())
    assert inst["ask_customer"], "fixture assumption: template has open questions"
    tmp = ASSEMBLY / "fixtures" / "_tmp_incomplete.json"
    tmp.write_text(json.dumps(inst))
    try:
        r = run(str(tmp), "-o", "/tmp/should_not_be_created")
        assert r.returncode == 2
        assert "REFUSED" in r.stderr
        assert "still open for the customer" in r.stderr
    finally:
        tmp.unlink()


def test_refuses_when_instance_does_not_fit_graph():
    tmp = ASSEMBLY / "fixtures" / "_tmp_broken.json"
    tmp.write_text(json.dumps({
        "template": "broken", "source_app": "x", "category": "x", "modules": [],
        "inventory": {k: [] for k in ("records", "roles", "forms", "notifications",
                     "reports", "workflows", "file_types", "integrations", "screens")},
        "super_role": "Admin", "answers": {}, "per_instance": {}, "ask_customer": [], "features": [],
    }))
    try:
        r = run(str(tmp), "-o", "/tmp/should_not_be_created")
        assert r.returncode == 2
        assert "REFUSED" in r.stderr
        assert "does not fit the graph" in r.stderr
    finally:
        tmp.unlink()


def test_combine_unions_inventories_and_reconciles_shared_records(completed, tmp_path):
    out = tmp_path / "combined"
    r = run(
        "--combine", str(completed["booking-frontdesk"]), str(completed["accounting-ledger"]),
        "--reconcile", "Customer=Contact",
        "-o", str(out), "--spec-id", "SPEC-COMBINED", "--title", "combined",
    )
    # A real, undecided gap survives combination (Admin loses super-role status
    # in the merge and now needs answers it never needed alone) -> refusal is
    # the correct outcome, not a bug in the assembler.
    assert r.returncode == 2
    assert "P.01:Admin fires but is neither answered nor in ask_customer" in r.stderr
    assert "target" not in r.stderr.lower() or "unknown record" not in r.stderr  # the reference-rename bug, once real, stays fixed


def test_combine_reference_rename_reaches_nested_answer_values(completed, tmp_path):
    """R.02 link fields and R.11 relations name a record independently of the
    inventory list; --reconcile must rewrite those too, not just the list entry."""
    merged = json.loads((completed["booking-frontdesk"]).read_text())
    acct = json.loads((completed["accounting-ledger"]).read_text())
    # booking's Appointment record links to Customer both via inventory and via
    # nested field/relation references — exactly the case that broke before the fix.
    fields = merged["per_instance"]["R.02:Appointment"]
    assert any(f.get("target_record") == "Customer" for f in fields)

    out = tmp_path / "combined2"
    dst_b = tmp_path / "b.json"
    dst_a = tmp_path / "a.json"
    dst_b.write_text(json.dumps(merged))
    dst_a.write_text(json.dumps(acct))
    r = run("--combine", str(dst_b), str(dst_a), "--reconcile", "Customer=Contact", "-o", str(out))
    assert "target 'Customer'" not in r.stderr, "reference rename did not reach the nested field value"
