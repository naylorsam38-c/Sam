#!/usr/bin/env python3
"""
walk_library_apps.py — THE WALKER.

Takes the survivors the finder left in shortlist/<slug>.json and PROVES them:
  1. re-clones the repo at the exact commit the finder inspected
  2. stands it up from its own container recipe (compose file or Dockerfile)
  3. opens it in a real headless Chromium
  4. gets through whatever is in the way (setup wizard / register / login)
  5. walks the category's capability list, screenshotting as it goes
  6. writes walks/<slug>/<app>/WALKTHROUGH.md + result.json + screenshots/
  7. tears everything down and moves on

Verdict per capability (honest labels — read them as written):
  REACHED  a link/menu matching the capability was clicked and the page it led to
           is about that capability (title/heading/URL match). Screenshot kept.
  SEEN     the capability's words appear on a page the walker visited, but no
           dedicated screen for it was reached.
  ABSENT   no trace of it anywhere the walker went.
None of these is "the feature works end to end" — that is the next level up.
What the walker DOES prove: the app boots from its own recipe, serves screens,
lets a user in, and which capabilities have a screen you can get to.

Usage:
  python3 walk_library_apps.py               walk every category with a survivor
  python3 walk_library_apps.py crm blogging   walk only these slugs
  python3 walk_library_apps.py --list         list categories with survivors
"""

# =============================================================================
#  CONFIG — edit these; one comment each says what it does and what changes
# =============================================================================

CATEGORY_FILE = "categories/benchmark70.json"
#   The 70 categories with their capability lists — same file the finder uses.

SHORTLIST_DIR = "shortlist"
#   Where the finder's per-category shortlists live. Read only.

WALK_DIR = "walks"
#   Output root. One folder per category, one per app walked, inside.

REPORT_DIR = "reports"
#   WALK_TABLE.md (one row per category) and WALK_OUTPUT.txt (the run log) go here.

CANDIDATES_PER_CATEGORY = 2
#   Top-ranked survivor is walked first. If it fails to BOOT, the next-ranked one
#   is tried, up to this many. A booted app is never replaced — its gaps are the
#   result. Raise for more fallbacks, at the cost of more clone/boot time.

SKIP_ALREADY_WALKED = True
#   True: an app that already BOOTED (result.json on disk) is not walked again, so
#   a killed run can be restarted and carry on; BOOT FAILED apps are always retried.
#   False: walk everything again.

# --- Containers -------------------------------------------------------------------
CONTAINER_TOOL = "auto"
COMPOSE_TOOL = "auto"
#   The commands used. Docker users: "docker" and "docker compose" (as a list below).
COMPOSE_TOOL_ARGV = ["podman-compose"]
#   Exact argv prefix for compose. For docker: ["docker", "compose"].

CA_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"
#   Host CA bundle mounted into image BUILDS so https downloads inside the build
#   trust this network's egress proxy. Runtime containers get it from
#   /etc/containers/containers.conf. Set "" if your network needs no such thing.

COMPOSE_FILE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
                      "docker-compose.prod.yml", "docker-compose.production.yml")
#   Compose file names looked for, in order of preference.

COMPOSE_SEARCH_DIRS = (".", "docker", "deploy", "deployment", "docker-compose", "compose",
                       "examples", "example", "install", "contrib/docker", "scripts")
#   Directories (relative to repo root) searched for a compose file, in order.

DOCKERFILE_NAMES = ("Dockerfile", "Dockerfile.production", "Dockerfile.prod", "Dockerfile.release",
                    "docker/Dockerfile", "Containerfile")
#   Dockerfiles tried (repo-root first) when no compose file boots. Built with the
#   repo root as context and run with all exposed ports published.

COMPOSE_SKIP_NAME_PARTS = ("test", "dev", "development", "ci", "e2e", "override", "debug")
#   Compose files whose name contains one of these are skipped (test/dev rigs).

PREFER_PREBUILT_IMAGES = True
#   True: a compose file that only pulls images beats one that builds from source
#   (faster, fewer ways to fail). False: first file found wins.

ALLOW_IMAGE_BUILD = True
#   False: any recipe that has to build an image is recorded as BOOT FAILED
#   ("build required") instead of attempting it.

COPY_ENV_EXAMPLE = True
#   Many compose files read a .env. If .env is missing and .env.example (or
#   .env.sample / example.env) exists next to it, copy it. Mechanical, recorded.

BOOT_TIMEOUT_SECONDS = 900
#   How long to wait for the app to answer HTTP after `up`. Big apps (Rocket.Chat,
#   Superset) can take several minutes on first boot.

PORT_POLL_SECONDS = 6
#   Interval between readiness polls.

IGNORE_CONTAINER_PORTS = (5432, 3306, 27017, 6379, 9200, 5672, 25, 465, 587, 993, 995, 143, 110,
                          1883, 8883, 2181, 9092, 4222, 11211, 9000, 9001)
#   Database / broker / mail ports that are never the web UI. 9000/9001 are MinIO.

HTML_PROBE_PATHS = ("/", "/login", "/index.html", "/admin", "/app", "/ui", "/web")
#   Paths tried when hunting for the page that serves the UI.

REMOVE_IMAGES_AFTER = True
#   True: `podman image prune` + remove this app's images after the walk, so disk
#   does not fill up across 24+ apps. False: keep images (faster re-walks).

