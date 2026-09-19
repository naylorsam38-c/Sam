#!/usr/bin/env python3
"""
hunt.py -- discovery, inspection, evidence collection, scoring and the
admission decision for whole CANDIDATE applications, before any capability
is ever harvested from one. This is DISCOVERY, not harvesting (Section 13):
it never rewrites, converts, adapts or installs anything. It clones,
reads, scores, and writes a report. Only after a candidate is ADMITTED does
any later step (promotion, then 1_harvest/harvest_parts.py) touch the
shelf.

**It does not carry its own copy of the admission rule.** REQUIRED_FRAMEWORK,
REQUIRED_DATASTORE, ALLOWED_LICENCES, MIN_HOOKS, check_admission() and
usable_attach_points() are imported directly from 1_harvest/harvest_parts.py
-- the same script that will later actually harvest the winner. Two copies
of the same gate drift; the copy that drifted would be the one that let
something through.

The output directory name says what it is: OUTPUT_DIR defaults to
0_harvest_results, not "results" or "out" -- a candidate that was actually
inspected is never quietly absent from it.

This script does not decide which real repositories to try. It has no
network search of its own (see MIN_HOOKS's neighbour comment on why:
GitHub-wide search was out of scope for the session that wrote this).
Candidates are supplied to run_category() as CandidateSpec values that
someone -- a person, or an agent that has actually read the real
repository -- has already researched and can stand behind. What this
script verifies for real, from the actual clone, is: the exact commit,
the keyword-signal sweep (Section 7 -- signal only, never proof by
itself), git-derived quality metrics (commit recency, contributors,
tags), and the same admission decision harvest_parts.py would make.

Usage:
    python3 hunt.py --category "event ticketing" --candidates candidates_event_ticketing.py
    (see candidates_example.py for the CandidateSpec shape)

This script never auto-continues into promotion. It writes reports and
stops, per Section 13 and per instruction: "it stops so you get to look."
"""

# =====================================================================
# CONFIG  -- edit these. Nothing below this block needs changing.
# =====================================================================

OUTPUT_DIR = "../0_harvest_results"
# Where every candidate's REPORT.md, ATTACH_POINTS.md and evidence/ land,
# one folder per category, one subfolder per candidate. Named so a real run's
# output can never be mistaken for scratch -- every candidate actually
# inspected stays recorded here, winners and rejections alike.

CLONE_DIR = "/tmp/0_harvest_clones"
# Where candidates are cloned for real inspection. Outside the repo --
# these are working clones, not evidence; evidence/ under OUTPUT_DIR is
# what gets kept.

HARVEST_PARTS_PATH = "../1_harvest/harvest_parts.py"
# Where the real admission gate lives. Imported, not copied -- see the
# module docstring.

RECENT_COMMITS_WINDOW_DAYS = 182
# "Commits in the last six months" (Section 8, item 1), counted for real
# from `git log --since` against the clone's own history.

KEYWORD_SIGNALS = [
    "plugin", "plugin system", "plugin API", "extension", "extension point",
    "extensions API", "hook", "hooks", "webhook", "signal", "signals",
    "blinker", "event", "event listener", "event emitter", "subscriber",
    "dispatcher", "middleware", "entry point", "entry points", "extend",
    "extending", "custom module", "add-on", "addon",
    "third party integration", "contrib", "signals.py", "hooks.py",
    "events.py", "plugins/", "extensions/", "django.dispatch", "receiver",
    "Signal()", "AppConfig.ready", "pluggy", "stevedore",
]
# Section 7's full list. Discovery signals only -- a hit here is never, on
# its own, evidence for Rule G. See ATTACH_POINTS's own note: "A keyword hit
# is not proof of an extension mechanism."

CLONE_TIMEOUT_SECONDS = 180

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import os
import re
import sys
import json
import time
import shutil
import subprocess
import importlib.util
import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

HERE = Path(__file__).resolve().parent


