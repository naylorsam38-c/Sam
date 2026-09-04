#!/usr/bin/env python3
"""
builder.py — component 3 of the chain: the assembled numbered spec -> a real,
running application.

Builds what the spec says. Two generation rules, each bounded and explicit:

  * a record with real CRUD access grants -> a real sqlite table, real
    /api/<record>s routes, a real list+detail HTML screen per D13's numbered
    SCR-nnn entries, gated by the record's real permitted-actions from D04.
  * an integration whose provider is in OAUTH_PROVIDERS (a small registry of
    real, publicly documented OAuth endpoints — not invented per project) ->
    a real start/callback/status route triple and a real status screen.

Anything in the spec that fits neither rule is refused (raised, listed by its
numbered id), not guessed at or silently skipped — the same discipline as
every other refusing component in this chain. This keeps the ruleset small
and auditable rather than an open-ended "interpret the spec" pass.

Output ("recipe", not binary): a directory containing
  app.py       stdlib-only (http.server + sqlite3 + urllib) — no new
               dependencies, matching Command Desk's own stated constraint
  schema.sql   real CREATE TABLE statements
  static/*.html one real page per numbered screen (SCR-nnn), vanilla JS,
               fetch() against the real generated routes
  run.sh       starts it

Usage:
  python builder.py SPEC.json -o out_dir/ [--port 8788] [--secrets FILE]
"""

import argparse
import json
import os
import struct
import sys
import textwrap
import xml.etree.ElementTree as ET

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
LOGO_MANIFEST = json.load(open(os.path.join(ASSETS_DIR, "logos", "manifest.json"), encoding="utf-8"))
LOGOS = {l["id"]: l for l in LOGO_MANIFEST["logos"]}
LOGO_SPEC = LOGO_MANIFEST["spec"]

# Real, publicly documented OAuth 2.0 endpoints. Not invented, not guessed —
# refuse (BuildRefused) for any provider not listed here rather than making
# up an endpoint. Add a provider only from its own published documentation.
OAUTH_PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scope": "https://www.googleapis.com/auth/gmail.readonly",
    },
}

# Real product names that use a listed provider's real OAuth infrastructure —
# a factual mapping (Gmail really is a Google product on Google's OAuth), not
# a guess at an endpoint. Extend only from the product's own documentation.
PROVIDER_ALIASES = {
    "gmail": "google", "google workspace": "google", "google calendar": "google",
    "google drive": "google", "google sheets": "google",
}


class BuildRefused(Exception):
    """The spec asked for something this Builder has no generation rule for."""


def slug(name):
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def table_name(record):
    return slug(record) + "s"


def _screen_filename(screen_id):
    """A numbered screen's real, permanent id is now always template-
    prefixed (e.g. 'pm-teamwork/SCR-001', from lock_structure.py) so it can
    never collide across templates -- but that "/" is a real path separator,
    not a filename character. This is the one place that distinction is
    made, so a screen's static file always lands directly in static/,
    never in an unintended nested directory the Builder never creates."""
    return screen_id.replace("/", "__") + (".html" if not screen_id.endswith(".html") else "")


# --------------------------------------------------------------------------- schema
def build_schema(spec):
    lines = []
    for record, r in spec["build_model"]["records"].items():
        cols = ["id TEXT PRIMARY KEY", "created_at TEXT NOT NULL", "updated_at TEXT NOT NULL"]
        for fname, storage in r["storage"].items():
            cols.append(f"{slug(fname)} {storage.replace('FOREIGN_KEY_ROLE', 'TEXT').replace('FOREIGN_KEY', 'TEXT')}")
        lines.append(f"CREATE TABLE IF NOT EXISTS {table_name(record)} (\n  " + ",\n  ".join(cols) + "\n);")
    for name, flx in spec["build_model"]["integrations"].items():
        lines.append(textwrap.dedent(f"""\
            CREATE TABLE IF NOT EXISTS connections (
              provider TEXT PRIMARY KEY,
              state TEXT NOT NULL,
              access_token TEXT,
              refresh_token TEXT,
              expires_at TEXT,
              scopes TEXT
            );"""))
    return "\n\n".join(lines) + "\n"