CLONE_DIR = "/tmp/walk_clones"
CLONE_TIMEOUT_SECONDS = 900

# --- Browser --------------------------------------------------------------------
VIEWPORT = {"width": 1366, "height": 900}
PAGE_TIMEOUT_MS = 30000
#   Navigation/timeout per page action.

TEST_USER = {"name": "Library Walker", "username": "libwalker", "email": "libwalker@example.com",
             "password": "Walker-Pass-2026!", "site": "Library Walk", "url_field": "http://localhost"}
#   The account the walker tries to create / log in with. Some apps ship default
#   admin credentials in their compose files; those are tried too (below).

DEFAULT_CREDENTIALS = (("admin", "admin"), ("admin", "password"), ("admin@example.com", "admin"),
                       ("admin@example.com", "password"), ("admin", "admin123"), ("admin", "changeme"))
#   Tried at a login form when registration is not offered.

MAX_GATE_STEPS = 6
#   How many setup/register/login forms the walker will fill in a row before it
#   declares itself STUCK. Each step is screenshotted.

LINKS_PER_CAPABILITY = 2
#   How many matching links are clicked per capability (first wins if it REACHES).

MAX_LINKS_COLLECTED = 400
#   Cap on links/buttons harvested from a page.

SCREENSHOT_FULL_PAGE = False
#   True: whole scrolled page; False: viewport only (smaller files).

# --- Vocabulary (shared with the finder) ---------------------------------------
STOPWORDS = {"and", "or", "the", "with", "of", "for", "to", "a", "an", "in", "on", "by", "via", "per",
             "management", "manage", "managed", "support", "supported", "custom", "basic", "advanced"}
MIN_TOKEN_LEN = 4
SHORT_OK = {"sso", "mfa", "sla", "ocr", "pdf", "dms", "api", "apis", "cart", "tags", "tag", "chat", "dms",
            "crm", "erp", "seo", "csv", "rss", "git", "ci", "cd", "ide", "llm", "map", "maps", "ads", "kyc"}

GATE_WORDS = ("sign up", "signup", "register", "create account", "create an account", "get started",
              "setup", "set up", "install", "create admin", "create your account", "continue", "next",
              "finish", "log in", "login", "sign in")
#   Words that identify a form standing between the walker and the app.

VERBOSE = True

# =============================================================================
#  END OF CONFIG — logic below
# =============================================================================

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml is required")
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("playwright is required: pip install playwright && playwright install chromium")

HERE = Path(__file__).resolve().parent
LOG = []
USING_PODMAN = True

def configure_container_tools():
    global CONTAINER_TOOL, COMPOSE_TOOL, COMPOSE_TOOL_ARGV, USING_PODMAN
    override = os.environ.get("CONTAINER_TOOL_OVERRIDE")
    compose_override = os.environ.get("COMPOSE_TOOL_OVERRIDE")
    if override:
        CONTAINER_TOOL = override
    elif shutil.which("podman"):
        CONTAINER_TOOL = "podman"
    elif shutil.which("docker"):
        CONTAINER_TOOL = "docker"
    else:
        sys.exit("No supported container engine found: install Podman or Docker.")
    USING_PODMAN = CONTAINER_TOOL == "podman"
    if compose_override:
        COMPOSE_TOOL_ARGV = compose_override.split()
    elif USING_PODMAN and shutil.which("podman-compose"):
        COMPOSE_TOOL_ARGV = ["podman-compose"]
    elif not USING_PODMAN and shutil.which("docker"):
        COMPOSE_TOOL_ARGV = ["docker", "compose"] if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0 else ["docker-compose"]
    elif shutil.which("docker-compose"):
        COMPOSE_TOOL_ARGV = ["docker-compose"]
    else:
        sys.exit("Container engine found, but no usable compose command is installed.")
    say(f"Container engine: {CONTAINER_TOOL}; compose: {' '.join(COMPOSE_TOOL_ARGV)}", always=True)


def say(msg, always=False):
    LOG.append(msg)
    if VERBOSE or always:
        print(msg, flush=True)


def run(argv, cwd=None, timeout=None, env=None):
    """Run a command, capture everything, never raise."""
    try:
        p = subprocess.run(argv, cwd=cwd, timeout=timeout, capture_output=True, text=True,
                           env={**os.environ, **(env or {})})
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", str(e)


def best_error_line(text, max_len=300):
    """The most informative line of a failed command's stderr. buildx/compose often end
    with a generic '<cmd> --help' hint; prefer the actual ERROR:/error: line above it."""
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return ""
    for l in reversed(lines):
        if re.search(r"\berror\b", l, re.I) and "--help" not in l:
            return l.strip()[:max_len]
    return lines[-1].strip()[:max_len]


# --------------------------------------------------------------------------- clone at commit
def clone_at(repo, commit):
    d = Path(CLONE_DIR) / re.sub(r"[^a-zA-Z0-9]+", "_", repo)[-80:]
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    steps = [["git", "init", "-q"], ["git", "remote", "add", "origin", repo],
             ["git", "fetch", "-q", "--depth", "1", "origin", commit],
             ["git", "checkout", "-q", "FETCH_HEAD"]]
    for s in steps:
        rc, out, err = run(s, cwd=d, timeout=CLONE_TIMEOUT_SECONDS,
                           env={"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"})
        if rc != 0:
            return None, f"{' '.join(s[:2])} failed: {err.strip()[:300]}"
    return d, None


