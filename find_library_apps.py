#!/usr/bin/env python3
"""
find_library_apps.py — find the most robust, screen-serving, licensable open-source
app for every category in the benchmark list, without anyone opening them by hand.

What it does, per category:
  1. DISCOVER   — pull candidates from configured discovery sources (Awesome Selfhosted and/or Open Source Tools) (a real,
                  maintained dataset: licence, stars, last update, release, commits).
  2. PRE-FILTER — drop archived, stale, low-star and wrong-licence entries using the
                  directory's own data (cheap, no clone).
  3. CLONE      — shallow-clone each remaining repo and pin the commit hash.
  4. LICENCE    — read the repo's OWN licence file. Not in the allowed list = refused.
  5. SCREENS    — the app must serve its own screens (user-facing templates/pages and a
                  login). JSON-only or admin-only = refused.  ("A live app has screens.")
  6. RUNS       — the app must ship a container recipe (Dockerfile / compose) so the
                  walker can stand it up with one command. None = set aside.
  7. ROBUSTNESS — score from evidence: stars, commit cadence, release recency, tests,
                  CI. Ranks survivors. Never refuses.
  8. CAPABILITY — match the category's benchmark capabilities against the repo's own
                  routes, models, templates and file names. Coverage ranks survivors.
                  Never refuses. (The walker later proves each capability for real.)
  9. OUTPUT     — shortlist/<slug>.json (ranked survivors + every refusal with its
                  reason) and reports/LIBRARY_TABLE.md across all categories.

Usage:
  python3 find_library_apps.py                 # every category in the category file
  python3 find_library_apps.py crm dating      # only these slugs
  python3 find_library_apps.py --list          # show slugs and stop

No mocks. Every number comes from a real directory entry or a real clone.
"""

import os

# =============================================================================
#  RULES / CONFIG — edit here. One comment per setting says what changes if you do.
# =============================================================================

# --- Inputs ------------------------------------------------------------------
CATEGORY_FILE = "categories/benchmark70.json"

# Discovery sources. "awesome" preserves the original source; "open-source-tools"
# adds the live 52-category Open Source Tools catalogue as a candidate source.
# "all" combines both, deduplicating by repository URL.
DISCOVERY_SOURCE = os.environ.get("DISCOVERY_SOURCE", "all").strip().lower()
OPEN_SOURCE_TOOLS_CACHE_DIR = "open_source_tools"
OPEN_SOURCE_TOOLS_MAX_SOURCE_CATEGORIES = 3
OPEN_SOURCE_TOOLS_MAX_APPS_PER_CATEGORY = 30
#   The 70 categories with exemplar + capabilities + search mapping. Point this at a
#   different file (e.g. one built from CATEGORY_REGISTRY.json) to run on that list.

DIRECTORY_REPO = "https://github.com/awesome-selfhosted/awesome-selfhosted-data.git"
#   The machine-readable self-hosted directory. Change only if the dataset moves.

DIRECTORY_DIR = "/tmp/selfhosted_directory"
#   Where the directory dataset is cloned. It is refreshed on every run.

REFRESH_DIRECTORY = True
#   True = git pull the directory each run so stars/commits/releases are current.
#   False = reuse whatever is on disk (faster, may be stale).

# --- Outputs -----------------------------------------------------------------
SHORTLIST_DIR = "shortlist"
#   One JSON per category: ranked survivors and every refusal with a reason.

REPORT_DIR = "reports"
#   LIBRARY_TABLE.md (one row per category) and RUN_OUTPUT.txt (this run's log).

# --- Pre-filter from directory data (no clone needed) --------------------------
MIN_STARS = 200
#   Below this many GitHub stars the entry is not cloned. Lower = more candidates,
#   more clones, more weekend projects. Raise to keep only well-known projects.

MAX_MONTHS_SINCE_UPDATE = 12
#   Entries with no activity for longer than this are not cloned. Raise to admit
#   slower-moving projects.

REFUSE_ARCHIVED = True
#   Archived repositories are dead. False would let them through to the gates.

MAX_CLONES_PER_CATEGORY = 8
#   Only the top N pre-filtered entries (by stars) per category are cloned. Raise for
#   a wider net at the cost of clone time and disk.

# --- Licence gate (read from the repo's own file) ------------------------------
ALLOWED_LICENCES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC",
                    "MPL-2.0", "Unlicense", "0BSD", "Zlib", "CC0-1.0")
#   Verbatim list. A repo whose licence file is not one of these is refused.
#   MPL-2.0 is here pending Sam's decision — remove it to refuse MPL.

LICENCE_FILE_NAMES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENCE", "LICENCE.txt",
                      "LICENCE.md", "COPYING", "COPYING.txt", "LICENSE-MIT", "LICENSE.MIT",
                      "MIT-LICENSE", "MIT-LICENSE.txt", "LICENSE.rst", "UNLICENSE")
#   Names checked (case-insensitively) in the repo root. First match wins.

PREFILTER_ON_DIRECTORY_LICENCE = True
#   True = skip cloning entries whose directory-listed licence is not allowed (fast).
#   False = clone everything and let the repo's own licence file decide (slower, but
#   catches a directory mislabel).

NO_LICENCE_FILE_IS_REFUSAL = True
#   No licence file at all = refused. False would fall back to the directory's claim.

# --- Screens gate (the app must serve its own pages) ---------------------------
SCREEN_FILE_SUFFIXES = (".html", ".htm", ".html.erb", ".erb", ".haml", ".slim", ".ejs",
                        ".pug", ".jade", ".hbs", ".handlebars", ".njk", ".blade.php",
                        ".twig", ".tmpl", ".gohtml", ".jinja", ".jinja2", ".j2",
                        ".mustache", ".vue", ".svelte", ".jsx", ".tsx", ".astro",
                        ".razor", ".cshtml", ".heex", ".leex", ".eex", ".liquid")
#   File types that are screens (server templates or UI components). Add a suffix to
#   recognise another templating language.

SCREEN_EXCLUDE_PATH_PARTS = ("email", "emails", "mail", "mails", "mailer", "mailers",
                             "docs", "doc", "documentation", "test", "tests", "spec",
                             "specs", "__tests__", "fixtures", "node_modules", "vendor",
                             "vendors", "dist", "build", ".git", "example", "examples",
                             "storybook", "stories", "coverage", "site", "website",
                             "landing", "changelog", "third_party", "third-party",
                             "bower_components", "public/vendor", ".next", "e2e")