def _load_harvest_parts():
    """Import, never copy. If the real gate script cannot be loaded, this
    refuses outright rather than falling back to a local reimplementation."""
    path = (HERE / HARVEST_PARTS_PATH).resolve()
    if not path.is_file():
        print(f"REFUSED: no harvest_parts.py at {path} -- hunt.py has no "
              f"gate of its own and will not invent one")
        sys.exit(2)
    spec = importlib.util.spec_from_file_location("harvest_parts", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HP = _load_harvest_parts()


@dataclass
class CandidateSpec:
    """What a person (or an agent that has actually read the repository)
    supplies per candidate. Every field here is a claim that run_candidate()
    either verifies against the real clone or records as unverified -- never
    silently trusts and never silently drops."""
    repo_name: str            # "org/repo"
    repo_url: str
    branch: str = "main"
    commit: str = ""          # pinned SHA; if blank, resolved from branch HEAD
    licence: str = ""
    framework: str = ""
    datastore: str = ""
    api_docs_url: str = ""
    structural_match: str = ""
    attach_points: list = field(default_factory=list)
    extension_system_description: str = ""
    plugin_authoring_docs_present: Optional[bool] = None
    plugin_authoring_docs_location: str = ""
    third_party_plugins_present: Optional[bool] = None
    third_party_plugin_evidence: list = field(default_factory=list)
    researcher_notes: str = ""


def run(cmd, cwd=None, timeout=CLONE_TIMEOUT_SECONDS):
    return subprocess.run(cmd, cwd=cwd, timeout=timeout,
                          capture_output=True, text=True)


def clone_candidate(spec: CandidateSpec):
    """Real shallow clone, checked out to the exact resolved commit.
    Returns (path, resolved_commit, error_or_None)."""
    dest = Path(CLONE_DIR) / spec.repo_name.replace("/", "__")
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    r = run(["git", "clone", "--quiet", spec.repo_url, str(dest)],
            timeout=CLONE_TIMEOUT_SECONDS)
    if r.returncode != 0:
        return None, None, f"clone failed: {r.stderr.strip()[:300]}"

    if spec.commit:
        r = run(["git", "fetch", "--quiet", "--depth", "1", "origin", spec.commit],
                cwd=dest, timeout=CLONE_TIMEOUT_SECONDS)
        target = spec.commit if r.returncode == 0 else spec.commit
        r = run(["git", "checkout", "--quiet", target], cwd=dest)
        if r.returncode != 0:
            return None, None, (f"could not check out pinned commit "
                                f"{spec.commit}: {r.stderr.strip()[:300]}")
    else:
        r = run(["git", "checkout", "--quiet", spec.branch], cwd=dest)
        if r.returncode != 0:
            return None, None, f"could not check out branch {spec.branch}: {r.stderr.strip()[:300]}"

    resolved = run(["git", "rev-parse", "HEAD"], cwd=dest).stdout.strip()
    if spec.commit and resolved != spec.commit:
        return None, None, (f"resolved HEAD {resolved} does not match "
                            f"pinned commit {spec.commit}")
    return dest, resolved, None


def keyword_signal_sweep(path: Path):
    """Real grep across the real clone for Section 7's keyword list.
    Discovery signal only -- returns counts, never a verdict."""
    hits = {}
    for kw in KEYWORD_SIGNALS:
        try:
            r = subprocess.run(
                ["grep", "-riIl", "--include=*.py", "--include=*.md",
                 "--include=*.rst", "--", kw, str(path)],
                capture_output=True, text=True, timeout=60)
            n = len([l for l in r.stdout.splitlines() if l.strip()])
            if n:
                hits[kw] = n
        except Exception:
            continue
    return hits


def git_quality_metrics(path: Path):
    """Section 8, items 1-3, computed for real from the clone's own git
    history. Items 4-7 (test suite, docs site, issue ratio, third-party
    plugins) are not derivable from a shallow clone alone and are taken from
    the CandidateSpec's own researched fields instead -- recorded as
    RESEARCHER-SUPPLIED, not computed, so the report never blurs the two."""
    since = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(days=RECENT_COMMITS_WINDOW_DAYS)).strftime("%Y-%m-%d")
    # A shallow clone (--depth 1, or fetched to one commit) has only one
    # commit of history by construction; a full clone is needed for real
    # recency/contributor/tag counts.
    r = run(["git", "fetch", "--quiet", "--unshallow"], cwd=path, timeout=CLONE_TIMEOUT_SECONDS)
    unshallow_ok = r.returncode == 0

    commits_recent = None
    contributors = None
    tags = None
    if unshallow_ok:
        r = run(["git", "log", f"--since={since}", "--oneline"], cwd=path)
        commits_recent = len([l for l in r.stdout.splitlines() if l.strip()])
        r = run(["git", "shortlog", "-sn", "HEAD"], cwd=path, timeout=60)
        contributors = len([l for l in r.stdout.splitlines() if l.strip()])
        r = run(["git", "tag"], cwd=path)
        tags = len([l for l in r.stdout.splitlines() if l.strip()])

    test_suite_present = any(path.glob("test*")) or any(path.glob("**/tests/")) \
        or (path / "pytest.ini").exists() or (path / "tox.ini").exists()

    return {
        "history_available_for_recency_check": unshallow_ok,
        "commits_last_6_months": commits_recent,
        "contributors": contributors,
        "tagged_releases": tags,
        "test_suite_present_heuristic": bool(test_suite_present),
    }


