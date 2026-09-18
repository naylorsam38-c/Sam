#!/usr/bin/env python3
"""
layer1_checks.py -- the hard checks. The whole job on a good day.

No model. No cost. It rebuilds the working directory, starts the real system as
a real process on its own port, runs every check, drives a real browser through
a human journey at level 1, shuts the process down, and writes the run record.

It does not reimplement any of that. The checks that prove this app are already
written and already proven -- `host_test.py` in `4_host/`. This runs that, for
real, as its own process, and reads the run record it leaves behind. Two copies
of the same checks would drift, and the copy that drifted would be the one
reporting PASS.

**Never** repairs anything, calls a model, or decides what to do next. It reports
and exits. Judgement belongs to chain.py.

Standard: god mode, BUILD_CHAIN_STANDARD.md `layer1_checks.py`; Script Standard
1.2, 5, 6.

Usage:  layer1_checks.py                run the suite
        layer1_checks.py --last         print the last run's verdict, run nothing
"""

# =====================================================================
# CONFIGURATION BLOCK -- one comment per setting, above all logic.
# =====================================================================

CHECK_SUITE = "../4_host/host_test_data_dashboard.py"
# The suite that actually drives the system. If altered: that script is run
# instead. It must write a run record (see run_record.py) or this cannot
# report anything and exits 2.
# 2026-09-18: pointed at the data-dashboard (Redash) suite for this app's
# chain run -- was host_test_challenge_platform.py (CTFd) before that, and
# "./host_test.py" (event-ticketing/Indico) originally. Per
# HARVEST_TWO_MORE_APPS.md step 5: "pass the app through as that script's
# config expects" -- chain.py has no app-slug parameter of its own, so this
# config block is what actually selects which app the chain drives.

SUITE_ENV = {
    "REDASH_DATABASE_URL": "postgresql://redash_app:redash_app_pw@localhost/redash",
    "REDASH_REDIS_URL": "redis://localhost:6379/2",
    "REDASH_COOKIE_SECRET": "test-secret-for-harvest-eval-only",
    "REDASH_SECRET_KEY": "test-secret-for-harvest-eval-only",
    "PYTHONPATH": "/tmp/claude-0/-home-user-Sam/02357280-7cb7-5c2c-889b-4c54ea44631e/scratchpad/redash-src",
}
# Environment the suite needs to reach the real system. If altered: the suite
# runs against whatever is named here. A missing value is not substituted --
# the suite itself stops and says which one (Script Standard 1.4).

SUITE_TIMEOUT_SECONDS = 1800
# How long the suite may take before this gives up on it. If altered: a slower
# system is tolerated, or a hung one is caught sooner. A timeout is exit 2 --
# could not start -- never a failure, because a suite that never finished has
# not told you anything about the app.

RUNS_DIR = "./runs"
# Where run records are written and read. If altered: must match the suite's
# own runs directory and watch.py's, or each will be looking somewhere else.

LEVEL1_LEVEL = 1
# Which authority level counts as a complete human journey. If altered: a
# different level is treated as the one that proves a person can use the app.

REQUIRE_LEVEL1 = True
# True  = a suite with no level-1 check exits 3. Nothing about a real person
#         was proved, so the run is UNPROVEN rather than passed.
# False = a suite of lower-level checks alone may report 0. Turning this off
#         means a green run no longer means a person can use the app.

STREAM_SUITE_OUTPUT = True
# True  = the suite's own check lines appear as they happen, which is what
#         makes a long run readable.
# False = only this script's summary is printed.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import sys
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_record


def newest_run(before=None):
    """The highest-numbered run directory, optionally one that did not exist
    before the suite ran. Runs are found by literal directory name, never by
    reconstructing a number."""
    root = (HERE / RUNS_DIR).resolve()
    if not root.is_dir():
        return None
    runs = sorted(d for d in root.iterdir()
                  if d.is_dir() and (d / "run.json").is_file())
    if before is not None:
        runs = [d for d in runs if d.name not in before]
    return runs[-1] if runs else None


def existing_runs():
    root = (HERE / RUNS_DIR).resolve()
    if not root.is_dir():
        return set()
    return {d.name for d in root.iterdir() if d.is_dir()}