#   Any file with one of these as a path segment is NOT counted as a screen. Email
#   templates, docs sites and test fixtures are not app screens.

ADMIN_PATH_PARTS = ("admin", "admins", "backoffice", "back-office", "adminpanel")
#   Screens under these segments are counted separately. An app whose ONLY screens
#   are admin screens is refused (admin-only is not a live app).

MIN_SCREEN_FILES = 8
#   Fewer non-admin screen files than this = refused as not serving its own screens.
#   Lower to admit smaller apps; raise to demand richer UIs.

LOGIN_MARKERS = ("login", "log-in", "log_in", "signin", "sign-in", "sign_in",
                 "authenticate", "session/new", "sessions/new")
#   A screen file path or a source line containing one of these = the app has a
#   login. No login marker anywhere = refused (you can't walk an app you can't enter).

# --- Runs gate (the walker needs a one-command start) --------------------------
RUN_RECIPE_NAMES = ("dockerfile", "docker-compose.yml", "docker-compose.yaml",
                    "compose.yml", "compose.yaml", "docker-compose.prod.yml",
                    "docker-compose.production.yml", "docker-compose.dev.yml")
#   Any file with one of these names (case-insensitive) anywhere outside the excluded
#   dirs = the app can be stood up in a container. None = set aside as CAN'T STAND UP.

RUN_RECIPE_EXCLUDE_PATH_PARTS = ("docs", "doc", "documentation", "test", "tests",
                                 "node_modules", "vendor", "example", "examples")
#   Recipes under these segments do not count (a docs-site Dockerfile is not the app).

# --- Robustness score (ranks, never refuses) -----------------------------------
ROBUSTNESS_WEIGHTS = {
    "stars": 20,        # log-scaled GitHub stars, from the directory
    "commits_12m": 20,  # commits in the last 12 months, from the directory
    "release": 15,      # how recent the latest release is, from the directory
    "activity": 10,     # how recent the last activity is, from the directory
    "tests": 20,        # count of test files in the clone
    "ci": 10,           # a CI config is present in the clone
    "readme": 5,        # README length in the clone
}
#   Points available per component; total 100. Shift weight to what you value.

ROBUSTNESS_CAPS = {"stars": 20000, "commits_12m": 1500, "tests": 300, "readme_chars": 6000}
#   Value at which a component earns full marks. Above the cap earns no extra.

RELEASE_FULL_MARKS_MONTHS = 3
#   A release within this many months earns full release marks; marks fall to zero
#   at four times this figure.

TEST_PATH_PARTS = ("test", "tests", "spec", "specs", "__tests__", "e2e", "cypress")
TEST_FILE_PATTERNS = ("test_", "_test.", ".test.", ".spec.", "_spec.")
#   What counts as a test file: under a test directory, or a test-named file.

CI_PATHS = (".github/workflows", ".gitlab-ci.yml", ".circleci", "jenkinsfile",
            ".travis.yml", ".woodpecker.yml", ".woodpecker", "azure-pipelines.yml",
            ".drone.yml", "bitbucket-pipelines.yml", ".buildkite")
#   Presence of any of these = CI marks.

# --- Capability match (ranks, never refuses) -----------------------------------
CAPABILITY_STOPWORDS = {"and", "or", "the", "with", "of", "for", "to", "a", "an", "in",
                        "on", "by", "live", "tools", "management", "custom"}
#   Words inside a capability phrase that are too generic to search for.

CAPABILITY_MIN_TOKEN_LEN = 4
#   Shorter words are not searched (except entries in CAPABILITY_SHORT_OK).

CAPABILITY_SHORT_OK = {"sso", "mfa", "sla", "ocr", "pdf", "dms", "api", "apis", "cart",
                       "tags", "tax", "git", "ci", "gps", "map", "maps", "dm", "dms",
                       "bot", "bots", "ide", "fare", "fares", "poll", "chat", "feed",
                       "sync", "jobs", "job", "rsvp", "rsvps", "otp", "2fa", "qr"}
#   Short words that are still worth searching.

CAPABILITY_SOURCE_SUFFIXES = (".py", ".rb", ".php", ".js", ".ts", ".jsx", ".tsx", ".go",
                              ".java", ".kt", ".cs", ".rs", ".ex", ".exs", ".vue",
                              ".svelte", ".html", ".erb", ".ejs", ".pug", ".twig",
                              ".prisma", ".graphql", ".gql", ".sql", ".yml", ".yaml",
                              ".json", ".hbs", ".njk", ".blade.php", ".tmpl", ".gohtml")
#   File types whose names and contents form the corpus the capabilities are matched
#   against.

CAPABILITY_STRUCTURAL_PATH_MARKERS = ("route", "routes", "urls", "controller", "controllers",
                                      "handler", "handlers", "view", "views", "model", "models",
                                      "schema", "schemas", "migration", "migrations", "template",
                                      "templates", "component", "components", "page", "pages",
                                      "api", "service", "services", "resource", "resources",
                                      "entity", "entities", "domain", "feature", "features",
                                      "module", "modules", "app", "apps", "src")
#   Only files whose path contains one of these segments feed the capability corpus
#   (plus every file path). Restricting to structural files stops a huge codebase
#   matching every capability on stray words in build scripts and configs.

CAPABILITY_MAX_FILE_BYTES = 200_000
#   Files larger than this are skipped (minified bundles, lockfiles, data dumps).

CAPABILITY_EXCLUDE_PATH_PARTS = ("node_modules", "vendor", "vendors", "dist", "build",
                                 ".git", "bower_components", "third_party", "third-party",
                                 "locale", "locales", "i18n", "translations", "lang",
                                 "fixtures", "coverage", ".next")
#   Excluded from the corpus. Translation files would match every word in every
#   language; vendored code isn't the app.

MAX_SCAN_FILES = 20000
#   Hard stop on files walked per repo, to keep enormous monorepos bounded.

# --- Ranking -------------------------------------------------------------------
RANK_WEIGHT_CAPABILITY = 0.5
RANK_WEIGHT_ROBUSTNESS = 0.5
#   Final rank = capability coverage × first + robustness × second (both 0–100).
#   Tilt towards capability to favour feature-complete apps; towards robustness to
#   favour well-maintained ones.

RANK_BONUS_DESCRIPTION_MATCH = 10
#   Added to the rank when the project's own name/description matches one of the
#   category keywords (not just a shared directory tag). Set 0 to ignore.

