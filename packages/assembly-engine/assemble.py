#!/usr/bin/env python3
"""
assemble.py — component 2 of the chain: a template's own locked, numbered
structure -> one authoritative specification for the Builder.

Does not ask questions (that is the Requirements Engine's job, component 1) and
does not decide what a good app looks like (that was decided once, in
question_graph_v3.json, and is not re-decided here). It also does not derive
that structure from raw answers any more -- that used to happen here, fresh,
on every run (derive()/build_model(), still defined below), which meant a
screen or action's number was never actually permanent: reorder an inventory
list and every number downstream could shift. That computation now runs
exactly ONCE per template, offline, via lock_structure.py
(requirements-engine/lock_structure.py), which writes its result back into
the template file as a frozen "structure" block with permanent, prefixed ids
(pm-teamwork/SCR-001, never renumbered by a later run). assemble() here only
loads that structure whole and configures it -- spec id, title, deploy inputs.
It does not recompute a single screen or action id.

Input: one "instance" JSON in the same shape as requirements-engine/templates/*.json
(inventory, answers, per_instance, ask_customer, features, structure) — OR
several such files to combine (--combine), unioned per CONFIG_MAP.md's rule
and reconciled with --reconcile OldName=NewName for shared records.

Refuses (exit 2) rather than assembling a guess when:
  * the instance does not fit the graph (reuses check_template.check — the
    requirements engine's own coverage/reference validator, not a second one)
  * ask_customer is non-empty (the front door has not finished its job)
  * the instance has no locked "structure" (run lock_structure.py first —
    assemble.py refuses to derive one on the fly)
  * any numbered screen or action in that structure has a kind the Builder has
    no registered rendering rule for (REGISTERED_SCREEN_KINDS /
    REGISTERED_ACTION_KINDS below, kept in lockstep with builder.py's own real
    rules) — blocks and lists every offending item's permanent id, never
    silently skips or pretends it will be handled

Output (-o DIR):
  SPEC.json   the numbered field map + the build model, for the Builder
  SPEC.md     the same thing, numbered and readable, for a human sign-off

Usage:
  python assemble.py instance.json -o out/
  python assemble.py --combine templates/booking-frontdesk.json templates/accounting-ledger.json \\
                      --reconcile Customer=Contact -o out/
"""

import argparse
import copy
import json
import os
import sys
from collections import OrderedDict, defaultdict

ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-engine")
sys.path.insert(0, os.path.abspath(ENGINE_DIR))

import graph_lib          # noqa: E402  (requirements-engine/graph_lib.py)
import check_template      # noqa: E402  (requirements-engine/check_template.py — reused, not reimplemented)

GRAPH_PATH = os.path.join(os.path.abspath(ENGINE_DIR), "question_graph_v3.json")

# D01 / D14 — fixed field-type -> storage-type map. Exhaustive over the graph's
# closed field-type list (config.field_types); the graph enforces that closure,
# so an unmapped type here means the graph gained a type this file must learn too.
STORAGE_TYPE = {
    "short_text": "VARCHAR(255)", "long_text": "TEXT", "whole_number": "INTEGER",
    "decimal_number": "DECIMAL(18,4)", "money": "DECIMAL(18,2)", "date": "DATE",
    "date_time": "DATETIME", "yes_no": "BOOLEAN", "one_choice": "ENUM",
    "multi_choice": "JSON_ARRAY", "email": "VARCHAR(255)", "phone": "VARCHAR(40)",
    "url": "VARCHAR(2048)", "file": "FILE_REF", "link": "FOREIGN_KEY",
    "other": "FOREIGN_KEY_ROLE",  # every 'other' field in this graph is the person/user reference (see build_templates.py USER_REF)
}


class Refused(Exception):
    """Assembly refused: the answer set does not license a spec yet."""


# Kinds the Builder (packages/builder/builder.py) actually has a generation
# rule for today -- checked directly against its own code (build_screens()'s
# kind dispatch; crud_routes()/oauth_routes()'s own real routes), not guessed.
# Keep these two sets in lockstep with builder.py by hand: it is the one
# ground truth for "real Builder capability", and this file must never claim
# more than that ground truth supports.
REGISTERED_SCREEN_KINDS = {"list", "detail", "integration_status", "form", "report"}
REGISTERED_ACTION_KINDS = {"create", "edit", "delete", "connect", "transition", "custom",
                           "submit", "approve"}


