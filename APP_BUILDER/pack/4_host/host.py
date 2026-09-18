#!/usr/bin/env python3
"""
host.py -- the host. Serves the shelf.

This is the join between the two halves. On one side: harvested capabilities
sitting on the shelf, each a whole real module with a number. On the other: a
running web server. Until now nothing connected them.

A harvested part stands on its source package -- that is what the whole-module
harvest proved. So the host does not try to run the part in a vacuum. It builds
the source application's own stack, then serves ONLY the routes that belong to
capabilities on the shelf. Everything else the source app happens to ship is
refused.

That is what makes this a host and not just the source app running: the shelf
decides what exists.

  Usage:
      python3 host.py                     # serve on HOST_PORT
      python3 host.py --check             # list what would be served, exit
      python3 host.py --app event-ticketing

  Exit 0 = every shelf capability resolved to a live route.
  Exit 1 = at least one did not. The report says which.
"""

# =====================================================================
# RULES / CONFIG  -- edit these, nothing below this block
# =====================================================================

APP_SLUG = "event-ticketing"
# Which app on the shelf this host serves. One host, one app. Change this to
# stand up a different app from the same shelf.

SHELF_DIR = "shelf"
# Where the harvested capabilities live. Must be the same shelf
# harvest_parts.py wrote and shelf_records.py recorded.

FORMS_DIR = "forms"
# Where the filled harvest form lives. The host reads the recorded route and
# method for each capability from here, and verifies them against what the
# source application actually serves.

HOST_PORT = 8000
# Port the host listens on.

HOST_BIND = "127.0.0.1"
# Address the host binds to. 0.0.0.0 exposes it beyond this machine.

RUNTIME_FACTORY_FIELD = "app_factory"
# Which field of the app's own form names the callable that builds the
# runtime its parts need. The host does not know or care which app that
# is -- it reads it. If altered: the host looks in that field instead.
# The source application's own app factory, as module:function. This is what
# builds the stack a harvested part stands on -- its database session, its
# request handling, its models. Change this when the app slug's source repo
# changes. Rule E means one source repo per app, so there is exactly one.

RUNTIME_LOADER_FIELD = "models_loader"
# Which field of the form names the callable that must run before a part
# can be loaded, where the app needs one. Blank in the form means none.
# If altered: the host looks in that field instead.
# Some sources register their database models lazily, so a harvested module
# fails to import until every model is loaded. Blank this out if the source
# has no such function.

BIND_SHELF_PARTS = True
# True  = the shelf's own copy of a part is the code that serves its route.
#         Empty a part and its capability dies, which is what makes a repair
#         land somewhere that matters.
# False = the route is served by whatever the runtime already had behind it,
#         and the part file is never executed. Do not turn this off.

PART_FILENAME = "source.py"
# The file inside a capability's shelf directory that holds the part.

PROVENANCE_FILENAME = "PROVENANCE.json"
# The file beside it that records where the part came from.

PART_ENTRY_FIELD = "source_symbol"
# Which field of that provenance names the part's entry point. The host reads
# it rather than being told per app. If altered: it looks in that field.

RUNTIME_ADAPTER_FIELD = "view_adapter"
# Which field of the app's own form names how a part's entry point is turned
# into something servable, where the part needs adapting. That is a property
# of the runtime the part was written for, so it lives with the app, not here.
# Blank in the form means the entry point is already servable.

RESTRICT_TO_SHELF = True
# True  = only routes belonging to a shelf capability are served. Everything
#         else the source app ships returns 404. This is the point of the
#         host: the shelf decides what the app is.
# False = serve the whole source application. Useful for seeing what is
#         available before deciding what to put on the shelf.

TRAILING_SLASH_TOLERANT = True
# True  = a recorded route of '/x' matches a live route of '/x/' and vice
#         versa. Source apps are inconsistent about this and a mismatch would
#         otherwise report a live route as missing.

SERVE_STATIC = True
# True = the source app's static files are served too. Turn this off and any
#        page that references a stylesheet renders unstyled.