# --------------------------------------------------------------------------- recipe
def _resolve_ci(root, rel):
    """Resolve a recorded (lower-cased) relative path against the clone, case-insensitively."""
    cur = root
    for part in Path(rel).parts:
        match = next((c for c in cur.iterdir() if c.name.lower() == part.lower()), None) if cur.is_dir() else None
        if match is None:
            return None
        cur = match
    return cur


def find_recipes(root, recorded=()):
    """All candidate compose files, best first, plus Dockerfile fallbacks.
    `recorded` = the run_recipes paths the finder saw at this commit."""
    found = []
    for sd in COMPOSE_SEARCH_DIRS:
        base = root / sd
        if not base.is_dir():
            continue
        for n in COMPOSE_FILE_NAMES:
            f = base / n
            if f.is_file() and not any(k in f.name.lower() for k in COMPOSE_SKIP_NAME_PARTS):
                found.append(f)
    for rel in recorded:
        f = _resolve_ci(root, rel)
        if f and f.is_file() and "compose" in f.name.lower() and f not in found \
                and not any(k in str(f.relative_to(root)).lower() for k in COMPOSE_SKIP_NAME_PARTS):
            found.append(f)
    dockerfiles = []
    for n in DOCKERFILE_NAMES:
        f = _resolve_ci(root, n)
        if f and f.is_file():
            dockerfiles.append(f)
    recipes = []
    for f in found:
        try:
            doc = yaml.safe_load(f.read_text(errors="ignore")) or {}
        except Exception as e:
            continue
        services = doc.get("services") or {}
        if not isinstance(services, dict) or not services:
            continue
        builds = [n for n, s in services.items() if isinstance(s, dict) and "build" in s]
        recipes.append({"kind": "compose", "path": f, "services": list(services), "builds": builds, "doc": doc})
    if PREFER_PREBUILT_IMAGES:
        recipes.sort(key=lambda r: (bool(r["builds"]), str(r["path"]).count("/")))
    for f in dockerfiles:
        recipes.append({"kind": "dockerfile", "path": f, "services": ["app"], "builds": ["app"]})
    return recipes


def compose_ports(doc):
    """(service, container_port) pairs declared in the compose file."""
    out = []
    for name, s in (doc.get("services") or {}).items():
        if not isinstance(s, dict):
            continue
        for p in (s.get("ports") or []) + (s.get("expose") or []):
            p = str(p.get("target") if isinstance(p, dict) else p)
            cport = p.split("/")[0].split(":")[-1]
            if cport.isdigit():
                out.append((name, int(cport)))
    return out


def ensure_env(compose_path):
    """Copy .env.example -> .env next to the compose file (and at repo root) if .env is missing."""
    notes = []
    for base in [compose_path.parent]:
        env = base / ".env"
        if env.exists():
            continue
        for ex in (".env.example", ".env.sample", "example.env", "env.example", ".env.template", ".env.dist"):
            src = base / ex
            if src.is_file():
                shutil.copy(src, env)
                notes.append(f"copied {ex} -> .env")
                break
    return notes


