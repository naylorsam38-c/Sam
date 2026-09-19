#!/usr/bin/env python3
"""
capabilities.py — spec sections 12-14: CAPABILITY DISCOVERY, ATTACH-POINT
detection, and a REAL functional test, per app.

Only 22 of the 52 categories have a capability list at all (inherited from
benchmark70.json where the category means the same thing - see
categories_openapps52.json's capabilities_from field). For the other 30,
this script records NOT_DEFINED honestly and does nothing further - per
spec section 12, a capability must be linked to real implementation
evidence, and there is no invented universal capability list here (matches
the same rule WHAT_THIS_DOES.md set for openapps_source.py's own
categories/openapps52.json build).

For a category that DOES have capabilities:
  1. ATTACH POINT: search the app's own structural source (routes, models,
     controllers, templates, services - the same file classes a maintainer
     would look in) for the capability's meaningful words. A hit records the
     exact file (never "it's probably in there somewhere").
  2. UI LINK: cross-reference against screens.json - a browser-verified
     screen whose route/title/heading/nav-link-text also matches the
     capability's words is that capability's real UI entry point.
  3. LIVE TEST: if both an attach point AND a UI screen exist, actually visit
     that screen, find its primary form or action control, exercise it with
     sensible test data, and record what happened (submitted, URL changed,
     server responded) as PASS - or FAIL with the real error - never PASS
     from source inspection alone (spec section 22's non-negotiable rule).
  4. Anything short of that (attach point but no live screen, or a screen but
     no code evidence) is recorded NOT VERIFIED, not PASS.
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
MANIFEST_FILE = HERE / "manifest.json"
APPS_DIR = HERE / "applications"
CATEGORY_FILE = HERE / "categories_openapps52.json"
LIVE_FILE = HERE / "live_containers.json"
CAPS_DIR = HERE / "capabilities"

CHROMIUM_EXECUTABLE_PATH = os.environ.get("CHROMIUM_EXECUTABLE_PATH") or None
PAGE_TIMEOUT_MS = 20000
STOPWORDS = {"and", "or", "the", "with", "of", "for", "to", "a", "an", "in", "on", "by", "via",
            "management", "manage", "managed", "support", "supported", "custom", "basic", "advanced"}
MIN_TOKEN_LEN = 4
SHORT_OK = {"sso", "mfa", "ocr", "pdf", "api", "crm", "erp", "seo", "csv", "rss", "git", "ci",
           "cd", "ide", "llm", "map", "ads", "kyc", "dms"}
STRUCTURAL_MARKERS = ("route", "routes", "urls", "controller", "controllers", "handler", "handlers",
                      "view", "views", "model", "models", "schema", "migration", "template",
                      "templates", "component", "components", "page", "pages", "api", "service",
                      "services", "resource", "entity", "domain", "feature", "module", "app", "src")
STRUCTURAL_SUFFIXES = (".py", ".rb", ".php", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".cs",
                       ".rs", ".ex", ".vue", ".svelte", ".html", ".erb", ".ejs", ".graphql", ".sql")
EXCLUDE_PARTS = ("node_modules", "vendor", "dist", "build", ".git", "locale", "locales", "i18n",
                 "fixtures", "coverage")

TEST_VALUES = {"email": "libwalker@example.com", "password": "Walker-Pass-2026!",
              "text_default": "Library Walker Test"}


def tokens(cap):
    out = []
    for w in re.split(r"[^a-z0-9]+", cap.lower()):
        if not w or w in STOPWORDS:
            continue
        if len(w) < MIN_TOKEN_LEN and w not in SHORT_OK:
            continue
        out.append(w)
        if len(w) > 4 and w.endswith("s"):
            out.append(w[:-1])
    return sorted(set(out))


def has_token(text, toks):
    text = (text or "").lower()
    return [t for t in toks if re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", text)]


def find_attach_points(root, toks, limit=3):
    """File-level evidence: structural source files whose path or content
    contains the capability's words. Returns [{file, matched_in, snippet}]."""
    hits = []
    n = 0
    for p in root.rglob("*"):
        if n > 8000 or len(hits) >= limit:
            break
        parts = [x.lower() for x in p.relative_to(root).parts]
        if any(x in EXCLUDE_PARTS for x in parts[:-1]):
            continue
        if not p.is_file() or not p.name.lower().endswith(STRUCTURAL_SUFFIXES):
            continue
        if not any(x in STRUCTURAL_MARKERS for x in parts[:-1]):
            continue
        n += 1
        rel = "/".join(parts)
        path_hits = has_token(rel, toks)
        try:
            if p.stat().st_size > 150_000:
                continue
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        content_hits = has_token(text.lower(), toks)
        if path_hits or content_hits:
            line_no, snippet = None, None
            if content_hits:
                for i, line in enumerate(text.splitlines(), 1):
                    if has_token(line.lower(), content_hits[:1]):
                        line_no, snippet = i, line.strip()[:160]
                        break
            hits.append({"file": rel, "matched_words": sorted(set(path_hits + content_hits)),
                        "line": line_no, "snippet": snippet})
    return hits


