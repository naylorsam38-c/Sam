#!/usr/bin/env python3
"""
check_capability_bindings.py — the checker. Reads a BOUND_SPEC.json
(produced by bind_and_assemble.py) and prints PASS/FAIL for every single
numbered item: PASS means it has a real, named part binding (from
packages/builder/parts_shelf.json) pointing at real, already-running code;
FAIL means UNBOUND, with the exact reason already recorded on the item by
bind_and_assemble.py -- never re-derived, never softened. Exit code is 0
only when every item PASSes.

Second section, QUALIFICATION: for every part the spec pins, whether the
shelf still holds the exact bytes that were pinned (else DRIFT) and whether
the part's lifecycle status meets the bar a deployable build requires
(shelf.py REQUIRED_STATUS_FOR_DEPLOYABLE). A binding can be CLEAN while
qualification is not: that means every item has real code behind it, but
not every part has yet been driven in a real browser. The two are reported
separately so neither can hide the other.

Usage: python check_capability_bindings.py BOUND_SPEC.json [--require-qualified]
  --require-qualified   also exit non-zero unless every pinned part is at the
                        required status with no drift (the bar for a build that
                        is going to be called done)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "builder")))
import shelf as shelf_lib  # noqa: E402


def check_spec(path, require_qualified=False):
    spec = json.load(open(path, encoding="utf-8"))
    bm = spec["build_model"]
    lines = [f"BINDING CHECK: {spec['spec_id']} (customer_complete={spec['customer_complete']})"]

    results = []
    pinned = {}  # part_id -> pin, as recorded in the spec

    def check_item(id_, label, pb):
        ok = bool(pb["parts"])
        results.append(ok)
        status = "PASS" if ok else "FAIL"
        detail = ", ".join(pb["parts"]) if ok else (pb["note"] or "no binding")
        lines.append(f"{status} {id_} ({label}): {detail}")
        for p in pb.get("pins", []):
            pinned.setdefault(p["part_id"], p)

    for scr in bm["screens_inventory"]:
        check_item(scr["id"], f"screen/{scr['kind']}", scr["part_bindings"])
    for act in bm["actions_inventory"]:
        check_item(act["id"], f"action/{act['kind']}", act["part_bindings"])
    for name, notif in bm["notifications"].items():
        check_item(f"NTF:{name}", "notification", notif["part_bindings"])
    for name, rep in bm["reports"].items():
        check_item(f"RPT:{name}", "report", rep["part_bindings"])
    for op in bm["recurring_ops"]:
        check_item(op["id"], "recurring_op", op["part_bindings"])

    total, passed = len(results), sum(results)
    failed = total - passed
    lines.append("---")
    lines.append(f"{passed}/{total} PASS, {failed} FAIL")
    lines.append("CLEAN" if failed == 0 else f"NOT CLEAN -- {failed} item(s) unbound")

    # ---- qualification: are the pinned bytes still the shelf's bytes, and are they qualified?
    lines.append("")
    lines.append(f"QUALIFICATION CHECK (required status for a deployable build: {shelf_lib.REQUIRED_STATUS_FOR_DEPLOYABLE})")
    shelf = shelf_lib.load_shelf()
    by_id = {p["part_id"]: p for p in shelf["parts"]}
    q_ok = 0
    q_problems = 0
    if not pinned:
        lines.append("NO PINS -- this spec was bound before pins existed; rebind it")
        q_problems += 1
    for part_id in sorted(pinned):
        pin = pinned[part_id]
        part = by_id.get(part_id)
        if part is None:
            lines.append(f"MISSING {part_id}@{pin['version']}: no longer on the shelf")
            q_problems += 1
            continue
        current = shelf_lib.source_revision(part)
        drift = current != pin["revision"] or part["version"] != pin["version"]
        qualified = shelf_lib.meets(part)
        if drift:
            lines.append(f"DRIFT {part_id}: pinned {pin['version']}@{pin['revision']}, shelf is now {part['version']}@{current}")
            q_problems += 1
        elif not qualified:
            lines.append(f"UNQUALIFIED {part_id}@{pin['version']}: status {part['status']}")
            q_problems += 1
        else:
            lines.append(f"QUALIFIED {part_id}@{pin['version']} ({part['status']}) at {current}")
            q_ok += 1
    lines.append("---")
    lines.append(f"{q_ok}/{len(pinned)} parts qualified at their pinned revision, {q_problems} problem(s)")
    lines.append("QUALIFICATION CLEAN" if q_problems == 0 else f"QUALIFICATION NOT CLEAN -- {q_problems} part(s) unqualified, drifted or missing")
    return "\n".join(lines) + "\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    require_qualified = "--require-qualified" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 2
    text = check_spec(args[0], require_qualified)
    print(text)
    bad = "NOT CLEAN --" in text.split("QUALIFICATION CHECK")[0]
    if require_qualified and "QUALIFICATION NOT CLEAN" in text:
        bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
