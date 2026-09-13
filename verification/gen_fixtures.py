#!/usr/bin/env python3
"""
gen_fixtures.py — builds the real fixture set for testing build.py.

Writes fixtures/common/{shelf,templates,APPS_LIST.md,choice.json}. Every
capability here is a REAL Flask route module, buggy or fixed, run by a REAL
dynamically-loading Flask app (modules/CAP-0001/app.py). No stubs, no mocks:
every "failure" is a real HTTP 500 from a real bug, every "fix" is a real
file replacing it, exactly per Sam's build.py SPEC v1 no-stubs requirement.

Rerunnable: `python3 gen_fixtures.py` wipes and rebuilds fixtures/common/.
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fixtures" / "common"

if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir(parents=True)

SHELF = ROOT / "shelf"
CAPS = SHELF / "capabilities"
IMPLS = SHELF / "implementations"
TEMPLATES = ROOT / "templates"
for d in (CAPS, IMPLS, TEMPLATES):
    d.mkdir(parents=True)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, obj):
    write(path, json.dumps(obj, indent=2))


# ==============================================================================
# Record helpers -- the Numbering Standard's own shapes, word for word.
#   §3.6 capability, §3.7 implementation; §6.2 lifecycle words for status.
# Aliases (§7.1) are NOT fields on an IMPL record (§3.7 has none); they are
# the registry's `aliases` entity (§3.2), written to shelf/aliases.json.
# ==============================================================================
ALIASES = []  # (alias, impl_id)


def cap_record(cap_id, name, category, impl_ids, output_fields=(), approval_ref="APPROVAL-CAP"):
    return {
        "id": cap_id,
        "name": name,
        "category": category,
        "status": "active",
        # §3.6 defers data_shape's internals to the Unified Feature Structure
        # (not in the package); this is the minimum the §4.4 twelve-axis
        # match reads: input.required/types, output.fields/types, nullable,
        # requires_auth, security_constraints.
        "data_shape": {
            "input": {"required": [], "types": {}},
            "output": {"fields": list(output_fields), "types": {}},
            "nullable": [],
            "requires_auth": False,
            "security_constraints": {},
        },
        "dependencies": [],
        "permissions": [],
        "side_effects": [],
        "error_contract": {"error_codes": []},
        "implementations": list(impl_ids),
        "qualification": {"status": "approved", "approved_by": "Sam", "approval_ref": approval_ref},
    }


def impl_record(impl_id, cap_id, entrypoint, status="active", version="1.0.0", approval_ref="APPROVAL-IMPL"):
    return {
        "id": impl_id,
        "capability_id": cap_id,
        "status": status,
        "release": {"version": version, "commit": "gen_fixtures.py", "approved": True, "approval_ref": approval_ref},
        "source": {"repository": "shelf", "path": impl_id, "entrypoint": entrypoint},
        "dependencies": [],
        "tests": [],
        "rollback": {"previous_version": None},
    }


def alias(name, impl_id):
    ALIASES.append({"alias": name, "impl_id": impl_id})


# ==============================================================================
# CAP-0001 — the app itself: home page + /api/items + dynamic module loader
# ==============================================================================
write_json(CAPS / "CAP-0001.json",
           cap_record("CAP-0001", "Todo item list", "ui",
                      ["CAP-0001/IMPL-01", "CAP-0001/IMPL-02", "CAP-0001/IMPL-03"]))
write_json(IMPLS / "CAP-0001" / "IMPL-01.json", impl_record("CAP-0001/IMPL-01", "CAP-0001", "CAP-0001/app.py"))
alias("todo_app_core@1.0.0", "CAP-0001/IMPL-01")

LOADER_APP_PY = '''#!/usr/bin/env python3
"""modules/CAP-0001/app.py — the real toy app: home page, /api/items, and a
dynamic loader for sibling capability modules (modules/<CAP-id>/route.py).
Each route module declares ROUTE, METHOD, handle(request) -> (status, body).
Modules are loaded in sorted directory-name order; a later-sorted module's
handler for the same (method, route) pair wins over an earlier one -- this
is how a repair that lands in a new CAP's module directory can supersede a
broken handler left behind in an old one, without either module colliding
inside Flask's own routing table.
"""
import argparse
import importlib.util
from pathlib import Path
from flask import Flask, request, jsonify, Response

HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

app = Flask(__name__)
ITEMS = []
_next_id = [1]

INDEX_HTML = """<!doctype html>
<html><head><title>Todo</title></head>
<body>
<h1>Todo List</h1>
<button id="add-item-btn" data-slot="main_list" onclick="addItem()">Add milk</button>
<ul id="item-list"></ul>
<script>
function addItem(){
  fetch('/api/items', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text:'milk'})})
    .then(function(r){ return r.json(); })
    .then(function(item){
      var li = document.createElement('li');
      li.textContent = item.text;
      document.getElementById('item-list').appendChild(li);
    });
}
</script>
</body></html>"""


@app.route("/health")
def health():
    return jsonify({"ok": True}), 200


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.route("/api/items", methods=["GET", "POST"])
def items():
    if request.method == "POST":
        body = request.get_json(force=True, silent=True) or {}
        item = {"id": _next_id[0], "text": body.get("text", ""), "created": True}
        _next_id[0] += 1
        ITEMS.append(item)
        return jsonify(item), 201
    return jsonify(ITEMS), 200


ROUTE_HANDLERS = {}


def load_modules():
    if not MODULES_ROOT.is_dir():
        return
    for entry in sorted(MODULES_ROOT.iterdir()):
        if not entry.is_dir() or entry.name == "CAP-0001":
            continue
        route_file = entry / "route.py"
        if not route_file.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"mod_{entry.name}", route_file)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            err = str(e)
            route_guess = getattr(mod, "ROUTE", None) or f"/api/unknown-{entry.name}"

            def _import_error_handler(_req, _err=err):
                return 500, {"error": f"module import failed: {_err}"}

            ROUTE_HANDLERS[("GET", route_guess)] = _import_error_handler
            continue
        route = getattr(mod, "ROUTE", None)
        method = getattr(mod, "METHOD", "GET")
        handler = getattr(mod, "handle", None)
        if route and handler:
            ROUTE_HANDLERS[(method, route)] = handler


load_modules()


@app.route("/<path:subpath>", methods=["GET", "POST"])
def dispatch(subpath):
    path = "/" + subpath
    handler = ROUTE_HANDLERS.get((request.method, path))
    if handler is None:
        return jsonify({"error": "not found"}), 404
    try:
        status, body = handler(request)
    except Exception as e:
        return jsonify({"error": f"handler raised {type(e).__name__}: {e}"}), 500
    return jsonify(body), status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port)
'''
write(IMPLS / "CAP-0001" / "IMPL-01" / "CAP-0001" / "app.py", LOADER_APP_PY)

# IMPL-02: a "browser-broken" variant -- HTTP-level checks (CHK-001/002) still
# pass, but the button's onclick never appends to #item-list, so only the
# real Playwright journey check (CHK-020) fails. Used for row 21b.
write_json(IMPLS / "CAP-0001" / "IMPL-02.json",
           impl_record("CAP-0001/IMPL-02", "CAP-0001", "CAP-0001/app.py", status="approved"))
alias("todo_app_core_browser_broken@1.0.0", "CAP-0001/IMPL-02")
LOADER_APP_PY_BROWSER_BROKEN = LOADER_APP_PY.replace(
    'onclick="addItem()">Add milk</button>', '>Add milk</button>'
)
assert LOADER_APP_PY_BROWSER_BROKEN != LOADER_APP_PY
write(IMPLS / "CAP-0001" / "IMPL-02" / "CAP-0001" / "app.py", LOADER_APP_PY_BROWSER_BROKEN)

# IMPL-03: identical to the good baseline app, except it installs a SIGTERM
# handler that ignores the signal -- used to prove run_layer_one's cleanup
# actually falls through to SIGKILL (proc.kill()) when terminate() alone
# doesn't work, rather than leaving the process running.
write_json(IMPLS / "CAP-0001" / "IMPL-03.json",
           impl_record("CAP-0001/IMPL-03", "CAP-0001", "CAP-0001/app.py", status="approved"))
alias("todo_app_core_ignores_sigterm@1.0.0", "CAP-0001/IMPL-03")
LOADER_APP_PY_IGNORES_SIGTERM = LOADER_APP_PY.replace(
    "import argparse\nimport importlib.util",
    "import argparse\nimport importlib.util\nimport signal",
).replace(
    "if __name__ == \"__main__\":\n    parser = argparse.ArgumentParser()",
    "if __name__ == \"__main__\":\n    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n    parser = argparse.ArgumentParser()",
)
assert LOADER_APP_PY_IGNORES_SIGTERM != LOADER_APP_PY
assert "SIG_IGN" in LOADER_APP_PY_IGNORES_SIGTERM
write(IMPLS / "CAP-0001" / "IMPL-03" / "CAP-0001" / "app.py", LOADER_APP_PY_IGNORES_SIGTERM)


# ==============================================================================
# Helper to build a simple "compute" capability with buggy/fixed IMPL pair
# ==============================================================================
def route_module(route, ok_value_or_error, is_error):
    if is_error:
        return f'''ROUTE = "{route}"
METHOD = "GET"


def handle(request):
    return 500, {{"error": {ok_value_or_error!r}}}
'''
    return f'''ROUTE = "{route}"
METHOD = "GET"


def handle(request):
    return 200, {{"ok": True, "value": {ok_value_or_error!r}}}
'''


def compute_cap(cap_id, name, impl_ids, output_fields=("ok", "value")):
    # output_fields must be kept distinct per unrelated capability -- build.py's
    # find_structural_matches() does an exact-set match against a failing
    # check's declared "wants" shape. Two capabilities that declare the identical
    # output shape are, correctly, both eligible matches -- and build.py now
    # refuses to guess between them (HELD). Each capability below gets a shape
    # unique to it, except CAP-0005 "Feature Beta Alt", which is DELIBERATELY
    # built to share CAP-0003's shape -- that's the one true structural match.
    return cap_record(cap_id, name, "compute", impl_ids, output_fields=output_fields)


def impl_meta(impl_id, cap_id, alias_name, _evidence, status="active"):
    alias(alias_name, impl_id)
    return impl_record(impl_id, cap_id, f"{cap_id}/route.py", status=status)


# ------------------------------------------------------------------------------
# CAP-0002 Feature Alpha — pattern-mapped repair (row 15)
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0002.json", compute_cap("CAP-0002", "Feature Alpha", ["CAP-0002/IMPL-01", "CAP-0002/IMPL-02"],
                                                 output_fields=("ok", "value", "source")))
write_json(IMPLS / "CAP-0002" / "IMPL-01.json",
           impl_meta("CAP-0002/IMPL-01", "CAP-0002", "feature_alpha_broken@1.0.0", "gen_fixtures.py buggy alpha"))
write(IMPLS / "CAP-0002" / "IMPL-01" / "CAP-0002" / "route.py",
      route_module("/api/feature-a", "alpha stub not implemented", True))
write_json(IMPLS / "CAP-0002" / "IMPL-02.json",
           impl_meta("CAP-0002/IMPL-02", "CAP-0002", "feature_alpha_fix@1.0.0", "gen_fixtures.py fixed alpha", status="approved"))
write(IMPLS / "CAP-0002" / "IMPL-02" / "CAP-0002" / "route.py",
      # Round 4: CAP-0002 declares output_fields ("ok","value","source") --
      # the fixed response must actually return all three, or a generic
      # check that trusts the CAP's own declared shape (rather than a
      # hand-picked subset) would never be able to pass it, even repaired.
      'ROUTE = "/api/feature-a"\nMETHOD = "GET"\n\n\n'
      'def handle(request):\n    return 200, {"ok": True, "value": 42, "source": "shelf"}\n')

# ------------------------------------------------------------------------------
# CAP-0003 Feature Beta (buggy, unmapped) + CAP-0005 Feature Beta Alt
# (a different, already-approved capability with the same shape) — structural
# match repair (row 16)
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0003.json", compute_cap("CAP-0003", "Feature Beta", ["CAP-0003/IMPL-01"]))
write_json(IMPLS / "CAP-0003" / "IMPL-01.json",
           impl_meta("CAP-0003/IMPL-01", "CAP-0003", "feature_beta_broken@1.0.0", "gen_fixtures.py buggy beta, no known fix pattern"))
write(IMPLS / "CAP-0003" / "IMPL-01" / "CAP-0003" / "route.py",
      route_module("/api/feature-b", "beta broken, unmapped failure xyz123", True))

write_json(CAPS / "CAP-0005.json", compute_cap("CAP-0005", "Feature Beta Alt", ["CAP-0005/IMPL-01"]))
write_json(IMPLS / "CAP-0005" / "IMPL-01.json",
           impl_meta("CAP-0005/IMPL-01", "CAP-0005", "feature_beta_alt@1.0.0", "gen_fixtures.py structural-match alternative for beta"))
write(IMPLS / "CAP-0005" / "IMPL-01" / "CAP-0005" / "route.py",
      route_module("/api/feature-b", 99, False))

# ------------------------------------------------------------------------------
# CAP-0004 Regression Trap — pattern-mapped fix that also overwrites CAP-0001's
# app.py, breaking a previously-passing check (row 18)
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0004.json", compute_cap("CAP-0004", "Regression Trap", ["CAP-0004/IMPL-01", "CAP-0004/IMPL-02"],
                                                 output_fields=("ok", "trap")))
write_json(IMPLS / "CAP-0004" / "IMPL-01.json",
           impl_meta("CAP-0004/IMPL-01", "CAP-0004", "regression_trap_broken@1.0.0", "gen_fixtures.py buggy regression trap"))
write(IMPLS / "CAP-0004" / "IMPL-01" / "CAP-0004" / "route.py",
      route_module("/api/feature-regression", "regression trap not wired, needs patch", True))

write_json(IMPLS / "CAP-0004" / "IMPL-02.json",
           impl_meta("CAP-0004/IMPL-02", "CAP-0004", "regression_trap_fix@1.0.0",
                      "gen_fixtures.py fix that deliberately also overwrites CAP-0001/app.py -- for proving the regression guard",
                      status="approved"))
write(IMPLS / "CAP-0004" / "IMPL-02" / "CAP-0004" / "route.py",
      # Round 4: CAP-0004 declares output_fields ("ok","trap") -- include it for real.
      'ROUTE = "/api/feature-regression"\nMETHOD = "GET"\n\n\n'
      'def handle(request):\n    return 200, {"ok": True, "trap": "cleared", "value": 1}\n')
# The regression payload: CAP-0001/app.py identical to the good loader except
# /api/items POST now omits the "created" field -- breaks CHK-002, which
# passed on the prior run.
REGRESSION_APP_PY = LOADER_APP_PY.replace(
    '        item = {"id": _next_id[0], "text": body.get("text", ""), "created": True}',
    '        item = {"id": _next_id[0], "text": body.get("text", "")}',
)
assert REGRESSION_APP_PY != LOADER_APP_PY
write(IMPLS / "CAP-0004" / "IMPL-02" / "CAP-0001" / "app.py", REGRESSION_APP_PY)

# ------------------------------------------------------------------------------
# CAP-0006 Feature Gamma — pattern-mapped, but the shelf "fix" does not
# actually fix it (row 17 loop guard). A separate shelf snapshot for this
# capability (without IMPL-02 at all) is used for the gap/HELD scenarios
# (rows 2, 14, 20) -- built by the driver, not here.
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0006.json", compute_cap("CAP-0006", "Feature Gamma", ["CAP-0006/IMPL-01", "CAP-0006/IMPL-02"],
                                                 output_fields=("ok", "calibration")))
write_json(IMPLS / "CAP-0006" / "IMPL-01.json",
           impl_meta("CAP-0006/IMPL-01", "CAP-0006", "feature_gamma_broken@1.0.0", "gen_fixtures.py buggy gamma"))
write(IMPLS / "CAP-0006" / "IMPL-01" / "CAP-0006" / "route.py",
      route_module("/api/feature-gamma", "gamma broken, needs recalibration", True))
write_json(IMPLS / "CAP-0006" / "IMPL-02.json",
           impl_meta("CAP-0006/IMPL-02", "CAP-0006", "feature_gamma_fix@1.0.0",
                      "gen_fixtures.py -- deliberately still-broken 'fix', for proving the loop guard",
                      status="approved"))
write(IMPLS / "CAP-0006" / "IMPL-02" / "CAP-0006" / "route.py",
      route_module("/api/feature-gamma", "gamma broken, needs recalibration", True))

# ------------------------------------------------------------------------------
# CAP-0008 Feature Delta, CAP-0009 Feature Epsilon — both cleanly
# pattern-fixable, used together with alpha for the restart-ceiling test (row 19)
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0008.json", compute_cap("CAP-0008", "Feature Delta", ["CAP-0008/IMPL-01", "CAP-0008/IMPL-02"],
                                                 output_fields=("ok", "config")))
write_json(IMPLS / "CAP-0008" / "IMPL-01.json",
           impl_meta("CAP-0008/IMPL-01", "CAP-0008", "feature_delta_broken@1.0.0", "gen_fixtures.py buggy delta"))
write(IMPLS / "CAP-0008" / "IMPL-01" / "CAP-0008" / "route.py",
      route_module("/api/feature-delta", "delta broken, config missing", True))
write_json(IMPLS / "CAP-0008" / "IMPL-02.json",
           impl_meta("CAP-0008/IMPL-02", "CAP-0008", "feature_delta_fix@1.0.0", "gen_fixtures.py fixed delta", status="approved"))
write(IMPLS / "CAP-0008" / "IMPL-02" / "CAP-0008" / "route.py",
      # Round 4: CAP-0008 declares output_fields ("ok","config") -- include it for real.
      'ROUTE = "/api/feature-delta"\nMETHOD = "GET"\n\n\n'
      'def handle(request):\n    return 200, {"ok": True, "config": "loaded", "value": 7}\n')

write_json(CAPS / "CAP-0009.json", compute_cap("CAP-0009", "Feature Epsilon", ["CAP-0009/IMPL-01", "CAP-0009/IMPL-02"],
                                                 output_fields=("ok", "timeout")))
write_json(IMPLS / "CAP-0009" / "IMPL-01.json",
           impl_meta("CAP-0009/IMPL-01", "CAP-0009", "feature_epsilon_broken@1.0.0", "gen_fixtures.py buggy epsilon"))
write(IMPLS / "CAP-0009" / "IMPL-01" / "CAP-0009" / "route.py",
      route_module("/api/feature-epsilon", "epsilon broken, timeout stub", True))
write_json(IMPLS / "CAP-0009" / "IMPL-02.json",
           impl_meta("CAP-0009/IMPL-02", "CAP-0009", "feature_epsilon_fix@1.0.0", "gen_fixtures.py fixed epsilon", status="approved"))
write(IMPLS / "CAP-0009" / "IMPL-02" / "CAP-0009" / "route.py",
      # Round 4: CAP-0009 declares output_fields ("ok","timeout") -- include it for real.
      'ROUTE = "/api/feature-epsilon"\nMETHOD = "GET"\n\n\n'
      'def handle(request):\n    return 200, {"ok": True, "timeout": 30, "value": 3}\n')

# ==============================================================================
# CAP-0010 Feature Zeta, CAP-0011 Feature Eta -- round 4 genericity proof.
# build.py's build_checks() has never had a branch written for CAP-0010 or
# CAP-0011 by id -- these exist only to prove the generic compute-capability
# check generator (round 4) produces a real, correct check from nothing but
# what these two capabilities themselves declare: their own ROUTE/METHOD
# (read off their route.py, not written into build.py) and their own
# data_shape.output.fields (distinct shapes from every other capability, so
# a check that happened to pass by coincidence against the wrong fields would
# show up as a real failure, not a false positive).
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0010.json", compute_cap("CAP-0010", "Feature Zeta", ["CAP-0010/IMPL-01"],
                                                 output_fields=("zeta_status", "zeta_reading", "zeta_unit")))
write_json(IMPLS / "CAP-0010" / "IMPL-01.json",
           impl_meta("CAP-0010/IMPL-01", "CAP-0010", "feature_zeta@1.0.0", "gen_fixtures.py -- round 4 genericity proof, zeta"))
write(IMPLS / "CAP-0010" / "IMPL-01" / "CAP-0010" / "route.py",
      '''ROUTE = "/api/feature-zeta"
METHOD = "GET"


def handle(request):
    return 200, {"zeta_status": "nominal", "zeta_reading": 7.25, "zeta_unit": "bar"}
''')

write_json(CAPS / "CAP-0011.json", compute_cap("CAP-0011", "Feature Eta", ["CAP-0011/IMPL-01"],
                                                 output_fields=("eta_count", "eta_label")))
write_json(IMPLS / "CAP-0011" / "IMPL-01.json",
           impl_meta("CAP-0011/IMPL-01", "CAP-0011", "feature_eta@1.0.0", "gen_fixtures.py -- round 4 genericity proof, eta"))
write(IMPLS / "CAP-0011" / "IMPL-01" / "CAP-0011" / "route.py",
      '''ROUTE = "/api/feature-eta"
METHOD = "POST"


def handle(request):
    return 200, {"eta_count": 3, "eta_label": "batch-complete"}
''')

# Also proves the negative: a compute capability whose active IMPL's module
# has no ROUTE/METHOD at all gets no generic check (build_checks() skips it
# rather than inventing one) -- CAP-0012 "Feature Theta Undeclared".
write_json(CAPS / "CAP-0012.json", compute_cap("CAP-0012", "Feature Theta Undeclared", ["CAP-0012/IMPL-01"],
                                                 output_fields=("theta_value",)))
write_json(IMPLS / "CAP-0012" / "IMPL-01.json",
           impl_meta("CAP-0012/IMPL-01", "CAP-0012", "feature_theta_undeclared@1.0.0",
                      "gen_fixtures.py -- round 4: deliberately no ROUTE/METHOD declared"))
write(IMPLS / "CAP-0012" / "IMPL-01" / "CAP-0012" / "route.py",
      "# deliberately no ROUTE or METHOD constant -- proves build_checks() skips rather than guesses\n"
      "def handle(request):\n    return 200, {\"theta_value\": 1}\n")


# ==============================================================================
# Templates
# ==============================================================================
def slot(slot_id, target_cap, selector=None):
    s = {
        "slot_id": slot_id, "name": slot_id.replace("_", " ").title(), "target_capability": target_cap,
        "expected_contract": {
            "required_input_fields": [], "input_types": {}, "output_fields": [],
            "output_types": {}, "nullable_fields": [], "permissions": [], "requires_auth": False,
            "dependencies": [], "handled_errors": [], "security_constraints": {}, "side_effects": [],
            "min_version": "1.0.0",
        },
    }
    if selector:
        s["selector"] = selector
    return s


def base_template(required_caps, slots, test_ok=True, has_tests=True, start_mod="CAP-0001/app.py",
                   port_flask=True):
    tpl = {
        "accepted": True,
        "app_type": "Todo List App",
        "required_capabilities": required_caps,
        "interface_slots": slots,
        "entry_route": "/",
        "entry_screen_name": "Home",
        "start_command": ["python3", "modules/" + start_mod],
        "port": 5000,
        "health_endpoint": "/health",
    }
    if has_tests:
        tpl["test_command"] = ["python3", "-c", "print('template tests ok')"] if test_ok else \
            ["python3", "-c", "import sys; print('template tests failing on purpose'); sys.exit(1)"]
    return tpl


# CHK-002 wants create record fields for CAP-0001's own /api/items, no
# expected_contract fields needed for that (it's not a matched-slot check --
# CAP-0001 is checked directly by build_checks(), independent of contracts).
BASE_SLOTS_0001 = [slot("main_list", "CAP-0001", "#add-item-btn")]

write_json(TEMPLATES / "todo_list_app.json",
           base_template(["CAP-0001"], BASE_SLOTS_0001))

write_json(TEMPLATES / "todo_pattern.json",
           base_template(["CAP-0001", "CAP-0002"], BASE_SLOTS_0001 + [slot("alpha", "CAP-0002")]))

write_json(TEMPLATES / "todo_structural.json",
           base_template(["CAP-0001", "CAP-0003"], BASE_SLOTS_0001 + [slot("beta", "CAP-0003")]))

write_json(TEMPLATES / "todo_loopguard.json",
           base_template(["CAP-0001", "CAP-0006"], BASE_SLOTS_0001 + [slot("gamma", "CAP-0006")]))

write_json(TEMPLATES / "todo_regression.json",
           base_template(["CAP-0001", "CAP-0004"], BASE_SLOTS_0001 + [slot("regress", "CAP-0004")]))

write_json(TEMPLATES / "todo_restart_ceiling.json",
           base_template(["CAP-0001", "CAP-0002", "CAP-0008", "CAP-0009"],
                          BASE_SLOTS_0001 + [slot("alpha", "CAP-0002"), slot("delta", "CAP-0008"), slot("epsilon", "CAP-0009")]))

write_json(TEMPLATES / "todo_gap.json",
           base_template(["CAP-0001", "CAP-0006"], BASE_SLOTS_0001 + [slot("gamma", "CAP-0006")]))

write_json(TEMPLATES / "todo_no_tests.json",
           base_template(["CAP-0001"], BASE_SLOTS_0001, has_tests=False))

write_json(TEMPLATES / "todo_failing_tests.json",
           base_template(["CAP-0001"], BASE_SLOTS_0001, test_ok=False))

bad_health_tpl = base_template(["CAP-0001"], BASE_SLOTS_0001)
bad_health_tpl["start_command"] = ["python3", "-c", "import time; time.sleep(60)"]
write_json(TEMPLATES / "todo_bad_health.json", bad_health_tpl)

# CAP-0001 is required (so its app.py + health endpoint are present and the
# app actually runs) but NO interface slot targets it, so no BTN ever gets
# capability_id=CAP-0001 -- build_checks() gates CHK-001/002/020 on exactly
# that, so none of them are generated. Only CHK-010 (alpha) exists. A
# dedicated shelf snapshot (driver-built) points CAP-0002 at the already-
# fixed IMPL-02, so alpha passes cleanly and the run reaches "all checks
# passed, but none of them was the browser check" on the very first try.
no_browser_tpl = base_template(["CAP-0001", "CAP-0002"], [slot("alpha", "CAP-0002")])
write_json(TEMPLATES / "todo_no_browser_check.json", no_browser_tpl)

browser_broken_tpl = base_template(["CAP-0001"], BASE_SLOTS_0001)
write_json(TEMPLATES / "todo_browser_broken.json", browser_broken_tpl)

sigterm_tpl = base_template(["CAP-0001"], BASE_SLOTS_0001)
write_json(TEMPLATES / "todo_sigterm.json", sigterm_tpl)

# Round 4 genericity proof: CAP-0010/0011 have real, distinct declared shapes
# build_checks() has never had a branch for; CAP-0012 has no declared
# ROUTE/METHOD at all and must be silently skipped, not guessed at.
write_json(TEMPLATES / "todo_generic.json",
           base_template(["CAP-0001", "CAP-0010", "CAP-0011", "CAP-0012"],
                          BASE_SLOTS_0001 + [slot("zeta", "CAP-0010"), slot("eta", "CAP-0011"),
                                             slot("theta", "CAP-0012")]))

# ------------------------------------------------------------------------------
# Round 5 (H-T3 ruling) — CAP-0013 declares MORE nullable fields and MORE
# security constraints than a slot actually requires. Under the old exact-
# equality match this would HELD even though the capability is strictly
# stricter/safer than what was asked for; under the loosened directional
# subset match it must bind cleanly.
# ------------------------------------------------------------------------------
write_json(CAPS / "CAP-0013.json", {
    "id": "CAP-0013", "name": "Feature Iota", "category": "compute", "status": "active",
    "data_shape": {
        "input": {"required": [], "types": {}},
        "output": {"fields": ["ok", "iota_value"], "types": {}},
        # the capability allows "iota_value" to be null -- MORE than a slot
        # that only expects "ok" might ever be null (nullable_fields: ["ok"]).
        "nullable": ["iota_value"],
        "requires_auth": False,
        # the capability enforces an extra constraint ("encrypted_at_rest")
        # beyond anything a slot would ask for.
        "security_constraints": {"encrypted_at_rest": True},
    },
    "dependencies": [], "permissions": [], "side_effects": [],
    "error_contract": {"error_codes": []},
    "implementations": ["CAP-0013/IMPL-01"],
    "qualification": {"status": "approved", "approved_by": "Sam", "approval_ref": "APPROVAL-CAP"},
})
write_json(IMPLS / "CAP-0013" / "IMPL-01.json", impl_meta("CAP-0013/IMPL-01", "CAP-0013", "feature_iota@1.0.0", "gen_fixtures.py -- round 5, H-T3 subset-match proof"))
write(IMPLS / "CAP-0013" / "IMPL-01" / "CAP-0013" / "route.py",
      'ROUTE = "/api/feature-iota"\nMETHOD = "GET"\n\n\ndef handle(request):\n    return 200, {"ok": True, "iota_value": None}\n')

iota_slot = slot("iota", "CAP-0013")
# The slot only actually cares that "ok" might be null -- it does NOT know
# or require that "iota_value" can be null too; the CAP is free to be more
# tolerant/defensive than the slot asked for. Under the OLD exact-equality
# match this would have failed (["ok"] != ["iota_value"]) even though the
# capability is strictly safer, never less safe, than what's required.
iota_slot["expected_contract"]["nullable_fields"] = ["ok", "iota_value"]
iota_slot["expected_contract"]["security_constraints"] = {}  # narrower than the CAP's own {"encrypted_at_rest": True}
write_json(TEMPLATES / "todo_subset_ok.json",
           base_template(["CAP-0001", "CAP-0013"], BASE_SLOTS_0001 + [iota_slot]))

# The negative case: a slot that requires a security constraint the
# capability does NOT declare must still HELD -- the loosened match must not
# have become "anything goes."
write_json(CAPS / "CAP-0014.json", {
    "id": "CAP-0014", "name": "Feature Kappa Underdeclared", "category": "compute", "status": "active",
    "data_shape": {
        "input": {"required": [], "types": {}},
        "output": {"fields": ["ok"], "types": {}},
        "nullable": [], "requires_auth": False,
        "security_constraints": {},  # deliberately does NOT declare encrypted_at_rest
    },
    "dependencies": [], "permissions": [], "side_effects": [],
    "error_contract": {"error_codes": []},
    "implementations": ["CAP-0014/IMPL-01"],
    "qualification": {"status": "approved", "approved_by": "Sam", "approval_ref": "APPROVAL-CAP"},
})
write_json(IMPLS / "CAP-0014" / "IMPL-01.json", impl_meta("CAP-0014/IMPL-01", "CAP-0014", "feature_kappa_underdeclared@1.0.0", "gen_fixtures.py -- round 5, H-T3 negative proof"))
write(IMPLS / "CAP-0014" / "IMPL-01" / "CAP-0014" / "route.py",
      'ROUTE = "/api/feature-kappa"\nMETHOD = "GET"\n\n\ndef handle(request):\n    return 200, {"ok": True}\n')

kappa_slot = slot("kappa", "CAP-0014")
kappa_slot["expected_contract"]["security_constraints"] = {"encrypted_at_rest": True}
write_json(TEMPLATES / "todo_subset_reject.json",
           base_template(["CAP-0001", "CAP-0014"], BASE_SLOTS_0001 + [kappa_slot]))

# ==============================================================================
# APPS_LIST.md + baseline choice.json
# ==============================================================================
write(ROOT / "APPS_LIST.md", "# Approved app types\n\n- Todo List App\n")

write_json(ROOT / "choice.json", {
    "app_type": "Todo List App",
    "skin_id": "skin-001",
    "skin_version": "1.0.0",
    "arrangement": [{"slot": "main_list", "position": "center"}],
    "branding": {"name": "Sam's Todo", "color": "#111111"},
})

write_json(SHELF / "aliases.json", {"aliases": ALIASES})
print(f"fixtures written under {ROOT}")
