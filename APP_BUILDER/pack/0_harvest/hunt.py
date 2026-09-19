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

# ---- EXEMPLAR (Section 26) ----
REGISTRY_PATH = "../CATEGORY_REGISTRY.json"
# The canonical 70-category list the production harvest loops over
# (Section 24/28). A category id or slug passed to run_category() is looked
# up here so results can be labelled and ranked consistently; hunt.py itself
# still runs whatever categories it is called with -- see
# run_registry_harvest.py for the --categories all driver.

EXEMPLAR_FEATURES_PATH = "../EXEMPLAR_FEATURES.json"
# Section 26.1. Sam edits this; hunt.py only reads it. A category id with no
# entry here is recorded as feature_match NOT MEASURED (reason: not yet
# researched) -- distinct from an entry that exists with an empty features
# list and a stated reason (exemplar has no public feature page).

MIN_FEATURE_MATCH = 0.0
# Section 26.3. Floor on exemplar feature match (0.0-1.0). At 0.0 it only
# ranks eligible candidates. Raise it and a category whose best gated
# candidate falls below records NONE ADMITTED with the reason stated.

DOCS_ONLY_WEIGHT = 0.5
# Section 26.2. How much a feature found only in README/docs counts,
# against 1.0 for a feature found in code.

LIBRARY_INDEX_PATH = "../../GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md"
# Section 25. The existing file the repository's own governance layer names
# for the library (APP_LIBRARY_MANIFEST.md). Its pre-existing content refers
# to an older, unrelated verification/ and OUTPUT_LIBRARY/ tree that is not
# present in this checkout -- that is a pre-existing condition of this file,
# not something this harvester created or is asked to repair. Winners from
# this harvest are appended under a clearly separate, clearly labelled
# section (see records.py's write_library_index()), never mixed into or
# overwriting the older content.

# ---- SCORING WEIGHTS (Section 34) ----
W_COMMITS = 1.0
W_CONTRIBUTORS = 1.0
W_RELEASES = 1.0
W_TESTS = 1.0
W_DOCS = 1.0
W_ISSUE_CLOSURE = 2.0
W_THIRD_PARTY_PLUGINS = 2.0
# Weights inside the quality score (log1p on the count-shaped components, so
# one candidate with ten thousand commits doesn't drown everything else).
# Ranking within a category is exemplar feature match first, this score
# second (Section 26.3) -- neither overrides a Section 32 gate.

STOP_ON_FIRST_ERROR = False
# True = one candidate raising an unexpected exception halts the whole run.
# False = the error is recorded against that candidate as REJECTED and the
# run continues to the next one.

# =====================================================================
# Nothing below here needs editing
# =====================================================================

