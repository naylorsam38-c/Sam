#!/usr/bin/env python3
"""
bind_and_assemble.py — binds every numbered item (SCR, ACT, NTF, RPT, OPS)
across all five locked templates to a real part on the shelf
(packages/builder/parts_shelf.json / PARTS_SHELF.md), writes the binding
directly into a generated spec (not a side document, not interview question
IDs), assembles all five, and runs the checker against each, saving its raw
output alongside the spec.

Honesty note, stated up front because it changes what "done" can mean here:
this repository's Builder (packages/builder/builder.py) has a real, working
generation rule for exactly two things -- a record's CRUD routes and an
OAuth 'connect' action (parts crud_list_detail / oauth_connect on the
shelf). It has no generic runtime for workflow transitions, reports,
custom actions, or notification delivery (confirmed by reading builder.py
directly: no 'workflow'/'transition'/'stage' handling anywhere, no
'report' screen-kind rule). There is no app_engine.py runtime or
"foundation modules" in this repository -- those belong to a different
codebase. So CRUD/OAuth items bind to the Builder's real existing rule.
Everything else binds to one of the 16 real engines on the shelf ONLY
where a real, proven part's capability actually matches that item's real
declared behaviour (by name: a custom action's own name, an automatic
transition's own (workflow, from, to), a report's own name, an OPS job's
own timing shape). No new part is written here. An item with no real match
is left UNBOUND and reported as such -- never given a fabricated binding
just to make the checker read clean.

None of the five templates can be run through assemble.py's real customer-
facing path (assemble()) because every one of them, honestly, still leaves
real customer questions in ask_customer -- that is not a defect, it is the
whole point of "the front door does not guess" (see assemble.py's own
Refused paths). So this script produces a clearly-labelled, DIFFERENT
artifact per template: BOUND_SPEC.json, marked "customer_complete": false,
for verifying the part-binding/registration mechanism only. It is not a
deployable spec and packages/loop/run_chain.py must not be pointed at it.

Usage: python bind_and_assemble.py
Outputs, per template, under build/<template>/:
  BOUND_SPEC.json   the locked structure + part bindings, embedded in-line
  SPEC.md           the same thing, human-readable
  CHECK_OUTPUT.txt  the raw stdout of check_capability_bindings.py run against it
"""

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSEMBLY_DIR = os.path.join(HERE, "..", "assembly-engine")
BUILDER_DIR = os.path.join(HERE, "..", "builder")
sys.path.insert(0, os.path.abspath(ASSEMBLY_DIR))
sys.path.insert(0, os.path.abspath(BUILDER_DIR))
sys.path.insert(0, HERE)

import assemble as ae               # noqa: E402  (registration_gaps() / REGISTERED_*_KINDS -- reused, not reimplemented)
import check_capability_bindings    # noqa: E402
import shelf as shelf_lib           # noqa: E402  (pin() / source_revision() -- the shelf's own identity, not recomputed here)

TEMPLATE_DIR = os.path.join(HERE, "templates")
BUILD_DIR = os.path.join(HERE, "build")
TEMPLATES = ["pm-teamwork", "crm-pipeline", "booking-frontdesk", "erp-backbone", "accounting-ledger",
             "command-desk"]

SHELF = json.load(open(os.path.join(BUILDER_DIR, "parts_shelf.json"), encoding="utf-8"))
PARTS_BY_ID = {p["part_id"]: p for p in SHELF["parts"]}
# the exact identity of every part as it is at bind time -- version, source
# revision, lifecycle status -- computed once here and written into every
# binding as `pins`, so a bound spec names not just WHICH part but WHICH BYTES
# of it, and the checker can report drift when the shelf later moves on.
PINS_BY_ID = {p["part_id"]: shelf_lib.pin(p) for p in SHELF["parts"]}


def _resolve(part_ids, note):
    """Turns a list of real part_ids into (part_ids, real file::symbol
    locations, note) -- looked up from the shelf, never invented here.
    Every part_id used below must already exist on the shelf; a typo would
    KeyError rather than silently produce an empty location."""
    locations = [loc for pid in part_ids for loc in PARTS_BY_ID[pid]["location"]]
    return part_ids, locations, note


# ---------------------------------------------------------------- binding rules
# Every rule is keyed on a real, already-declared fact in the template's own
# locked structure -- never a guess.

CUSTOM_ACTION_BINDINGS = {
    "Duplicate": _resolve(["record_cloning"], None),
    "Reassign": _resolve(["custom_action_execution"],
                          "a plain restricted field edit: the generic custom-action rule performs it as "
                          "set_fields and enforces the action's own declared 'who'"),
    "Open source document": _resolve(["preserved_original_document_store"],
                      "the part serves the stored original by its recorded path and re-checks its "
                      "hash; the screen that opens it is a plain detail screen"),
    "Send": _resolve(["document_generation", "email_parsing"],
                      "document rendering and message composition are real and proven; actually "
                      "dispatching over SMTP was never built or proven, so this action is only "
                      "partially covered"),
}

