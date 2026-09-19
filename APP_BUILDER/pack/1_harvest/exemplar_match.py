#!/usr/bin/env python3
"""
exemplar_match.py -- Section 26.2: measuring one gated candidate against its
category's exemplar feature list, from the real clone.

For every feature in EXEMPLAR_FEATURES.json's entry for a category, this
module searches the real clone for the feature's keywords in two places:

    CODE   model class names, model field names, URL route names and paths,
           view and function names, template file names, management command
           names
    DOCS   README headings, docs/ headings, CHANGELOG entries

and assigns one of three verdicts:

    MATCHED     a keyword hit in CODE                    -- counts 1.0
    DOCS_ONLY   a keyword hit in DOCS but not CODE        -- counts DOCS_ONLY_WEIGHT (0.5 default)
    NOT_FOUND   no hit anywhere                           -- counts 0

feature_match = (sum of counts) / (number of features)

This ranks candidates within a category (Section 26.3); it is never an
admission gate on its own (Section 26.2: "Keyword hits here are a measure
of similarity, not proof of a working feature.").

Nothing here searches for the exemplar's own name, code, or product --
exemplars are proprietary, never candidates, never cloned (Section 26).
This module only ever touches the harvested candidate's own clone and the
category's EXEMPLAR_FEATURES.json entry, which is data Sam maintains.
"""

import ast
import json
import re
from pathlib import Path

from attach_points import _iter_py_files, _iter_template_files, _read, _rel, _SKIP_DIR_NAMES


def load_exemplar_features(path):
    """Returns {category_id: entry_dict}. A missing file is a hard stop --
    the caller decides what to do (see hunt.py's NOT MEASURED handling),
    this function never invents an empty registry to paper over it.

    Section 26.1: "A feature with no source_url is deleted before the file
    is used. Feature lists are not written from memory." -- enforced here,
    once, so every caller gets the filtered list rather than re-implementing
    the check."""
    with open(path) as f:
        data = json.load(f)
    out = {}
    for c in data.get("categories", []):
        kept = [f for f in (c.get("features") or []) if (f.get("source_url") or "").strip()]
        dropped = len(c.get("features") or []) - len(kept)
        entry = dict(c)
        entry["features"] = kept
        if dropped:
            entry["features_dropped_no_source_url"] = dropped
        out[c["id"]] = entry
    return out


# ---------------------------------------------------------------------
# CODE identifiers: everything Section 26.2 names as a place a feature's
# keyword may legitimately appear in real code.
# ---------------------------------------------------------------------

_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)", re.MULTILINE)
_CLASS_RE = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
_PATH_CALL_RE = re.compile(
    r"""\b(?:path|re_path|url)\s*\(\s*r?["']([^"']*)["']\s*,.*?(?:name\s*=\s*["']([^"']+)["'])?""",
    re.DOTALL)


def _collect_code_identifiers(root: Path):
    """[(identifier_text, file, line), ...] -- every class name, function/
    view name, URL path string, URL route name, template filename, and
    management-command filename in the clone. Field names are pulled in via
    the class-body Assign targets of any class (not just models -- a
    feature keyword may legitimately land on a form field or serializer
    field name too, and Section 26.2 does not restrict "model field names"
    so narrowly that a ModelForm field should be excluded)."""
    ids = []

    for f in _iter_py_files(root):
        text = _read(f)
        if text is None:
            continue
        rel = _rel(f, root)

        for m in _CLASS_RE.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            ids.append((m.group(1), rel, lineno))

        for m in _DEF_RE.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            ids.append((m.group(1), rel, lineno))

        for m in _PATH_CALL_RE.finditer(text):
            path_str, route_name = m.groups()
            lineno = text.count("\n", 0, m.start()) + 1
            if path_str:
                ids.append((path_str, rel, lineno))
            if route_name:
                ids.append((route_name, rel, lineno))

        try:
            tree = ast.parse(text, filename=str(f))
        except SyntaxError:
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for stmt in node.body:
                        if isinstance(stmt, ast.Assign):
                            for t in stmt.targets:
                                if isinstance(t, ast.Name):
                                    ids.append((t.id, rel, stmt.lineno))

        if "management/commands" in rel or "management\\commands" in rel:
            ids.append((f.stem, rel, 1))

    for f in _iter_template_files(root):
        rel = _rel(f, root)
        ids.append((f.stem, rel, 1))
        ids.append((f.name, rel, 1))

    return ids


# ---------------------------------------------------------------------
# DOCS corpus: README headings, docs/ headings, CHANGELOG entries.
# ---------------------------------------------------------------------

_MD_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_RST_HEADING_UNDERLINE_RE = re.compile(r"^([^\n]+)\n([=\-~`^\"'*+#]{3,})\s*$", re.MULTILINE)