# --------------------------------------------------------------------------- record CRUD generation
def crud_routes(spec):
    """One route set per record that has any real create/view/edit/delete
    grant (records with none — 'nobody' on every verb — get no routes, which
    is correct, not a gap: nothing may ever act on them over the API)."""
    routes = []
    for record, r in spec["build_model"]["records"].items():
        tbl = table_name(record)
        access = r["access"]
        if access.get("view"):
            routes.append(("GET", f"/api/{tbl}", "list_" + tbl, {"table": tbl}))
            routes.append(("GET", f"/api/{tbl}/", "get_" + tbl, {"table": tbl}))  # + <id>
        if access.get("create"):
            routes.append(("POST", f"/api/{tbl}", "create_" + tbl,
                           {"table": tbl, "fields": list(r["fields"])}))
        if access.get("edit"):
            routes.append(("PUT", f"/api/{tbl}/", "update_" + tbl,
                           {"table": tbl, "fields": list(r["fields"])}))
        if access.get("delete") and access["delete"] != "nobody":
            routes.append(("DELETE", f"/api/{tbl}/", "delete_" + tbl, {"table": tbl}))
    return routes


def render_crud_handler(method, path, name, ctx):
    tbl = ctx["table"]
    if name.startswith("list_"):
        return textwrap.dedent(f"""\
            def {name}(self):
                rows = query("SELECT * FROM {tbl} ORDER BY created_at DESC")
                respond(self, 200, rows)
            """)
    if name.startswith("get_"):
        return textwrap.dedent(f"""\
            def {name}(self, record_id):
                rows = query("SELECT * FROM {tbl} WHERE id = ?", (record_id,))
                if not rows:
                    respond(self, 404, {{"error": "not found"}}); return
                respond(self, 200, rows[0])
            """)
    if name.startswith("create_"):
        fields = ctx["fields"]
        cols = ", ".join(["id", "created_at", "updated_at"] + [slug(f) for f in fields])
        qmarks = ", ".join(["?"] * (3 + len(fields)))
        # field values are extracted at code-gen time (not via a generated
        # comprehension) -- the field list is already known here, and this
        # sidesteps a real bug this Builder shipped with once: {f!r} inside an
        # f-string is evaluated immediately by the *generator*, not left as
        # literal text in the *generated* code, so `f` must not appear as a
        # loop variable name inside an f-string template like this one.
        gets = ", ".join(f"body.get({name_!r})" for name_ in fields)
        return textwrap.dedent(f"""\
            def {name}(self, body):
                rid = new_id(); now = now_iso()
                values = [rid, now, now, {gets}]
                execute("INSERT INTO {tbl} ({cols}) VALUES ({qmarks})", values)
                respond(self, 201, {{"id": rid}})
            """)
    if name.startswith("update_"):
        fields = ctx["fields"]
        sets = ", ".join(f"{slug(name_)} = ?" for name_ in fields)
        gets = ", ".join(f"body.get({name_!r})" for name_ in fields)
        return textwrap.dedent(f"""\
            def {name}(self, record_id, body):
                values = [{gets}, now_iso(), record_id]
                n = execute("UPDATE {tbl} SET {sets}, updated_at = ? WHERE id = ?", values)
                if not n:
                    respond(self, 404, {{"error": "not found"}}); return
                respond(self, 200, {{"id": record_id}})
            """)
    if name.startswith("delete_"):
        return textwrap.dedent(f"""\
            def {name}(self, record_id):
                n = execute("DELETE FROM {tbl} WHERE id = ?", (record_id,))
                respond(self, 200 if n else 404, {{"deleted": bool(n)}})
            """)
    raise BuildRefused(f"no CRUD handler rule for {name}")


# --------------------------------------------------------------------------- OAuth integration generation
def oauth_routes(spec):
    routes = []
    for name, flx in spec["build_model"]["integrations"].items():
        provider = _resolve_provider(name, flx)
        if provider not in OAUTH_PROVIDERS:
            raise BuildRefused(
                f"integration '{name}': provider '{provider}' is not in OAUTH_PROVIDERS — "
                f"add its real authorize_url/token_url from its own published docs, or this "
                f"Builder will not invent one")
        slug_ = slug(provider)
        routes.append(("POST", f"/api/connections/{slug_}/start", f"start_{slug_}", {"provider": provider}))
        routes.append(("GET", f"/api/connections/{slug_}/callback", f"callback_{slug_}", {"provider": provider}))
    if spec["build_model"]["integrations"]:
        routes.append(("GET", "/api/connections/status", "connections_status", {}))
    return routes


