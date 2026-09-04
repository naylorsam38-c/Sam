#!/usr/bin/env python3
"""
bind_and_assemble.py — binds every numbered item (SCR, ACT, NTF, RPT, OPS)
across all five locked templates to a real engine, writes the binding
directly into a generated spec (not a side document), assembles all five,
and runs a checker against each, saving its raw output alongside the spec.

Honesty note, stated up front because it changes what "done" can mean here:
this repository's Builder (packages/builder/builder.py) has a real, working
generation rule for exactly two things -- a record's CRUD routes and an
OAuth 'connect' action. It has no generic runtime for workflow transitions,
reports, custom actions, or notification delivery (confirmed by reading
builder.py directly: no 'workflow'/'transition'/'stage' handling anywhere,
no 'report' screen-kind rule). So CRUD/OAuth items bind to that real,
existing rule. Everything else binds to one of the 17 real engines in
packages/builder/engines/ ONLY where a real engine's own proven capability
actually matches that item's real declared behaviour (by name: a custom
action's own name, an automatic transition's own (workflow, from, to), a
report's own name, an OPS job's own timing shape). No new engine is written
here. An item with no real match is left UNBOUND and reported as such --
never given a fabricated binding just to make a checker print clean.

None of the five templates can be run through assemble.py's real customer-
facing path (assemble()) because every one of them, honestly, still leaves
real customer questions in ask_customer -- that is not a defect, it is the
whole point of "the front door does not guess" (see assemble.py's own
Refused paths). So this script produces a clearly-labelled, DIFFERENT
artifact per template: BOUND_SPEC.json, marked "customer_complete": false,
for verifying the engine-binding/registration mechanism only. It is not a
deployable spec and packages/loop/run_chain.py must not be pointed at it.

Usage: python bind_and_assemble.py
Outputs, per template, under build/<template>/:
  BOUND_SPEC.json   the locked structure + engine bindings, embedded in-line
  SPEC.md           the same thing, human-readable
  CHECK_OUTPUT.txt  the raw stdout of check_bindings.py run against it
"""

import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSEMBLY_DIR = os.path.join(HERE, "..", "assembly-engine")
sys.path.insert(0, os.path.abspath(ASSEMBLY_DIR))
sys.path.insert(0, HERE)

import assemble as ae   # noqa: E402  (registration_gaps() / REGISTERED_*_KINDS -- reused, not reimplemented)
import check_bindings   # noqa: E402

TEMPLATE_DIR = os.path.join(HERE, "templates")
BUILD_DIR = os.path.join(HERE, "build")
TEMPLATES = ["pm-teamwork", "crm-pipeline", "booking-frontdesk", "erp-backbone", "accounting-ledger"]

# ---------------------------------------------------------------- binding rules
# Every rule below is keyed on a real, already-declared fact in the template's
# own locked structure -- never a guess. (engines, note): engines is the real,
# proven module name(s) in packages/builder/engines/ that cover this item;
# note explains a partial match or names exactly what's still missing.

CUSTOM_ACTION_BINDINGS = {
    "Duplicate": (["record_cloning"], None),
    "Reassign": ([], "a plain restricted field edit -- no specialist engine needed, "
                      "but the Builder has no generic custom-action execution rule at all"),
    "Send": (["document_generation", "email_parsing"],
             "document rendering and message composition are real and proven; actually "
             "dispatching over SMTP was never built or proven, so this action is only "
             "partially covered"),
}

TRANSITION_BINDINGS = {
    ("Invoice lifecycle", "Awaiting payment", "Paid"): (["ledger_balancing"], None),
    ("Bill lifecycle", "Awaiting payment", "Paid"): (["ledger_balancing"], None),
    ("Purchase order lifecycle", "Confirmed", "Received"): (["stock_ledger"], None),
    ("Sales order lifecycle", "Confirmed", "Shipped"): (["stock_ledger"], None),
    ("Appointment lifecycle", "Booked", "Confirmed"): (
        [], "half of this transition is 'the deposit payment succeeds' -- needs live "
            "payment processing, not registered; the other half needs no engine at all, "
            "but the template models both as one automatic-triggered edge"),
}

REPORT_BINDINGS = {
    "Win rate": (["stage_history"], None),
    "No-show rate": (["stage_history"], None),
    "Sales by month": (["stage_history"], None),
    "Stock on hand": (["stock_ledger"], None),
}


def bind_action(act):
    if act["kind"] in ("create", "edit", "delete", "connect"):
        return ["(existing Builder rule -- CRUD/OAuth, no engine needed)"], None
    if act["kind"] == "custom":
        name = (act.get("detail") or {}).get("name")
        return CUSTOM_ACTION_BINDINGS.get(name, ([], "no binding rule for this custom action"))
    if act["kind"] == "transition":
        if act.get("mover") != "automatic":
            return [], "person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor"
        key = (act.get("workflow"), act.get("from"), act.get("to"))
        return TRANSITION_BINDINGS.get(key, ([], "no binding rule for this automatic transition"))
    return [], "no binding rule for this action kind"