def registration_gaps(structure):
    """Every numbered screen/action in a locked structure the Builder has no
    real rule for, as (id, kind, what) tuples -- never silently dropped, always
    named by their own permanent id so a human can see exactly what is missing
    without re-deriving anything.

    A registered KIND is not enough: the Builder's rule for a report needs that
    report's own executable ReportSpec, and its rule for a custom action needs
    that action's own executable effect. An item that does not carry what its
    rule needs is still a gap, because the Builder will still refuse it -- this
    gate stays in lockstep with what builder.py can really do, not with what it
    recognises the name of."""
    gaps = []
    reports = structure.get("reports") or {}
    for scr in structure.get("screens_inventory") or []:
        if scr["kind"] not in REGISTERED_SCREEN_KINDS:
            gaps.append((scr["id"], "screen", scr["kind"]))
        elif scr["kind"] == "report" and not (reports.get(scr.get("report")) or {}).get("spec"):
            gaps.append((scr["id"], "screen", "report (no executable ReportSpec)"))
    for act in structure.get("actions_inventory") or []:
        if act["kind"] not in REGISTERED_ACTION_KINDS:
            gaps.append((act["id"], "action", act["kind"]))
        elif act["kind"] == "custom" and not (act.get("detail") or {}).get("execution"):
            gaps.append((act["id"], "action", "custom (no executable effect)"))
    return gaps


#: Flip to True once a real sign-in engine exists on the shelf and builder.py
#: enforces sessions on every route (Job 6 of the 2026-09-06 Codex handoff).
#: Until then, an unenforced auth requirement is reported on the assembled
#: spec (never hidden) but does not block the build -- flipping this before
#: that engine exists would make every template refuse, with no part able to
#: close the gap, which is worse than an honest, visible, non-blocking flag.
ENFORCE_AUTH_GATE = False


def auth_registration_gap(auth):
    """None if `auth` (the AU.* answers) needs nothing the Builder cannot
    build, or a human-readable reason if it does. Today the Builder has zero
    sign-in enforcement of any kind, so any account-creation mode beyond "no
    real accounts" (AU.01 unset or explicitly none) is a real gap -- the app
    would tell every visitor they are whoever the request claims to be."""
    creation = auth.get("AU.01")
    if not creation or creation in ("none", []):
        return None
    return (f"AU.01 declares real accounts (creation: {creation!r}) but no sign-in engine is "
            f"registered on the shelf yet -- every route would trust an unauthenticated caller")


def _rename_refs_in_structure(structure, rename):
    """Rewrite record-name references inside a locked structure, for the real
    shapes build_model() actually produces (checked against every real
    structure block the five templates lock, not a generic JSON walk -- same
    discipline as _rename_refs below, which did the equivalent job for raw
    per_instance answers before structures were frozen). Renaming a record's
    own dict key is not enough: a link field's target_record, and any screen/
    action/notification that names a record, must move with it."""
    structure = copy.deepcopy(structure)
    structure["records"] = {
        rename(name): {
            **rec,
            "fields": {fname: (dict(fd, target_record=rename(fd["target_record"])) if fd.get("type") == "link" else fd)
                       for fname, fd in rec["fields"].items()},
        }
        for name, rec in structure["records"].items()
    }
    for scr in structure.get("screens_inventory") or []:
        if scr.get("record"):
            scr["record"] = rename(scr["record"])
    for act in structure.get("actions_inventory") or []:
        if act.get("record"):
            act["record"] = rename(act["record"])
    for notif in (structure.get("notifications") or {}).values():
        trig = notif.get("trigger") or {}
        if trig.get("record"):
            trig["record"] = rename(trig["record"])
        for r_ in notif.get("recipients") or []:
            if isinstance(r_, dict) and r_.get("kind") == "field" and r_.get("record"):
                r_["record"] = rename(r_["record"])
    return structure


def _merge_structures(structures):
    """Union several already-locked structures. Every id inside each one is
    already permanently prefixed by lock_structure.py with its own template's
    name, so concatenation can never collide two numbers and never needs a
    renumber -- exactly the point of freezing them first."""
    merged = {"records": {}, "roles": {}, "super_role": structures[0].get("super_role"),
              "workflows": {}, "notifications": {}, "reports": {}, "forms": {},
              "integrations": {}, "auth": {}, "brand": structures[0].get("brand"),
              "screens_inventory": [], "navigation": [], "landing_per_role": {},
              "actions_inventory": [], "recurring_ops": [], "qa_generated_tests": []}
    for s in structures:
        merged["records"].update(s["records"])
        merged["roles"].update(s["roles"])
        merged["workflows"].update(s["workflows"])
        merged["notifications"].update(s["notifications"])
        merged["reports"].update(s["reports"])
        merged["forms"].update(s["forms"])
        merged["integrations"].update(s["integrations"])
        merged["auth"].update(s.get("auth") or {})
        merged["landing_per_role"].update(s.get("landing_per_role") or {})
        merged["screens_inventory"] += s["screens_inventory"]
        merged["navigation"] += s["navigation"]
        merged["actions_inventory"] += s["actions_inventory"]
        merged["recurring_ops"] += s["recurring_ops"]
        merged["qa_generated_tests"] += s["qa_generated_tests"]
    return merged


