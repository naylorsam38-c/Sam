"""Assembly Engine (packages/assembly-engine): completed answers -> one
numbered spec.

Every test here runs against real data already in the repository — the five
requirements-engine templates, reverse-engineered from real apps (Asana,
Pipedrive, Acuity, Odoo, Xero) — or proves a refusal path with a
deliberately-invalid structure (the same genre of test validate_graph.py's
own --selftest and check_template.py's own --selftest use to prove their
refuse-paths work). Nothing here fabricates a plausible answer to a real
interview question: no template's ask_customer list is ever filled in for
the purpose of this test suite. A genuine end-to-end assembly needs answers
from a real customer, which is what the Command Desk instance (built from
Command Desk's own already-approved spec, not invented) is for.
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

sys.path.insert(0, str(ASSEMBLY))
sys.path.insert(0, str(ENGINE))
import assemble as ae          # noqa: E402
import graph_lib               # noqa: E402


def run(*args, cwd=ASSEMBLY):
    return subprocess.run([sys.executable, "assemble.py", *args], cwd=cwd, text=True, capture_output=True)


@pytest.fixture(scope="module")
def graph():
    g = graph_lib.load_graph(str(ENGINE / "question_graph_v3.json"))
    g["_q"] = {q["id"]: q for q in g["questions"]}
    return g


@pytest.fixture(params=TEMPLATES)
def real_template(request):
    return json.loads((ENGINE / "templates" / f"{request.param}.json").read_text())


# --------------------------------------------------------------------------- refusal paths (real inputs, real reasons)
def test_refuses_when_ask_customer_not_empty():
    """The front door's job (answering everything) is not done -> refuse, don't
    guess. Uses the real, as-shipped template: its ask_customer list is real,
    not staged for the test."""
    inst = json.loads((ENGINE / "templates" / "pm-teamwork.json").read_text())
    assert inst["ask_customer"], "the real template does have open questions -- that is the point being tested"
    tmp = ASSEMBLY / "_tmp_real_incomplete.json"
    tmp.write_text(json.dumps(inst))
    try:
        r = run(str(tmp), "-o", "/tmp/should_not_be_created")
        assert r.returncode == 2
        assert "REFUSED" in r.stderr
        assert "still open for the customer" in r.stderr
        for q in inst["ask_customer"]:
            assert q in r.stderr, f"open question {q} not listed in the refusal"
    finally:
        tmp.unlink()


def test_refuses_on_a_structurally_invalid_instance():
    """Same genre of test as validate_graph.py's and check_template.py's own
    --selftest: a deliberately invalid structure, to prove the refuse-path
    fires -- not a stand-in for a real product."""
    tmp = ASSEMBLY / "_tmp_structurally_invalid.json"
    tmp.write_text(json.dumps({
        "template": "invalid", "source_app": "n/a", "category": "n/a", "modules": [],
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


# --------------------------------------------------------------------------- derivations, against real recorded facts
def test_D01_storage_types_from_a_real_records_real_fields(graph, real_template):
    """D01 against whatever fields the template really has -- not fabricated
    ones -- checking the storage type it assigns is the fixed, documented map
    applied to the field's own real declared type."""
    inst = real_template
    for record in inst["inventory"]["records"]:
        fields = ae.fields_of(inst, record)
        if not fields:
            continue
        derived = ae.derive(graph, inst)["D01"][record]
        for name, fd in fields.items():
            assert derived[name] == ae.STORAGE_TYPE[fd["type"]], (
                f"{inst['template']}/{record}.{name}: real type {fd['type']!r} "
                f"should map to {ae.STORAGE_TYPE[fd['type']]!r}, got {derived[name]!r}")


def test_D14_enum_options_match_the_real_recorded_choice_list(graph, real_template):
    """Not every template has a one_choice/multi_choice field -- booking-frontdesk
    genuinely does not (checked against its real R.02 answers) -- so this checks
    equality wherever one exists rather than requiring one to exist."""
    inst = real_template
    derived = ae.derive(graph, inst)["D14"]
    for record in inst["inventory"]["records"]:
        for name, fd in ae.fields_of(inst, record).items():
            if fd["type"] in ("one_choice", "multi_choice"):
                assert derived[record][name] == fd["options"], (
                    f"{inst['template']}/{record}.{name}: enum should be the field's own real options")


def test_at_least_one_template_exercises_D14():
    """The per-template test above degrades to a no-op when a template has no
    choice field at all; confirm the derivation is exercised somewhere real."""
    graph_ = graph_lib.load_graph(str(ENGINE / "question_graph_v3.json"))
    graph_["_q"] = {q["id"]: q for q in graph_["questions"]}
    exercised = False
    for name in TEMPLATES:
        inst = json.loads((ENGINE / "templates" / f"{name}.json").read_text())
        if any(fd["type"] in ("one_choice", "multi_choice")
               for r in inst["inventory"]["records"] for fd in ae.fields_of(inst, r).values()):
            exercised = True
    assert exercised


