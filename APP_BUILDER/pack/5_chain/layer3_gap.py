#!/usr/bin/env python3
"""
layer3_gap.py -- build the missing part. The only place a model is touched, and
the last place the chain goes.

**The division of labour is the point of the whole design.** The script
diagnoses; the model builds. The model is never shown the failure and asked what
to do. It is handed a gap record and told to build exactly that.

Order, and it is not negotiable: classify the gap, write the numbered gap
record, and only then call the models. A model called before the record exists
is a model being asked to work out what is wrong, which is the thing this design
exists to avoid.

Several candidates are generated, never one, across more than one model or
framing. Every candidate is run through the full chain -- real build, real
process, real browser. Candidates that fail are discarded silently. The winner
is held for approval, never numbered onto the shelf automatically, because new
part numbers are permanent.

**Never decides that it should be called.** chain.py decides that. A model that
can invoke itself has no ceiling on scope or cost.

Standard: god mode, BUILD_CHAIN_STANDARD.md `layer3_gap.py` and CANDIDATE
GENERATION; Script Standard 1.1, 1.4, 4.

Usage:  layer3_gap.py <run-dir>     classify the failure and build the part
"""

# =====================================================================
# CONFIGURATION BLOCK -- one comment per setting, above all logic.
# =====================================================================

LAYER3_ENDPOINT = ""
# The model endpoint. Whatever is here receives a JSON body
# {"model": ..., "messages": [...]} with the credential as a bearer token.
# Nothing here is provider-specific.
# Empty means this script refuses to run and names this setting. It does not
# fall back to anything (Script Standard 1.4, 6).

LAYER3_MODEL = ""
# The model name sent in that body. Sam names this.
# Empty means this script refuses to run and names this setting.

LAYER3_CREDENTIAL = ""
# The credential sent as the Authorization bearer token. Pasted here, never a
# file, never argv, never printed, never in a repository (Script Standard 6).
# Empty means this script refuses to run and names this setting.

FRAMINGS = [
    # How the same gap record is put to a model. The value is variety of
    # approach, not quality of judgement -- a different framing catches what a
    # different person would have caught. Do not tune these toward agreement.
    "build the part this record describes, as plainly as it can be built",
    "build the part this record describes, assuming the simplest possible "
    "implementation that satisfies what proves it",
    "build the part this record describes, assuming the obvious approach has "
    "already been tried and did not work",
]

CANDIDATES_PER_FRAMING = 1
# How many candidates each framing produces. If altered: more attempts per
# framing. Total candidates = len(FRAMINGS) x this.

MINIMUM_CANDIDATES = 2
# The floor. Below this the script refuses to proceed rather than trust one
# model's first guess. Must match watch.py's MINIMUM_CANDIDATES or the audit
# will demand something this never produced.

REQUEST_TIMEOUT_SECONDS = 300
# How long a single model call may take. If altered: slower models tolerated,
# or hung ones caught sooner. A timeout discards that candidate only.

GAPS_DIR = "./gaps"
# Where numbered gap records are written. If altered: records land there.
# A gap record is permanent evidence -- it is what proves the part was
# specified before it was built.

GAP_ID_PREFIX = "GAP-"
GAP_ID_DIGITS = 4
# How gap numbers are formed. If altered: new gaps are named this way.
# Existing gaps keep the name they were written with.

RUNS_DIR = "./runs"
# Where run records live. Must match layer1_checks.py and watch.py.

CANDIDATE_JUDGE = "./layer1_checks.py"
# What decides whether a candidate is any good. The models are raw material;
# the judge is a script driving the real system. If altered: that script
# decides instead. It must exit 0 only on a real pass.

APP_SLUG = "challenge-platform"
# Which app on the shelf the built part belongs to. The running app loads a
# capability from shelf/<APP_SLUG>/<CAP-id>/source.py, and that is where a
# candidate must be placed to be judged at all. If altered: candidates are
# applied to that app instead.
# 2026-09-18: set for this app's chain run, was "challenge-platform" then
# "event-ticketing" before that.

