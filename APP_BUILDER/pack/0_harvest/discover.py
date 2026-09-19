#!/usr/bin/env python3
"""
discover.py -- Section 31's record-keeping half.

This session has no working GitHub-wide search API (this environment's
GitHub access is scoped to this repository only -- see the module docstring
in hunt.py) and no djangopackages.org/PyPI-search automation was built for
the same reason. Section 31's *queries* were run for real, by hand, using
WebSearch against the live web -- the same discipline hunt.py's own
docstring already establishes for candidate research ("Candidates are
supplied to run_category() as CandidateSpec values that someone -- a
person, or an agent that has actually read the real repository -- has
already researched and can stand behind").

What this module DOES automate: Section 31's own instruction that "every
query run and every repo returned, including the ones filtered out" gets
recorded in DISCOVERY.md, in the same place and the same shape a
programmatic search would have written it. A DiscoveryRun is filled from
real WebSearch results (never invented), then rendered here.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DiscoveryHit:
    repo_name: str
    repo_url: str
    kept: bool
    filter_reason: str = ""  # non-empty when kept is False


@dataclass
class DiscoveryRun:
    category_name: str
    category_slug: str
    exemplar: str
    queries: list = field(default_factory=list)      # the exact query strings run
    hits: list = field(default_factory=list)          # DiscoveryHit, every repo returned
    source: str = "WebSearch (live web search; no GitHub-wide search API available to this session)"


def queries_for(category_name: str, exemplar: str, secondary_exemplar: str = None):
    """Section 31's own query template, so every category's DISCOVERY.md
    shows the same reproducible pattern regardless of who filled it."""
    words = [w.lower() for w in category_name.split() if len(w) > 2]
    q = [f"{category_name.lower()} django github", "django " + " ".join(words)]
    for w in words:
        q.append(f"django {w}")
    q.append(f"topic:django {' '.join(words)}")
    if exemplar:
        q += [
            f"open source {exemplar} alternative django",
            f"{exemplar} clone django",
            f"self-hosted {exemplar}",
        ]
    if secondary_exemplar:
        q += [
            f"open source {secondary_exemplar} alternative django",
            f"{secondary_exemplar} clone django",
        ]
    return q


def write_discovery_md(run: DiscoveryRun, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# DISCOVERY — {run.category_name}", "",
        f"exemplar: {run.exemplar}",
        f"source: {run.source}",
        "",
        "## Queries run",
    ]
    for q in run.queries:
        lines.append(f"  - {q!r}")
    lines += ["", "## Every repository returned (kept and filtered out)"]
    kept = [h for h in run.hits if h.kept]
    dropped = [h for h in run.hits if not h.kept]
    lines.append(f"kept for cloning: {len(kept)}")
    lines.append(f"filtered out: {len(dropped)}")
    lines.append("")
    lines.append("| Repository | Kept | Reason filtered out |")
    lines.append("|------------|------|----------------------|")
    for h in run.hits:
        lines.append(f"| {h.repo_url} | {'yes' if h.kept else 'no'} | {h.filter_reason or '-'} |")
    lines.append("")
    (out_dir / "DISCOVERY.md").write_text("\n".join(lines) + "\n")
    return out_dir / "DISCOVERY.md"
