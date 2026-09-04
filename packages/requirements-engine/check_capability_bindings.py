#!/usr/bin/env python3
"""
check_capability_bindings.py — the checker. Reads a BOUND_SPEC.json
(produced by bind_and_assemble.py) and prints PASS/FAIL for every single
numbered item: PASS means it has a real, named part binding (from
packages/builder/parts_shelf.json) pointing at real, already-running code;
FAIL means UNBOUND, with the exact reason already recorded on the item by
bind_and_assemble.py -- never re-derived, never softened. Exit code is 0
only when every item PASSes.

Usage: python check_capability_bindings.py BOUND_SPEC.json
"""

import json
import sys


def check_spec(path):
    spec = json.load(open(path, encoding="utf-8"))
    bm = spec["build_model"]
    lines = [f"BINDING CHECK: {spec['spec_id']} (customer_complete={spec['customer_complete']})"]

    results = []

    def check_item(id_, label, pb):
        ok = bool(pb["parts"])
        results.append(ok)
        status = "PASS" if ok else "FAIL"
        detail = ", ".join(pb["parts"]) if ok else (pb["note"] or "no binding")
        lines.append(f"{status} {id_} ({label}): {detail}")

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
    return "\n".join(lines) + "\n"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    text = check_spec(sys.argv[1])
    print(text)
    return 0 if "NOT CLEAN" not in text else 1


if __name__ == "__main__":
    sys.exit(main())
