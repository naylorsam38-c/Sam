#!/usr/bin/env python3
"""
harvest_parts.py -- the copy step. Puts real code on the shelf.

This is the step that was missing. The harvest command brings back addresses
(file, symbol, line range) inside a filled form. assign_numbers.py turns those
into CAP numbers and a tree. Nothing, until now, went and fetched the code the
addresses point at -- so every number resolved to an empty shelf and build.py
had nothing to assemble.

This script closes that. For every capability in a filled form it fetches the
named file at the PINNED COMMIT, cuts out the named line range, verifies the
named symbol is actually in what it cut, and writes it to the shelf under that
capability's number, with its provenance and licence beside it.

It does not touch the form. It does not touch the registry. It does not touch
the tree. It reads addresses and fills the shelf.

  Usage:
      python3 harvest_parts.py forms/event-ticketing.form.json
      python3 harvest_parts.py                 # every filled form in FORMS_DIR

  Exit 0 = every capability in every form landed on the shelf and verified.
  Exit 1 = at least one did not. The report says which and why.

Rule N5 note: N5 forbids copying a capability INTO AN APP. Apps reference the
shelf in place, by number. This script writes to the shelf itself, which is the
library N5 assumes already exists. It never writes into an app folder.
"""

# =====================================================================
# RULES / CONFIG  -- edit these, nothing below this block
# =====================================================================

FORMS_DIR = "forms"
# Where filled harvest forms live. With no argument, every *.form.json in here
# that has an app_slug and capabilities is processed. Blank forms are skipped.

SHELF_DIR = "shelf"
# Where harvested code lands. One folder per app slug, one folder per
# capability number inside it. This is the library build.py assembles from.
# Point this somewhere else and you build a separate shelf without touching
# this one.

RAW_URL_TEMPLATE = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
# How a single file is fetched at an exact commit. Uses repo_name and commit
# straight out of the form's harvest_source block -- never a branch name, so
# the same run always returns the same bytes. Change this only if you move to a
# different host (e.g. a GitLab mirror).

REQUIRE_PINNED_COMMIT = True
# True  = a form whose harvest_source has no commit is REFUSED outright.
#         A branch moves; a commit does not. Harvesting off a branch means the
#         shelf silently changes under you.
# False = falls back to harvest_source.branch. Not recommended.

VERIFY_SYMBOL_PRESENT = True
# True  = after cutting the line range, the capability's source_symbol must
#         appear in the cut text, or that capability FAILS. This is what
#         catches a line range that has drifted since the form was filled.
# False = cut blindly. You lose the only automatic check that the address is
#         still correct.

SYMBOL_SPLIT_CHARS = ["/", ";", ","]
# source_symbol is written by a human and often names more than one thing,
# e.g. "RHRegister / LocalRegistrationHandler". The symbol check passes if ANY
# of the pieces appears. Widen this if forms start using another separator.

HARVEST_WHOLE_MODULE = True
# True  = harvest the ENTIRE file the symbol lives in, imports and all. A cut
#         line range gives you the symbol with nothing it stands on -- no
#         imports, no base class, no helpers -- so the part cannot run. The
#         recorded line range is kept on the provenance as the address of the
#         symbol inside the module, it just no longer limits what is fetched.
# False = fetch only the recorded line range. Smaller files, parts that do not
#         run on their own.

WHOLE_MODULE_MAX_LINES = 20000
# Refuse a module larger than this rather than writing something enormous to
# the shelf by accident. Raise it if a real source file is legitimately bigger.

LINE_CONTEXT = 0
# Extra lines to take either side of the named range. 0 = exactly the range in
# the form. Raise it if cut code keeps losing a decorator or a closing bracket
# that sits just outside the recorded range.

FAIL_ON_EMPTY_CUT = True
# True = a line range that yields nothing (range past end of file, or reversed)
#        is a failure, not an empty file quietly written to the shelf.

OVERWRITE_EXISTING = True
# True  = re-running replaces what is on the shelf. Safe, because the commit is
#         pinned -- the same form yields the same bytes.
# False = a capability already on the shelf is left alone and reported as
#         'kept'. Use this when hand-editing a shelf part.

WRITE_LICENCE_FILE = True
# True = every capability folder gets LICENCE.txt naming the source repo, its
#        licence from the form, and the exact commit. Required for a
#        permissive-licence audit; leave this on.

# ---------------------------------------------------------------------
# ADMISSION -- god mode's Harvest Admission Rule, enforced here, at the
# point code is fetched. A source that fails any of these never reaches
# the shelf, so nothing downstream has to inspect it afterwards.
# ---------------------------------------------------------------------

ENFORCE_ADMISSION = True
# True  = a source failing any rule below is REFUSED and nothing is written.
# False = fetch anything. This admits code the host cannot run; the whole
#         library rests on every part sharing one stack, so leaving this off
#         is a decision to break that.

