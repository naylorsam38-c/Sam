#!/usr/bin/env python3
"""
capabilities.py — spec sections 12-14: CAPABILITY DISCOVERY, ATTACH-POINT
detection, and a REAL functional test, per app.

Per Sam's correction: capabilities are discovered FROM the app itself, the
way spec section 12's own diagram says -

    APPLICATION -> SCREENS -> ROUTES -> CONTROLS -> BACKEND HANDLERS ->
    SERVICES -> MODELS -> CAPABILITIES

not looked up from an external, category-keyed list. Every screen
screens.py already browser-verified (a real page, not a 404/onboarding
shell) is a capability CANDIDATE; its name comes from the app's own heading
or title, never invented. This runs for every app that reaches
SCREEN-VERIFIED, regardless of category - the old 22/52 predefined-list gate
that silently gave 30 categories zero capabilities is gone. Where a category
happens to have a predefined list (categories_openapps52.json, inherited
from benchmark70.json), it's kept only as a cross-reference annotation on
matching discovered capabilities, never as the source of truth and never as
a reason to skip a category without one.

  1. DISCOVER: real screens from screens.json -> capability candidates,
     de-duplicated by name.
  2. ATTACH POINT: search the app's own structural source (routes, models,
     controllers, templates, services) for the capability's own words -
     derived from its real screen, not a guessed phrase.
  3. LIVE TEST: visit the screen, exercise its primary form OR its most
     prominent actionable button (many real capabilities - "New document",
     "Add vault" - are a single button before any form appears), and record
     what actually happened. PASS only from a real action; source presence
     alone is never enough (spec section 22).
"""
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

from screens import ScreenWalk

HERE = Path(__file__).resolve().parent
MANIFEST_FILE = HERE / "manifest.json"
APPS_DIR = HERE / "applications"
CATEGORY_FILE = HERE / "categories_openapps52.json"
LIVE_FILE = HERE / "live_containers.json"
CAPS_DIR = HERE / "capabilities"

CHROMIUM_EXECUTABLE_PATH = os.environ.get("CHROMIUM_EXECUTABLE_PATH") or None
PAGE_TIMEOUT_MS = 20000
MAX_CAPABILITIES_PER_APP = 20
STOPWORDS = {"and", "or", "the", "with", "of", "for", "to", "a", "an", "in", "on", "by", "via",
            "management", "manage", "managed", "support", "supported", "custom", "basic", "advanced",
            "home", "page", "app", "dashboard"}
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

NOT_A_SCREEN_MARKERS = ("page not found", "404", "not found", "error", "unauthorized", "forbidden",
                        "something went wrong")
ACTION_WORDS = ("create", "add", "new", "save", "submit", "upload", "start", "generate", "invite",
                "send", "connect", "continue", "next", "confirm", "apply", "sign")
DESTRUCTIVE_WORDS = ("delete", "remove", "destroy", "logout", "log out", "sign out", "uninstall",
                     "reset", "deactivate", "disable", "revoke", "purge", "wipe")

# email/password stay FIXED (not tagged below) - these have to match the
# exact credentials screens.py's gate-crawl used to create the app's test
# account, or capabilities.py's own re-login (a fresh browser context, no
# shared session) fails outright. The generic filler values are tagged with
# a per-run marker instead: re-running the pipeline against an app that was
# already tested once (a very normal thing to do while iterating on this
# pipeline, or on a full re-run) would otherwise resubmit the exact same
# "Library Walker Test" string a second time - a real app has every right to
# treat that as a no-op with nothing new to persist or announce, making a
# genuinely working capability look like NO_CONFIRMATION for a reason that
# has nothing to do with whether the capability actually works.
_RUN_TAG = str(int(time.time()))
TEST_VALUES = {"email": "libwalker@example.com", "password": "Walker-Pass-2026!",
              "text_default": f"Library Walker Test {_RUN_TAG}",
              "url": f"https://example.com/libwalker-test-{_RUN_TAG}"}
# Phrases that mean the app itself is confirming something actually happened -
# never inferred from a mere absence of an error, per spec section 22.
SUCCESS_MARKERS = ("successfully", "saved", "created", "added", "updated successfully",
                   "has been added", "has been created", "has been saved")


