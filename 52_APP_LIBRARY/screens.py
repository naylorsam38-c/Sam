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

TEST_USER = {"name": "Library Walker", "username": "libwalker", "email": "libwalker@example.com",
            "password": "Walker-Pass-2026!", "url": "https://example.com/libwalker-test"}
GATE_WORDS = ("sign up", "signup", "register", "create account", "get started", "setup", "set up",
             "install", "create admin", "continue", "next", "finish", "log in", "login", "sign in",
             "weiter", "next step", "proceed", "deploy", "confirm", "create", "dashboard")
# "dashboard": Infisical's own post-setup wizard ends on a "Your instance is
# ready - Go to dashboard / Access server console" screen where the choice
# is a plain JS-routed <button>, not an <a href> collect_nav_links() would
# have picked up as ordinary in-app navigation - without this, the gate
# crawl correctly stops (gate_state does read "IN": there's no login/setup
# form left) but nothing ever clicks through into the actual app, so every
# "screen" discovered afterward is this same launch-pad shell.
# Labels that must never be the thing a gate-crawl step clicks, even when
# they sit right next to a real forward action and look like part of the
# "same choice group" - Infisical's own multi-step signup wizard puts
# "Back" and "Create organization" as sibling buttons on its organization
# step; _find_gate_form doesn't recognise a bare "create organization"
# button as a gate (fixed above by adding "create" to GATE_WORDS) but
# _click_choice_step's sibling-group heuristic still needs to know never to
# pick the backward one first, in case some other step's wording isn't
# caught by GATE_WORDS at all.
BACKWARD_WORDS = ("back", "cancel", "skip", "previous", "prev", "close", "dismiss")
# When a landing page offers BOTH "Sign in" and "Sign up" as parallel
# top-level choices (shiptrack's own home page does exactly this), both are
# equally valid GATE_WORDS matches of the same length ("sign in" / "sign
# up", 7 chars each) - a pure shortest-label tie-break has no way to prefer
# one over the other and can arbitrarily pick "Sign in" first, which can
# never succeed with credentials for an account that doesn't exist yet on
# a fresh instance. Creating the account first is the same order the rest
# of this crawler already follows (DocuSeal's, Infisical's own setup
# wizards both create the account before anything else), so a signup-shaped
# word wins the tie whenever both are present in the same choice group.
SIGNUP_WORDS = ("sign up", "signup", "register", "create account", "get started", "setup", "set up",
               "create admin", "create")
MAX_GATE_STEPS = 9

# A page that LOOKS rendered (has real text, a nonzero body) can still be
# genuinely broken - a stuck websocket, a crashed client bundle, a server
# error rendered into the DOM. Counting that as "browser_verified" is exactly
# the false positive spec section 22 warns about ("never report PASS because
# it looks like it should work"). These phrases, seen prominently, mean the
# screen is not actually working, whatever else is on it.
ERROR_STATE_MARKERS = ("cannot connect to the socket server", "cannot connect to server",
                       "internal server error", "500 internal", "502 bad gateway",
                       "503 service unavailable", "application error", "an error occurred",
                       "something went wrong", "failed to fetch", "failed to load",
                       "unexpected error", "this page could not be", "reconnecting...",
                       "connection lost", "unable to connect")

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
            if ":" in r or "{" in r:
                continue  # router path pattern (":id", "{id}"), not a real navigable URL
            if LIKELY_UI_ROUTE.match(r) and len(r) < 60:
                routes.add(r)
        if len(routes) >= MAX_STATIC_ROUTES:
            break
    return sorted(routes)[:MAX_STATIC_ROUTES]