TRANSITION_BINDINGS = {
    ("Invoice lifecycle", "Awaiting payment", "Paid"): _resolve(["ledger_balancing"], None),
    ("Bill lifecycle", "Awaiting payment", "Paid"): _resolve(["ledger_balancing"], None),
    ("Purchase order lifecycle", "Confirmed", "Received"): _resolve(["stock_ledger"], None),
    ("Sales order lifecycle", "Confirmed", "Shipped"): _resolve(["stock_ledger"], None),
    ("Document lifecycle", "received", "filled"): _resolve(
        ["document_field_detection", "value_provenance"],
        "detection and provenance are real; a field whose value is MISSING stops here rather "
        "than moving on, which is the part's own behaviour"),
    ("Document lifecycle", "filled", "signed"): _resolve(["trust_gate_approval"], None),
    ("Document lifecycle", "signed", "done"): _resolve(["preserved_original_document_store"], None),
    ("Appointment lifecycle", "Booked", "Confirmed"): _resolve(
        [], "half of this transition is 'the deposit payment succeeds' -- needs live "
            "payment processing, not on the shelf; the other half needs no part at all, "
            "but the template models both as one automatic-triggered edge"),
}

WORKFLOW_EXECUTOR = _resolve(["workflow_executor"], None)
SYSTEM_TRANSITION = _resolve(["system_triggered_transition"],
    "the move itself is real and refuses anything not declared; whatever the declared event "
    "implies beyond moving the record needs its own part, and gets one where it exists")
CUSTOM_ACTION = _resolve(["custom_action_execution"], None)
APPROVAL_GATE = _resolve(["stage_approval_gate"], None)
FORM = _resolve(["form_render_submit"], None)

# reports whose own real metric fits reporting_engine's real, single-table
# scope (count/sum/avg/min/max, filter, one group-by) -- worked out by hand
# against each report's own real RP.04/RP.06 answers, not assumed:
#   pm-teamwork "Open tasks by person"/"Overdue tasks": single table (Task).
#   crm-pipeline "Pipeline by stage": single table (Deal), sum+count by stage.
#   booking-frontdesk "Upcoming appointments": single table (Appointment).
#   erp-backbone "Open orders": two metrics, each its own single table.
#   command-desk "Activity per agent": single table (Job), count of done /
#     failed grouped by agent, filtered to the week. Fits.
#   command-desk "Cost": single table (Job), sum of the Job record's own Cost
#     field grouped by agent, filtered to the period. Fits, now that the
#     answers put the cost of a hosted model call on the Job (Sam, 2026-09-04).
# Left unbound: accounting-ledger "Profit and loss" and "Aged receivables"
# (cross-table join, computed values, arithmetic between metrics, age
# bucketing) -- genuinely outside a single-table aggregation.
REPORTING_ENGINE = _resolve(["reporting_engine"], None)

REPORT_BINDINGS = {
    "Open tasks by person": REPORTING_ENGINE,
    "Overdue tasks": REPORTING_ENGINE,
    "Pipeline by stage": REPORTING_ENGINE,
    "Upcoming appointments": REPORTING_ENGINE,
    "Open orders": REPORTING_ENGINE,
    "Activity per agent": REPORTING_ENGINE,
    "Cost": REPORTING_ENGINE,
    "Win rate": _resolve(["stage_history"], None),
    "No-show rate": _resolve(["stage_history"], None),
    "Sales by month": _resolve(["stage_history"], None),
    "Stock on hand": _resolve(["stock_ledger"], None),
}

CRUD_OAUTH = _resolve(["crud_list_detail"], None)
OAUTH = _resolve(["oauth_connect"], None)
API_KEY = _resolve(["api_key_connect"], None)
NO_RULE = ([], [], None)


def bind_action(act):
    if act["kind"] == "connect":
        return OAUTH
    if act["kind"] in ("create", "edit", "delete"):
        return CRUD_OAUTH
    if act["kind"] == "submit":
        return FORM
    if act["kind"] == "approve":
        return APPROVAL_GATE
    if act["kind"] == "custom":
        name = (act.get("detail") or {}).get("name")
        return CUSTOM_ACTION_BINDINGS.get(name, CUSTOM_ACTION)
    if act["kind"] == "transition":
        if act.get("mover") != "automatic":
            return WORKFLOW_EXECUTOR
        key = (act.get("workflow"), act.get("from"), act.get("to"))
        # an edge with its own domain rule wins; otherwise the generic system mover
        return TRANSITION_BINDINGS.get(key, SYSTEM_TRANSITION)
    return [], [], "no binding rule for this action kind"


