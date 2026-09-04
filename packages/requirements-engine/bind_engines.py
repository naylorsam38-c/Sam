#!/usr/bin/env python3
"""
bind_engines.py — binds every numbered screen/action across the five locked
templates to an engine in packages/builder/ENGINE_CATALOGUE.md, by name.

Binding rules are a small, explicit table (below) keyed on the same real
facts already in each template's own locked structure -- a custom action's
own name, a report's own name, a transition's own (workflow, from, to) --
never a guess. An item with no matching rule is UNBOUND, listed as such,
not silently accepted.

Binding an engine to an item's underlying COMPUTATION is a separate fact
from whether packages/builder/builder.py has a real RENDERING/generation
rule for that item's KIND -- today builder.py only renders list/detail/
integration_status screens and generates create/edit/delete/connect
actions (see assemble.py's REGISTERED_SCREEN_KINDS/REGISTERED_ACTION_KINDS).
This script reports both facts separately for every numbered item, and
re-runs assemble.py's own registration_gaps() unmodified against each
template's real locked structure for the final "still blocking" list.

Usage: python bind_engines.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSEMBLY_DIR = os.path.join(HERE, "..", "assembly-engine")
sys.path.insert(0, os.path.abspath(ASSEMBLY_DIR))
sys.path.insert(0, HERE)

import assemble as ae   # noqa: E402  (registration_gaps() -- reused, not reimplemented)

TEMPLATE_DIR = os.path.join(HERE, "templates")
TEMPLATES = ["pm-teamwork", "crm-pipeline", "booking-frontdesk", "erp-backbone", "accounting-ledger"]

# -- custom action name -> engine(s), from SPECIALIST_ENGINES.md's own analysis
CUSTOM_ACTION_BINDINGS = {
    "Duplicate": (["record_cloning"], None),
    "Reassign": ([], "a plain restricted field edit -- no specialist engine needed, "
                      "but builder.py has no generic custom-action execution rule at all yet"),
    "Send": (["document_generation", "email_parsing"],
             "document rendering and message composition are bound and proven; actually "
             "dispatching over SMTP was not built or proven in this session, so this "
             "action is only partially covered"),
}

# -- (workflow, from, to) -> engine(s), for automatic/computed transitions only.
# Plain person-triggered transitions bind to nothing: no specialist engine is
# needed to interpret "role X presses a button", but builder.py has no generic
# workflow/state-machine execution rule at all -- a separate, distinct gap.
TRANSITION_BINDINGS = {
    ("Invoice lifecycle", "Awaiting payment", "Paid"): (["ledger_balancing"], None),
    ("Bill lifecycle", "Awaiting payment", "Paid"): (["ledger_balancing"], None),
    ("Purchase order lifecycle", "Confirmed", "Received"): (["stock_ledger"], None),
    ("Sales order lifecycle", "Confirmed", "Shipped"): (["stock_ledger"], None),
    ("Appointment lifecycle", "Booked", "Confirmed"): (
        [], "half of this transition is 'the deposit payment succeeds' -- needs live "
            "payment processing, not registered (see catalogue); the other half ('a "
            "staff member confirms manually') needs no engine at all, but the template "
            "models both as one automatic-triggered edge"),
}

# -- report name -> engine(s), where the report's own declared metric needs
# one of the built engines' real computation (stage-entry history, stock
# state). A report with no entry needs only plain aggregation over fields
# the record already has -- no engine was built for that (not in scope: no
# generic reporting/aggregation engine was named in the source list).
REPORT_BINDINGS = {
    "Win rate": (["stage_history"], None),
    "No-show rate": (["stage_history"], None),
    "Sales by month": (["stage_history"], None),
    "Stock on hand": (["stock_ledger"], None),
}


def bind_action(act):
    if act["kind"] in ("create", "edit", "delete", "connect"):
        return ["(none needed -- generic CRUD/OAuth rule)"], None
    if act["kind"] == "custom":
        name = (act.get("detail") or {}).get("name")
        engines, note = CUSTOM_ACTION_BINDINGS.get(name, ([], "no binding rule for this custom action"))
        return engines, note
    if act["kind"] == "transition":
        key = (act.get("workflow"), act.get("from"), act.get("to"))
        if act.get("mover") != "automatic":
            return [], "person-triggered -- no specialist engine needed, but no generic workflow executor is built"
        engines, note = TRANSITION_BINDINGS.get(key, ([], "no binding rule for this automatic transition"))
        return engines, note
    return [], "no binding rule for this action kind"


def bind_report(name):
    engines, note = REPORT_BINDINGS.get(name, ([], "plain aggregation over existing fields -- "
                                                     "no generic reporting engine was built"))
    return engines, note


def main():
    lines = ["# Engine bindings — every numbered item across the five locked templates\n",
             "Generated by `bind_engines.py`. For every numbered action and report, its "
             "bound engine(s) (by name, from `packages/builder/ENGINE_CATALOGUE.md`) or "
             "`UNBOUND` with the real reason. `still_blocking` is `assemble.py`'s own, "
             "unmodified `registration_gaps()` run against each template's real locked "
             "structure -- unaffected by binding, since builder.py's own rendering/"
             "generation rules were not changed in this delivery.\n"]

    overall_gaps = {}
    for name in TEMPLATES:
        t = json.load(open(os.path.join(TEMPLATE_DIR, f"{name}.json"), encoding="utf-8"))
        s = t["structure"]
        lines.append(f"\n## {name}\n")

        lines.append("**Actions**:\n")
        lines.append("| id | kind | detail | bound engine(s) | note |")
        lines.append("|---|---|---|---|---|")
        for act in s["actions_inventory"]:
            engines, note = bind_action(act)
            detail = act.get("record") or act.get("workflow") or act.get("form") or act.get("integration") or ""
            if act["kind"] == "custom":
                detail = f"{detail} / {(act.get('detail') or {}).get('name')}"
            elif act["kind"] == "transition":
                detail = f"{act.get('workflow')}: {act.get('from')} -> {act.get('to')}"
            status = ", ".join(engines) if engines else "**UNBOUND**"
            lines.append(f"| {act['id']} | {act['kind']} | {detail} | {status} | {note or ''} |")

        lines.append("\n**Reports**:\n")
        lines.append("| name | bound engine(s) | note |")
        lines.append("|---|---|---|")
        for rname in t["inventory"]["reports"]:
            engines, note = bind_report(rname)
            status = ", ".join(engines) if engines else "**UNBOUND**"
            lines.append(f"| {rname} | {status} | {note or ''} |")

        gaps = ae.registration_gaps(s)
        overall_gaps[name] = gaps
        lines.append(f"\n**Still blocking** (assemble.py's real, unmodified `registration_gaps()`, "
                      f"{len(gaps)} item(s)):\n")
        if gaps:
            for id_, kind, k in gaps:
                lines.append(f"- `{id_}` ({kind}, kind: `{k}`)")
        else:
            lines.append("- none")

    total = sum(len(g) for g in overall_gaps.values())
    lines.append(f"\n## Total still blocking across all five templates: {total}\n")
    with open(os.path.join(HERE, "BINDINGS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"wrote BINDINGS.md -- {total} items still blocking across {len(TEMPLATES)} templates")
    for name, gaps in overall_gaps.items():
        print(f"  {name}: {len(gaps)} blocking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