def _field_identity_text(page, inp):
    """name/id/placeholder attributes often don't say what a field actually
    is - DocuSeal's "App URL" field is id="encrypted_config_value",
    name="encrypted_config[value]", nothing in either says "url". The
    human-readable truth a real user reads is the field's own <label>, so
    classification has to consult that too, not just attributes. Covers
    label[for=id], a label the input is nested inside, and aria-labelledby."""
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
    """Many styled radio/checkbox widgets (Bootstrap's btn-check included)
    visually hide the real <input> behind its <label>, so a direct click/
    check on the input fails Playwright's actionability check (something
    else is on top of it at that point) even though the input is
    technically 'visible'. The real, working interaction a human performs
    is clicking the label. Falls back to a force-check only as a last
    resort, since that can silently miss a JS onChange handler."""
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
    """Typing into an EARLIER field can trigger a React re-render that
    swaps out a LATER field's DOM node before this loop ever reaches it -
    the ElementHandle for it, captured once at the top of the loop, then
    silently no-ops on click/fill (nothing throws) because it's pointing at
    a detached node. Infisical's own admin-signup form does exactly this:
    typing a password kicks off an async breach-check that re-renders the
    requirements panel sitting right above 'Confirm Password', so that
    field was never actually filled despite no error anywhere - the wizard
    then genuinely can't proceed ('Passwords do not match') and every
    'screen' discovered afterward was really just this same signup page.
    Verifies the value actually stuck; if not, waits for the DOM to settle
    and retries against a freshly re-queried element."""
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

    def _fill_visible_inputs(self, form):
        filled = 0
        checked_radio_groups = set()
        for inp in form.query_selector_all("input, select"):
            try:
                if not inp.is_visible():
                    continue
                tag = inp.evaluate("e => e.tagName.toLowerCase()")
                typ = (inp.get_attribute("type") or "text").lower()
                if tag == "select":
                    sel_name = " ".join(filter(None, [inp.get_attribute("name"), inp.get_attribute("id"),
                                                       inp.get_attribute("aria-label")])).lower()
                    if any(w in sel_name for w in ("lang", "locale", "i18n")):
                        # picking a random language/locale (index 1 was
                        # frequently a totally different language) put the UI
                        # into text this crawler's English gate-word matching
                        # can't read - leave the default alone.
                        continue
                    opts = inp.query_selector_all("option")
                    if len(opts) > 1:
                        inp.select_option(index=1)
                        filled += 1
                    continue
                if typ == "radio":
                    # a required single-choice group (database engine, plan
                    # tier, ...) leaves its submit button disabled until one
                    # option is picked - skipping radios entirely, as before,
                    # silently stalled every wizard that uses them.
                    group = inp.get_attribute("name") or id(inp)
                    if group in checked_radio_groups or inp.is_checked():
                        checked_radio_groups.add(group)
                        continue
                    if _check_or_click_label(self.page, inp):
                        checked_radio_groups.add(group)
                        filled += 1
                    continue
                if typ == "checkbox":
                    # commonly a required "I agree to the terms" gate on the
                    # same disabled-until-checked pattern as the radios above.
                    if not inp.is_checked() and _check_or_click_label(self.page, inp):
                        filled += 1
                    continue
                if typ in ("hidden", "submit", "button", "file"):
                    continue
                # attributes only for the general classification - name/id/
                # placeholder/autocomplete are precise, narrow signals.
                # Label TEXT is looser prose ("Limit allowed email domains"
                # contains "email" but wants a bare domain, not an address)
                # so it's consulted only for the one check that actually
                # needs it: nothing in a URL field's attributes necessarily
                # says "url" (DocuSeal's "App URL" setup field is
                # id="encrypted_config_value"), and "url"/"website"/"link"
                # are specific enough words that a label containing them
                # isn't at real risk of meaning something else.
                # id belongs alongside name/placeholder/autocomplete here -
                # Superset's own login form has a username field with
                # id="username" and NO name attribute at all (a React-
                # controlled input that doesn't need one for native form
                # submission), so classification found nothing to match on
                # and fell through to the generic name-field default.
                name = " ".join(filter(None, [inp.get_attribute("name"), inp.get_attribute("id"),
                                              inp.get_attribute("placeholder"),
                                              inp.get_attribute("autocomplete")])).lower()
                label_text = _field_identity_text(self.page, inp).lower()
                if "domain" in name or "domain" in label_text:
                    # a narrow, format-strict allowlist field ("Limit
                    # allowed email domains to...") - every filler value
                    # this crawler has is either a full email address or
                    # free text, neither a valid bare domain, and getting
                    # it wrong here silently blocked Infisical's own
                    # admin-setup wizard from ever reaching Continue. It's
                    # an optional restriction, so leaving it at its default
                    # (empty/unset) is the correct, safe choice - unlike
                    # the other fields here, filling it wrong is worse than
                    # not filling it at all.
                    continue
                if typ == "email" or "email" in name:
                    val = TEST_USER["email"]
                elif typ == "password" or "pass" in name:
                    val = TEST_USER["password"]
                elif (typ == "url" or "url" in name or "website" in name or "link" in name or
                      "url" in label_text or "website" in label_text or "link" in label_text):
                    # a plain name string fails most apps' own URL format
                    # validation, so a real syntactically-valid URL is needed
                    # for anything downstream to be honest evidence.
                    val = TEST_USER["url"]
                elif "user" in name or "login" in name or "handle" in name:
                    val = TEST_USER["username"]
                elif "name" in name or "org" in name or "team" in name or "company" in name or "workspace" in name:
                    val = TEST_USER["name"]
                else:
                    val = TEST_USER["name"]
                # click+type (not .fill(), which sets the DOM value directly
                # without a real input event) so React-controlled validators
                # actually see it - and _fill_text_input verifies the value
                # stuck and retries against a fresh element if an earlier
                # field's own re-render silently detached this one.
                if _fill_text_input(self.page, inp, val):
                    filled += 1
            except Exception:
                continue
        return filled

    def _submit(self, form):
        # query_selector only returns the FIRST DOM match for a selector; if
        # that one happens to be hidden (a lot of real forms have an earlier
        # non-visible button - a back button, a hidden template row), this
        # gave up even though the actual submit/next button was right there.
        # query_selector_all + scan for the first visible one fixes that -
        # but a component framework (Radix-UI style, seen on Infisical's own
        # multi-step admin-setup wizard) commonly implements each RADIO/
        # CHECKBOX inside a <form> as its own <button role=radio/checkbox>
        # with no label text at all, so "the first visible button in the
        # form" can just click one of THOSE instead of ever reaching the
        # real advance control - which, on that same wizard, isn't even
        # inside the <form> to begin with (the step's own fields are, but
        # the shared Back/Continue nav sits in a wrapper around it). A step
        # can look "submitted" 7 times over and never move.
        # A real nav/submit button's own label is inherently short ("Continue",
        # "Finish setup") - a GATE_WORDS substring turning up inside a much
        # LONGER label is a coincidence, not the actual advance control.
        # Infisical's own review step has this exactly: a "User access:
        # Anyone can **sign up**" summary/edit-card button sits right next to
        # the real "Finish setup" button, and "sign up" is a GATE_WORD - the
        # first-DOM-match version of this picked the summary card every time,
        # which just navigates back to re-edit that step, producing an
        # infinite Review <-> Control-who-can-join loop that never finishes.
        # Preferring the SHORTEST matching label breaks the tie correctly.
        # Gathers BOTH in-form and page-wide matches into one pool and picks
        # the single shortest label across all of them - NOT "in-form wins
        # whenever one exists". Tiering in-form ahead of page-wide was itself
        # a bug: on Infisical's review step, the real "Finish setup" button
        # lives entirely OUTSIDE the <form> (never a candidate at the in-form
        # tier at all), while the "User access: Anyone can **sign up**"
        # summary/edit-card - a coincidental GATE_WORDS hit - IS inside the
        # form, so it won every time regardless of length, and clicking it
        # just navigates back to re-edit that step.
        # Shortest-label-wins is a good tie-break but not the strongest
        # signal available: a native type=submit button IS the form's real
        # completion action; a type=button is just some other JS-handled
        # control that happens to share a GATE_WORD. Infisical's own login
        # form has this exactly - "Continue with LDAP/OIDC/SAML" (type=
        # button, disabled SSO options this instance never configured) are
        # each 1 character SHORTER than the real "Continue with Email"
        # (type=submit, the button that actually submits the email/password
        # just filled), so length-only picked a disabled control, the click
        # timed out, and nothing retried the button that would have worked.
        # Ranks by (is a real submit control, shortest label) and, if the
        # top pick's click fails or the control is disabled, falls through
        # to the next-best candidate instead of giving up outright.
        labeled_matches, bare_fallback = [], None
        for sel in ("button[type=submit]", "input[type=submit]", "button:not([type=button])", "button"):
            try:
                for b in form.query_selector_all(sel):
                    if not b.is_visible():
                        continue
                    label = (b.inner_text() or "").strip().lower()
                    if (any(w in label for w in GATE_WORDS) and
                            not any(w in label for w in BACKWARD_WORDS)):
                        is_submit = (b.get_attribute("type") or "").lower() == "submit"
                        labeled_matches.append((0 if is_submit else 1, len(label), label, b))
                    elif bare_fallback is None:
                        bare_fallback = b
            except Exception:
                continue
        try:
            for b in self.page.query_selector_all("button, input[type=submit]"):
                if not b.is_visible():
                    continue
                label = (b.inner_text() or b.get_attribute("value") or "").strip().lower()
                if (any(w in label for w in GATE_WORDS) and
                        not any(w in label for w in BACKWARD_WORDS)):
                    is_submit = (b.get_attribute("type") or "").lower() == "submit"
                    labeled_matches.append((0 if is_submit else 1, len(label), label, b))
        except Exception:
            pass
        labeled_matches.sort(key=lambda x: (x[0], x[1]))
        for _, _, _, cand in labeled_matches:
            try:
                if cand.is_disabled():
                    continue
                cand.click(timeout=4000)
                self.page.wait_for_timeout(2500)
                return True
            except Exception:
                continue
        if bare_fallback is not None:
            try:
                bare_fallback.click(timeout=4000)
                self.page.wait_for_timeout(2500)
                return True
            except Exception:
                pass
        return False

    def _find_gate_form(self):
        try:
            forms = [f for f in self.page.query_selector_all("form") if f.is_visible()]
        except Exception:
            forms = []
        pw = [f for f in forms if f.query_selector("input[type=password]")]
        if pw:
            return pw[0]
        for f in forms:
            try:
                t = (f.inner_text() or "").lower()
            except Exception:
                t = ""
            if any(w in t for w in GATE_WORDS) or f.query_selector("input[type=email]"):
                return f
        # some onboarding wizards (this includes real apps, not an edge case)
        # use a plain <div> wrapper with inputs + a button instead of <form> -
        # fall back to "the body itself" when it has a visible text input and
        # a button whose label matches a gate word, so the multi-step wizard
        # isn't mistaken for "no gate left". But a real, large, already-
        # authenticated app (code-server's own VS Code UI, once logged in) is
        # near-certain to have SOME input and SOME button somewhere on the
        # page whose label happens to contain a generic word like "create" or
        # "next" - that's not a gate, it's coincidence at scale. Never treat
        # the whole body as a gate once the page already looks like the real
        # app (logout/settings/profile/welcome visible) - code-server's own
        # "Walkthrough: Essential Features" onboarding tab, which sits
        # directly inside the real, already-logged-in editor UI, is exactly
        # this: correctly reads as "in" on _looks_like_app(), and without
        # this check the div-fallback still won, forcing this same real
        # screen to be re-submitted as a fake gate step 7 times over.
        if self._looks_like_app():
            return None
        try:
            has_input = self.page.query_selector("input:not([type=hidden])") is not None
            for b in self.page.query_selector_all("button"):
                if not b.is_visible():
                    continue
                label = (b.inner_text() or "").lower()
                if has_input and any(w in label for w in GATE_WORDS):
                    return self.page.query_selector("body")
        except Exception:
            pass
        return None

    def _click_choice_step(self):
        """Some setup wizards aren't a <form> at all - a single step of
        exclusive choice cards ('Embedded MariaDB' / 'MySQL' / 'SQLite') that
        must be clicked before a 'Continue' button does anything. Finds a
        group of >=2 visible, similarly-sized sibling elements that look like
        selectable options (not inside a form, not a destructive action),
        clicks the first, then clicks a following continue/next/weiter
        button if one is visible. Returns True if it changed anything."""
        try:
            # Genuinely interactive elements only - a bare [class*=card]/
            # [class*=option] catch-all matches purely decorative content
            # too (DaisyUI/Tailwind style plain <div class="card ..."> is
            # an extremely common way to lay out a marketing page's feature
            # highlights, not a choice control). DocuSeal's own landing
            # page has exactly 4 such divs ("Easy to Start" / "Mobile
            # Optimized" / "Secure" / "Open Source") that this method
            # started wrongly treating as a 4-way choice group once the
            # first-line-label fix (needed for real multi-line choice
            # cards elsewhere) made their short headings pass the length
            # filter - clicking one is a real, successful click that goes
            # nowhere, which looked like "submitted: True" nine times over
            # and never got anywhere near the actual "Sign In" link.
            candidates = [el for el in self.page.query_selector_all(
                "button, [role=button], [role=radio], [role=option], a[href]")
                if el.is_visible()]
        except Exception:
            candidates = []
        groups = {}
        for el in candidates:
            try:
                tag = el.evaluate("e => e.tagName")
                if tag == "A":
                    # an <a href> can navigate straight off the app entirely
                    # (DocuSeal's own landing page has a "click" link to
                    # https://www.docuseal.com/install in its marketing
                    # copy) - only a same-origin link is safe to even
                    # consider as an in-app choice.
                    href = el.get_attribute("href") or ""
                    dest = urljoin(self.base + "/", href)
                    if urlparse(dest).netloc != urlparse(self.base).netloc:
                        continue
                # a bigger "choice CARD" (icon + heading + description, not
                # just a short button label) has its real, human-recognised
                # label on its FIRST line - Infisical's own post-setup
                # launch-pad ("Go to dashboard\nCreate projects, manage
                # secrets, and invite your team.") is exactly this shape,
                # and matching against the WHOLE multi-line block both blew
                # the 40-char cutoff (rejecting a real choice outright) and
                # would have let unrelated description prose falsely
                # trigger a destructive/backward-word match.
                full_text = (el.inner_text() or "").strip()
                label = full_text.split("\n", 1)[0].strip().lower()
                # "back"/"cancel"/etc are never a valid choice-card pick -
                # excluding them from the candidate pool entirely (not just
                # skipping them as the pick) stops an ordinary "Back /
                # <forward action>" button pair from ever being mistaken
                # for a multi-choice card group in the first place, e.g.
                # Infisical's own signup wizard puts "Back" right next to
                # "Create organization" as siblings.
                if (not label or len(label) > 40 or
                        any(d in label for d in ("delete", "logout", "remove")) or
                        any(d in label for d in BACKWARD_WORDS)):
                    continue
                box = el.bounding_box()
                if not box:
                    continue
                parent = el.evaluate_handle("e => e.parentElement")
                pid = parent.evaluate("e => e ? (e.getAttribute('class')||'') + e.tagName : ''") if parent else ""
                groups.setdefault(pid, []).append((label, el, tag))
            except Exception:
                continue
        group = next((g for g in groups.values() if len(g) >= 2), None)
        if not group:
            return False
        # within a genuine choice group, a member whose own label is a
        # forward/gate action (e.g. "Create organization") is the one to
        # click, not whichever happened to be first in DOM order.
        forward = [(label, el) for label, el, _ in group if any(w in label for w in GATE_WORDS)]
        signup_forward = [(label, el) for label, el in forward if any(w in label for w in SIGNUP_WORDS)]
        if signup_forward:
            pick = min(signup_forward, key=lambda x: len(x[0]))[1]
        elif forward:
            pick = min(forward, key=lambda x: len(x[0]))[1]
        elif any(tag == "A" for _, _, tag in group):
            # an arbitrary "just click the first one" guess is fine for a
            # real choice-card group (radio-style options, an icon toggle -
            # nothing in the group can navigate off the app on its own),
            # but a group of same-origin LINKS with no gate-word match at
            # all is far more likely an unrelated nav cluster (a footer's
            # row of links, e.g.) than a genuine choice - guessing wrong
            # there means leaving the app on a page that isn't even part of
            # the gate crawl's job to recover from.
            return False
        else:
            pick = group[0][1]
        try:
            pick.click(timeout=3000)
            self.page.wait_for_timeout(500)
        except Exception:
            return False
        for b in self.page.query_selector_all("button"):
            try:
                if not b.is_visible():
                    continue
                label = (b.inner_text() or "").strip().lower()
                if any(w in label for w in ("continue", "next", "weiter", "proceed", "confirm")):
                    b.click(timeout=3000)
                    self.page.wait_for_timeout(1500)
                    break
            except Exception:
                continue
        return True

    def _click_single_gate_link(self):
        """Some apps show a marketing/landing page with a single 'Sign In' /
        'Log In' / 'Get Started' link or button - not a <form> yet (that's
        one more click away) and not a multi-choice card group (only one
        option, so _click_choice_step's ">=2 siblings" rule correctly
        ignores it, and its selector doesn't even query <a> tags). This
        matters most on the SECOND stage of a real run: install_startup.py
        boots one container, screens.py's gate-crawl creates the account via
        the FIRST-TIME setup wizard, then capabilities.py opens a fresh
        browser context against that SAME still-running app - which, since
        the account already exists, shows exactly this 'please sign in'
        landing page instead of the setup wizard. Clicking through to reveal
        the real login form is required for capabilities.py to ever reach
        the authenticated app at all. Deliberately picks the single
        best-matching, most prominent (shortest label) candidate rather than
        the first DOM match, since nav bars often repeat the same CTA."""
        try:
            els = [el for el in self.page.query_selector_all("a[href], button, [role=button]")
                  if el.is_visible()]
        except Exception:
            els = []
        best, best_signup = None, None
        for el in els:
            try:
                # first line only - see _click_choice_step's identical
                # comment: a bigger card (icon + heading + description) has
                # its real label on the first line, and matching the whole
                # multi-line block both blows this cutoff and risks a
                # description sentence containing a stray destructive word.
                label = (el.inner_text() or "").strip().split("\n", 1)[0].strip().lower()
            except Exception:
                continue
            if not label or len(label) > 30:
                continue
            if any(d in label for d in ("delete", "logout", "log out", "sign out", "remove")):
                continue
            if any(w in label for w in GATE_WORDS):
                if best is None or len(label) < len(best[0]):
                    best = (label, el)
                # shiptrack's own landing page offers "Sign in" and "Sign
                # up" side by side - see SIGNUP_WORDS' definition for why a
                # signup-shaped match has to win the tie over a same-length
                # "Sign in": nothing to log into yet on a fresh instance.
                if any(w in label for w in SIGNUP_WORDS):
                    if best_signup is None or len(label) < len(best_signup[0]):
                        best_signup = (label, el)
        pick = best_signup or best
        if pick is None:
            return False
        try:
            pick[1].click(timeout=3000)
            self.page.wait_for_timeout(1500)
            return True
        except Exception:
            return False

    def _looks_like_app(self):
        try:
            t = (self.page.inner_text("body", timeout=3000) or "").lower()
        except Exception:
            return False
        return any(w in t for w in ("logout", "log out", "sign out", "settings", "profile", "welcome"))

    def get_past_setup_wall(self):
        """Fills whatever setup/signup/login form stands between the homepage
        and the real app - the same problem the old walker called
        get_in(). Returns a log of what it did; never claims success it
        didn't reach."""
        steps = []
        for i in range(MAX_GATE_STEPS):
            form = self._find_gate_form()
            if form is None and self._looks_like_app():
                break  # already past the gate - don't let choice-click fire on real UI
            if form is not None:
                before = self.page.url
                filled = self._fill_visible_inputs(form)
                submitted = self._submit(form)
                steps.append({"step": i + 1, "kind": "form", "url_before": before,
                             "fields_filled": filled, "submitted": submitted, "url_after": self.page.url})
                if not submitted:
                    break
                continue
            before = self.page.url
            if self._click_choice_step():
                steps.append({"step": i + 1, "kind": "choice_click", "url_before": before,
                             "url_after": self.page.url})
                continue
            if self._click_single_gate_link():
                steps.append({"step": i + 1, "kind": "single_gate_link", "url_before": before,
                             "url_after": self.page.url})
                continue
            break
        return steps

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

    def click_link_by_href(self, href, text):
        """Navigates by CLICKING the real link element currently in the DOM,
        not a fresh page.goto() to the same URL. This matters for apps whose
        session/auth lives in an active socket connection or in-memory JS
        state rather than a cookie: a full page reload to a deep route can
        lose that state and bounce back to a login/404 screen even though
        the user is, in every real sense, still logged in - a full reload is
        not what a real user does to navigate a live app. Returns True if a
        matching, visible link was found and clicked."""
        try:
            candidates = self.page.query_selector_all(f'a[href="{href}"]')
            el = next((c for c in candidates if c.is_visible()), None)
            if el is None and text:
                # href match failed (client router rewrote it) - fall back to
                # the same visible text, which is what a human actually reads.
                loc = self.page.get_by_text(text, exact=True)
                if loc.count():
                    for i in range(min(loc.count(), 5)):
                        cand = loc.nth(i)
                        if cand.is_visible():
                            el = cand
                            break
            if el is None:
                return False
            el.click(timeout=4000)
            self.page.wait_for_timeout(1200)
            return True
        except Exception:
            return False

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
        return self.inventory_current_screen(name_hint)

    def inventory_current_screen(self, name_hint):
        """Same checks as verify_screen, but on whatever page is already
        loaded - used after a click-based navigation, where a fresh goto()
        would itself be the thing that breaks an SPA's live session."""
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
        body_lower = body_text.lower()
        error_hit = next((m for m in ERROR_STATE_MARKERS if m in body_lower), None)
        controls = self.inventory_controls()
        controls_detected = any(v > 0 for v in controls.values())
        shot = self.shot(name_hint)
        return {
            "reachable": True, "rendered": rendered, "error_state": error_hit,
            "controls_detected": controls_detected,
            "browser_verified": rendered and not error_hit,
            "title": title, "heading": heading_text,
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

        # get past whatever setup/signup/login wizard stands in the way first -
        # otherwise every "screen" discovered is really just the same gate
        # (spec section 7's screens must be the app's real screens, not its
        # onboarding wall).
        if not w.goto(base_url):
            gate_steps = []
        else:
            gate_steps = w.get_past_setup_wall()

        screens = []
        seen_urls = set()

        # 1. wherever the gate left us is screen #1 (already navigated there
        #    as part of get_past_setup_wall - inventory it in place, no re-nav)
        app_home_url = w.page.url
        home_result = w.inventory_current_screen("home")
        # Honest gate outcome: IN means no gate form remains on the page - a
        # screen with a login/signup form still on it is STUCK, whatever its
        # HTTP status, and every screen "reached" from there is really just
        # more of the gate, not proof of the app's real screens. (Requiring
        # literal "logout"/"settings" text here too was a false negative on
        # real dashboards that put account actions behind a collapsed avatar
        # menu - Uptime Kuma's own dashboard has no such text visible until
        # that menu is opened, despite being the genuine, working app.)
        gate_state = "IN" if w._find_gate_form() is None else "STUCK"
        screens.append({"screen_id": "SCR-001", "name": "Home", "route": "/",
                        "discovery_source": "startup_url", "gate_steps": gate_steps,
                        "gate_state": gate_state, **home_result})
        seen_urls.add(base_url.rstrip("/"))
        seen_urls.add(app_home_url.rstrip("/"))

        # 2. live navigation: links actually present on the authenticated
        #    home screen, visited by CLICKING them (not a fresh goto() to the
        #    same URL) - many apps keep session/live state in memory or an
        #    open socket, not just a cookie, and a full page reload to a deep
        #    route can lose that and bounce back to a login/404 screen even
        #    though the user is still, in every real sense, logged in.
        #    If the gate is still STUCK, every route from here is just more
        #    of the same gate - crawling them would manufacture screen count
        #    without any real evidence, so this stops at the honest result.
        nav_links = w.collect_nav_links() if (home_result["reachable"] and gate_state == "IN") else []
        seen_hrefs = set()
        i = 2
        for l in nav_links:
            if i - 2 >= MAX_SCREENS_TO_VISIT:
                break
            full = urljoin(base_url + "/", l["href"])
            if urlparse(full).netloc != urlparse(base_url).netloc:
                continue
            key = full.rstrip("/")
            if key in seen_urls or l["href"] in seen_hrefs:
                continue
            seen_urls.add(key)
            seen_hrefs.add(l["href"])
            label = l["text"] or screen_name_from_url(full)
            if w.page.url.rstrip("/") != app_home_url.rstrip("/"):
                w.goto(app_home_url)  # app_home_url is proven reachable; deep routes are not
            if w.click_link_by_href(l["href"], l["text"]):
                result = w.inventory_current_screen(label)
            else:
                result = w.verify_screen(full, label)  # fall back to direct nav if the click failed
            screens.append({"screen_id": f"SCR-{i:03d}", "name": label[:60],
                            "route": urlparse(w.page.url).path or urlparse(full).path,
                            "discovery_source": "nav_link_click", **result})
            i += 1

        # 3. static route candidates found in source, not already covered by
        #    live navigation - visited by direct goto() since there's no DOM
        #    element to click for a route nothing on screen links to. These
        #    are honestly weaker evidence for exactly the reason #2 exists.
        #    Same STUCK-gate stop as above.
        for r in (static_routes if gate_state == "IN" else []):
            if i - 2 >= MAX_SCREENS_TO_VISIT:
                break
            full = urljoin(base_url + "/", r.lstrip("/"))
            if full.rstrip("/") in seen_urls:
                continue
            seen_urls.add(full.rstrip("/"))
            label = screen_name_from_url(full)
            result = w.verify_screen(full, label)
            screens.append({"screen_id": f"SCR-{i:03d}", "name": label[:60], "route": urlparse(full).path,
                            "discovery_source": "static_route", **result})
            i += 1

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