def _rename_refs(qid, val, rename):
    """Rewrite record-name references inside a per-instance answer value, for the
    two field shapes the graph actually uses to reference another record by name
    (checked against every real per-instance shape in the five templates — not a
    generic JSON walk, since guessing which arbitrary string is 'a record name'
    is exactly the kind of invention this tool refuses to do elsewhere). Renaming
    an inventory item's own name (done by the caller) is not enough — a link
    field's target_record or a relation's target names the record independently
    and must move with it."""
    if qid == "R.02" and isinstance(val, list):
        return [dict(fd, target_record=rename(fd["target_record"])) if fd.get("type") == "link" else fd for fd in val]
    if qid == "R.11" and isinstance(val, list):
        return [dict(rel, target=rename(rel["target"])) for rel in val]
    return val


# --------------------------------------------------------------------------- combine
def combine(paths, reconcile):
    """Union several completed instances into one, per CONFIG_MAP.md's rule:
    union inventories, union answers/per_instance, reconcile named record clashes
    before the union (never silently — a name collision that isn't reconciled is
    a coverage/reference error the validator below will catch)."""
    insts = [json.load(open(p, encoding="utf-8")) for p in paths]

    def rename(s):
        return reconcile.get(s, s)

    merged = {
        "template": "+".join(i["template"] for i in insts),
        "source_app": " + ".join(i["source_app"] for i in insts),
        "category": "combined",
        "modules": sorted({m for i in insts for m in i["modules"]}),
        "inventory": defaultdict(list, {k: [] for k in
                     ("records", "roles", "forms", "notifications", "reports",
                      "workflows", "file_types", "integrations", "screens")}),
        "super_role": insts[0]["super_role"],
        "answers": {},
        "per_instance": {},
        "ask_customer": [],
        "features": [f for i in insts for f in i["features"]],
    }
    for i in insts:
        for kind, items in i["inventory"].items():
            for it in items:
                it2 = rename(it)
                if it2 not in merged["inventory"][kind]:
                    merged["inventory"][kind].append(it2)
        for qid, val in i["answers"].items():
            existing = merged["answers"].get(qid)
            if isinstance(existing, dict) and isinstance(val, dict):
                merged["answers"][qid] = {**existing, **val}   # e.g. C.06: role -> landing screen, union not overwrite
            else:
                merged["answers"][qid] = val   # a real scalar clash surfaces as a validator error downstream
        for key, val in i["per_instance"].items():
            qid, rest = key.split(":", 1)
            parts = rest.split(":")
            parts[0] = rename(parts[0])
            merged["per_instance"][f"{qid}:{':'.join(parts)}"] = _rename_refs(qid, val, rename)
        merged["ask_customer"] += [a for a in i["ask_customer"] if a not in merged["ask_customer"]]
    merged["inventory"] = dict(merged["inventory"])

    missing = [i["template"] for i in insts if not i.get("structure")]
    if missing:
        raise Refused("cannot combine -- these templates have no locked structure yet "
                       "(run lock_structure.py on them first): " + ", ".join(missing))
    renamed_structures = [_rename_refs_in_structure(i["structure"], rename) for i in insts]
    merged["structure"] = _merge_structures(renamed_structures)
    return merged


# --------------------------------------------------------------------------- lookups
def pk(key):
    bits = key.split(":")
    return bits[0], bits[1] if len(bits) > 1 else None, bits[2] if len(bits) > 2 else None


def get(inst, qid, inst_name=None, graph=None):
    if inst_name is not None and graph["_q"][qid]["per"]:
        return inst["per_instance"].get(f"{qid}:{inst_name}")
    return inst["answers"].get(qid)


def fields_of(inst, record):
    return {fd["name"]: fd for fd in (inst["per_instance"].get(f"R.02:{record}") or [])}