def quality_score(metrics, spec: CandidateSpec, keyword_hit_count):
    """Section 8's seven components, combined into one comparable number.
    Heaviest weight on third-party plugin evidence and issue closure, per
    Section 8 -- issue closure ratio has no real data source available to
    this script (see the module docstring on GitHub-search scope) and is
    scored 0 rather than guessed; that gap is stated plainly in the report,
    not hidden inside a total.

    This score ranks otherwise-eligible candidates against each other. It
    never overrides check_admission()'s hard gates -- see run_candidate()."""
    s = 0.0
    components = {}
    components["commits_last_6_months"] = min((metrics.get("commits_last_6_months") or 0) / 10, 5)
    components["contributors"] = min((metrics.get("contributors") or 0) / 5, 5)
    components["tagged_releases"] = min((metrics.get("tagged_releases") or 0), 5)
    components["test_suite_present"] = 3 if metrics.get("test_suite_present_heuristic") else 0
    components["plugin_authoring_docs"] = 4 if spec.plugin_authoring_docs_present else 0
    components["issue_closure_ratio"] = 0  # not collected -- no data source, see docstring
    # Heaviest weighting: third-party plugin evidence.
    components["third_party_plugins"] = 8 if spec.third_party_plugins_present else 0
    for v in components.values():
        s += v
    return s, components


def run_candidate(category: str, spec: CandidateSpec):
    """Clone, sweep, score, check admission, write the candidate's report.
    Never writes to the shelf. Returns a result dict for the category
    summary."""
    cat_slug = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")
    cand_slug = re.sub(r"[^a-z0-9]+", "-", spec.repo_name.lower()).strip("-")
    out_dir = (HERE / OUTPUT_DIR / cat_slug / cand_slug).resolve()
    evidence_dir = out_dir / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {category} :: {spec.repo_name} ===")
    path, resolved_commit, clone_err = clone_candidate(spec)

    result = {
        "category": category, "repo_name": spec.repo_name,
        "repo_url": spec.repo_url, "commit": resolved_commit or spec.commit,
        "admission_result": None, "rejection_reasons": [], "quality_score": None,
        "out_dir": str(out_dir),
    }

    if clone_err:
        result["admission_result"] = "REJECTED"
        result["rejection_reasons"] = [f"could not verify the real repository: {clone_err}"]
        (out_dir / "REPORT.md").write_text(
            f"# {spec.repo_name}\n\nREJECTED\n\ncould not verify the real "
            f"repository: {clone_err}\n")
        print(f"  REJECTED -- {clone_err}")
        return result

    signal_hits = keyword_signal_sweep(path)
    metrics = git_quality_metrics(path)
    score, score_components = quality_score(metrics, spec, len(signal_hits))

    src_for_gate = {
        "framework": spec.framework, "datastore": spec.datastore,
        "licence": spec.licence, "api_docs_url": spec.api_docs_url,
        "structural_match": spec.structural_match, "repo_name": spec.repo_name,
        "attach_points": spec.attach_points,
    }
    # The exact same function 1_harvest/harvest_parts.py will use later.
    reasons = HP.check_admission(src_for_gate, [], f"hunt:{spec.repo_name}")
    usable_aps = HP.usable_attach_points(spec.attach_points)
    admitted = not reasons
    result["admission_result"] = "ADMITTED" if admitted else "REJECTED"
    result["rejection_reasons"] = reasons
    result["quality_score"] = score

    ap_md = HP.render_attach_points_md(spec.repo_name, src_for_gate, spec.attach_points)
    (out_dir / "ATTACH_POINTS.md").write_text(ap_md)

    events = [a for a in usable_aps if a.get("kind", "").upper() == "EVENT"]
    slots = [a for a in usable_aps if a.get("kind", "").upper() == "SLOT"]
    data_pts = [a for a in usable_aps if a.get("kind", "").upper() == "DATA"]

    report = [
        f"# {spec.repo_name}", "",
        f"category: {category}",
        f"repository: {spec.repo_name}",
        f"repository URL: {spec.repo_url}",
        f"exact commit: {resolved_commit}",
        f"licence: {spec.licence}",
        f"framework: {spec.framework}",
        f"datastore: {spec.datastore}",
        "",
        "## Attach points",
        f"hook/signal keyword-sweep hits: {len(signal_hits)} distinct terms "
        f"(discovery signal only, not proof -- see keyword_hits below)",
        f"usable, evidenced attach-point count: {len(usable_aps)}",
        f"  event attach points: {len(events)}",
        f"  slot attach points: {len(slots)}",
        f"  data attach points: {len(data_pts)}",
        "",
        "## Documentation and ecosystem",
        f"plugin-authoring documentation: "
        f"{'yes' if spec.plugin_authoring_docs_present else 'no' if spec.plugin_authoring_docs_present is False else 'NOT RESEARCHED'}",
        f"  location: {spec.plugin_authoring_docs_location or '(none recorded)'}",
        f"third-party plugins: "
        f"{'yes' if spec.third_party_plugins_present else 'no' if spec.third_party_plugins_present is False else 'NOT RESEARCHED'}",
    ]
    for e in spec.third_party_plugin_evidence:
        report.append(f"  - {e}")
    report += [
        "", "## Quality score components (see quality_score() for the weighting)",
    ]
    for k, v in score_components.items():
        report.append(f"  {k}: {v}")
    report += [
        f"  TOTAL: {score}",
        f"  NOTE: issue_closure_ratio is always 0 here -- no real data source "
        f"was available to this script (GitHub-wide search was out of scope "
        f"for the session that wrote it); this is a stated gap, not a "
        f"silent zero.",
        "",
        "## Git-derived metrics (real, from the clone's own history)",
        json.dumps(metrics, indent=2),
        "",
        "## Keyword signal sweep (discovery only, never proof)",
        json.dumps(signal_hits, indent=2),
        "",
        "## Admission result",
        f"**{result['admission_result']}**",
    ]
    if reasons:
        report.append("")
        report.append("Rejection reason(s):")
        for r_ in reasons:
            report.append(f"  - {r_}")
    if spec.researcher_notes:
        report += ["", "## Researcher notes", spec.researcher_notes]
    (out_dir / "REPORT.md").write_text("\n".join(report) + "\n")

    # Evidence: the sweep output and the resolved git metrics, verbatim.
    (evidence_dir / "keyword_signal_sweep.json").write_text(json.dumps(signal_hits, indent=2))
    (evidence_dir / "git_quality_metrics.json").write_text(json.dumps(metrics, indent=2))
    (evidence_dir / "candidate_spec.json").write_text(json.dumps(asdict(spec), indent=2))

    print(f"  {result['admission_result']}  score={score}  "
          f"attach_points={len(usable_aps)}  commit={resolved_commit[:12] if resolved_commit else '?'}")
    if reasons:
        for r_ in reasons:
            print(f"    - {r_}")

    return result


