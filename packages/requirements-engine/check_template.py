#!/usr/bin/env python3
"""
check_template.py — mechanical proof that a template fits question_graph_v3.json

A template PASSES only if: every answer keys to a real question; every closed answer is a legal
option; every role, record, field and stage referenced actually exists in the template; and every
question that will fire for this template is either pre-answered or explicitly left to the customer.
No model in the loop.

Usage:
  python check_template.py templates/<name>.json [more...]     validate; exit 0 = all PASS
  python check_template.py --all                                validate every templates/*.json
  python check_template.py --selftest                           break a passing template six ways; each must be caught
"""

# ============================================================================
# RULES / CONFIG — edit these, not the logic below.
# ============================================================================
GRAPH = "question_graph_v3.json"   # graph to validate against. Point at a newer graph to re-prove all templates after a change.
TEMPLATE_DIR = "templates"         # where --all looks for templates.
ALLOW_SUPER_IN_GRANTS = True       # True: naming the super role in a grant is legal (it means 'only them, besides nobody').
                                   # False: flag it as redundant, since the super role can do everything anyway.
DATE_TYPES = {"date", "date_time"} # field types a relative-to-date notification may anchor on.
KIND_TO_INVENTORY = {"record": "records", "role": "roles", "form": "forms", "file_type": "file_types",
                     "workflow": "workflows", "integration": "integrations", "notification": "notifications",
                     "report": "reports", "deviation": None, "ambiguous_metric": None}
# ============================================================================

import copy, glob, json, os, sys

here = os.path.dirname(os.path.abspath(__file__))
UNKNOWN = "UNKNOWN"


def load_graph():
    g = json.load(open(os.path.join(here, GRAPH), encoding="utf-8"))
    g["_q"] = {q["id"]: q for q in g["questions"]}
    g["_parts"] = {p["code"]: p for p in g["parts"]}
    return g


