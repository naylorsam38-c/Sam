"""
graph_lib.py — small shared helpers over question_graph_v3.json.

Factored out of validate_graph.py so the Assembly Engine (packages/assembly-engine)
reuses the graph's own traceability logic instead of recomputing it a second way.
validate_graph.py imports field_sources() from here; its behaviour is unchanged
(same errors, same selftest catches) — verified by the existing test suite.
"""

import json
import os


def load_graph(path):
    with open(path, encoding="utf-8") as fh:
        g = json.load(fh)
    g["_q"] = {q["id"]: q for q in g["questions"]}
    g["_parts"] = {p["code"]: p for p in g["parts"]}
    return g


def field_sources(graph):
    """spec_field -> [owner_id, ...]. One clean source per field is a graph invariant
    that validate_graph.py enforces; callers that need the single owner should use
    field_source() below, which asserts that invariant rather than silently picking one.
    """
    sources = {}
    for q in graph["questions"]:
        for f in q["fills"]:
            sources.setdefault(f, []).append(q["id"])
    for d in graph["system_defaults"]:
        for f in d["fields"]:
            sources.setdefault(f, []).append(d["id"])
    for d in graph["derivations"]:
        for f in d["outputs"]:
            sources.setdefault(f, []).append(d["id"])
    for d in graph["deploy_inputs"]:
        for f in d["fields"]:
            sources.setdefault(f, []).append(d["id"])
    return sources


def field_source(graph):
    """spec_field -> single owner_id. Raises if the graph's own single-source
    invariant is violated (that case is validate_graph's job to report in detail)."""
    multi = field_sources(graph)
    out = {}
    for f, owners in multi.items():
        if len(owners) != 1:
            raise ValueError(f"spec field {f} has {len(owners)} sources {owners} — run validate_graph.py")
        out[f] = owners[0]
    return out


def owner_kind(graph, owner_id):
    """Classify an owner id: 'question' | 'system_default' | 'derivation' | 'deploy_input'."""
    if owner_id in graph["_q"]:
        return "question"
    if any(d["id"] == owner_id for d in graph["system_defaults"]):
        return "system_default"
    if any(d["id"] == owner_id for d in graph["derivations"]):
        return "derivation"
    if any(d["id"] == owner_id for d in graph["deploy_inputs"]):
        return "deploy_input"
    raise KeyError(owner_id)
