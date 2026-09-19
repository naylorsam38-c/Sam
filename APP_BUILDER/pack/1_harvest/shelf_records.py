#!/usr/bin/env python3
"""
shelf_records.py  --  step 5b of the harvest chain.

harvest_parts.py puts the real harvested code on the shelf at
    shelf/<slug>/<CAP-id>/source.py

build.py does not read that layout. It reads:
    shelf/capabilities/<CAP-id>.json                 -- the §3.6 record
    shelf/implementations/<CAP-id>/<IMPL-id>.json    -- the §3.7 record
    shelf/implementations/<CAP-id>/<IMPL-id>/        -- the payload directory
    shelf/aliases.json                               -- "name@version" -> CAP/IMPL

This script writes the three record files and the alias map. Every value it
writes is read off the filled form or off the harvest source block -- nothing
is invented, and no value is taken from any previously generated library.

It does NOT write the payload module. See PAYLOAD GAP at the bottom of this
file: that step needs a decision, not a script.

Run:
    python3 shelf_records.py forms/event-ticketing.form.json
    python3 shelf_records.py forms/event-ticketing.form.json --check
"""

# ===========================================================================
# RULES / CONFIG  --  edit these, not the logic below.
# ===========================================================================

# Where filled forms are read from, relative to this file.
FORMS_DIR = "forms"

# Where the harvested code already sits (written by harvest_parts.py).
# Change this if you move the harvest output somewhere else.
HARVEST_SHELF_DIR = "shelf"

# Where build.py expects to read records from. This must match build.py's own
# SHELF_DIR setting or build.py will not find anything this script writes.
BUILD_SHELF_DIR = "shelf"

# The implementation number given to the first implementation of a capability.
# A second implementation of the same capability would be IMPL-02, and so on.
# Changing this renumbers every implementation this script writes.
FIRST_IMPL_NUMBER = 1

# The filename the payload module is expected to use inside its payload
# directory. build.py reads source.entrypoint as a path under the app's
# modules/ folder, so the entrypoint written is "<CAP-id>/<this value>".
# Change this only if the host loader is changed to look for a different file.
PAYLOAD_MODULE_FILENAME = "route.py"

# The form has no per-capability category field, and build.py compares
# category when it sweeps the shelf for a reusable part. This setting decides
# what goes in that field:
#   "app_type"  -- every capability from this app gets the form's app_type
#                  (widest match inside one app, no match across apps)
#   "engine"    -- every capability gets the form's engine, e.g. Flask
#   "<literal>" -- anything else is written verbatim into every record
# Changing this changes which shelf parts build.py will consider
# interchangeable when it looks for a replacement.
CATEGORY_SOURCE = "app_type"

# Who approved admission, written into the qualification block. build.py
# refuses a capability whose qualification status is not approved.
APPROVED_BY = "Sam"

# The approval references written into the two record types. These are labels
# that appear in the records; changing them changes only the label.
CAP_APPROVAL_REF = "APPROVAL-CAP-HARVEST"
IMPL_APPROVAL_REF = "APPROVAL-IMPL-HARVEST"

# If true, the alias map gets an entry per capability, keyed
# "<cap name>@<version>". build.py's repair path resolves aliases to find a
# replacement part. Set false to write no aliases at all.
WRITE_ALIASES = True

# If true, refuse to write a record for any capability whose harvested source
# is not actually on the shelf. Set false to write records ahead of the code
# (not recommended -- build.py will then fail later instead of now).
REQUIRE_HARVESTED_SOURCE = True

# If true, overwrite record files that already exist. If false, an existing
# record is left alone and reported as skipped.
OVERWRITE_EXISTING = True

# If true, print what would be written and write nothing.
DRY_RUN = False

# ===========================================================================
# END CONFIG
# ===========================================================================

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# build.py's own key sets, §3.6 and §3.7. These are an EXACT top-level key
# match in build.py's verify_registry_invariants -- an extra or missing key is
# a hard failure there, so they are reproduced here verbatim as the target.
CAP_RECORD_KEYS = ("id", "name", "category", "status", "data_shape", "dependencies",
                   "permissions", "side_effects", "error_contract", "implementations",
                   "qualification", "attaches_to")
# "attaches_to" added 2026-09-19 -- must match build.py's CAP_RECORD_KEYS
# exactly, same reason the comment above already gives for the rest of
# this tuple.
IMPL_RECORD_KEYS = ("id", "capability_id", "status", "release", "source",
                    "dependencies", "tests", "rollback")