import math
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
sys.path.insert(0, str((HERE / HARVEST_PARTS_PATH).resolve().parent))
import attach_points as AP  # noqa: E402  (lives beside harvest_parts.py)
import exemplar_match as EM  # noqa: E402


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
    # recency/contributor/tag counts. clone_candidate() does a full clone by
    # default, so `git fetch --unshallow` would fail (there is nothing to
    # unshallow) and silently zero out this whole metric group -- checked
    # for real via rev-parse rather than assumed either way.
    is_shallow = run(["git", "rev-parse", "--is-shallow-repository"], cwd=path).stdout.strip() == "true"
    if is_shallow:
        r = run(["git", "fetch", "--quiet", "--unshallow"], cwd=path, timeout=CLONE_TIMEOUT_SECONDS)
        unshallow_ok = r.returncode == 0
    else:
        unshallow_ok = True

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
    """Section 34's formula:

        score = W_COMMITS*log1p(commits_6m) + W_CONTRIBUTORS*log1p(contributors)
              + W_RELEASES*log1p(releases) + W_TESTS*tests_present + W_DOCS*docs_present
              + W_ISSUE_CLOSURE*issue_closure + W_THIRD_PARTY_PLUGINS*log1p(third_party_plugins)

    commits/contributors/releases are real, from the clone's own git
    history (git_quality_metrics()). tests_present is a real filesystem
    heuristic. docs_present and third_party_plugins come from the
    CandidateSpec's researcher-supplied fields (plugin_authoring_docs_present
    and the length of third_party_plugin_evidence) -- this script has no
    GitHub API access to confirm them independently (documented in the
    module docstring), so they are recorded as researcher-supplied, not
    computed, wherever they appear in a report.

    issue_closure_ratio has no real data source available to this script at
    all (no GitHub API access -- see module docstring) and is scored 0
    rather than guessed; every report states this plainly rather than
    burying it inside a total.

    This score ranks otherwise-eligible candidates against each other. It
    never overrides check_admission()'s hard gates -- see run_candidate()."""
    components = {}
    components["commits_last_6_months"] = W_COMMITS * math.log1p(metrics.get("commits_last_6_months") or 0)
    components["contributors"] = W_CONTRIBUTORS * math.log1p(metrics.get("contributors") or 0)
    components["tagged_releases"] = W_RELEASES * math.log1p(metrics.get("tagged_releases") or 0)
    components["test_suite_present"] = W_TESTS if metrics.get("test_suite_present_heuristic") else 0.0
    components["plugin_authoring_docs"] = W_DOCS if spec.plugin_authoring_docs_present else 0.0
    components["issue_closure_ratio"] = 0.0  # not collected -- no data source, see docstring
    third_party_count = len(spec.third_party_plugin_evidence) if spec.third_party_plugins_present else 0
    components["third_party_plugins"] = W_THIRD_PARTY_PLUGINS * math.log1p(third_party_count)
    return round(sum(components.values()), 4), components


def _category_dict(category):
    """Accepts either a plain category-name string (back-compat with the
    3-category pilot) or a registry entry dict {id, category, slug,
    exemplar}. Normalizes to a dict with a "name" key and a "slug"."""
    if isinstance(category, dict):
        d = dict(category)
        d.setdefault("name", d.get("category"))
        d.setdefault("slug", re.sub(r"[^a-z0-9]+", "-", d["name"].lower()).strip("-"))
        return d
    return {"id": None, "name": category, "category": category,
            "slug": re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-"),
            "exemplar": None}


_EXEMPLAR_FEATURES_CACHE = None


def _exemplar_entry(cat: dict):
    global _EXEMPLAR_FEATURES_CACHE
    if cat.get("id") is None:
        return None, "category has no registry id (pre-registry pilot run)"
    if _EXEMPLAR_FEATURES_CACHE is None:
        path = (HERE / EXEMPLAR_FEATURES_PATH).resolve()
        if not path.is_file():
            return None, f"EXEMPLAR_FEATURES.json not found at {path}"
        _EXEMPLAR_FEATURES_CACHE = EM.load_exemplar_features(path)
    entry = _EXEMPLAR_FEATURES_CACHE.get(cat["id"])
    if entry is None:
        return None, "EXEMPLAR_FEATURES.json has no entry for this category yet"
    return entry, None


