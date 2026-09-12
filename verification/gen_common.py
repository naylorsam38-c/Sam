#!/usr/bin/env python3
"""
gen_common.py — shared, reusable machinery for generating real, non-fixture
build.py projects, factored out of gen_real_todo_app.py's own proven pattern
(round 7) so each additional real app type (of Sam's real 43-item
canonical_app_types.py list) is a declarative capability/template spec
instead of ~350 lines of hand-duplicated boilerplate per app.

Every record shape below (cap_record/impl_record/slot) is copied verbatim
from gen_real_todo_app.py, which itself copied gen_fixtures.py's shapes —
not reinvented, so the contract build.py actually validates stays identical
across every generated app. The host app (Flask + dynamic route-module
loader) is the same proven CAP-0100 convention, parameterized only by which
data file it points at and which HTML it serves.

This file has no import-time side effects — it only defines functions used
by per-app generator scripts.
"""
import json
import shutil
from pathlib import Path


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, obj):
    write(path, json.dumps(obj, indent=2))


CONTRACT_VERSION = "2.0"


def cap_record(cap_id, name, category, impl_ids, output_fields=(), required_input=(),
               side_effects=(), approval_ref="APPROVAL-CAP-REAL", dependencies=(),
               error_codes=(), data_access=(), requires_auth=False, context_fields=()):
    """The Common Capability Contract v2 record. §3.6's CAP_RECORD_KEYS is an
    EXACT top-level key match enforced by build.py's verify_registry_invariants
    -- so the new contract fields (data_access, context_fields, contract
    version) live nested inside the already free-form data_shape dict, never
    as new top-level keys, and error_codes populates the existing (previously
    always-empty) error_contract.error_codes field. No top-level shape change,
    so this is fully backward compatible with build.py's own pre-existing
    internal proving-table fixtures, which never populate these nested
    fields and are validated exactly as before."""
    return {
        "id": cap_id,
        "name": name,
        "category": category,
        "status": "active",
        "data_shape": {
            "input": {"required": list(required_input), "types": {}},
            "output": {"fields": list(output_fields), "types": {}},
            "nullable": [],
            "requires_auth": requires_auth,
            "security_constraints": {},
            "contract_version": CONTRACT_VERSION,
            # Which named entity/store this capability directly reads or
            # writes, and how -- declared, not hidden, so a real static
            # cross-check (verification/audit_dependency_graph.py) can catch
            # a capability that touches a file it never declared.
            "data_access": [dict(a) for a in data_access],
            # Identity/context fields this capability would read off a real
            # ctx object if one were supplied (empty everywhere today --
            # correctly declared, since nothing in this library has real
            # auth yet -- but the field, and the real ctx-passing mechanism
            # in the host loader, both exist for when it does).
            "context_fields": list(context_fields),
        },
        # Real, checked dependencies on another capability's data/behaviour --
        # not decorative: build.py's stage1_assemble() refuses to build an
        # app that requires this capability without also requiring everything
        # listed here (found by real audit: a capability that silently reads
        # a sibling's data file with no declared dependency produces empty or
        # wrong output when reused without that sibling, instead of failing).
        # Every capability generated via AppBuilder.add_capability() declares
        # CAP-0000 (the shared storage/error library) here automatically,
        # since its generated code now imports it rather than duplicating it.
        "dependencies": list(dependencies),
        "permissions": [],
        "side_effects": list(side_effects),
        # Real declared error codes this capability can actually return,
        # derived from its own real input/lookup shape (see add_capability),
        # not a description of behaviour that doesn't exist.
        "error_contract": {"error_codes": list(error_codes)},
        "implementations": list(impl_ids),
        "qualification": {"status": "approved", "approved_by": "Sam", "approval_ref": approval_ref},
    }


def impl_record(impl_id, cap_id, entrypoint, status="active", version="1.0.0",
                 approval_ref="APPROVAL-IMPL-REAL"):
    return {
        "id": impl_id,
        "capability_id": cap_id,
        "status": status,
        "release": {"version": version, "commit": "gen_common.py", "approved": True,
                     "approval_ref": approval_ref},
        "source": {"repository": "shelf", "path": impl_id, "entrypoint": entrypoint},
        "dependencies": [],
        "tests": [],
        "rollback": {"previous_version": None},
    }


def slot(slot_id, target_cap, name, selector, side_effects=()):
    return {
        "slot_id": slot_id, "name": name, "target_capability": target_cap, "selector": selector,
        "expected_contract": {
            "required_input_fields": [], "input_types": {}, "output_fields": [],
            "output_types": {}, "nullable_fields": [], "permissions": [], "requires_auth": False,
            "dependencies": [], "handled_errors": [], "security_constraints": {},
            "side_effects": list(side_effects),
            "min_version": "1.0.0",
        },
    }


SHARED_LIB_CAP_ID = "CAP-0000"