# --- Category gate (is it the RIGHT KIND of app?) --------------------------------
CATEGORY_GATE_ON = True
#   True: an app must DECLARE itself as this kind of app (below) AND have every
#   anchor capability before it can survive. False: old behaviour (vocabulary
#   matching only) — that is how a workflow scheduler ended up as "event ticketing".

DECLARATION_SOURCES = ("description", "readme")
#   Where the app's self-declaration is read from: the directory's one-line
#   description of the project, and/or the head of the repo's own README.
#   Remove "readme" to trust the description alone (stricter, fewer survivors).

DECLARATION_README_CHARS = 4000
#   Only the first N characters of the README count (title, tagline, intro).
#   Larger = looser (a feature list deep in a README could match by accident).

DECLARATION_MIN_HITS = 1
#   How many distinct phrases from the category's `declares` list must appear.
#   Raise to 2 to demand the app describes itself in the category's own words twice.

DECLARATION_ACCEPT_EXEMPLAR = True
#   True: naming the benchmark app ("alternative to Eventbrite") counts as a
#   declaration. Exemplar names are already in each category's `declares` list.

PRODUCT_NAME_CONTEXT_WORDS = ("alternative", "alternatives", "replacement", "replace", "replaces", "clone",
                              "like", "similar", "instead of", "self-hosted", "selfhosted", "self hosted",
                              "open-source", "open source", "version of", "inspired by", "competitor", "rival",
                              "equivalent", "think of it as", "hackable")
PRODUCT_NAME_CONTEXT_CHARS = 80
#   A PRODUCT NAME in the `declares` list (Eventbrite, WhatsApp, Jira, YouTube…) only
#   counts as a declaration when one of these context words sits within N characters
#   of it — "an open-source alternative to Eventbrite" declares; "sends alerts to
#   WhatsApp" is an integration and does not. Plain phrases ("event ticketing") count
#   anywhere. Empty the word list to let bare product names count (looser).

PRODUCT_NAMES = ("tinder", "facebook", "tiktok", "instagram", "pixelfed", "youtube", "peertube", "spotify",
                 "whatsapp", "messenger", "slack", "zoom", "linkedin", "reddit", "twitter", "substack", "medium",
                 "google news", "gmail", "google calendar", "nextcloud", "seafile", "google drive", "notion",
                 "google docs", "airtable", "google sheets", "powerpoint", "impress", "microsoft 365", "jira",
                 "asana", "trello", "salesforce", "sap", "erpnext", "xero", "shopify", "uber eats", "uber",
                 "booking.com", "airbnb", "eventbrite", "moodle", "udemy", "zendesk", "intercom", "hubspot",
                 "mailchimp", "google analytics", "tableau", "typeform", "zapier", "n8n", "dropbox", "docusign",
                 "paperless", "1password", "bitwarden", "keycloak", "authentik", "okta", "gitea", "gitlab",
                 "github", "github actions", "code-server", "codespaces", "chatgpt", "copilot", "github copilot",
                 "midjourney", "stable diffusion", "google", "google maps", "openstreetmap", "strava", "paprika",
                 "ynab", "upwork", "realestate.com.au", "facebook marketplace", "meetup", "mastodon", "capcut",
                 "plex", "jellyfin", "linear", "adobe acrobat")
#   Phrases treated as product names for the rule above. Add to it if you put a new
#   product name in a category's `declares` list.

README_FILE_NAMES = ("README.md", "readme.md", "Readme.md", "README.MD", "README.rst",
                     "README", "README.txt", "readme.txt", "README.markdown", "readme.rst")
#   Names tried, in order, when reading a repo's README (case-sensitive on GitHub).

README_FETCH_TIMEOUT_SECONDS = 20
#   Per-request timeout when re-gating without a clone (README fetched by URL at
#   the recorded commit, so the evidence is pinned to what was actually inspected).

ANCHOR_COUNT = 3
#   The first N capabilities in a category row are its ANCHORS — the things the
#   app cannot be without (ticketing: Events, organisers, ticket types). All must
#   match or the app is refused. 0 disables anchor checking. The rest of the row
#   is the walker's job, where each capability is proven or recorded as a gap.

ANCHOR_REQUIRE_ALL_WORDS = True
#   True: every meaningful word of an anchor must appear in the structural code
#   ("ticket types" needs both ticket AND type). False: any one word is enough —
#   that is how "type" alone let a scheduler claim "ticket types".

# --- Clone mechanics -------------------------------------------------------------
CLONE_DIR = "/tmp/library_clones"
#   Where repos are cloned while being inspected.

KEEP_CLONES = False
#   False = each clone is deleted as soon as its gates and scores are recorded (the
#   commit hash and all evidence stay in the shortlist). True = keep clones on disk
#   for the walker — only safe when the disk can hold every repo at once.

CLONE_TIMEOUT_SECONDS = 600
#   A clone slower than this is abandoned and recorded as CLONE FAILED.

GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
#   Never prompt for credentials; never download LFS blobs.

VERBOSE = True
#   True prints every step. False prints only the per-category summary lines.

# =============================================================================
#  END OF CONFIG — logic below
# =============================================================================

import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required: pip install pyyaml --break-system-packages")

HERE = Path(__file__).resolve().parent
LOG_LINES = []
_REPO_CACHE = {}   # repo url -> gate results (licence/screens/runs/robustness/corpus)


# --------------------------------------------------------------------------- logging
def say(msg, always=False):
    LOG_LINES.append(msg)
    if VERBOSE or always:
        print(msg, flush=True)


# --------------------------------------------------------------------------- inputs
def load_categories():
    data = json.loads((HERE / CATEGORY_FILE).read_text())
    return data["categories"]


