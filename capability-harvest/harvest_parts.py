#!/usr/bin/env python3
"""
harvest_parts.py — extracts one capability's real implementation onto the shelf.

Usage:
    python3 harvest_parts.py harvest_requests/CAP-0001.request.json

----------------------------------------------------------------------------
DETERMINISTIC PATH (documented per the handoff's explicit requirement —
section 7 asked for this to be written down, not left implicit):

  1. INPUT
       A harvest-request JSON path on argv[1], naming exactly
       {cap_id, app_slug}. Nothing else is read from argv, and nothing
       about "the current app" is assumed from context or cwd.

  2. PARSER / ENTRY
       main() loads that JSON, then loads two other files that are the
       real sources of truth for everything else it needs:
         - discovery/applications.json  (where the app was actually
           cloned, at which commit, under which licence)
         - output/attach_points.json    (where the capability was
           actually found: file, symbol, line range, decorators)
       harvest_parts.py never re-derives these; it only reads them.

  3. SELECTED SOURCE FILE
       SOURCE_ROOT/<app_slug>/<source_file_relative> from the attach-point
       record, resolved to an absolute path.

  4. SELECTED SYMBOL / LINE
       The attach-point record's function name + lineno/end_lineno.
       This is NOT trusted blindly: the file is re-parsed with `ast`
       right here, right now, and harvesting ABORTS LOUDLY if the named
       function has moved, been renamed, or changed shape since
       detection ran. Harvesting whatever now happens to sit at a stale
       line number would be worse than refusing outright.

  5. WRITER
       ast.get_source_segment() extracts the exact verbatim text of the
       re-confirmed function node — not a crude line-range string slice,
       which could accidentally include a neighbouring decorator or
       trailing blank lines.

  6. OUTPUT-PATH CONSTRUCTION
       Deterministic, computed once, from cap_id + app_slug alone:
         SHELF_ROOT/<app_slug>/<cap_id>/implementation.py
         SHELF_ROOT/<app_slug>/<cap_id>/PROVENANCE.json
         SHELF_ROOT/<app_slug>/<cap_id>/LICENCE.txt
       Never renamed, never inferred from anything else.

  7. SERIALIZATION
       - implementation.py: a short provenance header comment followed by
         the verbatim harvested source.
       - PROVENANCE.json: json.dump(..., indent=2, sort_keys=True) for
         reproducible, byte-for-byte output on re-runs against the same
         input.
       - LICENCE.txt: a verbatim copy of the real LICENSE file content
         found at discovery time (never re-typed, never summarised).
----------------------------------------------------------------------------
"""

