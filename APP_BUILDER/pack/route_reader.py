#!/usr/bin/env python3
"""
route_reader.py  --  reads a shelf part's route and method from real Flask code.

build.py's _extract_route_meta reads only top-level ROUTE / METHOD string
constants. Real Flask code does not declare routes that way. This reader
understands the three forms that actually occur, statically, via the AST --
the file is never imported or executed, exactly as before.

  1. ROUTE / METHOD constants          (generated parts, kept working)
  2. @bp.route('/path', methods=[...]) (the common Flask decorator)
  3. bp.add_url_rule('/path', 'name', Handler, methods=(...))
                                       (the call form -- what Indico uses)

Blueprint url_prefix is resolved, because the real path a request hits is the
prefix plus the rule.

Where a handler binds to more than one rule, this returns (None, None) and the
candidates are available separately. It never guesses -- that is the same
contract build.py's original reader had.

Run it against a file to see what it finds:
    python3 route_reader.py <file.py> [symbol]
"""

# ===========================================================================
# RULES / CONFIG  --  edit these, not the logic below.
# ===========================================================================

# Flask's own default when a rule names no methods. Changing this changes what
# method is reported for every route that does not state one.
DEFAULT_METHODS = ("GET",)

# Method names the host can actually dispatch. A route declaring anything else
# is reported as-is, but ONLY_DISPATCHABLE_METHODS below decides whether it is
# allowed to be the single chosen method.
DISPATCHABLE_METHODS = ("GET", "POST")

# If true, a rule declaring several methods collapses to the first one the host
# can dispatch (e.g. ('GET','POST') -> 'POST' when POST is listed first below).
# If false, a multi-method rule is ambiguous and returns nothing.
COLLAPSE_MULTI_METHOD = True

# The order a multi-method rule collapses in. The first match wins. POST is
# first because a rule that accepts both is nearly always a form: GET renders
# it, POST is the capability doing its work.
METHOD_PREFERENCE = ("POST", "GET")

# Attribute names treated as route-registering calls.
ROUTE_DECORATOR_NAMES = ("route",)
ADD_RULE_NAMES = ("add_url_rule",)

# Callables treated as constructing a blueprint whose url_prefix applies.
# Indico subclasses Blueprint as IndicoBlueprint, so both are listed.
BLUEPRINT_FACTORY_NAMES = ("Blueprint", "IndicoBlueprint")

# If true, a url_prefix found on a blueprint is prepended to its rules.
APPLY_URL_PREFIX = True

# A rule path starting with this marker is absolute: the blueprint's url_prefix
# does NOT apply to it. Indico uses "!" for exactly this, and its whole check-in
# API is declared that way. Set to "" to treat every path as prefixed, which
# would report those routes at a path no request ever hits.
ABSOLUTE_PATH_MARKER = "!"

# ===========================================================================
# END CONFIG
# ===========================================================================

import ast
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class Rule:
    """One route binding found in the source."""

    def __init__(self, path, methods, handler, lineno):
        self.path = path
        self.methods = tuple(methods)
        self.handler = handler
        self.lineno = lineno

    def __repr__(self):
        return f"{self.path}  {'/'.join(self.methods)}  -> {self.handler or '?'}  (line {self.lineno})"


def _str(node) -> Optional[str]:
    """A plain string literal, or None. Never evaluates anything."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _methods_from_keywords(keywords) -> Tuple[str, ...]:
    for kw in keywords:
        if kw.arg != "methods":
            continue
        if isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
            out = [_str(e) for e in kw.value.elts]
            got = tuple(m.upper() for m in out if m)
            if got:
                return got
    return DEFAULT_METHODS


def _handler_name(node) -> Optional[str]:
    """The dotted name of a handler passed positionally, e.g. regforms.RHFoo."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _handler_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _prefixes(tree) -> dict:
    """Maps a blueprint variable name to its url_prefix, where one is given."""
    out = {}
    if not APPLY_URL_PREFIX:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        if not isinstance(node.targets[0], ast.Name):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        fname = call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", None)
        if fname not in BLUEPRINT_FACTORY_NAMES:
            continue
        for kw in call.keywords:
            if kw.arg == "url_prefix":
                p = _str(kw.value)
                if p:
                    out[node.targets[0].id] = p.rstrip("/")
    return out


