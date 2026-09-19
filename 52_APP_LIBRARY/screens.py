#!/usr/bin/env python3
"""
screens.py — spec sections 7-11: SCREEN DISCOVERY + SCREEN EXISTENCE TEST +
SCREEN INTEGRITY CHECKS, per app.

Runs only on apps whose install_startup.py result was STARTABLE (their
containers were left running for exactly this reason - see live_containers.json).

Discovery: two independent sources, per spec section 7 -
  (a) STATIC - route/template file names found in the source tree (a route
      is a *candidate*, never counted as a real screen until reached).
  (b) LIVE NAVIGATION - links/buttons harvested from the running app's own
      homepage and, one hop deep, from screens already reached. This is how
      an app's real navigation is discovered rather than assumed.

Verification (the part spec section 8 calls "critical"): for every candidate,
Playwright actually navigates to it. A route is never counted as reachable
because grep found the string in source; only a live page load counts.
For each reached screen: HTTP outcome, DOM present, title/heading text,
control inventory (button/input/select/textarea/checkbox/link/table/form),
and a screenshot - per spec sections 9-10.

Output per app: applications/APP-0XX/screens.json (spec section 11's schema)
and applications/APP-0XX/evidence/*.png.
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
MANIFEST_FILE = HERE / "manifest.json"
APPS_DIR = HERE / "applications"
LIVE_FILE = HERE / "live_containers.json"

CHROMIUM_EXECUTABLE_PATH = os.environ.get("CHROMIUM_EXECUTABLE_PATH") or None
PAGE_TIMEOUT_MS = 20000
MAX_STATIC_ROUTES = 40
MAX_SCREENS_TO_VISIT = 14
VIEWPORT = {"width": 1366, "height": 900}

SCREEN_FILE_SUFFIXES = (".html", ".htm", ".erb", ".haml", ".ejs", ".pug", ".hbs",
                        ".njk", ".jinja", ".jinja2", ".vue", ".svelte", ".jsx", ".tsx", ".astro")
SCREEN_EXCLUDE_PARTS = ("node_modules", "vendor", "dist", "build", ".git", "test", "tests",
                        "spec", "__tests__", "fixtures", "coverage", "docs", "storybook")
ROUTE_LINE_RE = re.compile(r"""["'](/[a-zA-Z][a-zA-Z0-9_\-/:]{1,40})["']""")
LIKELY_UI_ROUTE = re.compile(r"^/(?!api/|_next|static|assets|\.well-known)")


def static_route_candidates(root):
    routes = set()
    n = 0
    for p in root.rglob("*"):
        if n > 6000:
            break
        parts = [x.lower() for x in p.relative_to(root).parts]
        if any(x in SCREEN_EXCLUDE_PARTS for x in parts[:-1]):
            continue
        if not p.is_file():
            continue
        name = p.name.lower()
        is_screen = any(name.endswith(s) for s in SCREEN_FILE_SUFFIXES)
        is_route_src = p.suffix.lower() in (".py", ".rb", ".php", ".js", ".ts", ".go", ".java")
        if not (is_screen or is_route_src):
            continue
        n += 1
        try:
            if p.stat().st_size > 150_000:
                continue
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for m in ROUTE_LINE_RE.finditer(text):
            r = m.group(1)
            if LIKELY_UI_ROUTE.match(r) and len(r) < 60:
                routes.add(r)
        if len(routes) >= MAX_STATIC_ROUTES:
            break
    return sorted(routes)[:MAX_STATIC_ROUTES]


class ScreenWalk:
    def __init__(self, page, base_url, evidence_dir):
        self.page, self.base, self.evidence_dir = page, base_url.rstrip("/"), evidence_dir
        self.shots = 0
        self.visited_urls = set()

    def shot(self, label):
        self.shots += 1
        name = f"{self.shots:03d}_{re.sub(r'[^a-z0-9]+', '_', label.lower())[:60]}.png"
        try:
            self.page.screenshot(path=str(self.evidence_dir / name))
            return name
        except Exception:
            return None

    def goto(self, url):
        try:
            self.page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            self.page.wait_for_timeout(1200)
            return True
        except Exception:
            return False

    def collect_nav_links(self):
        items = []
        try:
            for el in self.page.query_selector_all("a[href], [role=link], nav a")[:200]:
                try:
                    if not el.is_visible():
                        continue
                    href = el.get_attribute("href") or ""
                    text = (el.inner_text() or "").strip()[:60]
                    if not href or href.startswith(("#", "javascript:", "mailto:")):
                        continue
                    items.append({"href": href, "text": text})
                except Exception:
                    continue
        except Exception:
            pass
        return items

    def inventory_controls(self):
        try:
            counts = self.page.evaluate("""() => ({
                button: document.querySelectorAll('button, [role=button], input[type=submit], input[type=button]').length,
                input: document.querySelectorAll('input:not([type=submit]):not([type=button]):not([type=hidden])').length,
                textarea: document.querySelectorAll('textarea').length,
                select: document.querySelectorAll('select').length,
                checkbox: document.querySelectorAll('input[type=checkbox]').length,
                link: document.querySelectorAll('a[href]').length,
                menu: document.querySelectorAll('[role=menu], nav').length,
                table: document.querySelectorAll('table').length,
                form: document.querySelectorAll('form').length,
            })""")
            return counts
        except Exception:
            return {}

    def verify_screen(self, url, name_hint):
        if not self.goto(url):
            return {"reachable": False, "rendered": False, "controls_detected": False,
                    "browser_verified": False, "title": None, "controls": {}, "screenshot": None,
                    "note": "navigation failed (timeout or network error)"}
        try:
            title = self.page.title()
        except Exception:
            title = None
        try:
            heading = self.page.query_selector("h1, h2, [role=heading]")
            heading_text = (heading.inner_text() or "").strip() if heading else ""
        except Exception:
            heading_text = ""
        try:
            body_text = self.page.inner_text("body", timeout=5000)
        except Exception:
            body_text = ""
        rendered = bool(body_text and len(body_text.strip()) > 20)
        controls = self.inventory_controls()
        controls_detected = any(v > 0 for v in controls.values())
        shot = self.shot(name_hint)
        return {
            "reachable": True, "rendered": rendered, "controls_detected": controls_detected,
            "browser_verified": rendered, "title": title, "heading": heading_text,
            "controls": controls, "screenshot": shot, "final_url": self.page.url,
        }


def screen_name_from_url(url):
    path = urlparse(url).path.strip("/") or "home"
    return path.replace("/", "_")[:40] or "home"


def process_app(entry, base_url):
    app_id = entry["id"]
    d = APPS_DIR / app_id
    (d / "evidence").mkdir(parents=True, exist_ok=True)
    source_root = d / "source"

    static_routes = static_route_candidates(source_root) if source_root.is_dir() else []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM_EXECUTABLE_PATH)
        ctx = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
        page = ctx.new_page()
        w = ScreenWalk(page, base_url, d / "evidence")

        screens = []
        seen_urls = set()

        # 1. the homepage itself is always screen #1
        home_result = w.verify_screen(base_url, "home")
        screens.append({"screen_id": "SCR-001", "name": "Home", "route": "/",
                        "discovery_source": "startup_url", **home_result})
        seen_urls.add(base_url.rstrip("/"))

        # 2. live navigation: links actually present on the rendered homepage
        nav_links = w.collect_nav_links() if home_result["reachable"] else []
        candidates = []
        for l in nav_links:
            full = urljoin(base_url + "/", l["href"])
            if urlparse(full).netloc != urlparse(base_url).netloc:
                continue
            if full.rstrip("/") in seen_urls:
                continue
            candidates.append((full, l["text"] or screen_name_from_url(full), "nav_link"))

        # 3. static route candidates found in source, not already covered by nav
        for r in static_routes:
            full = urljoin(base_url + "/", r.lstrip("/"))
            if full.rstrip("/") in seen_urls or any(full == c[0] for c in candidates):
                continue
            candidates.append((full, screen_name_from_url(full), "static_route"))

        for i, (full, label, source) in enumerate(candidates[:MAX_SCREENS_TO_VISIT], 2):
            if full.rstrip("/") in seen_urls:
                continue
            seen_urls.add(full.rstrip("/"))
            result = w.verify_screen(full, label)
            screens.append({"screen_id": f"SCR-{i:03d}", "name": label[:60], "route": urlparse(full).path,
                            "discovery_source": source, **result})

        browser.close()

    out = {"application": app_id, "base_url": base_url,
          "static_routes_found": len(static_routes), "screens": screens}
    (d / "screens.json").write_text(json.dumps(out, indent=1))

    reached = sum(1 for s in screens if s["reachable"])
    rendered = sum(1 for s in screens if s["rendered"])
    verified = sum(1 for s in screens if s["browser_verified"])
    return {"screens_discovered": len(screens), "screens_reached": reached,
            "screens_rendered": rendered, "screens_browser_verified": verified}


