#!/usr/bin/env python3
"""
build.py — ONE SCRIPT. Spec v1 (2026-09-11).

Companion to THE BIBLE. Reads a choice, assembles an app from parts already
on the shelf, then proves that app works in a real browser. Prints one word.

One command, no options: `python build.py`. No cloud, no container, no
service (Bible Part Six).
"""

import os
import sys
import re
import ast
import json
import time
import shutil
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ==============================================================================
# CONFIGURATION BLOCK (Bible Rule 10) — one comment per setting, above all logic.
# Nothing configurable lives anywhere else in this file. No magic numbers inline.
# ==============================================================================

# Where the person's interface/branding choice for this build lives.
# If altered: build.py reads app_type, skin_id, skin_version, arrangement,
# branding from this file instead.
CHOICE_FILE = Path("./choice.json").resolve()

# The parts shelf: approved CAP/IMPL records (shelf/capabilities/*.json,
# shelf/implementations/<CAP-id>/<IMPL-id>.json + payload directory) and skin
# packages. If altered: assembly and repair copy parts from here instead.
SHELF_DIR = Path("./shelf").resolve()

# The one registry that allocates and remembers APP numbers across every
# build this folder has ever run. If altered: APP allocation and void
# bookkeeping read from and write to this file instead. Separate from each
# build's own builds/APP-nnn/registry.json, which is that one app's proof.
CANONICAL_REGISTRY = Path("./registry.json").resolve()

# Directory holding one JSON template per app type (filename = slugified
# app_type + ".json"). If altered: templates are read from here instead.
TEMPLATES_DIR = Path("./templates").resolve()

# The markdown list of approved app types the front door may offer.
# If altered: choice.json's app_type is validated against this file's bullet
# list instead. Not found there is BROKEN, never guessed.
APPS_LIST_FILE = Path("./APPS_LIST.md").resolve()

# Directory under which each assembled app gets its own APP-nnn subfolder.
# If altered: assembled apps land here instead; each build wipes and rebuilds
# its own subfolder only (Bible Part Six -- clean slate per run).
BUILDS_DIR = Path("./builds").resolve()

# Append-only run ledger: one JSON line per run/failure/repair/gap record.
# If altered: run numbering, the loop guard, the regression guard within one
# invocation's restarts, and the repeated-gap guard across invocations all
# read their history from and write it to this file instead.
LEDGER_FILE = Path("./run_ledger.jsonl").resolve()

# Directory where one detailed report is written per run (every check line,
# every subprocess's stdout). If altered: reports land here instead.
REPORTS_DIR = Path("./reports").resolve()

# How long (seconds) to wait for the assembled app's health endpoint to
# return 200 before giving up. If altered: slower- or faster-starting apps
# get more or less patience before BROKEN app did not start.
HEALTH_TIMEOUT_SECONDS = 15

# N means N repairs are allowed, each restarted and proven; the failure that
# would need an (N+1)th repair is BROKEN restart ceiling instead. If altered:
# raises or lowers tolerance for sequential shelf repairs in one invocation.
MAX_RESTARTS = 10

# False means: on any check failure, go straight to HELD instead of ever
# calling a model. If altered: turns the whole gap-building stage off.
ALLOW_LAYER3 = True

# The HTTP endpoint layer three POSTs each gap framing to. Sam names this --
# the code carries nothing provider-specific; whatever is here receives a
# JSON body {"model": LAYER3_MODEL, "messages": [...]} with the credential as
# a bearer token. Empty means the script refuses to do anything (Bible rule 13).
LAYER3_ENDPOINT = ""

# The model name sent in that body. Sam names this -- empty means the script
# refuses to do anything (Bible rule 13).
LAYER3_MODEL = ""

# The credential sent as the Authorization bearer token with the model call.
# Pasted here, never a file, never argv, never printed, never in a repo
# (Bible Part Six). Empty means the script refuses to do anything.
LAYER3_CREDENTIAL = ""

# The distinct framings of the same gap record sent to LAYER3_MODEL, one
# candidate per framing. If altered: more framings cost more per gap but
# widen the variety of candidate attempts; fewer costs less.
CANDIDATE_FRAMINGS = ["literal", "generalized", "minimal-change"]

# Layer two's first pass: a failure message substring -> a shelf part alias
# ("name@version"). If altered: which failures layer two can fix without a
# structural sweep, and which part it reaches for, changes.
FAILURE_PATTERN_MAP: Dict[str, str] = {}

# Stage three (round 6): where a proven (canonical status "active") app gets
# copied to, as a subdirectory of the current working directory. If altered:
# promotion reads/writes library apps here instead of ./library.
LIBRARY_SUBDIR = "library"

# Stage three: the marker file written into a promoted app's library copy,
# recording when and from which run it was promoted. If altered: promotion
# evidence is looked for under this filename instead.
PROMOTION_MARKER = "PROMOTED.json"

# ==============================================================================
# END OF CONFIGURATION BLOCK
# ==============================================================================


# ------------------------------------------------------------------------------
# Exit verdicts
# ------------------------------------------------------------------------------
class Broken(Exception):
    """Cannot make progress. Exit code 2."""


class Held(Exception):
    """Stops, names what is waiting. Exit code 1."""


# ------------------------------------------------------------------------------
# Ledger
# ------------------------------------------------------------------------------
_RUN_RE = re.compile(r"RUN-(\d+)")
_GAP_RE = re.compile(r"GAP-(\d+)")
_APP_RE = re.compile(r"APP-(\d+)")


def _read_ledger_lines() -> List[dict]:
    if not LEDGER_FILE.exists():
        return []
    out = []
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def append_ledger(record: dict) -> None:
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def next_run_id() -> str:
    """The next unused RUN id. Scans only the "run" field -- a run id that has
    actually been consumed by a real run_layer_one() call. "restarted_as" is
    a forward-looking bookkeeping label (this failure's repair is expected to
    be proven by the following run) and is NOT itself a consumed run id;
    counting it here would reserve a number twice and skip one (confirmed by
    real execution: a repair after RUN-0001 landed on RUN-0003, silently
    skipping RUN-0002, before this fix)."""
    highest = 0
    for rec in _read_ledger_lines():
        val = rec.get("run")
        if isinstance(val, str):
            m = _RUN_RE.search(val)
            if m:
                highest = max(highest, int(m.group(1)))
    return f"RUN-{highest + 1:04d}"


def find_prior_gap_for_check(check_id: str) -> Optional[str]:
    """The gap guard reads the ledger, not memory (row 20) -- so a gap's
    identity is tied to which check it came from. If this check has ever
    produced a gap record before (in this or an earlier invocation), that is
    the SAME gap raised again."""
    for rec in _read_ledger_lines():
        if rec.get("gap") and rec.get("check") == check_id:
            return rec["gap"]
    return None


def next_gap_id() -> str:
    highest = 0
    for rec in _read_ledger_lines():
        val = rec.get("gap")
        if isinstance(val, str):
            m = _GAP_RE.search(val)
            if m:
                highest = max(highest, int(m.group(1)))
    return f"GAP-{highest + 1:04d}"


# ------------------------------------------------------------------------------
# Canonical registry (APP allocation + lifecycle bookkeeping)
#
# Record shapes are the Numbering Standard's own, word for word:
#   §3.3 application  {id, name, status, owner, created_at, screens}
#   §3.4 screen       {id, app_id, name, status, buttons}
#   §3.5 button       {id, screen_id, name, expected_contract, capability_id, status}
#   §3.6 capability   {id, name, category, status, data_shape, dependencies,
#                      permissions, side_effects, error_contract,
#                      implementations, qualification}
#   §3.7 implementation {id, capability_id, status, release, source,
#                      dependencies, tests, rollback}
# Status values are §6.2's lifecycle states -- candidate, approved, active,
# deprecated, retired -- plus "void" for a failed allocation (§6.1 rule 14).
# The registry's top-level entity is "applications" (§3.2).
# ------------------------------------------------------------------------------
LIFECYCLE_STATES = ("candidate", "approved", "active", "deprecated", "retired")

APP_RECORD_KEYS = ("id", "name", "status", "owner", "created_at", "screens")
SCR_RECORD_KEYS = ("id", "app_id", "name", "status", "buttons")
BTN_RECORD_KEYS = ("id", "screen_id", "name", "expected_contract", "capability_id", "status")
CAP_RECORD_KEYS = ("id", "name", "category", "status", "data_shape", "dependencies",
                   "permissions", "side_effects", "error_contract", "implementations", "qualification")
IMPL_RECORD_KEYS = ("id", "capability_id", "status", "release", "source", "dependencies", "tests", "rollback")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_canonical_registry() -> Dict[str, Any]:
    if not CANONICAL_REGISTRY.exists():
        return {"applications": []}
    try:
        with open(CANONICAL_REGISTRY, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"applications": []}


def write_canonical_registry(data: Dict[str, Any]) -> None:
    tmp = CANONICAL_REGISTRY.parent / f".{CANONICAL_REGISTRY.name}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(CANONICAL_REGISTRY)


