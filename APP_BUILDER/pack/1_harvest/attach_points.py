#!/usr/bin/env python3
"""
attach_points.py -- mechanical attach-point measurement, from the real clone.

Section 33 of the Django/PostgreSQL + attach-point + exemplar-matched
category harvest handoff asked for this to be code, not judgement: three
questions (does the app announce something happened? is there a named place
in the UI a capability can render into? is there an entity a capability can
read or write?), each answered from the AST of the real .py files and the
real template files sitting in the clone -- never from documentation, never
from a keyword count, never invented.

This module does not replace hunt.py's CandidateSpec.attach_points; it fills
it. A CandidateSpec supplied by a researcher may still carry extra ADAPTER
entries (an attach point our own system would have to build, because the
candidate has none natively) -- those still have to be a human or agent
judgement call, recorded as ADAPTER, never claimed NATIVE. Everything NATIVE
that this module reports is reproducible: run it twice against the same
commit and it returns the same points, because it read them off the same
files.

Three verdicts a measured point can carry, per Section 33:
    USABLE                  counts toward MIN_HOOKS / MIN_EVENTS / MIN_SLOTS / MIN_DATA
    DEFINED_NOT_SENT        a custom Signal() with no .send()/.send_robust() site found
                             anywhere in the clone -- defined, never fired, doesn't count
    DEFINED_NOT_REACHABLE   a concrete Model with no reference to it anywhere outside its
                             own definition (no view, serializer, admin registration, or
                             URL) -- an orphan, doesn't count
    MODEL_SIGNAL_EXCLUDED   Django's own post_save/pre_save/post_delete/pre_delete for a
                             reachable model -- real and NATIVE, but Django fires these on
                             every model in every app, so counting them toward MIN_EVENTS
                             would make the EVENT gate meaningless; excluded unless
                             REQUIRE_MODEL_SIGNALS_COUNT is turned on by the caller

Every non-USABLE point stays in the record (evidence/attach_points.json) --
Section 36 explicitly requires the "doesn't count" reasoning to be visible,
not silently dropped.
"""

import ast
import re
from pathlib import Path

# ---------------------------------------------------------------------
# What counts as "the app" vs. vendored/generated code we should not
# attribute attach points to. Same exclusion list for every walk below.
# ---------------------------------------------------------------------
_SKIP_DIR_NAMES = {
    ".git", "node_modules", "venv", ".venv", "env", ".tox", "__pycache__",
    "migrations", "static", "staticfiles", "dist", "build", ".eggs",
    "site-packages", "vendor", "third_party",
}

_MAX_FILE_BYTES = 2_000_000  # skip anything absurd; a generated file, not app code


def _iter_py_files(root: Path):
    for p in root.rglob("*.py"):
        if any(part in _SKIP_DIR_NAMES for part in p.parts):
            continue
        try:
            if p.stat().st_size > _MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield p


def _iter_template_files(root: Path):
    for p in root.rglob("*.html"):
        if any(part in _SKIP_DIR_NAMES for part in p.parts):
            continue
        yield p


def _read(p: Path):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _parse(p: Path):
    text = _read(p)
    if text is None:
        return None, None
    try:
        return ast.parse(text, filename=str(p)), text
    except SyntaxError:
        # Python 2 file, or a fixture/generated file that doesn't parse as
        # Python 3. Skipped, not guessed at -- a point cannot be evidenced
        # from a file we could not actually parse.
        return None, text


def _rel(p: Path, root: Path):
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _app_label_for(p: Path, root: Path):
    """The Django app a file belongs to: the nearest ancestor directory
    (below the file) that itself contains apps.py or models.py, else the
    top-level directory under the repo root, else the repo root name."""
    cur = p.parent
    while cur != root and cur != cur.parent:
        if (cur / "apps.py").exists() or (cur / "models.py").exists():
            return cur.name
        cur = cur.parent
    rel = _rel(p, root)
    parts = rel.split("/")
    return parts[0] if parts and parts[0] not in (".", "") else root.name


