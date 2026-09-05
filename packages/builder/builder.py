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
import re
import struct
import sys
import shutil
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


def q(identifier):
    """A column/table name as it must appear in generated SQL. Some perfectly
    ordinary field names slug to SQL keywords — Command Desk's own 'When' and
    'On' are both reserved — so every generated identifier is quoted. Found by
    running the generated app, not by reading it: the first build died on
    `near "when": syntax error`.

    Square brackets rather than double quotes because this SQL is itself
    written inside a double-quoted Python string in the generated app —
    quoting it the obvious way produced generated code that would not even
    parse, which the live run caught immediately."""
    if "]" in identifier:
        raise BuildRefused(f"cannot quote identifier {identifier!r}")
    return "[" + identifier + "]"


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
            cols.append(f"{q(slug(fname))} {storage.replace('FOREIGN_KEY_ROLE', 'TEXT').replace('FOREIGN_KEY', 'TEXT')}")
        initial = _initial_stage(_workflow_for(spec, record))
        if initial:
            # a record whose own R.10 says it moves through stages gets a real
            # stage column, starting in the workflow's own declared initial stage
            cols.append(f"stage TEXT NOT NULL DEFAULT '{initial}'")
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
            # the row's own trail: every audit_trail entry (moves, approvals, pressed
            # actions) and every stage entry, oldest first -- the FINDINGS gap
            # "audit_trail has no route or screen that exposes the trail". Every
            # viewable record has one, lifecycle or not: a pressed custom action on
            # a record with no stages is still a trail entry. (Found by a browser
            # opening a Project: 404 on its trail.)
            routes.append(("GET", f"/api/history/{tbl}/", "history_" + tbl, {"table": tbl}))
        if access.get("create"):
            routes.append(("POST", f"/api/{tbl}", "create_" + tbl,
                           {"table": tbl, "fields": list(r["fields"]),
                            "initial_stage": _initial_stage(_workflow_for(spec, record)),
                            "on_create": _create_effects_for(spec, record)}))
        if access.get("edit"):
            routes.append(("PUT", f"/api/{tbl}/", "update_" + tbl,
                           {"table": tbl, "fields": list(r["fields"])}))
        if access.get("delete") and access["delete"] != "nobody":
            routes.append(("DELETE", f"/api/{tbl}/", "delete_" + tbl, {"table": tbl}))
    return routes