PART_FILENAME = "source.py"
# The filename a candidate is written as when it is applied. If altered: the
# candidate lands under that name. Must match what the host loads.

REQUIRE_CAPABILITY_IN_FAILURE = True
# True  = a failure that names no capability stops layer three. There is
#         nowhere to put a part, and choosing a capability for it would be a
#         guess (Script Standard 1.4). Some failures are host defects, not
#         missing parts, and this is what tells them apart.
# False = layer three would have to pick somewhere. Do not turn this off.

SEND_ONLY_GAP_RECORD = True
# True  = the model is handed the gap record and nothing else. Not the
#         conversation, not the wider codebase, not "here is an error, fix it".
# False = more context may be attached. Turning this off is what turns a
#         specified build back into a model guessing at a problem, and watch.py
#         fails W-15 on any run where it was off.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import re
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def refuse(setting):
    """Script Standard 1.4 and 6 -- a missing setting stops the script and
    names it. No default, no fallback, no 'best effort'."""
    print(f"\nHELD  layer three cannot run  missing setting  {setting}")
    print("no model was called, and no part was built")
    sys.exit(2)


def die(code, why):
    print(f"\nLAYER THREE COULD NOT RUN: {why}")
    sys.exit(code)


def next_gap_id():
    root = (HERE / GAPS_DIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    highest = 0
    for p in root.glob(f"{GAP_ID_PREFIX}*.json"):
        tail = p.stem[len(GAP_ID_PREFIX):]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{GAP_ID_PREFIX}{highest + 1:0{GAP_ID_DIGITS}d}"


def previous_gaps():
    """Every gap already raised. A gap raised twice means the part was built
    but never shelved, or its pattern was never added to layer two's map."""
    root = (HERE / GAPS_DIR).resolve()
    if not root.is_dir():
        return []
    out = []
    for p in sorted(root.glob(f"{GAP_ID_PREFIX}*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            pass
    return out


def classify(failure):
    """
    Work out what class of behaviour is missing, from the failure's own
    message, its check number and its authority level.

    This is the diagnosis, and it is the script's job, not the model's. If it
    cannot be done specifically, that is a fault in the check -- a failure
    message too vague to specify a part is too vague to act on at all -- and
    this exits 2 saying so rather than handing the vagueness to a model.
    """
    msg = (failure.get("message") or "").strip()
    text = (failure.get("text") or "").strip()
    if not msg or not text:
        return None, "the failure record carries no message or no claim"
    if len(msg) < 12:
        return None, (f"the failure message is too short to specify a part: "
                      f"{msg!r} -- that is a fault in the check, not in the "
                      f"shelf")

    missing = (f"whatever makes this true: {text}")
    proves_it = (f"the same check, {failure.get('check')}, at level "
                 f"{failure.get('level')}, passes against the real system")
    return {"missing": missing, "proves_it": proves_it}, None


def write_gap_record(failure, classified):
    """
    The numbered gap record. Written BEFORE any model is called -- that order
    is the whole design, and watch.py W-13 checks it.

    Every field is required. If one cannot be filled the record is not written
    and this stops. An incomplete record is how invented work gets in.
    """
    gap_id = next_gap_id()
    rec = {
        "gap": gap_id,
        "run": failure.get("run"),
        "check": failure.get("check"),
        "level": failure.get("level"),
        "message": failure.get("message"),
        "missing": classified["missing"],
        "proves_it": classified["proves_it"],
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "model_called_after_record": False,
        "prompt_contents": None,
        "candidates_generated": 0,
        "candidates_passed": 0,
        "winner": None,
        "winner_driven_through_chain": False,
        "winner_touched_only_part": False,
        "held_for_approval": False,
    }
    empty = [k for k in ("gap", "run", "check", "level", "message",
                         "missing", "proves_it")
             if rec.get(k) in (None, "", [])]
    if empty:
        die(2, f"the gap record cannot be completed -- missing "
               f"{', '.join(empty)}")
    path = (HERE / GAPS_DIR).resolve() / f"{gap_id}.json"
    path.write_text(json.dumps(rec, indent=2))
    return rec, path


def call_model(gap_record, framing):
    """
    One model call. The model is handed the gap record and the framing, and
    nothing else.

    If the endpoint cannot be reached or refuses, this says so honestly and
    returns nothing. It never substitutes a fabricated response (Script
    Standard 1.1).
    """
    sendable = {k: gap_record[k] for k in
                ("gap", "check", "level", "message", "missing", "proves_it")}
    prompt = (f"{framing}\n\n"
              f"GAP RECORD:\n{json.dumps(sendable, indent=2)}\n\n"
              f"Return only the code for the part. No explanation.")
    body = json.dumps({
        "model": LAYER3_MODEL,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        LAYER3_ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {LAYER3_CREDENTIAL}"})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        print(f"      candidate discarded: endpoint refused, HTTP {e.code}")
    except Exception as e:
        print(f"      candidate discarded: {type(e).__name__}: {str(e)[:70]}")
    return None


def extract_code(response_text):
    """Take the code out of the model's reply. A reply with no code in it is
    not a candidate, and returns None rather than being written out as one."""
    t = response_text
    if "```" in t:
        blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", t, re.S)
        if blocks:
            t = max(blocks, key=len)
    t = t.strip()
    return t if t else None


def judge(candidate_code, cap_id):
    """
    The judge is a script driving the real system, never a model's opinion of
    its own work. Exit 0 and nothing else counts as passing.

    The candidate is placed into the app the running host actually loads, the
    judge is run against it for real, and the original is then put back
    whatever the outcome. Judging a candidate that was never applied would be
    judging the unchanged app and calling the result the candidate's.
    """
    judge_path = (HERE / CANDIDATE_JUDGE).resolve()
    if not judge_path.is_file():
        die(2, f"no judge at {judge_path} -- a candidate cannot be kept "
               f"without one")

    live = (HERE / "shelf" / APP_SLUG / cap_id / PART_FILENAME).resolve()
    if not live.parent.is_dir():
        die(2, f"no capability directory at {live.parent} -- a candidate "
               f"cannot be judged where the app cannot load it")

    original = live.read_bytes() if live.is_file() else None
    try:
        live.write_text(candidate_code)
        proc = subprocess.run([sys.executable, str(judge_path)],
                              cwd=str(HERE), capture_output=True, text=True)
        return proc.returncode == 0
    finally:
        # The app is put back exactly as it was, pass or fail. A candidate
        # that failed must not be left in the app it failed against.
        if original is None:
            if live.is_file():
                live.unlink()
        else:
            live.write_bytes(original)


def capability_in(failure):
    """The capability a part would belong to, read off the failure itself.
    Never inferred from anything else."""
    named = failure.get("capability")
    if named:
        return named
    for field in ("check", "text", "message"):
        m = re.search(r"CAP-\d{4,}", str(failure.get(field) or ""))
        if m:
            return m.group(0)
    return None


def main():
    argv = sys.argv[1:]
    if not argv:
        die(2, "no run directory given")

    # The settings are checked before anything else happens, so a run that
    # cannot reach a model says so without having written a gap number it
    # then abandons.
    if not LAYER3_ENDPOINT:
        refuse("LAYER3_ENDPOINT")
    if not LAYER3_MODEL:
        refuse("LAYER3_MODEL")
    if not LAYER3_CREDENTIAL:
        refuse("LAYER3_CREDENTIAL")

    total_candidates = len(FRAMINGS) * CANDIDATES_PER_FRAMING
    if total_candidates < MINIMUM_CANDIDATES:
        die(2, f"the config would generate {total_candidates} candidate(s), "
               f"below the floor of {MINIMUM_CANDIDATES}")

    run_dir = Path(argv[0])
    if not run_dir.is_dir():
        run_dir = (HERE / RUNS_DIR / run_dir.name).resolve()
    if not run_dir.is_dir():
        die(2, f"no run directory at {run_dir}")

    fpath = run_dir / "failures.json"
    if not fpath.is_file():
        die(2, f"no failures.json in {run_dir} -- layer three is only ever "
               f"called on a run that failed")
    failures = json.loads(fpath.read_text())
    if not failures:
        die(2, "no failure records to classify")
    failure = failures[0]

    print(f"FAILURE  {failure['check']}  level {failure['level']}  "
          f"{failure['text']}")
    print(f"         {failure['message']}")

    classified, why = classify(failure)
    if classified is None:
        print(f"\nBROKEN  the gap could not be classified: {why}")
        sys.exit(2)

    cap_id = capability_in(failure)
    if cap_id is None and REQUIRE_CAPABILITY_IN_FAILURE:
        print(f"\nBROKEN  this failure names no capability, so there is "
              f"nowhere on the shelf for a part to go")
        print(f"        that makes it a defect in the app or the host, not a "
              f"missing part -- layer three cannot fix it and will not guess")
        sys.exit(2)

    rec, path = write_gap_record(failure, classified)
    print(f"\nGAP      {rec['gap']}  written to {path}")
    print(f"MISSING  {rec['missing']}")
    print(f"PROVES   {rec['proves_it']}")

    # A gap raised twice is only a fault if a part was actually built for it
    # last time. If the previous attempt produced nothing -- the endpoint was
    # down, no candidate passed -- then retrying is the correct thing to do,
    # and refusing would leave the gap permanently unfixable.
    same = [g for g in previous_gaps()
            if g.get("check") == rec["check"] and g.get("gap") != rec["gap"]
            and g.get("held_for_approval")]
    if same:
        print(f"\nBROKEN  {rec['check']} already raised {same[0]['gap']}, and a "
              f"part was built for it -- that part was never numbered onto the "
              f"shelf, or its pattern was never added to layer two's map")
        sys.exit(2)

    # Only now is a model touched.
    rec["model_called_after_record"] = True
    rec["prompt_contents"] = ["gap_record"] if SEND_ONLY_GAP_RECORD else ["gap_record", "extra"]

    print(f"\nGENERATING  {total_candidates} candidate(s) across "
          f"{len(FRAMINGS)} framing(s)")
    winners = []
    generated = 0
    cand_root = (HERE / GAPS_DIR).resolve() / rec["gap"]
    cand_root.mkdir(parents=True, exist_ok=True)

    for fi, framing in enumerate(FRAMINGS, 1):
        for ci in range(CANDIDATES_PER_FRAMING):
            generated += 1
            out = call_model(rec, framing)
            if out is None:
                continue
            code = extract_code(out)
            if code is None:
                print("      candidate discarded: the reply contained no code")
                continue
            cdir = cand_root / f"candidate-{fi}-{ci + 1}"
            cdir.mkdir(parents=True, exist_ok=True)
            (cdir / "response.txt").write_text(out)
            (cdir / PART_FILENAME).write_text(code)
            if judge(code, cap_id):
                winners.append((cdir, fi))
            # A candidate that fails is discarded silently. Sam never sees it.

    rec["candidates_generated"] = generated
    rec["candidates_passed"] = len(winners)

    if not winners:
        rec["held_for_approval"] = False
        path.write_text(json.dumps(rec, indent=2))
        print(f"\nHELD  {rec['gap']}  {generated} candidate(s) tried, none "
              f"passed the real check")
        sys.exit(1)

    # More than one passing candidate: the one touching the least is preferred
    # (Script Standard 1.6).
    winners.sort(key=lambda w: len((w[0] / PART_FILENAME).read_text()))
    winner, framing_index = winners[0]

    rec["winner"] = str(winner.relative_to(HERE))
    rec["capability"] = cap_id
    rec["winner_driven_through_chain"] = True
    rec["winner_touched_only_part"] = True
    rec["held_for_approval"] = True
    path.write_text(json.dumps(rec, indent=2))

    print(f"\nHELD  {rec['gap']}  part built and held for approval")
    print(f"      {len(winners)}/{generated} candidate(s) passed, framing "
          f"{framing_index} won")
    print(f"      new part numbers are permanent, so this waits for Sam")
    sys.exit(0)


if __name__ == "__main__":
    main()
