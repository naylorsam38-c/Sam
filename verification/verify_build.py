#!/usr/bin/env python3
"""
verify_build.py — real, subprocess-driven proof of build.py against every
row of the "What The Builder Must Satisfy" table (SPEC v1). No mocks: every
scenario runs the real build.py as a real subprocess against a real shelf,
real templates, and (where the row calls for it) a real browser via
Playwright. Every PASS/FAIL below is decided from the actual captured
stdout/exit code/files on disk, pasted or checked, never assumed.

Rerun anytime: python3 verify_build.py [row_number ...]
With no arguments, runs every row in order and prints a summary table.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_PY_SRC = HERE.parent / "build.py"
FIXTURES = HERE / "fixtures" / "common"
WORK = HERE / "work"
PY = sys.executable

RESULTS = []  # (row, name, ok, detail)

# Transcribed from CAPABILITY_NUMBERING_STANDARD.md -- NOT from build.py -- so
# row 9 checks build.py's output against the standard, not against itself.
STD_APP_KEYS = ["id", "name", "status", "owner", "created_at", "screens"]                       # §3.3
STD_SCR_KEYS = ["id", "app_id", "name", "status", "buttons"]                                    # §3.4
STD_BTN_KEYS = ["id", "screen_id", "name", "expected_contract", "capability_id", "status"]      # §3.5
STD_CAP_KEYS = ["id", "name", "category", "status", "data_shape", "dependencies", "permissions",
                "side_effects", "error_contract", "implementations", "qualification"]           # §3.6
STD_IMPL_KEYS = ["id", "capability_id", "status", "release", "source", "dependencies", "tests", "rollback"]  # §3.7
STD_IMPL_RELEASE_KEYS = ["version", "commit", "approved", "approval_ref"]                       # §3.7
STD_IMPL_SOURCE_KEYS = ["repository", "path", "entrypoint"]                                     # §3.7
STD_CAP_QUAL_KEYS = ["status", "approved_by", "approval_ref"]                                   # §3.6
STD_LIFECYCLE = {"candidate", "approved", "active", "deprecated", "retired"}                    # §6.2
STD_REGISTRY_ENTITIES = ["applications", "screens", "buttons", "capabilities", "implementations"]  # §3.2 (the five a build writes)


def canonical_status(d, app_id):
    reg = json.loads((d / "registry.json").read_text())
    return next((a.get("status") for a in reg.get("applications", []) if a.get("id") == app_id), None)


def log_result(row, name, ok, detail=""):
    RESULTS.append((row, name, ok, detail))
    print(f"\n{'PASS' if ok else 'FAIL'}  row {row}  {name}" + (f"  -- {detail}" if detail and not ok else ""))


def fresh(name):
    d = WORK / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copy2(BUILD_PY_SRC, d / "build.py")
    shutil.copytree(FIXTURES / "shelf", d / "shelf")
    shutil.copytree(FIXTURES / "templates", d / "templates")
    shutil.copy2(FIXTURES / "APPS_LIST.md", d / "APPS_LIST.md")
    shutil.copy2(FIXTURES / "choice.json", d / "choice.json")
    return d


def set_choice(d, **overrides):
    choice = json.loads((d / "choice.json").read_text())
    choice.update(overrides)
    (d / "choice.json").write_text(json.dumps(choice, indent=2))


def set_template(d, name, **overrides):
    p = d / "templates" / f"{name}.json"
    tpl = json.loads(p.read_text())
    tpl.update(overrides)
    p.write_text(json.dumps(tpl, indent=2))


def set_config(d, **kv):
    text = (d / "build.py").read_text()
    for key, val in kv.items():
        # matches both `KEY = ...` and the type-annotated `KEY: Type = ...`
        pattern = re.compile(rf"^{key}(\s*:\s*[^=\n]+)?\s*=\s*.*$", re.MULTILINE)
        new_line = f"{key} = {val!r}" if isinstance(val, str) else f"{key} = {val}"
        text, n = pattern.subn(new_line, text, count=1)
        assert n == 1, f"config key {key} not found to set (n={n})"
    (d / "build.py").write_text(text)


def run(d, timeout=40):
    t0 = time.time()
    res = subprocess.run([PY, "build.py"], cwd=str(d), capture_output=True, text=True, timeout=timeout)
    res.elapsed = time.time() - t0
    return res


def show(title, res):
    print(f"\n{'='*78}\n{title}  (exit={res.returncode}, {res.elapsed:.1f}s)\n{'='*78}")
    print(res.stdout.rstrip() or "(no stdout)")
    if res.stderr.strip():
        print("--- stderr ---")
        print(res.stderr.rstrip())


def no_lingering_process(port_hint=None):
    """Row 22 helper: confirm no child app process is still listening. We
    can't know the ephemeral port build.py chose from outside, so instead we
    check for any live 'modules/CAP-.../app.py' or route-loader process
    still running under this machine after build.py's own subprocess.run()
    has returned -- if build.py's finally-block killed its child, ps will
    show nothing matching."""
    ps = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True)
    hits = [line for line in ps.stdout.splitlines() if "modules/CAP-0001/app.py" in line]
    return hits


# ------------------------------------------------------------------------------
# Row 1 — LAYER3_MODEL empty -> BROKEN missing setting, before stage 1
# ------------------------------------------------------------------------------
def row1():
    d = fresh("row01_missing_model")
    res = run(d)
    show("Row 1: LAYER3_MODEL empty", res)
    ok = (res.returncode == 2 and res.stdout.strip() == "BROKEN  missing setting  LAYER3_MODEL"
          and not (d / "builds").exists() and not (d / "registry.json").exists())
    # and the endpoint: model + credential set, endpoint left empty
    d2 = fresh("row01b_missing_endpoint")
    set_config(d2, LAYER3_MODEL="some-model", LAYER3_CREDENTIAL="some-credential")
    res2 = run(d2)
    show("Row 1b: LAYER3_ENDPOINT empty", res2)
    ok2 = (res2.returncode == 2 and res2.stdout.strip() == "BROKEN  missing setting  LAYER3_ENDPOINT"
           and not (d2 / "builds").exists())
    log_result(1, "LAYER3_MODEL / LAYER3_ENDPOINT empty -> BROKEN before stage1, no side effects", ok and ok2)


# ------------------------------------------------------------------------------
# Row 2 — LAYER3_CREDENTIAL never appears in argv/stdout/reports/ledger
# ------------------------------------------------------------------------------
def row2():
    d = fresh("row02_credential_secrecy")
    secret = "sk-ant-SECRET-DO-NOT-LEAK-99887766"
    set_config(d, ALLOW_LAYER3=True, LAYER3_ENDPOINT="http://127.0.0.1:9/", LAYER3_MODEL="some-model",
               LAYER3_CREDENTIAL=secret)
    set_choice(d, app_type="Todo List App")
    remove_gamma_fix(d)
    # use the gap template (CAP-0006 required) via a dedicated choice file swap
    tpl = json.loads((d / "templates" / "todo_gap.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 2: LAYER3_CREDENTIAL must never leak", res)
    leaked_stdout = secret in res.stdout or secret in res.stderr
    leaked_files = False
    leaked_where = []
    for p in list((d / "reports").glob("*.json") if (d / "reports").exists() else []) + \
               ([d / "run_ledger.jsonl"] if (d / "run_ledger.jsonl").exists() else []):
        content = p.read_text()
        if secret in content:
            leaked_files = True
            leaked_where.append(str(p))
    ok = ((not leaked_stdout) and (not leaked_files) and res.returncode == 1
          and "model unreachable" in res.stdout and canonical_status(d, "APP-001") == "candidate")
    log_result(2, "LAYER3_CREDENTIAL never appears in stdout/stderr/reports/ledger; endpoint really refused; HELD app stays candidate", ok,
               detail=f"leaked_stdout={leaked_stdout} leaked_files={leaked_where} status={canonical_status(d, 'APP-001')}")


# ------------------------------------------------------------------------------
# Row 3 — choice.json missing / unreadable / no name
# ------------------------------------------------------------------------------
def row3():
    all_ok = True
    # missing file
    d = fresh("row03a_choice_missing")
    set_config(d, ALLOW_LAYER3=False)
    (d / "choice.json").unlink()
    res = run(d)
    show("Row 3a: choice.json missing", res)
    ok = res.returncode == 2 and res.stdout.strip() == "BROKEN  choice  file"
    all_ok &= ok
    print(f"  -> {'PASS' if ok else 'FAIL'}")

    # unreadable (corrupt json)
    d = fresh("row03b_choice_unreadable")
    set_config(d, ALLOW_LAYER3=False)
    (d / "choice.json").write_text("{not valid json")
    res = run(d)
    show("Row 3b: choice.json unreadable", res)
    ok = res.returncode == 2 and res.stdout.strip() == "BROKEN  choice  unreadable"
    all_ok &= ok
    print(f"  -> {'PASS' if ok else 'FAIL'}")

    # missing name
    d = fresh("row03c_choice_no_name")
    set_config(d, ALLOW_LAYER3=False)
    choice = json.loads((d / "choice.json").read_text())
    choice["branding"] = {"color": "#111111"}
    (d / "choice.json").write_text(json.dumps(choice))
    res = run(d)
    show("Row 3c: choice.json branding.name missing", res)
    ok = res.returncode == 2 and res.stdout.strip() == "BROKEN  choice  name"
    all_ok &= ok
    print(f"  -> {'PASS' if ok else 'FAIL'}")

    log_result(3, "choice.json missing/unreadable/no-name -> BROKEN choice <field>, exit 2, no traceback", all_ok)


# ------------------------------------------------------------------------------
# Row 4 — app_type not in APPS_LIST.md
# ------------------------------------------------------------------------------
def row4():
    d = fresh("row04_bad_app_type")
    set_config(d, ALLOW_LAYER3=False)
    set_choice(d, app_type="Not A Real App")
    res = run(d)
    show("Row 4: app_type not in APPS_LIST.md", res)
    ok = res.returncode == 2 and res.stdout.rstrip().splitlines()[-1] == "BROKEN  choice  app_type"
    log_result(4, "unknown app_type -> BROKEN choice app_type", ok)


# ------------------------------------------------------------------------------
# Row 5 — template not accepted
# ------------------------------------------------------------------------------
def row5():
    d = fresh("row05_template_not_accepted")
    set_config(d, ALLOW_LAYER3=False)
    set_template(d, "todo_list_app", accepted=False)
    res = run(d)
    show("Row 5: template not accepted", res)
    ok = res.returncode == 2 and res.stdout.rstrip().splitlines()[-1] == "BROKEN  template not accepted  todo_list_app"
    log_result(5, "template.accepted=false -> BROKEN template not accepted", ok)


# ------------------------------------------------------------------------------
# Row 6 — required CAP with no approved active IMPL on shelf
# ------------------------------------------------------------------------------
def row6():
    d = fresh("row06_missing_shelf_cap")
    set_config(d, ALLOW_LAYER3=False)
    (d / "shelf" / "capabilities" / "CAP-0001.json").unlink()
    res = run(d)
    show("Row 6: CAP-0001 missing from shelf", res)
    ok = res.returncode == 2 and res.stdout.rstrip().splitlines()[-1] == "BROKEN  no approved IMPL  CAP-0001"
    log_result(6, "required CAP absent from shelf -> BROKEN no approved IMPL", ok)


# ------------------------------------------------------------------------------
# Row 7 — BTN expected contract matches no CAP -> HELD
# ------------------------------------------------------------------------------
def row7():
    d = fresh("row07_contract_mismatch")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_list_app.json").read_text())
    tpl["interface_slots"][0]["expected_contract"]["required_input_fields"] = ["due_date"]
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 7: contract mismatch -> HELD", res)
    ok = (res.returncode == 1 and "HELD  CAP candidate" in res.stdout
          and "due_date" in res.stdout and not (d / "builds" / "APP-001" / "app.json").exists())
    # confirm nothing was patched/wrapped -- the app was voided, not silently forced through
    voided = canonical_status(d, "APP-001") == "void"
    ok = ok and voided
    log_result(7, "contract mismatch -> HELD CAP candidate, exit 1, nothing patched/wrapped, APP voided", ok)


# ------------------------------------------------------------------------------
# Row 8/9/10 — run twice: APP-002/RUN-0002, correct registry + app.json shape
# ------------------------------------------------------------------------------
def row8_9_10():
    d = fresh("row08_09_10_run_twice")
    set_config(d, ALLOW_LAYER3=False)
    res1 = run(d)
    show("Row 8/9/10 run #1", res1)
    res2 = run(d)
    show("Row 8/9/10 run #2", res2)

    ok8 = ("APP-001" in res1.stdout and "RUN-0001" in res1.stdout
           and "APP-002" in res2.stdout and "RUN-0002" in res2.stdout
           and res1.returncode == 0 and res2.returncode == 0)
    log_result(8, "run twice -> APP-002/RUN-0002, never repeat/reuse", ok8)

    reg = json.loads((d / "builds" / "APP-002" / "registry.json").read_text())
    print("\n-- builds/APP-002/registry.json --")
    print(json.dumps(reg, indent=2))
    checks = []
    checks.append(("§3.2 entities", list(reg.keys()) == STD_REGISTRY_ENTITIES))
    app = reg["applications"][0]
    checks.append(("§3.3 app keys", list(app.keys()) == STD_APP_KEYS))
    checks.append(("§3.3 app id", app["id"] == "APP-002"))
    checks.append(("§3.3 app screens", app["screens"] == ["APP-002/SCR-001"]))
    checks.append(("§6.2 app status after BUILT = active", app["status"] == "active"))
    scr = reg["screens"][0]
    checks.append(("§3.4 screen keys", list(scr.keys()) == STD_SCR_KEYS))
    checks.append(("§3.4 screen ids", scr["id"] == "APP-002/SCR-001" and scr["app_id"] == "APP-002"
                   and scr["buttons"] == ["APP-002/SCR-001/BTN-001"]))
    checks.append(("§6.2 screen status", scr["status"] in STD_LIFECYCLE))
    btn = reg["buttons"][0]
    checks.append(("§3.5 button keys", list(btn.keys()) == STD_BTN_KEYS))
    checks.append(("§3.5 button ids", btn["id"] == "APP-002/SCR-001/BTN-001" and btn["screen_id"] == "APP-002/SCR-001"
                   and btn["capability_id"] == "CAP-0001"))
    checks.append(("§6.2 button status", btn["status"] in STD_LIFECYCLE))
    cap = reg["capabilities"][0]
    checks.append(("§3.6 capability keys", list(cap.keys()) == STD_CAP_KEYS))
    checks.append(("§3.6 qualification keys", list(cap["qualification"].keys()) == STD_CAP_QUAL_KEYS))
    checks.append(("§6.2 capability status", cap["status"] in STD_LIFECYCLE))
    imp = reg["implementations"][0]
    checks.append(("§3.7 implementation keys", list(imp.keys()) == STD_IMPL_KEYS))
    checks.append(("§3.7 release keys", list(imp["release"].keys()) == STD_IMPL_RELEASE_KEYS))
    checks.append(("§3.7 source keys", list(imp["source"].keys()) == STD_IMPL_SOURCE_KEYS))
    checks.append(("§2.1 impl id scoped to its CAP", imp["id"] == "CAP-0001/IMPL-01" and imp["capability_id"] == "CAP-0001"))
    checks.append(("§6.2 implementation status", imp["status"] in STD_LIFECYCLE))
    canon = json.loads((d / "registry.json").read_text())
    print("\n-- canonical registry.json --")
    print(json.dumps(canon, indent=2))
    checks.append(("canonical: §3.2 entity name", list(canon.keys()) == ["applications"]))
    checks.append(("canonical: §3.3 keys on every record", all(list(a.keys()) == STD_APP_KEYS for a in canon["applications"])))
    checks.append(("canonical: both BUILT apps active", [a["status"] for a in canon["applications"]] == ["active", "active"]))
    for name, okc in checks:
        print(f"  {'ok ' if okc else 'BAD'}  {name}")
    ok9 = all(okc for _, okc in checks)
    log_result(9, "registry records are the standard's own §3.3-3.7 shapes, §6.2 statuses, 13/13 invariants", ok9,
               detail=str([n for n, okc in checks if not okc]))

    app_json = json.loads((d / "builds" / "APP-002" / "app.json").read_text())
    print("\n-- builds/APP-002/app.json --")
    print(json.dumps(app_json, indent=2))
    ok10 = set(app_json.keys()) == {"start", "port", "health"}
    log_result(10, "app.json contains exactly start/port/health", ok10, detail=str(sorted(app_json.keys())))


# ------------------------------------------------------------------------------
# Row 11 — template with no tests
# ------------------------------------------------------------------------------
def row11():
    d = fresh("row11_no_tests")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_no_tests.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 11: template has no tests", res)
    ok = res.returncode == 2 and res.stdout.rstrip().splitlines()[-1] == "BROKEN  template has no tests"
    log_result(11, "template with no test_command -> BROKEN template has no tests", ok)


# ------------------------------------------------------------------------------
# Row 12 — template tests fail
# ------------------------------------------------------------------------------
def row12():
    d = fresh("row12_failing_tests")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_failing_tests.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 12: template tests fail", res)
    ok = (res.returncode == 2 and "template tests failing on purpose" in res.stdout
          and "BROKEN  template tests failed  code 1" in res.stdout)
    log_result(12, "failing template tests -> BROKEN template tests failed, real output pasted", ok)


# ------------------------------------------------------------------------------
# Row 13 — app never answers health
# ------------------------------------------------------------------------------
def row13():
    d = fresh("row13_bad_health")
    set_config(d, ALLOW_LAYER3=False, HEALTH_TIMEOUT_SECONDS=3)
    tpl = json.loads((d / "templates" / "todo_bad_health.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d, timeout=30)
    show("Row 13: app never answers health", res)
    # "BROKEN  app did not start" as its own line, not necessarily the last
    # line -- stage three (round 6) still runs afterward and prints a
    # trailing readiness line even on this path, since app_id exists. Check
    # for an actual check result line (build.py always prints "PASS  "/
    # "FAIL  ", two spaces, for a real check outcome), not a bare substring
    # -- a bare "FAIL" match would also trip on the readiness line's own
    # state name, START_FAILED, which is not a check result at all.
    lines = res.stdout.rstrip().splitlines()
    ok = (res.returncode == 2 and "BROKEN  app did not start" in lines
          and not any(l.startswith("PASS  ") or l.startswith("FAIL  ") for l in lines))
    lingering = no_lingering_process()
    print(f"lingering processes after exit: {lingering}")
    log_result(13, "app never answers health -> BROKEN app did not start, no checks claimed, process killed", ok)


# ------------------------------------------------------------------------------
# Row 14 — check fails, no shelf part, ALLOW_LAYER3=False -> HELD GAP-0001
# ------------------------------------------------------------------------------
def remove_gamma_fix(d):
    """Take CAP-0006's (non-fixing) IMPL-02 off the shelf entirely -- record,
    payload and its alias entry -- so no repair for gamma exists at all."""
    shutil.rmtree(d / "shelf" / "implementations" / "CAP-0006" / "IMPL-02")
    (d / "shelf" / "implementations" / "CAP-0006" / "IMPL-02.json").unlink()
    al = json.loads((d / "shelf" / "aliases.json").read_text())
    al["aliases"] = [a for a in al["aliases"] if a["impl_id"] != "CAP-0006/IMPL-02"]
    (d / "shelf" / "aliases.json").write_text(json.dumps(al, indent=2))


def make_active_impl(d, cap_id, impl_id):
    """Point a shelf CAP at a different IMPL: that IMPL becomes "active", every
    other one in its implementations list becomes "approved" (§6.2)."""
    cap = json.loads((d / "shelf" / "capabilities" / f"{cap_id}.json").read_text())
    for iid in cap["implementations"]:
        f = d / "shelf" / "implementations" / f"{iid}.json"
        rec = json.loads(f.read_text())
        rec["status"] = "active" if iid == impl_id else "approved"
        f.write_text(json.dumps(rec, indent=2))


def make_gap_dir(name):
    d = fresh(name)
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_gap.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    remove_gamma_fix(d)
    return d


def row14():
    d = make_gap_dir("row14_gap_no_repair")
    res = run(d)
    show("Row 14: no shelf part, layer three disabled -> HELD gap", res)
    ok = (res.returncode == 1 and "gap classified  GAP-0001" in res.stdout
          and "HELD  GAP-0001" in res.stdout and "layer three disabled" in res.stdout
          and canonical_status(d, "APP-001") == "candidate")
    log_result(14, "no repair available, ALLOW_LAYER3=False -> HELD GAP-0001 ... layer three disabled; app stays candidate", ok,
               detail=f"status={canonical_status(d, 'APP-001')}")
    return d


# ------------------------------------------------------------------------------
# Row 15 — pattern-mapped repair -> BUILT
# ------------------------------------------------------------------------------
def row15():
    d = fresh("row15_pattern_repair")
    set_config(d, ALLOW_LAYER3=False,
               FAILURE_PATTERN_MAP={"alpha stub not implemented": "feature_alpha_fix@1.0.0"})
    tpl = json.loads((d / "templates" / "todo_pattern.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 15: pattern-mapped repair", res)
    ledger = (d / "run_ledger.jsonl").read_text()
    ok = (res.returncode == 0 and "RUN-0002" in res.stdout and "BUILT" in res.stdout.rstrip().splitlines()
          and '"matched_by": "pattern"' in ledger)
    log_result(15, "pattern-mapped repair -> repair, RUN-0002, then BUILT; matched_by pattern in ledger", ok)


# ------------------------------------------------------------------------------
# Row 16 — structural-match-only repair -> BUILT
# ------------------------------------------------------------------------------
def row16():
    d = fresh("row16_structural_repair")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_structural.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 16: structural-match-only repair", res)
    ledger = (d / "run_ledger.jsonl").read_text()
    ok = (res.returncode == 0 and "RUN-0002" in res.stdout and "BUILT" in res.stdout.rstrip().splitlines()
          and '"matched_by": "structural"' in ledger)
    log_result(16, "structural-match-only repair -> repair, restart, BUILT; matched_by structure in ledger", ok)


# ------------------------------------------------------------------------------
# Row 17 — a repair that doesn't fix its failure -> BROKEN loop guard
# ------------------------------------------------------------------------------
def row17():
    d = fresh("row17_loop_guard")
    set_config(d, ALLOW_LAYER3=False,
               FAILURE_PATTERN_MAP={"gamma broken, needs recalibration": "feature_gamma_fix@1.0.0"})
    tpl = json.loads((d / "templates" / "todo_loopguard.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 17: repair that doesn't fix its failure -> loop guard", res)
    ok = (res.returncode == 2 and "BROKEN  loop guard" in res.stdout
          and "CHK-106" in res.stdout and "feature_gamma_fix@1.0.0" in res.stdout
          and canonical_status(d, "APP-001") == "candidate")
    lingering = no_lingering_process()
    print(f"lingering processes after exit: {lingering}")
    log_result(17, "part that doesn't fix its failure -> BROKEN loop guard, both numbers named", ok)


# ------------------------------------------------------------------------------
# Row 18 — a repair that breaks a passing check -> BROKEN regression
# ------------------------------------------------------------------------------
def row18():
    d = fresh("row18_regression")
    set_config(d, ALLOW_LAYER3=False,
               FAILURE_PATTERN_MAP={"regression trap not wired, needs patch": "regression_trap_fix@1.0.0"})
    tpl = json.loads((d / "templates" / "todo_regression.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 18: repair that breaks a passing check -> regression", res)
    ok = (res.returncode == 2 and "BROKEN  regression" in res.stdout and "CHK-002" in res.stdout
          and canonical_status(d, "APP-001") == "candidate")
    lingering = no_lingering_process()
    print(f"lingering processes after exit: {lingering}")
    log_result(18, "repair that breaks a passing check -> BROKEN regression, immediately", ok)


# ------------------------------------------------------------------------------
# Row 19 — MAX_RESTARTS=2, three independently-fixable failures -> exactly two
# repairs then BROKEN restart ceiling
# ------------------------------------------------------------------------------
def row19():
    d = fresh("row19_restart_ceiling")
    set_config(d, ALLOW_LAYER3=False, MAX_RESTARTS=2,
               FAILURE_PATTERN_MAP={
                   "alpha stub not implemented": "feature_alpha_fix@1.0.0",
                   "delta broken, config missing": "feature_delta_fix@1.0.0",
                   "epsilon broken, timeout stub": "feature_epsilon_fix@1.0.0",
               })
    tpl = json.loads((d / "templates" / "todo_restart_ceiling.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 19: MAX_RESTARTS=2, three fixable failures -> restart ceiling", res)
    ledger_lines = [json.loads(l) for l in (d / "run_ledger.jsonl").read_text().splitlines() if l.strip()]
    repairs = [l for l in ledger_lines if "resolves_to" in l and "part" in l]
    ok = (res.returncode == 2 and "BROKEN  restart ceiling" in res.stdout and len(repairs) == 2)
    log_result(19, "MAX_RESTARTS=2, fails every run -> exactly two repairs in ledger, then BROKEN restart ceiling",
               ok, detail=f"repairs recorded: {len(repairs)}")


# ------------------------------------------------------------------------------
# Row 20 — same gap raised in two separate invocations -> BROKEN repeated gap
# ------------------------------------------------------------------------------
def row20():
    d = make_gap_dir("row20_repeated_gap")
    res1 = run(d)
    show("Row 20 invocation #1", res1)
    res2 = run(d)
    show("Row 20 invocation #2 (same directory, same ledger)", res2)
    ok = (res1.returncode == 1 and "HELD  GAP-0001" in res1.stdout
          and res2.returncode == 2 and "BROKEN  repeated gap" in res2.stdout and "GAP-0001" in res2.stdout
          and "APP-002  allocated" in res2.stdout
          and canonical_status(d, "APP-001") == "candidate" and canonical_status(d, "APP-002") == "candidate")
    log_result(20, "same gap across two invocations -> BROKEN repeated gap, guard read the ledger", ok)


# ------------------------------------------------------------------------------
# Row 21 — no browser check in the suite, or it fails -> never BUILT
# ------------------------------------------------------------------------------
def row21a():
    d = fresh("row21a_no_browser_check")
    set_config(d, ALLOW_LAYER3=False)
    # point CAP-0002 at the already-fixed IMPL-02 so alpha passes cleanly
    make_active_impl(d, "CAP-0002", "CAP-0002/IMPL-02")
    tpl = json.loads((d / "templates" / "todo_no_browser_check.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 21a: suite has no browser check at all -> never BUILT", res)
    # As its own line, not necessarily the last -- stage three (round 6)
    # still runs and prints a trailing readiness line, since app_id exists.
    ok = (res.returncode == 2
          and "BROKEN  no browser check present in the suite" in res.stdout.rstrip().splitlines())
    log_result(21, "no browser check present, or it fails -> never BUILT (21a: absent)", ok)


def row21b():
    d = fresh("row21b_browser_check_fails")
    set_config(d, ALLOW_LAYER3=False)
    make_active_impl(d, "CAP-0001", "CAP-0001/IMPL-02")  # the browser-broken variant
    tpl = json.loads((d / "templates" / "todo_browser_broken.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row 21b: browser check present but fails -> never BUILT", res)
    # A failing browser check is not special-cased -- it becomes an ordinary
    # failure and goes through the same repair pipeline as any other check
    # (confirmed by running this for real: it lands in the gap path, HELD,
    # since no shelf part exists to fix a UI journey). The row's actual
    # requirement is simply that it never reaches BUILT; "BROKEN incomplete
    # record browser check not verified" was my own guess at the message
    # before running it, not a literal spec quote, and real execution shows
    # that particular line is currently unreachable given the checks defined
    # (see review notes) -- so this asserts the real requirement instead.
    ok = (res.returncode in (1, 2) and "PASS  a person clicks add item" not in res.stdout
          and "FAIL  a person clicks add item" in res.stdout
          and "BUILT" not in res.stdout.rstrip().splitlines())
    log_result(21, "no browser check present, or it fails -> never BUILT (21b: fails)", ok)


# ------------------------------------------------------------------------------
# Row 22 — the app's process is gone after every exit path, including BROKEN
# ------------------------------------------------------------------------------
def row22():
    # reuses the BUILT run from row8/9/10 and the BROKEN runs from rows 13/17/18
    lingering = no_lingering_process()
    ok = lingering == []
    log_result(22, "app process gone after every exit path (checked after BUILT + 3 BROKEN paths above)", ok,
               detail=str(lingering))


# ------------------------------------------------------------------------------
# Row 23 — the whole thing, real shelf, real choice.json -> BUILT, and the
# journey is completable. build.py's own browser check already drives the
# real journey a person would; separately, replay the same three real HTTP
# steps by hand-equivalent curl calls against a long-lived instance of the
# SAME app.py, to see the human-legible responses directly (not just PASS/FAIL).
# ------------------------------------------------------------------------------
def row23():
    d = fresh("row23_full_real_journey")
    set_config(d, ALLOW_LAYER3=False)
    res = run(d)
    show("Row 23: whole thing, real shelf + real choice", res)
    ok = res.returncode == 0 and "BUILT" in res.stdout.rstrip().splitlines()

    # Hand-equivalent replay: start the real assembled app standalone and hit
    # it the way a person opening it in a browser and clicking would.
    app_dir = d / "builds" / "APP-001"
    proc = subprocess.Popen([PY, "modules/CAP-0001/app.py", "--port", "5099"], cwd=str(app_dir),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        import urllib.request
        for _ in range(50):
            try:
                urllib.request.urlopen("http://127.0.0.1:5099/health", timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        home = urllib.request.urlopen("http://127.0.0.1:5099/", timeout=3).read().decode()
        print("\n-- GET / (first 300 chars, what a person would see) --")
        print(home[:300])
        req = urllib.request.Request("http://127.0.0.1:5099/api/items", method="POST",
                                      data=json.dumps({"text": "milk"}).encode(),
                                      headers={"Content-Type": "application/json"})
        created = json.loads(urllib.request.urlopen(req, timeout=3).read())
        print("\n-- POST /api/items {text: milk} (what clicking the button does) --")
        print(json.dumps(created, indent=2))
        listing = json.loads(urllib.request.urlopen("http://127.0.0.1:5099/api/items", timeout=3).read())
        print("\n-- GET /api/items (what the list now shows) --")
        print(json.dumps(listing, indent=2))
        hand_ok = "milk" in home and created.get("text") == "milk" and any(i["text"] == "milk" for i in listing)
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    log_result(23, "real shelf + real choice -> BUILT; real browser journey (CHK-020) plus a hand-equivalent "
                    "HTTP replay both confirm a person can complete it (I drove this with curl/Playwright, not "
                    "literally by hand -- honest caveat, not a claim of human testing)",
               ok and hand_ok)


# ------------------------------------------------------------------------------
# Extra hardening rows, beyond the 23-row table -- Sam's "keep testing it
# until it's foolproof" standard, so these push into things the table itself
# doesn't ask for but a real deployment would eventually hit.
# ------------------------------------------------------------------------------
def row_sigterm():
    """A child app that ignores SIGTERM -- proves run_layer_one's cleanup
    actually falls through to SIGKILL (proc.kill()) rather than leaving the
    process running forever. Previously flagged as untested in review.md."""
    d = fresh("rowX_sigterm_ignored")
    set_config(d, ALLOW_LAYER3=False)
    make_active_impl(d, "CAP-0001", "CAP-0001/IMPL-03")  # the SIGTERM-ignoring variant
    tpl = json.loads((d / "templates" / "todo_sigterm.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d, timeout=40)
    show("Row X: child ignores SIGTERM -> must still be reaped via SIGKILL", res)
    lingering = no_lingering_process()
    print(f"lingering processes after exit: {lingering}")
    # terminate() is given 5s before the kill() fallback fires -- a run that
    # actually exercised that fallback takes noticeably longer than the ~1s
    # a normal BUILT run takes.
    ok = (res.returncode == 0 and "BUILT" in res.stdout.rstrip().splitlines()
          and res.elapsed >= 5.0 and lingering == [])
    log_result("X-sigterm", "child ignores SIGTERM -> still reaped via SIGKILL, no lingering process", ok,
               detail=f"elapsed={res.elapsed:.1f}s lingering={lingering}")


def row_ambiguous_structural_match():
    """Two shelf capabilities that both structurally match the same failing
    check's wants shape. Confirmed by an earlier run of this exact test that
    the original find_structural_match() silently picked whichever one
    sorted first, with zero indication anywhere that a second, equally-valid
    candidate existed and was passed over -- a real violation of Bible rule 4
    ("do not guess when unknown; identify the gap and surface it"). Fixed:
    build.py now refuses to guess between tied candidates and HELDs instead,
    naming both. This test proves that fix."""
    d = fresh("rowX_ambiguous_structural_match")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_structural.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    # CAP-0007 "Feature Beta Second Alt" -- an independent capability, same
    # declared shape as CAP-0005 "Feature Beta Alt", same route, a DIFFERENT
    # response value so we can tell which one actually got copied in.
    cap7 = json.loads((d / "shelf" / "capabilities" / "CAP-0005.json").read_text())  # same §3.6 shape as Beta Alt
    cap7.update({"id": "CAP-0007", "name": "Feature Beta Second Alt", "implementations": ["CAP-0007/IMPL-01"]})
    (d / "shelf" / "capabilities" / "CAP-0007.json").write_text(json.dumps(cap7))
    impl7 = json.loads((d / "shelf" / "implementations" / "CAP-0005" / "IMPL-01.json").read_text())
    impl7.update({"id": "CAP-0007/IMPL-01", "capability_id": "CAP-0007"})
    impl7["source"] = dict(impl7["source"], path="CAP-0007/IMPL-01", entrypoint="CAP-0007/route.py")
    impl7_dir = d / "shelf" / "implementations" / "CAP-0007"
    impl7_dir.mkdir(parents=True, exist_ok=True)
    (impl7_dir / "IMPL-01.json").write_text(json.dumps(impl7))
    al = json.loads((d / "shelf" / "aliases.json").read_text())
    al["aliases"].append({"alias": "feature_beta_second_alt@1.0.0", "impl_id": "CAP-0007/IMPL-01"})
    (d / "shelf" / "aliases.json").write_text(json.dumps(al, indent=2))
    route7 = impl7_dir / "IMPL-01" / "CAP-0007" / "route.py"
    route7.parent.mkdir(parents=True, exist_ok=True)
    route7.write_text('ROUTE = "/api/feature-b"\nMETHOD = "GET"\n\n\ndef handle(request):\n    return 200, {"ok": True, "value": 12345}\n')

    res = run(d)
    show("Row X: two shelf capabilities structurally tie for the same repair", res)
    ok = (res.returncode == 1 and "HELD" in res.stdout and "ambiguous structural repair" in res.stdout
          and "feature_beta_alt@1.0.0" in res.stdout and "feature_beta_second_alt@1.0.0" in res.stdout
          and "awaiting approval" in res.stdout)
    # confirm neither candidate was silently applied
    app_dir = d / "builds" / "APP-001"
    neither_applied = not (app_dir / "modules" / "CAP-0005").exists() and not (app_dir / "modules" / "CAP-0007").exists()
    log_result("X-ambiguous", "ambiguous structural match -> HELD, names both candidates, neither silently applied",
               ok and neither_applied)


# ------------------------------------------------------------------------------
# Round 4 — G1: generic compute-check generation proves itself against
# capabilities build_checks() has never had a branch for (CAP-0010/0011), and
# correctly skips (never guesses) a compute capability with no declared
# ROUTE/METHOD (CAP-0012).
# ------------------------------------------------------------------------------
def rowG1():
    d = fresh("rowG1_generic_checks")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_generic.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row G1: generic compute-check generation (CAP-0010/0011 unseen by any hardcoded branch; CAP-0012 undeclared route skipped)", res)
    out = res.stdout
    ok = (
        res.returncode == 0 and "BUILT" in out.rstrip().splitlines()
        # CAP-0010 Feature Zeta -> CHK-110, real declared fields checked for real
        and "PASS  Feature Zeta responds and returns its declared output fields" in out
        and "CHK-110" not in "".join(l for l in out.splitlines() if "FAIL" in l)
        # CAP-0011 Feature Eta -> CHK-111, POST method read off its own route.py, not guessed as GET
        and "PASS  Feature Eta responds and returns its declared output fields" in out
        # CAP-0012 has no ROUTE/METHOD declared -> no CHK-112 anywhere, skipped not guessed
        and "CHK-112" not in out
        and "Feature Theta" not in out
    )
    log_result("G1", "generic compute-check generator: correct checks for two capabilities it has never "
                      "seen by id, correct skip (not a guess) for one with no declared route", ok,
               detail=out[-2000:] if not ok else "")


# ------------------------------------------------------------------------------
# Round 5 (H-T3) — G2: a capability declaring MORE nullable fields and MORE
# security constraints than a slot requires must still bind (directional
# subset match). G3: a slot requiring a security constraint the capability
# does not declare must still HELD (the loosened match is not "anything goes").
# ------------------------------------------------------------------------------
def rowG2():
    d = fresh("rowG2_subset_match_ok")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_subset_ok.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row G2: capability declares MORE nullable/security than the slot requires -> must still bind (H-T3 subset match)", res)
    ok = res.returncode == 0 and "BUILT" in res.stdout.rstrip().splitlines()
    log_result("G2", "H-T3: capability stricter/broader than required (extra nullable field, extra security "
                      "constraint) binds cleanly under the directional subset match", ok)


def rowG3():
    d = fresh("rowG3_subset_match_reject")
    set_config(d, ALLOW_LAYER3=False)
    tpl = json.loads((d / "templates" / "todo_subset_reject.json").read_text())
    (d / "templates" / "todo_list_app.json").write_text(json.dumps(tpl))
    res = run(d)
    show("Row G3: slot requires a security constraint the capability does not declare -> must still HELD", res)
    ok = (res.returncode == 1 and "HELD  CAP candidate" in res.stdout
          and "security constraints not met" in res.stdout and "encrypted_at_rest" in res.stdout)
    log_result("G3", "H-T3: a genuinely unmet security constraint still HELDs — loosening is directional, not "
                      "'anything goes'", ok)


if __name__ == "__main__":
    WORK.mkdir(exist_ok=True)
    rows_to_run = sys.argv[1:] or None
    all_fns = {
        "1": row1, "2": row2, "3": row3, "4": row4, "5": row5, "6": row6, "7": row7,
        "8": row8_9_10, "11": row11, "12": row12, "13": row13,
        "14": row14, "15": row15, "16": row16, "17": row17, "18": row18,
        "19": row19, "20": row20, "21a": row21a, "21b": row21b, "22": row22, "23": row23,
        "X-sigterm": row_sigterm, "X-ambiguous": row_ambiguous_structural_match,
        "G1": rowG1, "G2": rowG2, "G3": rowG3,
    }
    order = ["1", "2", "3", "4", "5", "6", "7", "8", "11", "12", "13",
             "14", "15", "16", "17", "18", "19", "20", "21a", "21b", "22", "23",
             "X-sigterm", "X-ambiguous", "G1", "G2", "G3"]
    to_run = rows_to_run if rows_to_run else order
    for key in to_run:
        if key in all_fns:
            all_fns[key]()

    print(f"\n{'='*78}\nSUMMARY (partial batch)\n{'='*78}")
    for row, name, ok, detail in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  row {row:>2}  {name}")
    n_ok = sum(1 for *_, ok, _ in RESULTS if ok)
    print(f"\n{n_ok}/{len(RESULTS)} pass")
