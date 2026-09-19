#!/usr/bin/env python3
"""
watch.py -- the audit. The last gate before BUILT.

Everything else in the chain is trying to make the app work. This is trying to
catch it having only appeared to.

It never repairs, never writes to the shelf, never calls a model, never touches
the app. It opens the run's record read-only and answers one question: did this
run actually do what it claims. A script that could fix what it audits would
have a reason to go easy on it.

Twenty-two checks in three groups. Any FAIL means the chain must not report
BUILT. Records missing or unreadable is exit 2 -- it claims nothing, the same
way a script that cannot start claims no checks.

Standard: god mode, ACTIVE/active_standards/BUILD_CHAIN_STANDARD.md, the
`watch.py` section, and the Script Standard throughout.

Usage:  watch.py                 audit the latest run
        watch.py RUN-0007        audit that run
        watch.py --runs ./runs   look for runs there instead
"""

# =====================================================================
# CONFIGURATION BLOCK -- one comment per setting, above all logic.
# Nothing configurable lives anywhere else in this file.
# =====================================================================

RUNS_DIR = "./runs"
# Where run directories live. If altered: audits runs from there instead.
# Must match run_record.RUNS_DIR or this audits nothing and says so.

LEVEL1_LEVEL = 1
# Which check level counts as a level-1 journey -- a real person doing a real
# thing. If altered: a different level is treated as the one that proves a
# person can use the app. Raising this makes BUILT harder to reach, never
# easier.

MINIMUM_CANDIDATES = 2
# How many candidates layer three must generate for a gap before the winner is
# trustworthy. If altered: fewer or more are demanded. One candidate is one
# model's first guess with nothing to compare it against, which is why the
# floor is two.

UNREADABLE_RECORD_EXIT = 2
# What to exit with when the record is missing, unreadable or incomplete.
# 2 = claims nothing; the run is simply not audited, and therefore not BUILT.
# 1 = treats it as a failed audit instead.
# Leave at 2. A record that cannot be read has not told you the run was bad,
# only that you cannot tell.

VALID_ORIGINS = ("harvested", "written")
# The only two origins a part may have. If altered: other values are accepted
# as valid origins. Anything outside this list fails W-22 rather than being
# assumed to be one of them.

# --- Individual checks. Each one off means that thing stops being audited. ---
# A silently narrowed audit is worse than no audit, so every switch here is
# printed in the output when it is off.

CHECKS_ENABLED = {
    "W-01": True,  # off = a run may pass on a database left by the last run
    "W-02": True,  # off = a run need not have started and stopped its own process
    "W-03": True,  # off = a run may pass against substituted datastores
    "W-04": True,  # off = mocks and fakes stop being caught
    "W-05": True,  # off = a run may reach BUILT with no level-1 journey at all
    "W-06": True,  # off = a SKIP on the level-1 journey stops counting against it
    "W-07": True,  # off = a page with no scripts and no styling counts as working
    "W-08": True,  # off = a check may be counted without a verdict against it
    "W-09": True,  # off = the output contract stops being enforced
    "W-10": True,  # off = a clean run stops being reported as a clean run
    "W-11": True,  # off = layer two may apply something that is not on the shelf
    "W-12": True,  # off = a repair may resume mid-run instead of restarting
    "W-13": True,  # off = a model may be called before the gap record exists
    "W-14": True,  # off = an incomplete gap record stops being caught
    "W-15": True,  # off = the model may be handed more than the gap record
    "W-16": True,  # off = one candidate is enough
    "W-17": True,  # off = a candidate may be kept on a model's word alone
    "W-18": True,  # off = a candidate may change more than the part
    "W-19": True,  # off = a new part may be shelved without approval
    "W-20": True,  # off = the same gap may be raised over and over
    "W-21": True,  # off = a regression stops being caught
    "W-22": True,  # off = a part's origin need not be recorded
}

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import sys
import json
from pathlib import Path

