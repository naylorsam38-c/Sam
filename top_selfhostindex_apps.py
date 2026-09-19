#!/usr/bin/env python3
"""
top_selfhostindex_apps.py — for every category on SelfHostIndex (selfhostindex.com),
pick the single top app that passes Sam's legal side and the library's app rules.

What it does, per category:
  1. CATEGORIES — read the live category list from selfhostindex.com/categories/.
  2. LIST       — read the category page: every app card with SelfHostIndex's own
                  health score, stars, archived flag and listed licence.
  3. RANK       — order apps the way SelfHostIndex rates them (health, then stars).
  4. PRE-FILTER — drop archived apps and apps whose LISTED licence is not allowed
                  (cheap, no clone). Every drop is recorded with its reason.
  5. REPO       — open the app's own SelfHostIndex page and read its code repository.
  6. GATES      — hand the repo to find_library_apps.py's own inspect_repo():
                  clone at a pinned commit, read the repo's OWN licence file (the legal
                  side), screens + login gate, container-recipe gate. Same rules, same
                  code as the main finder — nothing re-implemented here.
  7. DEEP LICENCE — every licence file in the repo + the root file's wording. Mixed
                  licensing (e.g. an "Enterprise" folder) refuses the app.
  8. TEST       — stand the app up from its own recipe (walk_library_apps.py's Boot), open
                  it in real Playwright Chromium, get in (register / login / setup), then
                  visit EVERY screen it can reach and click EVERY button and link on each,
                  screenshotting every screen and recording what every click did (new
                  screen, change on page, server error, page crash, nothing).
  9. PASS       — boots + gets in + no click causes a server error or a page crash (rules
                  in config). Fails = drop to the next app down the list and repeat.
 10. LIBRARY    — a passing app is written into library_completed/<category>/ with its
                  licence evidence, test report and every screenshot. LIBRARY.md indexes
                  the completed library. Nothing passes = NONE ADMITTED (blank beats wrong).
 11. OUTPUT     — selfhostindex/TOP_APPS.md (one row per category), TOP_APPS.json,
                  per-category JSON with every refusal and failed test, the raw pages
                  fetched (evidence), tests/<category>/<app>/ for every app tested, and
                  RUN_OUTPUT.txt.

Needs on the machine: podman + podman-compose, Playwright Chromium, pyyaml, git.
Restartable: categories already in library_completed/ are skipped (RESUME below).

Usage:
  python3 top_selfhostindex_apps.py               # all categories
  python3 top_selfhostindex_apps.py crm-erp wikis # only these category slugs
  python3 top_selfhostindex_apps.py --list        # print categories + counts and stop

No mocks. Every number comes from a live SelfHostIndex page or a real clone.
"""

# =============================================================================
#  RULES / CONFIG — edit here. One comment per setting says what changes if you do.
# =============================================================================

SITE = "https://selfhostindex.com"
#   The directory being followed. Change only if the site moves.

CATEGORIES_PATH = "/categories/"
#   Page that lists every category with its app count.

EXPECTED_CATEGORY_COUNT = 55
#   The site says "55 categories". If the live page shows a different number the run
#   stops and says so, instead of quietly working from a different list. Set to 0 to
#   accept whatever the page shows.

RANK_BY = ("health", "stars")
#   How "top" is decided, in order. "health" = SelfHostIndex's own 0-100 maintenance
#   score (their rating). "stars" = GitHub stars (popularity). Swap the order to rank
#   by popularity first. Apps with no health score sort below every scored app.

ALLOWED_LICENCES = None
#   None = use exactly the ALLOWED_LICENCES list in find_library_apps.py (one legal
#   rulebook for the whole library). Put a tuple here only to override it for this run.

PREFILTER_ON_LISTED_LICENCE = True
#   True = skip cloning apps whose licence as LISTED on SelfHostIndex is not allowed
#   (fast). The repo's own licence file still decides for everything that is cloned.
#   False = clone every candidate and let only the licence file decide (slower; catches
#   a site mislabel that wrongly lists a permissive app as GPL).

SKIP_ARCHIVED = True
#   Archived projects are dead. False lets them through to the gates.

MIN_HEALTH = 0
#   Apps with a health score below this are not cloned. Unscored apps count as 0.
#   Raise (e.g. 50) to refuse poorly maintained apps even if nothing else passes.

MAX_CANDIDATES_PER_CATEGORY = 6
#   How many apps (after pre-filter, in rank order) are cloned and gated before the
#   category is declared NONE ADMITTED. Raise to dig deeper into long categories.

ALLOW_SAME_APP_IN_TWO_CATEGORIES = False
#   False = an app already picked as top in one category is skipped in any later one,
#   so the shelf has no duplicates. True = the same app may top several categories.

REQUEST_DELAY_SECONDS = 1.0
#   Pause between page requests to the site. Lower = faster, harder on their server.

REQUEST_TIMEOUT_SECONDS = 30
#   A page slower than this is recorded as a fetch failure.

USER_AGENT = "Mozilla/5.0 (library top-app picker; contact via repo owner)"
#   Sent with every request.

OUT_DIR = "selfhostindex"
#   Where results go (relative to this script).

DEEP_LICENCE_AUDIT = True
#   True = after the root licence passes, read EVERY licence file in the repo (not just
#   the root) and the root file's wording. Any file whose licence is not allowed, or a
#   root file that says only part of the code is under it, refuses the app. This caught
#   Rocket.Chat: root reads MIT, but packages inside carry an Enterprise licence.
#   False = trust the root file alone (how find_library_apps.py behaves today).

DEEP_LICENCE_FILE_PREFIXES = ("license", "licence", "copying", "unlicense")
#   A FILE (not folder) whose name starts with one of these, with no extension or a
#   .txt/.md/.rst extension, is read as a licence file.