def refresh_directory():
    d = Path(DIRECTORY_DIR)
    if d.exists() and (d / "software").exists():
        if REFRESH_DIRECTORY:
            say("directory: refreshing")
            subprocess.run(["git", "-C", str(d), "pull", "-q", "--ff-only"],
                           timeout=300, env={**os.environ, **GIT_ENV})
    else:
        say("directory: cloning")
        if d.exists():
            shutil.rmtree(d)
        subprocess.run(["git", "clone", "--depth", "1", "-q", DIRECTORY_REPO, str(d)],
                       check=True, timeout=600, env={**os.environ, **GIT_ENV})
    entries = []
    for f in sorted((d / "software").glob("*.yml")):
        e = yaml.safe_load(f.read_text())
        if isinstance(e, dict) and e.get("source_code_url"):
            entries.append(e)
    head = subprocess.run(["git", "-C", str(d), "rev-parse", "--short=12", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    say(f"directory: {len(entries)} entries with a source URL, dataset commit {head}")
    return entries, head


# --------------------------------------------------------------------------- discover
def months_between(iso_date, today):
    try:
        d = datetime.strptime(str(iso_date)[:10], "%Y-%m-%d").date()
    except Exception:
        return None
    return (today.year - d.year) * 12 + (today.month - d.month)


def discover(cat, entries, today):
    """Return (kept, prefiltered) — kept are directory entries worth cloning."""
    tags = set(cat.get("directory_tags", []))
    kws = [k.lower() for k in cat.get("keywords", [])]
    matched = []
    for e in entries:
        hit_tag = bool(tags & set(e.get("tags", [])))
        text = f"{e.get('name', '')} {e.get('description', '')}".lower()
        hit_kw = any(re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", text) for k in kws)
        if hit_tag or hit_kw:
            matched.append((e, "tag+keyword" if (hit_tag and hit_kw) else ("tag" if hit_tag else "keyword")))
    kept, dropped = [], []
    for e, how in matched:
        name = e.get("name")
        reason = None
        source = e.get("discovery_source", "awesome-selfhosted")
        if REFUSE_ARCHIVED and e.get("archived"):
            reason = "archived"
        elif (e.get("stargazers_count") or 0) < MIN_STARS:
            reason = f"stars {e.get('stargazers_count')} < {MIN_STARS}"
        else:
            m = months_between(e.get("updated_at"), today)
            # Open Source Tools does not expose a reliable update timestamp in its
            # directory cards. Do not invent one and do not reject the candidate for
            # missing data; the real repository inspection remains authoritative.
            if source != "open-source-tools" and (m is None or m > MAX_MONTHS_SINCE_UPDATE):
                reason = f"last update {e.get('updated_at')} older than {MAX_MONTHS_SINCE_UPDATE} months"
            elif PREFILTER_ON_DIRECTORY_LICENCE and e.get("licenses") and not any(l in ALLOWED_LICENCES for l in e.get("licenses", [])):
                reason = f"directory lists licence {e.get('licenses')}"
        if reason:
            dropped.append({"name": name, "repo": e.get("source_code_url"), "stage": "pre-filter",
                            "reason": reason, "found_via": how})
        else:
            kept.append((e, how))
    kept.sort(key=lambda t: -(t[0].get("stargazers_count") or 0))
    cut = kept[MAX_CLONES_PER_CATEGORY:]
    for e, how in cut:
        dropped.append({"name": e.get("name"), "repo": e.get("source_code_url"), "stage": "pre-filter",
                        "reason": f"outside top {MAX_CLONES_PER_CATEGORY} by stars", "found_via": how})
    return kept[:MAX_CLONES_PER_CATEGORY], dropped


# --------------------------------------------------------------------------- clone
def clone_dir_for(url):
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", url.replace("https://", "").replace("http://", ""))
    return Path(CLONE_DIR) / tail


def clone(url):
    """Shallow clone at the default branch; return (root, commit) or (None, error)."""
    dest = clone_dir_for(url)
    env = {**os.environ, **GIT_ENV}
    if (dest / ".git").exists():
        h = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        if h:
            return dest, h
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(["git", "clone", "--depth", "1", "--single-branch", "-q", url, str(dest)],
                           capture_output=True, text=True, timeout=CLONE_TIMEOUT_SECONDS, env=env)
    except subprocess.TimeoutExpired:
        shutil.rmtree(dest, ignore_errors=True)
        return None, f"clone timed out after {CLONE_TIMEOUT_SECONDS}s"
    if r.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        return None, f"clone failed: {r.stderr.strip()[:200]}"
    h = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                       capture_output=True, text=True).stdout.strip()
    return dest, h


# --------------------------------------------------------------------------- walking
def _parts(p, root):
    return [x.lower() for x in p.relative_to(root).parts]


def walk_files(root):
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            n += 1
            if n > MAX_SCAN_FILES:
                return
            yield Path(dirpath) / fn


# --------------------------------------------------------------------------- licence
def read_licence(root):
    names = {n.lower(): n for n in LICENCE_FILE_NAMES}
    for p in sorted(root.iterdir()):
        if p.is_file() and p.name.lower() in names:
            head = p.read_text(errors="ignore")[:6000]
            return classify_licence(head), p.name
    return "", None


def classify_licence(head):
    h = head
    if "Commons Clause" in h:
        return "Commons-Clause"
    if "Business Source License" in h:
        return "BUSL-1.1"
    if "Elastic License" in h:
        return "Elastic-2.0"
    if "Server Side Public License" in h:
        return "SSPL"
    if "Open Software License" in h:
        return "OSL-3.0"
    if "PolyForm" in h:
        return "PolyForm"
    if "Creative Commons Attribution-NonCommercial" in h or "CC BY-NC" in h:
        return "CC-BY-NC"
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in h:
        return "AGPL-3.0"
    if "GNU LESSER GENERAL PUBLIC LICENSE" in h:
        return "LGPL"
    if "GNU GENERAL PUBLIC LICENSE" in h:
        return "GPL"
    if "European Union Public Licence" in h:
        return "EUPL-1.2"
    if "Apache License" in h and "Version 2.0" in h:
        return "Apache-2.0"
    if "Mozilla Public License" in h:
        return "MPL-2.0"
    if "This is free and unencumbered software released into the public domain" in h:
        return "Unlicense"
    if "CC0 1.0" in h or "Creative Commons Zero" in h:
        return "CC0-1.0"
    if "ISC License" in h or "Permission to use, copy, modify, and/or" in h:
        return "ISC"
    if "zlib License" in h.lower() or ("This software is provided 'as-is'" in h and "altered source" in h):
        return "Zlib"
    if "Neither the name of" in h and "Redistribution and use" in h:
        return "BSD-3-Clause"
    if "Redistribution and use in source and binary forms" in h:
        return "BSD-2-Clause"
    if "MIT License" in h or "Permission is hereby granted, free of charge" in h:
        return "MIT"
    return "UNRECOGNISED"


# --------------------------------------------------------------------------- screens
def _is_screen_file(p):
    name = p.name.lower()
    return any(name.endswith(s) for s in SCREEN_FILE_SUFFIXES)


def read_screens(root):
    """Count user-facing screen files and look for a login. Returns a dict of evidence."""
    total, admin, user = 0, 0, 0
    langs = set()
    login_hits = []
    user_examples = []
    for p in walk_files(root):
        parts = _parts(p, root)
        if any(x in SCREEN_EXCLUDE_PATH_PARTS for x in parts[:-1]):
            continue
        if _is_screen_file(p):
            total += 1
            langs.add(next(s for s in SCREEN_FILE_SUFFIXES if p.name.lower().endswith(s)))
            if any(x in ADMIN_PATH_PARTS for x in parts):
                admin += 1
            else:
                user += 1
                if len(user_examples) < 6:
                    user_examples.append("/".join(parts))
        rel = "/".join(parts)
        if any(m in rel for m in LOGIN_MARKERS) and len(login_hits) < 5:
            login_hits.append(rel)
    # A path-level login hit is decisive. Otherwise look inside route/source files.
    if not login_hits:
        for p in walk_files(root):
            parts = _parts(p, root)
            if any(x in SCREEN_EXCLUDE_PATH_PARTS for x in parts[:-1]):
                continue
            if not (_is_screen_file(p) or p.suffix.lower() in (".py", ".rb", ".php", ".js", ".ts", ".go", ".java", ".ex", ".rs", ".cs")):
                continue
            try:
                if p.stat().st_size > CAPABILITY_MAX_FILE_BYTES:
                    continue
                txt = p.read_text(errors="ignore").lower()
            except Exception:
                continue
            if any(m in txt for m in ("/login", "login\"", "login'", "sign in", "signin", "log in")):
                login_hits.append("/".join(parts) + " (in content)")
                break
    return {"screen_files_total": total, "screen_files_user": user, "screen_files_admin": admin,
            "screen_languages": sorted(langs), "user_screen_examples": user_examples,
            "login_evidence": login_hits}


# --------------------------------------------------------------------------- runs
def read_run_recipe(root):
    names = set(RUN_RECIPE_NAMES)
    found = []
    for p in walk_files(root):
        parts = _parts(p, root)
        if any(x in RUN_RECIPE_EXCLUDE_PATH_PARTS for x in parts[:-1]):
            continue
        if p.name.lower() in names or p.name.lower().startswith("dockerfile"):
            found.append("/".join(parts))
            if len(found) >= 6:
                break
    return found


# --------------------------------------------------------------------------- robustness
def read_repo_metrics(root):
    tests = 0
    ci = []
    readme_chars = 0
    ci_lower = tuple(c.lower() for c in CI_PATHS)
    for p in walk_files(root):
        parts = _parts(p, root)
        rel = "/".join(parts)
        if any(x in ("node_modules", "vendor", "dist", "build") for x in parts[:-1]):
            continue
        if any(x in TEST_PATH_PARTS for x in parts[:-1]) or any(t in p.name.lower() for t in TEST_FILE_PATTERNS):
            tests += 1
        if any(rel.startswith(c) for c in ci_lower) and len(ci) < 3:
            ci.append(rel)
        if len(parts) == 1 and parts[0].startswith("readme"):
            try:
                readme_chars = max(readme_chars, len(p.read_text(errors="ignore")))
            except Exception:
                pass
    return {"test_files": tests, "ci_evidence": ci, "readme_chars": readme_chars}


def robustness_score(entry, metrics, today):
    W, C = ROBUSTNESS_WEIGHTS, ROBUSTNESS_CAPS
    parts = {}
    stars = entry.get("stargazers_count") or 0
    parts["stars"] = W["stars"] * min(1.0, math.log1p(stars) / math.log1p(C["stars"]))
    commits = sum((entry.get("commit_history") or {}).values())
    parts["commits_12m"] = W["commits_12m"] * min(1.0, commits / C["commits_12m"])
    rel = (entry.get("current_release") or {}).get("published_at")
    m = months_between(rel, today) if rel else None
    if m is None:
        parts["release"] = 0.0
    else:
        parts["release"] = W["release"] * max(0.0, 1.0 - max(0, m - RELEASE_FULL_MARKS_MONTHS) / (3 * RELEASE_FULL_MARKS_MONTHS))
    ma = months_between(entry.get("updated_at"), today)
    parts["activity"] = W["activity"] * (max(0.0, 1.0 - (ma or 12) / MAX_MONTHS_SINCE_UPDATE))
    parts["tests"] = W["tests"] * min(1.0, metrics["test_files"] / C["tests"])
    parts["ci"] = W["ci"] * (1.0 if metrics["ci_evidence"] else 0.0)
    parts["readme"] = W["readme"] * min(1.0, metrics["readme_chars"] / C["readme_chars"])
    total = round(sum(parts.values()), 1)
    return total, {k: round(v, 1) for k, v in parts.items()}, {"stars": stars, "commits_12m": commits,
                                                               "latest_release": rel, "updated_at": entry.get("updated_at")}


# --------------------------------------------------------------------------- capability
def build_corpus(root):
    """Lower-cased text of source file paths and contents, for capability matching."""
    chunks = []
    for p in walk_files(root):
        parts = _parts(p, root)
        if any(x in CAPABILITY_EXCLUDE_PATH_PARTS for x in parts[:-1]):
            continue
        rel = "/".join(parts)
        chunks.append(rel)
        name = p.name.lower()
        if not any(name.endswith(s) for s in CAPABILITY_SOURCE_SUFFIXES):
            continue
        if not any(x in CAPABILITY_STRUCTURAL_PATH_MARKERS for x in parts[:-1]):
            continue
        try:
            if p.stat().st_size > CAPABILITY_MAX_FILE_BYTES:
                continue
            chunks.append(p.read_text(errors="ignore").lower())
        except Exception:
            continue
    return "\n".join(chunks)


def capability_tokens(cap):
    words = re.split(r"[^a-z0-9]+", cap.lower())
    toks = []
    for w in words:
        if not w or w in CAPABILITY_STOPWORDS:
            continue
        if len(w) < CAPABILITY_MIN_TOKEN_LEN and w not in CAPABILITY_SHORT_OK:
            continue
        toks.append(w)
        if len(w) > 4 and w.endswith("s"):
            toks.append(w[:-1])   # singular form
        if len(w) > 5 and w.endswith("ies"):
            toks.append(w[:-3] + "y")
    return sorted(set(toks))


def match_capabilities(caps, corpus):
    matched, missing, detail = [], [], {}
    for cap in caps:
        toks = capability_tokens(cap)
        hits = [t for t in toks if re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", corpus)]
        detail[cap] = hits
        (matched if hits else missing).append(cap)
    cov = round(100.0 * len(matched) / len(caps), 1) if caps else 0.0
    return cov, matched, missing, detail


# --------------------------------------------------------------------------- category gate
def _phrase_in(phrase, text):
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])", text) is not None


def _declares_with(phrase, text):
    """Plain phrase: present anywhere. Product name: present AND within
    PRODUCT_NAME_CONTEXT_CHARS of an 'alternative to'-style context word."""
    phrase = phrase.lower()
    pat = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
    if phrase not in PRODUCT_NAMES or not PRODUCT_NAME_CONTEXT_WORDS:
        return re.search(pat, text) is not None
    for m in re.finditer(pat, text):
        window = text[max(0, m.start() - PRODUCT_NAME_CONTEXT_CHARS): m.end() + PRODUCT_NAME_CONTEXT_CHARS]
        if any(w in window for w in PRODUCT_NAME_CONTEXT_WORDS):
            return True
    return False


def read_readme(root):
    """README head straight from the clone."""
    for n in README_FILE_NAMES:
        p = Path(root) / n
        if p.is_file():
            try:
                return p.read_text(errors="ignore")[:DECLARATION_README_CHARS], n
            except Exception:
                pass
    return "", None


def fetch_readme(repo_url, commit):
    """README head fetched by URL at the recorded commit — used by --regate when the
    clone is gone, so the evidence is pinned to the exact commit that was inspected."""
    import urllib.request
    m = re.match(r"https?://(github\.com|gitlab\.com|codeberg\.org)/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url or "")
    if not m or not commit:
        return "", None, "unsupported host or no recorded commit"
    host, owner, name = m.groups()
    last = "no README found under any known name"
    for n in README_FILE_NAMES:
        if host == "github.com":
            u = f"https://raw.githubusercontent.com/{owner}/{name}/{commit}/{n}"
        elif host == "gitlab.com":
            u = f"https://gitlab.com/{owner}/{name}/-/raw/{commit}/{n}"
        else:
            u = f"https://codeberg.org/{owner}/{name}/raw/commit/{commit}/{n}"
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "library-finder"})
            with urllib.request.urlopen(req, timeout=README_FETCH_TIMEOUT_SECONDS) as r:
                return r.read().decode("utf-8", "ignore")[:DECLARATION_README_CHARS], n, None
        except Exception as ex:
            last = f"{n}: {ex}"
    return "", None, last