def _unparse(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


# =====================================================================
# 33.1 EVENT
# =====================================================================

_MODEL_SIGNAL_NAMES = {"post_save", "pre_save", "post_delete", "pre_delete"}


def _find_custom_signals(root: Path):
    """Module-level `NAME = Signal(...)` or `NAME = django.dispatch.Signal(...)`.
    Returns {signal_var_name: {"file", "lineno", "providing_args"}}."""
    signals = {}
    for f in _iter_py_files(root):
        tree, _ = _parse(f)
        if tree is None:
            continue
        for node in tree.body:  # module level only -- Section 33.1 says so
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            func = node.value.func
            fname = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else "")
            if fname != "Signal":
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                providing = []
                for kw in node.value.keywords:
                    if kw.arg == "providing_args" and isinstance(kw.value, ast.List):
                        for elt in kw.value.elts:
                            if isinstance(elt, ast.Constant):
                                providing.append(elt.value)
                signals[target.id] = {
                    "file": _rel(f, root),
                    "lineno": node.lineno,
                    "providing_args": providing,
                }
    return signals


def _find_send_sites(root: Path, signal_names):
    """Every `<name>.send(...)` / `<name>.send_robust(...)` call site for a
    known signal variable name, anywhere in the clone -- a signal is often
    imported into a different module from where it is defined. Returns
    {signal_var_name: [{"file", "lineno", "kwargs": [...]}]}."""
    sites = {name: [] for name in signal_names}
    if not signal_names:
        return sites
    for f in _iter_py_files(root):
        tree, _ = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in ("send", "send_robust"):
                continue
            if not isinstance(func.value, ast.Name):
                continue
            name = func.value.id
            if name not in sites:
                continue
            kwargs = [kw.arg for kw in node.keywords if kw.arg and kw.arg != "sender"]
            sites[name].append({
                "file": _rel(f, root), "lineno": node.lineno, "kwargs": kwargs,
            })
    return sites


def _find_webhook_events(root: Path):
    """Outgoing HTTP POSTs whose URL argument's source text names a webhook
    or callback -- Section 33.1's "webhooks / outgoing events". A textual
    heuristic on the unparsed argument, not a guess at runtime behaviour: it
    only fires when the word is actually in the code that builds the URL."""
    found = []
    pat = re.compile(r"webhook|callback", re.IGNORECASE)
    for f in _iter_py_files(root):
        tree, _ = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            callee = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else "")
            if callee not in ("post", "urlopen"):
                continue
            args_src = " ".join(_unparse(a) for a in node.args)
            kwargs_src = " ".join(_unparse(kw.value) for kw in node.keywords)
            src = args_src + " " + kwargs_src
            if pat.search(src):
                found.append({"file": _rel(f, root), "lineno": node.lineno, "call": callee,
                              "evidence_text": src.strip()[:200]})
    return found


