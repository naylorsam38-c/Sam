#!/usr/bin/env python3
"""specgate — the rejection-rule linter for Spec Builder specs (rules R1–R12).

Mechanical. No model. Reads a spec YAML, emits failures as JSON lines
{rule, path, message}, plus a summary. Exit codes:

  0  pass (releasable to decompose, subject to human approval)
  3  ask-ready: the ONLY failures are R2 (unresolved [ASK] markers) —
     the spec is structurally complete and should go to the ASK step
  2  fail: any other rule fired — back to DRAFT with this list

Design decisions, per the review of the design doc:
  * R2 vs pipeline order: gate runs before ASK, so R2-only gets exit 3.
  * Absent categories: an empty list is rejected (R1); declared absence
    `{none: "<reason>"}` is accepted. Silence is never an answer.
  * Human-judgement criteria: `human: true` exempts a criterion from R3's
    runnable-verify requirement and R4's banned words; they are counted
    separately and never count toward automatic pass.
  * R10 is a heuristic (self-report tells in `verify`); its residue is
    explicitly left to the human approval gate.
  * Banned words match on word boundaries ("networks" does not trip "works").
"""

import json
import re
import sys

import yaml

BANNED = [
    "works", "correct", "properly", "good", "reliable", "robust",
    "user-friendly", "clean", "appropriate", "as expected", "seamless",
    "intuitive", "handles gracefully",
]
def _banned_pattern(w):
    # Inflection-tolerant for the phrase entries; exact word-boundary otherwise.
    special = {
        "handles gracefully": r"handle[sd]?\s+gracefully",
        "as expected": r"as\s+expected",
        "user-friendly": r"user[\s-]?friendly",
    }
    body = special.get(w, re.escape(w))
    return re.compile(r"(?<![\w-])" + body + r"(?![\w-])", re.I)


BANNED_RE = [_banned_pattern(w) for w in BANNED]

# R10 heuristic: tells that a verify step is the builder's own report.
SELF_REPORT_RE = re.compile(
    r"(?<![\w-])(builder|confirm(s|ed)?|manual(ly)?|attest(s|ed)?|self[- ]report|"
    r"ask\s+the\s+builder|says\s+it|i\s+verified)(?![\w-])", re.I)

ASK_RE = re.compile(r"\[ASK[^\]]*\]?")

HEADER_FIELDS = ["spec_id", "version", "title", "source", "status"]
INTENT_FIELDS = ["goal", "user", "success", "out_of_scope"]
SUBSTANCE_LISTS = ["surfaces", "data", "actions", "externals", "permissions"]
BOUNDS_FIELDS = ["constraints", "budget", "environment", "rollback"]
GATE_FIELDS = ["acceptance", "missing_info_policy", "evidence_required"]
STATUSES = {"draft", "gated", "approved", "superseded"}


def _is_none_decl(v):
    """Declared absence: {none: "<non-empty reason>"}."""
    return isinstance(v, dict) and set(v) == {"none"} and isinstance(v["none"], str) and v["none"].strip()