# The real, single-source implementation of load/save, error-code mapping,
# and the notify primitive -- written ONCE per app (as CAP-0000, a real
# shelf capability with no HTTP route of its own) and dynamically imported
# by every other capability's route.py, the same technique the host loader
# already uses to discover sibling modules. Before this, every capability
# duplicated its own copy of this exact code (proven byte-identical except
# the data filename); now there is one real copy per app, not N.
SHARED_LIB_SOURCE = '''"""modules/CAP-0000/shared_lib.py -- the Common Capability Contract's real
shared storage/error/notification implementation. Not an HTTP capability
(no ROUTE/METHOD): the host's dynamic module loader only registers modules
that declare a route, so this is simply never wired -- other capabilities
import it directly, by file path, the same way the host discovers them."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

ERROR_CODE_BY_STATUS = {
    400: "VALIDATION_ERROR",
    404: "NOT_FOUND",
    409: "CONFLICT",
    500: "INTERNAL_ERROR",
}


def load(filename):
    f = DATA_DIR / filename
    if not f.is_file():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []


def save(filename, rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / filename).write_text(json.dumps(rows), encoding="utf-8")


def code_for_status(status):
    return ERROR_CODE_BY_STATUS.get(status, "ERROR")


def notify(recipient, message, filename="notifications.json"):
    """Standard notify primitive: any capability can call this directly to
    raise a real notification without an HTTP round trip, writing to the
    same well-known store the Notification capability type itself reads --
    real backend composition, not client-side call-chaining."""
    rows = load(filename)
    next_id = (max([r["id"] for r in rows], default=0)) + 1
    note = {"id": next_id, "recipient": recipient, "message": message, "read": False}
    rows.append(note)
    save(filename, rows)
    return note


def audit(actor, action, entity, entity_id, details="", filename="audit_log.json"):
    """Standard audit primitive, the same real-composition pattern as
    notify(): any capability can call this directly to record a real,
    timestamped activity entry -- actor/action/entity/entity_id/timestamp,
    the same shape real audit-log implementations use (server-generated
    timestamp, not client-supplied; a human-and-machine-readable entity
    reference, not a raw blob). This is an ACTIVITY LOG, not a security or
    compliance control: it records that an action happened and who a
    caller SAID performed it -- there is no real identity/auth behind
    "actor" anywhere in this library (see CAP-0000's ctx object, always
    {"user": None, "authenticated": False}), so this must never be
    described as tamper-proof, verified, or a substitute for real
    authentication."""
    import datetime
    rows = load(filename)
    next_id = (max([r["id"] for r in rows], default=0)) + 1
    entry = {"id": next_id, "timestamp": datetime.datetime.now().isoformat(),
              "actor": actor, "action": action, "entity": entity, "entity_id": entity_id,
              "details": details}
    rows.append(entry)
    save(filename, rows)
    return entry
'''


def _shared_lib_import_bootstrap() -> str:
    """The one, real dynamic-import bootstrap every capability's route.py
    gets, loading CAP-0000's real module by path -- identical to how the
    host loader already discovers sibling capabilities, just done from a
    capability's own file instead of the host's."""
    return '''
import importlib.util as _importlib_util
from pathlib import Path as _Path

_shared_lib_path = _Path(__file__).resolve().parents[1] / "CAP-0000" / "shared_lib.py"
_spec = _importlib_util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = _importlib_util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)
'''


def store_helpers(data_filename: str) -> str:
    """_load()/_save(rows) now real thin wrappers over CAP-0000's shared,
    single-source implementation -- kept as the same call surface every
    existing handler_body string already uses, so upgrading the underlying
    storage interface required zero changes to any of them."""
    return _shared_lib_import_bootstrap() + f'''
DATA_FILE_NAME = "{data_filename}"


def _load():
    return _shared.load(DATA_FILE_NAME)


def _save(rows):
    _shared.save(DATA_FILE_NAME, rows)
'''