# --------------------------------------------------------------------------- derivations
def derive(graph, inst):
    """D01–D15. Each function's docstring is the graph's own `rule` text for that
    derivation id, so the mapping between code and the graph's declared logic stays
    checkable by inspection."""
    inv = inst["inventory"]
    records, roles, workflows = inv["records"], inv["roles"], inv["workflows"]
    d = {}

    # D01 — Fixed 1:1 map from field type to column type.
    d["D01"] = {r: {fname: STORAGE_TYPE[fd["type"]] for fname, fd in fields_of(inst, r).items()} for r in records}

    # D14 — Choice options become an enum with the exact listed values.
    d["D14"] = {
        r: {fname: fd["options"] for fname, fd in fields_of(inst, r).items() if fd["type"] in ("one_choice", "multi_choice")}
        for r in records
    }

    # D02 — Form fields = target record's fields + extra fields.
    forms = {}
    for fm in inv["forms"]:
        target = (inst["per_instance"].get(f"F.02:{fm}") or {}).get("target")
        base = list(fields_of(inst, target)) if target else []
        extra = [x["field"] for x in (inst["per_instance"].get(f"F.03:{fm}") or [])]
        forms[fm] = base + extra
    d["D02"] = forms

    # D04 — Permitted = every explicit grant; forbidden = everything else (default deny); admin = any user-management grant.
    all_verbs = {"view", "create", "edit", "delete"}
    permitted, is_admin = {r: [] for r in roles}, {r: False for r in roles}
    for r in records:
        for verb, qid in (("view", "R.05"), ("create", "R.06"), ("edit", "R.07"), ("delete", "R.08")):
            ans = inst["per_instance"].get(f"{qid}:{r}")
            if not ans or ans == "nobody":   # roles_scoped questions may legally answer 'nobody'
                continue
            granted = ans if qid == "R.06" else [e["role"] for e in ans]
            scoped = {e["role"]: e.get("scope") for e in ans} if qid != "R.06" else {}
            for role in granted:
                if role in permitted:
                    permitted[role].append({"action": verb, "record": r, "scope": scoped.get(role, "all")})
    for role in roles:
        if role == inst.get("super_role"):
            is_admin[role] = True
            continue
        au11, au13 = inst["answers"].get("AU.11") or {}, inst["answers"].get("AU.13") or []
        is_admin[role] = role in (au11.get("by") or []) or role in au13
    # forbidden per record: everything not explicitly granted for that record (default deny)
    forbidden_per_record = {r: {rec: sorted(all_verbs - {p["action"] for p in permitted[r] if p["record"] == rec}) for rec in records} for r in roles}
    d["D04"] = {"permitted_actions": permitted, "forbidden_actions": forbidden_per_record, "is_admin": is_admin}

    # D05 — Immediate on event; offset for relative_to_date; cron for schedule.
    timing = {}
    for n in inv["notifications"]:
        trig = inst["per_instance"].get(f"N.01:{n}") or {}
        kind = trig.get("kind")
        timing[n] = ("immediate" if kind == "event" else
                      f"offset:{trig.get('offset')}" if kind == "relative_to_date" else
                      f"cron:{trig.get('schedule')}" if kind == "schedule" else "unspecified")
    d["D05"] = timing

    # D06 — File inherits its parent record's retention.
    d["D06"] = {ft: (inst["per_instance"].get(f"R.14:{(inst['per_instance'].get(f'FI.01:{ft}') or {}).get('parent')}"))
                for ft in inv["file_types"]}

    # D07 — Unflagged metric = count/sum of the named field; flagged metric = RP.05 text.
    reports = {}
    terms = [w.lower() for w in graph["config"]["ambiguous_metric_terms"]]
    for rp in inv["reports"]:
        metrics = inst["per_instance"].get(f"RP.04:{rp}") or []
        defs = {}
        for m in metrics:
            flagged = any(w in m.lower() for w in terms)
            defs[m] = (inst["per_instance"].get(f"RP.05:{rp}:{m}") if flagged else f"auto: count/sum of '{m}'")
        reports[rp] = {"data_source": (inst["per_instance"].get(f"RP.01:{rp}") or ""), "metrics": defs}
    d["D07"] = reports

    # Not a numbered derivation on its own — the graph's Part FLX (external
    # systems) restates directly into build_model the same way D08 restates
    # FL.03, since none of the five templates use an integration and this path
    # has had no real data to derive against until Command Desk (component 8).
    integrations = {}
    for i in inv.get("integrations") or []:
        integrations[i] = {
            "purpose": inst["per_instance"].get(f"FLX.01:{i}"),
            "sends": (inst["per_instance"].get(f"FLX.02:{i}") or {}).get("sends"),
            "receives": (inst["per_instance"].get(f"FLX.02:{i}") or {}).get("receives"),
            "timing": inst["per_instance"].get(f"FLX.03:{i}"),
            "connection_scope": inst["per_instance"].get(f"FLX.04:{i}"),
            "on_unavailable": inst["per_instance"].get(f"FLX.05:{i}"),
        }
    d["FLX"] = integrations

    # D08 — Edges exactly as listed in FL.03; nothing added.
    d["D08"] = {w: inst["per_instance"].get(f"FL.03:{w}") or [] for w in workflows}

    # D09 — Operator role sees all orgs; everyone else sees their memberships.
    d["D09"] = {"operator_sees": "all_orgs", "others_see": "own_memberships"} if inv.get("orgs") is not None else None

    # D10 — Each subscription event links to one plan by name.
    d["D10"] = inst["answers"].get("B.03")

    # D11 — Every duration/schedule answer becomes one OPS-nnn job.
    ops_inputs = next(dv for dv in graph["derivations"] if dv["id"] == "D11")["inputs"]
    ops_items = []
    n = 1
    for qid in ops_inputs:
        q = graph["_q"][qid]
        if q["per"]:
            pool = inv.get(check_template.KIND_TO_INVENTORY.get(q["per"])) or []
            for inst_name in pool:
                v = inst["per_instance"].get(f"{qid}:{inst_name}")
                if v:
                    ops_items.append({"id": f"OPS-{n:03d}", "source": f"{qid}:{inst_name}", "detail": v})
                    n += 1
        else:
            v = inst["answers"].get(qid)
            if v:
                ops_items.append({"id": f"OPS-{n:03d}", "source": qid, "detail": v})
                n += 1
    d["D11"] = ops_items

    # D12 — One numbered action per create/edit/delete grant, custom action, transition, cancel, approve, form submit.
    # Each action also carries "outcome": a plain restatement of its own already-declared
    # fields (verb+record, the custom action's own R.15 effect text, the transition's own
    # from/to, etc.) -- never new business content, just the declared outcome made explicit
    # per action, so a numbered action's outcome and permitted role are both in one place.
    actions = []
    n = 1
    for r in records:
        for verb, roles_with in (("create", [ro for ro in roles if any(p["record"] == r and p["action"] == "create" for p in permitted[ro])]),
                                  ("edit", [ro for ro in roles if any(p["record"] == r and p["action"] == "edit" for p in permitted[ro])]),
                                  ("delete", [ro for ro in roles if any(p["record"] == r and p["action"] == "delete" for p in permitted[ro])])):
            if roles_with:
                verb_text = {"create": "creates a new", "edit": "edits an existing", "delete": "deletes a"}[verb]
                actions.append({"id": f"ACT-{n:03d}", "kind": verb, "record": r, "roles": roles_with,
                                 "outcome": f"{verb_text} '{r}' record"})
                n += 1
        for ca in inst["per_instance"].get(f"R.15:{r}") or []:
            actions.append({"id": f"ACT-{n:03d}", "kind": "custom", "record": r, "detail": ca,
                             "roles": ca.get("who"), "outcome": ca.get("effect")})
            n += 1
    for w in workflows:
        for t in inst["per_instance"].get(f"FL.03:{w}") or []:
            actions.append({"id": f"ACT-{n:03d}", "kind": "transition", "workflow": w, "from": t["from"], "to": t["to"],
                             "mover": t.get("mover"), "roles": t.get("roles"),
                             "outcome": f"moves '{w}' from '{t['from']}' to '{t['to']}'"})
            n += 1
        cancel = inst["per_instance"].get(f"FL.07:{w}") or {}
        if cancel.get("allowed") == "yes":
            actions.append({"id": f"ACT-{n:03d}", "kind": "cancel", "workflow": w, "roles": cancel.get("by"),
                             "from_stages": cancel.get("from_stages"),
                             "outcome": f"cancels '{w}' from stage(s) {cancel.get('from_stages')}"})
            n += 1
        for a in inst["per_instance"].get(f"FL.05:{w}") or []:
            actions.append({"id": f"ACT-{n:03d}", "kind": "approve", "workflow": w, "stage": a.get("stage"), "roles": a.get("approvers"),
                             "outcome": f"approves '{w}' at stage '{a.get('stage')}'"})
            n += 1
    for fm in inv["forms"]:
        target = (inst["per_instance"].get(f"F.02:{fm}") or {}).get("target")
        actions.append({"id": f"ACT-{n:03d}", "kind": "submit", "form": fm, "record": target, "roles": None,
                         "outcome": f"submits the '{fm}' form" + (f", creating/editing its target record '{target}'" if target else "")})
        n += 1
    for i, flx in d["FLX"].items():
        if (flx.get("timing") or {}).get("kind") == "manual":
            roles_ = flx["timing"].get("who") or []
            actions.append({"id": f"ACT-{n:03d}", "kind": "connect", "integration": i, "roles": roles_,
                             "outcome": f"starts the OAuth connect flow for integration '{i}'"})
            n += 1
    d["D12"] = actions

    # D13 — One list + one detail screen per record, one per form/report, plus landing per role.
    screens = []
    n = 1
    for r in records:
        screens.append({"id": f"SCR-{n:03d}", "kind": "list", "record": r}); n += 1
        screens.append({"id": f"SCR-{n:03d}", "kind": "detail", "record": r}); n += 1
    for fm in inv["forms"]:
        screens.append({"id": f"SCR-{n:03d}", "kind": "form", "form": fm,
                         "record": (inst["per_instance"].get(f"F.02:{fm}") or {}).get("target")}); n += 1
    for rp in inv["reports"]:
        screens.append({"id": f"SCR-{n:03d}", "kind": "report", "report": rp}); n += 1
    for i in d["FLX"]:
        screens.append({"id": f"SCR-{n:03d}", "kind": "integration_status", "integration": i}); n += 1
    landing = inst["answers"].get("C.06") or {}
    d["D13"] = {"screens": screens, "navigation": [s["id"] for s in screens], "landing_per_role": landing}

    # D15 — For every numbered action and transition: perform it as each role, assert the declared outcome and location.
    tests = []
    n = 1
    for a in d["D12"]:
        for role in (a.get("roles") or ["<any authenticated role>"]):
            tests.append({
                "id": f"QA-{n:03d}", "action_id": a["id"], "role": role, "action": a,
                "expect": "the action's declared effect is observable and the response location matches the record/workflow it acted on",
            })
            n += 1
    for role in roles:
        for scr in d["D13"]["screens"]:
            allowed = True
            if scr["kind"] in ("list", "detail") and scr.get("record"):
                allowed = role in permitted and any(p["record"] == scr["record"] and p["action"] == "view" for p in permitted[role])
            tests.append({"id": f"QA-{n:03d}", "kind": "screen_access", "screen_id": scr["id"], "role": role,
                          "expect": "reachable" if allowed else "blocked (403 or absent from navigation)"})
            n += 1
    d["D15"] = tests

    return d


