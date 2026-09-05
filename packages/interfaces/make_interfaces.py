#!/usr/bin/env python3
"""
make_interfaces.py — three working interfaces per family, from the family's
own assembled SPEC.json. 5 families x 3 designs = 15 single-file HTML apps.

Each interface is a real client of the generated app: every control on it
calls the real generated route (create/edit/delete, person-moved stage
transitions, approvals, declared custom actions, public forms, reports, the
activity trail) and shows only what the current role is really allowed to
do -- the same rules the routes enforce. Opened as a file with no server, it
runs on an in-browser demo store that follows the same declared rules and
says so in a banner.

The three designs are different products, not three colour schemes:
  console  sidebar + data tables + slide-over detail (desk work)
  board    kanban columns per stage + card grids + modal detail (visual flow)
  pocket   mobile-first: bottom tabs, card lists, full-screen pages, action sheet

Usage:
  python make_interfaces.py            # all families (needs build_families.py to have run)
  python make_interfaces.py crm-pipeline
Writes:
  build/<family>/app/static/ui-<design>.html   served by the built app at /ui-<design>.html
  build/<family>/app/static/index.html         chooser between the three
  out/<family>/<design>.html                   the same files, gathered for delivery
"""

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
BUILD = os.path.join(HERE, "build")
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(HERE, "..", "builder"))
import builder as bl  # noqa: E402  the same slug/table rules the routes use

FAMILIES = ["pm-teamwork", "crm-pipeline", "booking-frontdesk", "erp-backbone", "accounting-ledger"]
DESIGNS = ["console", "board", "pocket"]
# one accent per family (C.02 tone answers are words, not colours; these are the
# reference instance's palette and change with it)
ACCENTS = {
    "pm-teamwork": ("#2563eb", "#7c3aed"),
    "crm-pipeline": ("#ea580c", "#db2777"),
    "booking-frontdesk": ("#0d9488", "#2563eb"),
    "erp-backbone": ("#4f46e5", "#0891b2"),
    "accounting-ledger": ("#15803d", "#0d9488"),
}


def _roles(list_or_str):
    """Every access answer shape the graph produces, flattened to role names:
    a list of role names, a list of {role, scope}, or 'nobody'."""
    if not list_or_str or list_or_str == "nobody":
        return []
    return [x["role"] if isinstance(x, dict) else x for x in list_or_str]


def model_from_spec(spec):
    bm = spec["build_model"]
    roles = list(bm["roles"])
    records = {}
    for name, r in bm["records"].items():
        lifecycle = r.get("lifecycle") or {}
        wf_name = None
        if isinstance(lifecycle, dict) and lifecycle.get("has") == "yes":
            wanted = list(lifecycle.get("stages") or [])
            for wn, wf in bm["workflows"].items():
                if bl._stage_names(wf) == wanted:
                    wf_name = wn
                    break
        custom = [dict(a["detail"]) for a in bm["actions_inventory"] if a["kind"] == "custom" and a.get("record") == name]
        records[name] = {
            "table": bl.table_name(name),
            "title_field": r.get("title_field"),
            "fields": [dict(f, slug=bl.slug(f["name"])) for f in r["fields"].values()],
            "access": {"view": _roles(r["access"].get("view")), "create": _roles(r["access"].get("create")),
                       "edit": _roles(r["access"].get("edit")), "delete": _roles(r["access"].get("delete"))},
            "has_stage": bool(wf_name),
            "workflow": wf_name,
            "custom_actions": custom,
            "on_create": r.get("on_create") or [],
        }
    workflows = {}
    for wn, wf in bm["workflows"].items():
        stages = bl._stage_names(wf)
        raw = wf.get("stages")
        initial = wf.get("initial") or (raw.get("initial") if isinstance(raw, dict) else None) or (stages[0] if stages else None)
        terminal = wf.get("terminal") or (raw.get("terminal") if isinstance(raw, dict) else None) or []
        workflows[wn] = {
            "stages": stages, "initial": initial, "terminal": terminal,
            "transitions": [{k: t[k] for k in ("from", "to", "mover", "roles", "event") if k in t} for t in wf["transitions"]],
            "approvals": wf.get("approvals") or [], "on_reject": wf.get("on_reject") or None,
            "effects": wf.get("effects") or [],
        }
    forms = {}
    for scr in bm["screens_inventory"]:
        if scr["kind"] == "form":
            fname = scr["form"]
            rec = scr["record"]
            forms[fname] = {"record": rec, "slug": bl.slug(fname),
                            "fields": [bl.slug(n) for n in bm["forms"][fname] if n in bm["records"][rec]["fields"]]}
    reports = {}
    for name, rep in bm["reports"].items():
        reports[name] = {"slug": bl.slug(name), "question": rep.get("data_source") or "",
                         "metrics": [e["metric"] for e in rep.get("spec") or []], "specs": rep.get("spec") or []}
    return {
        "family": spec.get("source_template"),
        "spec_id": spec["spec_id"],
        "app_name": (bm.get("brand") or {}).get("app_name") or "App",
        "roles": roles,
        "role_admin": {r: bool(bm["roles"][r].get("is_admin")) for r in roles},
        "super_role": bm.get("super_role"),
        "records": records,
        "workflows": workflows,
        "forms": forms,
        "reports": reports,
        "landing_per_role": bm.get("landing_per_role") or {},
        "screens": [{k: s.get(k) for k in ("id", "kind", "record", "report", "form") if s.get(k)} for s in bm["screens_inventory"]],
    }