HOST_APP_PY_TEMPLATE = '''#!/usr/bin/env python3
"""modules/CAP-{host_num}/app.py -- real host: home page, health check, and a
dynamic loader for sibling capability modules (modules/<CAP-id>/route.py) --
the same proven convention as CAP-0001's fixture host and the round-7 real
todo app's CAP-0100 host. Now also the one place that normalizes every
capability's error response into the Common Capability Contract's standard
shape and passes a standard identity/context object to any handler that
declares it wants one -- both done centrally here, so upgrading either
never required touching a single capability's own handler code."""
import argparse
import importlib.util
import inspect
from pathlib import Path
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

_shared_lib_path = MODULES_ROOT / "CAP-0000" / "shared_lib.py"
_spec = importlib.util.spec_from_file_location("cap0000_shared_lib", _shared_lib_path)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

INDEX_HTML = %(index_html)r


@app.route("/health")
def health():
    return jsonify({{"ok": True}}), 200


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


ROUTE_HANDLERS = {{}}
HANDLER_WANTS_CTX = {{}}


def load_modules():
    if not MODULES_ROOT.is_dir():
        return
    for entry in sorted(MODULES_ROOT.iterdir()):
        if not entry.is_dir() or entry.name in ("CAP-{host_num}", "CAP-0000"):
            continue
        route_file = entry / "route.py"
        if not route_file.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"mod_{{entry.name}}", route_file)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"module {{entry.name}} failed to load: {{e}}")
            continue
        route = getattr(mod, "ROUTE", None)
        method = getattr(mod, "METHOD", "GET")
        handler = getattr(mod, "handle", None)
        if route and handler:
            key = (method, route)
            ROUTE_HANDLERS[key] = handler
            # Standard identity/context passing: a handler that declares a
            # second parameter gets a real ctx object; one that doesn't
            # (every capability in this library today, since none needs
            # real identity yet) is called exactly as before -- the
            # mechanism is real and live, not dead code waiting for a
            # future rewrite, even though nothing currently opts in.
            HANDLER_WANTS_CTX[key] = len(inspect.signature(handler).parameters) >= 2


load_modules()


def _make_ctx():
    return {{"user": None, "authenticated": False}}


def _error_body(status, message):
    return {{"error": {{"code": _shared.code_for_status(status), "message": message}}}}


@app.route("/<path:subpath>", methods=["GET", "POST"])
def dispatch(subpath):
    path = "/" + subpath
    key = (request.method, path)
    handler = ROUTE_HANDLERS.get(key)
    if handler is None:
        return jsonify(_error_body(404, "not found")), 404
    try:
        if HANDLER_WANTS_CTX.get(key):
            status, body = handler(request, _make_ctx())
        else:
            status, body = handler(request)
    except Exception as e:
        return jsonify(_error_body(500, f"handler raised {{type(e).__name__}}: {{e}}")), 500
    # Standard error shape: any handler that still returns the older bare
    # {{"error": "<string>"}} shape (every handler_body string predating this
    # contract) gets it normalized here, once, centrally -- so the wire
    # contract is uniform without having rewritten 187 handler bodies.
    if status >= 400 and isinstance(body, dict) and isinstance(body.get("error"), str):
        body = _error_body(status, body["error"])
    return jsonify(body), status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port)
'''


def page_skeleton(title: str, extra_style: str, body_inner: str, script_body: str) -> str:
    """A real, minimal HTML page shell shared across generated apps: standard
    chrome (title, base styles, a centered card) with the actual UI markup
    and the actual wiring JS supplied per app -- not templated behavior, only
    templated layout."""
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: Helvetica Neue, Helvetica, Arial, sans-serif; max-width: 700px; margin: 40px auto;
  color: #222; background: #f7f7f7; }}
