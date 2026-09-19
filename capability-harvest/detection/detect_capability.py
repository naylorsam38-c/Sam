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
    {
        "cap_id": "CAP-0002",
        "name": "manage inventory",
        "category": "inventory",
        "app_slug": "inventory-tracker",
        "source_file_relative": "app.py",
        "route_path_hint": "/update/",
        "evidence_call_names": {"execute", "commit"},
    },
    {
        "cap_id": "CAP-0003",
        "name": "search records",
        "category": "hostel-booking",
        "app_slug": "hostelfix",
        "source_file_relative": "app.py",
        "route_path_hint": "/search",
        "evidence_call_names": {"filter", "ilike"},
    },
    {
        "cap_id": "CAP-0004",
        "name": "track streak",
        "category": "habit-tracking",
        "app_slug": "habit-tracker",
        "source_file_relative": "app.py",
        # calculate_streaks() is a plain function, not a Flask route -- it
        # has no @app.route decorator to hint on. detect_by_symbol_name
        # below is used for this target instead of the route-based search.
        "symbol_hint": "calculate_streaks",
        "evidence_call_names": {"sorted", "max"},
    },
    {
        "cap_id": "CAP-0005",
        "name": "send message",
        "category": "messaging",
        "app_slug": "flask-messenger",
        "source_file_relative": "messenger.py",
        "route_path_hint": "/",
        "evidence_call_names": {"connect", "execute", "commit"},
        # home() is a thin route that delegates to _add_message(); the real
        # evidence (the INSERT) lives in the helper it calls, which is why
        # this target's evidence_call_names are checked against
        # _add_message via symbol_hint instead of the route function body.
        "symbol_hint": "_add_message",
    },
    {
        "cap_id": "CAP-0006",
        "name": "write review",
        "category": "recipe-sharing",
        "app_slug": "recipe-app",
        "source_file_relative": "routes/comments.py",
        "symbol_hint": "make_comment",
        "evidence_call_names": {"execute", "commit"},
    },
    {
        "cap_id": "CAP-0007",
        "name": "generate report",
        "category": "personal-finance",
        "app_slug": "fintrack",
        "source_file_relative": "app/routes/reports.py",
        "route_path_hint": "/generate_report",
        # Real delegation to the PDF/Excel builders defined lower in the
        # same file -- not just "renders a template".
        "evidence_call_names": {"_build_pdf_report", "_build_excel_report"},
    },
    {
        "cap_id": "CAP-0008",
        "name": "award badge",
        "category": "gamified-learning",
        "app_slug": "bounty-simulator",
        "source_file_relative": "backend/main.py",
        "symbol_hint": "check_badges",
        "evidence_call_names": {"filter_by", "add", "commit"},
    },
    {
        "cap_id": "CAP-0009",
        "name": "show leaderboard",
        "category": "gamified-learning",
        "app_slug": "bounty-simulator",
        "source_file_relative": "backend/main.py",
        "route_path_hint": "/api/leaderboard",
        "evidence_call_names": {"order_by", "desc", "limit"},
    },
    {
        "cap_id": "CAP-0010",
        "name": "add favourite",
        "category": "cafe-directory",
        "app_slug": "flask-coffee-and-wifi",
        "source_file_relative": "main.py",
        "route_path_hint": "/add_bookmark/",
        "evidence_call_names": {"add", "commit"},
    },
    {
        "cap_id": "CAP-0011",
        "name": "log workout",
        "category": "fitness",
        "app_slug": "casettafit",
        "source_file_relative": "app/routes/workout.py",
        "route_path_hint": "/log-set",
        "evidence_call_names": {"add", "commit"},
    },
    {
        "cap_id": "CAP-0012",
        "name": "rate item",
        "category": "media-rating",
        "app_slug": "zinny-api",
        "source_file_relative": "src/zinny_api/api/ratings.py",
        "symbol_hint": "save_rating",
        "evidence_call_names": {"execute", "commit"},
    },
    {
        "cap_id": "CAP-0013",
        "name": "calculate tax",
        "category": "payroll",
        "app_slug": "payroll-tax-calculator",
        "source_file_relative": "salary_engine.py",
        "symbol_hint": "calculate_payroll_details",
        "evidence_call_names": {"max", "min"},
    },
    {
        "cap_id": "CAP-0014",
        "name": "book slot",
        "category": "healthcare-scheduling",
        "app_slug": "hospital-management-real",
        "source_file_relative": "app.py",
        "symbol_hint": "patient_book",
        "evidence_call_names": {"filter_by", "add", "commit"},
    },
    {
        "cap_id": "CAP-0015",
        "name": "generate invoice",
        "category": "billing",
        "app_slug": "invoice-generator",
        "source_file_relative": "server.py",
        "symbol_hint": "generate_invoice_pdf",
        "evidence_call_names": {"render_template", "write_pdf"},
    },
    {
        "cap_id": "CAP-0016",
        "name": "register account",
        "category": "healthcare-scheduling",
        "app_slug": "hospital-management-real",
        "source_file_relative": "app.py",
        "symbol_hint": "patient_register",
        "evidence_call_names": {"generate_password_hash", "commit"},
    },
    {
        "cap_id": "CAP-0017",
        "name": "log in",
        "category": "healthcare-scheduling",
        "app_slug": "hospital-management-real",
        "source_file_relative": "app.py",
        "symbol_hint": "login",
        "evidence_call_names": {"check_password_hash", "commit"},
    },
    {
        "cap_id": "CAP-0018",
        "name": "log out",
        "category": "healthcare-scheduling",
        "app_slug": "hospital-management-real",
        "source_file_relative": "app.py",
        "symbol_hint": "logout",
        "evidence_call_names": {"commit"},
    },
    {
        "cap_id": "CAP-0019",
        "name": "upload image",
        "category": "media",
        "app_slug": "image-upload-app",
        "source_file_relative": "app.py",
        "symbol_hint": "upload_image",
        "evidence_call_names": {"secure_filename", "save"},
    },
    {
        "cap_id": "CAP-0020",
        "name": "track location",
        "category": "attendance-tracking",
        "app_slug": "smart-attendance-system",
        "source_file_relative": "views/student.py",
        "symbol_hint": "mark_attendance",
        "evidence_call_names": {"verify_location", "commit"},
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
    """
    Two search modes, both requiring genuine evidence in the candidate's
    own body before it counts as a match -- a route path or a symbol name
    is only ever a HINT that narrows candidates, never the decision itself:

      - route_path_hint: candidate functions are Flask routes whose
        decorator path contains the hint (the capability lives directly in
        the route handler).
      - symbol_hint: candidate is the function with exactly that name,
        wherever it's defined (the capability lives in a plain function or
        a helper the route delegates to, not the route handler itself).
    """
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        route_path = None
        if "symbol_hint" in target:
            if node.name != target["symbol_hint"]:
                continue
        else:
            for dec in node.decorator_list:
                path = _decorator_route_path(dec)
                if path is not None:
                    route_path = path
                    break
            if route_path is None or target["route_path_hint"] not in route_path:
                continue  # not even a hint match -- keep looking

        evidence_present = _call_names_in(node) & target["evidence_call_names"]
        if not evidence_present:
            # The candidate matched by name/route alone -- exactly the kind
            # of false positive this detector exists to reject. Do not
            # record it as an attach point; keep looking in case of an
            # overload, then fall through to "not found" if nothing matches.
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

    hint_desc = f"symbol named '{target['symbol_hint']}'" if "symbol_hint" in target else \
        f"a route containing '{target['route_path_hint']}'"
    return {
        "cap_id": target["cap_id"],
        "name": target["name"],
        "category": target["category"],
        "app_slug": target["app_slug"],
        "found": False,
        "reason": f"no function matching {hint_desc} was found whose body calls any of {sorted(target['evidence_call_names'])}",
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