# --------------------------------------------------------------------------- numbered field map
def build_field_map(graph, inst):
    """Every spec field, traced to the question/default/derivation/deploy-input
    that owns it (graph_lib.field_source), with its resolved value. Refuses
    (raises Refused) if a field's owning question fires but the answer is absent
    — that is a coverage gap the caller must have already ruled out, so hitting
    it here means the graph and the instance disagree about what 'complete' means."""
    sources = graph_lib.field_source(graph)
    inv = inst["inventory"]
    rows = []

    def add(number, spec_field, value, kind):
        rows.append({"number": number, "spec_field": spec_field, "value": value, "source_kind": kind})

    for spec_field, owner in sorted(sources.items()):
        kind = graph_lib.owner_kind(graph, owner)
        if kind == "question" and owner == "A.15":
            # Special shape: A.15's nine fills are `inventory.<kind>` flat fields whose
            # value is the inventory array itself, not an `answers["A.15"]` entry.
            invkind = spec_field.split(".", 1)[1]
            add(owner, spec_field, inv.get(invkind), kind)
        elif kind == "question" and owner == "RP.05":
            # Special shape: the only two-placeholder field in the graph — one row per
            # (report, flagged metric) pair, mirroring check_template.py's own coverage walk.
            terms = [w.lower() for w in graph["config"]["ambiguous_metric_terms"]]
            for rp in inv.get("reports") or []:
                for m in inst["per_instance"].get(f"RP.04:{rp}") or []:
                    if any(w in m.lower() for w in terms):
                        concrete = f"report.{rp}.metric.{m}.definition"
                        add(f"{owner}:{rp}:{m}", concrete, inst["per_instance"].get(f"{owner}:{rp}:{m}"), kind)
        elif kind == "question":
            q = graph["_q"][owner]
            if q["per"] is None:
                add(owner, spec_field, inst["answers"].get(owner), kind)
            elif "{" in spec_field:
                pool_key = check_template.KIND_TO_INVENTORY.get(q["per"])
                for item in (inv.get(pool_key) or []):
                    concrete = spec_field.replace("{" + spec_field[spec_field.index("{") + 1:spec_field.index("}")] + "}", item)
                    add(f"{owner}:{item}", concrete, inst["per_instance"].get(f"{owner}:{item}"), kind)
            else:
                add(owner, spec_field, inst["answers"].get(owner) or inst["per_instance"].get(owner), kind)
        elif kind == "system_default":
            default = next(x for x in graph["system_defaults"] if x["id"] == owner)
            add(owner, spec_field, default["behaviour"], kind)
        elif kind == "derivation":
            add(owner, spec_field, f"see build_model.{owner}", kind)
        elif kind == "deploy_input":
            di = next(x for x in graph["deploy_inputs"] if x["id"] == owner)
            deploy_answers = inst.get("deploy_answers") or {}
            add(owner, spec_field, deploy_answers.get(owner, "[PENDING — collected at deploy time, not at requirements time]"), kind)
    return rows


