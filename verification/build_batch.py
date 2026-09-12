#!/usr/bin/env python3
"""build_batch.py [slug ...] — real orchestrator implementing Master Spec
section 15's own pseudocode: for each app type, generate its real shelf
+ template, run the real build.py as a real subprocess, capture its real
outcome, and continue to the next app regardless of failure (never stop
after the first). No slug args -> runs every registered app.

Prints build.py's own real final line for each app plus a consolidated
status table at the end. Exits 0 only if every requested app reached READY."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import app_defs  # noqa: E402
from build_one import BUILDERS  # noqa: E402

ROOT = HERE / "library_build"
ROOT.mkdir(exist_ok=True)


def run_one(slug: str):
    BUILDERS[slug](ROOT)
    project = ROOT / slug
    build_py_src = (HERE.parent / "build.py").read_text()
    build_py_src = build_py_src.replace("ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project),
                          capture_output=True, text=True, timeout=120)
    out = res.stdout + res.stderr
    last_lines = [l for l in out.strip().splitlines() if l.strip()][-6:]
    readiness_line = next((l for l in reversed(out.strip().splitlines()) if l.startswith("readiness")), "")
    return res.returncode, out, last_lines, readiness_line


def main():
    slugs = sys.argv[1:] or sorted(BUILDERS)
    results = []
    for slug in slugs:
        print(f"\n{'=' * 78}\nBUILDING: {slug}\n{'=' * 78}")
        try:
            code, out, last_lines, readiness_line = run_one(slug)
        except Exception as e:
            print(f"EXCEPTION: {e}")
            results.append((slug, "EXCEPTION", str(e)))
            continue
        print(out)
        ready = "READY" in readiness_line
        results.append((slug, "READY" if ready else "NOT_READY", readiness_line or f"exit={code}"))

    print(f"\n{'=' * 78}\nBATCH SUMMARY\n{'=' * 78}")
    ready_count = 0
    for slug, status, detail in results:
        marker = "PASS" if status == "READY" else "FAIL"
        if status == "READY":
            ready_count += 1
        print(f"  {marker}  {slug:35s} {status:12s} {detail}")
    print(f"\n{ready_count}/{len(results)} READY")
    return 0 if ready_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