def _create_effects_for(spec, record):
    """The record's own declared create effects, each completed with the
    target record's real workflow (its transitions and approvals) so the
    generated app can fire the declared automatic edge without looking it up
    by name at request time. Refuses an effect whose target has no workflow
    or whose named event is not one of that workflow's own automatic edges."""
    out = []
    for eff in spec["build_model"]["records"][record].get("on_create") or []:
        eff = dict(eff)
        target_record = next((r for r in spec["build_model"]["records"] if table_name(r) == eff.get("table")), None)
        if target_record is None:
            raise BuildRefused(f"{record}: create effect names table {eff.get('table')!r}, which is no record's table")
        wf = _workflow_for(spec, target_record)
        if not wf:
            raise BuildRefused(f"{record}: create effect targets {target_record!r}, which has no lifecycle to move")
        events = {t.get("event") for t in wf["transitions"] if t.get("mover") == "automatic"}
        if eff.get("event") not in events:
            raise BuildRefused(f"{record}: create effect fires event {eff.get('event')!r}, which is not an automatic "
                               f"edge of '{target_record} lifecycle' (declared: {sorted(e for e in events if e)})")
        eff["transitions"] = [{k: t[k] for k in ("from", "to", "mover", "event", "roles") if k in t}
                              for t in wf["transitions"]]
        eff["approvals"] = wf.get("approvals") or []
        out.append(eff)
    return out


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
        cols = ", ".join([q("id"), q("created_at"), q("updated_at")] + [q(slug(f)) for f in fields])
        qmarks = ", ".join(["?"] * (3 + len(fields)))
        # field values are extracted at code-gen time (not via a generated
        # comprehension) -- the field list is already known here, and this
        # sidesteps a real bug this Builder shipped with once: {f!r} inside an
        # f-string is evaluated immediately by the *generator*, not left as
        # literal text in the *generated* code, so `f` must not appear as a
        # loop variable name inside an f-string template like this one.
        gets = ", ".join(f"body.get({name_!r})" for name_ in fields)
        initial = ctx.get("initial_stage")
        on_create = ctx.get("on_create") or []
        lines = [f"def {name}(self, body):",
                 "    rid = new_id(); now = now_iso()",
                 f"    values = [rid, now, now, {gets}]",
                 f'    execute("INSERT INTO {tbl} ({cols}) VALUES ({qmarks})", values)',
                 "    effects = []"]
        if initial or on_create:
            lines += ["    conn = get_db()", "    try:"]
            if initial:
                # a record with a lifecycle really enters its initial stage now: the
                # stage_history part records it, so rate/by-month reports see it
                lines.append(f"        stage_history.record_transition(conn, {tbl!r}, rid, {initial!r})")
            if on_create:
                lines += [f'        row = dict(conn.execute("SELECT * FROM {tbl} WHERE id = ?", (rid,)).fetchone())',
                          f"        effects = run_create_effects(conn, {on_create!r}, row)"]
            lines += ["    finally:", "        conn.close()"]
        lines += [
            "    _nconn = get_db()",
            "    try:",
            f'        _nrow = dict(_nconn.execute("SELECT * FROM {tbl} WHERE id = ?", (rid,)).fetchone())',
            f'        notified = notify(_nconn, NOTIFICATION_DECLS, "record_created", table={tbl!r}, row=_nrow)',
            "    finally:",
            "        _nconn.close()",
        ]
        lines.append('    respond(self, 201, {"id": rid, "effects": effects, "notified": notified})')
        return "\n".join(lines) + "\n"
    if name.startswith("update_"):
        fields = ctx["fields"]
        sets = ", ".join(f"{q(slug(name_))} = ?" for name_ in fields)
        gets = ", ".join(f"body.get({name_!r})" for name_ in fields)
        cols = [slug(f) for f in fields]
        has_stock = {"stock_on_hand", "reorder_point"} <= set(cols)
        return textwrap.dedent(f"""\
            def {name}(self, record_id, body):
                _nconn = get_db()
                try:
                    _before = _nconn.execute("SELECT * FROM {tbl} WHERE id = ?", (record_id,)).fetchone()
                    if _before is None:
                        return respond(self, 404, {{"error": "not found"}})
                    values = [{gets}, now_iso(), record_id]
                    _nconn.execute("UPDATE {tbl} SET {sets}, updated_at = ? WHERE id = ?", values)
                    _nconn.commit()
                    _after = dict(_nconn.execute("SELECT * FROM {tbl} WHERE id = ?", (record_id,)).fetchone())
                    notified = []
                    for _col in {cols!r}:
                        if _after.get(_col) and _after.get(_col) != _before[_col]:
                            notified += notify(_nconn, NOTIFICATION_DECLS, "field_set",
                                               table={tbl!r}, row=_after, column=_col)
                    if {has_stock!r} and _after.get("stock_on_hand") is not None and _after.get("reorder_point") is not None:
                        try:
                            if float(_after["stock_on_hand"]) <= float(_after["reorder_point"]):
                                notified += notify(_nconn, NOTIFICATION_DECLS, "threshold", table={tbl!r}, row=_after)
                        except (TypeError, ValueError):
                            pass
                    respond(self, 200, {{"id": record_id, "notified": notified}})
                finally:
                    _nconn.close()
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
    seen = set()
    for name, flx in spec["build_model"]["integrations"].items():
        if flx.get("auth") == "api_key":
            continue          # a pasted key is not an OAuth round trip — see api_key_routes
        provider = _resolve_provider(name, flx)
        if provider not in OAUTH_PROVIDERS:
            raise BuildRefused(
                f"integration '{name}': provider '{provider}' is not in OAUTH_PROVIDERS — "
                f"add its real authorize_url/token_url from its own published docs, or this "
                f"Builder will not invent one")
        slug_ = slug(provider)
        if slug_ in seen:     # two services on one provider share its real round trip
            continue
        seen.add(slug_)
        routes.append(("POST", f"/api/connections/{slug_}/start", f"start_{slug_}", {"provider": provider}))
        routes.append(("GET", f"/api/connections/{slug_}/callback", f"callback_{slug_}", {"provider": provider}))
    if spec["build_model"]["integrations"]:
        routes.append(("GET", "/api/connections/status", "connections_status", {}))
    return routes


def api_key_routes(spec):
    """A linked service that authenticates with a pasted key is not an OAuth
    round trip and must not be generated as one: it gets a real route that
    stores the real key against the real connection row."""
    routes = []
    for name, flx in spec["build_model"]["integrations"].items():
        if flx.get("auth") != "api_key":
            continue
        routes.append(("POST", f"/api/connections/{slug(name)}/key", f"key_{slug(name)}",
                        {"provider_name": name}))
    return routes


def render_api_key_handler(name, ctx):
    provider = ctx["provider_name"]
    return textwrap.dedent(f'''\
        def {name}(self, body):
            """Stores the real pasted key for {provider!r}. The key is never
            echoed back — the response says only that it is connected."""
            key = (body or {{}}).get("key")
            if not key:
                return respond(self, 400, {{"error": "key is required"}})
            execute("INSERT INTO connections (provider, state, access_token) VALUES (?, 'connected', ?) "
                    "ON CONFLICT(provider) DO UPDATE SET state='connected', access_token=excluded.access_token",
                    ({provider!r}, key))
            respond(self, 200, {{"provider": {provider!r}, "state": "connected"}})
        ''')


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
import json, os, re, sqlite3, sys, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, urlencode
import uuid

DB_PATH = os.environ.get("APP_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db"))

#: Every declared notification / recurring op, classified once by the Builder
#: at generation time (never re-derived at request time) -- see builder.py's
#: notification_decls()/job_decls(). A None "kind" means the Builder found no
#: mechanical rule for it; it is still listed, with the real reason, never
#: silently dropped.
NOTIFICATION_DECLS = {notification_decls_json}
RECURRING_JOBS = {recurring_jobs_json}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")) as f:
        conn.executescript(f.read())
    audit_trail.ensure_table(conn)
    stage_approval_gate.ensure_table(conn)
    stage_history.ensure_table(conn)
    notification_delivery.ensure_table(conn)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _job_fired (
            fire_key TEXT PRIMARY KEY,
            fired_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _recipients_for(conn, decl, table, row):
    """Who a delivered notification really goes to, from the notification's own
    declared N.02 recipients. A recipient this app cannot resolve is delivered
    to the declared description itself rather than dropped, so it is visible."""
    out = []
    for r in decl.get("recipients") or []:
        kind = r.get("kind")
        if kind == "field" and row is not None:
            col = "".join(c.lower() if c.isalnum() else "_" for c in r.get("field", "")).strip("_")
            val = row.get(col)
            if val:
                out.append(str(val))
                continue
            out.append(f"[{{r.get('field')}} not set on this {{r.get('record')}}]")
        elif kind == "roles":
            out.extend(r.get("roles") or [])
        elif kind == "owner" and row is not None:
            out.append(str(row.get("owner") or "[owner]"))
        elif kind == "custom":
            out.append(str(r.get("who") or "[recipient]"))
        else:
            out.append(f"[{{kind}}]")
    return out or ["[nobody declared]"]


def notify(conn, decls, kind, table=None, row=None, stage=None, action=None, column=None, extra=None):
    """Fires every declared notification whose trigger really just happened.
    Delivery is in-app only and on purpose: nothing in this system is connected
    to a mail or SMS provider, so an email leg would be a claim, not a delivery.
    The channels the notification declares are recorded on the row either way,
    so what was asked for stays visible next to what really happened."""
    fired = []
    for d in decls:
        if d.get("kind") != kind:
            continue
        p = d.get("params") or {{}}
        if table and p.get("table") and p["table"] != table:
            continue
        if kind == "stage_reached" and p.get("stage") != stage:
            continue
        if kind == "custom_action" and p.get("action") != action:
            continue
        if kind == "field_set" and (column is not None and p.get("column") != column):
            continue
        if kind == "field_set" and row is not None and not row.get(p.get("column")):
            continue
        subject = d["name"]
        body = (extra or f"{{d['name']}} — {{table or ''}} {{(row or {{}}).get('id', '') or ''}}").strip()
        for who in _recipients_for(conn, d, table, row):
            notification_delivery.deliver(conn, who, subject, body, in_app_only=True)
        fired.append({{"notification": d["name"], "id": d.get("id"),
                      "to": _recipients_for(conn, d, table, row),
                      "declared_channels": d.get("channels") or [],
                      "delivered_by": "in_app only — no mail or SMS provider is connected"}})
    return fired


def _parse_duration_seconds(text):
    """A duration phrase from a real R.14/FL.10 answer, turned into seconds --
    the run-time twin of builder.py's own _parse_duration_seconds, so a job's
    declared duration is honoured exactly as the Builder classified it."""
    if not isinstance(text, str):
        return None
    m = re.match(r"\\s*([\\d.]+)\\s*(second|minute|hour|day|week|month|year)s?\\s*$", text.strip(), re.I)
    if not m:
        return None
    n = float(m.group(1)); unit = m.group(2).lower()
    scale = {{"second": 1, "minute": 60, "hour": 3600, "day": 86400,
             "week": 604800, "month": 2629800, "year": 31557600}}[unit]
    return n * scale


def run_job(conn, decls, job):
    """Runs one declared recurring job for real, against the real database --
    or, if the Builder found no mechanical rule for it, reports the real
    reason. Never guesses: a job whose kind is None here was already refused
    a rule at build time (see builder.py's _classify_recurring_op)."""
    kind = job.get("kind")
    p = job.get("params") or {{}}
    if kind == "purge":
        seconds = _parse_duration_seconds(p["duration"])
        cutoff_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - seconds))
        n = conn.execute(f"DELETE FROM {{p['table']}} WHERE created_at < ?", (cutoff_iso,)).rowcount
        conn.commit()
        return {{"job": job["name"], "kind": kind, "ran": True, "deleted": n}}
    if kind == "date_timeout":
        seconds = _parse_duration_seconds(p["duration"])
        rows = [dict(r) for r in conn.execute(
            f"SELECT * FROM {{p['table']}} WHERE stage = ?", (p["from_stage"],)).fetchall()]
        moved = []
        for row in rows:
            val = row.get(p["field"])
            cond = (not val) if p["negate"] else bool(val)
            if not cond:
                continue
            hist = conn.execute(
                "SELECT entered_at FROM _stage_history WHERE record_table = ? AND row_id = ? AND stage = ? "
                "ORDER BY entered_at DESC LIMIT 1", (p["table"], str(row["id"]), p["from_stage"])).fetchone()
            if not hist or (time.time() - hist[0]) < seconds:
                continue
            conn.execute(f"UPDATE {{p['table']}} SET stage = ? WHERE id = ?", (p["to_stage"], row["id"]))
            conn.commit()
            stage_history.record_transition(conn, p["table"], row["id"], p["to_stage"])
            fired = notify(conn, decls, "stage_reached", table=p["table"], row=row, stage=p["to_stage"])
            moved.append({{"id": row["id"], "notified": fired}})
        return {{"job": job["name"], "kind": kind, "ran": True, "moved": moved}}
    if kind == "due_reminder":
        offset = str(p.get("offset") or "+0 seconds")
        seconds = _parse_duration_seconds(offset.lstrip("+-")) or 0
        sign = -1 if offset.strip().startswith("-") else 1
        rows = [dict(r) for r in conn.execute(f"SELECT * FROM {{p['table']}}").fetchall()]
        fired_rows = []
        for row in rows:
            raw = row.get(p.get("column"))
            if not raw:
                continue
            try:
                due = time.mktime(time.strptime(str(raw)[:19], "%Y-%m-%dT%H:%M:%S"))
            except Exception:
                continue
            if time.time() < due + sign * seconds:
                continue
            key = f"{{job['id']}}:{{row['id']}}"
            if conn.execute("SELECT 1 FROM _job_fired WHERE fire_key = ?", (key,)).fetchone():
                continue
            conn.execute("INSERT INTO _job_fired (fire_key, fired_at) VALUES (?, ?)", (key, now_iso()))
            conn.commit()
            fired = notify(conn, decls, "relative_to_date", table=p["table"], row=row)
            fired_rows.append({{"id": row["id"], "notified": fired}})
        return {{"job": job["name"], "kind": kind, "ran": True, "fired": fired_rows}}
    return {{"job": job["name"], "kind": kind, "ran": False, "reason": job.get("unwired_reason")}}


def run_transition_effects(conn, effects, table, row_id, entered_stage):
    """The workflow's own declared, executable effects for entering a stage
    (the template's transition_effects block), run right after the move that
    entered it. Returns what each effect really did, for the response."""
    done = []
    for eff in effects or []:
        if eff.get("on_enter") != entered_stage:
            continue
        if eff.get("op") == "apply_order_lines":
            applied = stock_ledger.apply_order_lines(
                conn, eff["line_table"], eff["line_fk"], row_id, eff["product_table"], eff["product_fk"],
                eff["quantity_column"], eff["direction"])
            done.append({{"op": "apply_order_lines", "direction": eff["direction"], "lines": applied}})
        else:
            raise ValueError("no executable rule for transition effect " + repr(eff.get("op")))
    return done