# --------------------------------------------------------------------------- top level
# derive() and build_model() are no longer called by assemble() below -- they
# are used exactly once per template, by requirements-engine/lock_structure.py,
# to freeze a template's numbered "structure" block. Kept here (not moved)
# because assemble() still imports this module for Refused/check_template/
# graph_lib wiring, and because lock_structure.py explicitly reuses these two
# functions rather than reimplementing derivation logic a second time. Tests
# that want real structural facts from a real template without a locked
# structure (e.g. a template that predates lock_structure.py) can still call
# derive()+build_model() directly; assemble() itself never does.
def build_model(inst, derived):
    """The concrete, expanded structures the Builder and the Playwright tester
    actually read. Pure function of an instance's real inventory/answers plus
    its derived values — no completeness check here (that is assemble()'s job)
    so callers who only need real structural facts (e.g. Builder unit tests
    against a real template's real records) can call this directly without
    needing a customer-complete instance."""
    return {
        "records": {r: {"fields": fields_of(inst, r), "storage": derived["D01"][r], "enums": derived["D14"][r],
                         "access": {"view": inst["per_instance"].get(f"R.05:{r}"), "create": inst["per_instance"].get(f"R.06:{r}"),
                                    "edit": inst["per_instance"].get(f"R.07:{r}"), "delete": inst["per_instance"].get(f"R.08:{r}")},
                         "title_field": inst["per_instance"].get(f"R.03:{r}"), "id_style": inst["per_instance"].get(f"R.04:{r}"),
                         "lifecycle": inst["per_instance"].get(f"R.10:{r}"), "retention": inst["per_instance"].get(f"R.14:{r}"),
                         "custom_actions": inst["per_instance"].get(f"R.15:{r}") or [],
                         # declared, executable effects of creating a row (accounting-ledger's
                         # Payment settling the Invoice/Bill it is applied to) -- from the
                         # template's own create_effects block, never inferred from prose
                         "on_create": (inst.get("create_effects") or {}).get(r) or []}
                    for r in inst["inventory"]["records"]},
        "roles": {ro: {"permitted": derived["D04"]["permitted_actions"][ro], "is_admin": derived["D04"]["is_admin"][ro]}
                  for ro in inst["inventory"]["roles"]},
        "super_role": inst.get("super_role"),
        "workflows": {w: {"trigger": inst["per_instance"].get(f"FL.01:{w}"), "stages": inst["per_instance"].get(f"FL.02:{w}"),
                           "transitions": derived["D08"][w], "approvals": inst["per_instance"].get(f"FL.05:{w}") or [],
                           "on_reject": inst["per_instance"].get(f"FL.06:{w}"), "cancel": inst["per_instance"].get(f"FL.07:{w}"),
                           "timeouts": inst["per_instance"].get(f"FL.10:{w}") or [],
                           # the executable form of FL.08's on_complete prose (erp-backbone's
                           # stock movements on Received/Shipped) -- from the template's own
                           # transition_effects block; a workflow without one has none
                           "effects": (inst.get("transition_effects") or {}).get(w) or []}
                      for w in inst["inventory"]["workflows"]},
        "notifications": {n: {"trigger": inst["per_instance"].get(f"N.01:{n}"), "recipients": inst["per_instance"].get(f"N.02:{n}"),
                               "channels": inst["per_instance"].get(f"N.03:{n}"), "timing": derived["D05"][n]}
                           for n in inst["inventory"]["notifications"]},
        "reports": {name: dict(rep, spec=(inst.get("report_specs") or {}).get(name))
                     for name, rep in derived["D07"].items()},
        "forms": derived["D02"],
        "integrations": {name: dict(flx, auth=(inst.get("integration_auth") or {}).get(name, "oauth"))
                          for name, flx in derived["FLX"].items()},
        "auth": {k: v for k, v in inst["answers"].items() if k.startswith("AU.")},
        "brand": {"app_name": inst["answers"].get("A.05"), "assets": inst["answers"].get("C.04")},
        "screens_inventory": derived["D13"]["screens"],
        "navigation": derived["D13"]["navigation"],
        "landing_per_role": derived["D13"]["landing_per_role"],
        "actions_inventory": derived["D12"],
        "recurring_ops": derived["D11"],
        "qa_generated_tests": derived["D15"],
    }