def allocate_app_id(name: str) -> str:
    """§6.1: sequential, never reused, read from the current highest number
    in the canonical registry (void entries count -- their numbers stay
    taken). The new record is a full §3.3 application record in the
    "candidate" state (§6.2: proposed, not yet approved)."""
    reg = read_canonical_registry()
    highest = 0
    for a in reg.get("applications", []):
        m = _APP_RE.search(a.get("id", ""))
        if m:
            highest = max(highest, int(m.group(1)))
    new_id = f"APP-{highest + 1:03d}"
    reg.setdefault("applications", []).append({
        "id": new_id, "name": name, "status": "candidate", "owner": "builder",
        "created_at": _now(), "screens": [],
    })
    write_canonical_registry(reg)
    return new_id


def set_app_status(app_id: Optional[str], status: str, screens: Optional[List[str]] = None) -> None:
    """Moves one canonical application record to `status`, keeping every
    other §3.3 field as it was; fills `screens` when given (end of stage 1).
    Only a BUILT run ever passes "active" here."""
    if not app_id:
        return
    try:
        reg = read_canonical_registry()
        for i, a in enumerate(reg.get("applications", [])):
            if a.get("id") == app_id:
                a["status"] = status
                if screens is not None:
                    a["screens"] = list(screens)
                reg["applications"][i] = a
                break
        write_canonical_registry(reg)
    except Exception as e:
        print(f"  (note: could not write {status} record for {app_id}: {e})", file=sys.stderr)


def void_app(app_id: Optional[str]) -> None:
    """§6.1 rule 14: a failed allocation is recorded as void, never silently
    reused."""
    set_app_status(app_id, "void")


# ------------------------------------------------------------------------------
# Shelf readers -- the shelf is read in the same §3.6 / §3.7 format
# ------------------------------------------------------------------------------
def read_shelf_cap(cap_id: str) -> Optional[dict]:
    f = SHELF_DIR / "capabilities" / f"{cap_id}.json"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_shelf_impl(impl_id: str) -> Optional[Tuple[dict, Path]]:
    """Returns (§3.7 record, payload directory) or None. The payload
    directory sits beside the record: shelf/implementations/<CAP>/<IMPL>/."""
    meta_file = SHELF_DIR / "implementations" / f"{impl_id}.json"
    payload_dir = SHELF_DIR / "implementations" / impl_id
    if not meta_file.is_file() or not payload_dir.is_dir():
        return None
    try:
        return json.loads(meta_file.read_text(encoding="utf-8")), payload_dir
    except Exception:
        return None


def read_shelf_aliases() -> Dict[str, str]:
    """§3.2 `aliases` / §7.1: shelf-part alias ("name@version") -> the one
    CAP/IMPL it references. Kept in shelf/aliases.json, never inside an
    IMPL record (§3.7 has no alias field; §7.3: an alias is not an identity)."""
    f = SHELF_DIR / "aliases.json"
    if not f.is_file():
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for entry in data.get("aliases", []):
        if isinstance(entry, dict) and entry.get("alias") and entry.get("impl_id"):
            out[entry["alias"]] = entry["impl_id"]
    return out


def alias_for(impl_id: str) -> str:
    """The shelf-part alias that references this IMPL (§7.1), or the IMPL id
    itself when no alias is registered for it."""
    for alias, ref in read_shelf_aliases().items():
        if ref == impl_id:
            return alias
    return impl_id


def cap_is_usable(cap: dict) -> bool:
    """§4.2 step 7 -- "Confirm the CAP is approved and active": status
    active (§6.2) and qualification.status approved."""
    return cap.get("status") == "active" and \
        (cap.get("qualification") or {}).get("status") == "approved"


def impl_is_usable(impl: dict) -> bool:
    """An IMPL Sam has approved (§6.2 "approved": eligible for registration,
    or "active": registered) with release.approved set. This is what a
    repair may reach for by alias; stage-one wiring is stricter -- see
    active_impl_for()."""
    return impl.get("status") in ("active", "approved") and bool((impl.get("release") or {}).get("approved"))


def active_impl_for(cap: dict) -> Optional[Tuple[dict, Path]]:
    """The one IMPL among cap.implementations that is "active" (§6.2:
    registered and available for use) with release.approved, and its
    payload directory. None if there isn't exactly one -- §5.1: one
    implementation by default."""
    found = []
    for impl_id in cap.get("implementations", []):
        got = read_shelf_impl(impl_id)
        if got and got[0].get("status") == "active" and impl_is_usable(got[0]) \
                and got[0].get("capability_id") == cap.get("id"):
            found.append(got)
    return found[0] if len(found) == 1 else None


# ------------------------------------------------------------------------------
# §3.8 registry invariants (thirteen, in §3.8's own order and words)
# ------------------------------------------------------------------------------
def verify_registry_invariants(registry: Dict[str, Any]) -> None:
    apps = registry.get("applications", [])
    screens = registry.get("screens", [])
    buttons = registry.get("buttons", [])
    caps = registry.get("capabilities", [])
    impls = registry.get("implementations", [])

    seen_ids = set()

    def unique(entity_id, label):
        # 1. Duplicate IDs.
        if not entity_id or entity_id in seen_ids:
            raise Broken(f"registry  duplicate or missing {label} id  {entity_id}")
        seen_ids.add(entity_id)

    def shape(record, keys, label):
        # 2. Invalid ID formats -- and the record shape itself, §3.3-3.7 word for word.
        if tuple(record.keys()) != keys:
            raise Broken(f"registry  {label} record is not the §3 shape  {record.get('id')}  "
                         f"has {list(record.keys())}  needs {list(keys)}")
        if record.get("status") not in LIFECYCLE_STATES:
            raise Broken(f"registry  {label} status not a §6.2 state  {record.get('id')}  {record.get('status')!r}")

    app_ids = set()
    for a in apps:
        aid = a.get("id")
        unique(aid, "application")
        shape(a, APP_RECORD_KEYS, "application")
        if not re.fullmatch(r"APP-\d{3,}", aid):
            raise Broken(f"registry  invalid id format  {aid}")
        app_ids.add(aid)

    # 8. Reuse of retired IDs -- the id this build carries must be exactly
    # this allocation in the canonical registry, not a retired/void one.
    canon = {a.get("id"): a for a in read_canonical_registry().get("applications", [])}
    for aid in app_ids:
        entry = canon.get(aid)
        if entry is None or entry.get("status") in ("retired", "void"):
            raise Broken(f"registry  reuse of retired id  {aid}")

    screen_ids = set()
    for s in screens:
        sid = s.get("id")
        unique(sid, "screen")
        shape(s, SCR_RECORD_KEYS, "screen")
        parent = s.get("app_id")
        if parent not in app_ids:
            raise Broken(f"registry  missing parent record  {sid}")  # 3.
        if not re.fullmatch(re.escape(parent) + r"/SCR-\d{3,}", sid):
            raise Broken(f"registry  invalid id format  {sid}")
        screen_ids.add(sid)

    cap_map = {}
    for c in caps:
        cid = c.get("id")
        unique(cid, "capability")
        shape(c, CAP_RECORD_KEYS, "capability")
        if not re.fullmatch(r"CAP-\d{4,}", cid):
            raise Broken(f"registry  invalid id format  {cid}")
        cap_map[cid] = c

    impl_map = {}
    for imp in impls:
        iid = imp.get("id")
        unique(iid, "implementation")
        shape(imp, IMPL_RECORD_KEYS, "implementation")
        parent_cap = imp.get("capability_id")
        if not parent_cap or parent_cap not in cap_map:
            raise Broken(f"registry  IMPL belongs to nonexistent CAP  {iid}")  # 6.
        if not re.fullmatch(re.escape(parent_cap) + r"/IMPL-\d{2,}", iid):
            raise Broken(f"registry  invalid id format  {iid}")
        impl_map[iid] = imp

    for b in buttons:
        bid = b.get("id")
        unique(bid, "button")
        shape(b, BTN_RECORD_KEYS, "button")
        parent = b.get("screen_id")
        if parent not in screen_ids:
            raise Broken(f"registry  missing parent record  {bid}")
        if not re.fullmatch(re.escape(parent) + r"/BTN-\d{3,}", bid):
            raise Broken(f"registry  invalid id format  {bid}")
        attached = b.get("capability_id")
        if isinstance(attached, list):
            if len(attached) != 1:
                raise Broken(f"registry  multiple active capability references on one BTN  {bid}")  # 10.
            attached = attached[0]
        if not attached or attached not in cap_map:
            raise Broken(f"registry  BTN references nonexistent CAP  {bid} -> {attached}")  # 4.
        if not cap_is_usable(cap_map[attached]):
            raise Broken(f"registry  unapproved CAP or IMPL creation  {attached}")  # 9.

    impl_owner: Dict[str, str] = {}
    for cid, c in cap_map.items():
        listed = c.get("implementations", [])
        active = [i for i in listed if i in impl_map and impl_map[i].get("status") == "active"
                  and impl_is_usable(impl_map[i])]
        if not active:
            raise Broken(f"registry  CAP without an approved active IMPL  {cid}")  # 5.
        for i in listed:
            if i in impl_owner and impl_owner[i] != cid:
                raise Broken(f"registry  IMPL assigned to more than one CAP  {i}")  # 7.
            impl_owner[i] = cid
        q = c.get("qualification") or {}
        if q.get("status") != "approved" or not q.get("approval_ref"):
            raise Broken(f"registry  missing approval evidence  {cid}")  # 12.

    for iid, imp in impl_map.items():
        if impl_owner.get(iid) not in (None, imp.get("capability_id")):
            raise Broken(f"registry  IMPL assigned to more than one CAP  {iid}")
        rel = imp.get("release") or {}
        if imp.get("status") in ("active", "approved") and not rel.get("approved"):
            raise Broken(f"registry  unapproved CAP or IMPL creation  {iid}")
        if not rel.get("approval_ref"):
            raise Broken(f"registry  missing approval evidence  {iid}")
        src = imp.get("source") or {}
        if imp.get("status") == "active" and not (src.get("repository") and src.get("path")):
            raise Broken(f"registry  missing source reference for active IMPL  {iid}")  # 13.

    # 11. Broken alias references -- every shelf alias must point at a real IMPL.
    for alias, impl_id in read_shelf_aliases().items():
        if read_shelf_impl(impl_id) is None:
            raise Broken(f"registry  broken alias reference  {alias} -> {impl_id}")