GAP_RECORD_REQUIRED = ("gap", "run", "check", "level", "message",
                       "missing", "proves_it")
REPAIR_RECORD_REQUIRED = ("run", "check", "part", "layer", "restarted_as")

RESULTS = []


def report(wid, state, claim, detail=""):
    RESULTS.append((wid, state, claim, detail))
    print(f"{state:<5} {wid}  {claim}")
    if detail:
        print(f"            {detail}")


def check(wid, claim, fn):
    """
    Run one check. A check that is switched off is reported SKIP with the
    reason, never quietly omitted.

    An exception inside a check is a FAIL, not a crash: the audit's job is to
    finish and report, and a check that cannot answer has not cleared the run.
    """
    if not CHECKS_ENABLED.get(wid, True):
        report(wid, "SKIP", claim, "switched off in the config block")
        return
    try:
        state, detail = fn()
    except Exception as e:
        report(wid, "FAIL", claim,
               f"the audit could not establish this: {type(e).__name__}: {str(e)[:80]}")
        return
    report(wid, state, claim, detail)


def cannot_audit(why):
    print(f"\nCANNOT AUDIT: {why}")
    print("0 checks claimed -- NOT AUDITED, and therefore not BUILT")
    sys.exit(UNREADABLE_RECORD_EXIT)


# ---------------------------------------------------------------------
# Group one -- did the run really run
# ---------------------------------------------------------------------

def group_one(r):
    env = r.get("environment") or {}

    def w01():
        v = env.get("working_directory_rebuilt")
        if v is True:
            return "PASS", "the working directory was deleted and rebuilt this run"
        if v is False:
            return "FAIL", ("the run reused an existing working directory -- a pass "
                            "may have been read off the last run")
        return "FAIL", "the run did not record whether it rebuilt its working directory"

    def w02():
        started, stopped = env.get("process_started"), env.get("process_stopped")
        port = env.get("port")
        if started is True and stopped is True:
            return "PASS", f"started and shut down its own process on port {port}"
        if started is not True:
            return "FAIL", "the run did not start its own process"
        return "FAIL", "the run started a process and did not record shutting it down"

    def w03():
        stores = env.get("datastores") or []
        if not stores:
            return "FAIL", "the run named no datastores, so none were proved real"
        fake = [s["name"] for s in stores if not s.get("real")]
        if fake:
            return "FAIL", f"not proved real: {', '.join(fake)}"
        return "PASS", f"real and reachable: {', '.join(s['name'] for s in stores)}"

    def w04():
        mocks = env.get("mocks_declared") or []
        if mocks:
            return "FAIL", f"the run declared {len(mocks)} substitution(s): {mocks[0]}"
        return "PASS", "the run declared no mocks, simulations or fake providers"

    check("W-01", "the working directory was rebuilt fresh", w01)
    check("W-02", "the app ran as its own process and was shut down", w02)
    check("W-03", "the datastores were real", w03)
    check("W-04", "nothing was mocked, simulated or faked", w04)


# ---------------------------------------------------------------------
# Group two -- was it actually proved
# ---------------------------------------------------------------------

