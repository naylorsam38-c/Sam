#!/usr/bin/env python3
"""decompose — split an approved spec into work packets. Mechanical. No model.

A script cannot invent a split, so the split is AUTHORED in the spec
(`packets[]`, written at draft time by the model, approved by Sam) and this
script VALIDATES and MATERIALISES it:

  D1  spec status is not 'approved', or the gate does not pass clean
  D2  packets[] absent or empty
  D3  a packet is missing job / inputs / tools / acceptance / budget
  D4  a packet references another packet's output in its inputs
      (inputs must be inline — "self-contained or it isn't a packet")
  D5  a machine acceptance criterion is covered by zero packets, or by
      more than one (exactly-once coverage)
  D6  a packet's acceptance ids are not a subset of the spec's
  D7  depends_on names an unknown packet, or the graph has a cycle
  D8  numeric packet budgets exceed the spec budget

On success writes packets/<spec_id>/<packet_id>.yaml (attempt=1 and a
deterministic idempotency_key added) and plan.json with parallel waves
(topological levels: everything in a wave can run concurrently).
Exit codes: 0 ok, 2 fail.
"""

import hashlib
import json
import pathlib
import re
import sys

import yaml

import specgate

XREF_RE = re.compile(r"(see|from|output of|result of)\s+(packet|P\d+|[A-Z]+-\d+/P\d+)", re.I)
PACKET_FIELDS = ["packet_id", "job", "inputs", "tools", "acceptance", "budget"]


def decompose(spec, out_dir):
    errors = []

    def err(code, path, message):
        errors.append({"rule": code, "path": path, "message": message})

    gate_failures, _ = specgate.check(spec)
    if gate_failures:
        err("D1", "$", f"gate does not pass clean ({len(gate_failures)} failures)")
    if (spec.get("header") or {}).get("status") != "approved":
        err("D1", "header.status", "spec is not approved — decomposition is post-approval only")

    packets = spec.get("packets")
    if not isinstance(packets, list) or not packets:
        err("D2", "packets", "packets[] absent or empty — the split is authored in the spec")
        return errors, None

    ids = [p.get("packet_id") for p in packets if isinstance(p, dict)]
    idset = set(ids)
    if len(ids) != len(idset):
        err("D7", "packets", "duplicate packet_id")

    machine_ac = [ac["id"] for ac in ((spec.get("gate") or {}).get("acceptance") or [])
                  if isinstance(ac, dict) and ac.get("human") is not True and ac.get("id")]
    coverage = {a: [] for a in machine_ac}

    graph = {}
    for i, p in enumerate(packets):
        path = f"packets[{i}]"
        if not isinstance(p, dict):
            err("D3", path, "packet is not a mapping")
            continue
        for k in PACKET_FIELDS:
            v = p.get(k)
            if v is None or (isinstance(v, (str, list, dict)) and not v):
                err("D3", f"{path}.{k}", "required packet field absent or empty")
        # D4: inputs must be inline
        for sp, s in specgate._walk_strings(p.get("inputs"), f"{path}.inputs"):
            if XREF_RE.search(s):
                err("D4", sp, f"input references another packet's output: '{s[:80]}' — "
                              "merge the packets or pass the value inline")
        # D5/D6: acceptance coverage
        for a in p.get("acceptance") or []:
            if a not in set(machine_ac) | {ac.get("id") for ac in ((spec.get("gate") or {}).get("acceptance") or []) if isinstance(ac, dict)}:
                err("D6", f"{path}.acceptance", f"unknown acceptance id '{a}'")
            if a in coverage:
                coverage[a].append(p.get("packet_id"))
        graph[p.get("packet_id")] = list(p.get("depends_on") or [])

    for a, owners in coverage.items():
        if len(owners) == 0:
            err("D5", "packets", f"machine criterion {a} is covered by no packet")
        elif len(owners) > 1:
            err("D5", "packets", f"machine criterion {a} is covered by {owners} — exactly once required")

    # D7: dependencies known + acyclic; compute waves (Kahn levels)
    for pid, deps in graph.items():
        for d in deps:
            if d not in idset:
                err("D7", f"{pid}.depends_on", f"unknown dependency '{d}'")
    waves, remaining, placed = [], dict(graph), set()
    while remaining:
        wave = sorted(pid for pid, deps in remaining.items()
                      if all(d in placed for d in deps if d in idset))
        if not wave:
            err("D7", "packets", f"dependency cycle among {sorted(remaining)}")
            break
        waves.append(wave)
        placed.update(wave)
        for pid in wave:
            remaining.pop(pid)

    # D8: budgets
    spec_budget = (spec.get("bounds") or {}).get("budget")
    nums = [p.get("budget") for p in packets if isinstance(p, dict) and isinstance(p.get("budget"), (int, float))]
    if isinstance(spec_budget, (int, float)) and nums and sum(nums) > spec_budget:
        err("D8", "packets", f"packet budgets sum to {sum(nums)} > spec budget {spec_budget}")

    if errors:
        return errors, None

    # ---- materialise --------------------------------------------------------
    spec_id = (spec.get("header") or {}).get("spec_id", "SPEC")
    out = pathlib.Path(out_dir) / str(spec_id)
    out.mkdir(parents=True, exist_ok=True)
    policy = (spec.get("gate") or {}).get("missing_info_policy")
    written = []
    for p in packets:
        q = dict(p)
        q.setdefault("spec_id", spec_id)
        q.setdefault("missing_info", policy)
        q.setdefault("attempt", 1)
        q.setdefault("idempotency_key", hashlib.sha256(
            json.dumps({"s": spec_id, "p": p.get("packet_id"),
                        "v": (spec.get("header") or {}).get("version")},
                       sort_keys=True).encode()).hexdigest()[:16])
        fp = out / (str(p.get("packet_id")).replace("/", "_") + ".yaml")
        fp.write_text(yaml.safe_dump(q, sort_keys=False), encoding="utf-8")
        written.append(str(fp))
    plan = {"spec_id": spec_id, "waves": waves, "packets": written}
    (out / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return [], plan


def main(argv):
    if len(argv) not in (2, 3):
        print("usage: decompose.py <spec.yaml> [out_dir]", file=sys.stderr)
        return 2
    spec = yaml.safe_load(open(argv[1], encoding="utf-8"))
    errors, plan = decompose(spec, argv[2] if len(argv) == 3 else "packets")
    for e in errors:
        print(json.dumps(e))
    if errors:
        return 2
    print(json.dumps(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
