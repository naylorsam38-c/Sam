#!/usr/bin/env python3
"""
install_startup.py — spec sections 6-7: INSTALLATION + STARTUP gate, per app.

Runs only on apps that are ACQUIRED (source cloned, licence cleared). For
each:
  1. Detect the ecosystem from the repo's own dependency/config files -
     never guessed, only what's actually present in the checkout.
  2. Find a container recipe (compose file or Dockerfile) - this pipeline
     starts apps the way they document starting themselves, not a hand-rolled
     substitute. No recipe = INSTALL_FAILED ("no documented way to run it").
  3. Boot it for real via Docker: pull/build images, bring the stack up.
  4. Verify STARTUP for real: container running AND a port listening AND an
     HTTP response AND that response looks like a real page (not just any
     response) - a bare /health 200 is explicitly insufficient per spec
     section 6, so this checks the app's actual root/likely UI paths too.

Known, already-diagnosed constraint of THIS sandbox (not a defect in this
script): its egress policy denies ghcr.io, quay.io, and OS package mirrors
(deb.debian.org, Alpine's apk mirrors) outright. A recipe that needs one of
those mid-build or mid-pull is recorded BLOCKED_EXTERNAL_DEPENDENCY with the
exact host and error, per spec section 15 - not silently marked failed, and
never retried against the same blocked host.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
MANIFEST_FILE = HERE / "manifest.json"
APPS_DIR = HERE / "applications"

BOOT_TIMEOUT_SECONDS = 480
PORT_POLL_SECONDS = 5
IGNORE_CONTAINER_PORTS = (5432, 3306, 27017, 6379, 9200, 5672, 25, 465, 587, 993, 995, 143, 110,
                          1883, 8883, 2181, 9092, 4222, 11211, 9000, 9001)
HTML_PROBE_PATHS = ("/", "/login", "/index.html", "/admin", "/app", "/ui")
COMPOSE_FILE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",
                      "docker-compose.prod.yml", "docker-compose.production.yml")
COMPOSE_SEARCH_DIRS = (".", "docker", "deploy", "deployment", "docker-compose", "compose",
                       "examples", "example", "install", "contrib/docker", "scripts")
COMPOSE_SKIP_NAME_PARTS = ("test", "dev", "development", "ci", "e2e", "override", "debug")
DOCKERFILE_NAMES = ("Dockerfile", "Dockerfile.production", "Dockerfile.prod", "Dockerfile.release",
                    "docker/Dockerfile", "Containerfile")

DEP_FILES = {
    "node": ("package.json",), "python": ("requirements.txt", "pyproject.toml", "Pipfile"),
    "ruby": ("Gemfile",), "php": ("composer.json",), "go": ("go.mod",),
    "java_maven": ("pom.xml",), "java_gradle": ("build.gradle", "build.gradle.kts"),
    "dotnet_glob": ("*.csproj",),
}

BLOCKED_HOSTS = ("ghcr.io", "quay.io", "pkg-containers.githubusercontent.com",
                 "deb.debian.org", "dl-cdn.alpinelinux.org", "security.debian.org",
                 "production.cloudfront.docker.com", "releases.cortezaproject.org")
# The known list above is a fallback; the real signature of this sandbox's
# policy denial is a "<url>": Forbidden right after a failed request, for
# ANY host (registry.custom-domain.com, cgr.dev, etc, not just the well-known
# ones) - so the host is parsed straight out of the actual failing line
# rather than string-matched against a fixed list, which previously picked up
# an unrelated "ghcr.io" mentioned elsewhere in the same log and misreported
# the real blocked host (cgr.dev) as ghcr.io.
FORBIDDEN_HOST_RE = re.compile(r'https?://([a-zA-Z0-9.\-]+)(?::\d+)?/[^\s"]*"\s*:\s*Forbidden')


def run(argv, cwd=None, timeout=None):
    try:
        p = subprocess.run(argv, cwd=cwd, timeout=timeout, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", str(e)


def best_error_line(text, max_len=400):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return ""
    for l in reversed(lines):
        if re.search(r"\berror\b", l, re.I) and "--help" not in l:
            return l.strip()[:max_len]
    return lines[-1].strip()[:max_len]


def blocked_host_in(text):
    hosts = FORBIDDEN_HOST_RE.findall(text)
    if hosts:
        return hosts[-1]  # the last (most proximate to the actual failure) match
    for h in BLOCKED_HOSTS:
        if h in text:
            return h
    return None


def detect_ecosystem(root):
    found = {}
    for eco, files in DEP_FILES.items():
        for pat in files:
            matches = list(root.glob(pat)) if "*" in pat else ([root / pat] if (root / pat).is_file() else [])
            if matches:
                found.setdefault(eco, []).append(str(matches[0].relative_to(root)))
    has_docker = (root / "Dockerfile").is_file() or any((root / n).is_file() for n in COMPOSE_FILE_NAMES)
    db_hint = None
    for f in ("docker-compose.yml", "docker-compose.yaml"):
        p = root / f
        if p.is_file():
            t = p.read_text(errors="ignore").lower()
            for db in ("postgres", "mysql", "mariadb", "mongo", "redis"):
                if db in t:
                    db_hint = db
                    break
    return {"detected_ecosystems": found, "has_container_recipe": has_docker,
            "database_requirement": db_hint}


def find_recipes(root):
    found = []
    for sd in COMPOSE_SEARCH_DIRS:
        base = root / sd
        if not base.is_dir():
            continue
        for n in COMPOSE_FILE_NAMES:
            f = base / n
            if f.is_file() and not any(k in f.name.lower() for k in COMPOSE_SKIP_NAME_PARTS):
                found.append(f)
    dockerfiles = [root / n for n in DOCKERFILE_NAMES if (root / n).is_file()]
    recipes = []
    for f in found:
        try:
            doc = yaml.safe_load(f.read_text(errors="ignore")) or {}
        except Exception:
            continue
        services = doc.get("services") or {}
        if not isinstance(services, dict) or not services:
            continue
        builds = [n for n, s in services.items() if isinstance(s, dict) and "build" in s]
        recipes.append({"kind": "compose", "path": f, "services": list(services), "builds": builds, "doc": doc})
    recipes.sort(key=lambda r: (bool(r["builds"]), str(r["path"]).count("/")))
    for f in dockerfiles:
        recipes.append({"kind": "dockerfile", "path": f, "services": ["app"], "builds": ["app"]})
    return recipes


def ensure_env(compose_path):
    notes = []
    base = compose_path.parent
    env = base / ".env"
    if not env.exists():
        for ex in (".env.example", ".env.sample", "example.env", "env.example", ".env.template", ".env.dist"):
            src = base / ex
            if src.is_file():
                shutil.copy(src, env)
                notes.append(f"copied {ex} -> .env")
                break
    return notes


def compose_ports(doc):
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


class Boot:
    def __init__(self, app_id, root, recipe):
        self.app_id, self.root, self.recipe = app_id, root, recipe
        self.project = ("lib_" + re.sub(r"[^a-z0-9]+", "", app_id.lower()))[:40]
        self.log = []

    def up(self):
        r = self.recipe
        if r["kind"] == "compose":
            self.log += ensure_env(r["path"])
            argv = ["docker", "compose", "-p", self.project, "-f", str(r["path"])]
            rc, out, err = run(argv + ["up", "-d"], cwd=r["path"].parent, timeout=BOOT_TIMEOUT_SECONDS)
            self.log.append(f"$ {' '.join(argv)} up -d\n{out[-2000:]}\n{err[-2000:]}")
            if rc != 0:
                host = blocked_host_in(out + err)
                return False, best_error_line(err) if err.strip() else out.strip()[-400:], host
        else:
            img = f"localhost/{self.project}:lib"
            bargs = ["docker", "build", "-t", img, "--network=host", "-f", str(r["path"]), "."]
            rc, out, err = run(bargs, cwd=self.root, timeout=BOOT_TIMEOUT_SECONDS)
            self.log.append(f"$ {' '.join(bargs)}\n{out[-2000:]}\n{err[-2000:]}")
            if rc != 0:
                host = blocked_host_in(out + err)
                return False, best_error_line(err) if err.strip() else "", host
            rc, out, err = run(["docker", "run", "-d", "--name", self.project, "--label",
                                f"com.docker.compose.project={self.project}", "-P", img], timeout=120)
            self.log.append(f"$ docker run -d -P {img}\n{out}\n{err[-800:]}")
            if rc != 0:
                return False, best_error_line(err), None
        return True, "", None

    def running_containers(self):
        rc, out, err = run(["docker", "ps", "--format", "json", "--filter",
                            f"label=com.docker.compose.project={self.project}"], timeout=60)
        data = []
        for line in out.strip().splitlines():
            try:
                data.append(json.loads(line))
            except Exception:
                continue
        if not data:
            rc, out, err = run(["docker", "ps", "--format", "json", "--filter", f"name={self.project}"], timeout=60)
            for line in out.strip().splitlines():
                try:
                    data.append(json.loads(line))
                except Exception:
                    continue
        return data

    def candidate_urls(self):
        urls = []
        declared = compose_ports(self.recipe["doc"]) if self.recipe["kind"] == "compose" else []
        for c in self.running_containers():
            for p in (c.get("Ports") or "").split(","):
                m = re.search(r"0\.0\.0\.0:(\d+)->(\d+)", p)
                if m:
                    hp, cp = m.group(1), int(m.group(2))
                    if cp not in IGNORE_CONTAINER_PORTS:
                        urls.append((f"http://127.0.0.1:{hp}", f"{c.get('Names')} published {hp}->{cp}"))
            rc, out, err = run(["docker", "inspect", "-f",
                                "{{range $k,$v := .NetworkSettings.Networks}}{{$v.IPAddress}} {{end}}|"
                                "{{range $k,$v := .Config.ExposedPorts}}{{$k}} {{end}}",
                                c.get("ID") or c.get("Id")], timeout=60)
            ips, _, exposed = out.strip().partition("|")
            ips = [i for i in ips.split() if i]
            ports = [int(x.split("/")[0]) for x in exposed.split() if x.split("/")[0].isdigit()]
            svc = None
            for name, s in (self.recipe.get("doc", {}).get("services") or {}).items():
                if name in (c.get("Names") or ""):
                    svc = name
            ports += [cp for (s, cp) in declared if s == svc]
            for ip in ips:
                for cp in sorted(set(ports)):
                    if cp not in IGNORE_CONTAINER_PORTS:
                        urls.append((f"http://{ip}:{cp}", f"{c.get('Names')} container {ip}:{cp}"))
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
            containers = self.running_containers()
            if not cands and not containers:
                return None, "no containers running after up"
            for base, label in cands:
                for path in HTML_PROBE_PATHS:
                    u = base + path
                    try:
                        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 library-acquirer"})
                        with urllib.request.urlopen(req, timeout=8) as resp:
                            body = resp.read(200000).decode("utf-8", "ignore")
                            ct = resp.headers.get("content-type", "")
                            code = resp.status
                    except urllib.error.HTTPError as e:
                        try:
                            body = e.read(200000).decode("utf-8", "ignore")
                        except Exception:
                            body = ""
                        ct = e.headers.get("content-type", "") if e.headers else ""
                        code = e.code
                    except Exception as e:
                        last = f"{u} -> {type(e).__name__}"
                        continue
                    if "text/html" in ct or "<html" in body.lower() or "<!doctype" in body.lower():
                        return {"url": u, "http_status": code}, f"UI answered at {u} ({label}), HTTP {code}"
                    last = f"{u} -> HTTP {code}, content-type {ct or 'none'}"
            time.sleep(PORT_POLL_SECONDS)
        return None, f"no real HTML UI within {BOOT_TIMEOUT_SECONDS}s (last: {last})"

    def down(self):
        r = self.recipe
        if r["kind"] == "compose":
            run(["docker", "compose", "-p", self.project, "-f", str(r["path"]), "down", "-v", "-t", "5"],
                cwd=r["path"].parent, timeout=300)
        run(["docker", "rm", "-f", "-t", "5", self.project], timeout=120)
        for c in self.running_containers():
            run(["docker", "rm", "-f", "-t", "5", c.get("ID") or c.get("Id")], timeout=120)


def process_app(entry):
    app_id = entry["id"]
    root = APPS_DIR / app_id / "source"
    if not root.is_dir():
        return {"status": "INSTALL_FAILED", "reason": "source directory missing"}, None

    ecosystem = detect_ecosystem(root)
    if not ecosystem["has_container_recipe"]:
        return {"status": "INSTALL_FAILED", "reason": "no Dockerfile or compose file - no documented way to run it"}, ecosystem

    recipes = find_recipes(root)
    if not recipes:
        return {"status": "INSTALL_FAILED", "reason": "compose/Dockerfile present but unusable (no services or unparseable)"}, ecosystem

    last_reason, boot_log, install = None, [], None
    for rec in recipes[:3]:
        print(f"  recipe {rec['path'].relative_to(root)} services={rec['services']} builds={rec['builds']}")
        boot = Boot(app_id, root, rec)
        ok, reason, blocked_host = boot.up()
        if not ok:
            boot_log.extend(boot.log)
            if blocked_host:
                boot.down()
                return {"status": "BLOCKED_EXTERNAL_DEPENDENCY",
                        "reason": f"install needs {blocked_host}, which this sandbox's egress policy denies: {reason}",
                        "blocked_host": blocked_host,
                        "runtime_hint": list(ecosystem["detected_ecosystems"]),
                        "startup_command": f"docker compose -f {rec['path'].name} up -d" if rec["kind"] == "compose"
                                            else f"docker build -f {rec['path'].name} .",
                        "log": boot_log[-2:]}, ecosystem
            print(f"    INSTALL_FAILED: {reason}")
            last_reason = reason
            boot.down()
            continue
        result, why = boot.wait_for_ui()
        if result:
            print(f"    STARTED: {why}")
            return {"status": "STARTABLE", "reason": None, "url": result["url"],
                    "http_status": result["http_status"], "recipe": str(rec["path"].relative_to(root)),
                    "recipe_kind": rec["kind"],
                    "runtime_hint": list(ecosystem["detected_ecosystems"]),
                    "startup_command": f"docker compose -f {rec['path'].name} up -d" if rec["kind"] == "compose"
                                        else f"docker build -f {rec['path'].name} . && docker run -P <image>",
                    "boot_object": boot}, ecosystem
        print(f"    STARTUP_FAILED: {why}")
        last_reason = why
        boot.down()
    return {"status": "STARTUP_FAILED", "reason": last_reason or "no recipe produced a running UI",
            "runtime_hint": list(ecosystem["detected_ecosystems"])}, ecosystem


def preflight():
    rc, out, err = run(["docker", "info"], timeout=30)
    if rc != 0:
        sys.exit(f"docker is not working: {err.strip()[:300]}")
    rc, out, err = run(["docker", "compose", "version"], timeout=30)
    if rc != 0:
        sys.exit(f"docker compose not available: {err.strip()[:300]}")


def main():
    preflight()
    manifest = json.loads(MANIFEST_FILE.read_text())
    counts = {}
    keep_running = []  # (app_id, Boot) for apps left up for the screen-discovery stage
    for entry in manifest["applications"]:
        if entry["status"] != "ACQUIRED":
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
            continue
        app_id = entry["id"]
        print(f"{app_id} ({entry['category_slug']}) {entry['name']}")
        result, ecosystem = process_app(entry)
        boot_obj = result.pop("boot_object", None)
        entry["status"] = result["status"]
        entry["install_startup"] = result
        entry["ecosystem"] = ecosystem
        counts[result["status"]] = counts.get(result["status"], 0) + 1

        d = APPS_DIR / app_id
        (d / "app.json").write_text(json.dumps({k: v for k, v in entry.items()}, indent=1))
        MANIFEST_FILE.write_text(json.dumps(manifest, indent=1))  # checkpoint after every app

        if boot_obj is not None:
            keep_running.append((app_id, boot_obj, result["url"]))
        # everything else (failed at install/startup) has nothing left running to tear down

    print("\n=== INSTALL/STARTUP SUMMARY ===")
    for k, v in sorted(counts.items()):
        print(f"{k}: {v}")

    # Leave STARTABLE apps' containers running for the screen-discovery stage;
    # write the live map so that stage doesn't need to re-boot anything.
    live = [{"app_id": a, "url": u, "project": b.project} for a, b, u in keep_running]
    (HERE / "live_containers.json").write_text(json.dumps(live, indent=1))
    print(f"\n{len(live)} app(s) left running for screen discovery; see live_containers.json")


if __name__ == "__main__":
    sys.exit(main())