def declaration_check(cat, description, readme):
    """Does the app say, in its own words, that it is this kind of app?"""
    phrases = [p.lower() for p in cat.get("declares", [])] or [k.lower() for k in cat.get("keywords", [])]
    if not DECLARATION_ACCEPT_EXEMPLAR:
        ex = [x.strip().lower() for x in cat["exemplar"].replace("/", ",").split(",")]
        phrases = [p for p in phrases if p not in ex]
    hits = {}
    if "description" in DECLARATION_SOURCES:
        t = (description or "").lower()
        hits["description"] = [p for p in phrases if _declares_with(p, t)]
    if "readme" in DECLARATION_SOURCES:
        t = (readme or "").lower()
        hits["readme"] = [p for p in phrases if _declares_with(p, t)]
    distinct = sorted({p for v in hits.values() for p in v})
    return len(distinct) >= DECLARATION_MIN_HITS, distinct, hits


def anchor_check(cat, detail):
    """detail: capability -> tokens that hit in the structural corpus."""
    anchors = cat["capabilities"][:ANCHOR_COUNT]
    failed = []
    for a in anchors:
        hits = set(detail.get(a, []))
        if ANCHOR_REQUIRE_ALL_WORDS:
            words = [w for w in re.split(r"[^a-z0-9]+", a.lower())
                     if w and w not in CAPABILITY_STOPWORDS
                     and (len(w) >= CAPABILITY_MIN_TOKEN_LEN or w in CAPABILITY_SHORT_OK)]
            ok = bool(words) and all(any(t in hits for t in capability_tokens(w)) for w in words)
        else:
            ok = bool(hits)
        if not ok:
            failed.append(a)
    return not failed, anchors, failed