def check(g, t):
    E = []
    Q = g["_q"]
    inv = t["inventory"]
    roles = list(inv["roles"])
    records = list(inv["records"])
    super_role = t.get("super_role")
    legal_roles = set(roles) | {g["config"]["public_role_token"], g["config"]["super_role_token"]}
    field_types = set(g["config"]["field_types"])
    terms = [w.lower() for w in g["config"]["ambiguous_metric_terms"]]
    answers = t["answers"]
    per = t["per_instance"]
    ask = set(t["ask_customer"])

    def pk(key):
        """split 'QID:Instance[:Metric]' -> (qid, instance, metric)"""
        bits = key.split(":")
        return bits[0], bits[1] if len(bits) > 1 else None, bits[2] if len(bits) > 2 else None

    # -- 1. every answer keys to a real question; instances exist -------------
    for qid in answers:
        if qid not in Q:
            E.append(f"answers: unknown question {qid}")
    for key in per:
        qid, inst, metric = pk(key)
        if qid not in Q:
            E.append(f"per_instance: unknown question {qid} in '{key}'")
            continue
        kind = Q[qid]["per"]
        if kind is None:
            E.append(f"per_instance: {qid} is not a per-instance question ('{key}')")
            continue
        if kind == "ambiguous_metric":
            if inst not in inv["reports"]:
                E.append(f"{key}: report '{inst}' not in inventory")
            elif metric is None or metric not in (per.get(f"RP.04:{inst}") or []):
                E.append(f"{key}: metric not listed in RP.04:{inst}")
        else:
            pool = inv.get(KIND_TO_INVENTORY[kind]) or []
            if inst not in pool:
                E.append(f"{key}: {kind} '{inst}' not in inventory {pool}")
    for qid in t["ask_customer"]:
        if pk(qid)[0] not in Q:
            E.append(f"ask_customer: unknown question {qid}")

    # -- helpers --------------------------------------------------------------
    def get(qid, inst=None):
        if inst is not None and Q[qid]["per"]:
            return per.get(f"{qid}:{inst}")
        return answers.get(qid)

    def role_ok(r):
        if r in legal_roles:
            return True
        if r == super_role:
            return ALLOW_SUPER_IN_GRANTS
        return False

    def check_roles(where, lst):
        for r in lst or []:
            if not role_ok(r):
                E.append(f"{where}: unknown role '{r}'")

    def rec_fields(rec):
        return {f["name"]: f for f in (per.get(f"R.02:{rec}") or [])}

    # -- 2. closed answers are legal options ----------------------------------
    def validate_value(qid, key, v):
        q = Q[qid]
        opts = [o.split(" — ")[0] for o in (q.get("options") or [])]
        real_opts = [o for o in opts if not o.startswith("<")]
        if q["type"] in ("choice", "yesno") and real_opts and opts == real_opts:
            allowed = real_opts + ([q["done"].get("or_value")] if q["done"].get("or_value") else [])
            if v not in allowed:
                E.append(f"{key}: '{v}' not in {allowed}")
        if q["type"] == "multi":
            if not isinstance(v, list) or not v:
                E.append(f"{key}: multi answer must be a non-empty list")
            else:
                for x in v:
                    if real_opts and x not in real_opts:
                        E.append(f"{key}: '{x}' not in {real_opts}")
        if q["type"] == "roles":
            if v == "nobody" or v == []:
                return
            check_roles(key, v if isinstance(v, list) else [v])
        if q["type"] == "roles_scoped":
            if v == "nobody" and q["done"].get("or_value") == "nobody":
                return
            if not isinstance(v, list) or not v:
                E.append(f"{key}: scoped-role answer must be a non-empty list (or 'nobody' where allowed)")
                return
            scopes = q["done"].get("scopes", [])
            for e_ in v:
                if not role_ok(e_.get("role")):
                    E.append(f"{key}: unknown role '{e_.get('role')}'")
                if e_.get("scope") not in scopes:
                    E.append(f"{key}: scope '{e_.get('scope')}' not in {scopes}")
                if e_.get("scope") == "linked" and not e_.get("via"):
                    E.append(f"{key}: 'linked' scope must say via what")

    for qid, v in answers.items():
        if qid in Q:
            validate_value(qid, qid, v)
    for key, v in per.items():
        qid = pk(key)[0]
        if qid in Q and Q[qid]["per"] != "ambiguous_metric":
            validate_value(qid, key, v)

    # -- 3. cross-references resolve ------------------------------------------
    for rec in records:
        flds = rec_fields(rec)
        for name, fd in flds.items():
            if fd.get("type") not in field_types:
                E.append(f"R.02:{rec}: field '{name}' has unknown type '{fd.get('type')}'")
            if fd.get("type") in ("one_choice", "multi_choice") and not fd.get("options"):
                E.append(f"R.02:{rec}: choice field '{name}' has no options")
            if fd.get("type") == "link":
                if fd.get("target_record") not in records:
                    E.append(f"R.02:{rec}: link field '{name}' targets unknown record '{fd.get('target_record')}'")
            if fd.get("type") == "other" and not fd.get("custom_rule"):
                E.append(f"R.02:{rec}: 'other' field '{name}' has no custom_rule")
            for k in ("required", "unique"):
                if fd.get(k) not in ("yes", "no"):
                    E.append(f"R.02:{rec}: field '{name}' {k} must be yes/no")
        title = per.get(f"R.03:{rec}")
        if title is not None and title not in flds:
            E.append(f"R.03:{rec}: title field '{title}' is not a field of {rec}")
        own = per.get(f"R.09:{rec}")
        if own and own.get("basis") == "field" and own.get("field") not in flds:
            E.append(f"R.09:{rec}: ownership field '{own.get('field')}' is not a field of {rec}")
        for r_ in per.get(f"R.11:{rec}") or []:
            if r_.get("target") not in records:
                E.append(f"R.11:{rec}: relation targets unknown record '{r_.get('target')}'")
        life = per.get(f"R.10:{rec}")
        if life and life.get("has") == "yes":
            stages = life.get("stages") or []
            if not any((per.get(f"FL.02:{w}") or {}).get("stages") == stages for w in inv["workflows"]):
                E.append(f"R.10:{rec}: lifecycle {stages} has no workflow in the inventory with exactly those stages")

    for w in inv["workflows"]:
        st = per.get(f"FL.02:{w}") or {}
        stages = st.get("stages") or []
        if st:
            if st.get("initial") not in stages:
                E.append(f"FL.02:{w}: initial stage not in stages")
            for x in st.get("terminal") or []:
                if x not in stages:
                    E.append(f"FL.02:{w}: terminal stage '{x}' not in stages")
        for m in per.get(f"FL.03:{w}") or []:
            for end in ("from", "to"):
                if m.get(end) not in stages:
                    E.append(f"FL.03:{w}: transition {end} '{m.get(end)}' not a declared stage")
            if m.get("mover") == "roles":
                check_roles(f"FL.03:{w}", m.get("roles"))
            elif m.get("mover") == "automatic":
                if not m.get("event"):
                    E.append(f"FL.03:{w}: automatic transition with no event")
            else:
                E.append(f"FL.03:{w}: mover must be roles|automatic")
        for a in per.get(f"FL.05:{w}") or []:
            if a.get("stage") not in stages:
                E.append(f"FL.05:{w}: approval stage '{a.get('stage')}' not declared")
            check_roles(f"FL.05:{w}", a.get("approvers"))
        rej = per.get(f"FL.06:{w}")
        if rej and rej.get("back_to") not in stages:
            E.append(f"FL.06:{w}: back_to '{rej.get('back_to')}' not a declared stage")
        can = per.get(f"FL.07:{w}") or {}
        if can.get("allowed") == "yes":
            check_roles(f"FL.07:{w}", can.get("by"))
            for s in can.get("from_stages") or []:
                if s not in stages:
                    E.append(f"FL.07:{w}: cancellable from undeclared stage '{s}'")
        ro = per.get(f"FL.09:{w}")
        if ro is not None and ro != "never" and ro not in stages:
            E.append(f"FL.09:{w}: read-only-from '{ro}' not a declared stage")
        for to_ in per.get(f"FL.10:{w}") or []:
            if to_.get("stage") not in stages:
                E.append(f"FL.10:{w}: timeout on undeclared stage '{to_.get('stage')}'")

    for n in inv["notifications"]:
        trig = per.get(f"N.01:{n}") or {}
        if trig.get("kind") == "relative_to_date":
            rec = trig.get("record")
            if rec not in records:
                E.append(f"N.01:{n}: anchors on unknown record '{rec}'")
            elif (rec_fields(rec).get(trig.get("date_field"), {}).get("type")) not in DATE_TYPES:
                E.append(f"N.01:{n}: '{trig.get('date_field')}' is not a date field of {rec}")
        for r_ in per.get(f"N.02:{n}") or []:
            if r_.get("kind") == "roles":
                check_roles(f"N.02:{n}", r_.get("roles"))
            if r_.get("kind") == "field":
                rec = r_.get("record")
                if rec not in records or r_.get("field") not in rec_fields(rec):
                    E.append(f"N.02:{n}: recipient field '{r_.get('field')}' not found on record '{rec}'")

    for ft in inv["file_types"]:
        p = per.get(f"FI.01:{ft}") or {}
        if p.get("parent") not in records:
            E.append(f"FI.01:{ft}: parent record '{p.get('parent')}' not in inventory")
    for fm in inv["forms"]:
        p = per.get(f"F.02:{fm}") or {}
        if p.get("target") not in records:
            E.append(f"F.02:{fm}: target record '{p.get('target')}' not in inventory")
    for rp in inv["reports"]:
        check_roles(f"RP.02:{rp}", per.get(f"RP.02:{rp}"))
    c06 = answers.get("C.06")
    if c06 is not None and set(c06.keys()) != set(roles):
        E.append(f"C.06: landing screens must cover exactly the roles {sorted(roles)}, got {sorted(c06)}")

    # -- 4. gate evaluation (tri-state) ---------------------------------------
    def ans_for_gate(qid, inst):
        if qid in ask or any(a.split(":")[0] == qid and a.endswith(":*") for a in ask):
            return UNKNOWN
        return get(qid, inst)

    def eval_gate(gate, inst=None):
        if not gate:
            return True
        if "all" in gate:
            vals = [eval_gate(x, inst) for x in gate["all"]]
            return False if False in vals else (UNKNOWN if UNKNOWN in vals else True)
        if "any" in gate:
            vals = [eval_gate(x, inst) for x in gate["any"]]
            return True if True in vals else (UNKNOWN if UNKNOWN in vals else False)
        v = ans_for_gate(gate["q"], inst)
        if v is UNKNOWN:
            return UNKNOWN
        op, val = gate["op"], gate.get("value")
        if v is None:
            return UNKNOWN   # unanswered gate source is itself a coverage error reported elsewhere
        if op == "eq":
            return v == val
        if op == "includes":
            return isinstance(v, list) and val in v
        if op == "includes_any":
            return isinstance(v, list) and any(x in v for x in val)
        if op == "min_items":
            return isinstance(v, list) and len(v) >= val
        if op == "scope_includes":
            return isinstance(v, list) and any(e.get("scope") == val for e in v)
        return UNKNOWN

    # -- 5. coverage: everything that fires is answered or asked --------------
    def covered(qid, inst=None, metric=None):
        key = qid if inst is None else (f"{qid}:{inst}" if metric is None else f"{qid}:{inst}:{metric}")
        if (key in answers) or (key in per):
            return True
        if qid in ask or f"{qid}:*" in ask or (inst and f"{qid}:{inst}" in ask):
            return True
        return False

    for q in g["questions"]:
        qid = q["id"]
        part = g["_parts"][q["part"]]
        if qid == "A.15":
            continue  # answered by the inventory itself
        pg = eval_gate(part.get("gate"))
        if pg is False:
            continue
        kind = q["per"]
        if kind is None:
            fire = eval_gate(q.get("gate"))
            if pg is True and fire is True and not covered(qid):
                E.append(f"coverage: {qid} fires for this template but is neither answered nor in ask_customer")
        elif kind == "ambiguous_metric":
            for rp in inv["reports"]:
                for m in per.get(f"RP.04:{rp}") or []:
                    if any(w in m.lower() for w in terms) and not covered(qid, rp, m):
                        E.append(f"coverage: RP.05 needed for ambiguous metric '{m}' in report '{rp}'")
        elif kind == "deviation":
            continue  # deviations are customer-driven by definition (A.14 is ask_customer)
        else:
            pool = inv.get(KIND_TO_INVENTORY[kind]) or []
            for inst in pool:
                if kind == "role" and inst == super_role:
                    continue  # the super role skips every authority question
                fire = eval_gate(q.get("gate"), inst)
                if pg is True and fire is True and not covered(qid, inst):
                    E.append(f"coverage: {qid}:{inst} fires but is neither answered nor in ask_customer")
    return E