def measure_events(root: Path, require_model_signals_count: bool, reachable_models: dict):
    """Returns (usable_events, all_measured_events)."""
    signals = _find_custom_signals(root)
    sites = _find_send_sites(root, set(signals))
    usable, all_measured = [], []

    for name, defn in signals.items():
        send_sites = sites.get(name, [])
        app_label = _app_label_for(root / defn["file"], root)
        point_name = f"{app_label}.{name}"
        payload = ", ".join(sorted({k for s in send_sites for k in s["kwargs"]}
                                    | set(defn["providing_args"])))
        if send_sites:
            evidence = (f"{defn['file']}:{defn['lineno']} (defined), "
                        f"{send_sites[0]['file']}:{send_sites[0]['lineno']} (sent)")
            point = {
                "name": point_name, "kind": "EVENT", "source_file": defn["file"],
                "source_symbol": name, "payload": payload, "implementation": "NATIVE",
                "evidence": evidence, "status": "USABLE",
            }
            usable.append(point)
            all_measured.append(point)
        else:
            all_measured.append({
                "name": point_name, "kind": "EVENT", "source_file": defn["file"],
                "source_symbol": name, "payload": payload, "implementation": "NATIVE",
                "evidence": f"{defn['file']}:{defn['lineno']} (defined, no send site found)",
                "status": "DEFINED_NOT_SENT",
            })

    for wh in _find_webhook_events(root):
        point = {
            "name": f"webhook.{Path(wh['file']).stem}.L{wh['lineno']}",
            "kind": "EVENT", "source_file": wh["file"], "source_symbol": wh["call"],
            "payload": wh["evidence_text"], "implementation": "NATIVE",
            "evidence": f"{wh['file']}:{wh['lineno']}", "status": "USABLE",
            "externally_consumable": True,
        }
        usable.append(point)
        all_measured.append(point)

    if require_model_signals_count:
        for m in reachable_models.values():
            for sig in sorted(_MODEL_SIGNAL_NAMES):
                point = {
                    "name": f"{m['app_label']}.{m['name']}.{sig}", "kind": "EVENT",
                    "source_file": m["file"], "source_symbol": m["name"],
                    "payload": ", ".join(m["fields"]), "implementation": "NATIVE",
                    "evidence": f"{m['file']}:{m['lineno']}", "status": "USABLE",
                }
                usable.append(point)
                all_measured.append(point)
    else:
        for m in reachable_models.values():
            for sig in sorted(_MODEL_SIGNAL_NAMES):
                all_measured.append({
                    "name": f"{m['app_label']}.{m['name']}.{sig}", "kind": "EVENT",
                    "source_file": m["file"], "source_symbol": m["name"],
                    "payload": ", ".join(m["fields"]), "implementation": "NATIVE",
                    "evidence": f"{m['file']}:{m['lineno']} "
                                f"(Django built-in model signal, not counted -- "
                                f"REQUIRE_MODEL_SIGNALS_COUNT is False)",
                    "status": "MODEL_SIGNAL_EXCLUDED",
                })

    return usable, all_measured


# =====================================================================
# 33.3 DATA (computed before SLOT, since SLOT's view-template map and
# EVENT's model-signal step both want to know what's reachable)
# =====================================================================

def _is_model_base(base_node):
    if isinstance(base_node, ast.Attribute):
        return base_node.attr == "Model"
    if isinstance(base_node, ast.Name):
        return base_node.id == "Model"
    return False


def _class_is_abstract(class_node):
    for stmt in class_node.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
            for inner in stmt.body:
                if isinstance(inner, ast.Assign):
                    for t in inner.targets:
                        if isinstance(t, ast.Name) and t.id == "abstract":
                            if isinstance(inner.value, ast.Constant) and inner.value.value is True:
                                return True
    return False


def _field_names(class_node):
    names = []
    for stmt in class_node.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            func = stmt.value.func
            callee = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else "")
            if callee.endswith("Field") or callee == "ForeignKey" or callee == "OneToOneField" \
               or callee == "ManyToManyField":
                for t in stmt.targets:
                    if isinstance(t, ast.Name):
                        names.append(t.id)
    return names


def _find_models(root: Path):
    """Every concrete class inheriting models.Model, direct or via one level
    of an abstract base also found in this clone."""
    models = {}
    abstract_bases = set()
    class_defs = []  # (node, file, app_label)

    for f in _iter_py_files(root):
        tree, _ = _parse(f)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_defs.append((node, f))

    direct_model_names = set()
    for node, f in class_defs:
        if any(_is_model_base(b) for b in node.bases):
            direct_model_names.add(node.name)
            if _class_is_abstract(node):
                abstract_bases.add(node.name)

    for node, f in class_defs:
        bases_names = [b.id for b in node.bases if isinstance(b, ast.Name)]
        is_model = any(_is_model_base(b) for b in node.bases) or \
            any(bn in direct_model_names for bn in bases_names)
        if not is_model:
            continue
        if _class_is_abstract(node):
            continue
        app_label = _app_label_for(f, root)
        models[node.name] = {
            "name": node.name, "app_label": app_label, "file": _rel(f, root),
            "lineno": node.lineno, "fields": _field_names(node),
        }
    return models