def _collect_docs_lines(root: Path):
    """[(line_text, file, line_no), ...] from README*, docs/**, CHANGELOG* --
    headings for README/docs, every non-empty line for CHANGELOG (a
    changelog's unit is the entry, not a heading)."""
    lines = []

    def add_headings(f: Path):
        text = _read(f)
        if text is None:
            return
        rel = _rel(f, root)
        for m in _MD_HEADING_RE.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            lines.append((m.group(1), rel, lineno))
        for m in _RST_HEADING_UNDERLINE_RE.finditer(text):
            lineno = text.count("\n", 0, m.start()) + 1
            lines.append((m.group(1), rel, lineno))

    for f in root.glob("README*"):
        if f.is_file():
            add_headings(f)
    docs_dir = root / "docs"
    if docs_dir.is_dir():
        for f in docs_dir.rglob("*"):
            if f.suffix in (".md", ".rst") and f.is_file() and \
               not any(part in _SKIP_DIR_NAMES for part in f.parts):
                add_headings(f)

    for pat in ("CHANGELOG*", "HISTORY*", "NEWS*"):
        for f in root.glob(pat):
            if not f.is_file():
                continue
            text = _read(f)
            if text is None:
                continue
            rel = _rel(f, root)
            for i, line in enumerate(text.splitlines(), start=1):
                if line.strip():
                    lines.append((line.strip(), rel, i))

    return lines


def _keyword_hits(text, keyword):
    return keyword.lower() in text.lower()


def measure_feature_match(clone_path, category_entry, docs_only_weight=0.5):
    """category_entry: one dict from EXEMPLAR_FEATURES.json's categories
    list (has "features": [{"name","keywords",...}, ...]). Returns the
    per-feature verdicts and the aggregate feature_match score."""
    root = Path(clone_path).resolve()
    features = category_entry.get("features") or []

    if not features:
        return {
            "exemplar": category_entry.get("exemplar"),
            "features_checked": 0, "features_matched": 0, "docs_only": 0, "not_found": 0,
            "feature_match": None,
            "per_feature": [],
            "note": category_entry.get("no_feature_page_reason")
                    or "empty feature list for this category",
        }

    code_ids = _collect_code_identifiers(root)
    docs_lines = _collect_docs_lines(root)

    per_feature = []
    matched = docs_only = not_found = 0
    total = 0.0

    for feat in features:
        name = feat.get("name", "")
        keywords = feat.get("keywords") or []
        verdict, evidence, hit_kw = "NOT_FOUND", "", ""

        for kw in keywords:
            hit = next(((ident, f, ln) for ident, f, ln in code_ids if _keyword_hits(ident, kw)), None)
            if hit:
                verdict = "MATCHED"
                evidence = f"{hit[1]}:{hit[2]} ({hit[0]!r})"
                hit_kw = kw
                break
        if verdict == "NOT_FOUND":
            for kw in keywords:
                hit = next(((ln_text, f, ln) for ln_text, f, ln in docs_lines if _keyword_hits(ln_text, kw)), None)
                if hit:
                    verdict = "DOCS_ONLY"
                    evidence = f"{hit[1]}:{hit[2]}"
                    hit_kw = kw
                    break

        if verdict == "MATCHED":
            matched += 1
            total += 1.0
        elif verdict == "DOCS_ONLY":
            docs_only += 1
            total += docs_only_weight
        else:
            not_found += 1

        per_feature.append({
            "name": name, "verdict": verdict, "keyword_matched": hit_kw, "evidence": evidence,
        })

    feature_match = total / len(features)

    return {
        "exemplar": category_entry.get("exemplar"),
        "features_checked": len(features), "features_matched": matched,
        "docs_only": docs_only, "not_found": not_found,
        "feature_match": round(feature_match, 4),
        "per_feature": per_feature,
    }


def render_feature_match_md(candidate_label, result):
    lines = [f"# FEATURE_MATCH — {candidate_label}", ""]
    if result.get("feature_match") is None:
        lines.append(f"exemplar: {result.get('exemplar')}")
        lines.append("feature_match: NOT MEASURED")
        lines.append(f"reason: {result.get('note')}")
        lines.append("")
        return "\n".join(lines)

    lines += [
        f"exemplar: {result['exemplar']}",
        f"features checked: {result['features_checked']}",
        f"features matched (CODE): {result['features_matched']}",
        f"docs-only: {result['docs_only']}",
        f"not found: {result['not_found']}",
        f"feature_match: {result['feature_match']:.2f}",
        "",
        "| Feature | Verdict | Keyword | Evidence |",
        "|---------|---------|---------|----------|",
    ]
    for pf in result["per_feature"]:
        ev = pf["evidence"].replace("|", "\\|") if pf["evidence"] else "-"
        lines.append(f"| {pf['name']} | {pf['verdict']} | {pf['keyword_matched'] or '-'} | {ev} |")
    lines.append("")
    return "\n".join(lines)


def not_measured_result(reason):
    """A candidate rejected at a gate never has its clone measured against
    the exemplar (Section 26.5: "A candidate rejected at the gates has
    feature_match = NOT MEASURED (rejected at gate <rule>)."). This is that
    record."""
    return {"exemplar": None, "features_checked": 0, "features_matched": 0,
            "docs_only": 0, "not_found": 0, "feature_match": None,
            "per_feature": [], "note": reason}
