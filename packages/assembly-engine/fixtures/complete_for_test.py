#!/usr/bin/env python3
"""
complete_for_test.py — fill a template's ask_customer questions with clearly
synthetic placeholder answers, so the assembler can be regression-tested end
to end against all five templates. Test fixture generation only: this is not
how a real instance gets completed (that is the Requirements Engine's job,
by asking a real customer) — see task 8 for a real, non-synthetic instance.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "..", "requirements-engine")
sys.path.insert(0, os.path.abspath(ENGINE))
import graph_lib  # noqa: E402

SYNTH = {
    "text": "test value", "confirm": "confirmed", "yesno": "yes",
}


def synth_value(q):
    t = q["type"]
    if t in SYNTH:
        return SYNTH[t]
    if t == "choice":
        opts = [o.split(" — ")[0] for o in (q.get("options") or []) if not o.startswith("<")]
        return opts[0] if opts else "test"
    if t == "multi":
        opts = [o.split(" — ")[0] for o in (q.get("options") or []) if not o.startswith("<")]
        return opts[:1] or ["test"]
    if t == "structured":
        return {"note": "synthetic test value"}
    return "test"


def complete(graph, inst):
    inst = copy.deepcopy(inst)
    qs = graph["_q"]
    for entry in list(inst["ask_customer"]):
        qid = entry.split(":")[0]
        q = qs[qid]
        v = synth_value(q)
        if q["per"] is None:
            inst["answers"][qid] = v
        else:
            # ask_customer entries for per-instance questions are rare in these
            # templates (none of the five leave a per-instance question fully
            # open) — handled generically in case a future template does.
            for inst_name in inst["inventory"].get(graph_lib_pool(q["per"]), []):
                inst["per_instance"].setdefault(f"{qid}:{inst_name}", v)
    inst["ask_customer"] = []
    if inst["answers"].get("0.01") not in (None,) and inst["answers"]["0.01"] not in ("full", "guided", "hands-off"):
        inst["answers"]["0.01"] = "hands-off"
    return inst


def graph_lib_pool(per_kind):
    return {"record": "records", "role": "roles", "form": "forms", "file_type": "file_types",
            "workflow": "workflows", "notification": "notifications", "report": "reports",
            "integration": "integrations"}.get(per_kind, "records")


if __name__ == "__main__":
    graph = graph_lib.load_graph(os.path.join(os.path.abspath(ENGINE), "question_graph_v3.json"))
    graph["_q"] = {q["id"]: q for q in graph["questions"]}
    src, dst = sys.argv[1], sys.argv[2]
    inst = json.load(open(src, encoding="utf-8"))
    out = complete(graph, inst)
    json.dump(out, open(dst, "w", encoding="utf-8"), indent=2)
    print("wrote", dst)