REQUIRED_FRAMEWORK = "flask"
# Rule A, first half. The framework every part must be built on. Compared
# case-insensitively against the source's declared framework.

REQUIRED_DATASTORE = "postgresql"
# Rule A, second half. The database every part must be built on. Two parts
# on different datastores cannot coexist in one app; fixing that at assembly
# time is a rewrite, and a rewrite is where invented code enters the library.
# Accepts the aliases below.

DATASTORE_ALIASES = {
    "postgresql": ["postgresql", "postgres", "psql", "postgresql16", "postgres16"],
}
# What counts as the same datastore written differently. Extend a list here
# rather than loosening REQUIRED_DATASTORE.

ALLOWED_LICENCES = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0"]
# Rule C. Permissive only. Anything not on this list is refused outright --
# copyleft licences would follow the code into every app built from it.

REQUIRE_API_DOCS = True
# Rule B. The source must publish REST API documentation. If it does, the
# capability contract is already written down and can be recorded rather than
# inferred from source under pressure.

REQUIRE_STRUCTURAL_MATCH = True
# Rule D. The source must be recorded as matching the commercial exemplar it
# was chosen against, in one sentence.

ONE_SOURCE_PER_APP = True
# Rule E. Every capability in one app comes from one repo. Rule A makes parts
# compatible at stack level; this keeps them compatible at application level --
# one set of models, one session model, one set of conventions.

NETWORK_TIMEOUT_SECONDS = 30
# Per-file fetch timeout.

FETCH_RETRIES = 2
# Retries per file before that file is called unreachable.

DRY_RUN = False
# True = print exactly what would be fetched and written, and write nothing.

# =====================================================================
# Nothing below here is configuration.
# =====================================================================

import json
import os
import re
import sys
import glob
import time
import urllib.request
import urllib.error


def die(msg):
    print(f"REFUSED: {msg}")
    sys.exit(1)


def parse_line_ranges(raw, default_path):
    """
    source_lines is written by hand and is not always one clean range.
    Handles:
        "233-367"
        "416-424 (RH); 437-483 (indico/.../util.py)"
        "68-128, 140-147"
    Returns a list of (path, start, end). A parenthetical that looks like a
    file path overrides the path for that range; anything else in parentheses
    is a note and ignored.
    """
    out = []
    if not raw or not str(raw).strip():
        return out
    for chunk in re.split(r"[;,]", str(raw)):
        chunk = chunk.strip()
        if not chunk:
            continue
        path = default_path
        note = re.search(r"\(([^)]*)\)", chunk)
        if note:
            inner = note.group(1).strip()
            # Treat it as a path only if it looks like one.
            if "/" in inner or inner.endswith(".py"):
                path = inner
            chunk = chunk[: note.start()] + chunk[note.end():]
        m = re.search(r"(\d+)\s*-\s*(\d+)", chunk)
        if m:
            out.append((path, int(m.group(1)), int(m.group(2))))
            continue
        m = re.search(r"(\d+)", chunk)
        if m:
            n = int(m.group(1))
            out.append((path, n, n))
    return out


_file_cache = {}


def fetch_file(repo, commit, path):
    key = (repo, commit, path)
    if key in _file_cache:
        return _file_cache[key]
    url = RAW_URL_TEMPLATE.format(repo=repo, commit=commit, path=path)
    last = None
    for attempt in range(FETCH_RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=NETWORK_TIMEOUT_SECONDS) as r:
                if r.status != 200:
                    last = f"HTTP {r.status}"
                    continue
                text = r.read().decode("utf-8", errors="replace")
                _file_cache[key] = text
                return text
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:
            last = str(e)
        if attempt < FETCH_RETRIES:
            time.sleep(1)
    _file_cache[key] = None
    raise RuntimeError(f"could not fetch {url} ({last})")


def symbol_pieces(symbol):
    pieces = [str(symbol or "")]
    for ch in SYMBOL_SPLIT_CHARS:
        nxt = []
        for p in pieces:
            nxt.extend(p.split(ch))
        pieces = nxt
    cleaned = []
    for p in pieces:
        p = p.strip()
        # "RHRegistrationForm._process_POST" -> also accept the bare attribute
        if p:
            cleaned.append(p)
            if "." in p:
                cleaned.extend([x for x in p.split(".") if x])
    return [c for c in cleaned if len(c) >= 3]