def run_candidate(category, spec: CandidateSpec):
    """Clone, sweep, score, mechanically measure attach points (Section 33),
    check admission, measure exemplar feature match (Section 26.2), write
    the candidate's report. Never writes to the shelf. Returns a result
    dict for the category summary."""
    cat = _category_dict(category)
    cand_slug = re.sub(r"[^a-z0-9]+", "-", spec.repo_name.lower()).strip("-")
    out_dir = (HERE / OUTPUT_DIR / cat["slug"] / cand_slug).resolve()
    evidence_dir = out_dir / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== {cat['name']} :: {spec.repo_name} ===")
    path, resolved_commit, clone_err = clone_candidate(spec)

    result = {
        "category": cat, "repo_name": spec.repo_name,
        "repo_url": spec.repo_url, "commit": resolved_commit or spec.commit,
        "admission_result": None, "rejection_reasons": [], "quality_score": None,
        "feature_match": None, "out_dir": str(out_dir),
    }

    if clone_err:
        result["admission_result"] = "REJECTED"
        result["rejection_reasons"] = [f"could not verify the real repository: {clone_err}"]
        fm = EM.not_measured_result(f"rejected before clone: {clone_err}")
        (out_dir / "REPORT.md").write_text(
            f"# {spec.repo_name}\n\nREJECTED\n\ncould not verify the real "
            f"repository: {clone_err}\n")
        (out_dir / "FEATURE_MATCH.md").write_text(EM.render_feature_match_md(spec.repo_name, fm))
        print(f"  REJECTED -- {clone_err}")
        return result

    signal_hits = keyword_signal_sweep(path)
    metrics = git_quality_metrics(path)
    score, score_components = quality_score(metrics, spec, len(signal_hits))

    # Section 33: mechanical attach-point measurement from the real clone,
    # never from documentation or a researcher's claim. This is the primary
    # source; any ADAPTER points a researcher supplied on the CandidateSpec
    # (an attach point our own system would have to build) are additive and
    # kept, never claimed NATIVE by this merge.
    measured = AP.measure_attach_points(path, require_model_signals_count=HP.REQUIRE_MODEL_SIGNALS_COUNT)
    mechanical_usable = measured["usable_total"]
    adapter_supplied = [a for a in (spec.attach_points or [])
                        if (a.get("implementation") or "").strip().upper() == "ADAPTER"]
    merged_attach_points = mechanical_usable + adapter_supplied

    src_for_gate = {
        "framework": spec.framework, "datastore": spec.datastore,
        "licence": spec.licence, "api_docs_url": spec.api_docs_url,
        "structural_match": spec.structural_match, "repo_name": spec.repo_name,
        "attach_points": merged_attach_points,
        "extension_system_description": measured["extension_system"]["evidence"] and
            "; ".join(measured["extension_system"]["evidence"])
            or spec.extension_system_description,
    }
    # The exact same function 1_harvest/harvest_parts.py will use later.
    reasons = HP.check_admission(src_for_gate, [], f"hunt:{spec.repo_name}")

    # PROVENANCE (Section 32): harvesting must not modify candidate source
    # (Section 13). Checked for real, after every read-only inspection step
    # above, not assumed clean.
    provenance_status = run(["git", "status", "--porcelain"], cwd=path).stdout.strip()
    if provenance_status:
        reasons.append(
            f"Provenance: the clone was modified during inspection "
            f"(git status --porcelain is non-empty): {provenance_status[:300]}")

    usable_aps = HP.usable_attach_points(merged_attach_points)
    admitted = not reasons
    result["admission_result"] = "ADMITTED" if admitted else "REJECTED"
    result["rejection_reasons"] = reasons
    result["quality_score"] = score

    ap_md = HP.render_attach_points_md(spec.repo_name, src_for_gate, merged_attach_points)
    (out_dir / "ATTACH_POINTS.md").write_text(ap_md)

    events = [a for a in usable_aps if a.get("kind", "").upper() == "EVENT"]
    slots = [a for a in usable_aps if a.get("kind", "").upper() == "SLOT"]
    data_pts = [a for a in usable_aps if a.get("kind", "").upper() == "DATA"]

    # Section 26.2 -- exemplar feature match. A rejected candidate is never
    # measured (Section 26.5): the clone failed the gate, so ranking it
    # against the exemplar would be comparing something not admitted.
    if admitted:
        entry, no_entry_reason = _exemplar_entry(cat)
        if entry is not None:
            fm = EM.measure_feature_match(path, entry, docs_only_weight=DOCS_ONLY_WEIGHT)
        else:
            fm = EM.not_measured_result(no_entry_reason)
    else:
        fm = EM.not_measured_result(f"rejected at gate(s): {'; '.join(reasons)}")
    result["feature_match"] = fm["feature_match"]
    result["feature_match_detail"] = fm
    (out_dir / "FEATURE_MATCH.md").write_text(EM.render_feature_match_md(spec.repo_name, fm))

    report = [
        f"# {spec.repo_name}", "",
        f"category: {cat['name']}" + (f" (id {cat['id']}, slug {cat['slug']})" if cat.get("id") else ""),
        f"repository: {spec.repo_name}",
        f"repository URL: {spec.repo_url}",
        f"exact commit: {resolved_commit}",
        f"licence: {spec.licence}",
        f"framework: {spec.framework}",
        f"datastore: {spec.datastore}",
        "",
        "## Attach points (Section 33 -- mechanically measured from the real clone)",
        f"hook/signal keyword-sweep hits: {len(signal_hits)} distinct terms "
        f"(discovery signal only, not proof -- see keyword_hits below)",
        f"usable, evidenced attach-point count: {len(usable_aps)}",
        f"  event attach points: {len(events)}",
        f"  slot attach points: {len(slots)}",
        f"  data attach points: {len(data_pts)}",
        f"defined-but-unusable points measured (not counted): "
        f"{len(measured['all_measured']) - len(mechanical_usable)}",
        "",
        "## Extension system evidence",
    ]
    if measured["extension_system"]["evidence"]:
        for e in measured["extension_system"]["evidence"]:
            report.append(f"  - {e}")
    else:
        report.append("  (none mechanically found)")
    report += [
        f"plugin-authoring documentation (mechanically found): "
        f"{'yes -- ' + measured['extension_system']['plugin_authoring_docs_location'] if measured['extension_system']['plugin_authoring_docs_present'] else 'no'}",
        "",
        "## Documentation and ecosystem (researcher-supplied, not computed -- no GitHub API access)",
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
        f"was available to this script (no GitHub API access for repositories "
        f"outside this session's own repo, see module docstring); this is a "
        f"stated gap, not a silent zero.",
        "",
        "## Exemplar feature match (Section 26.2)",
        f"exemplar: {fm.get('exemplar') or cat.get('exemplar') or '(none)'}",
        f"features checked: {fm['features_checked']}  matched(code): {fm['features_matched']}  "
        f"docs-only: {fm['docs_only']}  not found: {fm['not_found']}",
        f"feature_match: {fm['feature_match']:.2f}" if fm['feature_match'] is not None
            else f"feature_match: NOT MEASURED ({fm.get('note')})",
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

    # Evidence: everything real, verbatim.
    (evidence_dir / "keyword_signal_sweep.json").write_text(json.dumps(signal_hits, indent=2))
    (evidence_dir / "git_quality_metrics.json").write_text(json.dumps(metrics, indent=2))
    (evidence_dir / "quality.json").write_text(json.dumps(
        {"components": score_components, "total": score}, indent=2))
    (evidence_dir / "candidate_spec.json").write_text(json.dumps(asdict(spec), indent=2))
    (evidence_dir / "attach_points.json").write_text(json.dumps(measured, indent=2))
    (evidence_dir / "feature_match.json").write_text(json.dumps(fm, indent=2))
    (evidence_dir / "gates.json").write_text(json.dumps(
        {"admission_result": result["admission_result"], "rejection_reasons": reasons}, indent=2))
    (evidence_dir / "provenance.txt").write_text(
        f"repo_url: {spec.repo_url}\ncommit: {resolved_commit}\n"
        f"clone_date: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n")

    print(f"  {result['admission_result']}  score={score}  "
          f"feature_match={fm['feature_match']}  attach_points={len(usable_aps)}  "
          f"commit={resolved_commit[:12] if resolved_commit else '?'}")
    if reasons:
        for r_ in reasons:
            print(f"    - {r_}")

    return result


def _rank_key(r):
    # Section 26.3: exemplar feature match first (None/NOT MEASURED sorts
    # last), quality score as tiebreak.
    fm = r["feature_match"]
    return (fm if fm is not None else -1.0, r["quality_score"] or 0.0)


def write_category_summary(category, results: list):
    cat = _category_dict(category)
    out_dir = (HERE / OUTPUT_DIR / cat["slug"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    eligible = [r for r in results if r["admission_result"] == "ADMITTED"]
    rejected = [r for r in results if r["admission_result"] == "REJECTED"]
    ranked = sorted(eligible, key=_rank_key, reverse=True)

    winner = None
    floor_reason = None
    if ranked:
        top = ranked[0]
        top_fm = top["feature_match"] if top["feature_match"] is not None else 0.0
        if top_fm < MIN_FEATURE_MATCH:
            floor_reason = (f"best feature match {top_fm:.2f} below "
                            f"MIN_FEATURE_MATCH {MIN_FEATURE_MATCH:.2f}")
        else:
            winner = top

    lines = [
        f"# CATEGORY_SUMMARY — {cat['name']}", "",
        f"category: {cat['name']}" + (f" (id {cat['id']}, slug {cat['slug']})" if cat.get("id") else ""),
        f"exemplar: {cat.get('exemplar') or '(not recorded)'}",
        f"candidates inspected: {len(results)}",
        f"candidates passing hard gates (ADMITTED): {len(eligible)}",
        f"candidates rejected: {len(rejected)}",
        "",
        "## Rankings (eligible candidates only -- feature match first, quality score tiebreak)",
    ]
    for r in ranked:
        fm_s = f"{r['feature_match']:.2f}" if r["feature_match"] is not None else "N/A"
        lines.append(f"  feature_match={fm_s}  quality={r['quality_score']:.2f}  "
                     f"{r['repo_name']}  ({r['commit']})")
    lines += ["", "## Rejected, with reasons"]
    for r in rejected:
        lines.append(f"  {r['repo_name']}:")
        for reason in r["rejection_reasons"]:
            lines.append(f"    - {reason}")
    lines += ["", "## Selected candidate"]
    if winner:
        fm_s = f"{winner['feature_match']:.2f}" if winner["feature_match"] is not None else "N/A"
        lines.append(f"**{winner['repo_name']}** @ {winner['commit']}  "
                     f"(feature_match {fm_s} vs {cat.get('exemplar') or '(exemplar not recorded)'}, "
                     f"quality {winner['quality_score']:.2f})")
    else:
        lines.append("**NONE ADMITTED**")
        lines.append("")
        if not results:
            reason = "no candidates were inspected for this category"
        elif floor_reason:
            reason = floor_reason
        else:
            reason = ("every inspected candidate failed at least one hard admission rule "
                      "-- see each candidate's own REPORT.md for which")
        lines.append("Reason: " + reason)
    (out_dir / "CATEGORY_SUMMARY.md").write_text("\n".join(lines) + "\n")
    return winner


def write_harvest_summary(category_results: dict):
    """category_results: {category_key: (winner_or_None, all_results, cat_dict)}"""
    out_dir = (HERE / OUTPUT_DIR).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = ["# HARVEST_SUMMARY", ""]
    for _key, (winner, results, cat) in category_results.items():
        lines.append(f"## {cat['name']}" + (f" (id {cat['id']})" if cat.get("id") else ""))
        lines.append(f"candidates inspected: {len(results)}")
        if winner:
            fm_s = f"{winner['feature_match']:.2f}" if winner["feature_match"] is not None else "N/A"
            lines.append(f"selected: ADMITTED {winner['repo_name']} @ {winner['commit']} "
                         f"match {fm_s} vs {cat.get('exemplar') or '(exemplar not recorded)'}")
        else:
            lines.append("selected: NONE ADMITTED")
        lines.append("")
    (out_dir / "HARVEST_SUMMARY.md").write_text("\n".join(lines) + "\n")


_LIBRARY_SECTION_HEADING = "## Django/PostgreSQL Attach-Point Harvest — Library Index"
_LIBRARY_TABLE_HEADER = ("| # | Category | Exemplar | Feature match | Repository | Commit | "
                         "Licence | Attach points |")
_LIBRARY_TABLE_RULE = "|---|----------|----------|----------------|------------|--------|---------|---------------|"


def write_library_index(winners: list):
    """Section 25. winners: [{"category": cat_dict, "repo_name", "repo_url",
    "commit", "licence", "feature_match", "attach_point_count"}, ...] --
    ADMITTED winners only; a NONE ADMITTED category never calls this.

    Appends to the existing library index file (LIBRARY_INDEX_PATH) under a
    clearly separate, clearly labelled section. Never touches the file's
    pre-existing content above that section -- see the CONFIG comment on
    LIBRARY_INDEX_PATH for why that content is left alone rather than
    "fixed"."""
    path = (HERE / LIBRARY_INDEX_PATH).resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"LIBRARY_INDEX_PATH does not exist: {path} -- Section 25 says stop and "
            f"report rather than invent one. This path is CONFIG-set to the file the "
            f"repository's own governance layer already names for the library "
            f"(APP_LIBRARY_MANIFEST.md); if that file has moved, update LIBRARY_INDEX_PATH.")

    text = path.read_text()
    if _LIBRARY_SECTION_HEADING in text:
        head, _, _tail_after_heading = text.partition(_LIBRARY_SECTION_HEADING)
        existing_rows = []
        for line in _tail_after_heading.splitlines():
            if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                existing_rows.append(line)
        next_n = len(existing_rows) + 1
        new_lines = existing_rows
    else:
        head = text.rstrip("\n") + "\n\n"
        next_n = 1
        new_lines = []

    for w in winners:
        cat = w["category"]
        fm = f"{w['feature_match']:.2f}" if w.get("feature_match") is not None else "N/A"
        row = (f"| {next_n} | {cat['name']} | {cat.get('exemplar') or '(not recorded)'} | {fm} | "
              f"{w['repo_url']} | {w['commit']} | {w['licence']} | {w['attach_point_count']} |")
        new_lines.append(row)
        next_n += 1

    rebuilt = (head + _LIBRARY_SECTION_HEADING + "\n\n"
              + "Entries below are written only by pack/0_harvest/hunt.py's "
                "write_library_index(), one row per ADMITTED category winner "
                "(Section 25). A category recorded NONE ADMITTED gets no row.\n\n"
              + _LIBRARY_TABLE_HEADER + "\n" + _LIBRARY_TABLE_RULE + "\n"
              + "\n".join(new_lines) + "\n")
    path.write_text(rebuilt)
    return path, next_n - 1


def run_category(category, specs: list):
    """Run every candidate in one category, write CATEGORY_SUMMARY.md,
    return (winner_or_None, all_results). Stops there -- promotion is a
    separate, explicit step."""
    cat = _category_dict(category)
    results = []
    for s in specs:
        if STOP_ON_FIRST_ERROR:
            results.append(run_candidate(cat, s))
        else:
            try:
                results.append(run_candidate(cat, s))
            except Exception as e:  # noqa: BLE001 -- recorded, not swallowed
                results.append({
                    "category": cat, "repo_name": s.repo_name, "repo_url": s.repo_url,
                    "commit": s.commit, "admission_result": "REJECTED",
                    "rejection_reasons": [f"unhandled error while inspecting: {e!r}"],
                    "quality_score": None, "feature_match": None,
                })
                print(f"  REJECTED -- unhandled error: {e!r}")
    winner = write_category_summary(cat, results)
    return winner, results


if __name__ == "__main__":
    print("hunt.py is a library -- see the module docstring for how to call "
          "run_category() with real, researched CandidateSpec values. It "
          "does not invent candidates to try.")
    sys.exit(0)