def run_report_metric(conn, sp):
    engine = sp.get("engine")
    if engine in (None, "reporting_engine"):
        return reporting_engine.run_report(conn, sp)
    if engine == "stage_history" and sp.get("kind") == "rate_over_last_days":
        return stage_history.rate_over_last_days(conn, sp["table"], sp["numerator_stage"],
                                                 sp["denominator_stages"], sp["days"])
    if engine == "stage_history" and sp.get("kind") == "line_value_by_month":
        return stage_history.line_value_by_month(conn, sp["table"], sp["stage"], sp["line_table"], sp["line_fk"],
                                                 sp["quantity_column"], sp["price_column"], sp.get("months", 12))
    if engine == "stock_ledger" and sp.get("kind") == "count_at_or_below_reorder":
        return stock_ledger.count_at_or_below_reorder(conn, sp["table"], sp["stock_column"], sp["reorder_column"])
    raise ValueError("no rule for report metric engine " + repr(engine) + " kind " + repr(sp.get("kind")))


def run_custom_action(conn, action, table, row_id, actor_role, inputs):
    """One declared button, run by the part its op names. The generic engine
    performs its own ops; 'clone' is the record_cloning part and
    'generate_document' the document_generation part, each guarded by the
    action's own declared 'who' and logged through the audit trail exactly as
    the generic engine logs its own."""
    effect = action.get("effect") or {{}}
    op = effect.get("op")
    if op in ("set_fields", "clear_fields", "reset_to_stage", "set_fields_from_input"):
        return custom_action_execution.run(conn, action, table, row_id, actor_role, inputs=inputs)
    who = action.get("who") or []
    if actor_role not in who:
        raise custom_action_execution.NotAllowed(
            f"{{actor_role!r}} may not press {{action.get('name')!r}}; declared: {{who}}")
    if op == "clone":
        new_id_ = record_cloning.clone(conn, table, row_id, overrides=effect.get("overrides") or {{}},
                                       title_column=effect.get("title_column"),
                                       title_suffix=effect.get("title_suffix"))
        if effect.get("overrides", {{}}).get("stage"):
            stage_history.record_transition(conn, table, new_id_, effect["overrides"]["stage"])
        audit_trail.record(conn, table, row_id, "custom:" + action["name"],
                           before={{}}, after={{"cloned_to": new_id_}})
        return {{"action": action["name"], "by": actor_role, "cloned_to": new_id_}}
    if op == "generate_document":
        row = conn.execute(f"SELECT * FROM [{{table}}] WHERE id = ?", (row_id,)).fetchone()
        if row is None:
            raise ValueError(f"{{table}}.id = {{row_id!r}} does not exist")
        row = dict(row)
        title = " ".join(str(row.get(c) or "") for c in effect.get("title_columns") or []).strip() or row_id
        lines_ = [f"{{c.replace('_', ' ')}}: {{row.get(c) if row.get(c) is not None else ''}}"
                  for c in effect.get("body_columns") or []]
        total = 0.0
        if effect.get("line_table"):
            cols = effect.get("line_columns") or []
            for item in conn.execute(f"SELECT * FROM [{{effect['line_table']}}] WHERE [{{effect['line_fk']}}] = ?",
                                     (row_id,)).fetchall():
                item = dict(item)
                lines_.append(" | ".join(str(item.get(c) if item.get(c) is not None else "") for c in cols))
                try:
                    total += float(item.get("quantity") or 0) * float(item.get("unit_amount") or 0)
                except (TypeError, ValueError):
                    pass
            lines_.append(f"Total: {{total:.2f}}")
        html_doc = document_generation.render_html(title, lines_)
        doc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
        os.makedirs(doc_dir, exist_ok=True)
        stamp = now_iso()
        pdf_path = os.path.join(doc_dir, f"{{table}}-{{row_id}}.pdf")
        document_generation.render_pdf(pdf_path, title, lines_)
        with open(os.path.join(doc_dir, f"{{table}}-{{row_id}}.html"), "w", encoding="utf-8") as fh:
            fh.write(html_doc)
        if effect.get("stamp_column"):
            conn.execute(f"UPDATE [{{table}}] SET [{{effect['stamp_column']}}] = ? WHERE id = ?", (stamp, row_id))
            conn.commit()
        audit_trail.record(conn, table, row_id, "custom:" + action["name"],
                           before={{}}, after={{"document": os.path.basename(pdf_path), "stamped": stamp}})
        return {{"action": action["name"], "by": actor_role, "document_html": html_doc,
                "document_pdf": "/documents/" + os.path.basename(pdf_path), "stamped": stamp, "total": total,
                # honest: the document is generated and the row stamped; there is no
                # outbound-mail part on the shelf, so nothing was emailed
                "email": "not dispatched: no outbound email part is on the shelf"}}
    raise custom_action_execution.UnknownOperation(f"no rule for op {{op!r}}")