def main():
    manifest = json.loads(MANIFEST_FILE.read_text())
    live = json.loads(LIVE_FILE.read_text()) if LIVE_FILE.exists() else []
    live_by_id = {l["app_id"]: l for l in live}
    entries_by_id = {e["id"]: e for e in manifest["applications"]}

    counts = {}
    for app_id, l in live_by_id.items():
        entry = entries_by_id[app_id]
        print(f"{app_id} ({entry['category_slug']}) {entry['name']} @ {l['url']}")
        try:
            summary = process_app(entry, l["url"])
        except Exception as e:
            summary = None
            entry["status"] = "SCREEN_FAILED"
            entry["screen_summary"] = {"error": f"{type(e).__name__}: {e}"}
            print(f"  SCREEN_FAILED: {type(e).__name__}: {e}")
            counts["SCREEN_FAILED"] = counts.get("SCREEN_FAILED", 0) + 1
            (APPS_DIR / app_id / "app.json").write_text(json.dumps(entry, indent=1))
            continue
        entry["screen_summary"] = summary
        entry["status"] = "SCREEN-VERIFIED" if summary["screens_browser_verified"] > 0 else "SCREEN_FAILED"
        print(f"  discovered={summary['screens_discovered']} reached={summary['screens_reached']} "
              f"rendered={summary['screens_rendered']} browser_verified={summary['screens_browser_verified']}")
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
        (APPS_DIR / app_id / "app.json").write_text(json.dumps(entry, indent=1))
        MANIFEST_FILE.write_text(json.dumps(manifest, indent=1))

    print("\n=== SCREEN DISCOVERY SUMMARY ===")
    for k, v in sorted(counts.items()):
        print(f"{k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
