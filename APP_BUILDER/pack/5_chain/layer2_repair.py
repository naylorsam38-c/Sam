#!/usr/bin/env python3
"""
layer2_repair.py -- repair from the shelf. No model. Still free.

Takes one failure record from layer one, matches its own message against the
failure-pattern map below, and applies the mapped part by number and version.

**It never invents a fix.** It only places parts that already exist on the
shelf. If the map has no entry it returns "no part" and the chain escalates to
layer three. A layer two that improvises is indistinguishable from a layer three
with no record of what it did.

**It never prints PASS for the failure it just repaired.** The proof of a repair
is the next run, not this one.

Standard: god mode, BUILD_CHAIN_STANDARD.md `layer2_repair.py`; Script Standard
1.4, 1.6, 3.

Usage:  layer2_repair.py <run-dir>            repair the first failure in it
        layer2_repair.py <run-dir> --check N  repair that check number
        layer2_repair.py --map                print the map and stop
"""

# =====================================================================
# CONFIGURATION BLOCK -- one comment per setting, above all logic.
# =====================================================================

SHELF_DIR = "./shelf"
# The parts shelf. If altered: parts are looked for there instead. A part named
# in the map below but absent from the shelf is exit 2, never a silent skip.

RUNS_DIR = "./runs"
# Where run records live. If altered: must match layer1_checks.py and watch.py.

FAILURE_PATTERNS = [
    # Each entry: a plain substring or regex that a layer-one failure message
    # is matched against, and the numbered shelf part that fixes that failure.
    #
    # Matching is on the failure's OWN message, not the check number, so the
    # same part fixes the same problem wherever it surfaces.
    #
    # This list starts empty on purpose. An entry is added only after layer
    # three has built a part, that part has been approved and numbered onto the
    # shelf, and the failure it fixes has been seen for real. A pattern written
    # ahead of a part is a guess about a failure nobody has had yet.
    #
    # Format:
    #   {"match": "<substring or regex>", "part": "<CAP-id>/<IMPL-id>",
    #    "version": "<version>", "regex": False}
]

PATTERN_IS_REGEX_BY_DEFAULT = False
# False = "match" is a plain substring, case-insensitive. Safer: a substring
#         cannot accidentally match far more than it meant to.
# True  = "match" is a regular expression. Only turn this on if every entry in
#         the map is written as one.

REQUIRE_EXACTLY_ONE_MATCH = True
# True  = if two patterns match the same failure, this stops with exit 2 and
#         names both. Two parts claiming the same failure is a fault in the
#         map, and picking one silently is exactly the guess Script Standard
#         1.4 forbids.
# False = the first match wins. Do not turn this off to get past a clash --
#         fix the map.

APP_SLUG = "data-dashboard"
# Which app on the shelf is being repaired. A part belongs to a capability, and
# the running app loads that capability from
# shelf/<APP_SLUG>/<CAP-id>/source.py -- so this is what decides where a repair
# actually lands. If altered: repairs are applied to that app instead.
# 2026-09-18: set for this app's chain run, was "challenge-platform" then
# "event-ticketing" before that.

BACKUP_BEFORE_APPLY = True
# True  = whatever a repair overwrites is copied into the run directory first,
#         so the repair is reversible and there is a record of what was there.
# False = the original is gone. Do not turn this off.

APPLY = True
# True  = the matched part is actually placed into the app.
# False = the match is reported and nothing is placed. Useful for reading what
#         the map would do, never for a real chain run.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import re
import sys
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent


def die(code, why):
    print(f"\nLAYER TWO COULD NOT RUN: {why}")
    sys.exit(code)


def load_failures(run_dir):
    path = Path(run_dir) / "failures.json"
    if not path.is_file():
        die(2, f"no failures.json in {run_dir} -- layer two is only ever "
               f"called on a run that failed")
    try:
        recs = json.loads(path.read_text())
    except Exception as e:
        die(2, f"{path} is unreadable: {type(e).__name__}")
    if not isinstance(recs, list) or not recs:
        die(2, f"{path} holds no failure records")
    required = ("run", "check", "level", "text", "message")
    for r in recs:
        # A level of 0 is a real level, not a missing field. Testing
        # truthiness here rejected every non-level-1 failure record.
        missing = [f for f in required if r.get(f) in (None, "")]
        if missing:
            die(2, f"a failure record is missing {', '.join(missing)} -- an "
                   f"incomplete record is how invented work gets in")
    return recs


def matches(failure):
    """Every pattern that claims this failure. Never the first one found --
    all of them, so a clash is visible rather than resolved by ordering."""
    msg = failure["message"] or ""
    hits = []
    for entry in FAILURE_PATTERNS:
        pat = entry.get("match")
        if not pat:
            continue
        is_rx = entry.get("regex", PATTERN_IS_REGEX_BY_DEFAULT)
        try:
            hit = (re.search(pat, msg, re.I) is not None) if is_rx \
                else (pat.lower() in msg.lower())
        except re.error as e:
            die(2, f"pattern {pat!r} is not a valid regex: {e}")
        if hit:
            hits.append(entry)
    return hits


