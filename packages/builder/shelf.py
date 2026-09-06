#!/usr/bin/env python3
"""
shelf.py — the parts shelf's lifecycle authority.

Every part on packages/builder/parts_shelf.json carries, after this module
has initialised it: a version, a lifecycle status, the exact source revision
that was qualified, and where it came from. Nothing here runs a model. The
status of a part is never typed in by hand: PRODUCT_QUALIFIED is granted only
by a qualification receipt written by the live tester after a real browser
drove the part end to end, and FROZEN is a one-time owner action on a part
that already holds that receipt.

Why this exists — Command Desk revision 42f7cf6ce72f63fa (9 Aug): every
gate green, 580 tests passing, and the first real browser click threw,
because nothing between the tests and the product had opened a browser. The
shelf must not repeat that at the part level: a part that has only ever been
proven by a test is TESTED, and says so; only a real-browser journey makes it
PRODUCT_QUALIFIED; and once FROZEN its bytes cannot change under the same
version.

  python shelf.py check                     every part carries valid lifecycle data;
                                            FROZEN/QUALIFIED parts match their receipts
  python shelf.py revision <part_id>        the current source revision of one part
  python shelf.py freeze <part_id>          one-time: PRODUCT_QUALIFIED -> FROZEN
  python shelf.py bump <part_id> <version>  start a new version of a FROZEN part
  python shelf.py init-lifecycle            one-time migration of a shelf that predates this file
"""

# ============================================================================
# RULES / CONFIG — edit here, not in the logic below.
# ============================================================================

#: The lifecycle a part moves through, in order. A part may only ever move
#: forward through this list except via `bump`, which starts a new version
#: at TESTED. Change the order and every status comparison below follows it.
LIFECYCLE = ["IMPLEMENTED", "TESTED", "PRODUCT_QUALIFIED", "FROZEN", "DEPRECATED"]

#: The lowest status a part must hold before a deployable build may vendor
#: it. Lower it to "TESTED" and apps ship on parts no browser has driven —
#: exactly the 42f7cf6c failure. Raise it to "FROZEN" and every part needs
#: an explicit freeze before any app can be declared done.
REQUIRED_STATUS_FOR_DEPLOYABLE = "PRODUCT_QUALIFIED"

#: Where qualification receipts live, relative to this file. One JSON file
#: per part@version. The receipt's `revision` must equal the part's current
#: source revision for the qualification to count; if the part's bytes
#: change, the receipt goes stale and `check` says so.
RECEIPTS_DIR = "qualification"

#: The version every part starts at when the lifecycle is first initialised.
INITIAL_VERSION = "1.0.0"

#: The status a part is given at initialisation when its shelf record already
#: cites real test evidence (every part on this shelf does). Nothing is set
#: higher than this by initialisation — PRODUCT_QUALIFIED needs a receipt.
INITIAL_STATUS_WITH_EVIDENCE = "TESTED"