def selftest():
    g = load_graph()
    base_t = json.load(open(os.path.join(here, TEMPLATE_DIR, "accounting-ledger.json"), encoding="utf-8"))
    base = set(check(g, base_t))
    results, allok = [], not base

    def case(name, mutate):
        t = copy.deepcopy(base_t)
        mutate(t)
        new = [e for e in check(g, t) if e not in base]
        results.append((name, bool(new), new[:1]))

    case("illegal option value", lambda t: t["per_instance"].__setitem__("R.12:Invoice", "explode"))
    case("unknown role in a grant", lambda t: t["per_instance"].__setitem__("RP.02:Profit and loss", ["Wizard"]))
    case("transition to an undeclared stage", lambda t: t["per_instance"]["FL.03:Bill lifecycle"].append(
        {"from": "Draft", "to": "Shredded", "mover": "roles", "roles": ["Accountant"]}))
    case("title field that does not exist", lambda t: t["per_instance"].__setitem__("R.03:Contact", "Nickname"))
    case("coverage hole (answer deleted)", lambda t: t["per_instance"].pop("N.03:Invoice sent"))
    case("ambiguous metric without a definition", lambda t: t["per_instance"].pop("RP.05:Profit and loss:revenue"))
    for name, caught, sample in results:
        print(f"  [{'caught' if caught else 'MISSED'}] {name}" + (f" -> {sample[0]}" if sample else ""))
        allok = allok and caught
    print("SELFTEST", "PASS" if allok else "FAIL")
    return 0 if allok else 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == "--selftest":
        return selftest()
    g = load_graph()
    paths = sorted(glob.glob(os.path.join(here, TEMPLATE_DIR, "*.json"))) if sys.argv[1] == "--all" else sys.argv[1:]
    bad = 0
    for p in paths:
        t = json.load(open(p, encoding="utf-8"))
        errs = check(g, t)
        n_ans = len(t["answers"]) + len(t["per_instance"])
        print(f"{t['template']:22s} {n_ans:4d} answers  {'PASS' if not errs else f'FAIL ({len(errs)})'}")
        for e in errs:
            print("    ", e)
        bad += bool(errs)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
