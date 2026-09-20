#!/usr/bin/env python3
"""
acquire.py — spec sections 4-5: ACQUISITION + LICENCE gate, per app.

DISCOVER -> CLONE -> RECORD COMMIT -> VERIFY LICENCE -> RECORD PROVENANCE

Deterministic: shallow clone at the default branch, pin the exact commit SHA
reached, read the repo's OWN LICENSE file (never trust a directory's label),
classify it, and refuse if it's not on the allowed list. Every app gets a
provenance.json regardless of outcome. Failure is recorded as
ACQUISITION_FAILED or LICENCE_UNCLEAR, never silently skipped, and this
script tries the NEXT discovery candidate for that category before giving up
entirely (spec section 3's "READY gate" implies replacement, not one shot).
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST_FILE = HERE / "manifest.json"
APPS_DIR = HERE / "applications"
CLONE_TIMEOUT = 600
GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}

# Per Sam: use everything whose licence is genuinely good open source, not just
# the permissive subset. That means every OSI-approved licence, copyleft
# included (GPL/AGPL/LGPL/EUPL obligate you to share your changes; they don't
# stop you using and deploying the app, which is what this library does).
# Still refused: source-available-but-not-open-source licences that restrict
# who can run the software or how (BUSL, Elastic, SSPL, Commons-Clause,
# PolyForm, OSL's patent-termination terms), non-commercial-only licences
# (CC-BY-NC), and no licence file at all / UNRECOGNISED - those really are
# "no good" for a library meant to be used.
ALLOWED_LICENCES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
                    "MPL-2.0", "Unlicense", "0BSD", "Zlib", "CC0-1.0",
                    "GPL", "GPL-2.0", "GPL-3.0", "AGPL-3.0", "LGPL", "LGPL-2.1",
                    "LGPL-3.0", "EUPL-1.2")
REFUSED_LICENCES_NOTE = ("Commons-Clause", "BUSL-1.1", "Elastic-2.0", "SSPL", "OSL-3.0",
                         "PolyForm", "CC-BY-NC", "UNRECOGNISED", None)
LICENCE_FILE_NAMES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "LICENCE.txt",
                      "LICENCE.md", "COPYING", "COPYING.txt", "LICENSE-MIT", "LICENSE.MIT",
                      "MIT-LICENSE", "MIT-LICENSE.txt", "LICENSE.rst", "UNLICENSE")


def classify_licence(head):
    h = head
    if "Commons Clause" in h: return "Commons-Clause"
    if "Business Source License" in h: return "BUSL-1.1"
    if "Elastic License" in h: return "Elastic-2.0"
    if "Server Side Public License" in h: return "SSPL"
    if "Open Software License" in h: return "OSL-3.0"
    if "PolyForm" in h: return "PolyForm"
    if "Creative Commons Attribution-NonCommercial" in h or "CC BY-NC" in h: return "CC-BY-NC"
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in h: return "AGPL-3.0"
    if "GNU LESSER GENERAL PUBLIC LICENSE" in h: return "LGPL"
    if "GNU GENERAL PUBLIC LICENSE" in h: return "GPL"
    if "European Union Public Licence" in h: return "EUPL-1.2"
    if "Apache License" in h and "Version 2.0" in h: return "Apache-2.0"
    if "Mozilla Public License" in h: return "MPL-2.0"
    if "This is free and unencumbered software released into the public domain" in h: return "Unlicense"
    if "CC0 1.0" in h or "Creative Commons Zero" in h: return "CC0-1.0"
    if "ISC License" in h or "Permission to use, copy, modify, and/or" in h: return "ISC"
    if "zlib License" in h.lower() or ("This software is provided 'as-is'" in h and "altered source" in h): return "Zlib"
    if "Neither the name of" in h and "Redistribution and use" in h: return "BSD-3-Clause"
    if "Redistribution and use in source and binary forms" in h: return "BSD-2-Clause"
    if "MIT License" in h or "Permission is hereby granted, free of charge" in h: return "MIT"
    return "UNRECOGNISED"


def run(argv, cwd=None, timeout=None):
    try:
        p = subprocess.run(argv, cwd=cwd, timeout=timeout, capture_output=True, text=True,
                           env={**__import__("os").environ, **GIT_ENV})
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"


def clone(url, dest):
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rc, out, err = run(["git", "clone", "--depth", "1", "--single-branch", "-q", url, str(dest)],
                       timeout=CLONE_TIMEOUT)
    if rc != 0:
        return None, err.strip()[:400]
    rc, out, err = run(["git", "-C", str(dest), "rev-parse", "HEAD"], timeout=60)
    commit = out.strip()
    rc2, out2, _ = run(["git", "-C", str(dest), "rev-parse", "--abbrev-ref", "HEAD"], timeout=60)
    branch = out2.strip()
    return {"commit": commit, "branch": branch}, None


def sha256_of_tree_listing(root):
    """Not a full content checksum (too slow for large repos) - a deterministic
    checksum of the tracked file list + sizes, cheap and still catches a
    silently-different checkout. Recorded as 'source_checksum' per spec section 4."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        rel = str(p.relative_to(root))
        h.update(rel.encode())
        h.update(str(p.stat().st_size).encode())
    return h.hexdigest()