# --------------------------------------------------------------------------- boot
class Boot:
    def __init__(self, slug, app, root, recipe):
        self.slug, self.app, self.root, self.recipe = slug, app, root, recipe
        self.project = ("walk_" + re.sub(r"[^a-z0-9]+", "", (slug + app).lower()))[:40]
        self.log = []
        self.containers = []

    def up(self):
        r = self.recipe
        if r["builds"] and not ALLOW_IMAGE_BUILD:
            return False, "recipe needs an image build and ALLOW_IMAGE_BUILD is False"
        if r["kind"] == "compose":
            self.log += ensure_env(r["path"])
            argv = COMPOSE_TOOL_ARGV + ["-p", self.project, "-f", str(r["path"])]
            if r["builds"] and USING_PODMAN:
                bargs = f"--volume {CA_BUNDLE}:{CA_BUNDLE}:ro --env SSL_CERT_FILE={CA_BUNDLE} --env NODE_EXTRA_CA_CERTS={CA_BUNDLE} --env REQUESTS_CA_BUNDLE={CA_BUNDLE} --network=host" if CA_BUNDLE else "--network=host"
                argv += [f"--podman-build-args={bargs}"]
            rc, out, err = run(argv + ["up", "-d"], cwd=r["path"].parent, timeout=BOOT_TIMEOUT_SECONDS)
            self.log.append(f"$ {' '.join(argv)} up -d\n{out[-3000:]}\n{err[-3000:]}")
            if rc != 0:
                return False, f"compose up failed (rc {rc}): {best_error_line(err) if err.strip() else out.strip()[-300:]}"
        else:
            img = f"localhost/{self.project}:walk"
            bargs = [CONTAINER_TOOL, "build", "-t", img, "--network=host"]
            if CA_BUNDLE and USING_PODMAN:
                # docker build (buildx) has no --volume/--env flags for the build step;
                # this CA-trust injection is podman-build-specific, same as the compose path above.
                bargs += ["--volume", f"{CA_BUNDLE}:{CA_BUNDLE}:ro", "--env", f"SSL_CERT_FILE={CA_BUNDLE}",
                          "--env", f"NODE_EXTRA_CA_CERTS={CA_BUNDLE}"]
            rc, out, err = run(bargs + ["-f", str(r["path"]), "."], cwd=self.root, timeout=BOOT_TIMEOUT_SECONDS)
            self.log.append(f"$ {' '.join(bargs)} -f Dockerfile .\n{out[-2000:]}\n{err[-3000:]}")
            if rc != 0:
                return False, f"image build failed: {best_error_line(err) if err.strip() else ''}"
            rc, out, err = run([CONTAINER_TOOL, "run", "-d", "--name", self.project, "--label",
                                f"{'io.podman.compose.project' if USING_PODMAN else 'com.docker.compose.project'}={self.project}", "-P", img], timeout=120)
            self.log.append(f"$ podman run -d -P {img}\n{out}\n{err[-1000:]}")
            if rc != 0:
                return False, f"container run failed: {err.strip()[:300]}"
        return True, ""

    def running_containers(self):
        rc, out, err = run([CONTAINER_TOOL, "ps", "--format", "json", "--filter",
                            f"label=io.podman.compose.project={self.project}"], timeout=60)
        try:
            data = json.loads(out) if out.strip() else []
        except Exception:
            data = []
        if not data:   # dockerfile path uses the label too; fall back to name
            rc, out, err = run([CONTAINER_TOOL, "ps", "--format", "json", "--filter", f"name={self.project}"], timeout=60)
            try:
                data = json.loads(out) if out.strip() else []
            except Exception:
                data = []
        self.containers = data
        return data

    def candidate_urls(self):
        """Every (url, label) worth probing: published host ports, then container ip:port."""
        urls = []
        declared = compose_ports(self.recipe["doc"]) if self.recipe["kind"] == "compose" else []
        for c in self.running_containers():
            name = (c.get("Names") or [""])[0]
            for p in c.get("Ports") or []:
                hp, cp = p.get("host_port"), p.get("container_port")
                if hp and cp not in IGNORE_CONTAINER_PORTS:
                    urls.append((f"http://127.0.0.1:{hp}", f"{name} published {hp}->{cp}"))
            rc, out, err = run([CONTAINER_TOOL, "inspect", "-f",
                                "{{.NetworkSettings.IPAddress}} {{range $k,$v := .NetworkSettings.Networks}}{{$v.IPAddress}} {{end}}|{{range $k,$v := .Config.ExposedPorts}}{{$k}} {{end}}",
                                c.get("Id")], timeout=60)
            ips, _, exposed = out.strip().partition("|")
            ips = [i for i in ips.split() if i]
            ports = [int(x.split("/")[0]) for x in exposed.split() if x.split("/")[0].isdigit()]
            svc = (c.get("Labels") or {}).get("com.docker.compose.service") or (c.get("Labels") or {}).get("io.podman.compose.service")
            ports += [cp for (s, cp) in declared if s == svc]
            for ip in ips:
                for cp in sorted(set(ports)):
                    if cp not in IGNORE_CONTAINER_PORTS:
                        urls.append((f"http://{ip}:{cp}", f"{name} container {ip}:{cp}"))
        seen, out_urls = set(), []
        for u, l in urls:
            if u not in seen:
                seen.add(u)
                out_urls.append((u, l))
        return out_urls

    def wait_for_ui(self):
        deadline = time.time() + BOOT_TIMEOUT_SECONDS
        last = "no containers running"
        while time.time() < deadline:
            cands = self.candidate_urls()
            if not cands and not self.containers:
                return None, "no containers running after up"
            for base, label in cands:
                for path in HTML_PROBE_PATHS:
                    u = base + path
                    try:
                        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 library-walker"})
                        with urllib.request.urlopen(req, timeout=8) as r:
                            body = r.read(200000).decode("utf-8", "ignore")
                            ct = r.headers.get("content-type", "")
                    except urllib.error.HTTPError as e:
                        try:
                            body = e.read(200000).decode("utf-8", "ignore")
                        except Exception:
                            body = ""
                        ct = e.headers.get("content-type", "") if e.headers else ""
                        last = f"{u} -> HTTP {e.code}"
                    except Exception as e:
                        last = f"{u} -> {type(e).__name__}"
                        continue
                    if "text/html" in ct or "<html" in body.lower() or "<!doctype" in body.lower():
                        return u, f"UI answered at {u} ({label})"
                    last = f"{u} -> {ct or 'no content-type'}"
            time.sleep(PORT_POLL_SECONDS)
        return None, f"UI never answered within {BOOT_TIMEOUT_SECONDS}s (last: {last})"

    def container_logs(self, lines=80):
        out = []
        for c in self.containers:
            rc, o, e = run([CONTAINER_TOOL, "logs", "--tail", str(lines), c.get("Id")], timeout=60)
            out.append(f"--- {(c.get('Names') or [''])[0]}\n{o[-4000:]}\n{e[-4000:]}")
        return "\n".join(out)

    def down(self):
        r = self.recipe
        if r["kind"] == "compose":
            run(COMPOSE_TOOL_ARGV + ["-p", self.project, "-f", str(r["path"]), "down", "-v", "-t", "5"],
                cwd=r["path"].parent, timeout=300)
        run([CONTAINER_TOOL, "rm", "-f", "-t", "5", self.project], timeout=120)
        for c in self.containers:
            run([CONTAINER_TOOL, "rm", "-f", "-t", "5", c.get("Id")], timeout=120)
        if USING_PODMAN:
            run([CONTAINER_TOOL, "pod", "rm", "-f", "pod_" + self.project], timeout=120)
        run([CONTAINER_TOOL, "network", "prune", "-f"], timeout=120)
        run([CONTAINER_TOOL, "volume", "prune", "-f"], timeout=120)
        if REMOVE_IMAGES_AFTER:
            run([CONTAINER_TOOL, "image", "prune", "-af"], timeout=600)


