#!/usr/bin/env python3
"""Open Source Tools (open-source-tools.com) discovery adapter.

This is a DISCOVERY source only. It never admits an application. Candidates still
pass the existing repository licence, screen, run-recipe, category and later real
browser/capability gates.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.request
from pathlib import Path

SITE = "https://www.open-source-tools.com"
CATEGORIES_URL = SITE + "/categories/all"
USER_AGENT = "Mozilla/5.0 (library discovery adapter; capability proof engine)"
TIMEOUT = 30
DELAY = 0.25
CACHE_FILE = "open_source_tools/cache.json"
EXPECTED_CATEGORY_COUNT = 52


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    time.sleep(DELAY)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def _fetch_cached(url: str, cache_dir: Path, suffix: str = ".html") -> str:
    key = re.sub(r"[^A-Za-z0-9._-]+", "_", url.replace(SITE, "").strip("/")) or "home"
    path = cache_dir / f"{key[:180]}{suffix}"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    body = _fetch(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return body


def _text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()


def parse_categories(page: str) -> list[dict]:
    found = {}
    # Handles /categories/<slug> links used by the live directory.
    for m in re.finditer(r'href=["\']/categories/([^"\'/?#]+)[^>]*>(.*?)</a>', page, re.S | re.I):
        slug, inner = m.groups()
        name = _text(inner)
        name = re.sub(r"\s+", " ", name).strip()
        if name and slug not in {"all", "latest"}:
            found[slug] = {"slug": slug, "name": name}
    return list(found.values())


def _parse_cards(page: str) -> list[dict]:
    cards = []
    # Current pages use article/card-style markup. Keep parser deliberately tolerant.
    chunks = re.findall(r'<article\b([^>]*)>(.*?)</article>', page, re.S | re.I)
    if not chunks:
        chunks = re.findall(r'<div\b[^>]*class=["\'][^"\']*card[^"\']*["\'][^>]*>(.*?)</div>\s*(?=<div|<article|$)', page, re.S | re.I)
        chunks = [("", x) for x in chunks]
    for attrs, body in chunks:
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', body, re.I)
        app_href = next((h for h in hrefs if re.match(r"^/[a-z0-9][a-z0-9_-]*$", h, re.I)), None)
        if not app_href:
            continue
        name_m = re.search(r'<h[23][^>]*>(.*?)</h[23]>', body, re.S | re.I)
        name = _text(name_m.group(1)) if name_m else app_href.strip("/").replace("-", " ").title()
        desc_m = re.search(r'<p[^>]*>(.*?)</p>', body, re.S | re.I)
        desc = _text(desc_m.group(1)) if desc_m else ""
        stars = 0
        sm = re.search(r'(\d+(?:\.\d+)?)\s*k\b', _text(body), re.I)
        if sm:
            stars = int(float(sm.group(1)) * 1000)
        else:
            sm = re.search(r'([\d,]+)\s*(?:GitHub\s*)?stars?', _text(body), re.I)
            if sm:
                stars = int(sm.group(1).replace(",", ""))
        tags = [_text(x) for x in re.findall(r'<(?:span|a)[^>]*class=["\'][^"\']*(?:badge|tag)[^"\']*["\'][^>]*>(.*?)</(?:span|a)>', body, re.S | re.I)]
        cards.append({"name": name, "description": desc, "stars": stars,
                      "tags": tags, "href": app_href})
    # Fallback: canonical tool links on pages whose card HTML differs.
    if not cards:
        seen = set()
        for href in re.findall(r'href=["\'](/[a-z0-9][a-z0-9_-]*)["\']', page, re.I):
            if href in seen or href in ("/categories", "/categories/all"):
                continue
            seen.add(href)
            cards.append({"name": href.strip("/").replace("-", " ").title(),
                          "description": "", "stars": 0, "tags": [], "href": href})
    return cards


def parse_app_page(page: str) -> dict:
    result = {"repo": None, "license": None, "description": "", "language": None, "features": []}
    for block in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            d = json.loads(html.unescape(block))
        except Exception:
            continue
        if isinstance(d, dict):
            if d.get("@type") == "SoftwareApplication" or d.get("codeRepository"):
                result["repo"] = d.get("codeRepository") or d.get("downloadUrl") or result["repo"]
                result["license"] = d.get("license") or result["license"]
                result["language"] = d.get("programmingLanguage") or result["language"]
                result["description"] = d.get("description") or result["description"]
                result["features"] = d.get("featureList") or result["features"]
    # Common visible metadata fallbacks.
    if not result["repo"]:
        m = re.search(r'href=["\'](https?://(?:github|gitlab|codeberg)\\?\.[^"\']+)["\'][^>]*>[^<]*(?:GitHub|Repository|Source)', page, re.I)
        if m:
            result["repo"] = m.group(1)
    if not result["license"]:
        m = re.search(r'(?:License|Licence)\s*</[^>]+>\s*([^<]{2,40})', page, re.I)
        if m:
            result["license"] = _text(m.group(1))
    return result


def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if len(x) >= 3}


def match_category(source_name: str, source_slug: str, benchmark: dict) -> float:
    source = _tokens(source_name + " " + source_slug)
    target = _tokens(" ".join([
        benchmark.get("category", ""), benchmark.get("slug", ""),
        benchmark.get("exemplar", ""), *benchmark.get("keywords", []),
    ]))
    if not source or not target:
        return 0.0
    overlap = len(source & target)
    score = overlap / max(1, len(source | target))
    if benchmark.get("category", "").lower() == source_name.lower():
        score += 1.0
    if benchmark.get("slug", "").replace("-", " ").lower() == source_name.lower():
        score += 0.8
    return score


def discover_for_category(benchmark: dict, cache_dir: Path | None = None, max_source_categories: int = 3,
                          max_apps_per_source_category: int = 30) -> list[dict]:
    """Return normalized finder entries from the 52-category Open Source Tools directory."""
    cache_dir = cache_dir or Path(CACHE_FILE).parent
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        category_page = _fetch_cached(CATEGORIES_URL, cache_dir)
    except Exception:
        return []
    categories = parse_categories(category_page)
    if len(categories) != EXPECTED_CATEGORY_COUNT:
        raise RuntimeError(f"Open Source Tools category count changed: expected {EXPECTED_CATEGORY_COUNT}, found {len(categories)}")
    ranked_categories = sorted(
        ((match_category(c["name"], c["slug"], benchmark), c) for c in categories),
        key=lambda x: -x[0]
    )
    selected = [(s, c) for s, c in ranked_categories if s > 0][:max_source_categories]
    out = []
    seen = set()
    for score, cat in selected:
        try:
            page = _fetch_cached(f"{SITE}/categories/{cat['slug']}", cache_dir)
        except Exception:
            continue
        cards = _parse_cards(page)[:max_apps_per_source_category]
        for card in cards:
            try:
                app_page = _fetch_cached(SITE + card["href"], cache_dir)
                meta = parse_app_page(app_page)
            except Exception:
                meta = {}
            repo = meta.get("repo")
            if not repo or repo in seen:
                continue
            seen.add(repo)
            out.append({
                "name": card["name"],
                "description": meta.get("description") or card.get("description", ""),
                "tags": card.get("tags", []) + [cat["name"], cat["slug"]],
                "source_code_url": repo,
                "licenses": [meta.get("license")] if meta.get("license") else [],
                "stargazers_count": card.get("stars") or 0,
                "archived": False,
                "updated_at": None,
                "current_release": {},
                "commit_history": {},
                "discovery_source": "open-source-tools",
                "source_category": cat["name"],
                "source_category_slug": cat["slug"],
                "source_category_match": round(score, 4),
                "source_url": SITE + card["href"],
            })
    out.sort(key=lambda e: -(e.get("stargazers_count") or 0))
    return out
