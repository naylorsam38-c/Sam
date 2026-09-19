#!/usr/bin/env python3
"""
discover_candidates.py — Stage 1 (DISCOVER) of the acquisition gate.

Source: the open-source ecosystem, per spec section 2 — not tied to any one
website. Primary source is the awesome-selfhosted-data directory (cloned via
plain git, unlimited, machine-readable: licence, stars, last commit, archived
flag). GitHub's search API is a documented, rate-limited (30 req/hour)
supplement for categories the directory covers poorly — those are called out
separately so the orchestrating session can spend that budget deliberately
rather than by accident.

Output: 52_APP_LIBRARY/candidates.json — every category's matched entries,
sorted by stars, with a flag for categories that need GitHub-search
supplementation (fewer than MIN_CANDIDATES_BEFORE_SUPPLEMENT real matches).
This is discovery only — no licence/screens/runs gate applied here.
"""
import json
import re
import yaml
from pathlib import Path
from datetime import date, datetime

HERE = Path(__file__).resolve().parent
DIRECTORY_DIR = Path("/tmp/selfhosted_directory")
CATEGORY_FILE = HERE / "categories_openapps52.json"
OUT_FILE = HERE / "candidates.json"
MIN_CANDIDATES_BEFORE_SUPPLEMENT = 3
MIN_STARS = 100


def load_directory():
    entries = []
    for f in sorted((DIRECTORY_DIR / "software").glob("*.yml")):
        e = yaml.safe_load(f.read_text())
        if isinstance(e, dict) and e.get("source_code_url"):
            entries.append(e)
    return entries


def months_since(iso_date):
    try:
        d = datetime.strptime(str(iso_date)[:10], "%Y-%m-%d").date()
    except Exception:
        return None
    today = date.today()
    return (today.year - d.year) * 12 + (today.month - d.month)


def matches(entry, keywords):
    text = f"{entry.get('name','')} {entry.get('description','')}".lower()
    tags = set(t.lower() for t in entry.get("tags", []))
    hits = []
    for kw in keywords:
        kwl = kw.lower()
        if kwl in tags or re.search(r"(?<![a-z0-9])" + re.escape(kwl) + r"(?![a-z0-9])", text):
            hits.append(kw)
    return hits


def main():
    cats = json.loads(CATEGORY_FILE.read_text())["categories"]
    entries = load_directory()
    print(f"directory: {len(entries)} entries with a source URL")

    out = {}
    needs_supplement = []
    for c in cats:
        kws = c["keywords"]
        cands = []
        for e in entries:
            if e.get("archived"):
                continue
            if (e.get("stargazers_count") or 0) < MIN_STARS:
                continue
            hits = matches(e, kws)
            if not hits:
                continue
            m = months_since(e.get("updated_at"))
            if m is not None and m > 18:
                continue
            cands.append({
                "name": e.get("name"), "source_code_url": e.get("source_code_url"),
                "stargazers_count": e.get("stargazers_count") or 0,
                "licenses": e.get("licenses") or [], "updated_at": e.get("updated_at"),
                "description": e.get("description"), "matched_keywords": hits,
                "discovery_source": "awesome-selfhosted",
            })
        cands.sort(key=lambda x: -x["stargazers_count"])
        out[c["slug"]] = cands[:15]
        if len(cands) < MIN_CANDIDATES_BEFORE_SUPPLEMENT:
            needs_supplement.append(c["slug"])

    OUT_FILE.write_text(json.dumps({"candidates": out, "needs_github_search_supplement": needs_supplement},
                                    indent=1))
    print(f"wrote {OUT_FILE}")
    print(f"{len(needs_supplement)}/52 categories have fewer than {MIN_CANDIDATES_BEFORE_SUPPLEMENT} "
          f"awesome-selfhosted candidates and need GitHub-search supplementation:")
    for s in needs_supplement:
        print(f"  {s}  ({len(out[s])} found)")


if __name__ == "__main__":
    main()