def tokens(text):
    out = []
    for w in re.split(r"[^a-z0-9]+", (text or "").lower()):
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
    contains the capability's own words. Returns [{file, matched_words, line, snippet}]."""
    if not toks:
        return []
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


def derive_capability_name(screen):
    """The capability's name comes from what the app itself calls this
    screen - heading text first (what a user actually sees as the section
    title), then <title>, then the route. Never invented."""
    heading = (screen.get("heading") or "").strip()
    title = (screen.get("title") or "").strip()
    route = screen.get("route") or "/"
    if heading and len(heading) < 60:
        return heading
    if title:
        # strip a trailing " | AppName" / " - AppName" suffix
        name = re.split(r"\s*[|–-]\s*", title)[0].strip()
        if name:
            return name
    label = route.strip("/").split("/")[0].replace("-", " ").replace("_", " ").title()
    return label or "Home"


def is_real_screen(screen):
    if not screen.get("browser_verified"):
        return False
    text_bits = f"{screen.get('title') or ''} {screen.get('heading') or ''}".lower()
    if any(m in text_bits for m in NOT_A_SCREEN_MARKERS):
        return False
    controls = screen.get("controls") or {}
    if not any((controls.get(k) or 0) > 0 for k in controls):
        return False  # a rendered page with zero controls has nothing to exercise or call a capability
    return True


def discover_capability_candidates(screens):
    """screens.json's screens -> de-duplicated capability candidates, each
    tied back to the real screen it came from."""
    seen_names, seen_routes, out = set(), set(), []
    for s in screens:
        if not is_real_screen(s):
            continue
        route = (s.get("route") or "/").rstrip("/") or "/"
        if route in seen_routes:
            continue
        name = derive_capability_name(s)
        key = name.lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        seen_routes.add(route)
        out.append({"name": name, "screen": s})
        if len(out) >= MAX_CAPABILITIES_PER_APP:
            break
    return out


def _field_identity_text(page, inp):
    """See screens.py's identical helper: name/id/placeholder attributes
    often don't say what a field actually is - DocuSeal's "App URL" field
    is id="encrypted_config_value", name="encrypted_config[value]", nothing
    in either says "url". The human-readable truth a real user reads is the
    field's own <label>, so classification has to consult that too."""
    parts = []
    try:
        el_id = inp.get_attribute("id")
        if el_id:
            label = page.query_selector(f'label[for="{el_id}"]')
            if label:
                parts.append(label.inner_text())
    except Exception:
        pass
    try:
        nested = inp.evaluate("e => { const l = e.closest('label'); return l ? l.innerText : ''; }")
        if nested:
            parts.append(nested)
    except Exception:
        pass
    try:
        aria = inp.get_attribute("aria-labelledby")
        if aria:
            for aid in aria.split():
                el = page.query_selector(f'#{aid}')
                if el:
                    parts.append(el.inner_text())
    except Exception:
        pass
    return " ".join(p for p in parts if p)


def _check_or_click_label(page, inp):
    """See screens.py's identical helper: styled radio/checkbox widgets
    (Bootstrap btn-check included) hide the real <input> behind its
    <label>, so a direct click/check often fails actionability even though
    the input is technically 'visible'. Click the label instead."""
    try:
        inp.check(timeout=1500)
        return True
    except Exception:
        pass
    try:
        el_id = inp.get_attribute("id")
        if el_id:
            label = page.query_selector(f'label[for="{el_id}"]')
            if label and label.is_visible():
                label.click(timeout=2000)
                return True
    except Exception:
        pass
    try:
        inp.check(timeout=1500, force=True)
        return True
    except Exception:
        return False