def _find_reachable(root: Path, models: dict, file_cache: dict = None):
    """A model is reachable if its name is referenced anywhere outside its
    own definition file: a view, serializer, admin registration, URL, or
    form. Also determines WRITE via ModelForm/Serializer Meta.model or
    <Model>.objects.create( / .save() usage.

    Reads every .py file's text exactly once (file_cache), then checks all
    models against that in-memory cache -- the naive O(models x files) with
    a fresh disk read per pair is fine for a normal-sized app, but becomes
    minutes of wall time against something the size of the Django framework
    itself (thousands of files). One pass to build the cache, then pure
    in-memory regex work, whatever the model count."""
    if file_cache is None:
        file_cache = {f: _read(f) for f in _iter_py_files(root)}

    reachable = {}
    for name, m in models.items():
        own_file = root / m["file"]
        found_ref = None
        found_write = False
        interface = "ORM"
        word = re.compile(r"\b" + re.escape(name) + r"\b")
        create_pat = re.compile(re.escape(name) + r"\.objects\.create\s*\(")
        for f, text in file_cache.items():
            if f == own_file or text is None or name not in text:
                continue
            if not word.search(text):
                continue
            rel = _rel(f, root)
            fname_l = f.name.lower()
            if found_ref is None:
                found_ref = f"{rel} (referenced)"
            if "serializer" in fname_l or "SerializerMethodField" in text or \
               re.search(r"class\s+\w*" + re.escape(name) + r"\w*Serializer", text):
                interface = "DRF"
            if re.search(r"class\s+\w*" + re.escape(name) + r"\w*Form\b", text) or \
               create_pat.search(text):
                found_write = True
                if found_ref is None or "referenced" in found_ref:
                    found_ref = f"{rel} (write path)"
            if found_ref and found_write:
                break  # nothing more this model's reachability needs
        if found_ref:
            reachable[name] = dict(m)
            reachable[name]["evidence_extra"] = found_ref
            reachable[name]["operations"] = "READ, WRITE" if found_write else "READ"
            reachable[name]["interface"] = interface
    return reachable


def measure_data(root: Path, file_cache: dict = None):
    """Returns (usable_data, all_measured_data, reachable_models_dict)."""
    if file_cache is None:
        file_cache = {f: _read(f) for f in _iter_py_files(root)}
    models = _find_models(root)
    reachable = _find_reachable(root, models, file_cache)
    usable, all_measured = [], []
    for name, m in models.items():
        point_name = f"{m['app_label']}.{m['name']}"
        if name in reachable:
            r = reachable[name]
            point = {
                "name": point_name, "kind": "DATA", "source_file": m["file"],
                "source_symbol": m["name"], "operations": r["operations"],
                "payload": ", ".join(m["fields"]), "implementation": "NATIVE",
                "evidence": f"{m['file']}:{m['lineno']}, {r['evidence_extra']}",
                "status": "USABLE", "interface": r["interface"],
            }
            usable.append(point)
            all_measured.append(point)
        else:
            all_measured.append({
                "name": point_name, "kind": "DATA", "source_file": m["file"],
                "source_symbol": m["name"], "payload": ", ".join(m["fields"]),
                "implementation": "NATIVE",
                "evidence": f"{m['file']}:{m['lineno']} "
                            f"(model defined, no reference found outside its own file)",
                "status": "DEFINED_NOT_REACHABLE",
            })
    return usable, all_measured, reachable


# =====================================================================
# 33.2 SLOT
# =====================================================================