def group_two(r):
    checks = r.get("checks") or []
    l1 = r.get("level1") or {}
    level1_checks = [c for c in checks if c.get("level") == LEVEL1_LEVEL]

    def w05():
        if not level1_checks:
            return "FAIL", ("no level-1 check ran, so nothing here proves a person "
                            "can use the app")
        if l1.get("ran") is not True:
            return "FAIL", "a level-1 check is listed but the run did not record it running"
        driver = l1.get("driver")
        if not driver:
            return "FAIL", "the level-1 journey did not record what drove it"
        return "PASS", f"a level-1 journey ran in {driver} at {l1.get('path')}"

    def w06():
        states = [c.get("state") for c in level1_checks]
        if not states:
            return "FAIL", "there is no level-1 verdict to read"
        if "FAIL" in states:
            return "FAIL", "the level-1 journey failed"
        if all(s == "SKIP" for s in states):
            return "FAIL", ("every level-1 check was skipped -- a SKIP is not a pass "
                            "and this run is UNPROVEN")
        if l1.get("passed") is not True:
            return "FAIL", "the run did not record the level-1 journey passing"
        return "PASS", "the level-1 journey passed"

    def w07():
        n = l1.get("javascript_errors")
        if n is None:
            return "FAIL", "the run did not record whether the page threw javascript errors"
        if n:
            return "FAIL", f"the page a person lands on threw {n} javascript error(s)"
        return "PASS", "the page a person lands on threw none"

    def w08():
        if not checks:
            return "FAIL", "the run claims no checks at all"
        blank = [c.get("id") for c in checks
                 if c.get("state") not in ("PASS", "FAIL", "SKIP")]
        if blank:
            return "FAIL", f"{len(blank)} check(s) counted with no verdict: {blank[0]}"
        unclaimed = [c.get("id") for c in checks if not (c.get("claim") or "").strip()]
        if unclaimed:
            return "FAIL", f"{len(unclaimed)} check(s) with no claim against them"
        return "PASS", f"all {len(checks)} checks carry a verdict and a claim"

    def w09():
        verdict, code = r.get("verdict"), r.get("exit_code")
        if verdict is None or code is None:
            return "FAIL", "the run recorded no final verdict or no exit code"
        failed = sum(1 for c in checks if c.get("state") == "FAIL")
        if failed and code == 0:
            return "FAIL", f"{failed} check(s) failed but the run exited 0"
        if verdict == "PASS" and failed:
            return "FAIL", f"the run reported PASS with {failed} failing check(s)"
        if verdict != "PASS" and code == 0:
            return "FAIL", f"the run reported {verdict} and still exited 0"
        return "PASS", f"verdict {verdict}, exit {code}, {failed} failing check(s)"

    check("W-05", "a level-1 journey ran in a real browser", w05)
    check("W-06", "that journey passed, and a SKIP was not counted as a pass", w06)
    check("W-07", "the landing page threw no javascript errors", w07)
    check("W-08", "every claimed check has a verdict against it", w08)
    check("W-09", "the verdict matches what the checks actually say", w09)


# ---------------------------------------------------------------------
# Group three -- did the loop behave
# ---------------------------------------------------------------------