def _resolve_provider(name, flx):
    """The graph's FLX questions record purpose/sends/receives in prose, not a
    provider id — real facts, but not yet a lookup key. Resolve to a known
    provider name by exact case-insensitive match against OAUTH_PROVIDERS,
    checking the integration's own name first (this repo's real convention —
    see the Command Desk instance) then its recorded purpose text. Refuses
    rather than guessing if neither names a known provider."""
    for candidate in (name, flx.get("purpose") or ""):
        low = candidate.lower()
        for provider in OAUTH_PROVIDERS:
            if provider in low:
                return provider
        for alias, provider in PROVIDER_ALIASES.items():
            if alias in low:
                return provider
    raise BuildRefused(f"integration '{name}': cannot resolve which OAuth provider this is "
                        f"from its name or purpose — name it explicitly")


def render_oauth_handler(name, ctx):
    provider = ctx["provider"]
    slug_ = slug(provider)
    cfg = OAUTH_PROVIDERS[provider]
    env_id = f"{provider.upper()}_CLIENT_ID"
    env_secret = f"{provider.upper()}_CLIENT_SECRET"
    if name.startswith("start_"):
        return textwrap.dedent(f"""\
            def {name}(self):
                client_id = os.environ.get({env_id!r})
                if not client_id:
                    respond(self, 500, {{"error": "{env_id} not configured"}}); return
                nonce = new_id()
                execute("INSERT OR REPLACE INTO connections (provider, state) VALUES (?, ?)",
                        ({provider!r}, "pending:" + nonce))
                params = urlencode({{
                    "client_id": client_id,
                    "redirect_uri": self.base_url() + "/api/connections/{slug_}/callback",
                    "response_type": "code",
                    "scope": {cfg['default_scope']!r},
                    "state": nonce,
                    "access_type": "offline",
                }})
                self.send_response(302)
                self.send_header("Location", {cfg['authorize_url']!r} + "?" + params)
                self.end_headers()
            """)
    if name.startswith("callback_"):
        return textwrap.dedent(f"""\
            def {name}(self, query):
                code = query.get("code", [None])[0]
                if not code:
                    respond(self, 400, {{"error": "no code in callback"}}); return
                client_id = os.environ.get({env_id!r})
                client_secret = os.environ.get({env_secret!r})
                token = exchange_code_for_token(
                    {cfg['token_url']!r}, client_id, client_secret, code,
                    self.base_url() + "/api/connections/{slug_}/callback")
                if token is None:
                    respond(self, 502, {{"error": "token exchange failed"}}); return
                execute(
                    "UPDATE connections SET state='linked', access_token=?, refresh_token=?, "
                    "expires_at=?, scopes=? WHERE provider=?",
                    (token.get("access_token"), token.get("refresh_token"),
                     expiry_iso(token.get("expires_in")), token.get("scope"), {provider!r}))
                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()
            """)
    raise BuildRefused(f"no OAuth handler rule for {name}")


def render_status_handler():
    return textwrap.dedent("""\
        def connections_status(self):
            rows = query("SELECT provider, state, expires_at, scopes FROM connections")
            out = {r["provider"]: r for r in rows}
            respond(self, 200, out)
        """)