STATIC_ENDPOINT_NAMES = ("static", "assets")
# Blueprint names in the source application that serve stylesheets, scripts,
# fonts and images. A route belonging to one of these is kept even though no
# shelf capability claims it, because a page without its stylesheet is not the
# capability working. Keyed on the endpoint rather than the path: a source app
# may serve every asset through one converter rule whose path matches no
# literal prefix. Add a name here if a source application serves its assets
# from a differently-named blueprint.

FAIL_ON_UNRESOLVED = True
# True  = if any shelf capability has no matching live route, the host reports
#         it and exits rather than starting up half-served.
# False = start anyway and serve what resolved.

STAMP_HEADER = "X-Shelf-Capability"
# Every response served by a shelf capability carries this header naming the
# capability number that served it. This is how you tell a handler answering
# "not found" apart from the host refusing a route that is not on the shelf --
# the first carries the header, the second does not. Blank it out to stop
# stamping.

QUIET_SOURCE_LOGGING = True
# True = suppress the source application's own logging noise so the host's
#        report is readable. Its errors still surface as status codes.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import sys
import importlib.util
import json
import glob
import importlib


def load_symbol(spec):
    """'module.path:name' -> the actual object."""
    if not spec or ":" not in spec:
        return None
    mod_name, _, attr = spec.partition(":")
    mod = importlib.import_module(mod_name)
    return getattr(mod, attr)


def read_form(app_slug):
    """The filled harvest form for this app, or None."""
    for path in sorted(glob.glob(os.path.join(FORMS_DIR, "*.form.json"))):
        with open(path) as f:
            form = json.load(f)
        if form.get("app_slug") == app_slug:
            return form, path
    return None, None


def read_shelf_caps(app_slug):
    """Capability numbers actually sitting on the shelf for this app."""
    app_dir = os.path.join(SHELF_DIR, app_slug)
    if not os.path.isdir(app_dir):
        return []
    out = []
    for cap_id in sorted(os.listdir(app_dir)):
        src = os.path.join(app_dir, cap_id, "source.py")
        if os.path.exists(src):
            out.append(cap_id)
    return out


def normalise(route):
    """Compare routes without arguing about a trailing slash."""
    if not route:
        return ""
    if TRAILING_SLASH_TOLERANT:
        return route.rstrip("/") or "/"
    return route


def build_source_app(form):
    """Build the source application's own stack -- what a part stands on."""
    src = form.get("harvest_source") or {}
    models_loader = src.get(RUNTIME_LOADER_FIELD) or ""
    app_factory = src.get(RUNTIME_FACTORY_FIELD) or ""
    if not app_factory:
        print(f"REFUSED: the form for {APP_SLUG!r} names no "
              f"{RUNTIME_FACTORY_FIELD} -- the host cannot build a runtime it "
              f"has not been told about, and will not guess one")
        sys.exit(2)
    if models_loader:
        loader = load_symbol(models_loader)
        if loader:
            loader()
    factory = load_symbol(app_factory)
    if factory is None:
        print(f"REFUSED: {RUNTIME_FACTORY_FIELD} {app_factory!r} did not resolve")
        sys.exit(1)
    return factory()