DEEP_LICENCE_EXCLUDE_PATH_PARTS = ("node_modules", "vendor", "vendors", "third_party", "third-party",
                                   "bower_components", ".git", "test", "tests", "fixtures", "examples",
                                   "example", "docs", "licenses", "licences")
#   Licence files under these folders are ignored: they are copies of dependencies'
#   licences or test data, not the app's own terms. Remove "vendor" etc. to be stricter.

DEEP_LICENCE_UNRECOGNISED_REFUSES = True
#   True = a licence file the classifier cannot name (e.g. a company's own "Enterprise
#   License") refuses the app. False = it is recorded as a warning only.

MIXED_LICENCE_MARKERS = ("portions of this software", "enterprise edition", "commercial license",
                         "commercial licence", "ee license", "ee licence", "except for the",
                         "with the exception of", "licensed separately", "different license")
#   Wording in the ROOT licence file that means only part of the code is under it.
#   Found = refused, with the sentence quoted. Add phrases as new tricks turn up.

# --- Test in Playwright ------------------------------------------------------
TEST_ON = True
#   True = every gated app is booted and button-tested before it can enter the library.
#   False = stop after the gates (the licence/screens/runs pick only, nothing tested).

MAX_SCREENS = 60
#   Most distinct screens (URLs) visited per app. Raise to go deeper into big apps;
#   screens not reached are listed in the report as "not visited (cap)".

MAX_CONTROLS_PER_SCREEN = 80
#   Most buttons/links clicked on one screen. Extra ones are recorded as not clicked.

MAX_TOTAL_CLICKS = 1500
#   Hard stop on clicks per app so one enormous app cannot run forever.

CLICK_SETTLE_MS = 1500
#   Wait after each click before judging what it did. Raise for slow apps.

CONTROL_SELECTOR = ("a[href], button, [role=button], [role=menuitem], [role=tab], [role=link], "
                    "input[type=submit], input[type=button]")
#   What counts as a button or link to click.

SKIP_CONTROL_WORDS = ("logout", "log out", "sign out", "signout", "delete", "remove", "destroy",
                      "erase", "wipe", "purge", "drop", "reset", "revoke", "deactivate", "disable",
                      "uninstall", "leave", "close account", "terminate", "shutdown", "shut down",
                      "restart", "reboot", "factory")
#   Controls whose text/label/link contains one of these are recorded but NOT clicked, so
#   the test does not log itself out or destroy the app mid-test. Remove a word to click it.

SKIP_HREF_PREFIXES = ("mailto:", "tel:", "javascript:void", "data:", "blob:")
#   Links starting with these are recorded, not clicked.

CLICK_EXTERNAL_LINKS = False
#   False = links to other websites are recorded as external, not followed.

PASS_REQUIRES_GATE = ("IN",)
#   Getting-in states that count as a pass. Add "NO_GATE_FOUND" to accept apps that open
#   straight onto a page with no login at all.

FAIL_ON_SERVER_ERROR = True
#   True = any click that makes the app answer with a 5xx fails the app.

FAIL_ON_PAGE_CRASH = True
#   True = a click that crashes the browser tab or leaves a blank page fails the app.

FAIL_ON_JS_ERROR = False
#   True = any uncaught JavaScript error on any screen fails the app. Off by default:
#   many healthy apps throw harmless errors. Every JS error is recorded either way.

MIN_CLICKS_TO_PASS = 5
#   An app where fewer than this many controls could be clicked has not really been
#   tested and fails. Lower for tiny single-screen apps.

MAX_SCREENSHOTS_PER_APP = 400
#   Screenshot cap per app (one per screen + one per click that changed something).

# --- Library ---------------------------------------------------------------------
LIBRARY_DIR = "library_completed"
#   Where passing apps go: one folder per category with ENTRY.json, TEST_REPORT.md and
#   the screenshots. LIBRARY.md at the top lists every completed entry.

RESUME = True
#   True = a category that already has an entry in the completed library is skipped,
#   so a stopped run carries on where it left off. False = redo every category.

SAVE_PAGES = True
#   True = keep every page fetched under OUT_DIR/pages/ so each pick can be re-checked
#   against exactly what the site said at run time. False saves disk.

# =============================================================================
#  END OF CONFIG — logic below
# =============================================================================

import html
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import find_library_apps as finder  # the library's own gates — single source of truth
if TEST_ON:
    import walk_library_apps as walker  # the library's own Boot + get-in — single source of truth
    from playwright.sync_api import sync_playwright
import shutil

OUT = HERE / OUT_DIR
PAGES = OUT / "pages"
TESTS = OUT / "tests"
LIB = HERE / LIBRARY_DIR
LOG = []
LICENCES = tuple(ALLOWED_LICENCES) if ALLOWED_LICENCES else tuple(finder.ALLOWED_LICENCES)


def say(msg):
    LOG.append(msg)
    print(msg, flush=True)


# --------------------------------------------------------------------------- fetch
def fetch(path):
    url = path if path.startswith("http") else SITE + path
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    time.sleep(REQUEST_DELAY_SECONDS)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as r:
        body = r.read().decode("utf-8", errors="replace")
    if SAVE_PAGES:
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.replace(SITE, "").strip("/")) or "home"
        PAGES.mkdir(parents=True, exist_ok=True)
        (PAGES / f"{name}.html").write_text(body)
    return body


def _text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()