# ------------------------------------------------------------------------------
# §4.4 contract matcher (twelve axes)
# ------------------------------------------------------------------------------
def _version_tuple(v: Any) -> Tuple[int, ...]:
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0,)


def match_contract(expected: Dict[str, Any], cap: Dict[str, Any], impl: Dict[str, Any]) -> Tuple[bool, str]:
    """§4.4's twelve axes. The CAP is a §3.6 record: the shape axes live
    under data_shape (input / output / nullable / requires_auth /
    security_constraints -- §3.6 defers data_shape's internals to the
    Unified Feature Structure, which is not in the package, so that
    sub-structure is the minimum these twelve comparisons need). Version
    compatibility is read from the active IMPL's §3.7 release.version."""
    shape = cap.get("data_shape", {})
    cin = shape.get("input", {})
    cout = shape.get("output", {})

    exp_req = set(expected.get("required_input_fields", []))
    if not exp_req.issubset(set(cin.get("required", []))):
        return False, f"missing required input fields: {exp_req - set(cin.get('required', []))}"
    if expected.get("input_types", {}) != cin.get("types", {}):
        return False, "input types mismatch"
    exp_out = set(expected.get("output_fields", []))
    if not exp_out.issubset(set(cout.get("fields", []))):
        return False, f"missing output fields: {exp_out - set(cout.get('fields', []))}"
    if expected.get("output_types", {}) != cout.get("types", {}):
        return False, "output types mismatch"
    # H-T3 (round 5, resolved by ruling since the source documents on hand
    # don't settle it): nullability is loosened to a DIRECTIONAL subset --
    # a capability may guarantee a field is non-null even where the caller
    # only expected it MIGHT be null (stricter than required is safe); a
    # capability may never declare a field nullable that the caller did not
    # already expect could be null (that would surprise the caller with an
    # unhandled null). So cap.nullable must be a subset of expected.nullable,
    # never the reverse -- exact equality forced templates to over-declare
    # every nullable field a capability happened to allow, not just the ones
    # the slot actually needed to plan for.
    cap_nullable = set(shape.get("nullable", []))
    exp_nullable = set(expected.get("nullable_fields", []))
    if not cap_nullable.issubset(exp_nullable):
        return False, f"capability allows null on fields the caller doesn't expect: {cap_nullable - exp_nullable}"
    if set(expected.get("permissions", [])) != set(cap.get("permissions", [])):
        return False, "permissions mismatch"
    if expected.get("requires_auth", False) != shape.get("requires_auth", False):
        return False, "authentication requirement mismatch"
    exp_deps = set(expected.get("dependencies", []))
    if not exp_deps.issubset(set(cap.get("dependencies", []))):
        return False, "unmet dependencies"
    exp_err = set(expected.get("handled_errors", []))
    if not exp_err.issubset(set(cap.get("error_contract", {}).get("error_codes", []))):
        return False, "unhandled error contract codes"
    # H-T3, same ruling: security_constraints loosens to a dict-subset check
    # -- every constraint the caller actually requires must be present, with
    # the same value, on the capability; the capability is free to declare
    # additional constraints beyond what was asked for. Not a "stricter is
    # better" ordering (the constraint value's own semantics aren't defined
    # anywhere in the package, and inventing an ordering would be guessing),
    # just a real subset-of-key-value-pairs check.
    exp_sec = expected.get("security_constraints", {}) or {}
    cap_sec = shape.get("security_constraints", {}) or {}
    unmet_sec = {k: v for k, v in exp_sec.items() if cap_sec.get(k) != v}
    if unmet_sec:
        return False, f"security constraints not met by capability: {unmet_sec}"
    if expected.get("side_effects", []) != cap.get("side_effects", []):
        return False, "side effects mismatch"
    if _version_tuple(expected.get("min_version", "1.0.0")) > _version_tuple((impl.get("release") or {}).get("version", "0")):
        return False, "version incompatibility"
    return True, ""


