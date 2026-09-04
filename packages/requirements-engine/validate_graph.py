#!/usr/bin/env python3
"""
validate_graph.py — mechanical no-guessing check for question_graph_v3.json

Usage:
  python validate_graph.py question_graph_v3.json     validate a graph; exit 0 = PASS, exit 1 = FAIL (every violation printed)
  python validate_graph.py --selftest                  break a good graph seven different ways and prove each break is caught

No model in the loop. This replaces the handoff's proof_runner.py, whose PASS was regex keyword matching
(and which crashes on a second run: it calls shutil.rmtree without importing shutil).
"""

# ============================================================================
# RULES / CONFIG — edit these, not the logic below.
# ============================================================================
ID_PATTERN = r"^[A-Z0-9]+\.\d{2}$"      # required question-id shape. Change if you rename parts (e.g. allow lower case).
ALLOW_FORWARD_GATES = False             # True lets a question gate on a later question. Keep False: the script asks in order.
REQUIRE_OPS_COLLECTED = True            # every question tagged feeds:OPS must be an input of the recurring-ops derivation (OPS_DERIVATION).
OPS_DERIVATION = "D11"                  # id of the derivation that builds the recurring-ops list.
INVENTORY_KINDS = {"workflow", "notification", "integration", "deviation", "record", "form", "file_type", "report", "role", "screen"}
PLACEHOLDER_FOR_PER = {                 # which ${placeholder} a per-instance question may use.
    "role": "role", "record": "record", "form": "form", "file_type": "file_type", "workflow": "workflow",
    "integration": "integration", "notification": "notification", "report": "report",
    "ambiguous_metric": "metric", "deviation": "deviation",
}
SYMBOLIC_GATE_VALUES = {"AMBIGUOUS_METRIC_TERMS", "DEFAULTS"}   # gate values that name a config list instead of a literal.
# ============================================================================

import copy, json, re, sys

from graph_lib import field_sources


def validate(graph):
    errors = []
    E = errors.append
    qs = graph["questions"]
    order = graph["part_order"]
    parts = {p["code"]: p for p in graph["parts"]}
    qid = {}

    # parts
    for code in order:
        if code not in parts:
            E(f"part_order names undeclared part {code}")
    for code in parts:
        if code not in order:
            E(f"part {code} declared but not in part_order")

    # questions
    for q in qs:
        if not re.match(ID_PATTERN, q["id"]):
            E(f"{q['id']}: id does not match {ID_PATTERN}")
        if q["id"] in qid:
            E(f"{q['id']}: duplicate id")
        qid[q["id"]] = q
        if q["part"] not in parts:
            E(f"{q['id']}: unknown part {q['part']}")
        if not q.get("done") or "rule" not in q["done"]:
            E(f"{q['id']}: no done-rule")
        if q["type"] in ("choice", "multi") and not q.get("options"):
            E(f"{q['id']}: {q['type']} without options")
        if q.get("done", {}).get("rule") in ("one_of", "subset_min1"):
            opts = [o.split(" — ")[0] for o in (q.get("options") or [])]
            if q["done"].get("options") != opts:
                E(f"{q['id']}: done-rule options differ from prompt options")
        if not q.get("fills"):
            E(f"{q['id']}: fills no spec field")
        for ph in re.findall(r"\$\{(\w+)\}", q["prompt"]):
            want = PLACEHOLDER_FOR_PER.get(q.get("per") or "")
            if ph != want:
                E(f"{q['id']}: placeholder ${{{ph}}} but per={q.get('per')}")
        if q.get("creates") and q["creates"].get("kind") not in INVENTORY_KINDS:
            E(f"{q['id']}: creates unknown kind {q['creates'].get('kind')}")

    pos = {q["id"]: i for i, q in enumerate(qs)}
    rank = {code: i for i, code in enumerate(order)}

    def check_gate(owner_id, owner_part, gate, owner_pos):
        if not gate:
            return
        if "all" in gate or "any" in gate:
            for sub in gate.get("all", []) + gate.get("any", []):
                check_gate(owner_id, owner_part, sub, owner_pos)
            return
        target = gate["q"]
        if target not in qid:
            E(f"{owner_id}: gate references unknown question {target}")
            return
        t = qid[target]
        if not ALLOW_FORWARD_GATES:
            if rank[t["part"]] > rank[owner_part] or (owner_pos is not None and pos[target] >= owner_pos):
                E(f"{owner_id}: gate references later question {target}")
        v = gate.get("value")
        if gate["op"] in ("eq", "includes") and t.get("options") and isinstance(v, str) and v not in SYMBOLIC_GATE_VALUES:
            opts = [o.split(" — ")[0] for o in t["options"]]
            if v not in opts and not any(o.startswith("<") for o in opts):
                E(f"{owner_id}: gate value '{v}' not an option of {target} {opts}")
        if gate["op"] == "includes_any" and t.get("options"):
            opts = [o.split(" — ")[0] for o in t["options"]]
            for vv in v:
                if vv not in opts:
                    E(f"{owner_id}: gate value '{vv}' not an option of {target}")
        if gate["op"] == "eq" and t["type"] == "yesno" and v not in ("yes", "no"):
            E(f"{owner_id}: yes/no gate on {target} with value {v}")

    for q in qs:
        check_gate(q["id"], q["part"], q.get("gate"), pos[q["id"]])
    for code, p in parts.items():
        if p.get("gate"):
            # a part gate may reference any question in an earlier part
            first = next((i for i, q in enumerate(qs) if q["part"] == code), None)
            check_gate(f"part {code}", code, p["gate"], first)
    for d in graph["deploy_inputs"]:
        check_gate(d["id"], order[-1], d.get("gate"), None)

    # derivations
    dids = {d["id"] for d in graph["derivations"]}
    for d in graph["derivations"]:
        for inp in d["inputs"]:
            if inp != "*" and inp not in qid and inp not in dids:
                E(f"{d['id']}: input {inp} is not a question or derivation")
        if not d["outputs"]:
            E(f"{d['id']}: produces nothing")

    # recurring ops collection
    if REQUIRE_OPS_COLLECTED:
        ops = next((d for d in graph["derivations"] if d["id"] == OPS_DERIVATION), None)
        if not ops:
            E(f"no derivation {OPS_DERIVATION} to collect recurring ops")
        else:
            for q in qs:
                if "OPS" in (q.get("feeds") or []) and q["id"] not in ops["inputs"]:
                    E(f"{q['id']}: feeds OPS but is not an input of {OPS_DERIVATION}")

    # traceability: every spec field has exactly one source
    sources = field_sources(graph)
    master = graph["spec_fields"]
    for f in master:
        n = len(sources.get(f, []))
        if n == 0:
            E(f"spec field {f}: no source (builder would have to guess)")
        elif n > 1:
            E(f"spec field {f}: {n} sources {sources[f]} (two builders could follow different ones)")
    for f in sources:
        if f not in master:
            E(f"spec field {f}: claimed by {sources[f]} but not in master list")

    return errors


