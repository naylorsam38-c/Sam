#!/usr/bin/env python3
"""
build_families.py — the five reference instances, assembled and built.

A template deliberately leaves the customer's own questions open (its
ask_customer list: name, description, brand, imports, deviations, read-backs).
The Assembly Engine refuses to run until they are answered, and it is right
to. This script answers them for a REFERENCE instance of each family -- the
plainest possible customer, named after the family itself -- so the family
can be assembled, built, started and driven by a real browser end to end.

Every answer below is labelled as a reference answer; none is a guess about a
real customer. Change REFERENCE_ANSWERS and rerun to build a different one.

Usage:
  python build_families.py                 # assemble + build all five under packages/interfaces/build/<family>/
  python build_families.py pm-teamwork     # one family
"""

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ENGINE = os.path.join(ROOT, "packages", "requirements-engine")
ASSEMBLY = os.path.join(ROOT, "packages", "assembly-engine")
BUILDER = os.path.join(ROOT, "packages", "builder")
OUT = os.path.join(HERE, "build")
for p in (ENGINE, ASSEMBLY, BUILDER):
    sys.path.insert(0, p)
import graph_lib          # noqa: E402
import check_template     # noqa: E402
import assemble as ae     # noqa: E402
import builder as bl      # noqa: E402

FAMILIES = ["pm-teamwork", "crm-pipeline", "booking-frontdesk", "erp-backbone", "accounting-ledger"]
PORTS = {"pm-teamwork": 8801, "crm-pipeline": 8802, "booking-frontdesk": 8803,
         "erp-backbone": 8804, "accounting-ledger": 8805}

# ---------------------------------------------------------------------------
# REFERENCE ANSWERS -- the customer questions every template leaves open
# (build_templates.py ASK_ALWAYS), answered for a reference instance.
# ---------------------------------------------------------------------------
COMMON = {
    "0.01": "guided",
    "A.12": {"required": "no"},
    "A.13": {"region": "Australia", "languages": ["English"]},
    "A.14": [],
    "C.01": "none",
    "C.03": "balanced",
    "C.04": {"mode": "design_for_me"},
    "C.07": "confirmed", "Z.01": "confirmed", "Z.02": "confirmed", "Z.03": "confirmed",
}
REFERENCE_ANSWERS = {
    "pm-teamwork": {
        "A.01": "A shared task board: projects hold tasks, tasks are assigned to people, moved through To do / In progress / Done, and discussed in comments.",
        "A.02": "Plan work as projects and tasks, see who is carrying what, and chase what is overdue.",
        "A.03": "A small team and the outside collaborators it invites into specific projects.",
        "A.04": "Nothing slips: every open task has an owner and a date, and the overdue report is short.",
        "A.05": "Teamwork",
        "C.02": ["clear", "fast", "calm"],
    },
    "crm-pipeline": {
        "A.01": "A sales pipeline: organisations and contacts, deals moving through stages from Lead in to Won or Lost, and the activities that move them.",
        "A.02": "Track every deal from first contact to close, know the pipeline value by stage, and see the win rate.",
        "A.03": "A sales team: reps who own deals and a manager who sees everything.",
        "A.04": "The pipeline is honest -- every deal is in the stage it is really in -- and the win rate is known.",
        "A.05": "Pipeline",
        "C.02": ["focused", "energetic", "confident"],
    },
    "booking-frontdesk": {
        "A.01": "A front desk for appointments: services with durations and prices, customers, and appointments booked by staff or through a public form, then confirmed, completed or marked no-show.",
        "A.02": "Take bookings without phone calls, keep the calendar full, and know the no-show rate.",
        "A.03": "A small service business: an owner and the staff who deliver the appointments.",
        "A.04": "The book is full a week out and no-shows are rare.",
        "A.05": "Front Desk",
        "C.02": ["friendly", "simple", "warm"],
        # B.03 fires because bookings can carry a deposit: the reference instance
        # lists its one-off charges as the services themselves (per appointment)
        "B.03": [{"name": "Per appointment", "price": "the Service's own Price", "interval": "one_off",
                  "included": "one appointment of that service", "limits": "none"}],
    },
    "erp-backbone": {
        "A.01": "The operations core: products with stock on hand, suppliers and customer accounts, purchase orders that add stock when received and sales orders that subtract it when shipped.",
        "A.02": "Buy, sell and hold stock with every movement accounted for, and never run out unnoticed.",
        "A.03": "A trading business: sales, purchasing, warehouse and operations staff.",
        "A.04": "Stock on hand is always right and every open order is visible.",
        "A.05": "Backbone",
        "C.02": ["dense", "precise", "serious"],
    },
    "accounting-ledger": {
        "A.01": "The books: contacts, invoices with lines, bills, and the payments applied to them; invoices move from Draft through approval to Awaiting payment and settle to Paid.",
        "A.02": "Raise invoices, record bills and payments, and know what is owed.",
        "A.03": "A small business's accountant, its admin, and an outside advisor with read-only access.",
        "A.04": "Every invoice is sent, every payment is applied, and nothing is paid twice.",
        "A.05": "Ledger",
        "C.02": ["trustworthy", "quiet", "exact"],
    },
}


def reference_instance(family):
    t = json.load(open(os.path.join(ENGINE, "templates", f"{family}.json"), encoding="utf-8"))
    inst = copy.deepcopy(t)
    answers = dict(COMMON)
    answers.update(REFERENCE_ANSWERS[family])
    for q in list(inst["ask_customer"]):
        if q not in answers:
            raise SystemExit(f"{family}: open question {q} has no reference answer -- add one, do not guess")
        inst["answers"][q] = answers[q]
    inst["ask_customer"] = []
    inst["reference_instance"] = {"note": "reference answers from packages/interfaces/build_families.py; "
                                          "not a real customer's answers"}
    return inst


def assemble_family(graph, family, out_dir):
    inst = reference_instance(family)
    errors = check_template.check(graph, inst)
    if errors:
        raise SystemExit(f"{family}: reference instance fails check_template:\n  " + "\n  ".join(errors))
    spec = ae.assemble(graph, inst, spec_id=f"SPEC-{family.upper()}-REF", title=f"{inst['answers']['A.05']} ({family})")
    os.makedirs(out_dir, exist_ok=True)
    json.dump(inst, open(os.path.join(out_dir, "INSTANCE.json"), "w", encoding="utf-8"), indent=2, default=str)
    json.dump(spec, open(os.path.join(out_dir, "SPEC.json"), "w", encoding="utf-8"), indent=2, default=str)
    open(os.path.join(out_dir, "SPEC.md"), "w", encoding="utf-8").write(ae.render_markdown(spec))
    return spec


def build_family(family, out_root=OUT):
    graph = graph_lib.load_graph(os.path.join(ENGINE, "question_graph_v3.json"))
    graph["_q"] = {q["id"]: q for q in graph["questions"]}
    out_dir = os.path.join(out_root, family)
    spec = assemble_family(graph, family, out_dir)
    app_dir = os.path.join(out_dir, "app")
    result = bl.build(spec, app_dir, port=PORTS[family])
    return spec, app_dir, result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    families = argv or FAMILIES
    for family in families:
        try:
            spec, app_dir, result = build_family(family)
        except (ae.Refused, bl.BuildRefused) as e:
            print(f"{family}: REFUSED — {e}", file=sys.stderr)
            return 2
        print(f"{family}: built {len(result['records_built'])} records, {result['screens_built']} screens -> {app_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