def read(name):
    return open(os.path.join(SRC, name), encoding="utf-8").read()


def page(model, design, family):
    acc, acc2 = ACCENTS[family]
    css = read(design + ".css").replace("ACCENT2", acc2).replace("ACCENT", acc)
    title = f"{model['app_name']} · {design}"
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">"
        f"<title>{title}</title>"
        f"<meta name=\"generator\" content=\"packages/interfaces/make_interfaces.py from {model['spec_id']}\">"
        f"<style>\n{css}\n</style></head><body>\n"
        f"<div id=\"app\" data-family=\"{family}\" data-design=\"{design}\"></div>\n"
        f"<script>window.MODEL = {json.dumps(model, separators=(',', ':'))};</script>\n"
        f"<script>\n{read('demo_store.js')}\n</script>\n"
        f"<script>\n{read('parts.js')}\n</script>\n"
        f"<script>\n{read(design + '.js')}\n</script>\n"
        f"<script>\n{read('runtime.js')}\n</script>\n"
        "</body></html>\n"
    )


def chooser(model, family):
    acc, acc2 = ACCENTS[family]
    cards = "".join(
        f'<a class="c" href="/ui-{d}.html"><b>{d.title()}</b><span>{desc}</span></a>'
        for d, desc in (("console", "Sidebar, tables, slide-over detail — desk work."),
                        ("board", "Stage columns, cards, modal detail — see the flow."),
                        ("pocket", "Phone-first: tabs, cards, full-screen pages.")))
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{model['app_name']}</title><style>body{{margin:0;font:16px/1.5 system-ui,sans-serif;background:#0f1218;color:#eef1f6;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}}"
        f".w{{max-width:760px;width:100%}}h1{{margin:0 0 4px;font-size:30px}}h1 i{{font-style:normal;color:{acc}}}p{{color:#8f98a8;margin:0 0 22px}}.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}}"
        f".c{{display:flex;flex-direction:column;gap:6px;background:#171b24;border:1px solid #2a3140;border-radius:16px;padding:20px;color:#eef1f6;text-decoration:none}}.c b{{font-size:20px;color:{acc}}}.c span{{color:#8f98a8;font-size:14px}}.c:hover{{border-color:{acc}}}</style></head>"
        f"<body><div class=\"w\"><h1><i>{model['app_name']}</i> — pick an interface</h1><p>{family} · three designs of the same app, on the same routes. Screens generated by the Builder are still at their SCR-nnn pages.</p><div class=\"g\">{cards}</div></div></body></html>\n"
    )


def make(family):
    spec_path = os.path.join(BUILD, family, "SPEC.json")
    if not os.path.exists(spec_path):
        raise SystemExit(f"{family}: no SPEC.json under build/ -- run build_families.py first")
    spec = json.load(open(spec_path, encoding="utf-8"))
    model = model_from_spec(spec)
    static = os.path.join(BUILD, family, "app", "static")
    out = os.path.join(OUT, family)
    os.makedirs(static, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    json.dump(model, open(os.path.join(out, "MODEL.json"), "w", encoding="utf-8"), indent=1)
    for design in DESIGNS:
        html = page(model, design, family)
        for path in (os.path.join(static, f"ui-{design}.html"), os.path.join(out, f"{design}.html")):
            open(path, "w", encoding="utf-8").write(html)
    open(os.path.join(static, "index.html"), "w", encoding="utf-8").write(chooser(model, family))
    return model


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    for family in (argv or FAMILIES):
        m = make(family)
        print(f"{family}: {len(m['records'])} records, {len(m['workflows'])} workflows, {len(m['reports'])} reports, "
              f"{len(m['forms'])} forms -> 3 interfaces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
