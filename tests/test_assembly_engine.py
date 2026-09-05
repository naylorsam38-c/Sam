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


def test_refuses_when_a_template_has_no_locked_structure():
    """Every real template is locked (requirements-engine/lock_structure.py has
    run on all five) -- this proves the refusal fires for one that is not, by
    taking a real template and removing exactly that one key. assemble.py must
    not derive a structure on the fly to route around a missing lock."""
    inst = json.loads((ENGINE / "templates" / "pm-teamwork.json").read_text())
    assert inst.get("structure"), "fixture assumption: the real template is locked"
    del inst["structure"]
    tmp = ASSEMBLY / "_tmp_real_unlocked.json"
    tmp.write_text(json.dumps(inst))
    try:
        r = run(str(tmp), "-o", "/tmp/should_not_be_created_unlocked")
        assert r.returncode == 2
        assert "REFUSED" in r.stderr
        assert "no locked structure" in r.stderr
    finally:
        tmp.unlink()


def test_registration_gaps_flags_real_report_screens_and_transitions(real_template):
    """builder.py now has a real generation rule for report screens, form
    screens, transitions, custom actions, submits and approvals. A rule still
    needs what it runs on, so registration_gaps must flag exactly the items
    the Builder would really refuse: a report with no executable ReportSpec,
    a custom action with no executable effect, and any kind with no rule at
    all -- and must NOT flag an item the Builder can genuinely build."""
    structure = real_template["structure"]
    gaps = ae.registration_gaps(structure)
    gap_ids = {g[0] for g in gaps}
    reports = structure.get("reports") or {}
    report_screens = [s["id"] for s in structure["screens_inventory"] if s["kind"] == "report"]
    if not report_screens:
        pytest.skip(f"{real_template['template']} declares no reports (accounting-ledger's two were outside "
                    "every reporting part's scope and were removed from the template)")
    for scr in structure["screens_inventory"]:
        if scr["kind"] != "report":
            continue
        has_spec = bool((reports.get(scr.get("report")) or {}).get("spec"))
        assert (scr["id"] in gap_ids) is not has_spec, (
            f"{scr['id']}: a report screen is a gap exactly when its report has no ReportSpec")
    # every flagged item genuinely has an unregistered kind -- the gate names
    # real gaps, not real capability it mistakes for a gap
    for id_, kind, k in gaps:
        assert (k not in ae.REGISTERED_SCREEN_KINDS) if kind == "screen" else (k not in ae.REGISTERED_ACTION_KINDS)


def test_registration_gaps_does_not_flag_real_crud_or_oauth_connect():
    """The two things builder.py really can build -- a record's CRUD
    screens/actions and an OAuth connect action -- must never be reported as
    gaps. Uses pm-teamwork's real list/detail/create/edit/delete entries
    (already proven buildable end-to-end in tests/test_builder.py) and
    Command Desk's real connect action shape from its own approved spec."""
    pm = json.loads((ENGINE / "templates" / "pm-teamwork.json").read_text())
    crud_structure = {
        "screens_inventory": [s for s in pm["structure"]["screens_inventory"] if s["kind"] in ("list", "detail")],
        "actions_inventory": [a for a in pm["structure"]["actions_inventory"] if a["kind"] in ("create", "edit", "delete")],
    }
    assert crud_structure["screens_inventory"] and crud_structure["actions_inventory"]
    assert ae.registration_gaps(crud_structure) == []

    connect_structure = {
        "screens_inventory": [{"id": "SCR-001", "kind": "integration_status", "integration": "Gmail"}],
        "actions_inventory": [{"id": "ACT-001", "kind": "connect", "integration": "Gmail", "roles": ["Sam"]}],
    }
    assert ae.registration_gaps(connect_structure) == []


def test_assemble_blocks_with_the_real_item_numbers_listed():
    """End-to-end wiring test for the block-with-numbers rule itself: a
    minimal, fully-answered mechanism fixture (declared as such, same genre as
    test_refuses_on_a_structurally_invalid_instance below -- not a stand-in
    for a real product) whose one real report screen has no registered
    Builder rule. Proves assemble() reaches registration_gaps (not just the
    pure function above) and names the exact blocked id in its refusal."""
    inst = {
        "template": "mechanism-test", "source_app": "n/a", "category": "n/a", "modules": [],
        "inventory": {"records": [], "roles": [], "forms": [], "notifications": [],
                      "reports": ["Test report"], "workflows": [], "file_types": [],
                      "integrations": [], "screens": []},
        "super_role": None,
        "answers": {
            "0.01": "hands-off", "A.01": "A mechanism-test fixture, not a real product.",
            "A.02": "Prove assemble.py's registration gate fires.", "A.03": "This test suite.",
            "A.04": "The gate lists the blocked item's own id.", "A.05": "Mechanism Test",
            "A.06": ["web"], "A.07": "no", "A.08": "single", "A.09": "no", "A.11": "no",
            "A.12": {"required": "no"}, "A.13": {"region": "AU", "languages": ["en"]}, "A.14": [],
            "C.01": "No references.", "C.02": ["simple", "clear", "fast"], "C.03": "balanced",
            "C.04": {"mode": "design_for_me"}, "C.05": {"mode": "simplified"}, "C.07": True,
            "Z.01": True, "Z.02": True, "Z.03": True,
        },
        "per_instance": {
            "RP.01:Test report": "How many test items are there?", "RP.02:Test report": ["public"],
            "RP.03:Test report": {"delivery": "screen", "shape": "table"},
            "RP.04:Test report": ["count of test items"],
            "RP.06:Test report": {"filters": [], "default_range": "all time"},
            "RP.07:Test report": {"allowed": "no"}, "RP.08:Test report": {"enabled": "no"},
        },
        "ask_customer": [], "features": [],
    }
    graph = graph_lib.load_graph(str(ENGINE / "question_graph_v3.json"))
    graph["_q"] = {q["id"]: q for q in graph["questions"]}
    tmp = ASSEMBLY / "_tmp_mechanism_test.json"
    tmp.write_text(json.dumps(inst))
    try:
        sys.path.insert(0, str(ENGINE))
        import lock_structure
        lock_structure.lock_one(graph, str(tmp))
        locked = json.loads(tmp.read_text())
        with pytest.raises(ae.Refused, match="no registered Builder implementation") as exc_info:
            ae.assemble(graph, locked, "SPEC-TEST", "mechanism test")
        assert locked["structure"]["screens_inventory"][0]["id"] in str(exc_info.value)
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