# ------------------------------------------------------------------------------
# STAGE 1 — ASSEMBLE
# ------------------------------------------------------------------------------
def stage1_assemble() -> Tuple[str, Path, Dict[str, Any], Dict[str, Any]]:
    """Returns (app_id, app_dir, registry, locators). Raises Broken or Held."""
    allocated: Optional[str] = None
    try:
        # 2. Read choice.json
        if not CHOICE_FILE.is_file():
            raise Broken("choice  file")
        try:
            choice = json.loads(CHOICE_FILE.read_text(encoding="utf-8"))
        except Exception:
            raise Broken("choice  unreadable")
        for field in ("app_type", "skin_id", "skin_version", "arrangement", "branding"):
            if field not in choice:
                raise Broken(f"choice  {field}")
        if not choice.get("branding", {}).get("name"):
            raise Broken("choice  name")
        print(f"2  choice read  app_type={choice['app_type']!r}")

        if not APPS_LIST_FILE.is_file():
            raise Broken("choice  APPS_LIST.md missing")
        valid_types = []
        for raw in APPS_LIST_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith(("-", "*")):
                item = line.lstrip("-* \t").strip()
                if item:
                    valid_types.append(item)
        if choice["app_type"] not in valid_types:
            raise Broken("choice  app_type")

        # 3. Resolve template
        slug = choice["app_type"].lower().replace(" ", "_").replace("/", "_")
        tpl_path = TEMPLATES_DIR / f"{slug}.json"
        if not tpl_path.is_file():
            raise Broken(f"template not found  {slug}")
        try:
            template = json.loads(tpl_path.read_text(encoding="utf-8"))
        except Exception:
            raise Broken(f"template unreadable  {slug}")
        if not template.get("accepted", False):
            raise Broken(f"template not accepted  {slug}")
        print(f"3  template resolved  {slug}")

        # 4. Allocate APP number (a §3.3 "candidate" record), fresh directory
        allocated = allocate_app_id(choice["branding"]["name"])
        app_dir = BUILDS_DIR / allocated
        if app_dir.exists():
            shutil.rmtree(app_dir)
        app_dir.mkdir(parents=True, exist_ok=True)
        print(f"4  {allocated}  allocated")
        print(f"1  fresh directory  {app_dir}")

        # 5. Copy parts -- shelf records are read in their §3.6 / §3.7 shape
        required_caps = template.get("required_capabilities", [])
        loaded_caps: Dict[str, dict] = {}
        loaded_impls: Dict[str, dict] = {}
        for cid in required_caps:
            cap = read_shelf_cap(cid)
            if cap is None or not cap_is_usable(cap):
                raise Broken(f"no approved IMPL  {cid}")
            got = active_impl_for(cap)
            if got is None:
                raise Broken(f"no approved IMPL  {cid}")
            impl, impl_payload_dir = got
            _copy_payload(impl_payload_dir, app_dir / "modules")
            loaded_caps[cid] = cap
            loaded_impls[impl["id"]] = impl
        print(f"5  parts copied  {', '.join(required_caps) if required_caps else '(none required)'}")

        # 5b. Declared-dependency enforcement. A capability's own §3.6
        # "dependencies" field is not decorative: if it declares that it
        # needs another capability's data or behaviour, that capability
        # must also be required by this template -- and therefore already
        # copied in above -- or this is exactly the same class of silent,
        # undeclared coupling this field exists to prevent (found by real
        # audit: a capability that reads a sibling's data file by a
        # hardcoded path with no declared dependency silently produces
        # empty/wrong output when reused without that sibling, instead of
        # failing). Checked here, once, after every required capability's
        # own record is loaded, so a missing dependency is caught before
        # any code from either capability ever runs.
        for cid, cap in loaded_caps.items():
            for dep_id in cap.get("dependencies", []):
                if dep_id not in loaded_caps:
                    raise Broken(f"missing declared dependency  {cid} requires {dep_id}")

        # 6. Lay the skin
        skin_json = {
            "skin_id": choice["skin_id"],
            "skin_version": choice["skin_version"],
            "branding": choice["branding"],
            "arrangement": choice["arrangement"],
        }
        (app_dir / "skin.json").write_text(json.dumps(skin_json, indent=2), encoding="utf-8")
        print(f"6  skin laid  {choice['skin_id']}@{choice['skin_version']}")

        # 7. Allocate SCR/BTN, wire, contract-match
        arrangement_map = {i["slot"]: i["position"] for i in choice.get("arrangement", [])}
        slots = template.get("interface_slots", [])
        active_slots = [s for s in slots if s.get("target_capability") in loaded_caps]

        # §3.4 / §3.5 need a screen name and a button name; they come from the
        # template (Sam's supply), never invented here.
        if not template.get("entry_screen_name"):
            raise Broken("template  entry_screen_name")
        screen_id = f"{allocated}/SCR-001"
        route = template.get("entry_route", "/")
        buttons: List[dict] = []
        locators = {"screens": {screen_id: {"route": route}}, "buttons": {}}

        btn_idx = 1
        for slot in active_slots:
            if not slot.get("name"):
                raise Broken(f"template  slot name  {slot.get('slot_id')}")
            btn_id = f"{screen_id}/BTN-{btn_idx:03d}"
            btn_idx += 1
            target = slot["target_capability"]
            cap = loaded_caps[target]
            impl = next(i for i in loaded_impls.values() if i.get("capability_id") == target)
            ok, reason = match_contract(slot.get("expected_contract", {}), cap, impl)
            if not ok:
                raise Held(f"{btn_id} -> {target}: {reason}")
            # §3.5 button record, word for word. The BTN's declared expected
            # contract is the twelve-axis declaration it was validated against.
            buttons.append({
                "id": btn_id, "screen_id": screen_id, "name": slot["name"],
                "expected_contract": slot.get("expected_contract", {}),
                "capability_id": target, "status": "active",
            })
            # slot / arrangement position / selector are wiring, not identity:
            # they live in locators.json, beside the registry, not in it.
            locators["buttons"][btn_id] = {
                "selector": slot.get("selector", f"[data-slot='{slot['slot_id']}']"),
                "slot": slot["slot_id"],
                "position": arrangement_map.get(slot["slot_id"], "center"),
            }
        # §3.4 screen record, word for word.
        screen = {"id": screen_id, "app_id": allocated, "name": template["entry_screen_name"],
                  "status": "active", "buttons": [b["id"] for b in buttons]}
        print(f"7  wired  1 screen, {len(buttons)} button(s)")

        # 9. Registry + invariants. The §3.3 application record is written in
        # the "candidate" state -- assembled, not yet proven. Only a BUILT run
        # moves it to "active" (§6.2), in stage two.
        app_record = {
            "id": allocated, "name": choice["branding"]["name"], "status": "candidate",
            "owner": "builder", "created_at": _now(), "screens": [screen_id],
        }
        registry = {
            "applications": [app_record], "screens": [screen], "buttons": buttons,
            "capabilities": list(loaded_caps.values()), "implementations": list(loaded_impls.values()),
        }
        verify_registry_invariants(registry)
        (app_dir / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
        print(f"9  registry written  13/13 invariants passed")

        # 10. app.json + locators.json
        app_json = {
            "start": template.get("start_command"),
            "port": template.get("port"),
            "health": template.get("health_endpoint", "/health"),
        }
        if not app_json["start"] or not app_json["port"]:
            raise Broken("template  start_command/port")
        # Optional, additive: a template MAY declare how its own primary UI
        # journey is driven and confirmed (input_selector/input_value/
        # action_selector/confirm_selector/confirm_contains). Absent for
        # every template that predates this field -- build_checks() falls
        # back to the exact original hardcoded CAP-0001 fixture journey when
        # it's missing, so no existing proven template's behavior changes.
        if template.get("primary_journey"):
            app_json["primary_journey"] = template["primary_journey"]
        (app_dir / "app.json").write_text(json.dumps(app_json, indent=2), encoding="utf-8")
        (app_dir / "locators.json").write_text(json.dumps(locators, indent=2), encoding="utf-8")
        print(f"10  app.json + locators.json written")

        # 11. Template tests
        test_cmd = template.get("test_command")
        if not test_cmd:
            raise Broken("template has no tests")
        if not isinstance(test_cmd, list):
            raise Broken("template test_command must be an argument list")
        res = subprocess.run(test_cmd, cwd=str(app_dir), capture_output=True, text=True)
        if res.stdout:
            sys.stdout.write(res.stdout)
        if res.stderr:
            sys.stderr.write(res.stderr)
        if res.returncode != 0:
            raise Broken(f"template tests failed  code {res.returncode}")
        print(f"11  template tests passed")

        # Stage 1 done: still "candidate" in the canonical registry, now with
        # its screens filled in. Stage two decides whether it becomes active.
        set_app_status(allocated, "candidate", screens=[screen_id])
        print(f"12  {allocated}  assembled  {app_dir}")
        return allocated, app_dir, registry, locators

    except Held as h:
        void_app(allocated)
        print(f"HELD  CAP candidate  {h}  awaiting approval")
        raise
    except Broken as b:
        void_app(allocated)
        print(f"BROKEN  {b}")
        raise
    except Exception as e:
        void_app(allocated)
        print(f"BROKEN  unexpected failure: {e}")
        raise Broken(str(e))


def _copy_payload(src_dir: Path, dest_root: Path) -> None:
    """Copies every file under src_dir to the same relative path under
    dest_root, creating directories as needed. Used both for stage 1's
    initial part copy and for layer two's repairs -- a shelf part's payload
    directory IS the set of files it changes, nothing more, nothing less."""
    for path in src_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(src_dir)
            dest = dest_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


# ------------------------------------------------------------------------------
# STAGE 2 — PROVE
# ------------------------------------------------------------------------------
def _wait_for_health(base_url: str, health_path: str, timeout_s: float,
                      proc: Optional[subprocess.Popen] = None) -> bool:
    """Round 7: also watches the real subprocess itself (proc.poll()), not
    just the clock -- a process that has already crashed (missing real
    dependency, real import error, a real port conflict) is never going to
    start answering health checks no matter how long the timeout is, and
    waiting out the full HEALTH_TIMEOUT_SECONDS anyway would only delay
    surfacing the real reason (see run_layer_one(), which reads the
    process's own real stdout/stderr the moment this returns False)."""
    deadline = time.time() + timeout_s
    url = base_url.rstrip("/") + health_path
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        if proc is not None and proc.poll() is not None:
            return False  # the real process already exited -- stop waiting
        time.sleep(0.2)
    return False


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _http_json(method: str, url: str, body: Optional[dict] = None) -> Tuple[int, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)


def _extract_route_meta(module_file: Path) -> Tuple[Optional[str], Optional[str]]:
    """Reads a shelf part's declared ROUTE/METHOD the way §3.7's own contract
    already requires every route-module IMPL to declare them (see
    verification/gen_fixtures.py's route_module()) -- statically, via the AST,
    never by importing/executing the file. This is what lets build_checks()
    below generate a real check for a capability id it has never been told
    about by name: the route and method come from the shelf part itself, not
    from a branch written per CAP id here. Returns (None, None), never a
    guess, if either constant is absent or isn't a plain string literal --
    such a capability gets no generic check (see the loop below)."""
    try:
        tree = ast.parse(module_file.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    route = method = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            if target_name in ("ROUTE", "METHOD") and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, str):
                if target_name == "ROUTE":
                    route = node.value.value
                else:
                    method = node.value.value
    return route, method


def _detect_host_capability_id(app_json: Dict[str, Any], registry: Dict[str, Any]) -> Optional[str]:
    """Which capability IS the app's own host/entry module -- derived from a
    real, already-available fact (app.json's own "start" command, written
    by stage one straight from the template's start_command), never from a
    literal capability id written into this function. The host is whichever
    capability's active IMPL entrypoint is the exact module the start
    command launches. Returns None if nothing matches (e.g. a non-Python
    start command) -- no generic UI-journey checks get generated for that
    case, rather than guessing which capability is the host.

    Matching the start command alone isn't sufficient to decide there's a UI
    journey worth checking, though: a template may require the host module
    (so its health check answers) without giving it any front-door action at
    all -- proven deliberately by verify_build.py's row 21a, which requires
    CAP-0001 but wires only an unrelated capability, precisely so that NO
    browser check exists. So the host is recognized here only when there is
    real evidence of a UI journey to verify: either the module is wired to a
    button (the old CAP-0001 fixture's own pattern -- it bakes a create-item
    action into the host itself; see build_checks()'s docstring on why that
    specific pattern isn't required of every app), or the template explicitly
    declares one via `primary_journey` (the real-app pattern: a host page
    that is pure infrastructure, with every real action living in its own
    separate, slot-wired capability, still has a real journey to check --
    it's just declared instead of inferred from wiring)."""
    start = app_json.get("start") or []
    module_arg = None
    for part in start:
        if isinstance(part, str) and part.endswith(".py"):
            module_arg = part.split("modules/", 1)[-1]
            break
    if not module_arg:
        return None
    wired_cap_ids = {b.get("capability_id") for b in registry.get("buttons", [])}
    has_declared_journey = bool(app_json.get("primary_journey"))
    for impl in registry.get("implementations", []):
        cap_id = impl.get("capability_id")
        entrypoint = (impl.get("source") or {}).get("entrypoint")
        if entrypoint == module_arg and (cap_id in wired_cap_ids or has_declared_journey):
            return cap_id
    return None


def build_checks(base_url: str, registry: Dict[str, Any], locators: Dict[str, Any],
                  app_dir: Path, app_json: Dict[str, Any]) -> List[dict]:
    """Every check the real assembled app is put through. Each entry:
    id, claim, module (which CAP module slot it verifies, for repair
    targeting), wants (category/output_fields/side_effects, for structural
    matching), is_browser, run(ctx) -> (status, message).

    The host/entry capability (whichever module app.json's own "start"
    command launches -- see _detect_host_capability_id(), no capability id
    is hardcoded here) gets two generic checks: CHK-001 (the homepage
    renders the shared skin's button slots -- true for every assembled app,
    since every app goes through the same skin-laying step in stage one, not
    just this fixture) and CHK-020 (the primary UI journey, driven by the
    template's own declared `primary_journey` -- see stage1_assemble()).

    Every OTHER wired capability whose category is "compute" gets a check
    generated from what it has already declared on the shelf -- its CAP
    record's data_shape.output fields, and its active IMPL's own
    ROUTE/METHOD -- with no branch written for its specific id.

    CHK-002 is the one true exception, and it stays scoped to exactly the
    one host module it has always tested: CAP-0001's fixture app.py bakes a
    create-item route directly into the host module itself (GET+POST
    /api/items on one route), bypassing the shelf route-module convention
    entirely -- a real design smell flagged in round 4's own notes, not one
    to launder into a fake "generic" check. Real capabilities built after
    this round give each data-mutating action its own real route.py module
    (its own ROUTE/METHOD, its own declared output fields), which the
    generic compute-capability loop below already covers with zero changes.
    A host module that doesn't replicate CAP-0001's baked-in-route pattern
    correctly gets no CHK-002, because there is nothing of that shape to
    check -- not because the check was generalized to paper over the
    difference."""
    checks: List[dict] = []

    def add(chk_id, claim, module, wants, is_browser, fn):
        checks.append({"id": chk_id, "claim": claim, "module": module, "wants": wants,
                        "is_browser": is_browser, "run": fn})

    host_cap_id = _detect_host_capability_id(app_json, registry)
    journey = app_json.get("primary_journey")

    if host_cap_id:
        def chk_home(ctx):
            code, body = _http_json("GET", base_url + "/")
            if code != 200:
                return "FAIL", f"homepage returned {code}"
            if "data-slot=" not in str(body):
                return "FAIL", "homepage did not render the expected button slot"
            return "PASS", ""
        add("CHK-001", "a person arrives and sees the entry screen", host_cap_id,
            {"category": "ui", "output_fields": [], "side_effects": []}, False, chk_home)
        # (claim text intentionally generic now -- "entry screen" applies to
        # any host module, not just an item-list one; nothing in the proven
        # suite asserts on the old, item-list-specific wording, confirmed by
        # grep against verify_build.py before this change.)

    if host_cap_id == "CAP-0001":
        def chk_add_item(ctx):
            code, body = _http_json("POST", base_url + "/api/items", {"text": "milk"})
            if code != 201:
                return "FAIL", f"adding an item returned {code}: {body}"
            for field in ("id", "text", "created"):
                if not isinstance(body, dict) or field not in body:
                    return "FAIL", f"adding an item did not return the declared field {field!r}: {body}"
            return "PASS", ""
        add("CHK-002", "adding an item through the API returns the created record", "CAP-0001",
            {"category": "data", "output_fields": ["id", "text", "created"], "side_effects": ["creates_record"]},
            False, chk_add_item)

    # Generic compute-capability checks -- round 4, extended round 7. Nothing
    # here is keyed to a specific CAP id: the route/method are read
    # (statically) off the active shelf IMPL's own module file, and what
    # counts as a pass is read off the CAP's own declared
    # data_shape.output.fields (and, new in round 7, data_shape.input.
    # required -- see below). The check id is derived from the CAP's own
    # number (100 + its digits) so it stays the same for a given capability
    # across any template/run that wires it in, never renumbered by
    # iteration order.
    impl_by_cap_id = {i.get("capability_id"): i for i in registry.get("implementations", [])}
    wired_cap_ids = {b.get("capability_id") for b in registry.get("buttons", [])}
    for cap in registry.get("capabilities", []):
        cap_id = cap.get("id")
        if cap_id not in wired_cap_ids or cap.get("category") != "compute":
            continue
        impl = impl_by_cap_id.get(cap_id)
        if not impl:
            continue
        entrypoint = (impl.get("source") or {}).get("entrypoint")
        if not entrypoint:
            continue
        route, method = _extract_route_meta(app_dir / "modules" / entrypoint)
        if not route or not method:
            continue  # nothing declared to check generically -- not guessed
        wanted_fields = list(cap.get("data_shape", {}).get("output", {}).get("fields", []))
        side_effects = list(cap.get("side_effects", []))
        cap_name = cap.get("name", cap_id)
        cap_num_match = re.match(r"CAP-(\d+)", cap_id)
        chk_num = 100 + int(cap_num_match.group(1)) if cap_num_match else 100
        # Round 7: a capability that DECLARES required input fields (proven
        # first against CAP-0102..CAP-0107's real POST actions, each of
        # which genuinely requires a body -- "create" needs a title,
        # "toggle"/"edit"/"delete" need an id) gets a real request body built
        # from that declaration, instead of always calling with none. The
        # value per field is a generic, deterministic probe -- not invented
        # per capability id: a field literally named "id" (case-insensitive)
        # probes with 1 (the real first record a fresh, empty store would
        # hand out under this session's own id-allocation convention --
        # confirmed against CAP-0102's real route.py, "next_id = max(...,
        # default=0) + 1"), anything else probes with a short, real,
        # human-readable string naming the field itself. This is exactly the
        # same kind of arbitrary-but-real example value the original,
        # Sam-approved fixture used ("milk") -- real data sent to a real
        # endpoint, not a fabricated capability or requirement.
        #
        # Interoperability-upgrade addition: a capability that does real
        # semantic validation on a field (found by real audit: the new
        # Calendar/Event capability genuinely rejects a non-ISO-8601 "start"
        # with a 400, correctly) would otherwise fail this generic check for
        # doing its job right, not for being broken -- the generic string
        # probe is a real value for a generic field, but not for a
        # timestamp. A field recognizably date/time-shaped by name gets a
        # real, valid ISO-8601 probe instead, the same class of targeted
        # fix as the "id" special case above, not a workaround for this one
        # capability.
        required_fields = list(cap.get("data_shape", {}).get("input", {}).get("required", []))

        def _probe_value(field_name: str):
            lname = field_name.lower()
            if "id" in lname:
                return 1
            if lname in ("start", "end", "date", "timestamp") or lname.endswith(("_at", "_date", "_time")):
                return "2026-01-01T00:00:00"
            return f"probe value for {field_name}"

        probe_body = {f: _probe_value(f) for f in required_fields} if required_fields else None

        def make_generic_compute_check(_route=route, _method=method, _fields=wanted_fields,
                                        _cap_id=cap_id, _cap_name=cap_name, _body=probe_body):
            def chk(ctx):
                code, body = _http_json(_method, base_url + _route, _body)
                if not (200 <= code < 300):
                    err = body.get("error") if isinstance(body, dict) else body
                    return "FAIL", f"{_cap_name} ({_cap_id}) returned an error: {err}"
                if not isinstance(body, dict):
                    return "FAIL", f"{_cap_name} ({_cap_id}) returned a non-object response: {body}"
                missing = [f for f in _fields if f not in body]
                if missing:
                    return "FAIL", f"{_cap_name} ({_cap_id}) response missing declared field(s) {missing}: {body}"
                return "PASS", ""
            return chk

        add(f"CHK-{chk_num:03d}", f"{cap_name} responds and returns its declared output fields", cap_id,
            {"category": "compute", "output_fields": wanted_fields, "side_effects": side_effects},
            False, make_generic_compute_check())

    if host_cap_id:
        def chk_browser(ctx):
            from playwright.sync_api import sync_playwright
            errors = []
            with sync_playwright() as p:
                _chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
                browser = p.chromium.launch(executable_path=_chromium_path) if _chromium_path else p.chromium.launch()
                page = browser.new_page()
                # Chromium requests /favicon.ico automatically on every page load, with no app
                # code involved; a host module that (like real-world servers routinely do) has no
                # favicon route gets a 404 for it, which Chromium logs to the console as an
                # "error"-type message. Counting that as a journey failure would fail almost every
                # real app for browser housekeeping that has nothing to do with its actual
                # functionality -- and this specific request does not surface on Playwright's Page
                # network domain at all (confirmed: no "response" event fires for it in this
                # Chromium build), so it cannot be told apart from a real API failure after the
                # fact by matching against observed responses. Fulfilled directly at the network
                # layer instead, before it can ever fail -- this touches only the one well-known
                # browser-requested path; every other request, including a real failing app
                # endpoint, still reaches the real app and still fails this check.
                page.route("**/favicon.ico", lambda route: route.fulfill(status=204, body=""))
                page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(base_url + "/", timeout=10000)
                if journey:
                    # Template-declared, real DOM interaction -- no
                    # hardcoded selector or expected text. The action is
                    # either a real click (action_selector) or a real
                    # keypress in the input itself (action_key, e.g. "Enter"
                    # -- real UIs that submit on Enter, like TodoMVC's own
                    # spec, have no separate button to click at all, and
                    # inventing one just to fit this check would be exactly
                    # the kind of fake accommodation that isn't allowed here).
                    if journey.get("input_selector"):
                        page.fill(journey["input_selector"], journey.get("input_value", ""))
                    if journey.get("action_key"):
                        page.press(journey["input_selector"], journey["action_key"], timeout=5000)
                    else:
                        page.click(journey["action_selector"], timeout=5000)
                    confirm_selector = journey.get("confirm_selector", "body")
                    page.wait_for_selector(confirm_selector, timeout=5000)
                    text = page.inner_text(confirm_selector)
                else:
                    # No template declares primary_journey yet for this host
                    # module -- fall back to the exact original CAP-0001
                    # fixture journey, unchanged, so its proven behavior
                    # never regresses.
                    selector = locators.get("buttons", {}).get(
                        next((b["id"] for b in registry.get("buttons", []) if b["capability_id"] == host_cap_id), ""),
                        {}).get("selector", "#add-item-btn")
                    page.click(selector, timeout=5000)
                    page.wait_for_selector("#item-list li", timeout=5000)
                    text = page.inner_text("#item-list")
                browser.close()
            if errors:
                return "FAIL", f"javascript errors during the journey: {errors}"
            expected = journey["confirm_contains"] if journey else "milk"
            if expected not in text:
                return "FAIL", f"the primary journey did not produce the expected result (saw: {text!r})"
            return "PASS", ""
        # Exact original claim text preserved for the no-journey fallback --
        # verify_build.py's own row 21b asserts on this literal string, and
        # it is real, accurate prose for what that path actually checks.
        claim = ("a person completes the declared primary journey and sees the result"
                 if journey else "a person clicks add item and sees it appear in the list")
        add("CHK-020", claim, host_cap_id,
            {"category": "ui", "output_fields": [], "side_effects": []}, True, chk_browser)

    return checks


def run_layer_one(app_dir: Path, registry: dict, locators: dict, run_id: str) -> dict:
    app_json = json.loads((app_dir / "app.json").read_text(encoding="utf-8"))
    port = _free_port()
    start_cmd = list(app_json["start"]) + ["--port", str(port)]
    base_url = f"http://127.0.0.1:{port}"

    proc = subprocess.Popen(start_cmd, cwd=str(app_dir), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
    try:
        if not _wait_for_health(base_url, app_json.get("health", "/health"), HEALTH_TIMEOUT_SECONDS, proc):
            # Round 7: read the real process's own real stdout/stderr before
            # raising -- a bare "did not start" (e.g. because a real
            # dependency like Flask or Playwright isn't installed in this
            # environment) used to be thrown away unread here, forcing
            # whoever hit it to guess why. Read what's really there instead.
            try:
                proc.terminate()
                real_output, _ = proc.communicate(timeout=5)
            except Exception:
                real_output = ""
            real_output = (real_output or "").strip()
            # Exact original message preserved when there's nothing real to
            # add (verify_build.py's row 13 asserts on this literal line) --
            # the diagnostic only appends when the real process actually
            # printed something, never invents filler text to fit a shape.
            if real_output:
                raise Broken(f"app did not start\nreal process output:\n{real_output[-2000:]}")
            raise Broken("app did not start")

        checks = build_checks(base_url, registry, locators, app_dir, app_json)
        if not checks:
            raise Broken("incomplete record  no checks defined for this registry")

        passed: List[str] = []
        failures: List[dict] = []
        browser_check_passed = False
        browser_check_present = any(c["is_browser"] for c in checks)

        for chk in checks:
            try:
                status, message = chk["run"]({"app_dir": app_dir})
            except Exception as e:
                status, message = "FAIL", f"check raised {type(e).__name__}: {e}"
            if status == "PASS":
                print(f"PASS  {chk['claim']}")
                passed.append(chk["id"])
                if chk["is_browser"]:
                    browser_check_passed = True
            elif status == "SKIP":
                print(f"SKIP  {chk['claim']}  ({message})")
            else:
                print(f"FAIL  {chk['claim']}  {message}")
                # is_browser is carried on the failure record (round 5) so
                # anything reading run_ledger.jsonl/reports afterward -- e.g.
                # readiness_and_library.py's BROWSER_TEST_FAILED vs
                # RUNTIME_FAILED classification -- can tell a failing browser
                # journey apart from an ordinary check failure without
                # re-deriving it by guessing at claim text.
                failures.append({"run": run_id, "check": chk["id"], "claim": chk["claim"],
                                  "message": message, "module": chk["module"], "wants": chk["wants"],
                                  "is_browser": chk["is_browser"]})

        report = {
            "run": run_id, "checks_passed": passed, "checks_failed": failures,
            "browser_check_present": browser_check_present, "browser_check_passed": browser_check_passed,
        }
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / f"{run_id}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

        total = len(checks)
        print(f"{len(passed)}/{total} checks passed — {'PASS' if not failures else 'FAIL'}")
        return report
    finally:
        # Round 7: the health-check-failure path above may already have
        # terminated and reaped this same real process -- terminate()/wait()
        # on an already-exited process is harmless on every platform this
        # runs on, but guarded anyway so a real, already-handled failure
        # can never be masked by a second, unrelated exception here.
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass


def find_shelf_part_by_alias(alias: str) -> Optional[Tuple[str, dict, Path]]:
    """§7.1: a shelf-part alias ("name@version") resolves through
    shelf/aliases.json to one CAP/IMPL. Returns (impl id, §3.7 record,
    payload dir) if that IMPL exists and is usable, else None."""
    impl_id = read_shelf_aliases().get(alias)
    if not impl_id:
        return None
    got = read_shelf_impl(impl_id)
    if got is None:
        return None
    meta, payload_dir = got
    if not impl_is_usable(meta):
        return None
    return meta["id"], meta, payload_dir


def find_structural_matches(wants: dict, exclude_cap: Optional[str]) -> List[Tuple[str, dict, Path]]:
    """Sweeps the WHOLE shelf for every APPROVED, active CAP (other than the
    one already wired) whose category/output_fields/side_effects match
    `wants`, with an approved active IMPL, and returns every match found --
    not just the first. Which one (if any) is safe to apply automatically is
    a judgment call made by the caller, not by this sweep: two shelf parts
    that structurally tie are exactly the kind of thing Bible rule 4 says not
    to silently guess between."""
    caps_root = SHELF_DIR / "capabilities"
    matches: List[Tuple[str, dict, Path]] = []
    if not caps_root.is_dir():
        return matches
    for cap_file in sorted(caps_root.glob("CAP-*.json")):
        cap = read_shelf_cap(cap_file.stem)
        if cap is None or cap.get("id") == exclude_cap or not cap_is_usable(cap):
            continue
        shape = cap.get("data_shape", {}).get("output", {})
        if cap.get("category") != wants.get("category"):
            continue
        if set(shape.get("fields", [])) != set(wants.get("output_fields", [])):
            continue
        if set(cap.get("side_effects", [])) != set(wants.get("side_effects", [])):
            continue
        got = active_impl_for(cap)
        if got is None:
            continue
        meta, payload_dir = got
        matches.append((meta["id"], meta, payload_dir))
    return matches


def run_layer_two(failure: dict, app_dir: Path) -> Optional[dict]:
    message = failure["message"]

    for pattern, alias in FAILURE_PATTERN_MAP.items():
        if pattern in message:
            found = find_shelf_part_by_alias(alias)
            if found:
                part_id, meta, payload_dir = found
                _copy_payload(payload_dir, app_dir / "modules")
                print(f"      repaired by shelf part {alias} -> {part_id} (layer 2, pattern)")
                return {"part": alias, "resolves_to": part_id, "matched_by": "pattern"}

    matches = find_structural_matches(failure.get("wants", {}), exclude_cap=failure["module"])
    if len(matches) > 1:
        named = ", ".join(f"{alias_for(pid)} -> {pid}" for pid, meta, _ in matches)
        msg = (f"{failure['check']}: ambiguous structural repair -- "
               f"{len(matches)} shelf parts match equally ({named})")
        print(f"HELD  {msg}  awaiting approval")
        raise Held(f"{msg}  awaiting approval")
    if matches:
        part_id, meta, payload_dir = matches[0]
        alias = alias_for(part_id)
        _copy_payload(payload_dir, app_dir / "modules")
        print(f"      repaired by shelf part {alias} -> {part_id} (layer 2, structural)")
        return {"part": alias, "resolves_to": part_id, "matched_by": "structural"}

    return None


def call_layer3_model(prompt: str) -> Tuple[bool, str]:
    """Real POST to LAYER3_ENDPOINT, naming LAYER3_MODEL in the body and
    sending LAYER3_CREDENTIAL as a bearer token (never argv, never printed).
    Nothing here is specific to any provider: the endpoint, the model name
    and the credential are all config-block values Sam sets. Returns
    (reached, body_or_error). Reached means the endpoint answered with a
    2xx; the raw response body is returned as-is. If the endpoint cannot be
    reached or refuses, this says so honestly rather than substituting a
    fabricated response (Bible rule 1)."""
    body = json.dumps({
        "model": LAYER3_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        LAYER3_ENDPOINT,
        data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LAYER3_CREDENTIAL}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return True, resp.read().decode("utf-8", "replace")
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def run_layer_three(failure: dict, run_id: str) -> dict:
    check_id = failure["check"]
    message = failure["message"]

    prior_gap = find_prior_gap_for_check(check_id)
    if prior_gap:
        raise Broken(f"repeated gap  {prior_gap} was raised twice")

    gap_id = next_gap_id()
    missing = f"{check_id} needs behaviour the shelf does not have: {message}"
    proves_it = f"{failure['claim']} passes for real"
    gap_record = {
        "gap": gap_id, "run": run_id, "check": check_id, "message": message,
        "missing": missing, "proves_it": proves_it,
        "candidates_tried": 0, "candidates_passed": 0,
    }
    append_ledger(gap_record)
    print(f"      gap classified  {gap_id}  {missing}")

    if not ALLOW_LAYER3:
        print(f"HELD  {gap_id}  {missing}  layer three disabled")
        raise Held(f"{gap_id}  {missing}  layer three disabled")

    tried = 0
    reached_model = False
    unreachable_detail = ""
    for framing in CANDIDATE_FRAMINGS:
        tried += 1
        prompt = (
            f"Framing: {framing}\n"
            f"Gap: {gap_id}\nCheck: {check_id}\nFailure message: {message}\n"
            f"What the missing part must do: {missing}\n"
            f"What proves it exists: {proves_it}\n"
            "Return only the source of the fix."
        )
        reached, result = call_layer3_model(prompt)
        if reached:
            reached_model = True
            # A real candidate would be applied to a scratch copy of the app
            # and driven through run_layer_one() again; kept only if it
            # passes the browser check (Bible rule 2). No candidate is
            # trusted on the model's word alone.
        else:
            unreachable_detail = result

    gap_record["candidates_tried"] = tried
    if not reached_model:
        note = f"model unreachable: {unreachable_detail}"
        print(f"HELD  {gap_id}  {missing} ({tried} candidates tried)  {note}")
        raise Held(f"{gap_id}  {missing} ({tried} candidates tried)")

    print(f"HELD  {gap_id}  {missing} ({tried} candidates tried)")
    raise Held(f"{gap_id}  {missing} ({tried} candidates tried)")


def stage2_prove(app_id: str, app_dir: Path, registry: dict, locators: dict) -> Tuple[str, int]:
    passed_checks_history: set = set()
    repair_history: List[Tuple[str, str, str]] = []
    restarts = 0

    while True:
        run_id = next_run_id()
        print(f"\n{run_id}")
        report = run_layer_one(app_dir, registry, locators, run_id)

        failures = report["checks_failed"]
        passed = report["checks_passed"]

        if not failures:
            if not report["browser_check_present"]:
                append_ledger({"run": run_id, "app": app_id, "outcome": "BROKEN",
                                "checks_passed": passed, "checks_failed": [], "browser_check_passed": False})
                raise Broken("no browser check present in the suite")
            if not report["browser_check_passed"]:
                append_ledger({"run": run_id, "app": app_id, "outcome": "BROKEN",
                                "checks_passed": passed, "checks_failed": [], "browser_check_passed": False})
                raise Broken("incomplete record  browser check not verified")
            append_ledger({"run": run_id, "app": app_id, "outcome": "BUILT",
                            "checks_passed": passed, "checks_failed": [], "browser_check_passed": True})
            # Only a BUILT run writes "active" (§6.2: registered and available
            # for use) -- in the canonical registry and in this app's own.
            set_app_status(app_id, "active")
            registry["applications"][0]["status"] = "active"
            (app_dir / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
            print(f"{run_id}   build finished")
            print("BUILT")
            return "BUILT", 0

        failed_ids = {f["check"] for f in failures}
        regressed = passed_checks_history.intersection(failed_ids)
        if regressed:
            append_ledger({"run": run_id, "app": app_id, "outcome": "BROKEN",
                            "checks_passed": passed, "checks_failed": failures, "browser_check_passed": False})
            raise Broken(f"regression  {', '.join(sorted(regressed))}")
        passed_checks_history.update(passed)

        target = failures[0]
        append_ledger({"run": target["run"], "check": target["check"], "claim": target["claim"],
                        "message": target["message"]})

        if restarts >= MAX_RESTARTS:
            history = ", ".join(f"{c} via {p} ({r})" for r, c, p in repair_history)
            append_ledger({"run": run_id, "app": app_id, "outcome": "BROKEN",
                            "checks_passed": passed, "checks_failed": failures, "browser_check_passed": False})
            raise Broken(f"restart ceiling  {history}")

        repair = run_layer_two(target, app_dir)
        if repair:
            chk_id, part = target["check"], repair["part"]
            prior = [p for r, c, p in repair_history if c == chk_id and p == part]
            if prior:
                runs = ", ".join(r for r, c, p in repair_history if c == chk_id and p == part)
                raise Broken(f"loop guard  {chk_id} still fails after {part} (applied {runs})")

            restarts += 1
            next_id = f"RUN-{int(run_id.split('-')[1]) + 1:04d}"
            repair_history.append((run_id, chk_id, part))
            append_ledger({"run": run_id, "check": chk_id, "part": part,
                            "resolves_to": repair["resolves_to"], "matched_by": repair["matched_by"],
                            "restarted_as": next_id})
            continue

        run_layer_three(target, run_id)  # always raises Held or Broken


# ------------------------------------------------------------------------------
# STAGE THREE -- readiness classification + library promotion (round 6)
# ------------------------------------------------------------------------------
# Master Spec's 12-value readiness vocabulary (REFERENCE_ONLY ... READY) as a
# READ-ONLY translation of this file's own proven registry.json/ledger/reports
# state -- it does not change build.py's own §6.2 status vocabulary, which
# stays the source of truth -- plus one genuinely new behavior, library
# promotion (Section 19's actual gap: nothing before this point curates a
# "library" subset of builds/APP-nnn/). This was round 5's readiness_and_
# library.py, folded into this one file this round so build.py stays what
# Sam decided it should be on 2026-09-11: ONE script, every stage.
READINESS_STATES = [
    "REFERENCE_ONLY", "HARVESTED", "TEMPLATE_COMPLETE", "CAPABILITIES_UNBOUND",
    "CAPABILITIES_READY", "BUILD_FAILED", "BUILT", "START_FAILED",
    "RUNTIME_FAILED", "BROWSER_TEST_FAILED", "PROVEN", "LIBRARY_STORED", "READY",
]


def _read_reports() -> Dict[str, dict]:
    """Every reports/RUN-*.json under REPORTS_DIR, keyed by run id.
    run_layer_one() writes one of these unconditionally for every run that
    got past the health-check wait and had at least one check defined --
    before stage2_prove() decides what to do with the result. That makes
    this directory a more complete per-run record than run_ledger.jsonl's
    own "outcome" lines, which several real stage2_prove()/run_layer_two()/
    run_layer_three() exit paths (loop guard, repeated gap, layer-three-
    disabled/exhausted HELD) never write -- confirmed by reading those
    functions directly, not assumed."""
    out: Dict[str, dict] = {}
    if not REPORTS_DIR.is_dir():
        return out
    for f in REPORTS_DIR.glob("RUN-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("run"):
            out[data["run"]] = data
    return out


def _classify_failed_checks(failed: List[dict], browser_check_passed: bool, source_label: str) -> Tuple[str, str]:
    """A failing check tagged is_browser wins over an ordinary one, because a
    person could not complete the journey regardless of what else also
    failed -- shared by both call sites below (an app with an "outcome"
    ledger record, and one without) so the rule is identical either way."""
    browser_failed = [f.get("check") for f in failed if f.get("is_browser")]
    if browser_failed:
        return "BROWSER_TEST_FAILED", f"{source_label} has a failing browser-driven check that no repair resolved: {browser_failed}"
    if failed:
        return "RUNTIME_FAILED", f"{source_label} has unresolved check failure(s) that no repair resolved: {[f.get('check') for f in failed]}"
    if not browser_check_passed:
        return "BROWSER_TEST_FAILED", f"{source_label} had no failing checks but the browser check was absent or unverified"
    return "RUNTIME_FAILED", f"{source_label} did not reach BUILT for a reason not covered by the checks above -- see it directly"


def _cap_is_bound(cap_id: str) -> bool:
    """Exactly stage1_assemble()'s own real binding check (step 5) --
    reused, not reimplemented, so "readiness says bound" and "assembly
    would actually succeed" can never drift apart."""
    cap = read_shelf_cap(cap_id)
    if cap is None or not cap_is_usable(cap):
        return False
    return active_impl_for(cap) is not None


def compute_readiness(app_type: str, app_id: Optional[str] = None) -> Tuple[str, str]:
    """Returns (state, reason) -- state is always one of READINESS_STATES.
    Reads only files this script itself already writes (or their absence);
    invents nothing. `app_id` is required to resolve any state past
    CAPABILITIES_READY, because template/capability readiness is per app
    TYPE but a build outcome is per app INSTANCE -- the two aren't the same
    axis, and this function refuses to collapse them into a guess."""
    slug = app_type.lower().replace(" ", "_").replace("/", "_")
    tpl_file = TEMPLATES_DIR / f"{slug}.json"
    if not tpl_file.is_file():
        return "REFERENCE_ONLY", "no template file exists yet for this app type (harvest may exist elsewhere, not checked here)"
    try:
        tpl = json.loads(tpl_file.read_text(encoding="utf-8"))
    except Exception:
        return "REFERENCE_ONLY", "a template file exists but is not readable JSON"
    if not tpl.get("accepted", False):
        return "HARVESTED", "a template file exists but is not marked accepted"

    # Master Spec Section 18 lists TEMPLATE_COMPLETE as its own state between
    # HARVESTED and CAPABILITIES_UNBOUND/READY. In this data model the two
    # are the same instant: a template's required_capabilities and each
    # slot's target_capability are already part of the accepted template
    # record, so capability binding is already computable the moment
    # "accepted" is true -- there is no on-disk state where a template is
    # complete but binding is still unknown. This function reports the
    # furthest state it can actually determine rather than inventing a pause
    # point at TEMPLATE_COMPLETE. Flagged as a real design choice, not a
    # silent omission.
    required = tpl.get("required_capabilities", [])
    unbound = [c for c in required if not _cap_is_bound(c)]
    if unbound:
        return "CAPABILITIES_UNBOUND", f"required capabilities not bound to an approved active implementation: {unbound}"

    if app_id is None:
        return "CAPABILITIES_READY", "template accepted and every required capability is bound; no app_id given, so no build instance to report on"

    canon = read_canonical_registry()
    app_record = next((a for a in canon.get("applications", []) if a.get("id") == app_id), None)
    if app_record is None:
        return "CAPABILITIES_READY", f"template and capabilities ready, but {app_id} is not in the canonical registry (never allocated)"

    status = app_record.get("status")
    assembled = (BUILDS_DIR / app_id / "app.json").is_file()

    if status == "void":
        return "BUILD_FAILED", "canonical registry marks this allocation void -- assembly failed or its contract match was rejected before an app ever started"

    ledger = _read_ledger_lines()
    app_outcomes = [r for r in ledger if r.get("app") == app_id and "outcome" in r]

    if status == "active":
        # A BUILT run always sets canonical status active, and BUILT already
        # means the real browser check passed for real -- that already
        # satisfies the Master Spec's own definition of PROVEN.
        return "PROVEN", "canonical registry status is active -- build.py reached BUILT, meaning a real browser-driven check already passed"

    # status == "candidate": assembled, at least attempted, not (yet) proven.
    if not app_outcomes:
        if not assembled:
            return "BUILD_FAILED", "canonical status is candidate but assembly never completed (no app.json) -- inconsistent state, or assembly is still in progress"

        # Assembled, but no app-tagged "outcome" ledger record exists. Two
        # real cases land here (confirmed by reading the code, not assumed):
        # true START_FAILED (run_layer_one() raised before it ever built a
        # report dict -- neither a ledger outcome nor a reports/RUN-*.json
        # exists), or a failing-check run that exited via loop guard,
        # repeated gap, or a layer-three HELD/BROKEN (none of which write an
        # outcome record, but DID get a reports/RUN-*.json written first).
        reports = _read_reports()
        claimed_elsewhere = {r.get("run") for r in ledger
                              if r.get("outcome") and r.get("app") and r.get("app") != app_id}
        candidate_reports = {rid: rep for rid, rep in reports.items() if rid not in claimed_elsewhere}
        if not candidate_reports:
            return "START_FAILED", "the app was assembled (app.json exists) but no run ever produced a checks report -- consistent with the health check never returning 200 before this script's own report-writing point"

        latest_run = sorted(candidate_reports,
                             key=lambda r: int(m.group(1)) if (m := _RUN_RE.match(r)) else -1)[-1]
        latest = candidate_reports[latest_run]
        return _classify_failed_checks(latest.get("checks_failed", []), latest.get("browser_check_passed", False),
                                        f"the latest recorded run ({latest_run}, from reports/ -- no ledger outcome was ever written for it)")

    last = app_outcomes[-1]
    return _classify_failed_checks(last.get("checks_failed", []), bool(last.get("browser_check_passed")),
                                    f"the most recent run ({last.get('run')})")


def promote_to_library(app_id: str) -> Tuple[bool, str]:
    """The Section 19 gap: nothing above this point in the file has a
    library/ promotion step. Copies a build's own proof (registry.json,
    app.json, locators.json, modules/, skin.json, and every reports/RUN-
    *.json whose ledger entry names this app_id) into library/<app_id>/, but
    ONLY when the canonical registry already says this app_id is "active" (a
    real BUILT run) -- it never promotes a candidate or void app, and never
    re-derives a verdict itself."""
    canon = read_canonical_registry()
    app_record = next((a for a in canon.get("applications", []) if a.get("id") == app_id), None)
    if app_record is None:
        return False, f"{app_id} is not in the canonical registry"
    if app_record.get("status") != "active":
        return False, f"{app_id} is {app_record.get('status')!r}, not active -- only a proven (BUILT) app may be promoted"

    src = BUILDS_DIR / app_id
    if not src.is_dir():
        return False, f"{app_id} has no build directory to promote from"

    dest = Path(LIBRARY_SUBDIR) / app_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    ledger = _read_ledger_lines()
    evidence_runs = sorted({r["run"] for r in ledger if r.get("app") == app_id and "outcome" in r})
    evidence_dir = dest / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    for run_id in evidence_runs:
        report = REPORTS_DIR / f"{run_id}.json"
        if report.is_file():
            shutil.copy2(report, evidence_dir / report.name)

    marker = {
        "app_id": app_id, "promoted_from": str(src), "evidence_runs": evidence_runs,
        "canonical_status_at_promotion": "active",
    }
    (dest / PROMOTION_MARKER).write_text(json.dumps(marker, indent=2), encoding="utf-8")
    return True, f"promoted {app_id} to {dest} with {len(evidence_runs)} evidence run(s)"


def compute_readiness_with_library(app_type: str, app_id: str) -> Tuple[str, str]:
    """Same as compute_readiness(), but also checks for LIBRARY_STORED/READY
    -- both require compute_readiness() to have already reached PROVEN, so
    this never reports a library state for an app that isn't proven."""
    state, reason = compute_readiness(app_type, app_id)
    if state != "PROVEN":
        return state, reason
    lib_dir = Path(LIBRARY_SUBDIR) / app_id
    marker_file = lib_dir / PROMOTION_MARKER
    if not marker_file.is_file():
        return "PROVEN", "proven but not yet promoted to the library"
    required_evidence = ["registry.json", "app.json", "locators.json"]
    missing = [f for f in required_evidence if not (lib_dir / f).is_file()]
    if missing or not any((lib_dir / "evidence").glob("*.json")):
        return "LIBRARY_STORED", f"stored but evidence incomplete: missing {missing or 'no evidence run reports'}"
    return "READY", "promoted, with registry/app/locators and at least one evidence run report present"


def stage3_readiness_and_promote(app_id: Optional[str]) -> None:
    """Called by main() after stage two, on every path (BUILT, HELD,
    BROKEN) -- prints the Master Spec readiness line for this run, and, only
    when this run actually reached BUILT, promotes it to the library
    automatically (build.py's own stage two already checked every gate
    Section 19 asks for except evidence_saved/registry_updated, which this
    stage now closes). Never runs when stage one never allocated an app_id."""
    if not app_id:
        return
    choice = None
    try:
        choice = json.loads(CHOICE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    app_type = (choice or {}).get("app_type")
    if not app_type:
        print("readiness  skipped -- choice.json's app_type could not be re-read")
        return

    canon = read_canonical_registry()
    app_record = next((a for a in canon.get("applications", []) if a.get("id") == app_id), None)
    if app_record is not None and app_record.get("status") == "active":
        ok, msg = promote_to_library(app_id)
        print(("promoted  " if ok else "promotion refused  ") + msg)

    state, reason = compute_readiness_with_library(app_type, app_id)
    print(f"readiness  {state}  --  {reason}")


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("--readiness", "--promote"):
        return _cli_dispatch(sys.argv[1:])

    if ALLOW_LAYER3:
        if not LAYER3_MODEL or not LAYER3_MODEL.strip():
            print("BROKEN  missing setting  LAYER3_MODEL")
            return 2
        if not LAYER3_CREDENTIAL or not LAYER3_CREDENTIAL.strip():
            print("BROKEN  missing setting  LAYER3_CREDENTIAL")
            return 2
        if not LAYER3_ENDPOINT or not LAYER3_ENDPOINT.strip():
            print("BROKEN  missing setting  LAYER3_ENDPOINT")
            return 2

    try:
        app_id, app_dir, registry, locators = stage1_assemble()
    except Held:
        return 1
    except Broken:
        return 2

    exit_code = 2
    try:
        verdict, code = stage2_prove(app_id, app_dir, registry, locators)
        exit_code = code
    except Held:
        # Not proven: stays a candidate (§6.2). The number is kept, never reused.
        set_app_status(app_id, "candidate")
        exit_code = 1
    except Broken as b:
        print(f"BROKEN  {b}")
        set_app_status(app_id, "candidate")
        exit_code = 2

    # Stage three -- runs on every path (BUILT, HELD, BROKEN) now that stage
    # one has allocated a real app_id, so every run ends with a Master-Spec-
    # vocabulary readiness line, not just successful ones.
    stage3_readiness_and_promote(app_id)
    return exit_code


def _cli_dispatch(argv: List[str]) -> int:
    """Standalone readiness/promotion queries, without running a build --
    `python3 build.py --readiness <app_type> [app_id]` or
    `python3 build.py --promote <app_id>`. Reads the same on-disk state a
    normal run would; writes nothing except --promote's own copy step."""
    if argv[0] == "--promote":
        if len(argv) < 2:
            print("usage: build.py --promote <app_id>")
            return 2
        ok, msg = promote_to_library(argv[1])
        print(("PROMOTED  " if ok else "REFUSED  ") + msg)
        return 0 if ok else 1

    if argv[0] == "--readiness":
        if len(argv) < 2:
            print("usage: build.py --readiness <app_type> [app_id]")
            return 2
        app_type = argv[1]
        app_id = argv[2] if len(argv) > 2 else None
        if app_id:
            state, reason = compute_readiness_with_library(app_type, app_id)
        else:
            state, reason = compute_readiness(app_type)
        print(f"{state}  --  {reason}")
        return 0

    print(f"unknown option {argv[0]!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