def category_gate(cat, description, readme, detail):
    """Returns (passes, reason, evidence)."""
    if not CATEGORY_GATE_ON:
        return True, "", {"gate": "off"}
    dec_ok, distinct, hits = declaration_check(cat, description, readme)
    anc_ok, anchors, failed = anchor_check(cat, detail)
    ev = {"declared": dec_ok, "declaration_phrases_found": distinct, "declaration_hits": hits,
          "anchors": anchors, "anchors_missing": failed}
    if not dec_ok:
        return False, (f"does not declare itself as {cat['category'].lower()} — none of "
                       f"{cat.get('declares')} in its description or README head"), ev
    if not anc_ok:
        return False, f"declares itself but is missing anchor capabilities {failed}", ev
    return True, "", ev


def _discard_clone(root):
    if not KEEP_CLONES and root and Path(root).exists():
        shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- per repo
def inspect_repo(entry, today):
    url = entry["source_code_url"]
    if url in _REPO_CACHE:
        return _REPO_CACHE[url]
    res = {"name": entry.get("name"), "repo": url, "directory_licence": entry.get("licenses"),
           "directory_platforms": entry.get("platforms"), "website": entry.get("website_url")}
    root, commit = clone(url)
    if root is None:
        res.update({"gate": "clone", "verdict": "REFUSED", "reason": commit})
        _REPO_CACHE[url] = res
        _discard_clone(root)
        return res
    res["commit"] = commit
    res["clone_path"] = str(root) if KEEP_CLONES else "(deleted after inspection)"

    lic, lic_file = read_licence(root)
    res["licence"] = lic
    res["licence_file"] = lic_file
    if not lic_file:
        if NO_LICENCE_FILE_IS_REFUSAL:
            res.update({"gate": "licence", "verdict": "REFUSED", "reason": "no licence file in repo root"})
            _REPO_CACHE[url] = res
            return res
    elif lic not in ALLOWED_LICENCES:
        res.update({"gate": "licence", "verdict": "REFUSED", "reason": f"licence file says {lic}"})
        _REPO_CACHE[url] = res
        _discard_clone(root)
        return res

    sc = read_screens(root)
    res["screens"] = sc
    if sc["screen_files_user"] < MIN_SCREEN_FILES:
        res.update({"gate": "screens", "verdict": "REFUSED",
                    "reason": f"{sc['screen_files_user']} user-facing screen files (< {MIN_SCREEN_FILES}); "
                              f"{sc['screen_files_admin']} admin-only — not a live app with screens"})
        _REPO_CACHE[url] = res
        _discard_clone(root)
        return res
    if not sc["login_evidence"]:
        res.update({"gate": "screens", "verdict": "REFUSED", "reason": "no login found in paths or source"})
        _REPO_CACHE[url] = res
        _discard_clone(root)
        return res

    recipes = read_run_recipe(root)
    res["run_recipes"] = recipes
    if not recipes:
        res.update({"gate": "runs", "verdict": "SET ASIDE", "reason": "no Dockerfile or compose file — walker cannot stand it up"})
        _REPO_CACHE[url] = res
        _discard_clone(root)
        return res

    metrics = read_repo_metrics(root)
    total, parts, facts = robustness_score(entry, metrics, today)
    res["robustness"] = {"score": total, "parts": parts, "facts": facts, "repo_metrics": metrics}
    res["corpus"] = build_corpus(root)
    res["readme_head"], res["readme_file"] = read_readme(root)
    res["description"] = entry.get("description")
    res["verdict"] = "SURVIVES"
    _REPO_CACHE[url] = res
    _discard_clone(root)
    return res