# --------------------------------------------------------------------------- app.py assembly
APP_PRELUDE = '''\
#!/usr/bin/env python3
"""GENERATED by packages/builder/builder.py from {spec_id} ({title}).
Do not hand-edit — re-run the Builder against a revised spec instead.
Stdlib only: http.server, sqlite3, urllib, json. No new dependencies.
"""
import json, os, re, sqlite3, sys, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlencode
import uuid

DB_PATH = os.environ.get("APP_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")) as f:
        get_db().executescript(f.read())


def query(sql, params=()):
    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def new_id():
    return str(uuid.uuid4())


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def expiry_iso(seconds_from_now):
    if not seconds_from_now:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + float(seconds_from_now)))


def exchange_code_for_token(token_url, client_id, client_secret, code, redirect_uri):
    body = urlencode({{
        "client_id": client_id, "client_secret": client_secret,
        "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri,
    }}).encode()
    req = urllib.request.Request(token_url, data=body, headers={{"Accept": "application/json"}})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        print(f"token exchange failed: {{exc}}", file=sys.stderr)
        return None


def respond(handler, code, payload):
    body = json.dumps(payload).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
'''

APP_ROUTER = '''

class Handler(BaseHTTPRequestHandler):
    def base_url(self):
        return f"http://{{self.headers.get('Host', 'localhost')}}"

    def _body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {{}}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {{}}

    def do_GET(self):
        self._guarded(self._do_GET)

    def do_POST(self):
        self._guarded(self._do_POST)

    def do_PUT(self):
        self._guarded(self._do_PUT)

    def do_DELETE(self):
        self._guarded(self._do_DELETE)

    def _guarded(self, handler):
        # No route handler here may crash the request thread on a real
        # failure (a broken database file, a bad value from the client) --
        # found by exactly that happening once: an uncaught exception left
        # the client with a reset connection instead of a real 500, and the
        # traceback printed to stderr instead of anywhere a caller could see
        # it. respond() may itself have already sent a partial response by
        # the time something fails downstream of it, so this is a backstop,
        # not the primary error path for handlers that build their own
        # responses.
        try:
            handler()
        except Exception as exc:
            try:
                respond(self, 500, {{"error": str(exc)}})
            except Exception:
                pass  # headers already sent; nothing more this response can do

    def _do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        if path == "/" or path == "":
            path = "/index.html"
        if path == "/favicon.ico":
            # Browsers request this unconditionally; a plain 404 shows up as a
            # console error on every single page load with nothing to fix.
            self.send_response(204)
            self.end_headers()
            return
        if path.startswith("/static/") or re.match(r"^/[\\w.-]+\\.html$", path):
            self._serve_static(path.lstrip("/"))
            return
{get_dispatch}
        respond(self, 404, {{"error": "no route"}})

    def _do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
{post_dispatch}
        respond(self, 404, {{"error": "no route"}})

    def _do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
{put_dispatch}
        respond(self, 404, {{"error": "no route"}})

    def _do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
{delete_dispatch}
        respond(self, 404, {{"error": "no route"}})

    def _serve_static(self, rel):
        rel = rel[len("static/"):] if rel.startswith("static/") else rel
        fp = os.path.join(STATIC_DIR, rel)
        if not os.path.abspath(fp).startswith(os.path.abspath(STATIC_DIR)) or not os.path.isfile(fp):
            respond(self, 404, {{"error": "not found"}}); return
        with open(fp, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

{handlers}

def main():
    init_db()
    port = int(os.environ.get("PORT", {port}))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"listening on http://127.0.0.1:{{port}}")
    server.serve_forever()


if __name__ == "__main__":
    main()
'''


def _dispatch_call(method, path, name):
    """The exact call each route's dispatch line makes, keyed unambiguously by
    (method, name-prefix) -- no generic fallback branch, so a route this
    function does not recognise raises here instead of generating a call that
    would fail at request time in the generated server."""
    id_path = path.endswith("/")
    if method == "GET" and (name.startswith("list_") or name == "connections_status"):
        return f"self.{name}()"
    if method == "GET" and name.startswith("get_") and id_path:
        return f"self.{name}(path[len({path!r}):])"
    if method == "GET" and name.startswith("callback_"):
        return f"self.{name}(parse_qs(urlparse(self.path).query))"
    if method == "POST" and name.startswith("start_"):
        return f"self.{name}()"
    if method == "POST" and name.startswith("create_"):
        return f"self.{name}(self._body())"
    if method == "PUT" and name.startswith("update_") and id_path:
        return f"self.{name}(path[len({path!r}):], self._body())"
    if method == "DELETE" and name.startswith("delete_") and id_path:
        return f"self.{name}(path[len({path!r}):])"
    raise BuildRefused(f"no dispatch rule for {method} {path} -> {name}")