def read_licence(root):
    names = {n.lower(): n for n in LICENCE_FILE_NAMES}
    for p in sorted(root.iterdir()):
        if p.is_file() and p.name.lower() in names:
            head = p.read_text(errors="ignore")[:8000]
            return classify_licence(head), p.name
    return None, None


def acquire_one(app_id, candidate, category_slug):
    root = APPS_DIR / app_id / "source"
    clone_info, err = clone(candidate["source_code_url"], root)
    now = datetime.now(timezone.utc).isoformat()
    if clone_info is None:
        return {"status": "ACQUISITION_FAILED", "reason": f"clone failed: {err}"}, None
    lic, lic_file = read_licence(root)
    provenance = {
        "application": app_id,
        "category": category_slug,
        "repository_url": candidate["source_code_url"],
        "commit_sha": clone_info["commit"],
        "branch": clone_info["branch"],
        "download_timestamp": now,
        "download_method": "git clone --depth 1",
        "licence_file": lic_file,
        "licence_detected": lic,
        "licence_allowed": lic in ALLOWED_LICENCES if lic else False,
        "source_checksum_sha256": sha256_of_tree_listing(root),
        "discovery_source": candidate.get("discovery_source", "github-search-or-directory"),
        "stargazers_count": candidate.get("stargazers_count"),
    }
    if not lic_file:
        return {"status": "LICENCE_UNCLEAR", "reason": "no LICENSE file found in repo root"}, provenance
    if lic not in ALLOWED_LICENCES:
        return {"status": "LICENCE_UNCLEAR", "reason": f"licence file says {lic}, not on the allowed list {ALLOWED_LICENCES}"}, provenance
    return {"status": "ACQUIRED", "reason": None}, provenance


def main():
    manifest = json.loads(MANIFEST_FILE.read_text())
    results = {"ACQUIRED": 0, "ACQUISITION_FAILED": 0, "LICENCE_UNCLEAR": 0, "DISCOVERY_FAILED": 0}
    for entry in manifest["applications"]:
        app_id = entry["id"]
        if entry["status"] == "DISCOVERY_FAILED":
            results["DISCOVERY_FAILED"] += 1
            continue
        # Anything other than LICENCE_UNCLEAR already passed (or is past) the
        # licence gate under the OLD allowed list - re-running would just
        # redundantly re-clone an app that's already correctly ACQUIRED, or
        # worse, re-roll the candidate for one that's already progressed
        # further (INSTALL_FAILED/STARTUP_FAILED/BLOCKED_EXTERNAL_DEPENDENCY/
        # SCREEN-VERIFIED all imply a valid licence was already found).
        if entry["status"] != "LICENCE_UNCLEAR":
            results[entry["status"]] = results.get(entry["status"], 0) + 1
            continue
        candidates = entry.get("discovery_candidates") or [{
            "source_code_url": entry["repository"], "name": entry["name"],
            "discovery_source": "manual_override" if entry.get("manual_override_reason") else "unknown",
        }]
        # manual overrides aren't in discovery_candidates; make sure the chosen
        # pick is tried first regardless
        chosen_url = (entry.get("repository") or "").rstrip("/").lower()
        candidates = sorted(candidates, key=lambda c: 0 if (c.get("source_code_url") or "").rstrip("/").lower() == chosen_url else 1)

        attempts = []
        outcome, provenance = None, None
        for cand in candidates[:4]:
            print(f"{app_id} ({entry['category_slug']}): trying {cand['name']} {cand['source_code_url']}")
            outcome, provenance = acquire_one(app_id, cand, entry["category_slug"])
            attempts.append({"name": cand["name"], "repo": cand["source_code_url"], **outcome})
            print(f"  -> {outcome['status']}" + (f" ({outcome['reason']})" if outcome.get("reason") else ""))
            if outcome["status"] == "ACQUIRED":
                entry["name"] = cand["name"]
                entry["repository"] = cand["source_code_url"]
                break
        entry["status"] = outcome["status"]
        entry["acquisition_attempts"] = attempts
        entry["licence"] = provenance["licence_detected"] if provenance else None
        entry["commit"] = provenance["commit_sha"] if provenance else None
        results[outcome["status"]] = results.get(outcome["status"], 0) + 1

        d = APPS_DIR / app_id
        d.mkdir(parents=True, exist_ok=True)
        if provenance:
            (d / "provenance.json").write_text(json.dumps(provenance, indent=1))
        (d / "app.json").write_text(json.dumps(entry, indent=1))

    MANIFEST_FILE.write_text(json.dumps(manifest, indent=1))
    print("\n=== ACQUISITION SUMMARY ===")
    for k, v in results.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
