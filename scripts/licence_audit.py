#!/usr/bin/env python3
"""
Licence + dependency audit GATE (spec §22–§23 + correction).

Exit codes (use in CI / Docker build):
  0  PASS     — every shipping component verified; safe to label "licensing verified"
  1  PENDING  — no hard violation, but unpinned commits / missing SHA-256 remain;
               MUST NOT be labelled "licensing verified"
  2  FAIL     — a hard rule was violated; the build MUST stop

Hard-FAIL rules (any -> exit 2):
  R1 a shipping dependency has no licence
  R2 code licence and model-weight licence differ AND either is unapproved
  R3 a model downloads weights dynamically from an unverified source
  R4 a test asset / dataset carries a non-commercial restriction AND is shipped
  R5 InsightFace weights appear anywhere (manifest, tree, or installed pkgs)
  R6 CodeFormer, XTTS(-v2), Wav2Lip or FLUX.1-dev appear anywhere (transitively)
  R7 a shipped avatar bundle has missing/invalid provenance or a hash mismatch

Run:  python scripts/licence_audit.py [--lock config/dependency_lock.yaml] [--root .]
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys

import yaml

PLACEHOLDERS = {"PIN_ME", None, "", "null"}

# Single source of truth, shared with the runtime provider registry, so a
# licence can never be approved at runtime and banned at build time.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aura.providers.licences import is_noncommercial as _noncommercial  # noqa: E402


def load(path):
    with open(path) as f:
        return yaml.safe_load(f)


import re

# Ambiguous with our own source (e.g. our tts.py) -> only checked as an EXACT
# installed-package / requirement token, never as a path substring.
_AMBIGUOUS_AS_PATH = {"tts"}


def _pkg_token(line: str) -> str:
    return re.split(r"[=<>!~ \[]", line.strip(), 1)[0].strip().lower()


def scan_tree_and_pkgs(root: str, needles: list[str]) -> list[str]:
    """Transitive check with EXACT token matching (no substrings), so project
    files like aura/workers/tts.py never false-trigger the ban on coqui 'TTS'."""
    hits: list[str] = []
    path_needles = [n for n in needles if n not in _AMBIGUOUS_AS_PATH]

    # 1) file/dir names — exact stem or dir-name match only
    for p in glob.glob(os.path.join(root, "**"), recursive=True):
        if "/.git/" in p:
            continue
        stem = os.path.splitext(os.path.basename(p))[0].lower()
        if stem in path_needles:
            hits.append(f"path:{p}")

    # 2) requirements files — exact package token match (skip comments)
    for req in glob.glob(os.path.join(root, "**/requirements*.txt"), recursive=True):
        try:
            for line in open(req):
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if _pkg_token(s) in needles:
                    hits.append(f"{req}:{s}")
        except OSError:
            pass

    # 3) installed packages — exact package name match
    try:
        out = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                             capture_output=True, text=True, timeout=30).stdout
        for line in out.splitlines():
            if _pkg_token(line) in needles:
                hits.append(f"pip:{line.strip()}")
    except Exception:
        pass
    return hits


def audit(lock: dict, root: str):
    fails: list[str] = []
    pendings: list[str] = []
    approved_code = set(lock.get("approved_code_licences", []))
    approved_wt = set(lock.get("approved_weight_licences", []))
    forbidden = [f.lower() for f in lock.get("forbidden", [])]
    shipping_kinds = {"infra", "code", "model_code", "model_weight", "voice",
                      "codec", "avatar"}

    for c in lock.get("components", []):
        name = c.get("name", "?")
        kind = c.get("kind", "?")
        ships = c.get("ship", True) and kind in shipping_kinds
        lic = c.get("licence")
        wlic = c.get("weight_licence")

        # R1 — no licence on a shipping component
        if ships and (lic in PLACEHOLDERS):
            fails.append(f"R1 {name}: shipping component has no licence")

        # R2 — code vs weight licence mismatch with an unapproved side
        if kind == "model_weight" and lic and wlic and lic != wlic:
            if (lic not in approved_code and lic not in approved_wt) or \
               (wlic not in approved_wt and wlic not in approved_code):
                fails.append(f"R2 {name}: code lic '{lic}' != weight lic '{wlic}' and one is unapproved")

        # R3 — dynamic weight download from unverified source
        if c.get("dynamic_download") and c.get("download_source") != "verified":
            fails.append(f"R3 {name}: dynamic weight download from unverified source "
                         f"(pin + pre-download + local_files_only)")

        # R4 — non-commercial dataset/test asset that is shipped
        if kind in ("dataset", "test_asset") and _noncommercial(lic) and c.get("ship", True):
            fails.append(f"R4 {name}: non-commercial {kind} is shipped")

        # R5 — insightface weight declared
        if "insightface" in name.lower() and kind in ("model_weight", "model_code"):
            fails.append(f"R5 {name}: InsightFace present in manifest")

        # PENDING — shipping component not fully pinned/hashed
        if ships:
            if c.get("commit") in PLACEHOLDERS and kind != "codec" and c.get("repo") != "local":
                pendings.append(f"{name}: commit not pinned")
            if kind in ("model_weight", "avatar") and c.get("sha256") in PLACEHOLDERS:
                pendings.append(f"{name}: SHA-256 not recorded")

    # R7 — every shipped avatar bundle must carry valid, matching provenance
    for bundle_dir in sorted(glob.glob(os.path.join(root, "assets", "**", "bundle.json"),
                                       recursive=True)):
        d = os.path.dirname(bundle_dir)
        try:
            from aura.studio.provenance import verify_bundle
            for problem in verify_bundle(d):
                fails.append(f"R7 {os.path.relpath(d, root)}: {problem}")
        except Exception as e:
            fails.append(f"R7 {os.path.relpath(d, root)}: unreadable bundle ({e!r})")

    # R5/R6 — forbidden anywhere in tree / requirements / installed pkgs
    needles = forbidden + ["insightface"]
    for hit in scan_tree_and_pkgs(root, sorted(set(needles))):
        fails.append(f"R6 forbidden component present -> {hit}")

    return fails, pendings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", default="config/dependency_lock.yaml")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    lock = load(args.lock)
    fails, pendings = audit(lock, args.root)

    print("=" * 68)
    print("AURA LICENCE + DEPENDENCY AUDIT")
    print("=" * 68)
    if fails:
        print(f"\nHARD FAILURES ({len(fails)}):")
        for f in fails:
            print("  ✗", f)
    if pendings:
        print(f"\nPENDING / UNVERIFIED ({len(pendings)}):")
        for p in pendings:
            print("  •", p)

    status = "FAIL" if fails else ("PENDING" if pendings else "PASS")
    with open(os.path.join(args.root, ".licence_status"), "w") as f:
        f.write(status + "\n")

    print("\n" + "-" * 68)
    print(f"STATUS: {status}")
    if status == "PASS":
        print("All shipping components verified. Repo may be labelled "
              "'licensing verified'.")
        sys.exit(0)
    if status == "PENDING":
        print("No hard violation, but pins/checksums are incomplete. DO NOT "
              "label 'licensing verified'. Fill PIN_ME + SHA-256 on the build host.")
        sys.exit(1)
    print("Build must STOP until the failures above are resolved.")
    sys.exit(2)


if __name__ == "__main__":
    main()
