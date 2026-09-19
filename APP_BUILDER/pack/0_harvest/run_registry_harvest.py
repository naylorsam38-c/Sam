#!/usr/bin/env python3
"""
run_registry_harvest.py -- the registry-driven driver (Section 24/28/37).

    python3 run_registry_harvest.py --categories all
    python3 run_registry_harvest.py --categories 1,25,27
    python3 run_registry_harvest.py --categories todo-list,appointment-booking
    python3 run_registry_harvest.py --categories 1,25,27 --dry-run

For every requested category (by registry id or slug), this script:
  1. loads that category's queries + WebSearch discovery record from
     candidates/<slug>.py (a real, hand-researched module -- see that
     module's own docstring convention, and hunt.py's docstring on why
     candidate discovery is researcher-supplied in this environment);
  2. writes DISCOVERY.md;
  3. (unless --dry-run) runs hunt.run_category() over every supplied
     CandidateSpec -- clone, mechanical attach-point measurement, gates,
     exemplar feature match, quality score, CATEGORY_SUMMARY.md;
  4. registers any ADMITTED winner in the library index.

At the end it writes HARVEST_SUMMARY.md (one line per category actually
processed -- Section 37's validation-run subset is explicitly allowed to be
fewer than the full registry; a --categories all run is expected to produce
exactly REGISTRY count lines, and Section 36 has a test for that) and prints
a plain-text run report to stdout that RUN_REPORT.md can capture verbatim.

A category with no candidates/<slug>.py yet is not silently skipped: it is
recorded as NONE ADMITTED with reason "no candidate research module for
this category yet" -- Section 24's "a category marked NONE ADMITTED must
not be silently filled with an inferior or incompatible application" cuts
both ways; it also must not be silently left out of the summary.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hunt as H  # noqa: E402
import discover as D  # noqa: E402

REGISTRY_PATH = HERE / H.REGISTRY_PATH
CANDIDATES_DIR = HERE / "candidates"


def load_registry():
    with open(REGISTRY_PATH) as f:
        data = json.load(f)
    return data["categories"]


def select_categories(registry, spec):
    if spec == "all":
        return registry
    wanted = {s.strip() for s in spec.split(",") if s.strip()}
    out = []
    for cat in registry:
        if str(cat["id"]) in wanted or cat["slug"] in wanted:
            out.append(cat)
    missing = wanted - {str(c["id"]) for c in out} - {c["slug"] for c in out}
    if missing:
        print(f"WARNING: not found in registry, skipped: {sorted(missing)}")
    return out


def load_candidate_module(slug):
    path = CANDIDATES_DIR / f"{slug}.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"candidates_{slug}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--categories", required=True,
                    help="'all', comma-separated ids, or comma-separated slugs")
    ap.add_argument("--dry-run", action="store_true",
                    help="discovery only, no clones, prints what would be inspected")
    args = ap.parse_args()

    registry = load_registry()
    selected = select_categories(registry, args.categories)
    if not selected:
        print("REFUSED: no matching categories in the registry")
        sys.exit(1)

    print(f"registry: {REGISTRY_PATH} ({len(registry)} categories)")
    print(f"selected: {len(selected)} categor{'y' if len(selected) == 1 else 'ies'}")
    if args.dry_run:
        print("DRY_RUN -- discovery only, nothing will be cloned or written except DISCOVERY.md\n")

    category_results = {}
    winners_for_index = []

    for cat in selected:
        print(f"\n{'=' * 70}\n{cat['category']}  (id {cat['id']}, slug {cat['slug']}, "
              f"exemplar {cat['exemplar']})\n{'=' * 70}")
        mod = load_candidate_module(cat["slug"])
        out_dir = HERE / H.OUTPUT_DIR / cat["slug"]

        if mod is None:
            print("  no candidates/<slug>.py for this category -- NONE ADMITTED "
                  "(no candidate research module yet)")
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "CATEGORY_SUMMARY.md").write_text(
                f"# CATEGORY_SUMMARY — {cat['category']}\n\n"
                f"candidates inspected: 0\ncandidates passing hard gates (ADMITTED): 0\n"
                f"candidates rejected: 0\n\n## Selected candidate\n**NONE ADMITTED**\n\n"
                f"Reason: no candidate research module for this category yet "
                f"(candidates/{cat['slug']}.py does not exist)\n")
            category_results[cat["slug"]] = (None, [], H._category_dict(cat))
            continue

        discovery_run = D.DiscoveryRun(
            category_name=cat["category"], category_slug=cat["slug"],
            exemplar=cat["exemplar"], queries=mod.QUERIES, hits=mod.HITS)
        D.write_discovery_md(discovery_run, out_dir)

        if args.dry_run:
            kept = [h for h in mod.HITS if h.kept]
            print(f"  would inspect {len(kept)} candidate(s): "
                  f"{', '.join(h.repo_name for h in kept)}")
            continue

        winner, results = H.run_category(cat, mod.CANDIDATES)
        category_results[cat["slug"]] = (winner, results, H._category_dict(cat))

        if winner:
            # attach point count for the library index: recomputed from the
            # winner's own evidence file, the same real numbers REPORT.md shows.
            ap_evidence = json.loads(Path(winner["out_dir"], "evidence", "attach_points.json").read_text())
            winners_for_index.append({
                "category": H._category_dict(cat),
                "repo_name": winner["repo_name"], "repo_url": winner["repo_url"],
                "commit": winner["commit"], "licence": next(
                    (s.licence for s in mod.CANDIDATES if s.repo_name == winner["repo_name"]), ""),
                "feature_match": winner["feature_match"],
                "attach_point_count": ap_evidence["counts"]["usable_total"],
            })

    if not args.dry_run:
        H.write_harvest_summary(category_results)
        if winners_for_index:
            path, total = H.write_library_index(winners_for_index)
            print(f"\nlibrary index updated: {path} ({len(winners_for_index)} new entr"
                  f"{'y' if len(winners_for_index) == 1 else 'ies'}, {total} total rows "
                  f"in the harvest section)")
        else:
            print("\nno ADMITTED winners this run -- library index untouched")

    print("\n\n=== RUN COMPLETE ===")
    for slug, (winner, results, cat) in category_results.items():
        status = (f"ADMITTED {winner['repo_name']} @ {winner['commit'][:12]} "
                  f"match {winner['feature_match']:.2f}" if winner else "NONE ADMITTED")
        print(f"{cat['name']}: {status}  ({len(results)} candidates inspected)")


if __name__ == "__main__":
    main()