def check_admission(src, caps, where):
    """God mode's Harvest Admission Rule, applied to a source before a single
    byte is fetched. Returns a list of reasons it may not be harvested --
    empty means admitted. Never partially admits: one reason refuses the lot."""
    if not ENFORCE_ADMISSION:
        return []

    reasons = []

    fw = (src.get("framework") or "").strip().lower()
    if fw != REQUIRED_FRAMEWORK.lower():
        reasons.append(f"Rule A framework: needs {REQUIRED_FRAMEWORK}, source says "
                       f"{fw or '(not recorded)'}")

    ds = (src.get("datastore") or "").strip().lower().replace(" ", "")
    allowed_ds = DATASTORE_ALIASES.get(REQUIRED_DATASTORE.lower(), [REQUIRED_DATASTORE.lower()])
    if ds not in allowed_ds:
        reasons.append(f"Rule A datastore: needs {REQUIRED_DATASTORE}, source says "
                       f"{ds or '(not recorded)'}")

    lic = (src.get("licence") or src.get("license") or "").strip()
    if lic not in ALLOWED_LICENCES:
        reasons.append(f"Rule C licence: {lic or '(not recorded)'} is not permissive "
                       f"(allowed: {', '.join(ALLOWED_LICENCES)})")

    if REQUIRE_API_DOCS and not (src.get("api_docs_url") or "").strip():
        reasons.append("Rule B: source publishes no REST API documentation")

    if REQUIRE_STRUCTURAL_MATCH and not (src.get("structural_match") or "").strip():
        reasons.append("Rule D: no structural match to the commercial exemplar recorded")

    if ONE_SOURCE_PER_APP:
        repos = {(c.get("provenance") or {}).get("source_repo")
                 for c in caps if (c.get("provenance") or {}).get("source_repo")}
        repos.discard(src.get("repo_name"))
        if repos:
            reasons.append(f"Rule E: capabilities name other repos besides "
                           f"{src.get('repo_name')}: {', '.join(sorted(repos))}")

    return reasons


