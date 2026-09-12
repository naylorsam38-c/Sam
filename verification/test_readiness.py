#!/usr/bin/env python3
"""
test_readiness.py — round 6 proving table for build.py's stage three
(readiness classification + library promotion, folded into build.py itself
this round from round 5's separate readiness_and_library.py).

Runs AFTER gen_fixtures.py + verify_build.py, against the real project
directories they already left on disk under work/<row>/ (real build.py runs,
real registry.json, real run_ledger.jsonl, real reports/). No fixture data is
synthesized here.

Every check below invokes the REAL build.py as a REAL subprocess with
cwd=<that row's project directory> -- exactly how build.py is invoked for a
real build (see verify_build.py's own run_build()) and exactly how a human
would run it: `python3 build.py --readiness <app_type> [app_id]` and
`python3 build.py --promote <app_id>`. This is deliberately not an in-process
import: build.py's own config-block paths (TEMPLATES_DIR, SHELF_DIR, etc.)
are resolved once against the process's cwd, matching its "cwd is the
project directory" convention used everywhere else in this file -- so
proving the CLI really works, per-row, in its own subprocess, is both the
correct way to test it and a stronger proof than calling the underlying
functions directly would have been.

Usage:
    cd verification && python3 gen_fixtures.py && python3 verify_build.py \
        && python3 test_readiness.py
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
BUILD_PY = HERE.parent / "build.py"
PY = sys.executable

FAILURES = []


def _app_id_and_type(project_dir: Path):
    reg = json.loads((project_dir / "registry.json").read_text(encoding="utf-8"))
    apps = reg.get("applications", [])
    app_id = apps[0]["id"] if apps else None
    choice = json.loads((project_dir / "choice.json").read_text(encoding="utf-8"))
    return app_id, choice["app_type"]


def run_readiness(project_dir: Path, app_type: str, app_id: str = None):
    args = [PY, str(BUILD_PY), "--readiness", app_type] + ([app_id] if app_id else [])
    res = subprocess.run(args, cwd=str(project_dir), capture_output=True, text=True, timeout=60)
    out = (res.stdout or "").strip()
    if "  --  " not in out:
        return "PARSE_ERROR", f"exit={res.returncode} stdout={out!r} stderr={(res.stderr or '').strip()!r}"
    state, reason = out.split("  --  ", 1)
    return state.strip(), reason.strip()


def run_promote(project_dir: Path, app_id: str):
    args = [PY, str(BUILD_PY), "--promote", app_id]
    res = subprocess.run(args, cwd=str(project_dir), capture_output=True, text=True, timeout=60)
    out = (res.stdout or "").strip()
    ok = out.startswith("PROMOTED")
    return ok, out, res.returncode


def check_state(row: str, expected: str):
    project_dir = WORK / row
    if not project_dir.is_dir():
        FAILURES.append(f"{row}: fixture directory missing — did gen_fixtures.py/verify_build.py run first?")
        return
    app_id, app_type = _app_id_and_type(project_dir)
    state, reason = run_readiness(project_dir, app_type, app_id)
    mark = "PASS" if state == expected else "FAIL"
    print(f"{mark}  {row:32s} expected {expected:20s} got {state:20s}  {reason}")
    if state != expected:
        FAILURES.append(f"{row}: expected {expected}, got {state} ({reason})")


def main() -> int:
    print("== `build.py --readiness` (real subprocess, real cwd) against real build.py output ==\n")
    # Rows chosen to cover every readiness state a real build.py run actually
    # reaches (REFERENCE_ONLY and TEMPLATE_COMPLETE are pre-registry states
    # no proving-table row models, since every row starts from an
    # already-accepted template by design).
    check_state("row06_missing_shelf_cap", "CAPABILITIES_UNBOUND")
    check_state("row07_contract_mismatch", "BUILD_FAILED")
    # PROVEN's own check_state() coverage moved below: build.py's stage three
    # now runs inside the SAME invocation that reaches BUILT (round 6 folded
    # readiness_and_library.py's promotion into build.py itself), so by the
    # time verify_build.py's subprocess for these three rows has already
    # exited, the app is already promoted -- querying readiness afterward
    # correctly reports READY, not PROVEN. PROVEN-before-promotion is proven
    # separately below by deleting the library copy build.py just made and
    # re-querying (the "acceptance" block), which is the only way to observe
    # that intermediate state honestly now that promotion is automatic.
    check_state("row08_09_10_run_twice", "READY")
    check_state("row13_bad_health", "START_FAILED")
    check_state("row14_gap_no_repair", "RUNTIME_FAILED")
    check_state("row17_loop_guard", "RUNTIME_FAILED")
    check_state("row18_regression", "RUNTIME_FAILED")
    check_state("row19_restart_ceiling", "RUNTIME_FAILED")
    check_state("row20_repeated_gap", "RUNTIME_FAILED")
    check_state("row21a_no_browser_check", "BROWSER_TEST_FAILED")
    check_state("row21b_browser_check_fails", "BROWSER_TEST_FAILED")
    check_state("row23_full_real_journey", "READY")
    check_state("rowG1_generic_checks", "READY")

    print("\n== `build.py --promote` (real subprocess, real cwd) ==\n")

    # Refusal: a candidate (never reached BUILT) must never be promotable.
    project_dir = WORK / "row17_loop_guard"
    app_id, _ = _app_id_and_type(project_dir)
    ok, out, code = run_promote(project_dir, app_id)
    mark = "PASS" if (not ok and code == 1) else "FAIL"
    print(f"{mark}  refuses to promote a candidate app (exit={code})            {out}")
    if ok or code != 1:
        FAILURES.append(f"--promote wrongly accepted a candidate app or wrong exit code: {out!r} exit={code}")

    # Refusal: an unknown app_id must never be promotable.
    ok, out, code = run_promote(project_dir, "APP-999")
    mark = "PASS" if (not ok and code == 1) else "FAIL"
    print(f"{mark}  refuses to promote an app_id not in the registry (exit={code})  {out}")
    if ok or code != 1:
        FAILURES.append(f"--promote wrongly accepted an unknown app_id or wrong exit code: {out!r} exit={code}")

    # Acceptance: a real BUILT (active) app promotes, evidence included, and
    # `--readiness ... <app_id>` then reports LIBRARY_STORED -> READY.
    project_dir = WORK / "row23_full_real_journey"
    app_id, app_type = _app_id_and_type(project_dir)
    lib_dir = project_dir / "library" / app_id
    if lib_dir.exists():
        shutil.rmtree(lib_dir)

    state, reason = run_readiness(project_dir, app_type, app_id)
    mark = "PASS" if state == "PROVEN" else "FAIL"
    print(f"{mark}  proven-but-unpromoted reports PROVEN                       {reason}")
    if state != "PROVEN":
        FAILURES.append(f"expected PROVEN before promotion, got {state}")

    ok, out, code = run_promote(project_dir, app_id)
    mark = "PASS" if (ok and code == 0) else "FAIL"
    print(f"{mark}  promotes a real BUILT (active) app (exit={code})             {out}")
    if not ok or code != 0:
        FAILURES.append(f"--promote wrongly refused a real active app, or wrong exit code: {out!r} exit={code}")

    required = ["registry.json", "app.json", "locators.json", "PROMOTED.json"]
    missing = [f for f in required if not (lib_dir / f).is_file()]
    mark = "PASS" if not missing else "FAIL"
    print(f"{mark}  library copy contains registry/app/locators + marker       missing={missing}")
    if missing:
        FAILURES.append(f"library copy missing expected files: {missing}")

    evidence = list((lib_dir / "evidence").glob("*.json")) if (lib_dir / "evidence").is_dir() else []
    mark = "PASS" if evidence else "FAIL"
    print(f"{mark}  at least one real evidence run report copied                {[e.name for e in evidence]}")
    if not evidence:
        FAILURES.append("no evidence run report copied into the library promotion")

    state, reason = run_readiness(project_dir, app_type, app_id)
    mark = "PASS" if state == "READY" else "FAIL"
    print(f"{mark}  promoted app now reports READY                             {reason}")
    if state != "READY":
        FAILURES.append(f"expected READY after promotion, got {state}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all readiness/library checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
