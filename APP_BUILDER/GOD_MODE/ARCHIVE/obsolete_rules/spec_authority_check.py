#!/usr/bin/env python3
# SUPERSEDED -- NOT CURRENTLY USED AS GOVERNING AUTHORITY
# Superseded by: verification/godmode_alignment_check.py, following the
# activation of GOD_MODE/ACTIVE/God_Mode_Specification.md.
# Original path: verification/spec_authority_check.py
# Reason: this script's own checks assert a HOLD state (no active manifest
# exists, CANONICAL_SPEC.md is the document under review) that stopped
# being true the moment God Mode was activated -- running it unmodified
# now would report a false FAIL ("no active spec manifest exists") against
# a structure that is now correctly, deliberately active. Its logic was
# not deleted: it is preserved below exactly as it last ran (6/6 PASS,
# confirmed before this file was retired), and its config-block pattern
# was carried forward into its replacement.
# Archived: 2026-09-13
# SHA-256 at archival time: 04e9df60337a67c68c1d10c8f98e848f13b354cc9db34cae631210d58cbc87c0
"""spec_authority_check.py -- deterministic PASS/FAIL checker for the current
spec-authority state (see ../SPEC_AUTHORITY_DECISION.md). Checks that the
recorded HOLD decision is still internally consistent: no active manifest
silently appeared, CANONICAL_SPEC.md hasn't silently changed since the
inventory that backed the decision, the decision document still says what
this script expects, and the application's own verification evidence is
still present and green. Run it any time to confirm nothing has silently
drifted since the last spec-authority decision; re-run the full work order
(not just this script) if it reports anything other than a clean PASS.
"""

# ============================== CONFIG ==============================
# Repo root, relative to this file (verification/ is one level down).
REPO_ROOT_RELATIVE = ".."

# Where Phase A's inventory recorded CANONICAL_SPEC.md's hash at decision
# time. If CANONICAL_SPEC.md's real, current hash no longer matches the
# value recorded here, someone edited it after the decision was made
# without re-running this work order -- that is a FAIL, not a warning,
# because the whole point of the decision is that it describes a specific,
# fixed version of the file.
INVENTORY_FILE = "SPEC_AUTHORITY_INVENTORY.json"
SPEC_UNDER_REVIEW = "CANONICAL_SPEC.md"

# The decision record this checker cross-checks itself against. Change
# this path if the decision document is ever renamed.
DECISION_FILE = "SPEC_AUTHORITY_DECISION.md"

# The exact string this checker looks for to confirm the recorded decision.
# Update this if a future decision cycle produces a different verdict --
# this script does not judge whether HOLD/PROMOTE/REJECT is "correct", only
# whether the file on disk still says what it said when this check was
# last updated to expect it.
EXPECTED_DECISION_MARKER = "## Decision: **HOLD**"

# Where an active specification set would live if a future decision were
# PROMOTE. This checker only asserts that this does NOT exist while the
# recorded decision is HOLD -- if it appears without a matching PROMOTE
# decision, that is a real inconsistency (an active set with no promotion
# to justify it), not a false positive to silence.
ACTIVE_SPEC_MANIFEST = "spec/active/SPEC_MANIFEST.json"

# The application's own machine-readable verification evidence. This
# checker requires it to exist and say "overall": "PASS" -- it does not
# re-run the suite itself (the work order that produced this script was
# explicit: do not rerun tests merely to reproduce a result already on
# disk).
APP_VERIFICATION_RESULT = "verification/verification_result.json"

# The archived prior report this decision cycle preserved. If this
# checker ever reports FAIL because this is missing, someone deleted
# archived audit history, which the work order's own rules forbid.
ARCHIVED_PRIOR_REPORT = "spec/archive/reports/SPEC_AUTHORITY_CLEANUP_REPORT_prior_2026-09-13.md"
# ======================================================================

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = (HERE / REPO_ROOT_RELATIVE).resolve()


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(label, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    print(f"{status}  {label}" + (f"  -- {detail}" if detail else ""))
    return ok


def main():
    results = []

    inventory_path = ROOT / INVENTORY_FILE
    decision_path = ROOT / DECISION_FILE
    active_manifest_path = ROOT / ACTIVE_SPEC_MANIFEST
    app_verify_path = ROOT / APP_VERIFICATION_RESULT
    archived_report_path = ROOT / ARCHIVED_PRIOR_REPORT
    spec_path = ROOT / SPEC_UNDER_REVIEW

    # 1. Inventory exists and is valid JSON.
    inv = None
    if inventory_path.is_file():
        try:
            inv = json.loads(inventory_path.read_text())
            results.append(check("SPEC_AUTHORITY_INVENTORY.json exists and parses", True))
        except Exception as e:
            results.append(check("SPEC_AUTHORITY_INVENTORY.json exists and parses", False, str(e)))
    else:
        results.append(check("SPEC_AUTHORITY_INVENTORY.json exists and parses", False, "missing"))

    # 2. CANONICAL_SPEC.md's real hash matches what the inventory recorded.
    if inv is not None and spec_path.is_file():
        recorded = next((d["sha256_working_tree"] for d in inv.get("documents", [])
                          if d.get("path") == SPEC_UNDER_REVIEW), None)
        real = sha256_of(spec_path)
        results.append(check(f"{SPEC_UNDER_REVIEW} unchanged since inventory",
                              recorded is not None and recorded == real,
                              "no recorded hash found" if recorded is None else
                              (None if recorded == real else f"recorded {recorded[:12]}... real {real[:12]}...")))
    else:
        results.append(check(f"{SPEC_UNDER_REVIEW} unchanged since inventory", False,
                              "cannot compare -- inventory or spec file missing"))

    # 3. Decision document exists and states the expected decision.
    if decision_path.is_file():
        text = decision_path.read_text()
        results.append(check("SPEC_AUTHORITY_DECISION.md states the expected decision",
                              EXPECTED_DECISION_MARKER in text,
                              None if EXPECTED_DECISION_MARKER in text else
                              f"expected marker {EXPECTED_DECISION_MARKER!r} not found"))
    else:
        results.append(check("SPEC_AUTHORITY_DECISION.md states the expected decision", False, "missing"))

    # 4. No active spec manifest exists while the recorded decision is HOLD.
    #    (If a future decision is PROMOTE, update EXPECTED_DECISION_MARKER
    #    above and invert this check accordingly -- it is deliberately not
    #    conditional on the decision string, so it fails loudly instead of
    #    silently adapting if the two ever disagree.)
    manifest_absent = not active_manifest_path.is_file()
    results.append(check("no active spec manifest exists (consistent with HOLD)",
                          manifest_absent,
                          None if manifest_absent else f"found unexpected {ACTIVE_SPEC_MANIFEST}"))

    # 5. Application verification evidence exists and is green.
    if app_verify_path.is_file():
        try:
            appv = json.loads(app_verify_path.read_text())
            overall_pass = appv.get("overall") == "PASS"
            results.append(check("application verification evidence present and PASS",
                                  overall_pass, f"overall={appv.get('overall')!r}"))
        except Exception as e:
            results.append(check("application verification evidence present and PASS", False, str(e)))
    else:
        results.append(check("application verification evidence present and PASS", False, "missing"))

    # 6. Archived prior report preserved (audit history not deleted).
    results.append(check("archived prior cleanup report preserved",
                          archived_report_path.is_file(),
                          None if archived_report_path.is_file() else "missing"))

    overall = all(results)
    print()
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}  ({sum(results)}/{len(results)} checks passed)")
    return overall


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