def build_app_py(spec, port):
    routes = crud_routes(spec) + oauth_routes(spec)
    handlers = []
    dispatch = {"GET": [], "POST": [], "PUT": [], "DELETE": []}
    for method, path, name, ctx in routes:
        # connections_status has its own handler (below); every other route's
        # ctx is either an OAuth route (carries 'provider') or a CRUD route.
        if name != "connections_status":
            handlers.append(render_oauth_handler(name, ctx) if ctx.get("provider")
                             else render_crud_handler(method, path, name, ctx))
        cond = f"path.startswith({path!r})" if path.endswith("/") else f"path == {path!r}"
        dispatch[method].append(f"        if {cond}:\n            {_dispatch_call(method, path, name)}; return\n")
    if spec["build_model"]["integrations"]:
        handlers.append(render_status_handler())

    src = APP_PRELUDE.format(spec_id=spec["spec_id"], title=spec["title"])
    src += APP_ROUTER.format(
        get_dispatch="".join(dispatch["GET"]) or "        pass",
        post_dispatch="".join(dispatch["POST"]) or "        pass",
        put_dispatch="".join(dispatch["PUT"]) or "        pass",
        delete_dispatch="".join(dispatch["DELETE"]) or "        pass",
        handlers="\n".join(textwrap.indent(h, "    ") for h in handlers),
        port=port,
    )
    return src