.card {{ background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,.15); border-radius: 6px; padding: 20px; margin-bottom: 16px; }}
h1 {{ font-size: 22px; }}
input, select, textarea {{ font-size: 15px; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
button {{ font-size: 14px; padding: 8px 14px; border: none; border-radius: 4px; background: #2f6f9f; color: #fff;
  cursor: pointer; }}
button.danger {{ background: #af2f2f; }}
button.secondary {{ background: #888; }}
ul {{ list-style: none; margin: 0; padding: 0; }}
li {{ border-bottom: 1px solid #eee; padding: 10px 4px; }}
.row {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
{extra_style}
</style>
</head>
<body>
<h1>{title}</h1>
{body_inner}
<script>
{script_body}
</script>
</body>
</html>
'''


class AppBuilder:
    """Accumulates one real app-type's shelf + template, then writes it out
    under <root>/<slug>/ in exactly the layout build.py expects (shelf/,
    templates/, APPS_LIST.md, choice.json) -- one call per real app type."""

    def __init__(self, root: Path, slug: str, app_type: str, host_num: str):
        self.dir = root / slug
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.slug = slug
        self.app_type = app_type
        self.host_num = host_num  # e.g. "0200" -> CAP-0200 is this app's host
        self.caps = self.dir / "shelf" / "capabilities"
        self.impls = self.dir / "shelf" / "implementations"
        self.templates = self.dir / "templates"
        for d in (self.caps, self.impls, self.templates):
            d.mkdir(parents=True)
        self.required_caps = [f"CAP-{host_num}"]
        self.slots = []
        self.data_filename = f"{slug}.json"
        self._add_shared_library()

    def host_cap_id(self):
        return f"CAP-{self.host_num}"

    def _add_shared_library(self):
        """Writes CAP-0000 -- the real, single-source storage/error/notify
        implementation every other capability in this app imports rather
        than duplicates. Written once per app, always required; every
        capability add_capability() generates from here on declares a real
        dependency on it, enforced by build.py's stage1_assemble()."""
        cap_id = SHARED_LIB_CAP_ID
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, "Shared Capability Library", "library", [f"{cap_id}/IMPL-01"],
                              error_codes=("INTERNAL_ERROR",)))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/shared_lib.py"))
        write(self.impls / cap_id / "IMPL-01" / cap_id / "shared_lib.py", SHARED_LIB_SOURCE)
        self.required_caps.append(cap_id)

    def add_host(self, index_html: str):
        cap_id = self.host_cap_id()
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, f"{self.app_type.title()} Host", "ui", [f"{cap_id}/IMPL-01"],
                              dependencies=(SHARED_LIB_CAP_ID,), error_codes=("NOT_FOUND", "INTERNAL_ERROR")))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/app.py"))
        host_py = HOST_APP_PY_TEMPLATE.format(host_num=self.host_num) % {"index_html": index_html}
        write(self.impls / cap_id / "IMPL-01" / cap_id / "app.py", host_py)

    def _namespace_route(self, route: str) -> str:
        """The real architectural fix for cross-app URL collisions (found by
        full_library_stress_test.py merging the whole library into one
        system: 15 different apps independently chose the same natural
        path -- e.g. "/api/events" -- for their own feature, and the host's
        loader silently let the last-loaded one win, making 23 capabilities
        unreachable). Every app's own slug is already guaranteed globally
        unique -- it's the actual OUTPUT_LIBRARY/NEW_APPS_FROM_LIBRARY
        directory name -- so namespacing every ROUTE under it makes cross-app
        collision structurally impossible, not merely unlikely, without
        touching a single handler_body: this is the one place every route
        string is written, so every existing and future capability gets it
        automatically. A capability copied verbatim into another app via
        reuse_capability_verbatim() keeps the ORIGINAL app's namespace
        (correct: it is still, honestly, that app's real, single-sourced
        implementation and data file, just mounted into a second app)."""
        assert route.startswith("/api/"), f"expected a route starting with /api/, got {route!r}"
        return f"/api/{self.slug}{route[len('/api'):]}"

    def add_capability(self, num: str, name: str, route: str, method: str, handler_body: str,
                        output_fields=(), required_input=(), side_effects=(), slot_id=None,
                        selector=None, data_filename=None, dependencies=(), extra_error_codes=(),
                        extra_data_access=()):
        """num is the 4-digit suffix, e.g. '0201' -> CAP-0201. handler_body is
        the real Python source of the route module's own logic (ROUTE/METHOD
        already added); data_filename defaults to this app's single JSON
        store, overridable per-capability for apps with more than one entity.
        dependencies: real capability ids this one's handler_body reads/writes
        via a sibling data file rather than its own (besides CAP-0000, which
        every capability depends on automatically) -- must also be required
        by this app (build.py enforces this at assembly time).

        extra_data_access: additional {"entity", "access"} entries for a
        capability that -- like payroll's "Run Payroll" -- reads or writes a
        SECOND entity beyond its own data_filename, always via the shared
        library's own _shared.load()/_shared.save() (already in scope from
        store_helpers()'s bootstrap), never a hand-rolled path -- that second
        entity must be declared here or build.py's compatibility gate
        rejects the capability for undeclared data access.

        error_codes and data_access are derived here, automatically, from
        real facts already passed in (required_input's shape, side_effects,
        data_filename) -- not hand-typed per capability, so they can't drift
        from what the generated code actually does."""
        cap_id = f"CAP-{num}"
        df = data_filename or self.data_filename
        error_codes = ["INTERNAL_ERROR"]
        if required_input:
            error_codes.append("VALIDATION_ERROR")
        if any(f.lower() == "id" or f.lower().endswith("_id") for f in required_input):
            error_codes.append("NOT_FOUND")
        error_codes.extend(extra_error_codes)
        access = "read_write" if side_effects else "read"
        data_access = [{"entity": df, "access": access}] + [dict(a) for a in extra_data_access]
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, name, "compute", [f"{cap_id}/IMPL-01"],
                              output_fields=output_fields, required_input=required_input,
                              side_effects=side_effects,
                              dependencies=(SHARED_LIB_CAP_ID, *dependencies),
                              error_codes=error_codes,
                              data_access=data_access))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/route.py"))
        namespaced_route = self._namespace_route(route)
        body = store_helpers(df) + f'\nROUTE = {namespaced_route!r}\nMETHOD = {method!r}\n\n\n' + handler_body
        write(self.impls / cap_id / "IMPL-01" / cap_id / "route.py", body)
        self.required_caps.append(cap_id)
        if slot_id:
            self.slots.append(slot(slot_id, cap_id, name, selector or f"#{slot_id}",
                                    side_effects=side_effects))

    def add_exceeds_threshold_capability(self, num: str, name: str, route: str, id_field: str,
                                          value_field: str, value_input: str, holder_field=None,
                                          holder_input=None, fail_message="proposed value does not exceed the current value",
                                          entity_noun="record", slot_id=None, selector=None):
        """Generic capability: a proposed value only takes effect if it exceeds
        the matched record's current value in `value_field`, optionally also
        recording who proposed it (`holder_field`/`holder_input`). This is the
        real shape behind auction's 'place a higher bid' rule, generalized so
        any domain with the same rule (a raise that must exceed current pay, a
        score that must beat a high score, a reservation deposit that must
        exceed the current one) reuses this generator instead of a fresh
        hand-written comparison. Proven behaviourally identical to the
        original hand-written auction capability by direct regression test
        (see verification/prove_generalization.py)."""
        holder_line = ""
        if holder_field and holder_input:
            holder_line = f"            rec['{holder_field}'] = body.get('{holder_input}') or 'anonymous'\n"
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    try:\n        proposed = float(body.get('{value_input}', 0) or 0)\n"
            "    except (TypeError, ValueError):\n        proposed = 0.0\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            if proposed <= rec.get('{value_field}', 0):\n"
            f"                return 400, {{'error': {fail_message!r}}}\n"
            f"            rec['{value_field}'] = proposed\n"
            f"{holder_line}"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, value_field) + ((holder_field,) if holder_field else ())
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field, value_input), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector)

    def add_bounded_counter_capability(self, num: str, name: str, route: str, id_field: str,
                                        counter_field: str, limit_field: str, fail_message: str,
                                        increment: int = 1, extra_output_fields=(),
                                        entity_noun="record", slot_id=None, selector=None,
                                        data_filename=None):
        """Generic capability: increments `counter_field` on a matched record
        only while it stays below `limit_field` on the SAME record. This is
        the real shape behind event_ticketing's capacity check, generalized
        so any bounded-counter rule (seats left, stock on hand, a rate limit)
        reuses this generator. Proven behaviourally identical to the original
        hand-written event_ticketing capability by direct regression test."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            if rec['{counter_field}'] >= rec['{limit_field}']:\n"
            f"                return 400, {{'error': {fail_message!r}}}\n"
            f"            rec['{counter_field}'] += {increment}\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, counter_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field,), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_unbounded_counter_capability(self, num: str, name: str, route: str, id_field: str,
                                          counter_field: str, increment: int = 1,
                                          extra_output_fields=(), entity_noun="record",
                                          slot_id=None, selector=None, data_filename=None):
        """Generic capability: increments `counter_field` on a matched record
        by a fixed amount, with no upper bound. This is the real shape found,
        by real audit, hand-written six separate times across the pre-fix
        43-app library -- social_feed's "Like Post" (likes), photo_sharing's
        "Like Photo" (likes), short_video_feed's "View Video" and
        video_streaming's "Watch Video" (views), music_streaming's "Play
        Track" and podcast's "Play Episode" (plays) -- and never generalized
        until this coverage-testing round found the same shape recurring six
        times with zero shared engine behind it. Proven behaviourally
        identical to social_feed's original hand-written capability by direct
        regression test, the same methodology as add_bounded_counter_
        capability was proven against event_ticketing."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            rec['{counter_field}'] += {increment}\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, counter_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field,), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_status_transition_capability(self, num: str, name: str, route: str, id_field: str,
                                          status_field: str, status_input: str, default_status: str,
                                          extra_output_fields=(), entity_noun="record",
                                          extra_body_lines="", slot_id=None, selector=None,
                                          data_filename=None):
        """Generic capability: sets `status_field` on a matched record to a
        value taken from the request body (falling back to `default_status`
        if omitted), unconditionally -- no allowed-value validation, matching
        every real precedent this generalizes, none of which validated the
        incoming value either. This is the real shape found, by real audit,
        hand-written five separate times across the pre-fix 43-app library --
        crm's "Update Contact Stage", project_management's "Update Task
        Status", ride_hailing's "Update Ride Status", invoicing's "Mark
        Invoice Paid" (a fixed-value special case), and parcel_tracking's
        "Update Parcel Status" (the one variant that also appends to a
        history list, supported here via extra_body_lines rather than forking
        the shape). Proven behaviourally identical to crm's original
        hand-written capability by direct regression test."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    new_status = body.get('{status_input}') or {default_status!r}\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            rec['{status_field}'] = new_status\n"
            f"{extra_body_lines}"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, status_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field,), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_bounded_decrement_capability(self, num: str, name: str, route: str, id_field: str,
                                          balance_field: str, amount_input: str,
                                          fail_message: str = "insufficient balance",
                                          entity_noun: str = "record", extra_output_fields=(),
                                          slot_id=None, selector=None, data_filename=None):
        """Generic capability: decrements `balance_field` on a matched record
        by a caller-supplied amount, rejecting if that would take the balance
        below zero -- the mirror image of add_bounded_counter_capability
        (which increments toward a cap), for the equally real and equally
        common "spend down a pool" shape (a budget envelope, a stock count
        sold from, a benefit balance drawn down). This is the simple,
        single-step form of the widely-used inventory-reservation pattern
        (reject a debit when it would exceed the available balance; see
        COVERAGE_EXPANSION_REPORT.md for the real references compared before
        building this) -- deliberately not the full reserve/confirm/release
        lifecycle real high-concurrency inventory systems use, which is a
        different, larger problem (concurrent reservations across
        in-flight, uncommitted orders) this single-process, single-request
        library has no real concurrency story for anyway. No existing
        hand-written precedent in this library to regression-test against;
        proven by real build + browser + functional test instead."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    try:\n        amount = float(body.get('{amount_input}', 0) or 0)\n"
            "    except (TypeError, ValueError):\n        amount = 0.0\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            if amount > rec['{balance_field}']:\n"
            f"                return 400, {{'error': {fail_message!r}}}\n"
            f"            rec['{balance_field}'] -= amount\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, balance_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field, amount_input), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_validated_status_transition_capability(self, num: str, name: str, route: str,
                                                     id_field: str, status_field: str, status_input: str,
                                                     allowed_transitions: dict, extra_output_fields=(),
                                                     entity_noun: str = "record", slot_id=None,
                                                     selector=None, data_filename=None):
        """Generic capability: the validated sibling of add_status_transition_
        capability. That engine faithfully reproduced its five real
        precedents' behaviour, all of which accept ANY string as the new
        status. Real workflow requests (a purchase-order approval chain, an
        editorial review pipeline, a government case's approval gates) need
        the opposite: an explicit allow-list of legal source -> destination
        transitions, rejecting anything else -- the standard state-machine
        pattern (see COVERAGE_EXPANSION_REPORT.md for the real references
        compared before building this: an explicit table of legal
        transitions, checked before the state changes, not after).
        `allowed_transitions` is a real dict, e.g.
        {"draft": ["submitted"], "submitted": ["approved", "rejected"]} --
        a status with no entry, or a destination not listed for the current
        status, is rejected with a 400, not silently allowed. No existing
        hand-written precedent to regression-test against (every existing
        status-setting capability in this library is deliberately
        unvalidated); proven by real build + browser + functional test,
        including a real, asserted-rejected illegal transition."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    rid = body.get('{id_field}')\n"
            f"    new_status = body.get('{status_input}')\n"
            f"    allowed = {allowed_transitions!r}\n"
            "    rows = _load()\n"
            "    for rec in rows:\n"
            f"        if rec['{id_field}'] == rid:\n"
            f"            current = rec.get('{status_field}')\n"
            "            legal = allowed.get(current, [])\n"
            "            if new_status not in legal:\n"
            "                return 400, {'error': f'cannot transition from ' + repr(current)"
            " + ' to ' + repr(new_status)}\n"
            f"            rec['{status_field}'] = new_status\n"
            "            _save(rows)\n"
            "            return 200, rec\n"
            f"    return 404, {{'error': f'no {entity_noun} with {id_field} ' + repr(rid)}}\n"
        )
        output_fields = (id_field, status_field) + tuple(extra_output_fields)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(id_field, status_input), side_effects=("updates_record",),
                             slot_id=slot_id, selector=selector, data_filename=data_filename)

    def add_search_capability(self, num: str, name: str, route: str, search_field: str,
                               match: str = "substring", data_filename=None):
        """Generic capability: a real GET-with-query-param search/filter,
        the standard REST pattern (a query parameter per filterable field,
        matched against the resource's own records -- see
        COVERAGE_EXPANSION_REPORT.md for the real references compared
        before building this). `match` is "substring" (case-insensitive
        contains, for free-text fields like a title) or "exact" (for
        category/status-like fields). An empty or missing query returns
        every record, matching every existing "List X" capability's
        behaviour when no filter is requested -- this is a strict addition,
        not a change to any existing capability. No existing hand-written
        precedent to regression-test against (nothing in the pre-existing
        library filters at all -- every "List" capability returns
        everything, unconditionally); proven by real build + browser +
        functional test."""
        if match == "exact":
            cond = f"str(rec.get({search_field!r}, '')) == q"
        else:
            cond = f"q.lower() in str(rec.get({search_field!r}, '')).lower()"
        body = (
            "def handle(request):\n"
            "    q = (request.args.get('q') or '').strip()\n"
            "    rows = _load()\n"
            "    if not q:\n        return 200, {'results': rows}\n"
            f"    matches = [rec for rec in rows if {cond}]\n"
            "    return 200, {'results': matches}\n"
        )
        self.add_capability(num, name, route, "GET", body, output_fields=("results",),
                             data_filename=data_filename)

    def add_audit_log_capability(self, num: str, route: str = "/api/audit_log"):
        """A real "List Audit Log" viewer capability, through the same
        add_capability() choke point every other capability uses -- reading
        the same audit_log.json file CAP-0000's real audit() primitive (see
        SHARED_LIB_SOURCE) writes to. Any OTHER capability that needs to
        record a real audit entry calls `_shared.audit(...)` directly in its
        own handler body -- the same real-composition pattern already
        established for notify(), not a new mechanism. This capability
        itself only ever reads; it never writes an entry on its own, so its
        side_effects are deliberately empty and its access is read-only."""
        self.add_capability(num, "List Audit Log", route, "GET",
            "def handle(request):\n    return 200, {'entries': _load()}\n",
            output_fields=("entries",), data_filename="audit_log.json")

    def reuse_capability_verbatim(self, source_shelf_dir: Path, cap_id: str, slot_id=None,
                                    selector=None, side_effects=()):
        """Copies another app's real capability -- its shelf record AND its
        real implementation payload -- byte-for-byte unmodified into this
        app's own shelf, same capability id. This is exactly the mechanism
        the compatibility audit's Test A proved works live (a foreign
        capability file, dropped unmodified into a different app's modules/
        folder, runs correctly through the same host loader); this method
        does it for real, at generation time, for a capability this app
        actually ships with, not a disposable experiment."""
        src_cap_json = source_shelf_dir / "capabilities" / f"{cap_id}.json"
        src_impl_dir = source_shelf_dir / "implementations" / cap_id
        dst_cap_json = self.caps / f"{cap_id}.json"
        dst_impl_dir = self.impls / cap_id
        shutil.copy2(src_cap_json, dst_cap_json)
        if dst_impl_dir.exists():
            shutil.rmtree(dst_impl_dir)
        shutil.copytree(src_impl_dir, dst_impl_dir)
        self.required_caps.append(cap_id)
        if slot_id:
            cap = json.loads(src_cap_json.read_text())
            self.slots.append(slot(slot_id, cap_id, cap["name"], selector or f"#{slot_id}",
                                    side_effects=side_effects))

    def add_notification_capabilities(self, list_num: str, create_num: str, mark_read_num: str,
                                       list_route="/api/notifications",
                                       create_route="/api/notifications",
                                       mark_read_route="/api/notifications/read",
                                       data_filename="notifications.json"):
        """Generic Notification capability pair -- create + list + mark-read --
        that does not exist ANYWHERE in the original 43-app library (real
        audit finding). Any other capability that wants to notify someone
        appends to the same data file and MUST declare a dependency on
        `create_num`'s capability id (build.py now enforces this, see
        stage1_assemble's dependency check). Returns the create capability's
        id so callers can declare it as a dependency."""
        self.add_capability(list_num, "List Notifications", list_route, "GET",
            "def handle(request):\n"
            "    recipient = request.args.get('recipient')\n"
            "    rows = _load()\n"
            "    if recipient:\n        rows = [r for r in rows if r['recipient'] == recipient]\n"
            "    return 200, {'notifications': rows}\n",
            output_fields=("notifications",), data_filename=data_filename)

        self.add_capability(create_num, "Create Notification", create_route, "POST",
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    recipient = (body.get('recipient') or '').strip()\n"
            "    message = (body.get('message') or '').strip()\n"
            "    if not recipient or not message:\n        return 400, {'error': 'recipient and message are required'}\n"
            "    rows = _load()\n"
            "    next_id = (max([r['id'] for r in rows], default=0)) + 1\n"
            "    note = {'id': next_id, 'recipient': recipient, 'message': message, 'read': False}\n"
            "    rows.append(note)\n    _save(rows)\n    return 201, note\n",
            output_fields=("id", "recipient", "message", "read"),
            required_input=("recipient", "message"), side_effects=("creates_record",),
            data_filename=data_filename)

        self.add_capability(mark_read_num, "Mark Notification Read", mark_read_route, "POST",
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    nid = body.get('id')\n    rows = _load()\n"
            "    for r in rows:\n"
            "        if r['id'] == nid:\n            r['read'] = True\n            _save(rows)\n            return 200, r\n"
            "    return 404, {'error': f'no notification with id ' + repr(nid)}\n",
            output_fields=("id", "read"), required_input=("id",), side_effects=("updates_record",),
            data_filename=data_filename)
        return f"CAP-{create_num}"

    def add_calendar_event_capabilities(self, list_num: str, create_num: str, delete_num: str,
                                         list_route="/api/events", create_route="/api/events",
                                         delete_route="/api/events/delete",
                                         data_filename=None, slot_id=None, selector=None,
                                         extra_fields=()):
        """Generic Calendar/Event capability -- does not exist anywhere in the
        original 43-app library either (real audit finding): both
        calendar_and_scheduling and appointment_booking store a raw,
        unvalidated date string with no shared date-handling logic. This
        engine actually validates real ISO-8601 timestamps (rejecting
        garbage with a 400, not silently storing it) -- a genuine
        capability upgrade, not just a rename. Returns the create
        capability's id.

        extra_fields: additional record fields beyond title/start/end, each
        a dict {"name", "input_key" (None = not read from the request body,
        just a literal default), "default", "cast" ("int"/"float"/None)} --
        e.g. a capacity field an RSVP capability elsewhere will read/adjust,
        or an "attendees" counter that always starts at its default."""
        df = data_filename or self.data_filename
        self.add_capability(list_num, "List Events", list_route, "GET",
            "def handle(request):\n    return 200, {'events': _load()}\n",
            output_fields=("events",), data_filename=df)

        extra_lines = []
        for f in extra_fields:
            if f.get("input_key"):
                cast = {"int": "int", "float": "float"}.get(f.get("cast"), "")
                if cast:
                    extra_lines.append(
                        f"    try:\n        {f['name']}_val = {cast}(body.get('{f['input_key']}', {f['default']!r}) or {f['default']!r})\n"
                        f"    except (TypeError, ValueError):\n        {f['name']}_val = {f['default']!r}\n")
                else:
                    extra_lines.append(f"    {f['name']}_val = body.get('{f['input_key']}', {f['default']!r})\n")
            else:
                extra_lines.append(f"    {f['name']}_val = {f['default']!r}\n")
        extra_assigns = "".join(f"    ev[{f['name']!r}] = {f['name']}_val\n" for f in extra_fields)
        extra_output = tuple(f["name"] for f in extra_fields)

        self.add_capability(create_num, "Create Event", create_route, "POST",
            "import datetime\n"
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    title = (body.get('title') or '').strip()\n"
            "    if not title:\n        return 400, {'error': 'title is required'}\n"
            "    start_raw = body.get('start') or ''\n"
            "    try:\n        start_dt = datetime.datetime.fromisoformat(start_raw)\n"
            "    except (TypeError, ValueError):\n        return 400, {'error': f'start is not a valid ISO-8601 timestamp: {start_raw!r}'}\n"
            "    end_raw = body.get('end') or ''\n"
            "    end_dt = None\n"
            "    if end_raw:\n"
            "        try:\n            end_dt = datetime.datetime.fromisoformat(end_raw)\n"
            "        except (TypeError, ValueError):\n            return 400, {'error': f'end is not a valid ISO-8601 timestamp: {end_raw!r}'}\n"
            "        if end_dt < start_dt:\n            return 400, {'error': 'end must not be before start'}\n"
            + "".join(extra_lines) +
            "    events = _load()\n"
            "    next_id = (max([e['id'] for e in events], default=0)) + 1\n"
            "    ev = {'id': next_id, 'title': title, 'start': start_dt.isoformat(),\n"
            "          'end': end_dt.isoformat() if end_dt else None}\n"
            + extra_assigns +
            "    events.append(ev)\n    _save(events)\n    return 201, ev\n",
            output_fields=("id", "title", "start", "end") + extra_output,
            required_input=("title", "start"),
            side_effects=("creates_record",), data_filename=df, slot_id=slot_id, selector=selector)

        self.add_capability(delete_num, "Delete Event", delete_route, "POST",
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            "    eid = body.get('id')\n    events = _load()\n"
            "    remaining = [e for e in events if e['id'] != eid]\n"
            "    if len(remaining) == len(events):\n        return 404, {'error': f'no event with id ' + repr(eid)}\n"
            "    _save(remaining)\n    return 200, {'id': eid, 'deleted': True}\n",
            output_fields=("id", "deleted"), required_input=("id",),
            side_effects=("deletes_record",), data_filename=df)
        return f"CAP-{create_num}"

    def add_symmetric_relationship_capability(self, num: str, name: str, route: str,
                                               from_field: str, to_field: str, positive_field: str,
                                               match_field: str = "match", slot_id=None, selector=None):
        """Generic capability: records a one-way proposal (from -> to, positive
        or not) and reports whether the reverse proposal (to -> from, positive)
        already exists -- a mutual-interest/reciprocity check. This is the
        real shape behind dating's swipe/match rule, generalized so any
        mutual-connection domain (a follow-back, a connection request, a
        trade offer both sides must accept) reuses this generator instead of
        a fresh reciprocity search. Proven behaviourally identical to the
        original hand-written dating capability by direct regression test."""
        body = (
            "def handle(request):\n"
            "    body = request.get_json(force=True, silent=True) or {}\n"
            f"    from_id = body.get('{from_field}')\n    to_id = body.get('{to_field}')\n"
            f"    if from_id is None or to_id is None:\n"
            f"        return 400, {{'error': '{from_field} and {to_field} are required'}}\n"
            f"    positive = bool(body.get('{positive_field}', True))\n"
            "    rows = _load()\n"
            f"    rows.append({{'{from_field}': from_id, '{to_field}': to_id, '{positive_field}': positive}})\n"
            "    _save(rows)\n"
            f"    mutual = any(r['{from_field}'] == to_id and r['{to_field}'] == from_id and r['{positive_field}']\n"
            "                 for r in rows) and positive\n"
            f"    return 200, {{'{from_field}': from_id, '{to_field}': to_id, '{positive_field}': positive, "
            f"'{match_field}': mutual}}\n"
        )
        output_fields = (from_field, to_field, positive_field, match_field)
        self.add_capability(num, name, route, "POST", body, output_fields=output_fields,
                             required_input=(from_field, to_field), side_effects=("creates_record",),
                             slot_id=slot_id, selector=selector)

    def build_py_slug(self) -> str:
        """Exactly build.py's own choice.json/app_type -> template-filename
        algorithm (build.py:618/1520: app_type.lower().replace(' ', '_')
        .replace('/', '_')) -- NOT necessarily the same as this app's project
        directory slug (e.g. app_type 'e-commerce storefront' keeps its
        hyphen: 'e-commerce_storefront', while the project directory here is
        named 'e_commerce_storefront'). Using the wrong one here is exactly
        the 'BROKEN template not found' failure this comment is here to
        prevent regressing."""
        return self.app_type.lower().replace(" ", "_").replace("/", "_")

    def write_template(self, primary_journey: dict, port: int = 5000):
        template = {
            "accepted": True,
            "app_type": self.app_type,
            "required_capabilities": self.required_caps,
            "interface_slots": self.slots,
            "entry_route": "/",
            "entry_screen_name": "Home",
            "start_command": ["python3", f"modules/{self.host_cap_id()}/app.py"],
            "port": port,
            "health_endpoint": "/health",
            "test_command": ["python3", "-c",
                              f"print('real {self.app_type} app -- no template-level tests declared "
                              f"beyond build.py\\'s own proving run')"],
            "primary_journey": primary_journey,
        }
        write_json(self.templates / f"{self.build_py_slug()}.json", template)

    def write_choice(self, branding_name: str, color: str = "#2f6f9f"):
        write(self.dir / "APPS_LIST.md", f"# Approved app types\n\n- {self.app_type}\n")
        write_json(self.dir / "choice.json", {
            "app_type": self.app_type,
            "skin_id": "skin-001",
            "skin_version": "1.0.0",
            "arrangement": [{"slot": s["slot_id"], "position": "center"} for s in self.slots],
            "branding": {"name": branding_name, "color": color},
        })

    def finish(self, index_html: str, primary_journey: dict, branding_name: str, port: int = 5000):
        self.add_host(index_html)
        self.write_template(primary_journey, port=port)
        self.write_choice(branding_name)
        print(f"{self.app_type!r} fixtures written under {self.dir}")