def bind_screen(scr, report_bindings_by_name, integrations=None):
    if scr["kind"] == "integration_status":
        # the screen's own integration declares how it authenticates; a pasted
        # key is a different real rule from an OAuth round trip
        auth = ((integrations or {}).get(scr.get("integration")) or {}).get("auth")
        return API_KEY if auth == "api_key" else OAUTH
    if scr["kind"] == "form":
        return FORM
    if scr["kind"] in ("list", "detail"):
        return CRUD_OAUTH
    if scr["kind"] == "report":
        return report_bindings_by_name.get(scr.get("report"),
                                            ([], [], "plain aggregation over existing fields -- no generic reporting part was built"))
    return [], [], "no binding rule for this screen kind"


def bind_notification(notif):
    kind = (notif.get("trigger") or {}).get("kind")
    if kind in ("relative_to_date", "schedule"):
        return _resolve(["scheduled_jobs", "notification_delivery"], None)
    return _resolve(["notification_delivery"], None)


def bind_ops():
    # every OPS-nnn item is, by D11's own definition, a duration/schedule
    # answer that must become a real background job -- exactly scheduled_jobs.
    return _resolve(["scheduled_jobs"], None)


def bind_structure(structure, inventory):
    """Pure function: returns a DEEP COPY of structure with a
    'part_bindings' block added to every numbered item -- never mutates the
    locked structure in place. Screens/actions/recurring_ops get it inline
    on each list entry; notifications/reports (dicts) get it inline on each
    value."""
    s = copy.deepcopy(structure)
    report_engines = {name: REPORT_BINDINGS.get(name, ([], [], "plain aggregation over existing fields -- no generic reporting part was built"))
                       for name in inventory["reports"]}

    def binding(parts, locations, note):
        return {"parts": parts, "locations": locations, "note": note,
                "pins": [PINS_BY_ID[pid] for pid in parts]}

    for scr in s["screens_inventory"]:
        scr["part_bindings"] = binding(*bind_screen(scr, report_engines, s.get("integrations")))
    for act in s["actions_inventory"]:
        act["part_bindings"] = binding(*bind_action(act))
    for name, notif in s["notifications"].items():
        notif["part_bindings"] = binding(*bind_notification(notif))
    for name, rep in s["reports"].items():
        rep["part_bindings"] = binding(*report_engines[name])
    for op in s["recurring_ops"]:
        op["part_bindings"] = binding(*bind_ops())
    return s


def render_md(name, t, bound):
    out = [f"# {name} — bound spec (verification artifact, not customer-complete)\n",
           f"`customer_complete: false` -- {len(t['ask_customer'])} real customer questions are still open "
           f"({', '.join(t['ask_customer'][:6])}{'...' if len(t['ask_customer']) > 6 else ''}). "
           "This spec exists only to verify part bindings against the locked structure; "
           "it must never be used to build a real app.\n"]

    def table(title, items, id_fn, kind_fn):
        out.append(f"\n## {title}\n")
        out.append("| id | kind | parts | note |\n|---|---|---|---|")
        for item in items:
            pb = item["part_bindings"]
            out.append(f"| {id_fn(item)} | {kind_fn(item)} | {', '.join(pb['parts']) or '**UNBOUND**'} | {pb['note'] or ''} |")

    table("Screens", bound["screens_inventory"], lambda s: s["id"], lambda s: s["kind"])
    table("Actions", bound["actions_inventory"], lambda a: a["id"], lambda a: a["kind"])
    table("Notifications", [dict(v, _name=k) for k, v in bound["notifications"].items()], lambda n: n["_name"], lambda n: "notification")
    table("Reports", [dict(v, _name=k) for k, v in bound["reports"].items()], lambda r: r["_name"], lambda r: "report")
    table("Recurring ops", bound["recurring_ops"], lambda o: o["id"], lambda o: "ops")
    return "\n".join(out) + "\n"


def main():
    for name in TEMPLATES:
        t = json.load(open(os.path.join(TEMPLATE_DIR, f"{name}.json"), encoding="utf-8"))
        bound_structure = bind_structure(t["structure"], t["inventory"])

        spec = {
            "spec_id": f"BOUND-{name.upper()}", "customer_complete": False,
            "ask_customer_open": t["ask_customer"], "source_template": name,
            "graph_version": t["structure"].get("locked_at_graph_version"),
            "build_model": bound_structure,
        }

        outdir = os.path.join(BUILD_DIR, name)
        os.makedirs(outdir, exist_ok=True)
        spec_path = os.path.join(outdir, "BOUND_SPEC.json")
        json.dump(spec, open(spec_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        open(os.path.join(outdir, "SPEC.md"), "w", encoding="utf-8").write(render_md(name, t, bound_structure))

        check_output = check_capability_bindings.check_spec(spec_path)
        open(os.path.join(outdir, "CHECK_OUTPUT.txt"), "w", encoding="utf-8").write(check_output)
        print(f"--- {name} ---")
        print(check_output)


if __name__ == "__main__":
    sys.exit(main())