def assemble(graph, inst, spec_id, title):
    errors = check_template.check(graph, inst)
    if errors:
        raise Refused("instance does not fit the graph:\n" + "\n".join(f"  - {e}" for e in errors))
    structure = inst.get("structure")
    if not structure:
        raise Refused("this template has no locked structure -- run requirements-engine/lock_structure.py "
                       "on it first. assemble.py configures a structure; it does not derive one from answers.")
    if inst["ask_customer"]:
        raise Refused("front door has not finished: still open for the customer:\n" +
                       "\n".join(f"  - {q}" for q in inst["ask_customer"]))

    gaps = registration_gaps(structure)
    if gaps:
        raise Refused("numbered items with no registered Builder implementation -- blocked, not skipped:\n" +
                       "\n".join(f"  - {id_} ({kind}, kind: {k})" for id_, kind, k in gaps))

    fields = build_field_map(graph, inst)
    # The structure is frozen at lock time, before the customer answers the
    # questions every template leaves open (A.05 name, C.04 brand, and the
    # auth block). Those mint no ids -- they are configuration, exactly what
    # this function exists to apply -- so they are overlaid here from the
    # instance's own answers. Found by building a reference instance and
    # seeing "App" as its name on every screen.
    structure = copy.deepcopy(structure)
    structure["brand"] = {"app_name": inst["answers"].get("A.05"), "assets": inst["answers"].get("C.04")}
    structure["auth"] = {k: v for k, v in inst["answers"].items() if k.startswith("AU.")}
    auth_gap = auth_registration_gap(structure["auth"])
    if auth_gap and ENFORCE_AUTH_GATE:
        raise Refused(f"auth registration gap -- blocked, not skipped:\n  - {auth_gap}")
    return {
        "spec_id": spec_id, "version": 1, "title": title,
        "graph_version": graph["version"],
        "source_template": inst.get("template"),
        "numbered_fields": fields,
        "build_model": structure,
        # None once ENFORCE_AUTH_GATE is on and every family has a real sign-in
        # part -- until then this is the honest, visible record that nothing
        # enforces who is acting, carried on the spec rather than hidden.
        "auth_registration_gap": auth_gap,
    }


