#!/usr/bin/env python3
"""
run_record.py -- the record a run leaves behind, so it can be audited.

`watch.py` never watches a run happen. It reads what the run wrote down
afterwards and decides whether the run did what it claims. This file is that
written-down form, and nothing else defines it.

Every script in the build chain writes into one of these. One record per run,
one directory per run, numbered and never reused.

A record is written even when the run fails. A run that produces no record
cannot be audited, and a run that cannot be audited is not BUILT.

Standard: god mode, ACTIVE/active_standards/ -- Script Standard 1.3 (config
block), 1.4 (no guessing), 6 (environment hygiene).
"""

# =====================================================================
# CONFIGURATION BLOCK -- one comment per setting, above all logic.
# =====================================================================

RUNS_DIR = "./runs"
# Where run directories are created, one per run, as RUN-nnnn.
# If altered: records are written and read there instead. watch.py must be
# pointed at the same place or it will audit nothing.

RUN_ID_PREFIX = "RUN-"
# The prefix on a run number. If altered: new runs are named with this
# instead. Existing runs keep the name they were written with.

RUN_ID_DIGITS = 4
# How many digits a run number is padded to. If altered: new runs are
# numbered wider or narrower. Existing runs are unaffected, and a run is
# always found by its literal directory name, never by reconstructing it.

RECORD_FILENAME = "run.json"
# The file inside a run directory that holds the record.
# If altered: written and read under this name instead.

KEEP_RUNS = 200
# How many run directories to keep before the oldest are deleted.
# If altered: more or fewer runs stay on disk. Set to 0 to keep every run
# forever. Deleting a run destroys the only evidence that run ever happened,
# so raise this rather than lower it when disk allows.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import json
import shutil
import datetime
from pathlib import Path


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class RunRecord:
    """
    One run. Built up as the run happens, written to disk at the end.

    Every field starts at a value that means "this was not established",
    never at a value that means "this was fine". An audit that reads a
    default and treats it as a pass is the failure mode this guards against.
    """

    def __init__(self, script, runs_dir=None):
        self.runs_dir = Path(runs_dir or RUNS_DIR).resolve()
        self.run_id = self._next_run_id()
        self.dir = self.runs_dir / self.run_id
        self.data = {
            "run": self.run_id,
            "script": script,
            "started": _now(),
            "ended": None,
            "verdict": None,          # PASS / FAIL / UNPROVEN / COULD_NOT_START
            "exit_code": None,
            "environment": {
                "working_directory_rebuilt": None,
                "process_started": None,
                "process_stopped": None,
                "port": None,
                "datastores": [],     # {"name", "real", "detail"}
                "mocks_declared": [], # anything the run knows was not real
            },
            "checks": [],             # {"id","level","state","claim","detail"}
            "level1": {
                "ran": False,
                "passed": None,
                "driver": None,       # what drove it, e.g. "chromium"
                "path": None,
                "javascript_errors": None,
            },
            "layer2": [],             # repair records
            "layer3": [],             # gap records + candidate results
            "parts": [],              # {"id","origin","source"}
        }

    # -- run numbering -------------------------------------------------

    def _next_run_id(self):
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        highest = 0
        for d in self.runs_dir.iterdir():
            if d.is_dir() and d.name.startswith(RUN_ID_PREFIX):
                tail = d.name[len(RUN_ID_PREFIX):]
                if tail.isdigit():
                    highest = max(highest, int(tail))
        return f"{RUN_ID_PREFIX}{highest + 1:0{RUN_ID_DIGITS}d}"

    # -- facts the run establishes as it goes --------------------------

    def environment(self, **facts):
        self.data["environment"].update(facts)

    def datastore(self, name, real, detail=""):
        self.data["environment"]["datastores"].append(
            {"name": name, "real": bool(real), "detail": detail})

    def declare_mock(self, what):
        """
        A run declares anything it knows was not real. Nothing should ever
        call this. It exists so that a run which does substitute something
        has an honest place to say so, rather than the audit having to infer
        it from silence.
        """
        self.data["environment"]["mocks_declared"].append(what)

    def check(self, check_id, level, state, claim, detail="", capability=None):
        # capability is which shelf capability this check drives, where the
        # check drives one. It is what tells layer three where a part would
        # go. None means this check exercises no single capability -- a host
        # or app-level check -- and layer three correctly refuses to invent a
        # home for a part that fixes it.
        self.data["checks"].append({
            "id": check_id, "level": level, "state": state,
            "claim": claim, "detail": detail, "capability": capability})

    def level1(self, **facts):
        self.data["level1"].update(facts)

    def repair(self, check, part, restarted_as):
        """Repair record -- Build Chain Standard, HANDOFF CONTRACTS."""
        self.data["layer2"].append({
            "run": self.run_id, "check": check, "part": part,
            "layer": 2, "restarted_as": restarted_as})

    def gap(self, gap_id, check, level, message, missing, proves_it,
            model_called_after_record=None, prompt_contents=None,
            candidates_generated=None, candidates_passed=None,
            winner_driven_through_chain=None, winner_touched_only_part=None,
            held_for_approval=None):
        """Gap record -- Build Chain Standard, HANDOFF CONTRACTS, plus what
        layer three did with it. The fields after proves_it are what the
        audit needs and the handoff contract alone does not carry."""
        self.data["layer3"].append({
            "gap": gap_id, "run": self.run_id, "check": check, "level": level,
            "message": message, "missing": missing, "proves_it": proves_it,
            "model_called_after_record": model_called_after_record,
            "prompt_contents": prompt_contents,
            "candidates_generated": candidates_generated,
            "candidates_passed": candidates_passed,
            "winner_driven_through_chain": winner_driven_through_chain,
            "winner_touched_only_part": winner_touched_only_part,
            "held_for_approval": held_for_approval,
        })

    def part(self, part_id, origin, source=""):
        """origin is 'harvested' or 'written'. Nothing else is valid, and
        the audit rejects any other value rather than assuming which."""
        self.data["parts"].append(
            {"id": part_id, "origin": origin, "source": source})

    # -- writing -------------------------------------------------------

    def write(self, verdict, exit_code):
        self.data["ended"] = _now()
        self.data["verdict"] = verdict
        self.data["exit_code"] = exit_code
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / RECORD_FILENAME
        path.write_text(json.dumps(self.data, indent=2))
        self._prune()
        return path

    def _prune(self):
        if not KEEP_RUNS:
            return
        runs = sorted(d for d in self.runs_dir.iterdir()
                      if d.is_dir() and d.name.startswith(RUN_ID_PREFIX))
        for old in runs[:-KEEP_RUNS]:
            shutil.rmtree(old, ignore_errors=True)


def load(run_dir):
    """Read a record back. Raises if it is missing or unreadable -- the
    caller decides what that means, and watch.py treats it as exit 2."""
    path = Path(run_dir) / RECORD_FILENAME
    return json.loads(path.read_text())


def latest(runs_dir=None):
    """The highest-numbered run directory, or None."""
    root = Path(runs_dir or RUNS_DIR).resolve()
    if not root.is_dir():
        return None
    runs = sorted(d for d in root.iterdir()
                  if d.is_dir() and d.name.startswith(RUN_ID_PREFIX))
    return runs[-1] if runs else None