# --------------------------------------------------------------------------- parse
def parse_categories(page):
    """[{slug, name, stated_count}] from the categories page tiles."""
    cats = []
    for m in re.finditer(r'<a class="cat-tile" href="/category/([^"/]+)/">(.*?)</a>', page, re.S):
        slug, inner = m.group(1), m.group(2)
        name = _text(re.search(r"<h3>(.*?)</h3>", inner, re.S).group(1))
        cm = re.search(r'class="cat-count">\s*([\d,]+)\s*apps?', inner)
        cats.append({"slug": slug, "name": name,
                     "stated_count": int(cm.group(1).replace(",", "")) if cm else None})
    return cats


def parse_category_page(page):
    """(stated_count, [app cards]) — cards carry the site's own data attributes."""
    stated = None
    sm = re.search(r'"numberOfItems":\s*(\d+)', page)
    if sm:
        stated = int(sm.group(1))
    apps = []
    for m in re.finditer(r'<article class="card"([^>]*)>(.*?)</article>', page, re.S):
        attrs = dict(re.findall(r'data-([a-z-]+)="([^"]*)"', m.group(1)))
        body = m.group(2)
        name_m = re.search(r"<h3>(.*?)</h3>", body, re.S)
        href_m = re.search(r'href="/app/([^"/]+)/"', body)
        badges = [_text(b) for b in re.findall(r'<span class="badge">(.*?)</span>', body, re.S)]
        lic = [b for b in badges if not b.lower().endswith("setup")]
        alt = re.search(r'class="card-alt">(.*?)</p>', body, re.S)
        tag = re.search(r'class="card-tagline">(.*?)</p>', body, re.S)
        health = attrs.get("health", "")
        apps.append({
            "slug": href_m.group(1) if href_m else attrs.get("name"),
            "name": _text(name_m.group(1)) if name_m else attrs.get("name"),
            "tagline": _text(tag.group(1)) if tag else "",
            "replaces": _text(alt.group(1)).replace("Replaces", "").strip() if alt else "",
            "health": int(health) if health.isdigit() else None,
            "stars": int(attrs.get("stars") or 0),
            "archived": attrs.get("archived", "").lower() in ("true", "1", "yes"),
            "listed_licence": lic[-1] if lic else "",
            "difficulty": attrs.get("difficulty", ""),
            "site_category": attrs.get("cat", ""),
        })
    return stated, apps


def parse_app_page(page):
    """Repo URL + licence from the app page's SoftwareApplication JSON-LD."""
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            d = json.loads(block)
        except json.JSONDecodeError:
            continue
        if d.get("@type") == "SoftwareApplication":
            return {"repo": d.get("codeRepository") or d.get("downloadUrl"),
                    "page_licence": d.get("license"), "language": d.get("programmingLanguage"),
                    "features": d.get("featureList")}
    return {"repo": None}


# --------------------------------------------------------------------------- rank
def rank_key(app):
    key = []
    for k in RANK_BY:
        v = app.get(k)
        key.append(-(v if v is not None else -1))
    return tuple(key)


def listed_licence_ok(lic):
    parts = [p.strip() for p in re.split(r"[,/]| OR | AND ", lic or "") if p.strip()]
    return any(p in LICENCES for p in parts)


# --------------------------------------------------------------------------- deep licence
def deep_licence_audit(root):
    """Return (ok, reason, findings) across every licence file and the root wording."""
    root = Path(root)
    findings, problems = [], []
    for p in finder.walk_files(root):
        rel_parts = [x.lower() for x in p.relative_to(root).parts]
        if any(x in DEEP_LICENCE_EXCLUDE_PATH_PARTS for x in rel_parts[:-1]):
            continue
        n = p.name.lower()
        stem, _, ext = n.partition(".")
        if not any(stem.startswith(pre) for pre in DEEP_LICENCE_FILE_PREFIXES):
            continue
        if ext not in ("", "txt", "md", "rst", "mit", "apache"):
            continue
        try:
            head = p.read_text(errors="ignore")[:6000]
        except Exception:
            continue
        lic = finder.classify_licence(head)
        rel = "/".join(p.relative_to(root).parts)
        findings.append({"file": rel, "licence": lic})
        if lic == "UNRECOGNISED":
            first = next((ln.strip() for ln in head.splitlines() if ln.strip()), "")[:120]
            if DEEP_LICENCE_UNRECOGNISED_REFUSES:
                problems.append(f"{rel} is an unrecognised licence (\"{first}\")")
        elif lic not in LICENCES:
            problems.append(f"{rel} is {lic}")
        if len(rel_parts) == 1:
            low = head.lower()
            for m in MIXED_LICENCE_MARKERS:
                i = low.find(m)
                if i >= 0:
                    sent = re.sub(r"\s+", " ", head[max(0, i - 40):i + 100]).strip()
                    problems.append(f"root {rel} covers only part of the code: \"...{sent}...\"")
                    break
    if problems:
        return False, "; ".join(problems[:4]) + (f" (+{len(problems) - 4} more)" if len(problems) > 4 else ""), findings
    return True, "", findings


def remove_clone(repo):
    shutil.rmtree(finder.clone_dir_for(repo), ignore_errors=True)


# --------------------------------------------------------------------------- button test
def _safe_name(s):
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")[:60] or "x"


def _screen_key(url):
    """Distinct screen = scheme+host+path+query, plus the fragment only for #/ SPA routes."""
    base, _, frag = url.partition("#")
    return base.rstrip("/") + (("#" + frag) if frag.startswith("/") or frag.startswith("!/") else "")


def _origin(url):
    m = re.match(r"(https?://[^/]+)", url or "")
    return m.group(1) if m else ""