def bind_screen(scr, report_bindings_by_name):
    if scr["kind"] in ae.REGISTERED_SCREEN_KINDS:
        return ["(existing Builder rule -- CRUD/OAuth, no engine needed)"], None
    if scr["kind"] == "report":
        return report_bindings_by_name.get(scr.get("report"), ([], "plain aggregation over existing fields -- no generic reporting engine was built"))
    return [], "no binding rule for this screen kind"


def bind_notification(name, notif):
    kind = (notif.get("trigger") or {}).get("kind")
    if kind in ("relative_to_date", "schedule"):
        return (["scheduled_jobs"],
                "covers the real timing half (wait until due, then fire); actual message "
                "delivery over email/sms/push has no engine -- see catalogue")
    return [], "event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine"


def bind_ops(op):
    # every OPS-nnn item is, by D11's own definition, a duration/schedule
    # answer that must become a real background job -- exactly scheduled_jobs.
    return ["scheduled_jobs"], None


def bind_structure(structure, inventory):
    """Pure function: returns a DEEP COPY of structure with an
    'engine_bindings' block added to every numbered item -- never mutates
    the locked structure in place. Screens/actions/recurring_ops get it
    inline on each list entry; notifications/reports (dicts) get it inline
    on each value."""
    s = copy.deepcopy(structure)
    report_engines = {name: bind_report_name(name) for name in inventory["reports"]}

    for scr in s["screens_inventory"]:
        engines, note = bind_screen(scr, report_engines)
        scr["engine_bindings"] = {"engines": engines, "note": note}
    for act in s["actions_inventory"]:
        engines, note = bind_action(act)
        act["engine_bindings"] = {"engines": engines, "note": note}
    for name, notif in s["notifications"].items():
        engines, note = bind_notification(name, notif)
        notif["engine_bindings"] = {"engines": engines, "note": note}
    for name, rep in s["reports"].items():
        engines, note = report_engines[name]
        rep["engine_bindings"] = {"engines": engines, "note": note}
    for op in s["recurring_ops"]:
        engines, note = bind_ops(op)
        op["engine_bindings"] = {"engines": engines, "note": note}
    return s


def bind_report_name(name):
    return REPORT_BINDINGS.get(name, ([], "plain aggregation over existing fields -- no generic reporting engine was built"))


def render_md(name, t, bound):
    out = [f"# {name} — bound spec (verification artifact, not customer-complete)\n",
           f"`customer_complete: false` -- {len(t['ask_customer'])} real customer questions are still open "
           f"({', '.join(t['ask_customer'][:6])}{'...' if len(t['ask_customer']) > 6 else ''}). "
           "This spec exists only to verify engine bindings against the locked structure; "
           "it must never be used to build a real app.\n"]
    out.append("## Screens\n")
    out.append("| id | kind | engines | note |\n|---|---|---|---|")
    for scr in bound["screens_inventory"]:
        eb = scr["engine_bindings"]
        out.append(f"| {scr['id']} | {scr['kind']} | {', '.join(eb['engines']) or '**UNBOUND**'} | {eb['note'] or ''} |")
    out.append("\n## Actions\n")
    out.append("| id | kind | engines | note |\n|---|---|---|---|")
    for act in bound["actions_inventory"]:
        eb = act["engine_bindings"]
        out.append(f"| {act['id']} | {act['kind']} | {', '.join(eb['engines']) or '**UNBOUND**'} | {eb['note'] or ''} |")
    out.append("\n## Notifications\n")
    out.append("| name | engines | note |\n|---|---|---|")
    for name_, notif in bound["notifications"].items():
        eb = notif["engine_bindings"]
        out.append(f"| {name_} | {', '.join(eb['engines']) or '**UNBOUND**'} | {eb['note'] or ''} |")
    out.append("\n## Reports\n")
    out.append("| name | engines | note |\n|---|---|---|")
    for name_, rep in bound["reports"].items():
        eb = rep["engine_bindings"]
        out.append(f"| {name_} | {', '.join(eb['engines']) or '**UNBOUND**'} | {eb['note'] or ''} |")
    out.append("\n## Recurring ops\n")
    out.append("| id | engines | note |\n|---|---|---|")
    for op in bound["recurring_ops"]:
        eb = op["engine_bindings"]
        out.append(f"| {op['id']} | {', '.join(eb['engines']) or '**UNBOUND**'} | {eb['note'] or ''} |")
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

        check_output = check_bindings.check_spec(spec_path)
        open(os.path.join(outdir, "CHECK_OUTPUT.txt"), "w", encoding="utf-8").write(check_output)
        print(f"--- {name} ---")
        print(check_output)


if __name__ == "__main__":
    sys.exit(main())