#: Provenance recorded at initialisation, keyed by part_id. `read_from` is the
#: reference application whose structure the part was read from (per
#: SPECIALIST_ENGINES.md / ENGINE_CATALOGUE.md); `implementation` says whose
#: code it is. Every part must appear here or initialisation refuses.
#: Code with no licence file is all-rights-reserved by default; that is the
#: legal default, not a decision made here — change LICENCE if the owner
#: decides otherwise.
LICENCE = "All rights reserved — the owner's original code; no licence granted"
ORIGINAL = "original code written for this shelf; no third-party source copied"
PROVENANCE = {
    "crud_list_detail":               {"read_from": ["Asana", "Pipedrive", "Acuity Scheduling", "Odoo core", "Xero core"], "implementation": "the Builder's own generation rule; " + ORIGINAL},
    "oauth_connect":                  {"read_from": ["Acuity Scheduling", "Xero core"], "implementation": "the Builder's own generation rule; " + ORIGINAL},
    "api_key_connect":                {"read_from": ["Command Desk interview answers (Tavily, model providers)"], "implementation": "the Builder's own generation rule; " + ORIGINAL},
    "record_cloning":                 {"read_from": ["Asana"], "implementation": ORIGINAL},
    "stage_history":                  {"read_from": ["Pipedrive", "Odoo core"], "implementation": ORIGINAL},
    "stage_conditional_requiredness": {"read_from": ["Pipedrive"], "implementation": ORIGINAL},
    "stock_ledger":                   {"read_from": ["Odoo core"], "implementation": ORIGINAL},
    "ledger_balancing":               {"read_from": ["Xero core"], "implementation": ORIGINAL},
    "scheduled_jobs":                 {"read_from": ["Acuity Scheduling"], "implementation": ORIGINAL},
    "document_generation":            {"read_from": ["Xero core"], "implementation": ORIGINAL},
    "email_parsing":                  {"read_from": ["Xero core"], "implementation": ORIGINAL},
    "audit_trail":                    {"read_from": ["Asana", "Pipedrive", "Acuity Scheduling", "Odoo core", "Xero core"], "implementation": ORIGINAL},
    "scheduling_availability":        {"read_from": ["Acuity Scheduling"], "implementation": ORIGINAL},
    "search_fts":                     {"read_from": ["Asana", "Pipedrive", "Odoo core"], "implementation": ORIGINAL},
    "import_export":                  {"read_from": ["Pipedrive", "Xero core"], "implementation": ORIGINAL},
    "file_conversion":                {"read_from": ["Xero core"], "implementation": ORIGINAL},
    "bank_feed_ofx":                  {"read_from": ["Xero core"], "implementation": ORIGINAL},
    "calendar_ics":                   {"read_from": ["Acuity Scheduling"], "implementation": ORIGINAL},
    "document_signing":               {"read_from": ["Acuity Scheduling", "Xero core"], "implementation": ORIGINAL},
    "pdf_form_filling":               {"read_from": ["Xero core"], "implementation": ORIGINAL},
    "document_field_detection":       {"read_from": ["Hands (airexploit paperwork)"], "implementation": ORIGINAL},
    "paperwork_session_lifecycle":    {"read_from": ["Hands (airexploit paperwork)"], "implementation": ORIGINAL},
    "trust_gate_approval":            {"read_from": ["Hands (airexploit paperwork)"], "implementation": ORIGINAL},
    "value_provenance":               {"read_from": ["Hands (airexploit paperwork)"], "implementation": ORIGINAL},
    "defined_workflow_containment":   {"read_from": ["Hands (airexploit paperwork)"], "implementation": ORIGINAL},
    "preserved_original_document_store": {"read_from": ["Hands (airexploit paperwork)"], "implementation": ORIGINAL},
    "workflow_executor":              {"read_from": ["Asana", "Pipedrive", "Acuity Scheduling", "Odoo core", "Xero core"], "implementation": ORIGINAL},
    "reporting_engine":               {"read_from": ["Asana", "Pipedrive", "Acuity Scheduling", "Odoo core", "Xero core"], "implementation": ORIGINAL},
    "notification_delivery":          {"read_from": ["Asana", "Pipedrive", "Acuity Scheduling", "Odoo core", "Xero core"], "implementation": ORIGINAL},
    "interface_picker":               {"read_from": ["Asana", "Pipedrive", "Acuity Scheduling", "Odoo core", "Xero core"], "implementation": ORIGINAL},
    "system_triggered_transition":    {"read_from": ["Command Desk interview answers"], "implementation": ORIGINAL},
    "custom_action_execution":        {"read_from": ["Command Desk interview answers"], "implementation": ORIGINAL},
    "form_render_submit":             {"read_from": ["Command Desk interview answers"], "implementation": ORIGINAL},
    "stage_approval_gate":            {"read_from": ["Command Desk interview answers (FL.05)"], "implementation": ORIGINAL},
}

# ============================================================================
# LOGIC — nothing below needs editing to tune the rules above.
# ============================================================================

import ast
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SHELF_PATH = os.path.join(HERE, "parts_shelf.json")

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class ShelfError(Exception):
    """A rule of the shelf was broken. The message names the part and the rule."""


def load_shelf(path=SHELF_PATH):
    return json.load(open(path, encoding="utf-8"))