# --------------------------------------------------------------------------- per category
def run_category(cat, entries, today, dataset_commit):
    slug = cat["slug"]
    say(f"\n=== {slug}  ({cat['category']} — exemplar {cat['exemplar']}) ===", always=True)
    kept, dropped = discover(cat, entries, today)
    say(f"  discovered {len(kept) + len(dropped)} directory entries, {len(kept)} pass pre-filter")
    survivors, refused = [], list(dropped)
    for e, how in kept:
        say(f"  -> {e.get('name')}  {e.get('source_code_url')}  stars={e.get('stargazers_count')}")
        r = inspect_repo(e, today)
        if r["verdict"] != "SURVIVES":
            say(f"     {r['verdict']} at {r['gate']}: {r['reason']}")
            refused.append({"name": r["name"], "repo": r["repo"], "commit": r.get("commit"), "stage": r["gate"],
                            "reason": r["reason"], "licence": r.get("licence"), "found_via": how,
                            "screens": r.get("screens")})
            continue
        cov, matched, missing, detail = match_capabilities(cat["capabilities"], r["corpus"])
        ok, why, gate_ev = category_gate(cat, r.get("description"), r.get("readme_head"), detail)
        if not ok:
            say(f"     REFUSED at category: {why}")
            refused.append({"name": r["name"], "repo": r["repo"], "commit": r.get("commit"), "stage": "category",
                            "reason": why, "licence": r.get("licence"), "found_via": how,
                            "category_gate": gate_ev, "capability_coverage_pct": cov})
            continue
        rank = round(RANK_WEIGHT_CAPABILITY * cov + RANK_WEIGHT_ROBUSTNESS * r["robustness"]["score"]
                     + (RANK_BONUS_DESCRIPTION_MATCH if "keyword" in how else 0), 1)
        say(f"     SURVIVES  licence={r['licence']} screens={r['screens']['screen_files_user']} "
            f"robustness={r['robustness']['score']} capability={cov}% rank={rank}")
        survivors.append({"name": r["name"], "repo": r["repo"], "commit": r["commit"], "website": r.get("website"),
                          "licence": r["licence"], "licence_file": r["licence_file"],
                          "screens": r["screens"], "run_recipes": r["run_recipes"],
                          "robustness": r["robustness"],
                          "capability": {"coverage_pct": cov, "matched": matched, "missing": missing,
                                         "evidence_tokens": detail},
                          "category_gate": gate_ev, "description": r.get("description"),
                          "readme_file": r.get("readme_file"),
                          "rank_score": rank, "found_via": how, "clone_path": r["clone_path"]})
    survivors.sort(key=lambda s: -s["rank_score"])
    out = {"category": cat["category"], "slug": slug, "exemplar": cat["exemplar"],
           "capabilities": cat["capabilities"], "checked_at": today.isoformat(),
           "directory_dataset_commit": dataset_commit,
           "gates": {"licence": list(ALLOWED_LICENCES), "min_screen_files": MIN_SCREEN_FILES,
                     "min_stars": MIN_STARS, "max_months_since_update": MAX_MONTHS_SINCE_UPDATE,
                     "category_gate": CATEGORY_GATE_ON, "declares": cat.get("declares"),
                     "anchor_count": ANCHOR_COUNT},
           "none_admitted": not survivors, "survivors": survivors, "refused": refused}
    d = HERE / SHORTLIST_DIR
    d.mkdir(exist_ok=True)
    (d / f"{slug}.json").write_text(json.dumps(out, indent=1))
    if survivors:
        top = survivors[0]
        say(f"  RESULT {slug}: {len(survivors)} survive — top {top['name']} ({top['licence']}, rank {top['rank_score']})", always=True)
    else:
        say(f"  RESULT {slug}: NONE ADMITTED ({len(refused)} refused)", always=True)
    return out