def render_markdown(spec):
    out = [f"# {spec['title']}", "", f"`{spec['spec_id']}` — assembled from `{spec['source_template']}` "
           f"against graph {spec['graph_version']}. Every field below is numbered by the question, "
           f"default, or derivation that owns it — nothing here was guessed.", ""]
    by_prefix = defaultdict(list)
    for row in spec["numbered_fields"]:
        by_prefix[row["spec_field"].split(".")[0]].append(row)
    for prefix in sorted(by_prefix):
        out.append(f"## {prefix}")
        out.append("")
        out.append("| # | Field | Value | Source |")
        out.append("|---|---|---|---|")
        for row in sorted(by_prefix[prefix], key=lambda r: r["spec_field"]):
            val = json.dumps(row["value"], ensure_ascii=False) if not isinstance(row["value"], str) else row["value"]
            val = (val[:80] + "…") if len(str(val)) > 80 else val
            out.append(f"| {row['number']} | `{row['spec_field']}` | {val} | {row['source_kind']} |")
        out.append("")
    bm = spec["build_model"]
    out.append("## Build model summary")
    out.append("")
    out.append(f"- Records: {', '.join(bm['records'])}")
    out.append(f"- Roles: {', '.join(bm['roles'])} (super: {bm['super_role']})")
    out.append(f"- Workflows: {', '.join(bm['workflows']) or 'none'}")
    out.append(f"- Screens: {len(bm['screens_inventory'])} (`{spec['spec_id']}` navigation order)")
    out.append(f"- Actions: {len(bm['actions_inventory'])}")
    out.append(f"- Generated QA tests: {len(bm['qa_generated_tests'])}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("instance", nargs="?", help="a completed instance JSON")
    ap.add_argument("--combine", nargs="+", help="combine several completed instances")
    ap.add_argument("--reconcile", nargs="*", default=[], help="OldName=NewName record renames applied before combining")
    ap.add_argument("--deploy-answers", help="optional deploy-inputs JSON (block 0, collected separately from the interview)")
    ap.add_argument("--spec-id", default="SPEC-ASSEMBLED-001")
    ap.add_argument("--title", default="Assembled specification")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)

    graph = graph_lib.load_graph(GRAPH_PATH)
    graph["_q"] = {q["id"]: q for q in graph["questions"]}

    if args.combine:
        reconcile = dict(x.split("=", 1) for x in args.reconcile)
        inst = combine(args.combine, reconcile)
    elif args.instance:
        inst = json.load(open(args.instance, encoding="utf-8"))
    else:
        ap.error("supply an instance file or --combine")

    if args.deploy_answers:
        inst["deploy_answers"] = json.load(open(args.deploy_answers, encoding="utf-8"))

    try:
        spec = assemble(graph, inst, args.spec_id, args.title)
    except Refused as e:
        print("REFUSED —", e, file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    json.dump(spec, open(os.path.join(args.out, "SPEC.json"), "w", encoding="utf-8"), indent=2, default=str)
    open(os.path.join(args.out, "SPEC.md"), "w", encoding="utf-8").write(render_markdown(spec))
    print(f"assembled {len(spec['numbered_fields'])} numbered fields, "
          f"{len(spec['build_model']['actions_inventory'])} actions, "
          f"{len(spec['build_model']['screens_inventory'])} screens, "
          f"{len(spec['build_model']['qa_generated_tests'])} generated tests -> {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