def group_three(r, previous):
    repairs = r.get("layer2") or []
    gaps = r.get("layer3") or []
    parts = r.get("parts") or []
    entered_l3 = bool(gaps)

    def skip_l3(detail="layer three was not entered"):
        return "SKIP", detail

    def w10():
        if not repairs and not gaps:
            return "PASS", "layer one went green with no repair and no gap -- nothing needed building"
        bits = []
        if repairs:
            bits.append(f"{len(repairs)} repair(s) from the shelf")
        if gaps:
            bits.append(f"{len(gaps)} gap(s) sent to a model")
        return "PASS", "; ".join(bits)

    def w11():
        if not repairs:
            return "SKIP", "no repair was applied"
        unnumbered = [x for x in repairs if not (x.get("part") or "").strip()]
        if unnumbered:
            return "FAIL", f"{len(unnumbered)} repair(s) applied with no part named"
        missing = [x for x in repairs
                   if any(f not in x or x[f] in (None, "") for f in REPAIR_RECORD_REQUIRED)]
        if missing:
            return "FAIL", f"{len(missing)} repair record(s) missing a required field"
        return "PASS", f"all {len(repairs)} repair(s) named a numbered shelf part"

    def w12():
        if not repairs:
            return "SKIP", "no repair was applied"
        resumed = [x for x in repairs if not (x.get("restarted_as") or "").strip()]
        if resumed:
            return "FAIL", (f"{len(resumed)} repair(s) did not restart the chain as a "
                            f"new run -- a repair never resumes")
        same = [x for x in repairs if x.get("restarted_as") == r.get("run")]
        if same:
            return "FAIL", "a repair restarted as the run it was already in"
        return "PASS", f"every repair restarted the chain as a new run number"

    def w13():
        if not entered_l3:
            return skip_l3()
        late = [g["gap"] for g in gaps if g.get("model_called_after_record") is not True]
        if late:
            return "FAIL", (f"the model was called before the gap record existed for "
                            f"{', '.join(late)}")
        return "PASS", f"the gap record was written first for all {len(gaps)} gap(s)"

    def w14():
        if not entered_l3:
            return skip_l3()
        for g in gaps:
            empty = [f for f in GAP_RECORD_REQUIRED
                     if f not in g or g[f] in (None, "", [])]
            if empty:
                return "FAIL", (f"{g.get('gap', 'a gap record')} is missing: "
                                f"{', '.join(empty)}")
        return "PASS", f"all {len(gaps)} gap record(s) have every field filled"

    def w15():
        if not entered_l3:
            return skip_l3()
        for g in gaps:
            sent = g.get("prompt_contents")
            if sent is None:
                return "FAIL", f"{g.get('gap')} did not record what the model was sent"
            if sent != ["gap_record"]:
                return "FAIL", (f"{g.get('gap')} handed the model more than the gap "
                                f"record: {sent}")
        return "PASS", "each model was handed the gap record and nothing else"

    def w16():
        if not entered_l3:
            return skip_l3()
        thin = [(g.get("gap"), g.get("candidates_generated")) for g in gaps
                if not isinstance(g.get("candidates_generated"), int)
                or g["candidates_generated"] < MINIMUM_CANDIDATES]
        if thin:
            return "FAIL", (f"{thin[0][0]} generated {thin[0][1]} candidate(s), "
                            f"minimum is {MINIMUM_CANDIDATES}")
        return "PASS", f"every gap generated at least {MINIMUM_CANDIDATES} candidates"

    def w17():
        if not entered_l3:
            return skip_l3()
        untested = [g.get("gap") for g in gaps
                    if g.get("winner_driven_through_chain") is not True]
        if untested:
            return "FAIL", (f"the winning candidate for {', '.join(untested)} was kept "
                            f"without being driven through the full chain")
        return "PASS", "every winning candidate was driven through the full chain"

    def w18():
        if not entered_l3:
            return skip_l3()
        wide = [g.get("gap") for g in gaps
                if g.get("winner_touched_only_part") is not True]
        if wide:
            return "FAIL", f"the winner for {', '.join(wide)} changed more than the part"
        return "PASS", "every winner touched only the part"

    def w19():
        if not entered_l3:
            return skip_l3()
        auto = [g.get("gap") for g in gaps if g.get("held_for_approval") is not True]
        if auto:
            return "FAIL", (f"{', '.join(auto)} was not held for approval -- new part "
                            f"numbers are permanent and wait")
        return "PASS", "every new part was held for approval"

    def w20():
        seen = [g.get("gap") for g in gaps]
        for p in previous:
            seen += [g.get("gap") for g in (p.get("layer3") or [])]
        dupes = {g for g in seen if g and seen.count(g) > 1}
        if dupes:
            return "FAIL", (f"gap {sorted(dupes)[0]} was raised more than once -- the "
                            f"part was built but never shelved, or its pattern was "
                            f"never added to layer two's map")
        if not seen:
            return "SKIP", "no gap was raised"
        return "PASS", f"no gap number was raised twice across {len(previous) + 1} run(s)"

    def w21():
        if not previous:
            return "SKIP", "no earlier run to compare against"
        prior = previous[-1]
        was_pass = {c.get("claim") for c in (prior.get("checks") or [])
                    if c.get("state") == "PASS"}
        now_fail = {c.get("claim") for c in (r.get("checks") or [])
                    if c.get("state") == "FAIL"}
        broke = was_pass & now_fail
        if broke:
            return "FAIL", (f"{len(broke)} check(s) that passed in {prior.get('run')} "
                            f"now fail, first: {sorted(broke)[0][:60]}")
        return "PASS", f"nothing that passed in {prior.get('run')} fails now"

    def w22():
        if not parts:
            return "FAIL", "the run recorded no parts at all"
        bad = [p for p in parts if p.get("origin") not in VALID_ORIGINS]
        if bad:
            return "FAIL", (f"{len(bad)} part(s) with no valid origin, first "
                            f"{bad[0].get('id')}: {bad[0].get('origin')!r}")
        counts = {o: sum(1 for p in parts if p["origin"] == o) for o in VALID_ORIGINS}
        return "PASS", ", ".join(f"{n} {o}" for o, n in counts.items() if n)

    check("W-10", "what this run actually needed", w10)
    check("W-11", "every repair came off the shelf", w11)
    check("W-12", "every repair restarted the chain, never resumed", w12)
    check("W-13", "the gap record was written before the model was called", w13)
    check("W-14", "every gap record is complete", w14)
    check("W-15", "the model got the gap record and nothing else", w15)
    check("W-16", "several candidates were generated, not one", w16)
    check("W-17", "the winner was proved, not trusted", w17)
    check("W-18", "the winner touched only the part", w18)
    check("W-19", "the new part was held for approval", w19)
    check("W-20", "no gap was raised twice", w20)
    check("W-21", "nothing that passed before fails now", w21)
    check("W-22", "every part's origin is recorded", w22)