def find_part(part_id, version):
    """Locate the numbered part on the shelf. A part named in the map but not
    on the shelf is a fault, not a miss -- the map is claiming something that
    does not exist."""
    shelf = (HERE / SHELF_DIR).resolve()
    try:
        cap_id, impl_id = part_id.split("/", 1)
    except ValueError:
        die(2, f"{part_id!r} is not a <CAP-id>/<IMPL-id> part number")
    record = shelf / "implementations" / cap_id / f"{impl_id}.json"
    payload = shelf / "implementations" / cap_id / impl_id
    if not record.is_file():
        die(2, f"the map names part {part_id} but there is no record for it "
               f"at {record}")
    try:
        d = json.loads(record.read_text())
    except Exception as e:
        die(2, f"{record} is unreadable: {type(e).__name__}")
    have = (d.get("release") or {}).get("version")
    if version and have != version:
        die(2, f"the map wants {part_id}@{version} but the shelf holds "
               f"{have!r} -- applying the wrong version silently is a guess")
    if not payload.is_dir():
        die(2, f"part {part_id} has a record but no payload directory at "
               f"{payload}")
    return record, payload, d


def apply_part(payload, target):
    """Copy the part's payload into the app. Touches nothing else (Script
    Standard 1.6). Returns the files placed, so the run record can say exactly
    what changed."""
    placed = []
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for src in sorted(payload.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(payload)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        placed.append(str(rel))
    return placed


def main():
    argv = sys.argv[1:]
    if "--map" in argv:
        if not FAILURE_PATTERNS:
            print("the failure-pattern map is empty -- layer two can repair "
                  "nothing yet, and every failure escalates to layer three")
            sys.exit(0)
        for e in FAILURE_PATTERNS:
            print(f"{e['match']!r}  ->  {e['part']}@{e.get('version', '')}")
        sys.exit(0)

    if not argv:
        die(2, "no run directory given")

    run_dir = Path(argv[0])
    if not run_dir.is_absolute():
        run_dir = (HERE / RUNS_DIR / run_dir.name).resolve() \
            if not run_dir.is_dir() else run_dir.resolve()
    if not run_dir.is_dir():
        die(2, f"no run directory at {run_dir}")

    wanted = None
    if "--check" in argv:
        i = argv.index("--check")
        if i + 1 >= len(argv):
            die(2, "--check given with no check number")
        wanted = argv[i + 1]

    failures = load_failures(run_dir)
    if wanted:
        failures = [f for f in failures if f["check"] == wanted]
        if not failures:
            die(2, f"no failure record for check {wanted} in {run_dir.name}")

    failure = failures[0]

    # Script Standard 3 -- the failure is never erased. It is printed first,
    # in full, before anything is said about repairing it.
    print(f"FAILURE  {failure['check']}  level {failure['level']}  "
          f"{failure['text']}")
    print(f"         {failure['message']}")

    hits = matches(failure)

    if not hits:
        print(f"\nNO PART  nothing on the shelf is mapped to this failure")
        print(f"{failure['run']}  layer two  no part -- escalate to layer three")
        sys.exit(1)

    if len(hits) > 1 and REQUIRE_EXACTLY_ONE_MATCH:
        names = ", ".join(h["part"] for h in hits)
        die(2, f"{len(hits)} parts claim this failure ({names}) -- the map is "
               f"wrong, and choosing between them here would be a guess")

    entry = hits[0]
    part_id = entry["part"]
    version = entry.get("version", "")
    record, payload, impl = find_part(part_id, version)

    if not APPLY:
        print(f"\nWOULD APPLY  {part_id}@{version} -- APPLY is off, nothing "
              f"was placed")
        sys.exit(1)

    # Where the repair actually has to land. The running app loads a
    # capability from shelf/<APP_SLUG>/<CAP-id>/, so anywhere else is a file
    # written into a directory nothing reads -- a repair that cannot repair.
    cap_id = part_id.split("/", 1)[0]
    target = Path(entry["target"]) if entry.get("target") else \
        (HERE / SHELF_DIR / APP_SLUG / cap_id).resolve()
    if not entry.get("target") and not target.parent.is_dir():
        die(2, f"no app directory at {target.parent} -- there is nowhere for "
               f"this repair to land, and writing it elsewhere would be a "
               f"repair that cannot repair")

    backed_up = []
    if BACKUP_BEFORE_APPLY and target.is_dir():
        bdir = run_dir / "before_repair" / cap_id
        bdir.mkdir(parents=True, exist_ok=True)
        for src in sorted(payload.rglob("*")):
            if src.is_dir():
                continue
            existing = target / src.relative_to(payload)
            if existing.is_file():
                dst = bdir / src.relative_to(payload)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(existing, dst)
                backed_up.append(str(src.relative_to(payload)))

    try:
        placed = apply_part(payload, target)
    except Exception as e:
        die(2, f"part {part_id} matched but could not be applied: "
               f"{type(e).__name__}: {str(e)[:70]}")

    repair = {
        "run": failure["run"],
        "check": failure["check"],
        "part": f"{part_id}@{version}" if version else part_id,
        "layer": 2,
        "restarted_as": None,   # chain.py fills this when it restarts
        "files": placed,
        "target": str(target),
        "backed_up": backed_up,
    }
    (run_dir / "repair.json").write_text(json.dumps(repair, indent=2))

    print(f"\nAPPLIED  {repair['part']}  ({len(placed)} file(s) into {target})")
    print(f"BY       layer two, from the shelf")
    print(f"{failure['run']}  layer two  part applied -- the proof is the next "
          f"run, not this one")
    sys.exit(0)


if __name__ == "__main__":
    main()