import ast
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _free_names(func_node) -> set:
    """
    Names this function reads but does not itself define -- its real,
    external dependencies. Excludes parameters, names it assigns/loops
    over/imports locally, and builtins, so PROVENANCE.json's "dependencies"
    field reports genuine collaborators (load_data, current_user, ...)
    rather than the function's own local variables.
    """
    assigned = set()
    for sub in ast.walk(func_node):
        if isinstance(sub, ast.arg):
            assigned.add(sub.arg)
        elif isinstance(sub, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        assigned.add(n.id)
        elif isinstance(sub, ast.comprehension):
            for n in ast.walk(sub.target):
                if isinstance(n, ast.Name):
                    assigned.add(n.id)
        elif isinstance(sub, (ast.Import, ast.ImportFrom)):
            for alias in sub.names:
                assigned.add((alias.asname or alias.name).split(".")[0])

    import builtins as _builtins
    builtins_names = set(dir(_builtins))
    read_names = {n.id for n in ast.walk(func_node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return (read_names - assigned - builtins_names) - {func_node.name}


def _find_function_now(tree: ast.AST, symbol: str, expected_lineno: int):
    """Re-confirm the attach point against the file as it exists right now."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            if node.lineno == expected_lineno:
                return node
    return None


def harvest(request: dict) -> Path:
    cap_id = request["cap_id"]
    app_slug = request["app_slug"]

    applications = {a["slug"]: a for a in config.load_json(config.REPOSITORY_SOURCE)["applications"]}
    attach_points = {a["cap_id"]: a for a in config.load_json(config.OUTPUT_ROOT / "attach_points.json")["attach_points"]}

    app = applications.get(app_slug)
    if app is None:
        raise SystemExit(f"ABORT: application '{app_slug}' not in {config.REPOSITORY_SOURCE}")
    if app["blocked"]:
        raise SystemExit(f"ABORT: application '{app_slug}' is licence-blocked, refusing to harvest from it")

    attach = attach_points.get(cap_id)
    if attach is None or not attach.get("found"):
        raise SystemExit(f"ABORT: no confirmed attach point for '{cap_id}' in {config.OUTPUT_ROOT}/attach_points.json")

    # 3. SELECTED SOURCE FILE
    source_path = Path(app["cloned_path"]) / attach["source_file_relative"]
    if not source_path.exists():
        raise SystemExit(f"ABORT: source file vanished since detection: {source_path}")

    source_text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(source_path))

    # 4. SELECTED SYMBOL/LINE -- re-verified, not trusted blindly
    node = _find_function_now(tree, attach["symbol"], attach["lineno"])
    if node is None:
        raise SystemExit(
            f"ABORT: attach point for {cap_id} has drifted -- "
            f"expected `{attach['symbol']}` at line {attach['lineno']} in {source_path}, "
            f"but it is no longer there. Re-run detect_capability.py before harvesting."
        )

    # 5. WRITER
    harvested_source = ast.get_source_segment(source_text, node)
    if harvested_source is None:
        raise SystemExit(f"ABORT: could not extract source segment for {attach['symbol']}")

    # 6. OUTPUT-PATH CONSTRUCTION
    shelf_dir = config.SHELF_ROOT / app_slug / cap_id
    shelf_dir.mkdir(parents=True, exist_ok=True)
    impl_path = shelf_dir / "implementation.py"
    provenance_path = shelf_dir / "PROVENANCE.json"
    licence_path = shelf_dir / "LICENCE.txt"

    collaborator_names = sorted(_free_names(node))

    header = (
        f"# Harvested by harvest_parts.py\n"
        f"# capability : {cap_id} ({attach['name']})\n"
        f"# from       : {app_slug} @ {app['resolved_commit']}\n"
        f"# source     : {attach['source_file_relative']}:{attach['lineno']}-{attach['end_lineno']}\n"
        f"# licence    : {app['licence']['licence_id']} ({app['licence']['licence_file']})\n"
        f"# NOTE: this file is evidence, not a standalone module -- it depends on "
        f"names from the source application's own modules (see PROVENANCE.json "
        f"'dependencies'). It is not imported directly; build.py binds it into a "
        f"verified, running instance of the source application.\n\n"
    )
    impl_path.write_text(header + harvested_source + "\n", encoding="utf-8")

    # 7. SERIALIZATION
    licence_file = app["licence"]["licence_file"]
    real_licence_text = (Path(app["cloned_path"]) / licence_file).read_text(encoding="utf-8") if licence_file else ""
    licence_path.write_text(real_licence_text, encoding="utf-8")

    provenance = {
        "cap_id": cap_id,
        "capability_name": attach["name"],
        "category": attach["category"],
        "application": {
            "slug": app_slug,
            "repo_url": app["clone_url"],
            "commit": app["resolved_commit"],
            "category": app["category"],
        },
        "licence": {
            "id": app["licence"]["licence_id"],
            "file": licence_file,
            "marker_matched": app["licence"]["marker_matched"],
            "flagged_for_sign_off": app["licence"]["flagged"],
        },
        "source": {
            "file": attach["source_file_relative"],
            "symbol": attach["symbol"],
            "lineno": attach["lineno"],
            "end_lineno": attach["end_lineno"],
            "decorators": attach["decorators"],
            "route_path": attach.get("route_path"),
            "evidence_calls_matched": attach.get("evidence_calls_matched"),
        },
        "dependencies": {
            "collaborators_referenced": collaborator_names,
            "note": (
                "These names are referenced by the harvested function but are not "
                "themselves harvested as separate shelf entries in this walking "
                "skeleton. build.py resolves them from a live checkout of the same "
                "application at the same commit, and verifies (by source comparison) "
                "that the mounted route is byte-identical to what was harvested here."
            ),
        },
        "checksums": {
            "harvested_source_sha256": _sha256_text(harvested_source),
            "whole_source_file_sha256_at_harvest": _sha256_file(source_path),
        },
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "harvest_tool": "harvest_parts.py",
    }
    config.write_json(provenance_path, provenance)

    return shelf_dir


def main():
    config.ensure_dirs()
    config.print_roots(__file__)

    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 harvest_parts.py <harvest_request.json>")

    request_path = Path(sys.argv[1])
    request = config.load_json(request_path)
    shelf_dir = harvest(request)
    print(f"Harvested {request['cap_id']} from {request['app_slug']} -> {shelf_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