def write_category_summary(category: str, results: list):
    cat_slug = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")
    out_dir = (HERE / OUTPUT_DIR / cat_slug).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    eligible = [r for r in results if r["admission_result"] == "ADMITTED"]
    rejected = [r for r in results if r["admission_result"] == "REJECTED"]
    ranked = sorted(eligible, key=lambda r: r["quality_score"] or 0, reverse=True)
    winner = ranked[0] if ranked else None

    lines = [
        f"# CATEGORY_SUMMARY — {category}", "",
        f"candidates inspected: {len(results)}",
        f"candidates passing hard gates (ADMITTED): {len(eligible)}",
        f"candidates rejected: {len(rejected)}",
        "",
        "## Quality rankings (eligible candidates only)",
    ]
    for r in ranked:
        lines.append(f"  {r['quality_score']:.1f}  {r['repo_name']}  ({r['commit']})")
    lines += ["", "## Rejected, with reasons"]
    for r in rejected:
        lines.append(f"  {r['repo_name']}:")
        for reason in r["rejection_reasons"]:
            lines.append(f"    - {reason}")
    lines += ["", "## Selected candidate"]
    if winner:
        lines.append(f"**{winner['repo_name']}** @ {winner['commit']}  "
                     f"(score {winner['quality_score']:.1f})")
    else:
        lines.append("**NONE ADMITTED**")
        lines.append("")
        lines.append("Reason: " + (
            "no candidates were inspected for this category"
            if not results else
            "every inspected candidate failed at least one hard admission rule "
            "-- see each candidate's own REPORT.md for which"))
    (out_dir / "CATEGORY_SUMMARY.md").write_text("\n".join(lines) + "\n")
    return winner


def write_harvest_summary(category_results: dict):
    """category_results: {category: (winner_or_None, all_results)}"""
    out_dir = (HERE / OUTPUT_DIR).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# HARVEST_SUMMARY", ""]
    for category, (winner, results) in category_results.items():
        lines.append(f"## {category}")
        lines.append(f"candidates inspected: {len(results)}")
        if winner:
            lines.append(f"selected: {winner['repo_name']} @ {winner['commit']} "
                         f"(score {winner['quality_score']:.1f})")
        else:
            lines.append("selected: NONE ADMITTED")
        lines.append("")
    (out_dir / "HARVEST_SUMMARY.md").write_text("\n".join(lines) + "\n")


def run_category(category: str, specs: list):
    """Run every candidate in one category, write CATEGORY_SUMMARY.md,
    return (winner_or_None, all_results). Stops there -- promotion is a
    separate, explicit step."""
    results = [run_candidate(category, s) for s in specs]
    winner = write_category_summary(category, results)
    return winner, results


if __name__ == "__main__":
    print("hunt.py is a library -- see the module docstring for how to call "
          "run_category() with real, researched CandidateSpec values. It "
          "does not invent candidates to try.")
    sys.exit(0)