def harvest_form(form_path):
    """Returns (rows, failures) for one form."""
    with open(form_path) as f:
        form = json.load(f)

    slug = form.get("app_slug")
    caps = form.get("capabilities") or []
    if not slug or not caps:
        return None, []

    src = form.get("harvest_source") or {}
    repo = src.get("repo_name")
    commit = src.get("commit")
    licence = src.get("licence", "")
    branch = src.get("branch", "")

    if not repo:
        die(f"{form_path}: harvest_source.repo_name is empty -- nothing to fetch from")
    if not commit:
        if REQUIRE_PINNED_COMMIT:
            die(f"{form_path}: harvest_source.commit is empty and "
                f"REQUIRE_PINNED_COMMIT is True -- refusing to harvest off a branch")
        commit = branch
        if not commit:
            die(f"{form_path}: no commit and no branch")

    refusals = check_admission(src, caps, form_path)
    if refusals:
        print(f"REFUSED: {slug} -- fails god mode's Harvest Admission Rule")
        for r in refusals:
            print(f"    {r}")
        print("    Nothing was fetched and nothing was written to the shelf.")
        sys.exit(1)

    app_dir = os.path.join(SHELF_DIR, slug)
    rows, failures = [], []

    for cap in caps:
        cap_id = cap.get("cap_id") or ""
        cap_name = cap.get("cap_name") or ""
        prov = cap.get("provenance") or {}
        sfile = prov.get("source_file") or ""
        slines = prov.get("source_lines") or ""
        ssym = prov.get("source_symbol") or ""

        label = f"{cap_id or '(no number)'} {cap_name}"

        if not cap_id:
            failures.append(f"{label}: no cap_id -- run assign_numbers.py first")
            rows.append((cap_id, cap_name, "-", "NO NUMBER"))
            continue
        if not sfile or not slines:
            failures.append(f"{label}: provenance incomplete "
                            f"(source_file={sfile!r} source_lines={slines!r})")
            rows.append((cap_id, cap_name, "-", "NO ADDRESS"))
            continue

        ranges = parse_line_ranges(slines, sfile)
        if not ranges:
            failures.append(f"{label}: could not read a line range out of {slines!r}")
            rows.append((cap_id, cap_name, "-", "BAD RANGE"))
            continue

        pieces = []
        total_lines = 0
        fetch_error = None
        seen_paths = set()
        for path, start, end in ranges:
            try:
                text = fetch_file(repo, commit, path)
            except RuntimeError as e:
                fetch_error = str(e)
                break
            lines = text.splitlines()

            if HARVEST_WHOLE_MODULE:
                # One module, once, whole. Several recorded ranges in the same
                # file collapse to a single copy of that file.
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                if len(lines) > WHOLE_MODULE_MAX_LINES:
                    fetch_error = (f"{path} is {len(lines)} lines, over "
                                   f"WHOLE_MODULE_MAX_LINES ({WHOLE_MODULE_MAX_LINES})")
                    break
                total_lines += len(lines)
                header = (f"# ---- {path} (whole module, symbol at {start}-{end}) "
                          f"@ {repo}@{commit[:12]} ----")
                pieces.append(header + "\n" + text.rstrip("\n"))
                continue

            lo = max(1, start - LINE_CONTEXT)
            hi = min(len(lines), end + LINE_CONTEXT)
            if lo > hi:
                continue
            cut = lines[lo - 1:hi]
            total_lines += len(cut)
            header = (f"# ---- {path}:{lo}-{hi} "
                      f"@ {repo}@{commit[:12]} ----")
            pieces.append(header + "\n" + "\n".join(cut))

        if fetch_error:
            failures.append(f"{label}: {fetch_error}")
            rows.append((cap_id, cap_name, "-", "UNREACHABLE"))
            continue

        body = "\n\n".join(pieces)

        if FAIL_ON_EMPTY_CUT and total_lines == 0:
            failures.append(f"{label}: line range {slines!r} cut zero lines from {sfile}")
            rows.append((cap_id, cap_name, 0, "EMPTY CUT"))
            continue

        if VERIFY_SYMBOL_PRESENT and ssym:
            pcs = symbol_pieces(ssym)
            if pcs and not any(p in body for p in pcs):
                failures.append(f"{label}: symbol {ssym!r} not found in "
                                f"{sfile}:{slines} -- the address has drifted")
                rows.append((cap_id, cap_name, total_lines, "SYMBOL MISSING"))
                continue

        cap_dir = os.path.join(app_dir, cap_id)
        part_path = os.path.join(cap_dir, "source.py")

        if os.path.exists(part_path) and not OVERWRITE_EXISTING:
            rows.append((cap_id, cap_name, total_lines, "kept"))
            continue

        if DRY_RUN:
            rows.append((cap_id, cap_name, total_lines, "would write"))
            continue

        os.makedirs(cap_dir, exist_ok=True)
        with open(part_path, "w") as f:
            f.write(body + "\n")

        with open(os.path.join(cap_dir, "PROVENANCE.json"), "w") as f:
            json.dump({
                "cap_id": cap_id,
                "cap_name": cap_name,
                "app_slug": slug,
                "repo_name": repo,
                "repo_url": src.get("repo_url", ""),
                "licence": licence,
                "commit": commit,
                "source_file": sfile,
                "source_symbol": ssym,
                "source_lines": slines,
                "ranges_fetched": [
                    {"path": p, "start": s, "end": e} for p, s, e in ranges
                ],
                "lines_written": total_lines,
                "symbol_verified": bool(VERIFY_SYMBOL_PRESENT and ssym),
                "fetched_by": "harvest_parts.py",
            }, f, indent=2)

        if WRITE_LICENCE_FILE:
            with open(os.path.join(cap_dir, "LICENCE.txt"), "w") as f:
                f.write(
                    f"Source repo: {src.get('repo_url', repo)}\n"
                    f"Licence:     {licence}\n"
                    f"Commit:      {commit}\n"
                    f"File:        {sfile}\n"
                    f"Lines:       {slines}\n\n"
                    f"This code was taken verbatim from the repo and commit above.\n"
                    f"It is reproduced under that licence. Do not edit this part in\n"
                    f"place -- re-harvest from a new commit instead, so provenance\n"
                    f"stays true.\n"
                )

        rows.append((cap_id, cap_name, total_lines, "on shelf"))

    return (slug, repo, commit, licence, rows), failures


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        form_paths = args
    else:
        form_paths = sorted(glob.glob(os.path.join(FORMS_DIR, "*.form.json")))

    if not form_paths:
        die(f"no forms found (looked in {FORMS_DIR})")

    print(f"shelf: {SHELF_DIR}")
    print(f"forms to consider: {len(form_paths)}")
    if DRY_RUN:
        print("DRY_RUN is True -- nothing will be written")
    print()

    all_failures = []
    apps_done = 0
    total_on_shelf = 0

    for fp in form_paths:
        try:
            result, failures = harvest_form(fp)
        except json.JSONDecodeError as e:
            all_failures.append(f"{fp}: not valid JSON ({e})")
            continue

        if result is None:
            continue

        slug, repo, commit, licence, rows = result
        apps_done += 1
        print(f"{slug}   <- {repo}@{commit[:12]}   ({licence})")
        print(f"  {'number':<10} {'capability':<28} {'lines':>6}  result")
        for cap_id, cap_name, n, status in rows:
            print(f"  {cap_id:<10} {cap_name:<28} {str(n):>6}  {status}")
            if status in ("on shelf", "kept"):
                total_on_shelf += 1
        print()
        all_failures.extend(failures)

    print("-" * 62)
    print(f"apps harvested: {apps_done}   capabilities on shelf: {total_on_shelf}   "
          f"failures: {len(all_failures)}")

    if all_failures:
        print()
        print("FAILURES")
        for f in all_failures:
            print(f"  - {f}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