# ---------------------------------------------------------------------

def load_run(d):
    path = Path(d) / "run.json"
    if not path.is_file():
        cannot_audit(f"no run.json in {d}")
    try:
        r = json.loads(path.read_text())
    except Exception as e:
        cannot_audit(f"{path} is unreadable: {type(e).__name__}: {str(e)[:70]}")
    if not isinstance(r, dict) or not r.get("run"):
        cannot_audit(f"{path} is not a run record -- it has no run number")
    return r


def main():
    argv = sys.argv[1:]
    runs_dir = Path(RUNS_DIR)
    wanted = None
    i = 0
    while i < len(argv):
        if argv[i] == "--runs" and i + 1 < len(argv):
            runs_dir = Path(argv[i + 1]); i += 2
        else:
            wanted = argv[i]; i += 1

    runs_dir = runs_dir.resolve()
    if not runs_dir.is_dir():
        cannot_audit(f"no runs directory at {runs_dir}")

    all_runs = sorted(d for d in runs_dir.iterdir()
                      if d.is_dir() and (d / "run.json").is_file())
    if not all_runs:
        cannot_audit(f"no run records under {runs_dir}")

    target = runs_dir / wanted if wanted else all_runs[-1]
    if not target.is_dir():
        cannot_audit(f"no run directory {target}")

    r = load_run(target)
    previous = []
    for d in all_runs:
        if d == target:
            break
        try:
            previous.append(json.loads((d / "run.json").read_text()))
        except Exception:
            pass  # an unreadable earlier run is not this run's fault

    print(f"auditing {r['run']} -- {r.get('script')} -- {r.get('started')}")
    off = [w for w, on in CHECKS_ENABLED.items() if not on]
    if off:
        print(f"NARROWED: {len(off)} check(s) switched off -- {', '.join(off)}")
    print()

    group_one(r)
    group_two(r)
    group_three(r, previous)

    passed = sum(1 for _, s, _, _ in RESULTS if s == "PASS")
    failed = sum(1 for _, s, _, _ in RESULTS if s == "FAIL")
    skipped = sum(1 for _, s, _, _ in RESULTS if s == "SKIP")
    total = len(RESULTS)

    print()
    if failed:
        names = ", ".join(w for w, s, _, _ in RESULTS if s == "FAIL")
        print(f"{passed}/{total} audit checks passed -- FAIL, {failed} failed "
              f"({names}). {r['run']} is not BUILT.")
        sys.exit(1)
    print(f"{passed}/{total} audit checks passed, {skipped} not applicable -- "
          f"PASS, {r['run']} did what it claims")
    sys.exit(0)


if __name__ == "__main__":
    main()