class ButtonTest:
    """Visit every reachable screen, click every control on it, record everything."""

    def __init__(self, page, out_dir, base_url, gate):
        self.page, self.out, self.base, self.gate = page, out_dir, base_url, gate
        self.origin = _origin(base_url)
        self.shots = 0
        self.screens = {}          # key -> {url, title, screenshot, controls: [...]}
        self.queue = []
        self.clicks = 0
        self.server_errors = []    # every 5xx seen during the test
        self.js_errors = []        # every uncaught JS error
        self.crashes = []
        self.external = set()
        page.on("response", self._on_response)
        page.on("pageerror", lambda e: self.js_errors.append({"screen": self.page.url, "error": str(e)[:300]}))
        page.on("crash", lambda *_: self.crashes.append({"screen": self.page.url, "error": "tab crashed"}))

    def _on_response(self, r):
        try:
            if r.status >= 500 and _origin(r.url) == self.origin:
                self.server_errors.append({"screen": self.page.url, "request": r.url[:300], "status": r.status})
        except Exception:
            pass

    def shot(self, label):
        if self.shots >= MAX_SCREENSHOTS_PER_APP:
            return None
        self.shots += 1
        name = f"{self.shots:03d}_{_safe_name(label.lower())[:50]}.png"
        try:
            self.page.screenshot(path=str(self.out / "screenshots" / name), full_page=False)
            return name
        except Exception as e:
            return f"(screenshot failed: {str(e)[:80]})"

    def goto(self, url):
        try:
            self.page.goto(url, timeout=walker.PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            self.page.wait_for_timeout(CLICK_SETTLE_MS)
            return True
        except Exception:
            return False

    def controls(self):
        """Visible controls on the current page, each with a stable signature."""
        out = []
        try:
            els = self.page.query_selector_all(CONTROL_SELECTOR)
        except Exception:
            return out
        seen = set()
        for el in els:
            try:
                if not el.is_visible():
                    continue
                text = (el.inner_text() or "").strip().replace("\n", " ")[:80]
                label = " ".join(filter(None, [el.get_attribute("aria-label"), el.get_attribute("title"),
                                               el.get_attribute("value")]))[:80]
                href = el.get_attribute("href") or ""
                tag = el.evaluate("e => e.tagName.toLowerCase()")
                sig = f"{tag}|{text}|{label}|{href}"
                n = 0
                while f"{sig}#{n}" in seen:
                    n += 1
                sig = f"{sig}#{n}"
                seen.add(sig)
                out.append({"el": el, "sig": sig, "tag": tag, "text": text, "label": label, "href": href})
            except Exception:
                continue
        return out

    def _skip_reason(self, c):
        words = f"{c['text']} {c['label']} {c['href']}".lower()
        for w in SKIP_CONTROL_WORDS:
            if w in words:
                return f"not clicked: matches skip word '{w}'"
        if any(c["href"].lower().startswith(p) for p in SKIP_HREF_PREFIXES):
            return "not clicked: non-page link"
        if c["href"].startswith("http") and _origin(c["href"]) != self.origin:
            self.external.add(c["href"][:200])
            if not CLICK_EXTERNAL_LINKS:
                return "not clicked: external link"
        return None

    def _body_fingerprint(self):
        try:
            return self.page.evaluate("() => document.body ? document.body.innerText.length + ':' + document.querySelectorAll('*').length : '0'")
        except Exception:
            return "?"

    def _page_is_blank(self):
        try:
            return self.page.evaluate("() => !document.body || document.body.innerText.trim().length === 0 && document.querySelectorAll('img,svg,canvas,video').length === 0")
        except Exception:
            return True

    def _still_in(self):
        """If a click logged us out, get back in with the walker's own gate logic."""
        try:
            if self.page.query_selector("form input[type=password]") and not self.gate._looks_like_app():
                state, steps = self.gate.get_in()
                return state in PASS_REQUIRES_GATE
        except Exception:
            pass
        return True

    def run(self):
        start = self.page.url
        self.queue.append(start)
        while self.queue and len(self.screens) < MAX_SCREENS and self.clicks < MAX_TOTAL_CLICKS:
            url = self.queue.pop(0)
            key = _screen_key(url)
            if key in self.screens:
                continue
            if not self.goto(url):
                self.screens[key] = {"url": url, "title": "", "screenshot": None, "load": "FAILED", "controls": []}
                continue
            screen = {"url": self.page.url, "title": self._title(), "screenshot": self.shot(f"screen_{self._title() or url}"),
                      "load": "OK", "controls": []}
            self.screens[key] = screen
            first = self.controls()
            say(f"       screen {len(self.screens):>3}: {screen['url'][:90]}  ({len(first)} controls)")
            sigs = [c["sig"] for c in first]
            for i, sig in enumerate(sigs):
                meta = next(c for c in first if c["sig"] == sig)
                rec = {"control": meta["text"] or meta["label"] or meta["href"] or meta["tag"], "tag": meta["tag"],
                       "href": meta["href"]}
                if i >= MAX_CONTROLS_PER_SCREEN or self.clicks >= MAX_TOTAL_CLICKS:
                    rec["result"] = "not clicked: cap reached"
                    screen["controls"].append(rec)
                    continue
                why = self._skip_reason(meta)
                if why:
                    rec["result"] = why
                    screen["controls"].append(rec)
                    continue
                screen["controls"].append(self._click(url, sig, rec))
        for u in self.queue:
            k = _screen_key(u)
            if k not in self.screens:
                self.screens[k] = {"url": u, "title": "", "screenshot": None, "load": "NOT VISITED (cap)", "controls": []}
        return self.report()

    def _title(self):
        try:
            return (self.page.title() or "").strip()[:80]
        except Exception:
            return ""

    def _click(self, screen_url, sig, rec):
        # Return to the screen fresh so every click starts from the same state.
        if _screen_key(self.page.url) != _screen_key(screen_url):
            self.goto(screen_url)
        target = next((c for c in self.controls() if c["sig"] == sig), None)
        if target is None:
            rec["result"] = "gone: control no longer on the screen when revisited"
            return rec
        e0, j0, c0 = len(self.server_errors), len(self.js_errors), len(self.crashes)
        before_url, before_fp = self.page.url, self._body_fingerprint()
        self.clicks += 1
        popups = []
        grab = lambda p: popups.append(p)
        self.page.context.on("page", grab)
        try:
            target["el"].click(timeout=5000)
        except Exception as ex:
            rec["result"] = f"CLICK FAILED: {str(ex).splitlines()[0][:150]}"
            return rec
        finally:
            self.page.wait_for_timeout(300)
            self.page.context.remove_listener("page", grab)
        if popups:
            p = popups[0]
            try:
                p.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass
            rec["result"] = f"opened new tab {p.url[:150]}"
            if _origin(p.url) == self.origin and _screen_key(p.url) not in self.screens:
                self.queue.append(p.url)
            for extra in popups:
                try:
                    extra.close()
                except Exception:
                    pass
            return rec
        self.page.wait_for_timeout(CLICK_SETTLE_MS)
        after_url = self.page.url
        rec["to"] = after_url
        if len(self.crashes) > c0 or (FAIL_ON_PAGE_CRASH and self._page_is_blank()):
            rec["result"] = "PAGE CRASH / BLANK PAGE"
            rec["screenshot"] = self.shot(f"crash_{rec['control']}")
            if len(self.crashes) == c0:
                self.crashes.append({"screen": screen_url, "control": rec["control"], "error": "blank page after click"})
            else:
                self.crashes[-1]["control"] = rec["control"]
            self.goto(screen_url)
        elif len(self.server_errors) > e0:
            errs = self.server_errors[e0:]
            for e in errs:
                e["control"] = rec["control"]
            rec["result"] = f"SERVER ERROR {errs[0]['status']} on {errs[0]['request'][:120]}"
            rec["screenshot"] = self.shot(f"err_{rec['control']}")
        elif _screen_key(after_url) != _screen_key(before_url):
            rec["result"] = "opened screen"
            if _origin(after_url) == self.origin and _screen_key(after_url) not in self.screens:
                self.queue.append(after_url)
            elif _origin(after_url) != self.origin:
                rec["result"] = "left the app (external page)"
        elif self._body_fingerprint() != before_fp:
            rec["result"] = "changed the page (menu / dialog / panel)"
            rec["screenshot"] = self.shot(f"changed_{rec['control']}")
        else:
            rec["result"] = "no visible change"
        if len(self.js_errors) > j0:
            rec["js_errors"] = [e["error"] for e in self.js_errors[j0:]][:3]
        if not self._still_in():
            rec["note"] = "click logged the test out and it could not get back in"
        return rec

    def report(self):
        allc = [c for s in self.screens.values() for c in s["controls"]]
        clicked = [c for c in allc if not c.get("result", "").startswith(("not clicked", "gone"))]
        return {"screens_visited": sum(1 for s in self.screens.values() if s["load"] == "OK"),
                "screens_failed_to_load": sum(1 for s in self.screens.values() if s["load"] == "FAILED"),
                "screens_not_visited_cap": sum(1 for s in self.screens.values() if s["load"].startswith("NOT")),
                "controls_found": len(allc), "controls_clicked": len(clicked),
                "controls_skipped": len(allc) - len(clicked),
                "server_errors": self.server_errors, "js_errors": self.js_errors, "crashes": self.crashes,
                "external_links": sorted(self.external), "screens": list(self.screens.values())}


def judge(gate_state, rep):
    fails = []
    if gate_state not in PASS_REQUIRES_GATE:
        fails.append(f"could not get in (gate {gate_state})")
    if rep:
        if rep["controls_clicked"] < MIN_CLICKS_TO_PASS:
            fails.append(f"only {rep['controls_clicked']} controls clickable (< {MIN_CLICKS_TO_PASS})")
        if FAIL_ON_SERVER_ERROR and rep["server_errors"]:
            fails.append(f"{len(rep['server_errors'])} server error(s), first: {rep['server_errors'][0]['status']} "
                         f"{rep['server_errors'][0]['request'][:100]}")
        if FAIL_ON_PAGE_CRASH and rep["crashes"]:
            fails.append(f"{len(rep['crashes'])} page crash / blank page(s)")
        if FAIL_ON_JS_ERROR and rep["js_errors"]:
            fails.append(f"{len(rep['js_errors'])} uncaught JS error(s)")
    return ("PASS", "") if not fails else ("FAIL", "; ".join(fails))


def test_app(cat_slug, row, run_recipes):
    """Boot from own recipe, get in, click everything. Returns result dict (verdict PASS/FAIL)."""
    out = TESTS / cat_slug / _safe_name(row["app"])
    if out.exists():
        shutil.rmtree(out)
    (out / "screenshots").mkdir(parents=True)
    res = {"app": row["app"], "repo": row["repo"], "commit": row["commit"],
           "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "boot": {}, "gate": {}, "test": None, "verdict": "FAIL", "reason": ""}
    root, err = walker.clone_at(row["repo"], row["commit"])
    if root is None:
        res["boot"] = {"status": "BOOT FAILED", "reason": f"clone: {err}"}
        res["reason"] = res["boot"]["reason"]
        return _test_finish(res, out)
    boot, url = None, None
    try:
        recipes = walker.find_recipes(root, run_recipes or ())
        if not recipes:
            res["boot"] = {"status": "BOOT FAILED", "reason": "no usable compose file or Dockerfile in clone"}
        for rec in recipes[:3]:
            say(f"     boot: {rec['path'].relative_to(root)}")
            boot = walker.Boot(cat_slug, row["app"], root, rec)
            ok, why = boot.up()
            if ok:
                url, why = boot.wait_for_ui()
            if url:
                res["boot"] = {"status": "BOOTED", "recipe": str(rec["path"].relative_to(root)), "url": url, "detail": why}
                break
            res["boot"] = {"status": "BOOT FAILED", "reason": why, "recipe": str(rec["path"].relative_to(root)),
                           "container_logs": boot.container_logs() if ok else "", "log": boot.log}
            boot.down()
            boot = None
        if not url:
            res["reason"] = f"boot failed: {res['boot'].get('reason')}"
            return _test_finish(res, out)
        say(f"     booted at {url}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport=walker.VIEWPORT, ignore_https_errors=True)
            page = ctx.new_page()
            gate = walker.Walk(page, out, url)
            if not gate.goto(url):
                res["gate"] = {"state": "PAGE FAILED TO LOAD"}
            else:
                state, steps = gate.get_in()
                res["gate"] = {"state": state, "steps": steps, "final_url": page.url}
                say(f"     gate: {state} after {len(steps)} step(s)")
                if state in PASS_REQUIRES_GATE:
                    res["test"] = ButtonTest(page, out, url, gate).run()
            browser.close()
    except Exception as ex:
        res["error"] = f"{type(ex).__name__}: {str(ex)[:300]}"
    finally:
        if boot:
            boot.down()
        shutil.rmtree(root, ignore_errors=True)
    if res.get("error") and not res["test"]:
        res["reason"] = f"test error: {res['error']}"
        return _test_finish(res, out)
    res["verdict"], res["reason"] = judge(res["gate"].get("state"), res["test"])
    return _test_finish(res, out)


def _test_finish(res, out):
    res["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    res["folder"] = str(out.relative_to(HERE))
    (out / "result.json").write_text(json.dumps(res, indent=1, default=str))
    t = res.get("test") or {}
    md = [f"# Test report — {res['app']}", "",
          f"Repo {res['repo']} @ `{res['commit']}`  ", f"{res['started']} → {res['finished']}", "",
          f"## Verdict: **{res['verdict']}**" + (f" — {res['reason']}" if res["reason"] else ""), "",
          f"- Boot: **{res['boot'].get('status', '—')}** {res['boot'].get('recipe', '')} {res['boot'].get('url', '')} "
          f"{res['boot'].get('reason', '')}",
          f"- Getting in: **{res['gate'].get('state', '—')}**"]
    for s in res["gate"].get("steps", []):
        md.append(f"  - {s['action']} → {s.get('to', s.get('url'))} → screenshots/{s['shot']}")
    if t:
        md += ["", f"## Coverage: {t['screens_visited']} screens visited, {t['controls_clicked']} of "
                   f"{t['controls_found']} controls clicked ({t['controls_skipped']} skipped), "
                   f"{t['screens_failed_to_load']} screens failed to load, {t['screens_not_visited_cap']} not visited (cap)",
               f"Server errors: {len(t['server_errors'])} · Page crashes: {len(t['crashes'])} · "
               f"JS errors: {len(t['js_errors'])} · External links: {len(t['external_links'])}", ""]
        for i, s in enumerate(t["screens"], 1):
            md += [f"### Screen {i}: {s['title'] or '(no title)'}", f"`{s['url']}` — {s['load']}"
                   + (f" — screenshots/{s['screenshot']}" if s.get("screenshot") else ""), ""]
            if s["controls"]:
                md += ["| Control | Result | Screenshot |", "|---|---|---|"]
                for c in s["controls"]:
                    ctl = (c["control"] or "").replace("|", "/")[:70]
                    md.append(f"| {ctl} | {c.get('result', '')}{(' → ' + c['to'][:80]) if c.get('to') and c.get('result') == 'opened screen' else ''} | "
                              f"{('screenshots/' + c['screenshot']) if c.get('screenshot') else ''} |")
                md.append("")
    if res.get("error"):
        md += ["", f"Error: {res['error']}"]
    (out / "TEST_REPORT.md").write_text("\n".join(md) + "\n")
    say(f"     TEST {res['verdict']}" + (f": {res['reason']}" if res["reason"] else
                                          f" — {t.get('screens_visited')} screens, {t.get('controls_clicked')} clicks"))
    return res


# --------------------------------------------------------------------------- library
def admit_to_library(cat, row, test):
    d = LIB / cat["slug"]
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    src = HERE / test["folder"]
    shutil.copytree(src / "screenshots", d / "screenshots")
    shutil.copy(src / "TEST_REPORT.md", d / "TEST_REPORT.md")
    t = test["test"]
    entry = {"category": cat["name"], "category_slug": cat["slug"], "source": f"{SITE}/category/{cat['slug']}/",
             "app": row["app"], "repo": row["repo"], "commit": row["commit"],
             "licence": row["licence_from_file"], "licence_file": row["licence_file"],
             "licence_files_checked": row.get("licence_files_checked"),
             "selfhostindex_health": row["health"], "stars": row["stars"], "replaces": row["replaces"],
             "boot_recipe": test["boot"].get("recipe"), "gate": test["gate"].get("state"),
             "screens_visited": t["screens_visited"], "controls_clicked": t["controls_clicked"],
             "controls_found": t["controls_found"], "server_errors": len(t["server_errors"]),
             "js_errors": len(t["js_errors"]), "admitted": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (d / "ENTRY.json").write_text(json.dumps(entry, indent=2))
    write_library_index()
    say(f"     ADMITTED to {LIBRARY_DIR}/{cat['slug']}/")


def write_library_index():
    rows = []
    for f in sorted(LIB.glob("*/ENTRY.json")):
        rows.append(json.loads(f.read_text()))
    lines = ["# Completed library", "",
             f"{len(rows)} entries. Each passed: licence (every licence file), screens, container recipe, "
             "booted from its own recipe, got in, every reachable button clicked with no server error or crash.", "",
             "| Category | App | Licence | Health | Screens | Clicks | Repo @ commit | Folder |", "|---|---|---|---|---|---|---|---|"]
    for e in rows:
        lines.append(f"| {e['category']} | **{e['app']}** | {e['licence']} | {e['selfhostindex_health']} | "
                     f"{e['screens_visited']} | {e['controls_clicked']}/{e['controls_found']} | "
                     f"{e['repo']} @ {e['commit'][:10]} | {e['category_slug']}/ |")
    LIB.mkdir(exist_ok=True)
    (LIB / "LIBRARY.md").write_text("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- directory link
def load_directory_index():
    """Map repo URL -> awesome-selfhosted-data entry, so robustness uses real commit/release data."""
    entries, head = finder.refresh_directory()
    idx = {}
    for e in entries:
        idx[e["source_code_url"].rstrip("/").lower()] = e
    return idx, head


# --------------------------------------------------------------------------- per category
def run_category(cat, directory, taken, today):
    slug = cat["slug"]
    say(f"\n=== {slug}  ({cat['name']}) ===")
    done = LIB / slug / "ENTRY.json"
    if RESUME and TEST_ON and done.exists():
        e = json.loads(done.read_text())
        say(f"  already in library: {e['app']} — skipped (RESUME)")
        taken[re.sub(r'[^a-z0-9]+', '-', e['app'].lower())] = slug
        return {"slug": slug, "category": cat["name"], "site_says": cat["stated_count"], "fetch_error": None,
                "refused": [], "top": {"app": e["app"], "slug": "", "repo": e["repo"], "health": e["selfhostindex_health"],
                                       "stars": e["stars"], "listed_licence": e["licence"], "licence_from_file": e["licence"],
                                       "licence_file": e["licence_file"], "replaces": e["replaces"], "commit": e["commit"],
                                       "test_verdict": "PASS (earlier run)"}}
    res = {"slug": slug, "category": cat["name"], "site_says": cat["stated_count"],
           "top": None, "refused": [], "fetch_error": None}
    try:
        stated, apps = parse_category_page(fetch(f"/category/{slug}/"))
    except Exception as ex:
        res["fetch_error"] = f"category page: {ex}"
        say(f"  FETCH FAILED: {ex}")
        return res
    res["parsed_apps"] = len(apps)
    res["page_numberOfItems"] = stated
    if stated is not None and stated != len(apps):
        say(f"  WARNING: page says {stated} apps, parsed {len(apps)}")
    say(f"  {len(apps)} apps on the page (tile said {cat['stated_count']})")

    apps.sort(key=rank_key)
    candidates = []
    for a in apps:
        why = None
        if SKIP_ARCHIVED and a["archived"]:
            why = "archived"
        elif (a["health"] or 0) < MIN_HEALTH:
            why = f"health {a['health']} < {MIN_HEALTH}"
        elif PREFILTER_ON_LISTED_LICENCE and not listed_licence_ok(a["listed_licence"]):
            why = f"listed licence {a['listed_licence'] or '(none)'} not allowed"
        elif not ALLOW_SAME_APP_IN_TWO_CATEGORIES and a["slug"] in taken:
            why = f"already top app in {taken[a['slug']]}"
        if why:
            res["refused"].append({"app": a["name"], "health": a["health"], "stars": a["stars"],
                                   "stage": "pre-filter", "reason": why})
        else:
            candidates.append(a)
    say(f"  {len(candidates)} pass pre-filter; gating up to {MAX_CANDIDATES_PER_CATEGORY}")

    for a in candidates[:MAX_CANDIDATES_PER_CATEGORY]:
        try:
            info = parse_app_page(fetch(f"/app/{a['slug']}/"))
        except Exception as ex:
            res["refused"].append({"app": a["name"], "stage": "app page", "reason": f"fetch failed: {ex}"})
            continue
        repo = (info.get("repo") or "").rstrip("/")
        if not repo:
            res["refused"].append({"app": a["name"], "stage": "app page", "reason": "no code repository listed"})
            continue
        entry = directory.get(repo.lower())
        linked = entry is not None
        if not linked:
            entry = {"name": a["name"], "source_code_url": repo, "stargazers_count": a["stars"],
                     "licenses": [a["listed_licence"]], "description": a["tagline"]}
        say(f"  -> {a['name']}  health {a['health']}  stars {a['stars']}  {repo}")
        r = dict(finder.inspect_repo(entry, today))
        if r.get("verdict") == "SURVIVES" and DEEP_LICENCE_AUDIT:
            ok, why, found = deep_licence_audit(finder.clone_dir_for(repo))
            r["deep_licence_files"] = found
            if not ok:
                r.update({"gate": "licence (deep)", "verdict": "REFUSED", "reason": why})
        remove_clone(repo)
        row = {"app": a["name"], "slug": a["slug"], "repo": repo, "health": a["health"],
               "stars": a["stars"], "listed_licence": a["listed_licence"],
               "page_licence": info.get("page_licence"), "replaces": a["replaces"],
               "tagline": a["tagline"], "language": info.get("language"),
               "commit": r.get("commit"), "licence_file": r.get("licence_file"),
               "licence_from_file": r.get("licence"), "directory_linked": linked,
               "gate": r.get("gate"), "verdict": r.get("verdict"), "reason": r.get("reason")}
        if r.get("verdict") == "SURVIVES" and TEST_ON:
            say("     gates passed — testing in Playwright")
            t = test_app(slug, row, r.get("run_recipes"))
            row["test_folder"] = t["folder"]
            row["test_verdict"] = t["verdict"]
            if t["verdict"] != "PASS":
                r.update({"gate": "test", "verdict": "FAILED TEST", "reason": t["reason"]})
                row.update({"gate": "test", "verdict": "FAILED TEST", "reason": t["reason"]})
        if r.get("verdict") == "SURVIVES":
            row["robustness"] = r["robustness"]["score"]
            row["robustness_note"] = "" if linked else "partial: repo not in directory dataset (no commit/release data)"
            row["screen_files_user"] = r["screens"]["screen_files_user"]
            row["login_evidence"] = r["screens"]["login_evidence"][:2]
            row["run_recipes"] = r["run_recipes"][:3]
            row["licence_files_checked"] = len(r.get("deep_licence_files", []))
            res["top"] = row
            taken[a["slug"]] = slug
            if TEST_ON:
                admit_to_library(cat, row, t)
            say(f"     TOP APP: {a['name']} ({r['licence']} from {r['licence_file']}, commit {r['commit'][:10]})")
            break
        res["refused"].append({**row, "stage": r.get("gate")})
        say(f"     {r.get('verdict')} at {r.get('gate')}: {r.get('reason')}")
    if not res["top"]:
        say("  NONE ADMITTED")
    return res


# --------------------------------------------------------------------------- output
def write_outputs(results, meta):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "categories").mkdir(exist_ok=True)
    for r in results:
        (OUT / "categories" / f"{r['slug']}.json").write_text(json.dumps(r, indent=2))
    (OUT / "TOP_APPS.json").write_text(json.dumps({"meta": meta, "results": results}, indent=2))
    admitted = [r for r in results if r["top"]]
    lines = ["# SelfHostIndex — top app per category",
             "",
             f"Run {meta['run_at']}. Source: {SITE}{CATEGORIES_PATH} ({meta['categories_on_site']} categories). "
             f"Ranked by {' then '.join(RANK_BY)}. Legal side: licence read from each repo's own file; "
             f"allowed = {', '.join(LICENCES)}.",
             "",
             f"**{len(admitted)} of {len(results)} categories have a top app. "
             f"{len(results) - len(admitted)} NONE ADMITTED.**",
             "",
             "| # | Category | Apps | Top app | Licence (file) | Health | Stars | Test | Replaces | Repo @ commit |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        t = r["top"]
        if t:
            lines.append(f"| {i} | {r['category']} | {r['site_says']} | **{t['app']}** | "
                         f"{t['licence_from_file']} ({t['licence_file']}) | {t['health']} | {t['stars']:,} | "
                         f"{t.get('test_verdict', 'not tested')} | "
                         f"{t['replaces'] or '—'} | {t['repo']} @ {t['commit'][:10]} |")
        else:
            why = r["fetch_error"] or f"{len(r['refused'])} refused — see categories/{r['slug']}.json"
            lines.append(f"| {i} | {r['category']} | {r['site_says']} | NONE ADMITTED | — | — | — | — | — | {why} |")
    lines += ["", "## Why the higher-rated apps lost", ""]
    for r in results:
        gated = [x for x in r["refused"] if x.get("stage") not in ("pre-filter",)]
        pre = [x for x in r["refused"] if x.get("stage") == "pre-filter"]
        lines.append(f"**{r['category']}** — {len(pre)} dropped at pre-filter"
                     + ("; cloned and refused: " + "; ".join(f"{x['app']} ({x['reason']})" for x in gated)
                        if gated else ""))
    (OUT / "TOP_APPS.md").write_text("\n".join(lines) + "\n")
    (OUT / "RUN_OUTPUT.txt").write_text("\n".join(LOG) + "\n")


# --------------------------------------------------------------------------- main
def main(argv):
    today = date.today()
    finder.VERBOSE = False
    finder.KEEP_CLONES = True   # clones kept only until this script's deep audit has read them
    cats = parse_categories(fetch(CATEGORIES_PATH))
    say(f"SelfHostIndex: {len(cats)} categories, {sum(c['stated_count'] or 0 for c in cats)} app listings")
    if EXPECTED_CATEGORY_COUNT and len(cats) != EXPECTED_CATEGORY_COUNT:
        sys.exit(f"STOP: site shows {len(cats)} categories, config expects {EXPECTED_CATEGORY_COUNT}. "
                 f"Check the site, then set EXPECTED_CATEGORY_COUNT.")
    if "--list" in argv:
        for c in cats:
            print(f"{c['stated_count']:>5}  {c['slug']:<22} {c['name']}")
        return
    on_site = len(cats)
    wanted = [a for a in argv if not a.startswith("-")]
    if wanted:
        unknown = set(wanted) - {c["slug"] for c in cats}
        if unknown:
            sys.exit(f"Unknown category slug(s): {', '.join(sorted(unknown))}. Use --list.")
        cats = [c for c in cats if c["slug"] in wanted]
    if TEST_ON:
        walker.preflight()                       # stops here if podman / compose / pulls don't work
        Path(walker.CLONE_DIR).mkdir(parents=True, exist_ok=True)
    directory, head = load_directory_index()
    taken, results = {}, []
    for c in cats:
        results.append(run_category(c, directory, taken, today))
        write_outputs(results, {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "categories_on_site": on_site,
                                "directory_dataset_commit": head, "allowed_licences": LICENCES,
                                "rank_by": RANK_BY})
    say(f"\nDONE: {sum(1 for r in results if r['top'])} of {len(results)} categories have a top app. "
        f"Table: {OUT / 'TOP_APPS.md'}" + (f"  Library: {LIB / 'LIBRARY.md'}" if TEST_ON else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