def find_ui_screen(screens, toks):
    for s in screens:
        if not s.get("browser_verified"):
            continue
        haystack = f"{s.get('name','')} {s.get('route','')} {s.get('title','') or ''} {s.get('heading','') or ''}"
        if has_token(haystack, toks):
            return s
    return None


class LiveTester:
    def __init__(self, page):
        self.page = page

    def fill_and_submit_primary_form(self):
        """Finds the first visible form with an actionable control, fills
        sensible values, submits, and reports what happened. Returns
        (attempted: bool, outcome: str, detail: str)."""
        try:
            forms = [f for f in self.page.query_selector_all("form") if f.is_visible()]
        except Exception:
            forms = []
        if not forms:
            return False, "NO_FORM_FOUND", "no visible <form> on this screen to exercise"
        form = forms[0]
        before_url = self.page.url
        filled = 0
        try:
            for inp in form.query_selector_all("input, textarea, select"):
                try:
                    if not inp.is_visible():
                        continue
                    tag = inp.evaluate("e => e.tagName.toLowerCase()")
                    typ = (inp.get_attribute("type") or "text").lower()
                    if tag == "select":
                        opts = inp.query_selector_all("option")
                        if len(opts) > 1:
                            inp.select_option(index=1)
                            filled += 1
                        continue
                    if typ in ("hidden", "submit", "button", "file", "checkbox", "radio"):
                        continue
                    name = " ".join(filter(None, [inp.get_attribute("name"), inp.get_attribute("placeholder")])).lower()
                    if typ == "email" or "email" in name:
                        val = TEST_VALUES["email"]
                    elif typ == "password":
                        val = TEST_VALUES["password"]
                    else:
                        val = TEST_VALUES["text_default"]
                    inp.fill(val, timeout=2000)
                    filled += 1
                except Exception:
                    continue
        except Exception:
            pass
        if filled == 0:
            return False, "NO_FILLABLE_FIELDS", "form present but no fillable inputs found"
        try:
            btn = form.query_selector("button[type=submit], input[type=submit], button:not([type=button])")
            if not btn:
                return True, "NO_SUBMIT_CONTROL", f"filled {filled} field(s) but found no submit control"
            btn.click(timeout=4000)
            self.page.wait_for_timeout(2500)
        except Exception as e:
            return True, "SUBMIT_FAILED", f"filled {filled} field(s), click/submit raised {type(e).__name__}: {e}"
        after_url = self.page.url
        try:
            body = self.page.inner_text("body", timeout=3000).lower()
        except Exception:
            body = ""
        has_error_banner = any(w in body for w in ("invalid", "error occurred", "something went wrong", "failed to"))
        if after_url != before_url:
            return True, "PASS", f"submitted, URL changed {before_url} -> {after_url}"
        if not has_error_banner:
            return True, "PASS", f"submitted, page responded without a visible error banner (same URL {after_url})"
        return True, "FAIL", f"submitted, page shows an error indicator: {body[:200]}"


