#!/usr/bin/env python3
"""
run_full_verification.py — the one command that reproduces the entire
claimed proof from a fresh extraction: the internal proving-table
regression suite, all 43 canonical apps, all 3 composed apps, the
compatibility gate + dependency-graph + hidden-access audit, real
end-to-end functional tests, and the full-library stress test (every
capability in the whole library merged into one real running system,
proving zero URL-namespace collisions -- see FULL_LIBRARY_STRESS_TEST.md).
Every step runs as a real subprocess against real files this script
creates fresh under verification/ (library_build/, work/, fixtures/,
functest_scratch/, full_stress_test/) -- never against OUTPUT_LIBRARY or
NEW_APPS_FROM_LIBRARY, and never assuming anything from a prior run.

Writes a single machine-readable result to
verification/verification_result.json and prints it to stdout. Exit code
is 0 only if every section passed.

Needs: Flask + Playwright installed (see bootstrap.py) and a working
Chromium for Playwright (see bootstrap.py's step 3 and README.md) -- a
missing browser is reported as its own, separately-labeled FAIL rather
than silently skipped or than failing every other section too.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

ALL_43_APPS = None  # filled in below from build_one.BUILDERS + todo_list


def run(args, cwd=HERE, timeout=600):
    t0 = time.time()
    res = subprocess.run([PY] + args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return {"ok": res.returncode == 0, "returncode": res.returncode,
            "seconds": round(time.time() - t0, 1), "stdout": res.stdout, "stderr": res.stderr}


def section(title):
    print(f"\n{'#' * 78}\n# {title}\n{'#' * 78}")


def main():
    sys.path.insert(0, str(HERE))
    from build_one import BUILDERS  # noqa: E402

    for d in ("library_build", "work", "fixtures", "gen_prove", "functest_scratch", "full_stress_test"):
        p = HERE / d
        if p.exists():
            shutil.rmtree(p)

    report = {"sections": {}}

    # 1. Internal proving-table regression suite (build.py's own mechanism
    # tests -- unaffected by anything in the capability library).
    section("1/7  Internal regression suite (verify_build.py + test_readiness.py)")
    r1 = run(["gen_fixtures.py"])
    r2 = run(["verify_build.py"])
    r3 = run(["test_readiness.py"])
    print(r2["stdout"][-2000:])
    print(r3["stdout"][-500:])
    m = None
    for line in r2["stdout"].splitlines():
        if line.strip().endswith("/29 pass"):
            m = line.strip()
    report["sections"]["proving_table"] = {
        "verify_build_29": m or "UNKNOWN", "verify_build_ok": r2["ok"],
        "test_readiness_ok": r3["ok"],
    }

    # 2. All 43 canonical apps.
    section("2/7  All 43 canonical apps (build_batch.py)")
    r4 = run(["build_batch.py"], timeout=1800)
    print(r4["stdout"][-3000:])
    ready_line = next((l for l in r4["stdout"].splitlines() if l.strip().endswith("READY")
                        and "/" in l and l.strip()[0].isdigit()), None)
    report["sections"]["canonical_apps"] = {
        "result_line": ready_line, "ok": r4["ok"], "expected_count": len(BUILDERS),
    }

    # 3. The 3 new composed apps.
    section("3/7  3 new composed apps")
    new_apps = {}
    for script in ("new_app_event_board.py", "new_app_fitness_challenge.py", "new_app_course_enrollment.py"):
        r = run([script], timeout=180)
        print(r["stdout"][-1000:])
        new_apps[script] = "READY" in r["stdout"] and r["ok"]
    report["sections"]["new_composed_apps"] = new_apps

    # 4. Generalized-engine regression (auction/event_ticketing/dating vs.
    # their generic-generator equivalents).
    section("4/7  Generalized-engine regression (prove_generalization.py)")
    r5 = run(["prove_generalization.py"], timeout=300)
    print(r5["stdout"][-1500:])
    report["sections"]["generalization_regression"] = {"ok": r5["ok"], "all_match": "ALL MATCH" in r5["stdout"]}

    # 5. Compatibility gate (exercised for real by every build above) +
    # recursive dependency-graph + hidden-data-access audit across the
    # WHOLE library at once.
    section("5/7  Compatibility gate + dependency-graph + hidden-access audit")
    r6 = run(["audit_dependency_graph.py"], timeout=120)
    print(r6["stdout"])
    report["sections"]["dependency_graph_audit"] = {"ok": r6["ok"], "output": r6["stdout"].strip().splitlines()[-1]}

    # 6. Real end-to-end functional tests, disposable copies only.
    section("6/7  End-to-end functional tests (functional_tests.py)")
    r7 = run(["functional_tests.py"], timeout=300)
    print(r7["stdout"])
    try:
        func_json = json.loads(r7["stdout"].strip().splitlines()[-1])
    except Exception:
        func_json = {"passed": 0, "total": 0}
    report["sections"]["functional_tests"] = {"ok": r7["ok"], **func_json}

    # 7. Full-library stress test: every capability in the whole library
    # merged into one real running system -- the one thing per-app
    # isolation testing (sections 1-6) structurally cannot see. Must report
    # zero collisions and zero shadowed capabilities; see
    # FULL_LIBRARY_STRESS_TEST.md for what this caught before the routes
    # were namespaced by owning app.
    section("7/7  Full-library stress test (full_library_stress_test.py)")
    r8 = run(["full_library_stress_test.py"], timeout=180)
    print(r8["stdout"][-3000:])
    try:
        stress_json = json.loads((HERE / "full_stress_test" / "stress_result.json").read_text())
        stress_summary = stress_json["summary"]
    except Exception:
        stress_summary = {"pass": 0, "shadowed": -1, "other_fail": -1, "total": 0}
    stress_ok = r8["ok"] and stress_summary["shadowed"] == 0 and stress_summary["other_fail"] == 0
    report["sections"]["full_library_stress_test"] = {"ok": stress_ok, **stress_summary}

    overall_ok = (
        report["sections"]["proving_table"]["verify_build_ok"]
        and report["sections"]["proving_table"]["test_readiness_ok"]
        and report["sections"]["canonical_apps"]["ok"]
        and all(new_apps.values())
        and report["sections"]["generalization_regression"]["all_match"]
        and r6["ok"]
        and r7["ok"]
        and stress_ok
    )
    report["overall"] = "PASS" if overall_ok else "FAIL"

    out_path = HERE / "verification_result.json"
    out_path.write_text(json.dumps(report, indent=2))
    section("FINAL RESULT")
    print(json.dumps(report, indent=2))
    print(f"\nWritten to {out_path}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