_BLOCK_RE = re.compile(r"{%-?\s*block\s+(\w+)\s*-?%}")
_EXTENDS_RE = re.compile(r"""{%-?\s*extends\s+["']([^"']+)["']\s*-?%}""")
_INCLUDE_VAR_RE = re.compile(r"{%-?\s*include\s+(\w+)\b")
_RENDER_TEMPLATE_RE = re.compile(
    r"""(?:render|TemplateResponse)\s*\(\s*request\s*,\s*["']([^"']+)["']""")
_TEMPLATE_NAME_ATTR_RE = re.compile(r"""template_name\s*=\s*["']([^"']+)["']""")
_HOOK_WORD_RE = re.compile(r"hook|slot|plugin|extension|extra|widget", re.IGNORECASE)
_MENU_VAR_RE = re.compile(r"^\s*(\w*(?:menu|nav|sidebar|toolbar)\w*)\s*=\s*[\[{]",
                           re.IGNORECASE | re.MULTILINE)
_ACTIONS_VAR_RE = re.compile(r"^\s*(\w*actions\w*)\s*=\s*\[", re.IGNORECASE | re.MULTILINE)


def _template_rendering_map(root: Path):
    """template relative-name-fragment -> [(view_file, view_symbol_or_line)]."""
    m = {}
    for f in _iter_py_files(root):
        text = _read(f)
        if text is None:
            continue
        for match in _RENDER_TEMPLATE_RE.finditer(text):
            m.setdefault(match.group(1), []).append(_rel(f, root))
        for match in _TEMPLATE_NAME_ATTR_RE.finditer(text):
            m.setdefault(match.group(1), []).append(_rel(f, root))
    return m


def _find_template_blocks(root: Path, render_map: dict):
    """Every {% block %}, tagged as a SLOT when its template is either
    extended by another real template, or rendered by a traced view."""
    extended_targets = set()
    template_files = list(_iter_template_files(root))
    for f in template_files:
        text = _read(f)
        if text is None:
            continue
        for match in _EXTENDS_RE.finditer(text):
            extended_targets.add(Path(match.group(1)).name)

    usable, all_measured = [], []
    for f in template_files:
        text = _read(f)
        if text is None:
            continue
        rel = _rel(f, root)
        stem = f.stem
        is_extended = f.name in extended_targets
        rendered_by = None
        for tmpl_key, views in render_map.items():
            if tmpl_key.endswith(f.name) or Path(tmpl_key).name == f.name:
                rendered_by = views[0]
                break
        for match in _BLOCK_RE.finditer(text):
            block_name = match.group(1)
            lineno = text.count("\n", 0, match.start()) + 1
            point_name = f"{root.name}.{stem}.{block_name}"
            if is_extended or rendered_by:
                point = {
                    "name": point_name, "kind": "SLOT", "source_file": rel,
                    "rendering_context": rendered_by or "(extended by a child template)",
                    "implementation": "NATIVE",
                    "evidence": f"{rel}:{lineno}"
                                + (f", {rendered_by}" if rendered_by else ""),
                    "status": "USABLE",
                }
                usable.append(point)
                all_measured.append(point)
            else:
                all_measured.append({
                    "name": point_name, "kind": "SLOT", "source_file": rel,
                    "implementation": "NATIVE",
                    "evidence": f"{rel}:{lineno} "
                                f"(block found, template not traced to any view or "
                                f"extends chain)",
                    "status": "DEFINED_NOT_REACHABLE",
                })
    return usable, all_measured