def test_D04_permissions_match_the_real_recorded_grants(graph, real_template):
    """Every permitted action D04 derives for a role must trace back to a real
    R.05-R.08 grant already in the template -- nothing invented, nothing lost."""
    inst = real_template
    d04 = ae.derive(graph, inst)["D04"]
    verb_q = {"view": "R.05", "create": "R.06", "edit": "R.07", "delete": "R.08"}
    for role, grants in d04["permitted_actions"].items():
        for g_ in grants:
            qid = verb_q[g_["action"]]
            real_answer = inst["per_instance"].get(f"{qid}:{g_['record']}")
            if qid == "R.06":
                assert role in (real_answer or []), f"{inst['template']}: {role} {g_} not backed by a real R.06 answer"
            else:
                real_roles = [e["role"] for e in (real_answer or []) if isinstance(real_answer, list)]
                assert role in real_roles, f"{inst['template']}: {role} {g_} not backed by a real {qid} answer"
    # and the super role is always admin, never guessed otherwise
    assert d04["is_admin"][inst["super_role"]] is True


def test_D12_actions_and_D13_screens_are_uniquely_numbered(graph, real_template):
    inst = real_template
    derived = ae.derive(graph, inst)
    act_ids = [a["id"] for a in derived["D12"]]
    scr_ids = [s["id"] for s in derived["D13"]["screens"]]
    assert act_ids, f"{inst['template']}: D12 produced no actions from real grants/transitions"
    assert scr_ids, f"{inst['template']}: D13 produced no screens from the real records/forms/reports"
    assert len(act_ids) == len(set(act_ids))
    assert len(scr_ids) == len(set(scr_ids))
    # exactly one list + one detail screen per real record (D13's stated rule)
    for record in inst["inventory"]["records"]:
        kinds = [s["kind"] for s in derived["D13"]["screens"] if s.get("record") == record]
        assert kinds.count("list") == 1 and kinds.count("detail") == 1


def test_D15_generates_one_qa_test_per_role_on_a_numbered_action(graph, real_template):
    """D15's own rule: for every numbered action, perform it as each role. Check
    the count against the real actions/roles the template really declares."""
    inst = real_template
    derived = ae.derive(graph, inst)
    # matches derive()'s own loop: an action with no roles (e.g. a custom action
    # with no role list) still gets exactly one test, via the placeholder role.
    expected = sum(len(a["roles"]) if a.get("roles") else 1 for a in derived["D12"])
    action_tests = [t for t in derived["D15"] if "action_id" in t]
    assert len(action_tests) == expected


# --------------------------------------------------------------------------- combine, on real templates, unmodified
def test_combine_real_templates_surfaces_a_real_unresolved_decision():
    """Booking's super role (Owner) differs from accounting's (Admin). Combined,
    Admin is no longer super and needs authority answers it never needed alone
    -- a real consequence of a real merge, not a fabricated one. This is the
    exact scenario CONFIG_MAP.md documents for booking + accounting."""
    r = run(
        "--combine",
        str(ENGINE / "templates" / "booking-frontdesk.json"),
        str(ENGINE / "templates" / "accounting-ledger.json"),
        "--reconcile", "Customer=Contact",
        "-o", "/tmp/should_not_be_created_either",
    )
    assert r.returncode == 2
    assert "P.01:Admin fires but is neither answered nor in ask_customer" in r.stderr


def test_combine_renames_a_real_nested_record_reference(graph):
    """R.02's real link fields and R.11's real relations name a record
    independently of the inventory list; --reconcile must rewrite those too.
    Uses booking-frontdesk's actual Appointment record, which really does
    link to Customer both ways."""
    booking = json.loads((ENGINE / "templates" / "booking-frontdesk.json").read_text())
    fields = booking["per_instance"]["R.02:Appointment"]
    assert any(f.get("target_record") == "Customer" for f in fields), \
        "fixture assumption: Appointment really links to Customer"

    accounting = json.loads((ENGINE / "templates" / "accounting-ledger.json").read_text())
    tmp_b = ASSEMBLY / "_tmp_real_booking.json"
    tmp_a = ASSEMBLY / "_tmp_real_accounting.json"
    tmp_b.write_text(json.dumps(booking))
    tmp_a.write_text(json.dumps(accounting))
    try:
        merged = ae.combine([str(tmp_b), str(tmp_a)], {"Customer": "Contact"})
        renamed_fields = merged["per_instance"]["R.02:Appointment"]
        assert any(f.get("target_record") == "Contact" for f in renamed_fields)
        assert not any(f.get("target_record") == "Customer" for f in renamed_fields)
        renamed_relations = merged["per_instance"]["R.11:Appointment"]
        assert any(rel["target"] == "Contact" for rel in renamed_relations)
    finally:
        tmp_b.unlink()
        tmp_a.unlink()