def _owner(func_node) -> Optional[str]:
    """The variable a .route/.add_url_rule call hangs off, e.g. _bp."""
    if isinstance(func_node, ast.Attribute) and isinstance(func_node.value, ast.Name):
        return func_node.value.id
    return None


def find_rules(source: str) -> List[Rule]:
    """Every route binding in the file, in source order."""
    tree = ast.parse(source)
    prefixes = _prefixes(tree)
    rules: List[Rule] = []

    def full(path, owner):
        if ABSOLUTE_PATH_MARKER and path.startswith(ABSOLUTE_PATH_MARKER):
            return path[len(ABSOLUTE_PATH_MARKER):]
        pre = prefixes.get(owner, "")
        return f"{pre}{path}" if pre else path

    # decorator form: @bp.route('/x', methods=[...])
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if dec.func.attr not in ROUTE_DECORATOR_NAMES or not dec.args:
                continue
            path = _str(dec.args[0])
            if path is None:
                continue
            rules.append(Rule(full(path, _owner(dec.func)),
                              _methods_from_keywords(dec.keywords),
                              node.name, dec.lineno))

    # call form: bp.add_url_rule('/x', 'name', Handler, methods=(...))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in ADD_RULE_NAMES or not node.args:
            continue
        path = _str(node.args[0])
        if path is None:
            continue
        handler = _handler_name(node.args[2]) if len(node.args) > 2 else None
        rules.append(Rule(full(path, _owner(node.func)),
                          _methods_from_keywords(node.keywords),
                          handler, node.lineno))

    return rules


def _collapse(methods) -> Optional[str]:
    usable = [m for m in methods if m in DISPATCHABLE_METHODS]
    if not usable:
        return None
    if len(usable) == 1:
        return usable[0]
    if not COLLAPSE_MULTI_METHOD:
        return None
    for pref in METHOD_PREFERENCE:
        if pref in usable:
            return pref
    return None


def extract_route_meta(module_file: Path,
                       symbol: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """The drop-in replacement for build.py's _extract_route_meta.

    Returns (route, method), or (None, None) if the file declares none, or if
    it declares several that disagree. Never guesses. If `symbol` is given,
    only rules bound to that handler are considered -- which is what makes a
    file with many routes readable for one capability."""
    try:
        source = module_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return None, None

    # 1. explicit constants win, exactly as before
    route = method = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("ROUTE", "METHOD"):
                val = _str(node.value)
                if val is not None:
                    if name == "ROUTE":
                        route = val
                    else:
                        method = val.upper()
    if route and method:
        return route, method

    # 2. real Flask declarations
    rules = find_rules(source)
    if symbol:
        rules = [r for r in rules if r.handler == symbol or (r.handler or "").endswith("." + symbol)]
    if not rules:
        return None, None

    resolved = {(r.path, _collapse(r.methods)) for r in rules}
    resolved = {(p, m) for p, m in resolved if m}
    if len(resolved) != 1:
        return None, None
    return resolved.pop()


def candidates(module_file: Path, symbol: Optional[str] = None) -> List[Rule]:
    """Every rule found, for when extract_route_meta declines to choose."""
    try:
        source = module_file.read_text(encoding="utf-8")
    except Exception:
        return []
    rules = find_rules(source)
    if symbol:
        rules = [r for r in rules if r.handler == symbol or (r.handler or "").endswith("." + symbol)]
    return rules


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: route_reader.py <file.py> [symbol]")
        sys.exit(1)
    f = Path(sys.argv[1])
    sym = sys.argv[2] if len(sys.argv) > 2 else None
    print(f"file:   {f}")
    print(f"symbol: {sym or '(any)'}")
    print(f"result: {extract_route_meta(f, sym)}")
    print("candidates:")
    for r in candidates(f, sym):
        print(f"   {r}")