# --------------------------------------------------------------------------- brand / logo
def _png_dimensions_and_alpha(path):
    """Real PNG header parsing (no Pillow, no new dependency): the IHDR chunk
    is fixed at byte offset 16 (8-byte signature + 4-byte length + 4-byte
    'IHDR' type), width and height as big-endian uint32, colour type as the
    tenth IHDR byte. Colour type 4 (greyscale+alpha) or 6 (RGBA) is treated
    as 'has transparency'; anything else fails LOGO_SPEC's background rule
    outright rather than guessing whether it is transparent."""
    with open(path, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        raise BuildRefused(f"{path}: not a valid PNG (bad signature/IHDR)")
    width, height = struct.unpack(">II", head[16:24])
    colour_type = head[25]
    return width, height, colour_type in (4, 6)


def _svg_dimensions(path):
    tree = ET.parse(path)
    root = tree.getroot()
    vb = root.get("viewBox")
    if vb:
        _, _, w, h = (float(x) for x in vb.split())
        return w, h
    w, h = root.get("width"), root.get("height")
    if w and h:
        return float(w.rstrip("px")), float(h.rstrip("px"))
    raise BuildRefused(f"{path}: SVG declares neither viewBox nor width/height")


def validate_provided_logo(path):
    """Checked against LOGO_SPEC (packages/builder/assets/logos/manifest.json)
    exactly as declared to the customer at C.04 — format, square aspect
    ratio, size bounds, and (for PNG) an alpha channel. Refuses, never
    resizes or reinterprets a file that does not meet it."""
    if not os.path.isfile(path):
        raise BuildRefused(f"logo file not found: {path}")
    ext = path.rsplit(".", 1)[-1].lower()
    if ext not in LOGO_SPEC["format"]:
        raise BuildRefused(f"{path}: format '.{ext}' not in {LOGO_SPEC['format']}")
    if ext == "png":
        w, h, has_alpha = _png_dimensions_and_alpha(path)
        if not has_alpha:
            raise BuildRefused(f"{path}: PNG has no alpha channel; {LOGO_SPEC['background']} background required")
    else:
        w, h = _svg_dimensions(path)
    if w != h:
        raise BuildRefused(f"{path}: {w}x{h} is not square ({LOGO_SPEC['aspect_ratio']} required)")
    if not (LOGO_SPEC["min_px"] <= w <= LOGO_SPEC["max_px"]):
        raise BuildRefused(f"{path}: {int(w)}px outside [{LOGO_SPEC['min_px']}, {LOGO_SPEC['max_px']}]")
    return int(w), int(h)


def resolve_logo(brand):
    """(inline_svg_or_none, alt_text). Three real modes, matching C.04:
    'premade' embeds a real starter mark; 'provided' validates the real file
    against LOGO_SPEC and embeds it (SVG inlined, PNG as a data: URI — no
    external asset pipeline needed); 'design_for_me' has no logo yet, which
    renders as a clean text wordmark, never a broken image tag. C.04 unasked
    (assets is None -- not present in the real answers, as for every template
    predating this question) is treated the same as an explicit 'design_for_me':
    that mode's whole purpose is to be the safe default when no logo decision
    exists yet, so this is not a guess about what the answer would have been,
    just the documented fallback applied to real absence of an answer."""
    assets = (brand or {}).get("assets")
    mode = (assets or {}).get("mode") if assets is not None else "design_for_me"
    app_name = brand.get("app_name") or "App"
    if mode == "premade":
        logo_id = assets.get("logo_id")
        if logo_id not in LOGOS:
            raise BuildRefused(f"C.04: premade logo_id '{logo_id}' is not in the starter library {sorted(LOGOS)}")
        svg_path = os.path.join(ASSETS_DIR, "logos", f"{logo_id}.svg")
        return open(svg_path, encoding="utf-8").read(), f"{app_name} ({LOGOS[logo_id]['name']} mark)"
    if mode == "provided":
        path = assets.get("path")
        if not path:
            raise BuildRefused("C.04: mode 'provided' with no file path")
        validate_provided_logo(path)
        if path.lower().endswith(".svg"):
            return open(path, encoding="utf-8").read(), app_name
        import base64
        data = base64.b64encode(open(path, "rb").read()).decode()
        return f'<img src="data:image/png;base64,{data}" width="32" height="32" alt="{app_name} logo">', app_name
    if mode == "design_for_me":
        return None, app_name
    raise BuildRefused(f"C.04: unknown brand mode {mode!r}")


# --------------------------------------------------------------------------- static screens
def _render_header(bm):
    """Real markup, computed once and injected into every real generated page:
    the resolved logo (or nothing, for design_for_me) plus the real app name.
    Returns (html, css) rather than a full page — every screen keeps its own
    <title>/<style>, this is inserted after that, never replacing it."""
    inline_svg_or_img, app_name = resolve_logo(bm.get("brand") or {})
    mark = ""
    if inline_svg_or_img:
        if inline_svg_or_img.lstrip().startswith("<svg"):
            mark = inline_svg_or_img.replace("<svg ", '<svg class="app-mark" ', 1)
        else:
            mark = inline_svg_or_img.replace('width="32" height="32"', 'width="32" height="32" class="app-mark"')
    html = f'<header class="app-header">{mark}<span class="app-name">{app_name}</span></header>'
    css = ("body{margin:0}.app-header{display:flex;align-items:center;gap:10px;padding:12px 16px;"
           "border-bottom:1px solid #ddd;font-family:system-ui,sans-serif}"
           ".app-mark{width:28px;height:28px}.app-name{font-weight:600}")
    return html, css


def _inject_header(page_html, header_html, header_css):
    page_html = page_html.replace("</style>", header_css + "</style>", 1)
    page_html = page_html.replace("<h1>", header_html + "<h1>", 1)
    return page_html


def build_screens(spec):
    """One real HTML file per numbered screen (SCR-nnn). Three screen kinds have
    a rendering rule: integration_status (what Command Desk needs), list and
    detail. report and form do not yet — refuses rather than rendering a
    placeholder that would look done and is not; see the README for why."""
    pages = {}
    bm = spec["build_model"]
    header_html, header_style = _render_header(bm)
    for scr in bm["screens_inventory"]:
        if scr["kind"] == "integration_status":
            page = _render_integration_screen(bm, scr)
        elif scr["kind"] == "list":
            page = _render_list_screen(bm, scr)
        elif scr["kind"] == "detail":
            page = _render_detail_screen(bm, scr)
        else:
            raise BuildRefused(f"{scr['id']}: no screen rendering rule for kind '{scr['kind']}'")
        pages[scr["id"]] = _inject_header(page, header_html, header_style)
    first_screen_id = bm["screens_inventory"][0]["id"] if bm["screens_inventory"] else None
    pages["index.html"] = pages.get(first_screen_id, "<!doctype html><title>App</title><p>No screens.</p>")
    return pages


def _render_integration_screen(bm, scr):
    name = scr["integration"]
    provider = _resolve_provider(name, bm["integrations"][name])
    slug_ = slug(provider)
    unavailable = (bm["integrations"][name].get("on_unavailable") or {})
    error_text = unavailable.get("message") or "Cannot reach server"
    return textwrap.dedent(f"""\
        <!doctype html>
        <title>Linked Services</title>
        <style>
          body{{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px}}
          .tile{{border:1px solid #ccc;border-radius:8px;padding:16px;margin:12px 0}}
          .state-linked{{color:#0a7a2f}} .state-missing{{color:#888}} .error{{color:#b00020}}
          button{{padding:8px 16px;cursor:pointer}}
        </style>
        <h1>Linked Services</h1>
        <div id="tiles">Loading…</div>
        <div id="error" class="error" hidden></div>
        <script>
        async function refresh() {{
          const tiles = document.getElementById('tiles');
          const err = document.getElementById('error');
          tiles.textContent = 'Loading…';
          err.hidden = true;
          try {{
            const res = await fetch('/api/connections/status');
            if (!res.ok) throw new Error('bad status');
            const data = await res.json();
            const conn = data[{provider!r}];
            const state = (conn && conn.state) || 'MISSING';
            tiles.innerHTML = '';
            const tile = document.createElement('div');
            tile.className = 'tile';
            tile.innerHTML = '<b>{provider.title()}</b>: <span class="state-' + state.toLowerCase() + '">' + state + '</span>';
            if (state !== 'linked') {{
              // A real top-level POST navigation, so the browser follows the
              // start route's 302 the same way a real click must: location.href
              // only ever issues GET, and the start route is POST-only (the
              // spec's own AC-01 requires POST) -- a plain link/onclick here
              // would 404 in a real browser even though nothing looked broken
              // in this generator's own tests, which is exactly the class of
              // defect the Playwright layer exists to catch.
              const form = document.createElement('form');
              form.method = 'POST';
              form.action = '/api/connections/{slug_}/start';
              const btn = document.createElement('button');
              btn.type = 'submit';
              btn.textContent = 'Connect {provider.title()}';
              form.appendChild(btn);
              tile.appendChild(document.createElement('br'));
              tile.appendChild(form);
            }}
            tiles.appendChild(tile);
          }} catch (e) {{
            tiles.textContent = '';
            err.textContent = {error_text!r};
            err.hidden = false;
          }}
        }}
        refresh();
        </script>
        """)


def _render_detail_screen(bm, scr):
    record = scr["record"]
    tbl = table_name(record)
    fields = list(bm["records"][record]["fields"])
    can_edit = bool(bm["records"][record]["access"].get("edit"))
    slugs_js = json.dumps([slug(f) for f in fields])
    rows_html = "".join(f'<tr><th>{f}</th><td><span data-field="{slug(f)}"></span></td></tr>' for f in fields)
    save_btn = '<button id="save" hidden>Save</button>' if can_edit else ""
    save_js = "" if not can_edit else textwrap.dedent(f"""
        document.getElementById('save').hidden = false;
        document.getElementById('save').onclick = async () => {{
          const body = {{}};
          for (const key of FIELD_KEYS) body[key] = document.querySelector(`[data-field="${{key}}"]`).textContent;
          const res = await fetch('/api/{tbl}/' + id, {{method: 'PUT', body: JSON.stringify(body)}});
          document.getElementById('state').textContent = res.ok ? 'Saved.' : 'Save failed.';
        }};""")
    return textwrap.dedent(f"""\
        <!doctype html>
        <title>{record}</title>
        <style>body{{font-family:system-ui,sans-serif;max-width:600px;margin:40px auto}}
        table{{border-collapse:collapse}} th,td{{border:1px solid #ccc;padding:6px;text-align:left}}
        [data-field]{{outline:none}}</style>
        <h1>{record} detail</h1>
        <div id="state">Loading…</div>
        <table id="fields" hidden>{rows_html}</table>
        {save_btn}
        <script>
        const FIELD_KEYS = {slugs_js};
        const id = new URLSearchParams(window.location.search).get('id');
        async function load() {{
          const state = document.getElementById('state');
          try {{
            const res = await fetch('/api/{tbl}/' + id);
            if (!res.ok) throw new Error('not found');
            const row = await res.json();
            for (const key of FIELD_KEYS) {{
              document.querySelector(`[data-field="${{key}}"]`).textContent = row[key] ?? '';
            }}
            document.getElementById('fields').hidden = false;
            state.hidden = true;
            {save_js}
          }} catch (e) {{
            state.textContent = 'Cannot reach server';
          }}
        }}
        if (id) load(); else document.getElementById('state').textContent = 'No id given.';
        </script>
        """)


def _render_list_screen(bm, scr):
    record = scr["record"]
    tbl = table_name(record)
    fields = list(bm["records"][record]["fields"])
    slugs_js = json.dumps([slug(f) for f in fields])
    headers = "".join(f"<th>{f}</th>" for f in fields)
    return textwrap.dedent(f"""\
        <!doctype html>
        <title>{record}s</title>
        <style>body{{font-family:system-ui,sans-serif;max-width:800px;margin:40px auto}}
        table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #ccc;padding:6px}}</style>
        <h1>{record}s</h1>
        <div id="state">Loading…</div>
        <table id="rows" hidden><thead><tr>{headers}</tr></thead><tbody></tbody></table>
        <script>
        const FIELD_KEYS = {slugs_js};
        async function load() {{
          const state = document.getElementById('state');
          const table = document.getElementById('rows');
          try {{
            const res = await fetch('/api/{tbl}');
            if (!res.ok) throw new Error('bad status');
            const rows = await res.json();
            if (!rows.length) {{ state.textContent = 'No {record.lower()}s yet.'; return; }}
            const body = table.querySelector('tbody');
            for (const r of rows) {{
              const tr = document.createElement('tr');
              for (const key of FIELD_KEYS) {{
                const td = document.createElement('td');
                td.textContent = r[key] ?? '';
                tr.appendChild(td);
              }}
              body.appendChild(tr);
            }}
            state.hidden = true; table.hidden = false;
          }} catch (e) {{
            state.textContent = 'Cannot reach server';
          }}
        }}
        load();
        </script>
        """)


# --------------------------------------------------------------------------- entry point
def build(spec, out_dir, port):
    unsupported = []
    try:
        crud_routes(spec)
    except BuildRefused as e:
        unsupported.append(str(e))
    try:
        oauth_routes(spec)
    except BuildRefused as e:
        unsupported.append(str(e))
    if unsupported:
        raise BuildRefused("cannot build — no generation rule for:\n" + "\n".join(f"  - {u}" for u in unsupported))

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "static"), exist_ok=True)

    open(os.path.join(out_dir, "schema.sql"), "w").write(build_schema(spec))
    open(os.path.join(out_dir, "app.py"), "w").write(build_app_py(spec, port))
    for name, html in build_screens(spec).items():
        open(os.path.join(out_dir, "static", _screen_filename(name)), "w").write(html)
    open(os.path.join(out_dir, "run.sh"), "w").write(textwrap.dedent(f"""\
        #!/bin/sh
        # GENERATED by packages/builder/builder.py from {spec['spec_id']}.
        cd "$(dirname "$0")"
        exec python3 app.py
        """))
    os.chmod(os.path.join(out_dir, "run.sh"), 0o755)
    return {
        "records_built": list(spec["build_model"]["records"]),
        "integrations_built": list(spec["build_model"]["integrations"]),
        "screens_built": len(spec["build_model"]["screens_inventory"]),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="SPEC.json from the Assembly Engine")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--port", type=int, default=8788)
    args = ap.parse_args(argv)

    spec = json.load(open(args.spec, encoding="utf-8"))
    try:
        result = build(spec, args.out, args.port)
    except BuildRefused as e:
        print("REFUSED —", e, file=sys.stderr)
        return 2
    print(f"built {len(result['records_built'])} record(s), {len(result['integrations_built'])} integration(s), "
          f"{result['screens_built']} screen(s) -> {args.out}/  (run: {args.out}/run.sh)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