def fail(msg):
    print(f"REFUSED  {msg}")
    sys.exit(1)


def load_form(arg):
    p = Path(arg)
    if not p.is_file():
        p = HERE / FORMS_DIR / Path(arg).name
    if not p.is_file():
        fail(f"form not found  {arg}")
    return json.loads(p.read_text(encoding="utf-8")), p


def category_for(form):
    if CATEGORY_SOURCE == "app_type":
        v = form.get("app_type", "")
    elif CATEGORY_SOURCE == "engine":
        v = (form.get("harvest_source") or {}).get("framework", "")
    else:
        return CATEGORY_SOURCE
    if not v:
        fail(f"CATEGORY_SOURCE is {CATEGORY_SOURCE!r} but the form's field is blank")
    return v


def cap_record(cap, form, impl_id):
    """Builds the §3.6 record. Every value comes from the form."""
    ds = cap.get("data_shape") or {}
    return {
        "id": cap["cap_id"],
        "name": cap["cap_name"],
        "category": category_for(form),
        "status": "active",
        "data_shape": {
            "input": {
                "required": list(ds.get("required_input_fields", [])),
                "types": dict(ds.get("input_types", {})),
            },
            "output": {
                "fields": list(ds.get("output_fields", [])),
                "types": dict(ds.get("output_types", {})),
            },
            "nullable": list(ds.get("nullable_fields", [])),
            "requires_auth": bool(ds.get("requires_auth", False)),
            "security_constraints": dict(ds.get("security_constraints", {})),
            "contract_version": ds.get("contract_version", "2.0"),
            "data_access": [dict(a) for a in ds.get("data_access", [])],
            "context_fields": list(ds.get("context_fields", [])),
        },
        "dependencies": list(ds.get("dependencies", [])),
        "permissions": list(ds.get("permissions", [])),
        "side_effects": list(ds.get("side_effects", [])),
        "error_contract": {
            "error_codes": list((ds.get("error_contract") or {}).get("error_codes", []))
        },
        "implementations": [impl_id],
        "qualification": {
            "status": "approved",
            "approved_by": APPROVED_BY,
            "approval_ref": CAP_APPROVAL_REF,
        },
        # Section 5: attach-point names this capability needs, by name only
        # -- never an application identity. Read straight off the form's
        # own capability entry; empty list if the form names none (every
        # capability harvested before this axis existed has none, and
        # nothing about that changes how it matches).
        "attaches_to": list(cap.get("attaches_to", [])),
    }


def impl_record(cap, form, impl_id):
    """Builds the §3.7 record. release.commit is the REAL upstream commit the
    code was cut from -- that is what makes this record traceable back to
    source, and what distinguishes a harvested part from a generated one."""
    ds = cap.get("data_shape") or {}
    hs = form.get("harvest_source") or {}
    commit = hs.get("commit", "")
    if not commit:
        fail("harvest_source.commit is blank -- refusing to record a part with no pinned commit")
    return {
        "id": impl_id,
        "capability_id": cap["cap_id"],
        "status": "active",
        "release": {
            "version": ds.get("min_version", "1.0.0"),
            "commit": commit,
            "approved": True,
            "approval_ref": IMPL_APPROVAL_REF,
        },
        "source": {
            "repository": hs.get("repo_name", ""),
            "path": impl_id,
            "entrypoint": f"{cap['cap_id']}/{PAYLOAD_MODULE_FILENAME}",
        },
        "dependencies": list(ds.get("dependencies", [])),
        "tests": [],
        "rollback": {"previous_version": None},
    }


def check_shape(record, keys, kind):
    got, want = set(record.keys()), set(keys)
    if got != want:
        extra, missing = got - want, want - got
        bits = []
        if extra:
            bits.append(f"extra {sorted(extra)}")
        if missing:
            bits.append(f"missing {sorted(missing)}")
        fail(f"{kind} record shape wrong -- {'; '.join(bits)}")