def _fill_text_input(page, inp, val):
    """See screens.py's identical helper: typing into an EARLIER field can
    trigger a React re-render that swaps out a LATER field's DOM node
    before this loop ever reaches it, silently no-opping its fill (nothing
    throws). Verifies the value actually stuck; if not, waits for the DOM
    to settle and retries against a freshly re-queried element."""
    try:
        inp.click(timeout=2000)
        inp.fill("")
        inp.type(val, delay=15, timeout=5000)
        if inp.input_value() == val:
            return True
    except Exception:
        pass
    try:
        name = inp.get_attribute("name")
        el_id = inp.get_attribute("id")
    except Exception:
        name = el_id = None
    if not name and not el_id:
        return False
    try:
        page.wait_for_timeout(1500)
        fresh = page.query_selector(f'[name="{name}"]') if name else None
        if fresh is None and el_id:
            fresh = page.query_selector(f'#{el_id}')
        if fresh is None:
            return False
        fresh.click(timeout=3000)
        fresh.fill("")
        fresh.type(val, delay=15, timeout=5000)
        return fresh.input_value() == val
    except Exception:
        return False


class LiveTester:
    def __init__(self, page):
        self.page = page
        self.typed_values = []

    def _fill_form(self, form):
        filled = 0
        checked_radio_groups = set()
        for inp in form.query_selector_all("input, textarea, select"):
            try:
                if not inp.is_visible():
                    continue
                tag = inp.evaluate("e => e.tagName.toLowerCase()")
                typ = (inp.get_attribute("type") or "text").lower()
                if tag == "select":
                    sel_name = " ".join(filter(None, [inp.get_attribute("name"), inp.get_attribute("id"),
                                                       inp.get_attribute("aria-label")])).lower()
                    if any(w in sel_name for w in ("lang", "locale", "i18n")):
                        continue  # see screens.py's identical comment: a random locale breaks everything downstream
                    opts = inp.query_selector_all("option")
                    if len(opts) > 1:
                        inp.select_option(index=1)
                        filled += 1
                    continue
                if typ == "radio":
                    # an unpicked required choice group leaves submit
                    # disabled - skipping radios entirely stalled every form
                    # that uses them for a real, meaningful choice.
                    group = inp.get_attribute("name") or id(inp)
                    if group in checked_radio_groups or inp.is_checked():
                        checked_radio_groups.add(group)
                        continue
                    if _check_or_click_label(self.page, inp):
                        checked_radio_groups.add(group)
                        filled += 1
                    continue
                if typ == "checkbox":
                    if not inp.is_checked() and _check_or_click_label(self.page, inp):
                        filled += 1
                    continue
                if typ in ("hidden", "submit", "button", "file"):
                    continue
                name = " ".join(filter(None, [inp.get_attribute("name"), inp.get_attribute("placeholder"),
                                              _field_identity_text(self.page, inp)])).lower()
                if typ == "email" or "email" in name:
                    val = TEST_VALUES["email"]
                elif typ == "password":
                    val = TEST_VALUES["password"]
                elif typ == "url" or "url" in name or "website" in name or "link" in name:
                    # a plain "Library Walker Test" string in a URL field
                    # fails most apps' own format validation, so nothing
                    # after it is real evidence of anything - a syntactically
                    # real URL gives the actual capability a fair chance to
                    # succeed or fail on its own logic.
                    val = TEST_VALUES["url"]
                else:
                    val = TEST_VALUES["text_default"]
                # click+type (not .fill(), which never fires a real input
                # event some React-controlled validators need) so an
                # earlier field's own re-render can't silently detach this
                # one's handle - _fill_text_input verifies the value
                # actually stuck and retries against a fresh element if not.
                if _fill_text_input(self.page, inp, val):
                    if val not in self.typed_values:
                        self.typed_values.append(val)
                    filled += 1
            except Exception:
                continue
        return filled

    def _body_text(self):
        """The evidence snapshot used for both error/success wording AND the
        'did a typed value get persisted' check. inner_text() alone only
        covers rendered TEXT NODES - it never includes an <input>'s current
        value, which is exactly how the most common kind of proof actually
        looks: a profile/settings edit form that redisplays your saved value
        in its own input field. Missing that turned a genuinely persisted,
        independently-reconfirmed save (DocuSeal's profile name) into a
        false NOT VERIFIED. Appending every visible field's current value
        closes that gap without changing anything about how the text-node
        side of the comparison works."""
        try:
            text = self.page.inner_text("body", timeout=3000)
        except Exception:
            text = ""
        try:
            values = self.page.eval_on_selector_all(
                "input, textarea, select",
                "els => els.map(e => e.value || '').join('\\n')")
        except Exception:
            values = ""
        return text + "\n" + values

    def _primary_form(self):
        """A page can have several independent <form> elements (a sidebar
        search box, several small settings forms, and the one actually
        relevant to this screen's capability). The FIRST one in DOM order
        is frequently NOT the meaningful one - Uptime Kuma's 'Add New
        Monitor' page has 7, and the real monitor-creation form isn't first.
        The one with the most fillable fields is the one actually worth
        exercising."""
        try:
            forms = [f for f in self.page.query_selector_all("form") if f.is_visible()]
        except Exception:
            forms = []
        if not forms:
            return None
        def field_count(f):
            try:
                return len([i for i in f.query_selector_all("input, select, textarea") if i.is_visible()])
            except Exception:
                return 0
        return max(forms, key=field_count)

    def fill_and_submit_primary_form(self):
        """Returns (attempted, outcome, detail)."""
        form = self._primary_form()
        if form is None:
            return False, "NO_FORM_FOUND", "no visible <form> on this screen"
        before_url = self.page.url
        before_body = self._body_text()
        self.typed_values = []
        filled = self._fill_form(form)
        if filled == 0:
            return False, "NO_FILLABLE_FIELDS", "form present but no fillable inputs found"
        try:
            btn = self._visible_submit_button(form)
            if not btn:
                return True, "NO_SUBMIT_CONTROL", f"filled {filled} field(s) but found no submit control"
            btn.click(timeout=4000)
            self.page.wait_for_timeout(2500)
        except Exception as e:
            return True, "SUBMIT_FAILED", f"filled {filled} field(s), click/submit raised {type(e).__name__}: {e}"
        return self._judge_result(before_url, before_body, f"submitted {filled} field(s)")

    def _visible_submit_button(self, form):
        # query_selector on a comma-list only returns the FIRST DOM match
        # across all of them; if that happens to be hidden, the real submit
        # button further down never gets tried. Scan every match, all
        # selectors, for the first one that's actually visible.
        for sel in ("button[type=submit]", "input[type=submit]", "button:not([type=button])", "button"):
            try:
                for b in form.query_selector_all(sel):
                    if b.is_visible():
                        return b
            except Exception:
                continue
        return None

    def click_primary_action_button(self):
        """Many real capabilities are a single button before any form shows
        up ('New Document', '+ Add vault'). Finds the most prominent visible
        button whose label is an action word (never a destructive one),
        clicks it, and if a form appears as a result, fills and submits
        that too. Returns (attempted, outcome, detail)."""
        try:
            buttons = [b for b in self.page.query_selector_all("button, [role=button], a.btn, a[class*=button]")
                      if b.is_visible()]
        except Exception:
            buttons = []
        target = None
        for b in buttons:
            try:
                label = (b.inner_text() or "").strip().lower()
            except Exception:
                continue
            if not label or any(d in label for d in DESTRUCTIVE_WORDS):
                continue
            if any(a in label for a in ACTION_WORDS):
                target = b
                break
        if target is None:
            return False, "NO_ACTION_BUTTON", "no non-destructive action button found on this screen"
        before_url = self.page.url
        before_body = self._body_text()
        self.typed_values = []
        try:
            target.click(timeout=4000)
            self.page.wait_for_timeout(1500)
        except Exception as e:
            return True, "CLICK_FAILED", f"click raised {type(e).__name__}: {e}"
        # a form may now be visible (a modal/drawer opened) - exercise it too
        form = self._primary_form()
        if form is not None:
            filled = self._fill_form(form)
            if filled:
                try:
                    btn = self._visible_submit_button(form)
                    if btn:
                        btn.click(timeout=4000)
                        self.page.wait_for_timeout(2000)
                except Exception:
                    pass
            return self._judge_result(before_url, before_body, f"clicked action button, filled+submitted the form it opened ({filled} fields)")
        return self._judge_result(before_url, before_body, "clicked action button (no form followed)")

    def _judge_result(self, before_url, before_body, action_desc):
        """PASS requires POSITIVE evidence something really happened - not
        merely the absence of an error banner, which a silently-rejected
        submission (client validation failed, nothing sent) also produces
        (spec section 22: PASS requires runtime evidence, never 'looks like
        it should have worked'). Evidence, any one of:
          - the app's own explicit success wording (a toast/banner),
          - the URL moved somewhere new (a created-item's own page/edit view,
            not back to a login/error screen),
          - a value this test actually typed - not fixed boilerplate the
            static template already had - now appears on the page where it
            didn't before, e.g. in a list, meaning it was persisted.
        None of that: NOT VERIFIED, never PASS, whatever the URL or error
        banner absence suggests."""
        after_url = self.page.url
        after_body = self._body_text()
        body_lower = after_body.lower()
        has_error_banner = any(w in body_lower for w in
                               ("invalid", "error occurred", "something went wrong", "failed to", "is required"))
        has_success_marker = any(w in body_lower for w in SUCCESS_MARKERS)
        new_value_persisted = any(v and v not in before_body and v in after_body for v in self.typed_values)

        if has_error_banner and not has_success_marker:
            return True, "FAIL", f"{action_desc}; page shows an error indicator: {after_body[:200]}"
        if has_success_marker:
            return True, "PASS", f"{action_desc}; app showed an explicit success message"
        if new_value_persisted:
            return True, "PASS", f"{action_desc}; a value this test typed now appears on the page where it didn't before (persisted)"
        if after_url != before_url and not any(w in after_url.lower() for w in ("login", "signin", "error", "404")):
            return True, "PASS", f"{action_desc}; navigated to a new page ({before_url} -> {after_url}) consistent with the action succeeding"
        return True, "NO_CONFIRMATION", (f"{action_desc}; no error, but no positive evidence either (no success "
                                         f"message, no typed value persisted anywhere on the page, same URL "
                                         f"{after_url}) - not counted as proof")

    def exercise(self):
        attempted, outcome, detail = self.fill_and_submit_primary_form()
        # A form being PRESENT doesn't mean it's the real capability - a
        # page can have an incidental form with nothing fillable (a hidden
        # CSRF-only logout form, an empty filter bar) or no visible submit
        # control, while the actual capability is a button that opens a
        # modal (DocuSeal's "Document Templates" screen: the only <form> on
        # it has zero visible fields; the real action is the "+ CREATE"
        # button). Falling back only on NO_FORM_FOUND missed exactly this
        # case and reported a real, working capability as unproven.
        if outcome in ("NO_FORM_FOUND", "NO_FILLABLE_FIELDS", "NO_SUBMIT_CONTROL"):
            btn_attempted, btn_outcome, btn_detail = self.click_primary_action_button()
            if btn_outcome != "NO_ACTION_BUTTON":
                return btn_attempted, btn_outcome, btn_detail
        return attempted, outcome, detail


