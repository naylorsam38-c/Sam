#!/usr/bin/env python3
"""
lock_structure.py — freezes a template's numbered build structure, once.

The five templates in templates/*.json are answer-sets: a template only holds
answers to question_graph_v3.json, never a structure of its own. Assembling used
to mean recomputing "structure" (which screen exists, which action, its number)
fresh from those answers on every run, via the Assembly Engine's derive()/
build_model() (packages/assembly-engine/assemble.py). Nothing was permanent:
run it twice with the answers reordered and the numbers could land differently.

This script runs that same derive()/build_model() (imported, not reimplemented
-- there is exactly one place in this repo that turns answers into a build
model) exactly ONCE per template and writes the result back into the template
file as a new top-level "structure" key. From then on:
  * assemble.py no longer calls derive()/build_model() itself -- it loads
    structure verbatim and only configures it (spec id, title, deploy inputs).
  * every id in structure (SCR-nnn, ACT-nnn, NOTIF-nnn, RPT-nnn, STG-nnn,
    TRN-nnn, OPS-nnn, QA-nnn) is prefixed with the template's own name
    ("pm-teamwork/SCR-001"), so combining templates later can never collide
    two numbers or force a renumber.
  * re-running this script is idempotent for anything already numbered: it
    loads the template's EXISTING structure first and reuses every id whose
    natural key (e.g. record+verb for a CRUD action, workflow+stage name for
    a transition) still matches. Only a genuinely new item gets a new,
    never-before-used number appended to that item kind's counter. Nothing
    already shipped ever gets renumbered by re-running this.

The answers/per_instance themselves are untouched -- they remain the one real
record of which question produced which value, still validated the normal way
by check_template.py. This is not a second requirements system: it is a frozen
build artifact of the one that already exists.

Usage:
  python lock_structure.py templates/<name>.json [more...]
  python lock_structure.py --all
"""

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSEMBLY_DIR = os.path.join(HERE, "..", "assembly-engine")
sys.path.insert(0, os.path.abspath(ASSEMBLY_DIR))
sys.path.insert(0, HERE)

import assemble as ae          # noqa: E402  (derive()/build_model() -- reused, not reimplemented)
import check_template          # noqa: E402  (the real, non-parallel validator -- must PASS first)
import graph_lib               # noqa: E402

GRAPH_PATH = os.path.join(HERE, "question_graph_v3.json")
TEMPLATE_DIR = os.path.join(HERE, "templates")


def _reuse_or_mint(prior_by_key, counters, kind, key):
    """Same natural key as a prior locked structure -> same id, forever.
    A key never seen before mints the next number for that kind and that
    template, continuing from the highest number this kind has ever used
    (never restarting the counter, even if earlier items were removed)."""
    if key in prior_by_key.get(kind, {}):
        return prior_by_key[kind][key]
    counters[kind] = counters.get(kind, 0) + 1
    return f"{kind}-{counters[kind]:03d}"


def _prior_index(old_structure):
    """natural-key -> bare id (without the template/ prefix), per numbered kind,
    read from a template's existing structure block (if any). Also returns the
    highest number already used per kind, so new ids never reuse an old number
    even if the item that held it was removed."""
    by_key, max_n = {}, {}

    def note(kind, key, full_id):
        bare = full_id.split("/", 1)[-1]
        by_key.setdefault(kind, {})[key] = bare
        n = int(bare.split("-")[-1])
        max_n[kind] = max(max_n.get(kind, 0), n)

    if not old_structure:
        return by_key, max_n
    for scr in old_structure.get("screens_inventory") or []:
        note("SCR", (scr["kind"], scr.get("record") or scr.get("form") or scr.get("report") or scr.get("integration")), scr["id"])
    for act in old_structure.get("actions_inventory") or []:
        key = (act["kind"], act.get("record"), act.get("workflow"), act.get("form"), act.get("integration"),
               (act.get("detail") or {}).get("name") if act["kind"] == "custom" else None,
               act.get("from"), act.get("to"), act.get("stage"))
        note("ACT", key, act["id"])
    for op in old_structure.get("recurring_ops") or []:
        note("OPS", op.get("source"), op["id"])
    for qa in old_structure.get("qa_generated_tests") or []:
        note("QA", (_strip_prefix(qa["action_id"]) if qa.get("action_id") else None,
                    qa.get("role"), qa.get("kind"),
                    _strip_prefix(qa["screen_id"]) if qa.get("screen_id") else None), qa["id"])
    for name, notif in (old_structure.get("notifications") or {}).items():
        if "id" in notif:
            note("NOTIF", name, notif["id"])
    for name, rep in (old_structure.get("reports") or {}).items():
        if "id" in rep:
            note("RPT", name, rep["id"])
    for wname, w in (old_structure.get("workflows") or {}).items():
        for st in w.get("stages") or []:
            if isinstance(st, dict):
                note("STG", (wname, st["name"]), st["id"])
        for tr in w.get("transitions") or []:
            if "id" in tr:
                note("TRN", (wname, tr["from"], tr["to"]), tr["id"])
    return by_key, max_n


def _strip_prefix(full_id):
    return full_id.split("/", 1)[-1] if "/" in full_id else full_id