def main():
    if len(sys.argv) < 2:
        fail("usage: shelf_records.py <form.json> [--check]")
    check_only = "--check" in sys.argv
    form, form_path = load_form(sys.argv[1])

    slug = form.get("app_slug", "")
    if not slug:
        fail("form has no app_slug")
    caps = form.get("capabilities") or []
    if not caps:
        fail("form has no capabilities")

    harvest_root = HERE / HARVEST_SHELF_DIR / slug
    shelf = HERE / BUILD_SHELF_DIR
    caps_out = shelf / "capabilities"
    impls_out = shelf / "implementations"

    written, skipped, problems = [], [], []
    aliases = {}

    for cap in caps:
        cid = cap.get("cap_id", "")
        if not cid:
            problems.append("a capability has no cap_id")
            continue

        src = harvest_root / cid / "source.py"
        if REQUIRE_HARVESTED_SOURCE and not src.is_file():
            problems.append(f"{cid}  no harvested source at {src.relative_to(HERE)}")
            continue

        impl_id = f"{cid}/IMPL-{FIRST_IMPL_NUMBER:02d}"
        c_rec = cap_record(cap, form, impl_id)
        i_rec = impl_record(cap, form, impl_id)
        check_shape(c_rec, CAP_RECORD_KEYS, "capability")
        check_shape(i_rec, IMPL_RECORD_KEYS, "implementation")

        if WRITE_ALIASES:
            aliases[f"{cap['cap_name']}@{i_rec['release']['version']}"] = impl_id

        c_file = caps_out / f"{cid}.json"
        i_file = impls_out / f"{impl_id}.json"
        payload_dir = impls_out / impl_id

        if not OVERWRITE_EXISTING and c_file.is_file():
            skipped.append(cid)
            continue
        if check_only or DRY_RUN:
            written.append(cid)
            continue

        c_file.parent.mkdir(parents=True, exist_ok=True)
        i_file.parent.mkdir(parents=True, exist_ok=True)
        payload_dir.mkdir(parents=True, exist_ok=True)
        c_file.write_text(json.dumps(c_rec, indent=2) + "\n", encoding="utf-8")
        i_file.write_text(json.dumps(i_rec, indent=2) + "\n", encoding="utf-8")
        written.append(cid)

    if aliases and not (check_only or DRY_RUN):
        # build.py's read_shelf_aliases() parses a LIST under the key
        # "aliases", each entry {"alias": ..., "impl_id": ...}. A flat
        # name->id map is silently read as empty, so the shape matters.
        af = shelf / "aliases.json"
        existing = {}
        if af.is_file():
            try:
                prior = json.loads(af.read_text(encoding="utf-8"))
                for e in prior.get("aliases", []):
                    if isinstance(e, dict) and e.get("alias") and e.get("impl_id"):
                        existing[e["alias"]] = e["impl_id"]
            except Exception:
                existing = {}
        existing.update(aliases)
        out = {"aliases": [{"alias": a, "impl_id": i} for a, i in sorted(existing.items())]}
        af.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    verb = "would write" if (check_only or DRY_RUN) else "wrote"
    print(f"{verb} records for {len(written)}/{len(caps)} capabilities  app={slug}")
    if skipped:
        print(f"skipped (already present): {', '.join(skipped)}")
    for p in problems:
        print(f"PROBLEM  {p}")
    if aliases:
        print(f"aliases: {len(aliases)}")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()


# ===========================================================================
# PAYLOAD GAP  --  read this before assuming the shelf is finished.
# ===========================================================================
# This script writes the records. It does not write
#     shelf/implementations/<CAP>/<IMPL>/<CAP>/route.py
# which is the file build.py copies into the app and the host actually runs.
#
# The host expects that module to be:
#     ROUTE   = '<path>'            -- plain string literal, read by AST
#     METHOD  = '<GET|POST>'        -- plain string literal, read by AST
#     DATA_FILE_NAME = '<file>'     -- if it stores anything
#     def handle(request): ...      -- returns (status, dict)
#     and all storage through _shared from modules/CAP-0000/shared_lib.py
#
# The harvested Indico code is not that shape. RHLogin is an Indico RH
# subclass bound to Indico's own base class, session machinery, WTForms and
# SQLAlchemy models against PostgreSQL. It cannot be translated into the
# module above by any mechanical rule -- the storage layer, the session
# layer and the request layer are all different.
#
# So the decision is which of these the system does, and it is not this
# script's to make:
#   A. Adapt each harvested part by hand into the host module contract.
#   B. Change the host to run the harvested framework as-is.
#   C. Harvest only from repos whose parts already fit the host contract.
# ===========================================================================