def run_create_effects(conn, effects, row):
    """A record's own declared, executable effects of being created (the
    template's create_effects block). ledger_balance: the new Payment is
    applied to the Invoice/Bill it names; when the payments applied reach that
    target's total, the target's own declared automatic edge fires through the
    system_triggered_transition part. Returns what happened, for the response."""
    done = []
    for eff in effects or []:
        if eff.get("op") != "ledger_balance":
            raise ValueError("no executable rule for create effect " + repr(eff.get("op")))
        target_id = row.get(eff["link_column"])
        if not target_id:
            continue
        total_rule = eff["total"]
        if total_rule["kind"] == "lines":
            total = ledger_balancing.line_total(conn, total_rule["line_table"], total_rule["line_fk"], target_id,
                                                total_rule["quantity_column"], total_rule["amount_column"])
        else:
            found = conn.execute(f"SELECT [{{total_rule['column']}}] FROM [{{eff['table']}}] WHERE id = ?",
                                 (target_id,)).fetchone()
            total = found[0] if found else None
        applied = ledger_balancing.applied_total(conn, eff["payments_table"], eff["link_column"], target_id,
                                                 eff["amount_column"])
        settled = ledger_balancing.settles(conn, total, eff["payments_table"], eff["link_column"], target_id,
                                           eff["amount_column"])
        result = {{"op": "ledger_balance", "target": eff["table"], "target_id": target_id,
                  "total": total, "applied": applied, "settled": settled, "moved": None}}
        if settled:
            current = conn.execute(f"SELECT stage FROM [{{eff['table']}}] WHERE id = ?", (target_id,)).fetchone()
            try:
                stage_approval_gate.check_may_leave(conn, eff.get("approvals") or [], eff["table"], target_id,
                                                    current["stage"] if current else None)
                moved_from, moved_to = system_triggered_transition.fire(
                    conn, eff["table"], target_id, "stage", eff.get("transitions") or [], eff["event"])
                stage_history.record_transition(conn, eff["table"], target_id, moved_to)
                result["moved"] = {{"from": moved_from, "to": moved_to}}
            except (system_triggered_transition.NoSuchEvent, system_triggered_transition.IllegalTransition,
                    stage_approval_gate.NotApproved) as err:
                # already Paid, Voided, or not yet at the stage the edge leaves from: the
                # payment is recorded and applied; the target simply does not move
                result["moved"] = None
                result["not_moved_because"] = str(err)
        done.append(result)
    return done


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
        if path.startswith("/documents/"):
            self._serve_document(path[len("/documents/"):])
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

    def _serve_document(self, rel):
        doc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "documents")
        fp = os.path.join(doc_dir, rel)
        if not os.path.abspath(fp).startswith(os.path.abspath(doc_dir)) or not os.path.isfile(fp):
            respond(self, 404, {{"error": "not found"}}); return
        with open(fp, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf" if fp.endswith(".pdf") else "text/html; charset=utf-8")
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
    if method == "POST" and id_path and any(name.startswith(p) for p in ("event_", "move_", "approve_", "action_")):
        return f"self.{name}(path[len({path!r}):], self._body())"
    if method == "POST" and name.startswith("key_"):
        return f"self.{name}(self._body())"
    if method == "POST" and name.startswith("submit_"):
        return f"self.{name}(self._body())"
    if method == "GET" and name.startswith("report_"):
        return f"self.{name}()"
    if method == "GET" and id_path and (name.startswith("approval_status_") or name.startswith("history_")):
        return f"self.{name}(path[len({path!r}):])"
    if method == "POST" and name == "run_jobs":
        return f"self.{name}()"
    raise BuildRefused(f"no dispatch rule for {method} {path} -> {name}")


def build_app_py(spec, port):
    routes = (crud_routes(spec) + oauth_routes(spec) + api_key_routes(spec) + workflow_routes(spec)
              + custom_action_routes(spec) + form_routes(spec) + report_routes(spec)
              + notification_routes(spec))
    handlers = []
    dispatch = {"GET": [], "POST": [], "PUT": [], "DELETE": []}
    for method, path, name, ctx in routes:
        # connections_status has its own handler (below); every other route's
        # ctx is either an OAuth route (carries 'provider') or a CRUD route.
        if name != "connections_status":
            if name.startswith("approval_status_"):
                handlers.append(render_read_handler(name, ctx))
            elif any(name.startswith(p) for p in ("event_", "move_", "approve_")):
                handlers.append(render_workflow_handler(name, ctx))
            elif name.startswith("action_"):
                handlers.append(render_custom_action_handler(name, ctx))
            elif name.startswith("submit_"):
                handlers.append(render_form_submit_handler(name, ctx))
            elif name.startswith("report_"):
                handlers.append(render_report_handler(name, ctx))
            elif name.startswith("key_"):
                handlers.append(render_api_key_handler(name, ctx))
            elif ctx.get("provider"):
                handlers.append(render_oauth_handler(name, ctx))
            elif name.startswith("history_"):
                handlers.append(render_read_handler(name, ctx))
            elif name == "list_notifications":
                handlers.append(render_notification_handler(name, ctx))
            elif name == "run_jobs":
                handlers.append(render_jobs_handler(name, ctx))
            else:
                handlers.append(render_crud_handler(method, path, name, ctx))
        cond = f"path.startswith({path!r})" if path.endswith("/") else f"path == {path!r}"
        dispatch[method].append(f"        if {cond}:\n            {_dispatch_call(method, path, name)}; return\n")
    if spec["build_model"]["integrations"]:
        handlers.append(render_status_handler())

    src = APP_PRELUDE.format(spec_id=spec["spec_id"], title=spec["title"],
                             notification_decls_json=repr(notification_decls(spec)),
                             recurring_jobs_json=repr(job_decls(spec)))
    src += ENGINE_IMPORTS
    src += APP_ROUTER.format(
        get_dispatch="".join(dispatch["GET"]) or "        pass",
        post_dispatch="".join(dispatch["POST"]) or "        pass",
        put_dispatch="".join(dispatch["PUT"]) or "        pass",
        delete_dispatch="".join(dispatch["DELETE"]) or "        pass",
        handlers="\n".join(textwrap.indent(h, "    ") for h in handlers),
        port=port,
    )
    return src


# --------------------------------------------------------------------------- workflow / action / form / report generation
#: The real engines a generated app uses, copied byte-for-byte out of
#: packages/builder/engines/ into the app's own engines/ directory at build
#: time. The generated app calls the shelf's real code; it does not carry a
#: reimplementation of it.
VENDORED_ENGINES = ("audit_trail", "workflow_executor", "system_triggered_transition",
                     "custom_action_execution", "form_render_submit", "reporting_engine",
                     "stage_approval_gate", "stage_history", "stock_ledger", "record_cloning",
                     "ledger_balancing", "document_generation", "notification_delivery",
                     "scheduled_jobs")

ENGINE_IMPORTS = """
ENGINES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines")
if ENGINES_DIR not in sys.path:
    sys.path.insert(0, ENGINES_DIR)
import audit_trail, workflow_executor, system_triggered_transition
import custom_action_execution, form_render_submit, reporting_engine, stage_approval_gate
import stage_history, stock_ledger, record_cloning, ledger_balancing, document_generation
import notification_delivery, scheduled_jobs
"""


def _stage_names(wf):
    stages = wf.get("stages") or []
    if isinstance(stages, dict):
        stages = stages.get("stages") or []
    return [st["name"] if isinstance(st, dict) else st for st in stages]


#: The trigger kinds the Builder can really fire. A declared notification whose
#: trigger matches none of them is NOT dropped and NOT guessed at: it is carried
#: into the app as `unwired`, listed on the notifications route with the reason,
#: and named at build time. A person can see that it was asked for and is not
#: happening -- which is the honest state, and the opposite of a dead feature.
NOTIFY_KINDS = ("relative_to_date", "stage_reached", "record_created", "field_set",
                "custom_action", "threshold")


def _classify_notification(spec, name, n):
    """(kind, params, unwired_reason). Read off the notification's own declared
    N.01 trigger and the records/workflows the template really has -- never from
    the prose alone where a real declaration exists."""
    bm = spec["build_model"]
    trig = n.get("trigger") or {}
    if trig.get("kind") == "relative_to_date":
        record = trig.get("record")
        if record not in bm["records"]:
            return None, None, f"anchors on {record!r}, which is not a declared record"
        field = trig.get("date_field")
        if field not in bm["records"][record]["fields"]:
            return None, None, f"anchors on {field!r}, which is not a field of {record}"
        return "relative_to_date", {"table": table_name(record), "column": slug(field),
                                    "offset": trig.get("offset") or "+0 days"}, None
    event = (trig.get("event") or "").strip()
    if not event:
        return None, None, "declares no event to fire on"
    # a stage this template really declares, named in the event text
    for record in bm["records"]:
        wf = _workflow_for(spec, record)
        if not wf:
            continue
        for stage in _stage_names(wf):
            if re.search(r"\b" + re.escape(stage) + r"\b", event):
                return "stage_reached", {"table": table_name(record), "stage": stage}, None
    # a custom action this record really declares
    for record in bm["records"]:
        for act in _custom_actions_for(spec, record):
            nm = (act.get("detail") or {}).get("name")
            if nm and re.search(r"\b" + re.escape(nm) + r"\b", event):
                return "custom_action", {"table": table_name(record), "action": nm}, None
    # a record of this template being created
    for record in bm["records"]:
        if re.search(r"\b" + re.escape(record.lower()) + r"\b", event.lower()) and "creat" in event.lower():
            return "record_created", {"table": table_name(record)}, None
    # a field of this template being set or changed
    for record in bm["records"]:
        for field in bm["records"][record]["fields"]:
            if re.search(r"\b" + re.escape(field) + r"\b", event) and ("set" in event or "chang" in event):
                return "field_set", {"table": table_name(record), "column": slug(field)}, None
    # a two-field threshold the stock part already evaluates
    if "falls to or below" in event.lower():
        for record in bm["records"]:
            cols = {slug(f) for f in bm["records"][record]["fields"]}
            if {"stock_on_hand", "reorder_point"} <= cols:
                return "threshold", {"table": table_name(record)}, None
    return None, None, ("names no stage, action, record, field or threshold this app declares, "
                        "so the Builder has no rule that could fire it")


def notification_decls(spec):
    """Every declared notification, classified. Nothing is invented and nothing
    is silently dropped."""
    out = []
    for name, n in spec["build_model"]["notifications"].items():
        kind, params, why = _classify_notification(spec, name, n)
        out.append({"name": name, "id": n.get("id"), "kind": kind, "params": params or {},
                    "recipients": n.get("recipients") or [], "channels": n.get("channels") or [],
                    "unwired_reason": why})
    return out


def _parse_duration_seconds(text):
    """A duration phrase from a real R.14/FL.10 answer, turned into seconds --
    at build time, the same rule the generated app's own _parse_duration_seconds
    uses at run time. Returns None if it names no real duration (e.g. "forever")."""
    if not isinstance(text, str):
        return None
    m = re.match(r"\s*([\d.]+)\s*(second|minute|hour|day|week|month|year)s?\s*$", text.strip(), re.I)
    if not m:
        return None
    n = float(m.group(1)); unit = m.group(2).lower()
    scale = {"second": 1, "minute": 60, "hour": 3600, "day": 86400,
             "week": 604800, "month": 2629800, "year": 31557600}[unit]
    return n * scale


def _classify_recurring_op(spec, op):
    """(kind, params, unwired_reason) for one D11 recurring-ops entry, read off
    its own declared source and detail -- the same discipline as notifications:
    a duration, stage, field or target this op's own text does not really name
    is never guessed at, it is reported as unwired with the real reason."""
    bm = spec["build_model"]
    source, detail = op["source"], op["detail"]
    prefix, _, rest = source.partition(":")
    if prefix == "R.14":
        record = rest
        if record not in bm["records"]:
            return None, {}, f"names {record!r}, which is not a declared record"
        seconds = _parse_duration_seconds(detail)
        if seconds is None:
            return None, {}, f"retention is {detail!r} -- nothing to purge"
        return "purge", {"table": table_name(record), "duration": detail}, None
    if prefix == "FL.10":
        # FL.10's own text names a *workflow*, not a record (e.g.
        # "FL.10:Appointment lifecycle") -- resolved to its real record the
        # same mechanical way _workflow_for() does it (matching declared
        # stages), never by assuming the workflow's name is the record's name
        # (that assumption broke crm-pipeline's "Deal pipeline" once already).
        wf_obj = bm["workflows"].get(rest)
        if wf_obj is None:
            return None, {}, f"names workflow {rest!r}, which is not declared"
        record = next((r for r in bm["records"] if _workflow_for(spec, r) is wf_obj), None)
        if record is None:
            return None, {}, f"workflow {rest!r} is not the real lifecycle of any declared record"
        if not isinstance(detail, list) or not detail:
            return None, {}, "declares no timeout rule"
        rule = detail[0]
        from_stage, duration, then = rule.get("stage"), rule.get("duration"), (rule.get("then") or "")
        wf = _workflow_for(spec, record)
        stages = _stage_names(wf) if wf else []
        if from_stage not in stages:
            return None, {}, f"names stage {from_stage!r}, which {record} does not declare"
        field = None
        for f in bm["records"][record]["fields"]:
            words = [w for w in re.split(r"\W+", f.lower()) if w]
            if words and all(w in then.lower() for w in words):
                field = f; break
        to_stage = None
        for st in stages:
            if st != from_stage and re.search(r"\b" + re.escape(st) + r"\b", then):
                to_stage = st; break
        if not field or not to_stage:
            return None, {}, (f"{then!r} does not name both a declared field and a declared stage this "
                              f"Builder can match mechanically, so it will not guess which rows to move")
        negate = bool(re.search(r"\bun\w*\b", then.lower())) or re.search(r"\bnot\b", then.lower()) is not None
        seconds = _parse_duration_seconds(duration)
        if seconds is None:
            return None, {}, f"timeout duration {duration!r} is not a real duration"
        return "date_timeout", {"table": table_name(record), "from_stage": from_stage, "to_stage": to_stage,
                                "field": slug(field), "negate": negate, "duration": duration}, None
    if prefix == "N.01":
        name = rest
        n = bm["notifications"].get(name)
        if not n:
            return None, {}, f"names notification {name!r}, which is not declared"
        kind, params, why = _classify_notification(spec, name, n)
        if kind == "relative_to_date":
            return "due_reminder", dict(params, notif=name), None
        return None, {}, "fires at the moment of its own event, not on a schedule -- see /api/notifications"
    if prefix == "RP.08":
        enabled = isinstance(detail, dict) and str(detail.get("enabled", "no")).lower() == "yes"
        if not enabled:
            return None, {}, "declared but turned off -- no export runs"
        return None, {}, "export is declared enabled but no export engine is wired yet"
    if prefix == "FL.01":
        return None, {}, "describes who may create a record, not something to run on a timer"
    if prefix == "B.08":
        return None, {}, "needs a declared field or stage marking a 'repeated failure' this app does not have"
    if prefix == "FLX.03":
        return None, {}, "an integration event, not a scheduled job"
    return None, {}, f"source {source!r} has no scheduling rule"


def job_decls(spec):
    """Every declared recurring op, classified. Nothing invented, nothing
    silently dropped -- the same contract as notification_decls."""
    out = []
    for op in spec["build_model"].get("recurring_ops") or []:
        kind, params, why = _classify_recurring_op(spec, op)
        out.append({"id": op["id"], "name": op["source"], "kind": kind, "params": params,
                    "unwired_reason": why})
    return out


def notification_routes(spec):
    """Two routes every generated app gets, because every family declares
    notifications and recurring work and neither was reachable before:
      GET  /api/notifications  what has really been delivered, plus anything
                               declared that the Builder cannot fire, with why
      POST /api/jobs/run       runs the declared recurring work now and reports
                               what each item did (or why it did nothing)"""
    routes = [("GET", "/api/notifications", "list_notifications", {})]
    routes.append(("POST", "/api/jobs/run", "run_jobs", {}))
    return routes


def _workflow_for(spec, record):
    """The record's own workflow: the one whose declared stages are exactly the
    record's R.10 lifecycle stages -- the same rule check_template.py uses to
    validate R.10 ("has a workflow in the inventory with exactly those
    stages"). Name is a fallback only: the graph's default name is
    '<record> lifecycle', but a template may name it otherwise (crm-pipeline's
    'Deal pipeline'), and a record with no lifecycle has no workflow at all --
    found by every /api/moves route of crm-pipeline's Deal being missing."""
    rec = spec["build_model"]["records"].get(record) or {}
    lifecycle = rec.get("lifecycle") or {}
    if isinstance(lifecycle, dict) and lifecycle.get("has") == "yes" and lifecycle.get("stages"):
        wanted = list(lifecycle["stages"])
        for wf in spec["build_model"]["workflows"].values():
            if _stage_names(wf) == wanted:
                return wf
    return spec["build_model"]["workflows"].get(f"{record} lifecycle")


def _initial_stage(wf):
    """The stage a new row really starts in: the workflow's own declared
    initial, or the first of its declared stages. A workflow that declares
    neither gets no stage column rather than an invented default."""
    if not wf:
        return None
    if wf.get("initial"):
        return wf["initial"]
    stages = wf.get("stages") or []
    if isinstance(stages, dict):
        # the un-locked build_model nests {stages, initial, terminal} here;
        # a locked structure hoists initial/terminal and lists the stages
        return stages.get("initial") or (stages.get("stages") or [None])[0]
    if not stages:
        return None
    first = stages[0]
    return first["name"] if isinstance(first, dict) else first


def _custom_actions_for(spec, record):
    return [a for a in spec["build_model"]["actions_inventory"]
            if a["kind"] == "custom" and a.get("record") == record]


def workflow_routes(spec):
    """Routes for every numbered transition and approve action: the system's
    own events, a person's own moves, and the approval a gated stage waits
    for."""
    routes = []
    for record in spec["build_model"]["records"]:
        wf = _workflow_for(spec, record)
        if not wf:
            continue
        tbl = table_name(record)
        ctx = {"table": tbl, "record": record,
               "transitions": [{k: t[k] for k in ("from", "to", "mover", "event", "roles") if k in t}
                                for t in wf["transitions"]],
               "approvals": wf.get("approvals") or [],
               "on_reject": wf.get("on_reject") or {},
               # FL.08 made executable (the template's transition_effects): what the
               # app really does the moment a row enters a stage
               "effects": wf.get("effects") or []}
        for eff in ctx["effects"]:
            if eff.get("op") != "apply_order_lines":
                raise BuildRefused(f"{record} lifecycle: no generation rule for transition effect {eff.get('op')!r}")
        if any(t.get("mover") == "automatic" for t in wf["transitions"]):
            routes.append(("POST", f"/api/events/{tbl}/", "event_" + tbl, ctx))
        if any(t.get("mover") == "roles" for t in wf["transitions"]):
            routes.append(("POST", f"/api/moves/{tbl}/", "move_" + tbl, ctx))
        if wf.get("approvals"):
            routes.append(("POST", f"/api/approvals/{tbl}/", "approve_" + tbl, ctx))
            # the decision a row carries at its current stage, readable: a screen
            # can say "waiting for Operations" or "approved by Admin" truthfully
            routes.append(("GET", f"/api/approvals/{tbl}/", "approval_status_" + tbl, ctx))
    return routes


#: every custom-action op the generated app can really perform, and the part
#: that performs it: the generic engine's own ops, plus one op each for the
#: record_cloning and document_generation parts
CUSTOM_ACTION_OPS = {
    "set_fields": "custom_action_execution", "clear_fields": "custom_action_execution",
    "reset_to_stage": "custom_action_execution", "set_fields_from_input": "custom_action_execution",
    "clone": "record_cloning", "generate_document": "document_generation",
}


def custom_action_routes(spec):
    routes = []
    for record in spec["build_model"]["records"]:
        actions = _custom_actions_for(spec, record)
        if not actions:
            continue
        declared = {}
        for act in actions:
            detail = act.get("detail") or {}
            execution = detail.get("execution")
            if not execution:
                raise BuildRefused(
                    f"{act['id']}: custom action {detail.get('name')!r} declares no executable effect "
                    f"(an 'execution' block on its R.15 answer) — refusing to guess what the button does")
            op = execution.get("op")
            if op not in CUSTOM_ACTION_OPS:
                raise BuildRefused(
                    f"{act['id']}: custom action {detail.get('name')!r} declares op {op!r}; the Builder has "
                    f"rules for {sorted(CUSTOM_ACTION_OPS)} and will not approximate anything else")
            declared[detail["name"]] = {"name": detail["name"], "who": detail.get("who") or [],
                                        "effect": execution}
        routes.append(("POST", f"/api/actions/{table_name(record)}/", "action_" + table_name(record),
                        {"table": table_name(record), "actions": declared}))
    return routes


def form_routes(spec):
    routes = []
    for act in spec["build_model"]["actions_inventory"]:
        if act["kind"] != "submit":
            continue
        record = act.get("record")
        if not record or record not in spec["build_model"]["records"]:
            raise BuildRefused(f"{act['id']}: the form's target record is not declared — cannot generate a submit")
        fields = _form_fields(spec, act["form"], record)
        routes.append(("POST", f"/api/forms/{slug(act['form'])}", "submit_" + slug(act["form"]),
                        {"table": table_name(record), "fields": fields, "form": act["form"]}))
    return routes


def _form_fields(spec, form, record):
    """The record's own declared fields, in the order the form declares
    them. A form field that is not a field of its target record is refused
    rather than invented."""
    record_fields = spec["build_model"]["records"][record]["fields"]
    out = []
    for name in spec["build_model"]["forms"][form]:
        if name not in record_fields:
            raise BuildRefused(f"form {form!r} collects {name!r}, which is not a field of {record!r}")
        out.append(record_fields[name])
    return out


def report_routes(spec):
    routes = []
    for name, rep in spec["build_model"]["reports"].items():
        specs = rep.get("spec")
        if not specs:
            raise BuildRefused(
                f"report {name!r} has no executable ReportSpec — refusing to guess how its numbers are counted")
        routes.append(("GET", f"/api/reports/{slug(name)}", "report_" + slug(name),
                        {"report": name, "metrics": specs}))
    _check_report_specs(spec)
    return routes


def render_workflow_handler(name, ctx):
    transitions = json.dumps(ctx["transitions"])
    approvals = json.dumps(ctx["approvals"])
    on_reject = json.dumps(ctx["on_reject"])
    effects = repr(ctx.get("effects") or [])
    tbl = ctx["table"]
    if name.startswith("event_"):
        return textwrap.dedent(f'''\
            def {name}(self, row_id, body):
                """A declared automatic edge, fired by the system's own event."""
                transitions = {transitions}
                approvals = {approvals}
                conn = get_db()
                try:
                    row = conn.execute("SELECT stage FROM {tbl} WHERE id = ?", (row_id,)).fetchone()
                    if row is None:
                        return respond(self, 404, {{"error": "no such row"}})
                    try:
                        stage_approval_gate.check_may_leave(conn, approvals, "{tbl}", row_id, row["stage"])
                    except stage_approval_gate.NotApproved as err:
                        return respond(self, 409, {{"error": str(err), "waiting_for_approval": True}})
                    try:
                        moved_from, moved_to = system_triggered_transition.fire(
                            conn, "{tbl}", row_id, "stage", transitions, body.get("event"))
                    except system_triggered_transition.NoSuchEvent as err:
                        return respond(self, 400, {{"error": str(err)}})
                    except system_triggered_transition.IllegalTransition as err:
                        return respond(self, 409, {{"error": str(err)}})
                    stage_history.record_transition(conn, "{tbl}", row_id, moved_to)
                    done = run_transition_effects(conn, {effects}, "{tbl}", row_id, moved_to)
                    _row = dict(conn.execute("SELECT * FROM {tbl} WHERE id = ?", (row_id,)).fetchone())
                    notified = notify(conn, NOTIFICATION_DECLS, "stage_reached", table="{tbl}", row=_row, stage=moved_to)
                    respond(self, 200, {{"from": moved_from, "to": moved_to, "effects": done, "notified": notified}})
                finally:
                    conn.close()
            ''')
    if name.startswith("move_"):
        return textwrap.dedent(f'''\
            def {name}(self, row_id, body):
                """A declared person-moved edge, moved by one of its own roles."""
                transitions = {transitions}
                approvals = {approvals}
                conn = get_db()
                try:
                    row = conn.execute("SELECT stage FROM {tbl} WHERE id = ?", (row_id,)).fetchone()
                    if row is None:
                        return respond(self, 404, {{"error": "no such row"}})
                    try:
                        stage_approval_gate.check_may_leave(conn, approvals, "{tbl}", row_id, row["stage"])
                    except stage_approval_gate.NotApproved as err:
                        return respond(self, 409, {{"error": str(err), "waiting_for_approval": True}})
                    try:
                        workflow_executor.transition(conn, "{tbl}", row_id, "stage", transitions,
                                                     body.get("to"), body.get("role"))
                    except workflow_executor.IllegalTransition as err:
                        return respond(self, 409, {{"error": str(err)}})
                    stage_history.record_transition(conn, "{tbl}", row_id, body.get("to"))
                    done = run_transition_effects(conn, {effects}, "{tbl}", row_id, body.get("to"))
                    _row = dict(conn.execute("SELECT * FROM {tbl} WHERE id = ?", (row_id,)).fetchone())
                    notified = notify(conn, NOTIFICATION_DECLS, "stage_reached", table="{tbl}", row=_row, stage=body.get("to"))
                    respond(self, 200, {{"from": row["stage"], "to": body.get("to"), "effects": done, "notified": notified}})
                finally:
                    conn.close()
            ''')
    return textwrap.dedent(f'''\
        def {name}(self, row_id, body):
            """The decision a gated stage is waiting for. A decline sends the
            record to the workflow's own declared back_to stage."""
            approvals = {approvals}
            on_reject = {on_reject}
            conn = get_db()
            try:
                row = conn.execute("SELECT stage FROM {tbl} WHERE id = ?", (row_id,)).fetchone()
                if row is None:
                    return respond(self, 404, {{"error": "no such row"}})
                try:
                    stage_approval_gate.decide(conn, approvals, "{tbl}", row_id, row["stage"],
                                               body.get("decision"), body.get("by"), body.get("reason"))
                except (stage_approval_gate.NotApprover, stage_approval_gate.NotAnApprover) as err:
                    return respond(self, 403, {{"error": str(err)}})
                except stage_approval_gate.NotApproved as err:
                    return respond(self, 409, {{"error": str(err)}})
                except ValueError as err:
                    return respond(self, 400, {{"error": str(err)}})
                if body.get("decision") == stage_approval_gate.DECLINED and on_reject.get("back_to"):
                    conn.execute("UPDATE {tbl} SET stage = ? WHERE id = ?", (on_reject["back_to"], row_id))
                    conn.commit()
                    stage_history.record_transition(conn, "{tbl}", row_id, on_reject["back_to"])
                    return respond(self, 200, {{"decision": "DECLINED", "stage": on_reject["back_to"]}})
                respond(self, 200, {{"decision": body.get("decision"), "stage": row["stage"]}})
            finally:
                conn.close()
        ''')


def render_read_handler(name, ctx):
    tbl = ctx["table"]
    if name.startswith("approval_status_"):
        approvals = json.dumps(ctx["approvals"])
        return textwrap.dedent(f'''\
            def {name}(self, row_id):
                """The gate (if any) at the row's current stage and the latest real
                decision recorded for it -- read, never assumed."""
                approvals = {approvals}
                conn = get_db()
                try:
                    row = conn.execute("SELECT stage FROM {tbl} WHERE id = ?", (row_id,)).fetchone()
                    if row is None:
                        return respond(self, 404, {{"error": "no such row"}})
                    gate = stage_approval_gate.gate_for(approvals, row["stage"])
                    decision = stage_approval_gate.decision_for(conn, "{tbl}", row_id, row["stage"]) if gate else None
                    respond(self, 200, {{"stage": row["stage"], "gate": gate, "decision": decision}})
                finally:
                    conn.close()
            ''')
    return textwrap.dedent(f'''\
        def {name}(self, row_id):
            """The row's own real trail, oldest first."""
            conn = get_db()
            try:
                trail = audit_trail.history_for(conn, "{tbl}", row_id)
                stages = [dict(r) for r in conn.execute(
                    "SELECT stage, entered_at FROM _stage_history WHERE record_table = ? AND row_id = ? ORDER BY entered_at",
                    ("{tbl}", str(row_id))).fetchall()]
                respond(self, 200, {{"audit": trail, "stages": stages}})
            finally:
                conn.close()
        ''')


def render_custom_action_handler(name, ctx):
    body = """
def NAME(self, tail, body):
    \"\"\"A record's own declared extra button, run by the real
    custom_action_execution engine.\"\"\"
    declared = ACTIONS
    row_id, _, action_name = tail.partition("/")
    action_name = urllib.parse.unquote(action_name)
    action = declared.get(action_name)
    if action is None:
        return respond(self, 404, {"error": "no declared action " + repr(action_name)})
    conn = get_db()
    try:
        try:
            result = run_custom_action(conn, action, TABLE, row_id, body.get("role"), body.get("inputs") or {})
        except custom_action_execution.NotAllowed as err:
            return respond(self, 403, {"error": str(err)})
        except custom_action_execution.UnknownOperation as err:
            return respond(self, 400, {"error": str(err)})
        except ValueError as err:
            return respond(self, 400 if "needs a value" in str(err) else 404, {"error": str(err)})
        _row = conn.execute("SELECT * FROM " + TABLE + " WHERE id = ?", (row_id,)).fetchone()
        if _row is not None:
            result["notified"] = notify(conn, NOTIFICATION_DECLS, "custom_action",
                                        table=TABLE, row=dict(_row), action=action_name)
        respond(self, 200, result)
    finally:
        conn.close()
"""
    return (body.replace("NAME", name)
                .replace("ACTIONS", json.dumps(ctx["actions"]))
                .replace("TABLE", repr(ctx["table"])).lstrip("\n"))


def render_form_submit_handler(name, ctx):
    body = """
def NAME(self, body):
    \"\"\"A real submission of the FORM form, validated against the target
    record's own declared fields.\"\"\"
    fields = FIELDS
    conn = get_db()
    try:
        try:
            now = now_iso()
            row_id = form_render_submit.submit(conn, TABLE, fields, body, row_id=new_id(),
                                               extra={"created_at": now, "updated_at": now})
        except form_render_submit.FieldNotDeclared as err:
            return respond(self, 400, {"error": str(err)})
        except form_render_submit.MissingRequired as err:
            return respond(self, 400, {"error": str(err)})
        except form_render_submit.NotUnique as err:
            return respond(self, 409, {"error": str(err)})
        respond(self, 201, {"id": row_id})
    finally:
        conn.close()
"""
    return (body.replace("NAME", name)
                .replace("FIELDS", json.dumps(ctx["fields"]))
                .replace("TABLE", repr(ctx["table"]))
                .replace("FORM", ctx["form"]).lstrip("\n"))


def render_notification_handler(name, ctx):
    return textwrap.dedent(f"""\
        def {name}(self):
            \"\"\"What has really been delivered (the real _notifications table),
            plus every declared notification the Builder cannot fire, with the
            real reason -- nothing declared is left unlisted.\"\"\"
            conn = get_db()
            try:
                delivered = [dict(r) for r in conn.execute(
                    "SELECT recipient, subject, body, channel, delivered_at FROM _notifications "
                    "ORDER BY delivered_at DESC").fetchall()]
                unwired = [d for d in NOTIFICATION_DECLS if d.get("kind") is None]
                respond(self, 200, {{"delivered": delivered, "declared": NOTIFICATION_DECLS, "unwired": unwired}})
            finally:
                conn.close()
        """)


def render_jobs_handler(name, ctx):
    return textwrap.dedent(f"""\
        def {name}(self):
            \"\"\"Runs every declared recurring job this Builder can really
            execute, against the real database, right now. A declared job it
            cannot run is reported with the real reason, never skipped
            silently and never guessed at.\"\"\"
            conn = get_db()
            try:
                results = [run_job(conn, NOTIFICATION_DECLS, j) for j in RECURRING_JOBS]
                respond(self, 200, {{"ran_at": now_iso(), "results": results}})
            finally:
                conn.close()
        """)


#: report metric engines the generated app can really run: the generic
#: reporting engine (no "engine" key, or "reporting_engine"), and the two
#: specialist parts with a report-shaped function each
REPORT_ENGINES = {
    None: {None}, "reporting_engine": {None},
    "stage_history": {"rate_over_last_days", "line_value_by_month"},
    "stock_ledger": {"count_at_or_below_reorder"},
}


def _check_report_specs(spec):
    for name, rep_ in spec["build_model"]["reports"].items():
        for entry in rep_.get("spec") or []:
            sp = entry.get("spec") or {}
            engine, kind = sp.get("engine"), sp.get("kind")
            if engine not in REPORT_ENGINES or (engine and kind not in REPORT_ENGINES[engine]):
                raise BuildRefused(f"report {name!r} metric {entry.get('metric')!r}: no generation rule for "
                                   f"engine={engine!r} kind={kind!r}")


def render_report_handler(name, ctx):
    metrics = json.dumps(ctx["metrics"])
    return textwrap.dedent(f'''\
        def {name}(self):
            """Every one of this report's declared metrics, each run for real
            by the part its spec names: the generic reporting engine, or the
            stage_history / stock_ledger part for the shapes it cannot express."""
            metrics = {metrics}
            conn = get_db()
            try:
                out = {{}}
                for entry in metrics:
                    out[entry["metric"]] = run_report_metric(conn, entry["spec"])
                respond(self, 200, out)
            finally:
                conn.close()
        ''')


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
    """One real HTML file per numbered screen (SCR-nnn). Five screen kinds have
    a rendering rule: integration_status, list, detail, form (rendered by the
    real form_render_submit part from the target record's own declared fields)
    and report (which fetches its real numbers from the generated report
    route). Any other kind is refused rather than rendered as a placeholder
    that would look done and is not."""
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
        elif scr["kind"] == "form":
            page = _render_form_screen(bm, scr)
        elif scr["kind"] == "report":
            page = _render_report_screen(bm, scr)
        else:
            raise BuildRefused(f"{scr['id']}: no screen rendering rule for kind '{scr['kind']}'")
        pages[scr["id"]] = _inject_header(page, header_html, header_style)
    first_screen_id = bm["screens_inventory"][0]["id"] if bm["screens_inventory"] else None
    pages["index.html"] = pages.get(first_screen_id, "<!doctype html><title>App</title><p>No screens.</p>")
    return pages


def _render_form_screen(bm, scr):
    """The real form, rendered by the real form_render_submit part from the
    target record's own declared fields — the same function the submit route
    validates against, so the screen and the route cannot drift apart."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines"))
    import form_render_submit
    form = scr["form"]
    record = scr.get("record")
    if not record or record not in bm["records"]:
        raise BuildRefused(f"{scr['id']}: the form's target record is not declared")
    fields = [bm["records"][record]["fields"][name] for name in bm["forms"][form]
              if name in bm["records"][record]["fields"]]
    body = form_render_submit.render_form(record, fields, f"/api/forms/{slug(form)}")
    # a link field is a real reference: its select is filled from the target
    # record's own real rows at page load, never from a baked-in list
    links = {form_render_submit._slug(f["name"]): table_name(f["target_record"])
             for f in fields if f.get("type") == "link" and f.get("target_record")}
    link_script = ("<script>const LINKS = " + json.dumps(links) + ";"
                   "Object.entries(LINKS).forEach(async ([field, table]) => {"
                   "const res = await fetch('/api/' + table); const rows = await res.json();"
                   "const sel = document.getElementById(field);"
                   "sel.innerHTML = rows.map(r => '<option value=\"' + r.id + '\">' +"
                   "((r.name || r.topic || r.service || r.id)) + '</option>').join('');"
                   "});</script>")
    script = ("<script>document.querySelector('form').addEventListener('submit', async e => {"
              "e.preventDefault();"
              "const data = Object.fromEntries(new FormData(e.target).entries());"
              "const r = await fetch(e.target.action, {method:'POST',"
              "headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});"
              "const out = await r.json();"
              "document.getElementById('result').textContent = r.ok ? ('saved ' + out.id) : out.error;"
              "});</script>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{form}</title></head><body>"
            f"{body}<p id='result'></p>{link_script}{script}</body></html>")


def _render_report_screen(bm, scr):
    """A real report screen: it fetches this report's real numbers from the
    generated route and renders them. No number is baked into the page."""
    name = scr["report"]
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{name}</title></head><body>"
            f"<h1>{name}</h1><table id='numbers'></table>"
            f"<script>fetch('/api/reports/{slug(name)}').then(r => r.json()).then(d => {{"
            f"document.getElementById('numbers').innerHTML = Object.entries(d).map(([metric, value]) => "
            f"'<tr><td>' + metric + '</td><td class=\\'value\\'>' + JSON.stringify(value) + '</td></tr>'"
            f").join('');}});</script></body></html>")


def _render_api_key_screen(name):
    """A linked service that authenticates with a pasted key: a real field and
    a real POST to the real key route. No OAuth button, because there is no
    OAuth round trip to start."""
    return textwrap.dedent(f"""\
        <!doctype html>
        <title>{name}</title>
        <style>body{{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px}}</style>
        <h1>{name}</h1>
        <p>This service authenticates with a key you paste in.</p>
        <form id="keyform">
          <input id="key" name="key" type="password" placeholder="API key" required>
          <button type="submit">Save key</button>
        </form>
        <p id="state"></p>
        <script>
        document.getElementById('keyform').addEventListener('submit', async e => {{
          e.preventDefault();
          const res = await fetch('/api/connections/{slug(name)}/key', {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{key: document.getElementById('key').value}})}});
          const out = await res.json();
          document.getElementById('state').textContent = res.ok ? out.state : out.error;
        }});
        </script>
        """)


def _render_integration_screen(bm, scr):
    name = scr["integration"]
    flx = bm["integrations"][name]
    if flx.get("auth") == "api_key":
        return _render_api_key_screen(name)
    provider = _resolve_provider(name, flx)
    slug_ = slug(provider)
    # FLX.05 is answered as a plain choice ("continue_without"), not a dict; a
    # dict with its own message is also accepted.
    unavailable = flx.get("on_unavailable") or {}
    if not isinstance(unavailable, dict):
        unavailable = {}          # FLX.05 is answered as a plain choice, not a dict
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
    """The record's fields, editable where the record grants edit -- and, for
    a record with a lifecycle, its stage and every control a person really
    has: the declared person-moved transitions out of the current stage, the
    approval a gated stage waits for, and the record's declared custom
    actions. Which role presses them is chosen on the screen (the generated
    app has no sign-in); the routes enforce the declared roles exactly as
    before. This closes the gap the seam journeys found: "the generated
    screens carry no lifecycle stage and no action controls"."""
    record = scr["record"]
    tbl = table_name(record)
    fields = list(bm["records"][record]["fields"])
    can_edit = bool(bm["records"][record]["access"].get("edit"))
    wf = _workflow_for({"build_model": bm}, record)
    slugs_js = json.dumps([slug(f) for f in fields])
    rows_html = "".join(f'<tr><th>{f}</th><td><span data-field="{slug(f)}"></span></td></tr>' for f in fields)
    if wf:
        rows_html += '<tr><th>Stage</th><td><span data-field="stage"></span></td></tr>'
    save_btn = '<button id="save" hidden>Save</button>' if can_edit else ""
    save_js = "" if not can_edit else textwrap.dedent(f"""
        document.getElementById('save').hidden = false;
        document.getElementById('save').onclick = async () => {{
          const body = {{}};
          for (const key of FIELD_KEYS) body[key] = document.querySelector(`[data-field="${{key}}"]`).textContent;
          const res = await fetch('/api/{tbl}/' + id, {{method: 'PUT', body: JSON.stringify(body)}});
          document.getElementById('state').textContent = res.ok ? 'Saved.' : 'Save failed.';
        }};""")
    transitions = json.dumps([{k: t[k] for k in ("from", "to", "mover", "roles") if k in t} for t in (wf["transitions"] if wf else [])])
    approvals = json.dumps((wf.get("approvals") if wf else None) or [])
    actions = json.dumps([{"name": a["name"], "who": a.get("who") or [], "inputs": ((a.get("execution") or {}).get("fields") or []) if (a.get("execution") or {}).get("op") == "set_fields_from_input" else []}
                          for a in _custom_actions_for({"build_model": bm}, record) and [x["detail"] for x in _custom_actions_for({"build_model": bm}, record)]])
    controls_js = textwrap.dedent(f"""
        const TRANSITIONS = {transitions}, APPROVALS = {approvals}, ACTIONS = {actions};
        async function post(path, body) {{
          const res = await fetch(path, {{method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(body)}});
          const out = await res.json().catch(() => ({{}}));
          if (res.ok) await load();   // re-read first: load() hides the state line on success
          const st = document.getElementById('state');
          st.hidden = false;
          st.textContent = res.ok ? 'Done.' : (out.error || 'Refused.');
        }}
        function renderControls(row) {{
          // every declared control, labelled with the role the declaration names:
          // the generated app has no sign-in, so the press carries that role and
          // the route still refuses anything the declaration does not allow
          const box = document.getElementById('controls'); box.innerHTML = '';
          for (const t of TRANSITIONS.filter(t => t.mover === 'roles' && t.from === row.stage)) {{
            const r = (t.roles || [])[0];
            const b = document.createElement('button'); b.textContent = 'Move to ' + t.to + ' (as ' + r + ')'; b.dataset.move = t.to;
            b.onclick = () => post('/api/moves/{tbl}/' + id, {{to: t.to, role: r}}); box.appendChild(b);
          }}
          const gate = APPROVALS.find(g => g.stage === row.stage);
          if (gate) {{
            const r = (gate.approvers || [])[0];
            for (const d of ['APPROVED', 'DECLINED']) {{
              const b = document.createElement('button'); b.textContent = (d === 'APPROVED' ? 'Approve' : 'Decline') + ' (as ' + r + ')';
              b.onclick = () => post('/api/approvals/{tbl}/' + id, {{decision: d, by: r}}); box.appendChild(b);
            }}
          }}
          for (const a of ACTIONS) {{
            const r = (a.who || [])[0];
            const b = document.createElement('button'); b.textContent = a.name + ' (as ' + r + ')';
            b.onclick = () => {{
              const inputs = {{}};
              for (const f of a.inputs) {{ const v = window.prompt(f.replace(/_/g, ' ')); if (v === null) return; inputs[f] = v; }}
              post('/api/actions/{tbl}/' + id + '/' + encodeURIComponent(a.name), {{role: r, inputs}});
            }};
            box.appendChild(b);
          }}
        }}""")
    return textwrap.dedent(f"""\
        <!doctype html>
        <title>{record}</title>
        <style>body{{font-family:system-ui,sans-serif;max-width:600px;margin:40px auto}}
        table{{border-collapse:collapse}} th,td{{border:1px solid #ccc;padding:6px;text-align:left}}
        [data-field]{{outline:none}} #controls{{margin:12px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
        #controls button{{padding:6px 12px;cursor:pointer}}</style>
        <h1>{record} detail</h1>
        <div id="state">Loading…</div>
        <table id="fields" hidden>{rows_html}</table>
        <div id="controls"></div>
        {save_btn}
        <script>
        const FIELD_KEYS = {slugs_js};
        const id = new URLSearchParams(window.location.search).get('id');
        {controls_js}
        async function load() {{
          const state = document.getElementById('state');
          try {{
            const res = await fetch('/api/{tbl}/' + id);
            if (!res.ok) throw new Error('not found');
            const row = await res.json();
            for (const key of FIELD_KEYS) {{
              document.querySelector(`[data-field="${{key}}"]`).textContent = row[key] ?? '';
            }}
            const st = document.querySelector('[data-field="stage"]');
            if (st) st.textContent = row.stage ?? '';
            renderControls(row);
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


# --------------------------------------------------------------------------- manifest
def parts_used(spec):
    """The shelf parts a build of this spec actually exercises, derived from
    what the spec declares — never from a list kept by hand. Every engine in
    VENDORED_ENGINES is copied into the app regardless (the generated app
    imports them all), but a part the spec gives nothing to do is vendored,
    not used, and the manifest says which is which."""
    bm = spec["build_model"]
    used = []
    if bm.get("records"):
        used.append("crud_list_detail")
    # the same split oauth_routes / api_key_routes make: a pasted key is
    # api_key; every other integration is an OAuth round trip
    auths = {("api_key" if i.get("auth") == "api_key" else "oauth") for i in bm.get("integrations", {}).values()}
    if "oauth" in auths:
        used.append("oauth_connect")
    if "api_key" in auths:
        used.append("api_key_connect")
    if any(s["kind"] == "form" for s in bm.get("screens_inventory", [])):
        used.append("form_render_submit")
    if bm.get("reports"):
        used.append("reporting_engine")
    person_moves = any(a["kind"] == "transition" and a.get("mover") != "automatic" for a in bm.get("actions_inventory", []))
    system_moves = any(t.get("mover") == "automatic" and t.get("event")
                       for wf in bm.get("workflows", {}).values() for t in wf.get("transitions", []))
    approvals = any(wf.get("approvals") for wf in bm.get("workflows", {}).values())
    customs = any(a["kind"] == "custom" and (a.get("detail") or {}).get("execution") for a in bm.get("actions_inventory", []))
    if person_moves:
        used.append("workflow_executor")
    if system_moves:
        used.append("system_triggered_transition")
    if approvals:
        used.append("stage_approval_gate")
    if customs:
        used.append("custom_action_execution")
    if person_moves or system_moves or customs:
        used.append("audit_trail")  # every move and every pressed action is logged through it
    if bm.get("workflows"):
        used.append("stage_history")  # every stage entry is recorded, from creation on
    ops = {(a.get("detail") or {}).get("execution", {}).get("op") for a in bm.get("actions_inventory", [])
           if a["kind"] == "custom"}
    if "clone" in ops:
        used.append("record_cloning")
    if "generate_document" in ops:
        used.append("document_generation")
    if any(e.get("op") == "apply_order_lines" for wf in bm.get("workflows", {}).values() for e in wf.get("effects") or []):
        used.append("stock_ledger")
    if any(e.get("op") == "ledger_balance" for r in bm.get("records", {}).values() for e in r.get("on_create") or []):
        used.append("ledger_balancing")
    return used


def build_manifest(spec):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import shelf as shelf_lib
    shelf = shelf_lib.load_shelf()
    by_id = {p["part_id"]: p for p in shelf["parts"]}
    def pins_for(ids):
        out = []
        for part_id in ids:
            if part_id not in by_id:
                raise BuildRefused(f"the Builder uses part '{part_id}' but it is not on the shelf")
            out.append(shelf_lib.pin(by_id[part_id]))
        return out
    return {
        "spec_id": spec["spec_id"],
        "required_status_for_deployable": shelf_lib.REQUIRED_STATUS_FOR_DEPLOYABLE,
        "parts": pins_for(parts_used(spec)),          # what this app exercises: the Definition of Done reads these
        "vendored": pins_for(VENDORED_ENGINES),      # every engine copied into the app, used or not
    }


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
    for generator in (api_key_routes, workflow_routes, custom_action_routes, form_routes, report_routes):
        try:
            generator(spec)
        except BuildRefused as e:
            unsupported.append(str(e))
    if unsupported:
        raise BuildRefused("cannot build — no generation rule for:\n" + "\n".join(f"  - {u}" for u in unsupported))

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "static"), exist_ok=True)

    # the shelf's real engines, copied byte-for-byte — the generated app runs
    # the same code the parts shelf proved, not a reimplementation of it
    engines_out = os.path.join(out_dir, "engines")
    os.makedirs(engines_out, exist_ok=True)
    engines_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines")
    for module in VENDORED_ENGINES:
        shutil.copyfile(os.path.join(engines_src, f"{module}.py"),
                        os.path.join(engines_out, f"{module}.py"))
    # the application manifest: exactly which shelf parts, at exactly which
    # source revision and lifecycle status, this app was assembled from. Written
    # from the shelf's own identity function, never typed here, so a later
    # reader can tell whether the shelf has moved on (drift) and whether
    # anything in the app was built on a part no real browser has yet driven.
    open(os.path.join(out_dir, "MANIFEST.json"), "w").write(json.dumps(build_manifest(spec), indent=1) + "\n")

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