def _empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def _walk_strings(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def check(spec):
    """Run R1–R12. Returns (failures, summary). Each failure: dict(rule, path, message)."""
    f = []

    def fail(rule, path, message):
        f.append({"rule": rule, "path": path, "message": message})

    if not isinstance(spec, dict):
        fail("R1", "$", "spec is not a mapping")
        return f, {}

    # ---- R1: required fields present and non-empty --------------------------
    def require(section, fields):
        sec = spec.get(section)
        if not isinstance(sec, dict):
            fail("R1", section, f"section '{section}' absent or not a mapping")
            return {}
        for k in fields:
            if k not in sec or _empty(sec[k]):
                if _is_none_decl(sec.get(k)):
                    continue
                fail("R1", f"{section}.{k}", "required field absent or empty")
        return sec

    header = require("header", HEADER_FIELDS)
    intent = require("intent", INTENT_FIELDS)
    substance = spec.get("substance")
    if not isinstance(substance, dict):
        fail("R1", "substance", "section 'substance' absent or not a mapping")
        substance = {}
    else:
        for k in SUBSTANCE_LISTS:
            v = substance.get(k)
            if _is_none_decl(v):
                continue
            if not isinstance(v, list) or len(v) == 0:
                fail("R1", f"substance.{k}",
                     "absent or empty — list entries or declared absence {none: reason} required")
    bounds = require("bounds", BOUNDS_FIELDS)
    gate = require("gate", GATE_FIELDS)

    status = header.get("status")
    if status is not None and status not in STATUSES:
        fail("R1", "header.status", f"status '{status}' not one of {sorted(STATUSES)}")

    # ---- R2: unresolved [ASK] markers anywhere ------------------------------
    for path, s in _walk_strings(spec):
        if ASK_RE.search(s):
            fail("R2", path, f"unresolved [ASK]: {s.strip()[:120]}")

    # ---- acceptance criteria: R3, R4, R10 -----------------------------------
    acceptance = gate.get("acceptance") if isinstance(gate, dict) else None
    machine, human = [], []
    if not isinstance(acceptance, list) or len(acceptance) == 0:
        fail("R3", "gate.acceptance", "acceptance[] is empty")
    else:
        for i, ac in enumerate(acceptance):
            p = f"gate.acceptance[{i}]"
            if not isinstance(ac, dict):
                fail("R3", p, "criterion is not a mapping")
                continue
            is_human = ac.get("human") is True
            (human if is_human else machine).append(ac)
            if _empty(ac.get("id")) or _empty(ac.get("check")):
                fail("R3", p, "criterion missing id or check")
            if _empty(ac.get("evidence")):
                fail("R3", p, "criterion missing evidence")
            if not is_human:
                verify = ac.get("verify")
                if _empty(verify):
                    fail("R3", p, "machine criterion has no runnable verify")
                else:
                    if SELF_REPORT_RE.search(str(verify)):
                        fail("R10", f"{p}.verify",
                             "verify depends on the builder's own report: "
                             f"'{str(verify)[:100]}'")
                check_s = str(ac.get("check", ""))
                for w, rx in zip(BANNED, BANNED_RE):
                    if rx.search(check_s):
                        fail("R4", f"{p}.check", f"banned word '{w}' in check")

    # ---- R5: every control names an endpoint or is display_only -------------
    surfaces = substance.get("surfaces")
    if isinstance(surfaces, list):
        for i, s in enumerate(surfaces):
            if not isinstance(s, dict):
                continue
            for j, c in enumerate(s.get("controls") or []):
                p = f"substance.surfaces[{i}].controls[{j}]"
                if not isinstance(c, dict):
                    fail("R5", p, "control is not a mapping")
                    continue
                display_only = c.get("type") == "display_only"
                if display_only and _empty(c.get("source")):
                    fail("R5", p, "display_only control names no data source")
                if not display_only and _empty(c.get("endpoint")):
                    fail("R5", p,
                         f"control '{c.get('label', '?')}' has neither an endpoint "
                         "nor type: display_only — there is no third option")

    # ---- R6: externals name a credential custodian --------------------------
    externals = substance.get("externals")
    if isinstance(externals, list):
        for i, e in enumerate(externals):
            p = f"substance.externals[{i}]"
            if not isinstance(e, dict):
                fail("R6", p, "external is not a mapping")
                continue
            for k in ("credential", "custodian", "paste_location"):
                if _empty(e.get(k)):
                    fail("R6", f"{p}.{k}",
                         "external service must name credential, custodian, and where it is pasted")

    # ---- R7: missing_info_policy present ------------------------------------
    if isinstance(gate, dict) and _empty(gate.get("missing_info_policy")):
        pass  # already an R1; R7 restated for clarity of report
    if isinstance(gate, dict) and "missing_info_policy" in gate and _empty(gate.get("missing_info_policy")):
        fail("R7", "gate.missing_info_policy", "missing_info_policy is empty")
    if isinstance(gate, dict) and "missing_info_policy" not in gate:
        fail("R7", "gate.missing_info_policy", "missing_info_policy is absent")

    # ---- R8: at most seven constraints --------------------------------------
    constraints = bounds.get("constraints") if isinstance(bounds, dict) else None
    if isinstance(constraints, list) and len(constraints) > 7:
        fail("R8", "bounds.constraints",
             f"{len(constraints)} constraints — more than seven means more than one spec; split it")

    # ---- R9: out_of_scope non-empty -----------------------------------------
    oos = intent.get("out_of_scope") if isinstance(intent, dict) else None
    if oos is not None and (not isinstance(oos, list) or len(oos) == 0):
        fail("R9", "intent.out_of_scope", "an empty scope boundary is never true")

    # ---- R11: side-effecting actions carry reversible + rollback ------------
    actions = substance.get("actions")
    if isinstance(actions, list):
        for i, a in enumerate(actions):
            p = f"substance.actions[{i}]"
            if not isinstance(a, dict):
                continue
            if "reversible" not in a:
                fail("R11", p, f"action '{a.get('name', '?')}' has no reversible flag")
            elif a["reversible"] is False and _empty(a.get("rollback")):
                fail("R11", f"{p}.rollback",
                     f"irreversible action '{a.get('name', '?')}' names no rollback")
            if "needs_approval" not in a:
                fail("R11", p, f"action '{a.get('name', '?')}' does not state whether it needs approval")

    # ---- R12: every data item names a storage location ----------------------
    data = substance.get("data")
    if isinstance(data, list):
        for i, d in enumerate(data):
            if isinstance(d, dict) and _empty(d.get("location")):
                fail("R12", f"substance.data[{i}]",
                     f"data item '{d.get('name', '?')}' has no named storage location")

    summary = {
        "criteria_machine": len(machine),
        "criteria_human": len(human),
        "note": "human criteria never count toward automatic pass",
    }
    return f, summary


def main(argv):
    if len(argv) != 2:
        print("usage: specgate.py <spec.yaml>", file=sys.stderr)
        return 2
    with open(argv[1], "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    failures, summary = check(spec)
    for x in failures:
        print(json.dumps(x))
    rules = {x["rule"] for x in failures}
    print(json.dumps({"summary": summary, "failures": len(failures),
                      "rules_fired": sorted(rules)}))
    if not failures:
        return 0
    if rules == {"R2"}:
        return 3  # ask-ready: structurally complete, questions outstanding
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
