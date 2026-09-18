#!/usr/bin/env python3
"""
chain.py -- the orchestrator. One command, and it runs to the end without
stopping to ask anything.

    python chain.py

It stops on exactly three things: BUILT, HELD, or BROKEN. It does not pause
between layers, does not wait for approval mid-run, and does not ask a question.
The only approval in the system is on new part numbers, and that happens after
the chain has stopped, not during it.

**A repair never resumes.** After any repair the chain restarts from the
beginning as a new numbered run, and every check runs again from scratch.
Resuming would mean the checks before the repair ran against a different system
than the ones after it.

Standard: god mode, BUILD_CHAIN_STANDARD.md `chain.py`; Script Standard 5.

Usage:  chain.py            run to a terminal state
        chain.py --dry      print what it would run and stop
"""

# =====================================================================
# CONFIGURATION BLOCK -- one comment per setting, above all logic.
# =====================================================================

TARGET = "./host.py"
# The thing being built and proved. If altered: the chain runs against that
# instead. This is not read directly -- it is what the layer-one suite drives --
# but a chain pointed at nothing is a chain proving nothing, so it is checked
# to exist before anything runs.

LEDGER_DIR = "./runs"
# Where run records are written, one directory per run. If altered: must match
# layer1_checks.py, layer3_gap.py and watch.py, or each looks somewhere else.

SHELF_DIR = "./shelf"
# The parts shelf layer two repairs from. If altered: parts come from there.

REPORTS_DIR = "./reports"
# Where the chain writes its own summary of each attempt. If altered: reports
# land there. These are what make a BROKEN verdict readable afterwards.

MAX_RESTARTS = 6
# How many times the chain may restart after a repair before it stops with
# BROKEN -- restart ceiling. If altered: the chain tries harder or gives up
# sooner. Raising this does not make a failing repair work; it just costs more
# runs to find that out.

ALLOW_LAYER_THREE = True
# True  = when the shelf has no part, the chain calls layer three and a model
#         is touched.
# False = the chain reports HELD at that point instead and no model is ever
#         called. Turn this off to run the whole chain at zero cost.

LAYER1 = "./layer1_checks.py"
LAYER2 = "./layer2_repair.py"
LAYER3 = "./layer3_gap.py"
WATCH = "./watch.py"
# The four scripts this calls. If altered: those are run instead. Each must
# obey its own exit codes, which is what this reads -- never their output.

STEP_TIMEOUT_SECONDS = 2400
# How long any single script may take. If altered: slower steps tolerated, or
# hung ones caught sooner. A timeout is BROKEN, never a pass.

STREAM_OUTPUT = True
# True  = each script's own lines appear as they happen, which is what makes a
#         long chain readable while it runs.
# False = only the chain's verdict is printed.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import sys
import json
import time
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent

L1_ALL_PASS, L1_FAILED, L1_COULD_NOT_START, L1_NO_LEVEL1 = 0, 1, 2, 3
L2_APPLIED, L2_NO_PART, L2_FAILED_TO_APPLY = 0, 1, 2
L3_BUILT, L3_CANNOT_BUILD, L3_REFUSED = 0, 1, 2

HISTORY = []   # (run, check, part) for the loop guard and the restart history


def run_script(path, args=()):
    p = (HERE / path).resolve()
    if not p.is_file():
        return None, f"no script at {p}"
    try:
        proc = subprocess.run(
            [sys.executable, str(p), *args], cwd=str(HERE),
            timeout=STEP_TIMEOUT_SECONDS,
            capture_output=not STREAM_OUTPUT, text=True)
        return proc.returncode, None
    except subprocess.TimeoutExpired:
        return None, f"{path} did not finish within {STEP_TIMEOUT_SECONDS}s"


def newest_run():
    root = (HERE / LEDGER_DIR).resolve()
    if not root.is_dir():
        return None
    runs = sorted(d for d in root.iterdir()
                  if d.is_dir() and (d / "run.json").is_file())
    return runs[-1] if runs else None


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return None


def finish(run, verdict, detail=""):
    """
    Script Standard 5 -- the last line is the verdict and only the verdict.
    Sam reads FAIL lines, UNPROVEN lines, and the last line.
    """
    reports = (HERE / REPORTS_DIR).resolve()
    reports.mkdir(parents=True, exist_ok=True)
    (reports / f"{run or 'chain'}.json").write_text(json.dumps({
        "run": run, "verdict": verdict, "detail": detail,
        "history": HISTORY,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }, indent=2))

    print()
    print(f"{run or 'chain'}   chain finished")
    print(f"{verdict}{('  ' + detail) if detail else ''}")
    sys.exit(0 if verdict == "BUILT" else 1)


def passing_claims(run_dir):
    r = read(Path(run_dir) / "run.json") or {}
    return {c.get("claim") for c in (r.get("checks") or [])
            if c.get("state") == "PASS"}