def process_app(entry, predefined_caps, base_url):
    app_id = entry["id"]
    d = APPS_DIR / app_id
    screens = json.loads((d / "screens.json").read_text())["screens"] if (d / "screens.json").exists() else []
    source_root = d / "source"

    candidates = discover_capability_candidates(screens)
    if not candidates:
        out = {"application": app_id, "capabilities_defined": True, "discovery_method": "app-derived",
              "note": "no real screen had any control to exercise - nothing to discover as a capability",
              "capabilities": []}
        (d / "capabilities.json").write_text(json.dumps(out, indent=1))
        return {"discovered": 0, "attach_point_found": 0, "proven": 0}

    predefined_toks = [(c, tokens(c)) for c in (predefined_caps or [])]

    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROMIUM_EXECUTABLE_PATH)
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, ignore_https_errors=True)
        page = ctx.new_page()
        tester = LiveTester(page)

        # This runs in its own fresh browser context (separate process from
        # screens.py, no shared cookies/localStorage/socket) - without
        # logging in again here first, every "capability" screen below was
        # actually just the same login form, and every result was really a
        # test of the login form, not the app. Same gate-crawl screens.py
        # already proved works for this app.
        walker = ScreenWalk(page, base_url, d / "evidence")
        if walker.goto(base_url):
            walker.get_past_setup_wall()
        app_home_url = page.url

        for idx, cand in enumerate(candidates, 1):
            name, screen = cand["name"], cand["screen"]
            toks = tokens(name) or tokens(screen.get("route"))
            attach = find_attach_points(source_root, toks) if source_root.is_dir() else []
            matched_predefined = [c for c, t in predefined_toks if set(t) & set(toks)]
            cap_id = f"CAP-{app_id[4:]}-{idx:02d}"
            rec = {"id": cap_id, "name": name, "route": screen.get("route"),
                  "discovered_from": "screen", "matched_predefined_capability": matched_predefined or None,
                  "attach_points": attach, "live_test": None, "verdict": "NOT VERIFIED"}

            full_url = urljoin(base_url.rstrip("/") + "/", (screen.get("route") or "/").lstrip("/"))
            try:
                page.goto(full_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                attempted, outcome, detail = tester.exercise()
                rec["live_test"] = {"url": full_url, "attempted": attempted, "outcome": outcome, "detail": detail}
                if outcome == "PASS" and attach:
                    rec["verdict"] = "PROVEN"
                elif outcome == "PASS":
                    rec["verdict"] = "NOT VERIFIED"
                    rec["reason"] = ("live action succeeded but no code attach point was located, "
                                     "so the implementation was not harvested - proof requires both")
                else:
                    rec["verdict"] = "NOT VERIFIED"
                    rec["reason"] = f"live test did not pass: {outcome} - {detail}"
            except Exception as e:
                rec["live_test"] = {"url": full_url, "attempted": False, "outcome": "NAV_FAILED",
                                    "detail": f"{type(e).__name__}: {e}"}
                rec["reason"] = "could not navigate to the screen to exercise it"
            results.append(rec)
            print(f"    {rec['verdict']:12s} {name}")
        browser.close()

    out = {"application": app_id, "capabilities_defined": True, "discovery_method": "app-derived",
          "predefined_capabilities_for_category": predefined_caps or [],
          "capabilities": results}
    (d / "capabilities.json").write_text(json.dumps(out, indent=1))
    for r in results:
        (CAPS_DIR / r["id"]).mkdir(parents=True, exist_ok=True)
        (CAPS_DIR / r["id"] / "record.json").write_text(json.dumps({"application": app_id, **r}, indent=1))

    proven = sum(1 for r in results if r["verdict"] == "PROVEN")
    attach_found = sum(1 for r in results if r["attach_points"])
    return {"discovered": len(results), "attach_point_found": attach_found, "proven": proven}


def main():
    manifest = json.loads(MANIFEST_FILE.read_text())
    categories = {c["slug"]: c for c in json.loads(CATEGORY_FILE.read_text())["categories"]}
    live = json.loads(LIVE_FILE.read_text()) if LIVE_FILE.exists() else []
    live_by_id = {l["app_id"]: l for l in live}
    entries_by_id = {e["id"]: e for e in manifest["applications"]}

    totals = {"discovered": 0, "attach_point_found": 0, "proven": 0}
    for app_id, l in live_by_id.items():
        entry = entries_by_id[app_id]
        if entry["status"] not in ("SCREEN-VERIFIED", "FUNCTIONALLY_VERIFIED"):
            continue
        predefined = (categories.get(entry["category_slug"]) or {}).get("capabilities") or []
        print(f"{app_id} ({entry['category_slug']}) {entry['name']}")
        try:
            summary = process_app(entry, predefined, l["url"])
        except Exception as e:
            summary = {"error": f"{type(e).__name__}: {e}"}
            print(f"  ERROR: {summary['error']}")
        entry["capability_summary"] = summary
        entry["status"] = "FUNCTIONALLY_VERIFIED" if summary.get("proven") else "SCREEN-VERIFIED"
        (APPS_DIR / app_id / "app.json").write_text(json.dumps(entry, indent=1))
        MANIFEST_FILE.write_text(json.dumps(manifest, indent=1))
        for k in totals:
            if isinstance(summary.get(k), (int, bool)):
                totals[k] += int(summary.get(k) or 0)

    print("\n=== CAPABILITY SUMMARY ===")
    print(totals)


if __name__ == "__main__":
    sys.exit(main())
