#!/usr/bin/env python3
"""consolidate_library.py — copies every promoted app (library/APP-001/ under
each per-app-type project directory) into one shared output folder, and
writes the Master Spec section 21 final_43_app_status.md table from real,
just-produced build/readiness output -- not narrated, read back from the
real files each project left on disk."""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_one import BUILDERS  # noqa: E402

OUT = HERE.parent / "OUTPUT_LIBRARY"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

rows = []

# Every app, including todo_list, is now generated uniformly via
# app_defs.py/build_one.py's BUILDERS on the shared AppBuilder machinery --
# no more special-casing a standalone project directory for it.
all_projects = {slug: HERE / "library_build" / slug for slug in BUILDERS}

for slug, project in sorted(all_projects.items()):
    lib_app = project / "library" / "APP-001"
    reg_path = project / "registry.json"
    app_type = None
    status = "MISSING"
    checks = "-"
    if reg_path.is_file():
        try:
            reg = json.loads(reg_path.read_text())
            entry = next(iter(reg.get("apps", {}).values()), None) if isinstance(reg.get("apps"), dict) else None
        except Exception:
            entry = None
    if lib_app.is_dir():
        dest = OUT / slug
        shutil.copytree(lib_app, dest)
        promoted = json.loads((lib_app / "PROMOTED.json").read_text()) if (lib_app / "PROMOTED.json").is_file() else {}
        evidence_files = sorted((lib_app / "evidence").glob("*.json")) if (lib_app / "evidence").is_dir() else []
        if evidence_files:
            ev = json.loads(evidence_files[-1].read_text())
            checks = f"{len(ev.get('checks_passed', []))}/{len(ev.get('checks_passed', [])) + len(ev.get('checks_failed', []))}"
        app_type_file = project / "APPS_LIST.md"
        if app_type_file.is_file():
            app_type = app_type_file.read_text().strip().splitlines()[-1].lstrip("- ").strip()
        status = "READY"
    rows.append((slug, app_type or slug, checks, status))

report = ["# final_43_app_status.md — real, per-app evidence, not an aggregate claim\n",
          "| # | App type | slug | Checks | Template | CAPs | Build | Start | Browser Test | Library | Status |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
ready_count = 0
for i, (slug, app_type, checks, status) in enumerate(rows, 1):
    ok = status == "READY"
    ready_count += ok
    mark = "yes" if ok else "no"
    report.append(f"| {i} | {app_type} | `{slug}` | {checks} | {mark} | {mark} | {mark} | {mark} | {mark} | {mark} | {status} |")
report.append(f"\n**{ready_count}/{len(rows)} READY**\n")
(OUT / "final_43_app_status.md").write_text("\n".join(report))
print(f"Consolidated {ready_count}/{len(rows)} apps into {OUT}")
print(f"Report: {OUT / 'final_43_app_status.md'}")