def lock_one(graph, path):
    t = json.load(open(path, encoding="utf-8"))
    name = t["template"]

    errors = check_template.check(graph, t)
    if errors:
        raise SystemExit(f"{name}: refuses to lock a template that fails check_template.py:\n" +
                          "\n".join(f"  - {e}" for e in errors))
    if t["ask_customer"]:
        pass  # locking a structure does not need every customer question answered -- only assemble.py does

    derived = ae.derive(graph, t)
    bm = ae.build_model(t, derived)

    prior = t.get("structure")
    by_key, max_n = _prior_index(prior)
    counters = dict(max_n)

    def assign(kind, key):
        return _reuse_or_mint(by_key, counters, kind, key)

    # screens_inventory: reassign permanent ids by natural key (kind + the one
    # thing that screen is about), then re-derive navigation/landing from those.
    old_id_by_scr_old_id = {}
    new_screens = []
    for scr in bm["screens_inventory"]:
        key = (scr["kind"], scr.get("record") or scr.get("form") or scr.get("report") or scr.get("integration"))
        new_id = assign("SCR", key)
        old_id_by_scr_old_id[scr["id"]] = new_id
        new_screens.append({**scr, "id": new_id})
    bm["screens_inventory"] = new_screens
    bm["navigation"] = [s["id"] for s in new_screens]

    new_actions = []
    old_act_id_by_old_id = {}
    for act in bm["actions_inventory"]:
        key = (act["kind"], act.get("record"), act.get("workflow"), act.get("form"), act.get("integration"),
               (act.get("detail") or {}).get("name") if act["kind"] == "custom" else None,
               act.get("from"), act.get("to"), act.get("stage"))
        new_id = assign("ACT", key)
        new_act = {**act, "id": new_id}
        old_act_id_by_old_id[act["id"]] = new_act
        new_actions.append(new_act)
    bm["actions_inventory"] = new_actions

    new_ops = []
    for op in bm["recurring_ops"]:
        new_id = assign("OPS", op.get("source"))
        new_ops.append({**op, "id": new_id})
    bm["recurring_ops"] = new_ops

    # qa_generated_tests reference an action by "action_id" (and embed the full
    # action under "action") and a screen by "screen_id" -- rewrite both to the
    # freshly (re)assigned ids before renumbering the tests themselves.
    new_qa = []
    for qa in bm["qa_generated_tests"]:
        new_act = old_act_id_by_old_id.get(qa.get("action_id"))
        mapped_screen_id = old_id_by_scr_old_id.get(qa.get("screen_id"))
        key = (new_act["id"] if new_act else None, qa.get("role"), qa.get("kind"), mapped_screen_id)
        new_id = assign("QA", key)
        entry = {**qa, "id": new_id}
        if new_act is not None:
            entry["action_id"] = new_act["id"]
            entry["action"] = new_act
        if mapped_screen_id is not None:
            entry["screen_id"] = mapped_screen_id
        new_qa.append(entry)
    bm["qa_generated_tests"] = new_qa

    for name_, notif in bm["notifications"].items():
        notif["id"] = assign("NOTIF", name_)
    for name_, rep in bm["reports"].items():
        rep["id"] = assign("RPT", name_)
    for wname, w in bm["workflows"].items():
        stages = w.get("stages") or {}
        stage_names = stages.get("stages") if isinstance(stages, dict) else (stages or [])
        w["stages"] = [{"id": assign("STG", (wname, s)), "name": s} for s in (stage_names or [])]
        w["initial"] = (stages.get("initial") if isinstance(stages, dict) else None)
        w["terminal"] = (stages.get("terminal") if isinstance(stages, dict) else None)
        for tr in w.get("transitions") or []:
            tr["id"] = assign("TRN", (wname, tr["from"], tr["to"]))

    # prefix every id with the template name, so combining templates can never
    # collide two numbers or need a renumber.
    def prefixed(x):
        return f"{name}/{x}"

    for scr in bm["screens_inventory"]:
        scr["id"] = prefixed(scr["id"])
    bm["navigation"] = [prefixed(s) for s in bm["navigation"]]
    for act in bm["actions_inventory"]:
        act["id"] = prefixed(act["id"])
    for op in bm["recurring_ops"]:
        op["id"] = prefixed(op["id"])
    for qa in bm["qa_generated_tests"]:
        qa["id"] = prefixed(qa["id"])
        if qa.get("action_id"):
            qa["action_id"] = prefixed(qa["action_id"])
        if qa.get("screen_id"):
            qa["screen_id"] = prefixed(qa["screen_id"])
    for notif in bm["notifications"].values():
        notif["id"] = prefixed(notif["id"])
    for rep in bm["reports"].values():
        rep["id"] = prefixed(rep["id"])
    for w in bm["workflows"].values():
        for st in w["stages"]:
            st["id"] = prefixed(st["id"])
        for tr in w.get("transitions") or []:
            tr["id"] = prefixed(tr["id"])

    bm["locked_at_graph_version"] = graph["version"]
    t["structure"] = bm
    json.dump(t, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return bm


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    graph = graph_lib.load_graph(GRAPH_PATH)
    paths = sorted(glob.glob(os.path.join(TEMPLATE_DIR, "*.json"))) if argv[0] == "--all" else argv
    for p in paths:
        bm = lock_one(graph, p)
        print(f"locked {os.path.basename(p)}: {len(bm['screens_inventory'])} screens, "
              f"{len(bm['actions_inventory'])} actions, {len(bm['notifications'])} notifications, "
              f"{len(bm['reports'])} reports, {len(bm['workflows'])} workflows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