def failing_claims(run_dir):
    r = read(Path(run_dir) / "run.json") or {}
    return {c.get("claim") for c in (r.get("checks") or [])
            if c.get("state") == "FAIL"}


def main():
    dry = "--dry" in sys.argv[1:]

    target = (HERE / TARGET).resolve()
    if not target.exists():
        print(f"\nBROKEN  nothing to build at {target}")
        sys.exit(1)

    if dry:
        for name, p in (("layer one", LAYER1), ("layer two", LAYER2),
                        ("layer three", LAYER3), ("audit", WATCH)):
            here = (HERE / p).resolve()
            print(f"{'ok  ' if here.is_file() else 'MISSING'}  {name}: {here}")
        print(f"\nlayer three is {'allowed' if ALLOW_LAYER_THREE else 'OFF -- '
              'the chain will HELD instead of calling a model'}")
        sys.exit(0)

    restarts = 0
    last_pass_dir = None

    while True:
        # ---- layer one -------------------------------------------------
        code, err = run_script(LAYER1)
        if err:
            finish(None, "BROKEN", err)

        run_dir = newest_run()
        run = (read(Path(run_dir) / "run.json") or {}).get("run") if run_dir else None

        if code == L1_COULD_NOT_START:
            finish(run, "BROKEN", "layer one could not start the system -- "
                                  "0 checks claimed, nothing was proved")

        if code == L1_NO_LEVEL1:
            finish(run, "BROKEN", "no level-1 check ran, so nothing here "
                                  "proves a person can use the app")

        # ---- regression, before anything else is attempted -------------
        if last_pass_dir is not None:
            broke = passing_claims(last_pass_dir) & failing_claims(run_dir)
            if broke:
                finish(run, "BROKEN",
                       f"regression -- {len(broke)} check(s) that passed "
                       f"earlier now fail, first: {sorted(broke)[0][:60]}")

        if code == L1_ALL_PASS:
            last_pass_dir = run_dir
            # ---- the audit ---------------------------------------------
            acode, aerr = run_script(WATCH, [Path(run_dir).name])
            if aerr:
                finish(run, "BROKEN", aerr)
            if acode == 2:
                finish(run, "BROKEN", "the run could not be audited, and a run "
                                      "that cannot be audited is not BUILT")
            if acode != 0:
                finish(run, "BROKEN", "layer one went green but the audit "
                                      "refused the run")
            finish(run, "BUILT")

        # ---- layer two -------------------------------------------------
        failures = read(Path(run_dir) / "failures.json") or []
        if not failures:
            finish(run, "BROKEN", "layer one reported failures but wrote no "
                                  "failure record -- nothing can act on that")
        first = failures[0]

        code2, err2 = run_script(LAYER2, [Path(run_dir).name])
        if err2:
            finish(run, "BROKEN", err2)

        if code2 == L2_FAILED_TO_APPLY:
            # Layer two's exit 2 covers both "could not run at all" and
            # "matched a part and could not apply it". Its own output says
            # which; this must not claim one when it was the other.
            finish(run, "BROKEN", "layer two could not complete -- see the "
                                  "reason it printed above")

        if code2 == L2_APPLIED:
            repair = read(Path(run_dir) / "repair.json") or {}
            part = repair.get("part")

            # ---- loop guard -------------------------------------------
            if (first["check"], part) in [(h[1], h[2]) for h in HISTORY]:
                before = [h[0] for h in HISTORY
                          if h[1] == first["check"] and h[2] == part]
                finish(run, "BROKEN",
                       f"loop guard  {first['check']} still fails after "
                       f"{part} (applied {', '.join(before + [run])})")

            HISTORY.append((run, first["check"], part))

            restarts += 1
            if restarts > MAX_RESTARTS:
                lines = "; ".join(f"{r}: {c} <- {p}" for r, c, p in HISTORY)
                finish(run, "BROKEN",
                       f"restart ceiling  {restarts} restarts  [{lines}]")

            repair["restarted_as"] = "pending"
            (Path(run_dir) / "repair.json").write_text(json.dumps(repair, indent=2))
            print(f"\n{run}  repaired with {part} -- restarting as a new run\n")
            continue   # a repair never resumes

        # ---- layer three -----------------------------------------------
        if not ALLOW_LAYER_THREE:
            finish(run, "HELD", f"no shelf part for {first['check']}, and "
                                f"layer three is switched off")

        code3, err3 = run_script(LAYER3, [Path(run_dir).name])
        if err3:
            finish(run, "BROKEN", err3)

        if code3 == L3_REFUSED:
            finish(run, "HELD", "layer three could not run -- see the setting "
                                "it named above")
        if code3 == L3_CANNOT_BUILD:
            finish(run, "HELD", f"no candidate passed for {first['check']}")

        # A part was built and is held for approval. New part numbers are
        # permanent, so the chain stops here rather than shelving it itself.
        finish(run, "HELD", "a part was built and is held for your approval -- "
                            "approve it onto the shelf and run again")


if __name__ == "__main__":
    main()