def _find_template_hooks(root: Path):
    """Dynamic {% include var %}, and inclusion/simple tags whose registered
    name or function name contains a hook-shaped word."""
    usable = []
    for f in _iter_template_files(root):
        text = _read(f)
        if text is None:
            continue
        rel = _rel(f, root)
        for match in _INCLUDE_VAR_RE.finditer(text):
            var = match.group(1)
            if var in ("request",):  # not a template-name variable
                continue
            lineno = text.count("\n", 0, match.start()) + 1
            usable.append({
                "name": f"{root.name}.{f.stem}.include_{var}", "kind": "SLOT",
                "source_file": rel, "rendering_context": f"dynamic include: {{{{ {var} }}}}",
                "implementation": "NATIVE", "evidence": f"{rel}:{lineno}",
                "status": "USABLE",
            })

    tag_pat = re.compile(
        r"@register\.(inclusion_tag|simple_tag)\s*\(\s*(?:[\"']([^\"']+)[\"'])?[^)]*\)\s*\n\s*def\s+(\w+)")
    for f in _iter_py_files(root):
        text = _read(f)
        if text is None or "@register." not in text:
            continue
        for match in tag_pat.finditer(text):
            tag_kind, registered, funcname = match.groups()
            label = registered or funcname
            if _HOOK_WORD_RE.search(label):
                lineno = text.count("\n", 0, match.start()) + 1
                rel = _rel(f, root)
                usable.append({
                    "name": f"{_app_label_for(f, root)}.{funcname}", "kind": "SLOT",
                    "source_file": rel, "source_symbol": funcname,
                    "rendering_context": f"@register.{tag_kind}",
                    "implementation": "NATIVE", "evidence": f"{rel}:{lineno}",
                    "status": "USABLE",
                })
    return usable


def _find_menu_registries(root: Path, file_cache: dict = None):
    """Python-side list/dict registries named *menu*/*nav*/*sidebar*/*toolbar*
    or *actions*, referenced (iterated) somewhere other than their own
    definition -- the same reachability discipline as DATA. Uses the same
    one-read-per-file cache as _find_reachable, for the same reason."""
    if file_cache is None:
        file_cache = {f: _read(f) for f in _iter_py_files(root)}

    usable = []
    candidates = []
    for f, text in file_cache.items():
        if text is None:
            continue
        for pat in (_MENU_VAR_RE, _ACTIONS_VAR_RE):
            for match in pat.finditer(text):
                candidates.append((match.group(1), f, text))

    for varname, defn_file, defn_text in candidates:
        word = re.compile(r"\b" + re.escape(varname) + r"\b")
        referenced_elsewhere = False
        ref_file = None
        for f, text in file_cache.items():
            if f == defn_file or text is None:
                continue
            if word.search(text):
                referenced_elsewhere = True
                ref_file = _rel(f, root)
                break
        if referenced_elsewhere:
            lineno = defn_text.count("\n", 0, defn_text.find(varname)) + 1
            usable.append({
                "name": f"{_app_label_for(defn_file, root)}.{varname}", "kind": "SLOT",
                "source_file": _rel(defn_file, root), "source_symbol": varname,
                "rendering_context": f"registry iterated in {ref_file}",
                "implementation": "NATIVE",
                "evidence": f"{_rel(defn_file, root)}:{lineno}, {ref_file}",
                "status": "USABLE",
            })
    return usable


def measure_slots(root: Path, file_cache: dict = None):
    render_map = _template_rendering_map(root)
    block_usable, block_all = _find_template_blocks(root, render_map)
    hook_usable = _find_template_hooks(root)
    menu_usable = _find_menu_registries(root, file_cache)
    usable = block_usable + hook_usable + menu_usable
    all_measured = block_all + hook_usable + menu_usable
    return usable, all_measured


# =====================================================================
# 33.4 EXTENSION SYSTEM -- evidence, not a gate on its own
# =====================================================================