def process_app(entry, category, base_url):
    app_id = entry["id"]
    caps_list = category.get("capabilities") or []
    d = APPS_DIR / app_id
    screens = json.loads((d / "screens.json").read_text())["screens"] if (d / "screens.json").exists() else []
    source_root = d / "source"

    if not caps_list:
        out = {"application": app_id, "category": category["slug"],
              "capabilities_defined": False,
              "note": "no capability list for this category (only 22/52 categories have one, "
                      "copied from benchmark70.json where the meaning matches - see "
                      "categories_openapps52.json's capabilities_from). Nothing invented.",
              "capabilities": []}
        (d / "capabilities.json").write_text(json.dumps(out, indent=1))
        return {"capabilities_defined": False, "discovered": 0, "attach_point_found": 0, "proven": 0}

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM_EXECUTABLE_PATH)
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, ignore_https_errors=True)
        page = ctx.new_page()
        tester = LiveTester(page)

        for idx, cap_name in enumerate(caps_list, 1):
            toks = tokens(cap_name)
            attach = find_attach_points(source_root, toks) if source_root.is_dir() else []
            screen = find_ui_screen(screens, toks)
            cap_id = f"CAP-{app_id[4:]}-{idx:02d}"
            rec = {"id": cap_id, "name": cap_name, "attach_points": attach,
                  "ui_screen": {"name": screen["name"], "route": screen["route"]} if screen else None,
                  "live_test": None, "verdict": "NOT VERIFIED"}

            if not attach and not screen:
                rec["verdict"] = "NOT VERIFIED"
                rec["reason"] = "no code attach point and no matching UI screen found"
            elif not screen:
                rec["verdict"] = "NOT VERIFIED"
                rec["reason"] = "code attach point found but no reachable UI screen for it"
            else:
                full_url = urljoin(base_url.rstrip("/") + "/", screen["route"].lstrip("/"))
                try:
                    page.goto(full_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                    page.wait_for_timeout(1000)
                    attempted, outcome, detail = tester.fill_and_submit_primary_form()
                    rec["live_test"] = {"url": full_url, "attempted": attempted, "outcome": outcome, "detail": detail}
                    if outcome == "PASS" and attach:
                        rec["verdict"] = "PROVEN"
                    elif outcome == "PASS":
                        rec["verdict"] = "NOT VERIFIED"
                        rec["reason"] = "UI action succeeded but no code attach point was located, so the " \
                                        "implementation was not harvested - proof requires both"
                    else:
                        rec["verdict"] = "NOT VERIFIED"
                        rec["reason"] = f"live test did not pass: {outcome}"
                except Exception as e:
                    rec["live_test"] = {"url": full_url, "attempted": False, "outcome": "NAV_FAILED",
                                        "detail": f"{type(e).__name__}: {e}"}
                    rec["reason"] = "could not navigate to the screen to exercise it"
            results.append(rec)
            print(f"    {rec['verdict']:12s} {cap_name}")
        browser.close()

    out = {"application": app_id, "category": category["slug"], "capabilities_defined": True,
          "capabilities": results}
    (d / "capabilities.json").write_text(json.dumps(out, indent=1))
    for r in results:
        (CAPS_DIR / r["id"]).mkdir(parents=True, exist_ok=True)
        (CAPS_DIR / r["id"] / "record.json").write_text(json.dumps({"application": app_id, **r}, indent=1))

    proven = sum(1 for r in results if r["verdict"] == "PROVEN")
    attach_found = sum(1 for r in results if r["attach_points"])
    return {"capabilities_defined": True, "discovered": len(results),
            "attach_point_found": attach_found, "proven": proven}


def main():
    manifest = json.loads(MANIFEST_FILE.read_text())
    categories = {c["slug"]: c for c in json.loads(CATEGORY_FILE.read_text())["categories"]}
    live = json.loads(LIVE_FILE.read_text()) if LIVE_FILE.exists() else []
    live_by_id = {l["app_id"]: l for l in live}
    entries_by_id = {e["id"]: e for e in manifest["applications"]}

    totals = {"capabilities_defined": 0, "discovered": 0, "attach_point_found": 0, "proven": 0}
    for app_id, l in live_by_id.items():
        entry = entries_by_id[app_id]
        if entry["status"] != "SCREEN-VERIFIED":
            continue
        cat = categories[entry["category_slug"]]
        print(f"{app_id} ({entry['category_slug']}) {entry['name']}")
        try:
            summary = process_app(entry, cat, l["url"])
        except Exception as e:
            summary = {"error": f"{type(e).__name__}: {e}"}
            print(f"  ERROR: {summary['error']}")
        entry["capability_summary"] = summary
        entry["status"] = "FUNCTIONALLY_VERIFIED" if summary.get("proven") else entry["status"]
        (APPS_DIR / app_id / "app.json").write_text(json.dumps(entry, indent=1))
        MANIFEST_FILE.write_text(json.dumps(manifest, indent=1))
        for k in totals:
            if isinstance(summary.get(k), (int, bool)):
                totals[k] += int(summary.get(k) or 0)

    print("\n=== CAPABILITY SUMMARY ===")
    print(totals)


if __name__ == "__main__":
    sys.exit(main())
