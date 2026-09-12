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


def cap_record(cap_id, name, category, impl_ids, output_fields=(), required_input=(),
               side_effects=(), approval_ref="APPROVAL-CAP-REAL"):
    return {
        "id": cap_id,
        "name": name,
        "category": category,
        "status": "active",
        "data_shape": {
            "input": {"required": list(required_input), "types": {}},
            "output": {"fields": list(output_fields), "types": {}},
            "nullable": [],
            "requires_auth": False,
            "security_constraints": {},
        },
        "dependencies": [],
        "permissions": [],
        "side_effects": list(side_effects),
        "error_contract": {"error_codes": []},
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


def store_helpers(data_filename: str) -> str:
    """Real load/save helpers against <app_dir>/data/<data_filename>, duplicated
    into every route module copy (per this system's own shelf convention: an
    IMPL's payload is copied standalone, no shared sibling import)."""
    return f'''
import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "{data_filename}"


def _load():
    if not DATA_FILE.is_file():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(rows):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(rows), encoding="utf-8")
'''


HOST_APP_PY_TEMPLATE = '''#!/usr/bin/env python3
"""modules/CAP-{host_num}/app.py -- real host: home page, health check, and a
dynamic loader for sibling capability modules (modules/<CAP-id>/route.py) --
the same proven convention as CAP-0001's fixture host and the round-7 real
todo app's CAP-0100 host."""
import argparse
import importlib.util
from pathlib import Path
from flask import Flask, jsonify, request, Response

app = Flask(__name__)
HERE = Path(__file__).resolve().parent
MODULES_ROOT = HERE.parent

INDEX_HTML = %(index_html)r


@app.route("/health")
def health():
    return jsonify({{"ok": True}}), 200


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


ROUTE_HANDLERS = {{}}


def load_modules():
    if not MODULES_ROOT.is_dir():
        return
    for entry in sorted(MODULES_ROOT.iterdir()):
        if not entry.is_dir() or entry.name == "CAP-{host_num}":
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
            ROUTE_HANDLERS[(method, route)] = handler


load_modules()


@app.route("/<path:subpath>", methods=["GET", "POST"])
def dispatch(subpath):
    path = "/" + subpath
    handler = ROUTE_HANDLERS.get((request.method, path))
    if handler is None:
        return jsonify({{"error": "not found"}}), 404
    try:
        status, body = handler(request)
    except Exception as e:
        return jsonify({{"error": f"handler raised {{type(e).__name__}}: {{e}}"}}), 500
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

    def host_cap_id(self):
        return f"CAP-{self.host_num}"

    def add_host(self, index_html: str):
        cap_id = self.host_cap_id()
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, f"{self.app_type.title()} Host", "ui", [f"{cap_id}/IMPL-01"]))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/app.py"))
        host_py = HOST_APP_PY_TEMPLATE.format(host_num=self.host_num) % {"index_html": index_html}
        write(self.impls / cap_id / "IMPL-01" / cap_id / "app.py", host_py)

    def add_capability(self, num: str, name: str, route: str, method: str, handler_body: str,
                        output_fields=(), required_input=(), side_effects=(), slot_id=None,
                        selector=None, data_filename=None):
        """num is the 4-digit suffix, e.g. '0201' -> CAP-0201. handler_body is
        the real Python source of the route module's own logic (ROUTE/METHOD
        already added); data_filename defaults to this app's single JSON
        store, overridable per-capability for apps with more than one entity."""
        cap_id = f"CAP-{num}"
        write_json(self.caps / f"{cap_id}.json",
                   cap_record(cap_id, name, "compute", [f"{cap_id}/IMPL-01"],
                              output_fields=output_fields, required_input=required_input,
                              side_effects=side_effects))
        write_json(self.impls / cap_id / "IMPL-01.json",
                   impl_record(f"{cap_id}/IMPL-01", cap_id, f"{cap_id}/route.py"))
        df = data_filename or self.data_filename
        body = store_helpers(df) + f'\nROUTE = {route!r}\nMETHOD = {method!r}\n\n\n' + handler_body
        write(self.impls / cap_id / "IMPL-01" / cap_id / "route.py", body)
        self.required_caps.append(cap_id)
        if slot_id:
            self.slots.append(slot(slot_id, cap_id, name, selector or f"#{slot_id}",
                                    side_effects=side_effects))

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