# --------------------------------------------------------------------------- report
def write_table(results, today, dataset_commit):
    d = HERE / REPORT_DIR
    d.mkdir(exist_ok=True)
    lines = [f"# Library table — {today.isoformat()} — directory dataset {dataset_commit}", "",
             "| # | Category | Exemplar | Top survivor | Declares itself via | Licence | Screens | Runs | Robustness | Capability | Survivors | Refused |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        if r["survivors"]:
            t = r["survivors"][0]
            dec = ", ".join((t.get("category_gate") or {}).get("declaration_phrases_found", [])) or "(gate not run)"
            lines.append(f"| {i} | {r['category']} | {r['exemplar']} | [{t['name']}]({t['repo']}) @ {t['commit'][:12]} | "
                         f"{dec} | {t['licence']} | {t['screens']['screen_files_user']} | {len(t['run_recipes'])} | "
                         f"{t['robustness']['score']} | {t['capability']['coverage_pct']}% | {len(r['survivors'])} | {len(r['refused'])} |")
        else:
            lines.append(f"| {i} | {r['category']} | {r['exemplar']} | **NONE ADMITTED** | — | — | — | — | — | — | 0 | {len(r['refused'])} |")
    (d / "LIBRARY_TABLE.md").write_text("\n".join(lines) + "\n")
    (d / "RUN_OUTPUT.txt").write_text("\n".join(LOG_LINES) + "\n")


# --------------------------------------------------------------------------- regate
def regate(cats, entries, today):
    """Apply the category gate to shortlists already on disk — no re-cloning.
    Description comes from the directory; README head is fetched at the recorded commit;
    anchor evidence is the per-capability token evidence saved at inspection time."""
    desc_by_repo = {e.get("source_code_url"): e.get("description") for e in entries}
    d = HERE / SHORTLIST_DIR
    results, struck_total = [], 0
    for cat in cats:
        f = d / f"{cat['slug']}.json"
        if not f.exists():
            continue
        out = json.loads(f.read_text())
        say(f"\n=== regate {cat['slug']}  ({cat['category']} — exemplar {cat['exemplar']}) ===", always=True)
        keep, struck = [], []
        for s in out["survivors"]:
            desc = s.get("description") or desc_by_repo.get(s["repo"])
            readme, rfile, err = fetch_readme(s["repo"], s.get("commit"))
            if err and VERBOSE:
                say(f"     (README not fetched for {s['name']}: {err})")
            ok, why, ev = category_gate(cat, desc, readme, s["capability"].get("evidence_tokens", {}))
            s["description"], s["readme_file"], s["category_gate"] = desc, rfile, ev
            if ok:
                say(f"  KEEP   {s['name']:<22} rank={s['rank_score']}  declares via {ev['declaration_phrases_found']}")
                keep.append(s)
            else:
                say(f"  STRIKE {s['name']:<22} rank={s['rank_score']}  {why}", always=True)
                struck.append({"name": s["name"], "repo": s["repo"], "commit": s.get("commit"), "stage": "category",
                               "reason": why, "licence": s.get("licence"), "found_via": s.get("found_via"),
                               "category_gate": ev, "capability_coverage_pct": s["capability"]["coverage_pct"],
                               "rank_before_category_gate": s["rank_score"]})
        keep.sort(key=lambda s: -s["rank_score"])
        out["survivors"] = keep
        out["refused"] = [r for r in out["refused"] if r.get("stage") != "category"] + struck
        out["none_admitted"] = not keep
        out["gates"].update({"category_gate": CATEGORY_GATE_ON, "declares": cat.get("declares"),
                             "anchor_count": ANCHOR_COUNT})
        out["regated_at"] = today.isoformat()
        f.write_text(json.dumps(out, indent=1))
        struck_total += len(struck)
        if keep:
            say(f"  RESULT {cat['slug']}: {len(keep)} survive, {len(struck)} struck — top {keep[0]['name']} "
                f"(rank {keep[0]['rank_score']})", always=True)
        else:
            say(f"  RESULT {cat['slug']}: NONE ADMITTED ({len(struck)} struck by category gate)", always=True)
        results.append(out)
    return results, struck_total


# --------------------------------------------------------------------------- main
def main(argv):
    global DISCOVERY_SOURCE
    if "--source" in argv:
        i = argv.index("--source")
        if i + 1 >= len(argv):
            sys.exit("--source requires awesome, open-source-tools, or all")
        DISCOVERY_SOURCE = argv[i + 1].strip().lower()
        argv = argv[:i] + argv[i + 2:]
    if DISCOVERY_SOURCE not in {"awesome", "open-source-tools", "all"}:
        sys.exit(f"invalid discovery source: {DISCOVERY_SOURCE!r}; use awesome, open-source-tools, or all")
    cats = load_categories()
    if "--list" in argv:
        for c in cats:
            print(f"{c['id']:>2}  {c['slug']:<28} {c['exemplar']}")
        return 0
    if "--help" in argv or "-h" in argv:
        print("usage: find_library_apps.py [slug ...]        run the finder for all/some categories\n"
              "       find_library_apps.py --regate [slug...] apply the category gate to shortlists already on disk\n"
              "       find_library_apps.py --list             list category slugs\n"
              "       find_library_apps.py --source {awesome|open-source-tools|all} [slug...]  override discovery source")
        return 0
    slugs = [a for a in argv if not a.startswith("--")]
    if slugs:
        unknown = [s for s in slugs if s not in {c["slug"] for c in cats}]
        if unknown:
            sys.exit(f"unknown slug(s): {unknown}")
        cats = [c for c in cats if c["slug"] in slugs]
    today = date.today()
    entries = []
    dataset_commits = []
    if DISCOVERY_SOURCE in ("awesome", "all"):
        awesome_entries, dataset_commit = refresh_directory()
        for e in awesome_entries:
            e.setdefault("discovery_source", "awesome-selfhosted")
        entries.extend(awesome_entries)
        dataset_commits.append(f"awesome-selfhosted:{dataset_commit}")
    if DISCOVERY_SOURCE in ("open-source-tools", "all"):
        from open_source_tools_source import discover_for_category
        say("Open Source Tools: live 52-category discovery enabled", always=True)
    dataset_commit = " + ".join(dataset_commits) if dataset_commits else "none"
    if "--regate" in argv:
        results, struck = regate(cats, entries, today)
        write_table(results, today, dataset_commit)
        admitted = sum(1 for r in results if r["survivors"])
        say(f"\nREGATE DONE: {struck} apps struck by the category gate; "
            f"{admitted}/{len(results)} categories still have a survivor. Table: {REPORT_DIR}/LIBRARY_TABLE.md", always=True)
        return 0
    Path(CLONE_DIR).mkdir(parents=True, exist_ok=True)
    results = []
    for c in cats:
        category_entries = list(entries)
        if DISCOVERY_SOURCE in ("open-source-tools", "all"):
            from open_source_tools_source import discover_for_category
            ost_entries = discover_for_category(
                c, Path(OPEN_SOURCE_TOOLS_CACHE_DIR),
                max_source_categories=OPEN_SOURCE_TOOLS_MAX_SOURCE_CATEGORIES,
                max_apps_per_source_category=OPEN_SOURCE_TOOLS_MAX_APPS_PER_CATEGORY,
            )
            if DISCOVERY_SOURCE == "open-source-tools":
                category_entries = ost_entries
            else:
                # Deduplicate across discovery sources; preserve both source records
                # when they point at different repositories.
                seen = {e.get("source_code_url") for e in category_entries}
                category_entries.extend(e for e in ost_entries if e.get("source_code_url") not in seen)
            say(f"  Open Source Tools supplied {len(ost_entries)} candidate(s) for {c['slug']}")
        results.append(run_category(c, category_entries, today, dataset_commit))
    write_table(results, today, dataset_commit)
    admitted = sum(1 for r in results if r["survivors"])
    say(f"\nDONE: {admitted}/{len(results)} categories have at least one survivor. "
        f"Table: {REPORT_DIR}/LIBRARY_TABLE.md", always=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