def selftest(graph):
    """Break the graph in known ways; every break must be caught. Returns list of (name, caught)."""
    results = []
    base = set(validate(graph))

    def case(name, mutate):
        g = copy.deepcopy(graph)
        mutate(g)
        new = [e for e in validate(g) if e not in base]     # only errors the mutation introduced count
        results.append((name, bool(new), new[:2]))

    def m_forward_gate(g):
        g["questions"][3]["gate"] = {"q": g["questions"][-1]["id"], "op": "eq", "value": "yes"}
    def m_unknown_gate(g):
        g["questions"][3]["gate"] = {"q": "ZZ.99", "op": "eq", "value": "yes"}
    def m_dup_source(g):
        g["system_defaults"][0]["fields"].append(g["questions"][4]["fills"][0])
    def m_orphan_field(g):
        g["spec_fields"].append("record.*.something_nobody_answers")
    def m_no_done(g):
        del g["questions"][5]["done"]
    def m_bad_gate_value(g):
        q = next(q for q in g["questions"] if q["id"] == "AU.05")
        q["gate"] = {"q": "AU.01", "op": "includes", "value": "telepathy"}
    def m_ops_uncollected(g):
        d = next(d for d in g["derivations"] if d["id"] == OPS_DERIVATION)
        d["inputs"].remove("R.14")
    def m_placeholder(g):
        g["questions"][1]["prompt"] += " ${record}"

    case("gate points at a later question", m_forward_gate)
    case("gate points at an unknown question", m_unknown_gate)
    case("spec field with two sources", m_dup_source)
    case("spec field with no source", m_orphan_field)
    case("question without done-rule", m_no_done)
    case("gate value not among target's options", m_bad_gate_value)
    case("duration answer not collected into recurring ops", m_ops_uncollected)
    case("instance placeholder in a fixed question", m_placeholder)
    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "--selftest":
        path = sys.argv[2] if len(sys.argv) > 2 else "question_graph_v3.json"
        graph = json.load(open(path, encoding="utf-8"))
        base = validate(graph)
        print(f"baseline graph v{graph['version']}: {'PASS' if not base else 'FAIL'}")
        for e in base:
            print("  ", e)
        allok = not base
        for name, caught, sample in selftest(graph):
            print(f"  [{'caught' if caught else 'MISSED'}] {name}" + (f" -> {sample[0]}" if sample else ""))
            allok = allok and caught
        print("SELFTEST", "PASS" if allok else "FAIL")
        return 0 if allok else 1
    graph = json.load(open(sys.argv[1], encoding="utf-8"))
    errs = validate(graph)
    qs = graph["questions"]
    print(f"graph v{graph['version']}: {len(qs)} questions ({sum(1 for q in qs if not q['per'])} fixed, {sum(1 for q in qs if q['per'])} per-instance), "
          f"{len(graph['system_defaults'])} defaults, {len(graph['derivations'])} derivations, {len(graph['deploy_inputs'])} deploy inputs, "
          f"{len(graph['spec_fields'])} spec fields")
    for e in errs:
        print("  FAIL", e)
    print("VERDICT", "PASS" if not errs else f"FAIL ({len(errs)} violations)")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