# --------------------------------------------------------------------------- browser walk
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
        if len(w) > 5 and w.endswith("ies"):
            out.append(w[:-3] + "y")
    return sorted(set(out))


def has_token(text, toks):
    text = text.lower()
    return [t for t in toks if re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", text)]


class Walk:
    def __init__(self, page, out_dir, base_url):
        self.page, self.out, self.base = page, out_dir, base_url
        self.shots = 0
        self.visited_text = []
        self.steps = []

    def shot(self, label):
        self.shots += 1
        name = f"{self.shots:02d}_{re.sub(r'[^a-z0-9]+', '_', label.lower())[:50]}.png"
        try:
            self.page.screenshot(path=str(self.out / "screenshots" / name), full_page=SCREENSHOT_FULL_PAGE)
        except Exception as e:
            name += f" (screenshot failed: {e})"
        return name

    def text(self):
        """Everything a user could read on the page: visible text PLUS placeholders,
        aria-labels, titles, alt text and link paths — icon-only navs live there."""
        try:
            t = self.page.inner_text("body", timeout=5000)
        except Exception:
            t = ""
        try:
            extra = self.page.evaluate(r"""() => {
                const out = [];
                for (const el of document.querySelectorAll('[placeholder],[aria-label],[title],img[alt],a[href]')) {
                    for (const a of ['placeholder','aria-label','title','alt']) { const v = el.getAttribute(a); if (v) out.push(v); }
                    const h = el.getAttribute('href'); if (h && !h.startsWith('http') && !h.startsWith('#')) out.push(h.replace(/[\/_\-\.?=&]+/g,' '));
                }
                return out.join(' ');
            }""")
        except Exception:
            extra = ""
        t = t + "\n" + (extra or "")
        self.visited_text.append(t)
        return t

    def goto(self, url):
        try:
            self.page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            self.page.wait_for_timeout(1500)
            return True
        except Exception:
            return False

    # ---- forms in the way (setup / register / login)
    def _fill_form(self, form):
        """Fill any visible inputs in a form with sensible values. Returns count filled."""
        filled = 0
        for inp in form.query_selector_all("input, select, textarea"):
            try:
                if not inp.is_visible():
                    continue
                typ = (inp.get_attribute("type") or "text").lower()
                name = " ".join(filter(None, [inp.get_attribute("name"), inp.get_attribute("id"),
                                              inp.get_attribute("placeholder"), inp.get_attribute("autocomplete")])).lower()
                tag = inp.evaluate("e => e.tagName.toLowerCase()")
                if tag == "select":
                    opts = inp.query_selector_all("option")
                    if len(opts) > 1:
                        inp.select_option(index=1)
                        filled += 1
                    continue
                if typ in ("hidden", "submit", "button", "file", "image", "reset"):
                    continue
                if typ == "checkbox":
                    if not inp.is_checked():
                        inp.check(timeout=2000)
                    filled += 1
                    continue
                if typ == "radio":
                    inp.check(timeout=2000)
                    filled += 1
                    continue
                if typ == "email" or "email" in name or "mail" in name:
                    val = TEST_USER["email"]
                elif typ == "password" or "pass" in name:
                    val = TEST_USER["password"]
                elif typ == "url" or "url" in name or "domain" in name or "host" in name:
                    val = TEST_USER["url_field"]
                elif typ == "number":
                    val = "1"
                elif "user" in name or "login" in name or "handle" in name or "nick" in name:
                    val = TEST_USER["username"]
                elif "site" in name or "title" in name or "company" in name or "org" in name or "workspace" in name or "team" in name:
                    val = TEST_USER["site"]
                elif "name" in name:
                    val = TEST_USER["name"]
                elif "code" in name or "token" in name or "key" in name or "otp" in name:
                    continue
                else:
                    val = TEST_USER["name"]
                inp.fill(val, timeout=3000)
                filled += 1
            except Exception:
                continue
        return filled

    def _submit(self, form):
        for sel in ("button[type=submit]", "input[type=submit]", "button:not([type=button])", "button"):
            try:
                b = form.query_selector(sel)
                if b and b.is_visible():
                    b.click(timeout=5000)
                    self.page.wait_for_timeout(3000)
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    return True
            except Exception:
                continue
        try:
            form.press("input", "Enter")
            self.page.wait_for_timeout(3000)
            return True
        except Exception:
            return False

    def _find_gate_form(self):
        forms = [f for f in self.page.query_selector_all("form") if f.is_visible()]
        pw = [f for f in forms if f.query_selector("input[type=password]")]
        if pw:
            return pw[0]
        for f in forms:
            t = (f.inner_text() or "").lower()
            if any(w in t for w in GATE_WORDS) or f.query_selector("input[type=email]"):
                return f
        # no form element: maybe a link to sign up / log in
        return None

    def _click_gate_link(self):
        for w in ("sign up", "register", "create account", "get started", "log in", "login", "sign in", "setup", "install"):
            try:
                loc = self.page.get_by_role("link", name=re.compile(w, re.I)).first
                if loc.count() and loc.is_visible():
                    loc.click(timeout=4000)
                    self.page.wait_for_timeout(2000)
                    return w
                loc = self.page.get_by_role("button", name=re.compile(w, re.I)).first
                if loc.count() and loc.is_visible():
                    loc.click(timeout=4000)
                    self.page.wait_for_timeout(2000)
                    return w
            except Exception:
                continue
        return None

    def get_in(self):
        """Fill whatever forms stand in the way. Returns (state, steps)."""
        steps = []
        tried_defaults = 0
        for i in range(MAX_GATE_STEPS):
            form = self._find_gate_form()
            if form is None:
                w = self._click_gate_link()
                if w:
                    steps.append({"action": f"clicked '{w}'", "url": self.page.url, "shot": self.shot(f"gate_{w}")})
                    form = self._find_gate_form()
                if form is None:
                    return ("IN" if i > 0 or self._looks_like_app() else "NO_GATE_FOUND"), steps
            before = self.page.url
            ftext = (form.inner_text() or "").lower() + " " + self.page.url.lower()
            is_login = form.query_selector("input[type=password]") is not None and not form.query_selector("input[type=email]") \
                and len(form.query_selector_all("input[type=password]")) == 1 \
                and not any(w in ftext for w in ("regist", "sign up", "signup", "create", "setup", "install"))
            if is_login and tried_defaults < len(DEFAULT_CREDENTIALS):
                u, p = DEFAULT_CREDENTIALS[tried_defaults]
                tried_defaults += 1
                try:
                    ins = [x for x in form.query_selector_all("input") if x.is_visible() and (x.get_attribute("type") or "text") not in ("hidden", "submit", "checkbox")]
                    if len(ins) >= 2:
                        ins[0].fill(u)
                        ins[1].fill(p)
                    action = f"login as {u}/{p}"
                except Exception:
                    action = "login form fill failed"
            else:
                n = self._fill_form(form)
                action = f"filled {n} fields"
            self._submit(form)
            after = self.page.url
            shot = self.shot(f"gate_step_{i+1}")
            steps.append({"action": action, "from": before, "to": after, "shot": shot})
            body = self.text().lower()
            if after != before and not self._find_gate_form():
                return "IN", steps
            if "invalid" in body or "incorrect" in body or "wrong" in body or "error" in body:
                if not is_login:
                    pass
            if self._find_gate_form() is None and self._looks_like_app():
                return "IN", steps
        return "STUCK", steps

    def _looks_like_app(self):
        t = self.text().lower()
        return any(w in t for w in ("logout", "log out", "sign out", "dashboard", "settings", "profile", "welcome"))

    # ---- capability walk
    def collect_links(self):
        items = []
        try:
            for el in self.page.query_selector_all("a[href], button, [role=button], [role=menuitem], [role=tab], [role=link], nav *, [aria-label], [title]")[:MAX_LINKS_COLLECTED]:
                try:
                    if not el.is_visible():
                        continue
                    txt = (el.inner_text() or "").strip()
                    href = el.get_attribute("href") or ""
                    title = " ".join(filter(None, [el.get_attribute("title"), el.get_attribute("aria-label"),
                                                   el.get_attribute("placeholder"), el.get_attribute("alt")]))
                    if txt or href or title:
                        items.append({"el": el, "text": txt[:80], "href": href, "title": title})
                except Exception:
                    continue
        except Exception:
            pass
        return items

    def walk_capabilities(self, caps):
        home = self.page.url
        results = {}
        home_text = self.text()
        for cap in caps:
            toks = tokens(cap)
            verdict, evidence, shot = "ABSENT", [], None
            if not self.goto(home):
                pass
            links = self.collect_links()
            matches = [l for l in links if has_token(f"{l['text']} {l['href']} {l['title']}", toks)]
            for l in matches[:LINKS_PER_CAPABILITY]:
                try:
                    l["el"].click(timeout=4000)
                    self.page.wait_for_timeout(2000)
                except Exception:
                    if l["href"] and not l["href"].startswith(("#", "javascript", "mailto")):
                        self.goto(l["href"] if l["href"].startswith("http") else self.base.rstrip("/") + "/" + l["href"].lstrip("/"))
                    else:
                        continue
                t = self.text()
                title = ""
                try:
                    title = self.page.title()
                    h = self.page.query_selector("h1, h2, [role=heading]")
                    title += " " + (h.inner_text() if h else "")
                except Exception:
                    pass
                hit_page = has_token(f"{title} {self.page.url}", toks)
                if hit_page:
                    verdict = "REACHED"
                    evidence = [f"clicked '{l['text'] or l['href']}' -> {self.page.url} (heading/url matched {hit_page})"]
                    shot = self.shot(f"cap_{cap}")
                    break
                elif has_token(t, toks):
                    verdict = "SEEN"
                    evidence = [f"clicked '{l['text'] or l['href']}' -> {self.page.url}; words {has_token(t, toks)} on page"]
                    shot = self.shot(f"cap_{cap}")
                self.goto(home)
            if verdict == "ABSENT":
                seen = has_token(" ".join(self.visited_text[-6:] + [home_text]), toks)
                if seen:
                    verdict, evidence = "SEEN", [f"words {seen} on visited pages; no dedicated screen reached"]
            results[cap] = {"verdict": verdict, "evidence": evidence, "screenshot": shot, "tokens": toks}
            say(f"       {verdict:<8} {cap}")
        return results


# --------------------------------------------------------------------------- one app
def walk_app(cat, surv, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "screenshots").mkdir(exist_ok=True)
    res = {"category": cat["category"], "slug": cat["slug"], "app": surv["name"], "repo": surv["repo"],
           "commit": surv["commit"], "started": datetime.now().isoformat(timespec="seconds"),
           "boot": {}, "gate": {}, "capabilities": {}, "summary": {}}
    say(f"  -> {surv['name']} @ {surv['commit'][:12]}", always=True)
    root, err = clone_at(surv["repo"], surv["commit"])
    if root is None:
        res["boot"] = {"status": "BOOT FAILED", "reason": f"clone: {err}"}
        return _finish(res, out_dir)
    recipes = find_recipes(root, surv.get("run_recipes") or ())
    if not recipes:
        res["boot"] = {"status": "BOOT FAILED", "reason": "no usable compose file or Dockerfile found in clone"}
        shutil.rmtree(root, ignore_errors=True)
        return _finish(res, out_dir)
    boot, url = None, None
    for rec in recipes[:3]:
        say(f"     recipe {rec['path'].relative_to(root)} services={rec['services']} builds={rec['builds']}")
        boot = Boot(cat["slug"], surv["name"], root, rec)
        ok, why = boot.up()
        if not ok:
            say(f"     BOOT FAILED: {why}")
            res["boot"] = {"status": "BOOT FAILED", "reason": why, "recipe": str(rec["path"].relative_to(root)), "log": boot.log}
            boot.down()
            continue
        url, why = boot.wait_for_ui()
        if url:
            say(f"     {why}")
            res["boot"] = {"status": "BOOTED", "recipe": str(rec["path"].relative_to(root)), "url": url,
                           "detail": why, "notes": boot.log[:1] if boot.log and boot.log[0].startswith("copied") else []}
            break
        say(f"     BOOT FAILED: {why}")
        res["boot"] = {"status": "BOOT FAILED", "reason": why, "recipe": str(rec["path"].relative_to(root)),
                       "container_logs": boot.container_logs(), "log": boot.log}
        boot.down()
    if not url:
        shutil.rmtree(root, ignore_errors=True)
        return _finish(res, out_dir)

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE_PATH") or None)
            ctx = browser.new_context(viewport=VIEWPORT, ignore_https_errors=True)
            page = ctx.new_page()
            w = Walk(page, out_dir, url)
            if not w.goto(url):
                res["gate"] = {"state": "PAGE FAILED TO LOAD"}
            else:
                res["gate"] = {"landing_shot": w.shot("landing"), "landing_url": page.url}
                state, steps = w.get_in()
                res["gate"].update({"state": state, "steps": steps, "final_url": page.url, "after_shot": w.shot("after_gate")})
                say(f"     gate: {state} after {len(steps)} step(s) -> {page.url}")
                res["capabilities"] = w.walk_capabilities(cat["capabilities"])
            browser.close()
    except Exception as e:
        res["gate"]["error"] = f"{type(e).__name__}: {e}"
    boot.down()
    shutil.rmtree(root, ignore_errors=True)
    return _finish(res, out_dir)


def _finish(res, out_dir):
    caps = res["capabilities"]
    n = len(caps)
    reached = sum(1 for c in caps.values() if c["verdict"] == "REACHED")
    seen = sum(1 for c in caps.values() if c["verdict"] == "SEEN")
    absent = [k for k, c in caps.items() if c["verdict"] == "ABSENT"]
    res["summary"] = {"booted": res["boot"].get("status") == "BOOTED", "gate": res["gate"].get("state"),
                      "capabilities": n, "reached": reached, "seen": seen, "absent": len(absent),
                      "gaps": absent + [k for k, c in caps.items() if c["verdict"] == "SEEN"]}
    res["finished"] = datetime.now().isoformat(timespec="seconds")
    (out_dir / "result.json").write_text(json.dumps(res, indent=1, default=str))
    md = [f"# Walkthrough — {res['app']} for {res['category']}", "",
          f"Repo {res['repo']} @ `{res['commit']}`  ", f"Started {res['started']}, finished {res['finished']}", "",
          f"## Boot: **{res['boot'].get('status')}**", ""]
    for k in ("recipe", "url", "detail", "reason", "notes"):
        if res["boot"].get(k):
            md.append(f"- {k}: {res['boot'][k]}")
    md += ["", f"## Getting in: **{res['gate'].get('state', '—')}**", ""]
    if res["gate"].get("landing_shot"):
        md.append(f"- landing: `{res['gate']['landing_url']}` → screenshots/{res['gate']['landing_shot']}")
    for s in res["gate"].get("steps", []):
        md.append(f"- {s['action']} → {s.get('to', s.get('url'))} → screenshots/{s['shot']}")
    if res["gate"].get("after_shot"):
        md.append(f"- after: `{res['gate']['final_url']}` → screenshots/{res['gate']['after_shot']}")
    if res["gate"].get("error"):
        md.append(f"- error: {res['gate']['error']}")
    md += ["", "## Capabilities", "", "| Capability | Verdict | Evidence | Screenshot |", "|---|---|---|---|"]
    for cap, c in caps.items():
        md.append(f"| {cap} | **{c['verdict']}** | {'; '.join(c['evidence'])} | {('screenshots/' + c['screenshot']) if c['screenshot'] else ''} |")
    s = res["summary"]
    md += ["", f"## Summary: booted={s['booted']} gate={s['gate']} reached {s['reached']}/{s['capabilities']}, "
               f"seen {s['seen']}, absent {s['absent']}", "",
           "Gaps (to be filled by capability services): " + (", ".join(s["gaps"]) or "none")]
    (out_dir / "WALKTHROUGH.md").write_text("\n".join(md) + "\n")
    return res


# --------------------------------------------------------------------------- per category
def walk_category(cat):
    f = HERE / SHORTLIST_DIR / f"{cat['slug']}.json"
    if not f.exists():
        return None
    sl = json.loads(f.read_text())
    if not sl["survivors"]:
        return None
    say(f"\n=== {cat['slug']}  ({cat['category']} — exemplar {cat['exemplar']}) ===", always=True)
    out = {"slug": cat["slug"], "category": cat["category"], "exemplar": cat["exemplar"], "attempts": []}
    for surv in sl["survivors"][:CANDIDATES_PER_CATEGORY]:
        d = HERE / WALK_DIR / cat["slug"] / re.sub(r"[^a-zA-Z0-9]+", "_", surv["name"])
        prior = json.loads((d / "result.json").read_text()) if (d / "result.json").exists() else None
        if SKIP_ALREADY_WALKED and prior and prior["boot"].get("status") == "BOOTED":
            res = prior
            say(f"  (already walked {surv['name']}: BOOTED, gate {res['gate'].get('state')})")
        else:
            res = walk_app(cat, surv, d)
        out["attempts"].append({"app": surv["name"], "dir": str(d.relative_to(HERE)), "summary": res["summary"],
                                "boot": res["boot"].get("status"), "reason": res["boot"].get("reason")})
        if res["boot"].get("status") == "BOOTED":
            break
    return out


def write_table(results, today):
    d = HERE / REPORT_DIR
    d.mkdir(exist_ok=True)
    lines = [f"# Walk table — {today.isoformat()}", "",
             "Verdicts: REACHED = a screen for it was reached; SEEN = words only; ABSENT = no trace. "
             "Booted + got in + reached is the proof level of this walker; it does not prove each feature end to end.", "",
             "| # | Category | App | Booted | Got in | Reached | Seen | Absent | Gaps | Folder |", "|---|---|---|---|---|---|---|---|---|---|"]
    n = 0
    for r in results:
        if not r:
            continue
        n += 1
        a = r["attempts"][-1]
        s = a["summary"]
        lines.append(f"| {n} | {r['category']} | {a['app']} | {a['boot']}{(' — ' + a['reason']) if a.get('reason') else ''} | "
                     f"{s.get('gate') or '—'} | {s['reached']}/{s['capabilities']} | {s['seen']} | {s['absent']} | "
                     f"{', '.join(s['gaps'][:8])}{'…' if len(s['gaps']) > 8 else ''} | {a['dir']} |")
    (d / "WALK_TABLE.md").write_text("\n".join(lines) + "\n")
    (d / "WALK_OUTPUT.txt").write_text("\n".join(LOG) + "\n")


def preflight():
    """Refuse to start unless a real container engine and compose tool work."""
    configure_container_tools()
    rc, out, err = run([CONTAINER_TOOL, "info"], timeout=60)
    if rc != 0:
        sys.exit(f"{CONTAINER_TOOL} is not working: {err.strip()[:300]}")
    rc, out, err = run([CONTAINER_TOOL, "pull", "-q", "alpine:3.20"], timeout=300)
    if rc != 0:
        sys.exit(f"{CONTAINER_TOOL} cannot pull a Docker Hub short name ('alpine:3.20'): {err.strip()[:300]}\n"
                 "Fix: put  unqualified-search-registries = [\"docker.io\"]  in /etc/containers/registries.conf")
    rc, out, err = run(COMPOSE_TOOL_ARGV + ["--version"], timeout=60)
    if rc != 0:
        sys.exit(f"{' '.join(COMPOSE_TOOL_ARGV)} is not available: {err.strip()[:200]}")


def main(argv):
    preflight()
    cats = json.loads((HERE / CATEGORY_FILE).read_text())["categories"]
    if "--list" in argv:
        for c in cats:
            f = HERE / SHORTLIST_DIR / f"{c['slug']}.json"
            if f.exists() and json.loads(f.read_text())["survivors"]:
                print(c["slug"])
        return 0
    slugs = [a for a in argv if not a.startswith("--")]
    if slugs:
        cats = [c for c in cats if c["slug"] in slugs]
    Path(CLONE_DIR).mkdir(parents=True, exist_ok=True)
    results = [walk_category(c) for c in cats]
    write_table(results, date.today())
    booted = sum(1 for r in results if r and r["attempts"][-1]["boot"] == "BOOTED")
    say(f"\nWALK DONE: {booted} booted of {sum(1 for r in results if r)} categories walked. "
        f"Table: {REPORT_DIR}/WALK_TABLE.md", always=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