def measure_extension_system(root: Path):
    evidence = []

    for fname in ("pyproject.toml", "setup.py", "setup.cfg"):
        f = root / fname
        if f.exists():
            text = _read(f) or ""
            if "entry_points" in text:
                lineno = text.count("\n", 0, text.find("entry_points")) + 1
                evidence.append(f"entry_points declared in {fname}:{lineno}")

    ready_pat = re.compile(r"class\s+\w+\(AppConfig\)[^\n]*\n(?:.*\n)*?\s*def\s+ready\s*\(self\)")
    for f in _iter_py_files(root):
        if f.name != "apps.py":
            continue
        text = _read(f)
        if text and "def ready" in text and re.search(r"AppConfig", text):
            body_match = re.search(r"def\s+ready\s*\(self\).*?(?=\n\s*def\s|\Z)", text, re.DOTALL)
            body = body_match.group(0) if body_match else ""
            if re.search(r"import_module|autodiscover|importlib", body):
                lineno = text.count("\n", 0, text.find("def ready")) + 1
                evidence.append(f"AppConfig.ready() autodiscovers modules: {_rel(f, root)}:{lineno}")

    for f in _iter_py_files(root):
        text = _read(f)
        if not text:
            continue
        if re.search(r"^\s*import\s+pluggy|^\s*from\s+pluggy", text, re.MULTILINE):
            evidence.append(f"pluggy usage: {_rel(f, root)}")
        if re.search(r"^\s*import\s+stevedore|^\s*from\s+stevedore", text, re.MULTILINE):
            evidence.append(f"stevedore usage: {_rel(f, root)}")

    for f in _iter_py_files(root):
        if f.name != "settings.py" and "settings" not in f.name:
            continue
        text = _read(f)
        if not text:
            continue
        for m in re.finditer(r"^\s*(PLUGINS|EXTENSIONS|HOOKS)\s*=", text, re.MULTILINE):
            evidence.append(f"{m.group(1)} setting: {_rel(f, root)}:"
                             f"{text.count(chr(10), 0, m.start()) + 1}")

    for f in _iter_py_files(root):
        text = _read(f)
        if text and "admin.autodiscover" in text:
            evidence.append(f"admin.autodiscover pattern: {_rel(f, root)}")
            break

    docs_hits = []
    for pat_name in ("README*", "docs/**/*.md", "docs/**/*.rst"):
        for f in root.glob(pat_name):
            text = _read(f)
            if text and re.search(r"writing a plugin|plugin development|creating an extension|"
                                   r"plugin authoring|how to write a plugin", text, re.IGNORECASE):
                docs_hits.append(_rel(f, root))
    plugin_docs_present = bool(docs_hits)

    return {
        "evidence": evidence,
        "plugin_authoring_docs_present": plugin_docs_present,
        "plugin_authoring_docs_location": docs_hits[0] if docs_hits else "",
    }


# =====================================================================
# Public entry point
# =====================================================================

def measure_attach_points(clone_path, require_model_signals_count: bool = False):
    """The whole of Section 33, run against one real clone. Returns a dict
    with usable_events/usable_slots/usable_data (feed these into
    CandidateSpec.attach_points), all_measured (the full inventory, DEFINED_
    NOT_SENT / DEFINED_NOT_REACHABLE / MODEL_SIGNAL_EXCLUDED included, for
    evidence/attach_points.json), and extension_system (evidence dict)."""
    root = Path(clone_path).resolve()
    file_cache = {f: _read(f) for f in _iter_py_files(root)}

    usable_data, all_data, reachable_models = measure_data(root, file_cache)
    usable_events, all_events = measure_events(root, require_model_signals_count, reachable_models)
    usable_slots, all_slots = measure_slots(root, file_cache)
    ext = measure_extension_system(root)

    usable = usable_events + usable_slots + usable_data
    all_measured = all_events + all_slots + all_data

    return {
        "usable_events": usable_events, "usable_slots": usable_slots, "usable_data": usable_data,
        "usable_total": usable,
        "all_measured": all_measured,
        "counts": {
            "usable_events": len(usable_events), "usable_slots": len(usable_slots),
            "usable_data": len(usable_data), "usable_total": len(usable),
        },
        "extension_system": ext,
    }


if __name__ == "__main__":
    import sys
    import json as _json
    if len(sys.argv) != 2:
        print("usage: attach_points.py <clone_path>")
        sys.exit(1)
    result = measure_attach_points(sys.argv[1])
    print(_json.dumps(result, indent=2))
