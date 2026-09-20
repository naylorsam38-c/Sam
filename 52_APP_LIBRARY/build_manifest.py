#!/usr/bin/env python3
"""
build_manifest.py — merges the two discovery sources (awesome-selfhosted-data
via candidates.json, GitHub search via github_search_supplement.json) and
picks ONE app per category for the fixed 52-slot manifest, per spec section 3.

Selection at this stage is provisional: highest stars, not archived. It is
NOT the licence/screens/runs verdict — those gates run later, per app, and
can replace this pick with the next-ranked candidate if this one fails
acquisition (spec section 4/16: ACQUISITION_FAILED does not stop the run,
it moves to the next candidate).

Output: manifest.json (52 entries, status DISCOVERED or DISCOVERY_FAILED),
applications/APP-0XX/ directories with a first-cut app.json each.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
CATEGORY_FILE = HERE / "categories_openapps52.json"
CANDIDATES_FILE = HERE / "candidates.json"
SUPPLEMENT_FILE = HERE / "github_search_supplement.json"
MANIFEST_FILE = HERE / "manifest.json"
APPS_DIR = HERE / "applications"

# Manual correction pass. The automated pick (highest-star candidate whose own
# description contains a category keyword) got fooled by a stray-word match in
# a handful of categories - e.g. "browser" -> code-server, because its
# description says "VS Code in the browser" (a web IDE, not a browser).
# Verified against real GitHub repos (mcp__github__search_repositories), not
# invented. None = deliberately left DISCOVERY_FAILED rather than forced.
MANUAL_OVERRIDES = {
    "browser": {"name": "Neko", "source_code_url": "https://github.com/m1k1o/neko",
                "stargazers_count": 22330, "licenses": ["Apache-2.0"],
                "description": "Virtual browser that runs in docker and uses WebRTC.",
                "override_reason": "automated pick (code-server) matched 'browser' as a stray word "
                                    "in 'VS Code in the browser' - it's a web IDE, not a browser app"},
    "social-media": {"name": "Postiz", "source_code_url": "https://github.com/gitroomhq/postiz-app",
                      "stargazers_count": 36052, "licenses": ["AGPL-3.0"],
                      "description": "Schedule posts, track the performance of your content, and manage "
                                      "all your social media accounts.",
                      "override_reason": "automated pick (RSSHub) is an RSS feed aggregator, not a "
                                          "social-media app"},
    "productivity": {"name": "Super Productivity", "source_code_url": "https://github.com/super-productivity/super-productivity",
                      "stargazers_count": 22121, "licenses": ["MIT"],
                      "description": "Advanced todo list app with integrated timeboxing and time tracking.",
                      "override_reason": "automated pick (4ga Boards) is a minor kanban board; this is "
                                          "the well-established, higher-star fit that didn't literally "
                                          "contain the word 'productivity' in its description"},
    "monitoring": {"name": "Uptime Kuma", "source_code_url": "https://github.com/louislam/uptime-kuma",
                    "stargazers_count": 91557, "licenses": [],
                    "description": "A fancy self-hosted monitoring tool.",
                    "override_reason": "automated pick (Pi-hole) is primarily a DNS/ad-blocker; this is "
                                        "the category-defining self-hosted monitoring tool"},
    "video-editors": {"name": "OpenReel Video", "source_code_url": "https://github.com/Augani/openreel-video",
                       "stargazers_count": 5124, "licenses": [],
                       "description": "OpenReel Video - Professional browser-based video editor. Open "
                                       "source CapCut alternative. 100% browser-based, no installation.",
                       "override_reason": "automated pick (Dawarich) is a location/travel tracker matched "
                                           "on the stray keyword 'timeline'; no real video editor was in "
                                           "either discovery source's candidate pool for this category"},
    "networking": {"name": "Nginx Proxy Manager", "source_code_url": "https://github.com/NginxProxyManager/nginx-proxy-manager",
                    "stargazers_count": 34175, "licenses": ["MIT"],
                    "description": "Docker container for managing Nginx proxy hosts with a simple, "
                                    "powerful interface.",
                    "override_reason": "per Sam's instruction that popularity/sandbox limits are never a "
                                        "valid exclusion reason, re-searched GitHub directly instead of "
                                        "leaving this DISCOVERY_FAILED. First picked Headscale (a "
                                        "self-hosted Tailscale control server), but it's a pure CLI/API "
                                        "coordination daemon with no web UI of its own - nothing for "
                                        "screens.py/capabilities.py to browser-test - so switched to this: "
                                        "a real networking tool (reverse-proxy/traffic management) with a "
                                        "genuine web dashboard and its own verified MIT LICENSE file"},
    "developer-tools": {"name": "code-server", "source_code_url": "https://github.com/coder/code-server",
                         "stargazers_count": 79356, "licenses": ["MIT"],
                         "description": "VS Code in the browser.",
                         "override_reason": "the earlier 'browser' category override (Neko) exists "
                                             "precisely because code-server is a developer tool, not a "
                                             "browser - it belongs here instead; verified MIT LICENSE file"},
    "logistics": {"name": "shiptrack", "source_code_url": "https://github.com/Aswincloud/shiptrack",
                  "stargazers_count": 1, "licenses": ["MIT"],
                  "description": "Free, open-source, self-hostable shipment tracking for Indian & "
                                  "international couriers.",
                  "override_reason": "self-hosted logistics/shipment-tracking software is a genuinely "
                                      "rare niche in open source (openapps.pro itself lists only 1 app "
                                      "for this whole category) - this is a real, low-star-but-legitimate "
                                      "fit directly matching the category's own description ('self-host "
                                      "... shipment tracking'), picked deliberately despite its low star "
                                      "count per Sam's instruction that popularity is never a valid "
                                      "exclusion reason; verified MIT LICENSE file"},
}


def main():
    cats = json.loads(CATEGORY_FILE.read_text())["categories"]
    directory_cands = json.loads(CANDIDATES_FILE.read_text())["candidates"]
    supplement = json.loads(SUPPLEMENT_FILE.read_text())["candidates"]

    entries = []
    now = datetime.now(timezone.utc).isoformat()
    for i, c in enumerate(cats, 1):
        slug = c["slug"]
        pool = list(directory_cands.get(slug, [])) + list(supplement.get(slug, []))
        # de-duplicate by repo URL, keep highest star count seen
        by_url = {}
        for cand in pool:
            u = (cand.get("source_code_url") or "").rstrip("/").lower()
            if not u:
                continue
            if u not in by_url or (cand.get("stargazers_count") or 0) > (by_url[u].get("stargazers_count") or 0):
                by_url[u] = cand
        ranked = sorted(by_url.values(), key=lambda x: -(x.get("stargazers_count") or 0))

        # Prefer a candidate that declares itself as this kind of app in its own
        # description (category label or a keyword phrase) over one that only
        # matched by loose tag/keyword overlap - this is what catches
        # "Home Assistant" being picked for ai-assistants, or "ElasticSearch"
        # for analytics: real apps, wrong category, matched on a stray word.
        declare_phrases = [c["category"].lower()] + [k.lower() for k in c.get("keywords", [])]
        declared = [r for r in ranked if any(p in (r.get("description") or "").lower() for p in declare_phrases)]
        pick_pool = declared or ranked
        pick = pick_pool[0] if pick_pool else None
        override_reason = None
        if slug in MANUAL_OVERRIDES:
            ov = MANUAL_OVERRIDES[slug]
            if ov is None:
                pick = None
            else:
                pick = ov
                override_reason = ov["override_reason"]
                # the override must actually be IN the candidate pool, not just
                # the top-level pick - acquire.py reads discovery_candidates,
                # not this entry's name/repository, when it cascades through
                # licence/acquisition failures.
                if not any((c.get("source_code_url") or "").rstrip("/").lower() ==
                           ov["source_code_url"].rstrip("/").lower() for c in ranked):
                    ranked = [ov] + ranked

        app_id = f"APP-{i:03d}"
        entry = {
            "id": app_id,
            "name": pick["name"] if pick else None,
            "category": c["category"],
            "category_slug": slug,
            "repository": pick["source_code_url"] if pick else None,
            "source_platform": "github.com",
            "licence": None,
            "version": None,
            "commit": None,
            "source_path": f"applications/{app_id}/source",
            "status": "DISCOVERED" if pick else "DISCOVERY_FAILED",
            "declared_itself": bool(declared) and not override_reason,
            "manual_override_reason": override_reason,
            "discovery_candidates": ranked,
            "discovery_failed_reason": None if pick else
                ("manually reviewed: no candidate in either discovery source is a genuine fit for this "
                 "category (see MANUAL_OVERRIDES in build_manifest.py)" if slug in MANUAL_OVERRIDES else
                 "no candidate found via awesome-selfhosted-data or GitHub search "
                 "(openapps.pro itself is blocked by this sandbox's egress policy, "
                 "per RULES.md-equivalent provenance note)"),
        }
        entries.append(entry)

        d = APPS_DIR / app_id
        (d / "source").mkdir(parents=True, exist_ok=True)
        (d / "test-results").mkdir(parents=True, exist_ok=True)
        (d / "evidence").mkdir(parents=True, exist_ok=True)
        (d / "app.json").write_text(json.dumps(entry, indent=1))

    manifest = {
        "generated_at": now,
        "target_count": 52,
        "category_source": "categories_openapps52.json (cached snapshot of openapps.pro's 52 categories; "
                            "the live site is blocked by this sandbox's egress policy, so candidate apps "
                            "come from awesome-selfhosted-data + GitHub search instead, per spec section 2)",
        "applications": entries,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=1))

    counts = {}
    for e in entries:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    print(f"TARGET APPLICATIONS: 52")
    print(f"DISCOVERED: {counts.get('DISCOVERED', 0)}")
    print(f"DISCOVERY_FAILED: {counts.get('DISCOVERY_FAILED', 0)}")
    if counts.get("DISCOVERY_FAILED"):
        print("  categories with no candidate at all:")
        for e in entries:
            if e["status"] == "DISCOVERY_FAILED":
                print(f"    {e['category_slug']}")


if __name__ == "__main__":
    main()