def bind_shelf_parts(app, resolved, app_slug, form):
    """
    Make the shelf's own copy of each part the code that actually serves its
    route.

    Without this the shelf decides only WHICH routes are served, while the
    code behind them is the source application's -- so a part could be emptied
    and nothing would notice, and a repair would have nowhere to land. Binding
    the shelf copy is what makes the part file the thing that runs.

    Each part names its own entry symbol in its PROVENANCE.json. Nothing here
    knows which application a part came from.
    """
    bound, skipped = [], []
    for r in resolved:
        cap_id = r["cap_id"]
        cap_dir = os.path.join(SHELF_DIR, app_slug, cap_id)
        src = os.path.join(cap_dir, PART_FILENAME)
        prov_path = os.path.join(cap_dir, PROVENANCE_FILENAME)
        if not (os.path.isfile(src) and os.path.isfile(prov_path)):
            skipped.append((cap_id, "no part file or no provenance"))
            continue
        try:
            with open(prov_path) as fh:
                symbol_name = (json.load(fh) or {}).get(PART_ENTRY_FIELD) or ""
        except Exception as exc:
            skipped.append((cap_id, f"provenance unreadable: {exc}"))
            continue
        if not symbol_name:
            skipped.append((cap_id, f"provenance names no {PART_ENTRY_FIELD}"))
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                f"shelf_{cap_id.replace('-', '_')}", src)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
        except Exception as exc:
            skipped.append((cap_id, f"part did not load: {type(exc).__name__}: {exc}"))
            continue
        # A provenance record may name more than one symbol, separated by "/",
        # where the capability was harvested as a handler plus what it calls.
        # A name may also be dotted, where it points at a method. What gets
        # bound is the class that serves the route, so the longest dotted
        # prefix that resolves to a class is what is taken -- never a guess at
        # a name the provenance does not contain.
        entry = None
        for candidate in [s.strip() for s in symbol_name.split("/") if s.strip()]:
            obj, found = mod, None
            for seg in candidate.split("."):
                obj = getattr(obj, seg, None)
                if obj is None:
                    break
                if isinstance(obj, type):
                    found = obj
            if found is not None:
                entry = found
                break
        if entry is None:
            skipped.append((cap_id, f"part has no class named by {symbol_name!r}"))
            continue
        adapter_path = (form.get("harvest_source") or {}).get(
            RUNTIME_ADAPTER_FIELD) or ""
        adapter = load_symbol(adapter_path) if adapter_path else None
        try:
            view = adapter(entry) if adapter else entry
        except Exception as exc:
            skipped.append((cap_id, f"could not be made servable: {exc}"))
            continue
        app.view_functions[r["endpoint"]] = view
        bound.append(cap_id)
    return bound, skipped


def resolve(app, form):
    """
    Match every shelf capability to a live route in the source application.
    Returns (resolved, unresolved).

    resolved is a list of dicts: cap_id, cap_name, route (the live rule),
    methods, endpoint.
    """
    live = {}
    for rule in app.url_map.iter_rules():
        live.setdefault(normalise(rule.rule), []).append(rule)

    on_shelf = set(read_shelf_caps(APP_SLUG))
    resolved, unresolved = [], []

    for cap in (form.get("capabilities") or []):
        cap_id = cap.get("cap_id")
        if cap_id not in on_shelf:
            continue
        want = normalise(cap.get("route"))
        method = (cap.get("method") or "GET").upper()
        rules = live.get(want, [])
        match = None
        for r in rules:
            if method in r.methods:
                match = r
                break
        if match is None and rules:
            match = rules[0]
        if match is None:
            unresolved.append({
                "cap_id": cap_id,
                "cap_name": cap.get("cap_name"),
                "route": cap.get("route"),
                "why": "no live route at that path in the source application",
            })
            continue
        resolved.append({
            "cap_id": cap_id,
            "cap_name": cap.get("cap_name"),
            "route": match.rule,
            "methods": sorted(match.methods - {"HEAD", "OPTIONS"}),
            "endpoint": match.endpoint,
        })
    return resolved, unresolved