def verdict_from(record):
    """
    Read the run record and decide layer one's exit code from it.

    The suite's own exit code is not trusted on its own. The record is the
    evidence; the exit code is a claim about it. Where they disagree, that is
    itself a fault and this says so rather than picking the friendlier one.
    """
    checks = record.get("checks") or []
    failed = [c for c in checks if c.get("state") == "FAIL"]
    level1 = [c for c in checks if c.get("level") == LEVEL1_LEVEL]
    level1_passed = [c for c in level1 if c.get("state") == "PASS"]

    if not checks:
        return 2, "the suite claimed no checks at all", failed

    if REQUIRE_LEVEL1 and not level1:
        return 3, (f"no level-{LEVEL1_LEVEL} check is present in the suite -- "
                   f"nothing here proves a person can use the app"), failed

    if REQUIRE_LEVEL1 and not level1_passed and not failed:
        return 3, (f"every level-{LEVEL1_LEVEL} check was skipped -- a SKIP is "
                   f"not a pass"), failed

    if failed:
        return 1, f"{len(failed)} check(s) failed", failed

    return 0, f"all {len(checks)} checks passed", failed


def failure_records(record, failed):
    """
    The failure record layer two reads -- BUILD_CHAIN_STANDARD, HANDOFF
    CONTRACTS. Every field required. If a field cannot be filled the record is
    not written, because an incomplete record is how invented work gets in.
    """
    out = []
    for c in failed:
        rec = {
            "run": record.get("run"),
            "check": c.get("id"),
            "level": c.get("level"),
            "text": c.get("claim"),
            "message": c.get("detail"),
            # Which capability the failing check drives, where it drives one.
            # Layer three needs it to know where a part would go, and refuses
            # rather than guessing when it is absent.
            "capability": c.get("capability"),
        }
        required = ("run", "check", "level", "text", "message")
        missing = [k for k in required if rec.get(k) in (None, "")]
        if missing:
            print(f"FAIL  incomplete failure record for {c.get('id')}: "
                  f"missing {', '.join(missing)}")
            continue
        out.append(rec)
    return out


def main():
    if "--last" in sys.argv[1:]:
        d = newest_run()
        if not d:
            print("\nno run records\n0 checks claimed -- UNPROVEN")
            sys.exit(2)
        r = run_record.load(d)
        print(f"{r['run']}  {r.get('verdict')}  exit {r.get('exit_code')}")
        sys.exit(0)

    suite = (HERE / CHECK_SUITE).resolve()
    if not suite.is_file():
        print(f"\nCOULD NOT RUN: no check suite at {suite}")
        print("0 checks claimed -- UNPROVEN")
        sys.exit(2)

    before = existing_runs()
    env = dict(os.environ)
    env.update(SUITE_ENV)

    try:
        proc = subprocess.run(
            [sys.executable, str(suite)],
            cwd=str(HERE), env=env, timeout=SUITE_TIMEOUT_SECONDS,
            capture_output=not STREAM_SUITE_OUTPUT, text=True)
        suite_exit = proc.returncode
    except subprocess.TimeoutExpired:
        print(f"\nCOULD NOT RUN: the suite did not finish within "
              f"{SUITE_TIMEOUT_SECONDS}s")
        print("0 checks claimed -- UNPROVEN")
        sys.exit(2)

    run_dir = newest_run(before=before)
    if run_dir is None:
        print("\nCOULD NOT RUN: the suite left no run record, so nothing about "
              "this run can be audited")
        print("0 checks claimed -- UNPROVEN")
        sys.exit(2)

    try:
        record = run_record.load(run_dir)
    except Exception as e:
        print(f"\nCOULD NOT RUN: {run_dir}/run.json is unreadable: "
              f"{type(e).__name__}")
        print("0 checks claimed -- UNPROVEN")
        sys.exit(2)

    code, why, failed = verdict_from(record)

    print()
    if code == 2:
        print(f"COULD NOT RUN: {why}")
        print("0 checks claimed -- UNPROVEN")
        sys.exit(2)

    if suite_exit == 0 and code != 0:
        print(f"FAIL  the suite exited 0 but its own record says: {why}")
    elif suite_exit != 0 and code == 0:
        print(f"FAIL  the suite exited {suite_exit} but its own record shows "
              f"no failing check")
        code = 1

    if code == 1:
        recs = failure_records(record, failed)
        path = run_dir / "failures.json"
        path.write_text(json.dumps(recs, indent=2))
        for r in recs:
            print(f"FAIL  {r['check']}  {r['text']}")
            print(f"      {r['message']}")
        print(f"\n{record['run']}  layer one  {why} -- {len(recs)} failure "
              f"record(s) written for layer two")
        sys.exit(1)

    if code == 3:
        print(f"{record['run']}  layer one  UNPROVEN -- {why}")
        sys.exit(3)

    print(f"{record['run']}  layer one  {why}")
    sys.exit(0)


if __name__ == "__main__":
    main()
