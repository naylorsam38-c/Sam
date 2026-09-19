#!/usr/bin/env python3
"""
detect_capability.py — Capability Discovery + Attach-Point Detection.

Finds where a target capability is genuinely implemented in a discovered
application, using Python's own `ast` module rather than filename or
keyword matching. A route path or function name is only a HINT that
narrows which function to look at; a candidate only counts as a real
attach point once its body is shown to actually call the functions that
implementation requires (e.g. csv.writer(...) and send_file(...) for a
CSV-export capability) — the same "evidence must be in the real construct,
not just mentioned nearby" principle as the capability-evidence matcher
fixed in PR #11, applied here to route-to-capability detection instead of
declaration-to-capability detection.

Run: python3 detection/detect_capability.py
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

# ----------------------------------------------------------------------------
# CONFIG — the capabilities this run looks for, and where to look.
# Walking-skeleton scope: one capability. `route_path_hint` and
# `evidence_call_names` only narrow the search; a match still requires the
# evidence calls to be genuinely present in the candidate function's body.
# ----------------------------------------------------------------------------
CAPABILITY_TARGETS = [
    {
        "cap_id": "CAP-0001",
        "name": "export data",
        "category": "personal-finance",
        "app_slug": "monthly-expenses-tracker",
        "source_file_relative": "app/routes.py",
        "route_path_hint": "/export",
        "evidence_call_names": {"writer", "send_file"},
    },
]
# ----------------------------------------------------------------------------


def _decorator_route_path(decorator: ast.expr):
    """If `decorator` looks like `<blueprint>.route('/path', ...)`, return the path string."""
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    is_route_call = isinstance(func, ast.Attribute) and func.attr == "route"
    if not is_route_call:
        return None
    if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
        return decorator.args[0].value
    return None


def _call_names_in(node: ast.AST):
    names = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            if isinstance(sub.func, ast.Name):
                names.add(sub.func.id)
            elif isinstance(sub.func, ast.Attribute):
                names.add(sub.func.attr)
    return names


def _unparse_decorator(node: ast.expr) -> str:
    try:
        return "@" + ast.unparse(node)
    except Exception:
        return "@<unparseable>"


def find_attach_point(source_path: Path, target: dict):
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        route_path = None
        for dec in node.decorator_list:
            path = _decorator_route_path(dec)
            if path is not None:
                route_path = path
                break
        if route_path is None or target["route_path_hint"] not in route_path:
            continue  # not even a hint match -- keep looking

        evidence_present = _call_names_in(node) & target["evidence_call_names"]
        if not evidence_present:
            # The route matched by name/path alone -- exactly the kind of
            # false positive this detector exists to reject. Do not record
            # it as an attach point; keep looking in case of an overload,
            # then fall through to "not found" if nothing else matches.
            continue

        return {
            "cap_id": target["cap_id"],
            "name": target["name"],
            "category": target["category"],
            "app_slug": target["app_slug"],
            "found": True,
            "source_file_relative": target["source_file_relative"],
            "symbol": node.name,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "decorators": [_unparse_decorator(d) for d in node.decorator_list],
            "route_path": route_path,
            "evidence_calls_matched": sorted(evidence_present),
        }

    return {
        "cap_id": target["cap_id"],
        "name": target["name"],
        "category": target["category"],
        "app_slug": target["app_slug"],
        "found": False,
        "reason": (
            f"no function decorated with a route containing '{target['route_path_hint']}' "
            f"was found whose body calls any of {sorted(target['evidence_call_names'])}"
        ),
    }


def main():
    config.ensure_dirs()
    config.print_roots(__file__)

    applications = {a["slug"]: a for a in config.load_json(config.REPOSITORY_SOURCE)["applications"]}

    results = []
    for target in CAPABILITY_TARGETS:
        app = applications.get(target["app_slug"])
        if app is None or app["blocked"]:
            results.append({
                "cap_id": target["cap_id"], "app_slug": target["app_slug"], "found": False,
                "reason": "application not discovered or blocked on licence -- see discovery/applications.json",
            })
            continue

        source_path = Path(app["cloned_path"]) / target["source_file_relative"]
        result = find_attach_point(source_path, target)
        status = "FOUND" if result["found"] else "NOT FOUND"
        print(f"  [{target['cap_id']}] {status}: {target['name']} in {target['app_slug']}")
        if result["found"]:
            print(f"    {result['source_file_relative']}:{result['lineno']}-{result['end_lineno']} "
                  f"symbol={result['symbol']} evidence={result['evidence_calls_matched']}")
        results.append(result)

    out_path = config.OUTPUT_ROOT / "attach_points.json"
    config.write_json(out_path, {"attach_points": results})
    print(f"Wrote {out_path}")

    not_found = [r for r in results if not r["found"]]
    return 1 if not_found else 0


if __name__ == "__main__":
    sys.exit(main())