def restrict(app, resolved):
    """
    Serve only what the shelf admits.

    Every route not belonging to a shelf capability is removed from the app's
    URL map, so the source application's other several-hundred endpoints stop
    existing. Static routes are kept when SERVE_STATIC is on, because a page
    without its stylesheet is not the capability working.
    """
    if not RESTRICT_TO_SHELF:
        return 0, 0

    keep_rules = {r["route"] for r in resolved}
    cap_for_rule = {r["route"]: r["cap_id"] for r in resolved}
    total = 0
    kept = 0
    for rule in app.url_map.iter_rules():
        total += 1
        if rule.rule in keep_rules:
            kept += 1

    def _is_static(endpoint, path):
        # Match on the ENDPOINT first, not the path. A source application may
        # serve all of its assets through one converter rule -- a rule whose
        # path is built from a converter, not a literal prefix -- and
        # that rule's path does not begin with any of the literal prefixes
        # below, so a path-only test refuses every stylesheet and script on the
        # page while the page itself still renders. Found by the level-1
        # browser check, which is the only thing that would have caught it.
        blueprint = endpoint.split(".")[0] if "." in endpoint else endpoint
        return SERVE_STATIC and (blueprint in STATIC_ENDPOINT_NAMES
                                 or endpoint.endswith("static")
                                 or "/static/" in path
                                 or path.startswith("/assets/")
                                 or path.startswith("/dist/"))

    # Refuse at dispatch rather than rebuilding the URL map. The source
    # application registers its routes with its own rule class and its own
    # map; replacing that map throws away routing behaviour the parts rely
    # on. Refusing here leaves the source stack exactly as it built itself
    # and still means the shelf decides what exists.
    from flask import request
    from werkzeug.exceptions import NotFound

    @app.before_request
    def _shelf_only():
        rule = request.url_rule
        if rule is None:
            return None
        if rule.rule in keep_rules:
            return None
        if _is_static(rule.endpoint or "", rule.rule):
            return None
        raise NotFound()

    @app.after_request
    def _stamp(response):
        if STAMP_HEADER:
            rule = request.url_rule
            if rule is not None and rule.rule in cap_for_rule:
                response.headers[STAMP_HEADER] = cap_for_rule[rule.rule]
        return response

    return kept, total - kept


def main():
    args = sys.argv[1:]
    check_only = "--check" in args
    if "--app" in args:
        globals()["APP_SLUG"] = args[args.index("--app") + 1]

    if QUIET_SOURCE_LOGGING:
        import warnings, logging
        warnings.filterwarnings("ignore")
        logging.disable(logging.ERROR)

    form, form_path = read_form(APP_SLUG)
    if form is None:
        print(f"REFUSED: no filled form for app slug {APP_SLUG!r} in {FORMS_DIR}/")
        sys.exit(1)

    on_shelf = read_shelf_caps(APP_SLUG)
    if not on_shelf:
        print(f"REFUSED: nothing on the shelf for {APP_SLUG!r} -- run harvest_parts.py")
        sys.exit(1)

    print(f"app: {APP_SLUG}   shelf: {len(on_shelf)} capabilities")
    print(f"runtime: {(form.get('harvest_source') or {}).get(RUNTIME_FACTORY_FIELD)}")

    app = build_source_app(form)
    total_source_routes = len(list(app.url_map.iter_rules()))

    resolved, unresolved = resolve(app, form)

    if BIND_SHELF_PARTS:
        bound, skipped = bind_shelf_parts(app, resolved, APP_SLUG, form)
        print(f"shelf parts bound: {len(bound)}")
        for cap_id, why in skipped:
            print(f"  NOT BOUND  {cap_id}: {why}")
        if skipped and FAIL_ON_UNRESOLVED:
            print("REFUSED: a capability on the shelf could not be bound to "
                  "its own part -- the app would be served by code the shelf "
                  "does not govern")
            sys.exit(1)

    print(f"\nsource application serves {total_source_routes} routes; "
          f"the shelf admits {len(resolved)}\n")
    print(f"  {'number':<10} {'capability':<26} {'methods':<12} route")
    for r in resolved:
        print(f"  {r['cap_id']:<10} {r['cap_name']:<26} "
              f"{','.join(r['methods']):<12} {r['route']}")

    if unresolved:
        print("\n  UNRESOLVED -- on the shelf, no live route:")
        for u in unresolved:
            print(f"  {u['cap_id']:<10} {u['cap_name']:<26} {u['route']}  -- {u['why']}")

    kept, dropped = restrict(app, resolved)
    if RESTRICT_TO_SHELF:
        print(f"\nrestricted to the shelf: {kept} routes kept, {dropped} refused")

    if unresolved and FAIL_ON_UNRESOLVED:
        print("\nNot serving. A capability on the shelf has no live route.")
        sys.exit(1)

    if check_only:
        print("\n--check: not starting a server.")
        return

    print(f"\nhost listening on http://{HOST_BIND}:{HOST_PORT}")
    app.run(host=HOST_BIND, port=HOST_PORT, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