def save_shelf(shelf, path=SHELF_PATH):
    json.dump(shelf, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(path, "a", encoding="utf-8").write("\n")


def part_by_id(shelf, part_id):
    for p in shelf["parts"]:
        if p["part_id"] == part_id:
            return p
    raise ShelfError(f"{part_id}: no such part on the shelf")


# ----------------------------------------------------------------- revisions
def _symbol_source(path, symbol):
    """The exact source text of one top-level def/class/assignment named
    `symbol` in `path`. Refuses (never guesses) if the symbol is not there:
    a location that points at nothing is a shelf defect, not something to
    hash around."""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        names = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        if symbol in names:
            return ast.get_source_segment(src, node)
    raise ShelfError(f"{path}::{symbol} — symbol not found; the part's location is wrong")


def _locate(rel, root):
    """A location is written relative to the repository root. The shelf's own
    files (packages/builder/...) are also found next to this module, so a
    builder directory copied elsewhere still hashes its own parts. Anything
    else must exist under root; nothing is guessed."""
    candidates = [os.path.join(root, rel)]
    prefix = "packages/builder/"
    if rel.startswith(prefix):
        candidates.append(os.path.join(HERE, rel[len(prefix):]))
    for c in candidates:
        if os.path.exists(c):
            return c
    raise ShelfError(f"{rel}: not found under {root}" + (f" or {HERE}" if len(candidates) > 1 else ""))


def source_revision(part, root=ROOT):
    """sha256 over the exact source of every location the part names, in the
    order named. A location is `relative/path.py::symbol` (that symbol's
    source) or `relative/path.py` (the whole file). Any byte change to any
    named symbol changes the revision."""
    h = hashlib.sha256()
    for loc in part["location"]:
        rel, symbol = loc.split("::", 1) if "::" in loc else (loc, None)
        path = _locate(rel, root)
        text = _symbol_source(path, symbol) if symbol else open(path, encoding="utf-8").read()
        h.update(loc.encode("utf-8"))
        h.update(b"\0")
        h.update(text.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


# ------------------------------------------------------------------ receipts
def receipt_path(part_id, version, shelf_path=SHELF_PATH):
    return os.path.join(os.path.dirname(os.path.abspath(shelf_path)), RECEIPTS_DIR, f"{part_id}@{version}.json")


def read_receipt(part_id, version, shelf_path=SHELF_PATH):
    path = receipt_path(part_id, version, shelf_path)
    if not os.path.exists(path):
        return None
    return json.load(open(path, encoding="utf-8"))


def record_qualification(part_id, revision, journeys, base_url, shelf_path=SHELF_PATH, root=ROOT):
    """Called by the live tester, never by hand. Writes the receipt for a
    part at the revision that was actually driven, and moves TESTED ->
    PRODUCT_QUALIFIED. Refuses if the revision passed in is not the part's
    current source revision (the tester drove stale bytes), and refuses to
    write a receipt with no passing browser journey in it."""
    shelf = load_shelf(shelf_path)
    part = part_by_id(shelf, part_id)
    current = source_revision(part, root)
    if revision != current:
        raise ShelfError(f"{part_id}: qualification claims revision {revision} but the shelf is at {current}")
    if part["status"] == "FROZEN" and part.get("frozen_revision") != revision:
        raise ShelfError(f"{part_id}: FROZEN at {part.get('frozen_revision')} but the bytes driven were {revision} — "
                         f"bump the version before qualifying changed code")
    passing = [j for j in journeys if j.get("result") == "PASS" and j.get("browser_verified") is True]
    if not passing:
        raise ShelfError(f"{part_id}: no browser-verified PASS journey — nothing to qualify")
    os.makedirs(os.path.dirname(receipt_path(part_id, part["version"], shelf_path)), exist_ok=True)
    receipt = {
        "part_id": part_id, "version": part["version"], "revision": revision,
        "qualified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base_url": base_url, "journeys": journeys,
    }
    json.dump(receipt, open(receipt_path(part_id, part["version"], shelf_path), "w", encoding="utf-8"), indent=1)
    part["qualified_revision"] = revision
    if LIFECYCLE.index(part["status"]) < LIFECYCLE.index("PRODUCT_QUALIFIED"):
        part["status"] = "PRODUCT_QUALIFIED"
    save_shelf(shelf, shelf_path)
    return receipt


# ------------------------------------------------------------------- actions
def freeze(part_id, shelf_path=SHELF_PATH, root=ROOT):
    """One-time. A PRODUCT_QUALIFIED part whose receipt matches its current
    bytes becomes FROZEN at exactly that revision. Anything else is refused
    with the reason."""
    shelf = load_shelf(shelf_path)
    part = part_by_id(shelf, part_id)
    if part["status"] == "FROZEN":
        raise ShelfError(f"{part_id}: already FROZEN at {part['frozen_revision']} — freeze is one-time; use bump to start a new version")
    if part["status"] != "PRODUCT_QUALIFIED":
        raise ShelfError(f"{part_id}: status is {part['status']}; only PRODUCT_QUALIFIED parts can be frozen")
    current = source_revision(part, root)
    receipt = read_receipt(part_id, part["version"], shelf_path)
    if receipt is None or receipt["revision"] != current or part["qualified_revision"] != current:
        raise ShelfError(f"{part_id}: the qualification receipt is not for the current bytes ({current}); re-qualify before freezing")
    part["status"] = "FROZEN"
    part["frozen_revision"] = current
    part["frozen_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_shelf(shelf, shelf_path)
    return part


def bump(part_id, new_version, shelf_path=SHELF_PATH):
    """Start a new version of a part. The old version's receipt stays on disk
    under its own name; the new version begins at TESTED with no qualified
    revision and must be qualified again before any deployable build may
    vendor it."""
    shelf = load_shelf(shelf_path)
    part = part_by_id(shelf, part_id)
    if not VERSION_RE.match(new_version):
        raise ShelfError(f"{part_id}: version '{new_version}' is not MAJOR.MINOR.PATCH")
    if tuple(map(int, new_version.split("."))) <= tuple(map(int, part["version"].split("."))):
        raise ShelfError(f"{part_id}: new version {new_version} must be greater than {part['version']}")
    part["version"] = new_version
    part["status"] = INITIAL_STATUS_WITH_EVIDENCE
    part["qualified_revision"] = None
    part.pop("frozen_revision", None)
    part.pop("frozen_at", None)
    save_shelf(shelf, shelf_path)
    return part


# --------------------------------------------------------------------- check
def check_part(part, shelf_path=SHELF_PATH, root=ROOT):
    """Every rule that applies to one part, as a list of problem strings.
    Empty list = the part is in order."""
    problems = []
    pid = part.get("part_id", "?")
    for field in ("version", "status", "provenance"):
        if field not in part:
            problems.append(f"{pid}: missing '{field}'")
    if problems:
        return problems
    if not VERSION_RE.match(str(part["version"])):
        problems.append(f"{pid}: version '{part['version']}' is not MAJOR.MINOR.PATCH")
    if part["status"] not in LIFECYCLE:
        problems.append(f"{pid}: status '{part['status']}' is not one of {LIFECYCLE}")
        return problems
    prov = part["provenance"]
    for field in ("read_from", "implementation", "licence"):
        if not prov.get(field):
            problems.append(f"{pid}: provenance is missing '{field}'")
    try:
        current = source_revision(part, root)
    except (ShelfError, FileNotFoundError, SyntaxError) as exc:
        problems.append(f"{pid}: cannot compute source revision — {exc}")
        return problems
    rank = LIFECYCLE.index(part["status"])
    if rank >= LIFECYCLE.index("PRODUCT_QUALIFIED") and part["status"] != "DEPRECATED":
        receipt = read_receipt(pid, part["version"], shelf_path)
        if receipt is None:
            problems.append(f"{pid}: status {part['status']} but no receipt at {os.path.relpath(receipt_path(pid, part['version'], shelf_path), root)}")
        elif receipt["revision"] != current:
            problems.append(f"{pid}: receipt is for revision {receipt['revision']} but the source is now {current} — the part changed after it was qualified")
        if part.get("qualified_revision") != current:
            problems.append(f"{pid}: qualified_revision {part.get('qualified_revision')} != current source {current}")
    if part["status"] == "FROZEN":
        if part.get("frozen_revision") != current:
            problems.append(f"{pid}: FROZEN at {part.get('frozen_revision')} but the source is now {current} — a frozen part changed without a version bump")
    return problems


def check_shelf(shelf=None, shelf_path=SHELF_PATH, root=ROOT):
    shelf = shelf or load_shelf(shelf_path)
    problems = []
    seen = set()
    for part in shelf["parts"]:
        if part["part_id"] in seen:
            problems.append(f"{part['part_id']}: duplicate part_id")
        seen.add(part["part_id"])
        problems.extend(check_part(part, shelf_path, root))
    return problems


def meets(part, required=REQUIRED_STATUS_FOR_DEPLOYABLE):
    """True when the part's status is at or above `required` (DEPRECATED never counts)."""
    if part["status"] == "DEPRECATED":
        return False
    return LIFECYCLE.index(part["status"]) >= LIFECYCLE.index(required)


def pin(part, root=ROOT):
    """The exact identity of a part as it is right now — what a bound spec or
    a built app's manifest records so the build can be reproduced and drift
    detected."""
    return {"part_id": part["part_id"], "version": part["version"],
            "revision": source_revision(part, root), "status": part["status"]}


# ------------------------------------------------------- one-time migration
def init_lifecycle(shelf_path=SHELF_PATH):
    """Adds lifecycle fields to a shelf that predates this module. Refuses
    if any part already carries them (this is not a reset) or if any part
    has no provenance entry in PROVENANCE above (nothing is invented)."""
    shelf = load_shelf(shelf_path)
    already = [p["part_id"] for p in shelf["parts"] if "status" in p]
    if already:
        raise ShelfError(f"lifecycle already initialised on: {', '.join(already)}")
    missing = [p["part_id"] for p in shelf["parts"] if p["part_id"] not in PROVENANCE]
    if missing:
        raise ShelfError(f"no provenance recorded for: {', '.join(missing)} — add them to PROVENANCE, do not guess")
    for part in shelf["parts"]:
        if not part.get("evidence"):
            raise ShelfError(f"{part['part_id']}: no evidence recorded; cannot start it at {INITIAL_STATUS_WITH_EVIDENCE}")
        part["version"] = INITIAL_VERSION
        part["status"] = INITIAL_STATUS_WITH_EVIDENCE
        part["qualified_revision"] = None
        part["provenance"] = dict(PROVENANCE[part["part_id"]], licence=LICENCE)
        source_revision(part)  # refuses now if a location is wrong
    shelf["lifecycle"] = {
        "states": LIFECYCLE,
        "required_for_deployable": REQUIRED_STATUS_FOR_DEPLOYABLE,
        "receipts": RECEIPTS_DIR + "/<part_id>@<version>.json",
        "rule": "status is granted by receipts from the live tester and by freeze; never typed in by hand",
    }
    save_shelf(shelf, shelf_path)
    return shelf


# ----------------------------------------------------------------------- CLI
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "check":
            problems = check_shelf()
            shelf = load_shelf()
            for p in shelf["parts"]:
                print(f"{p['part_id']:34} {p.get('version','-'):8} {p.get('status','-'):18} {source_revision(p) if 'location' in p else '-'}")
            print("---")
            for prob in problems:
                print("PROBLEM", prob)
            print("SHELF OK" if not problems else f"SHELF NOT OK — {len(problems)} problem(s)")
            return 0 if not problems else 1
        if cmd == "revision":
            print(source_revision(part_by_id(load_shelf(), args[0])))
            return 0
        if cmd == "freeze":
            part = freeze(args[0])
            print(f"FROZEN {part['part_id']}@{part['version']} at {part['frozen_revision']}")
            return 0
        if cmd == "bump":
            part = bump(args[0], args[1])
            print(f"{part['part_id']} is now {part['version']} ({part['status']}); qualify it again before it can ship")
            return 0
        if cmd == "init-lifecycle":
            shelf = init_lifecycle()
            print(f"initialised {len(shelf['parts'])} parts at {INITIAL_VERSION} / {INITIAL_STATUS_WITH_EVIDENCE}")
            return 0
    except ShelfError as exc:
        print("REFUSED —", exc, file=sys.stderr)
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
