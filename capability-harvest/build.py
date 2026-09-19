#!/usr/bin/env python3
"""
build.py — Build / Adapter stage.

Consumes a REGISTERED capability (capabilities/<CAP-ID>.json) and produces a
real, running composed application -- not a simulation, not a stand-in.

What "verified composition" means (documented honestly, see README "What
this proves vs. what's next"): it does not yet graft a harvested route onto
an unrelated host application (that needs the dependency-binding/adapter
system referenced in the handoff as future work). What it DOES do, for
real, every run:

  1. Integrity-checks the shelf record itself (the harvested text on disk
     still hashes to what PROVENANCE.json says was harvested).
  2. Re-extracts the same function from the live application checkout,
     right now, the same way harvest_parts.py did, and requires it to be
     BYTE-IDENTICAL to the shelved copy -- if the live source has drifted
     since harvest, this is reported, not silently ignored.
  3. Only then starts a real server for the app -- so what a live
     HTTP/Playwright test exercises is provably the exact capability that
     was harvested, not merely "the app, which happens to still work."

Real applications are not all shaped the same way, and this build stage
does not bend them to fit one template -- it runs each app the way its own
authors run it. Three runner kinds, chosen per application in
discovery/discover_applications.py's APPLICATION_MANIFEST (`runner` field):

  - flask_factory       : app exposes create_app(); we call it and run().
  - flask_module_attr    : app builds a module-level `app = Flask(...)`
                           object whose side effects (table creation, etc.)
                           run at import time; we import it and call run()
                           ourselves, since the app has no __main__ guard
                           gating its host/port.
  - script_entrypoint    : the app's own __main__ block gates real setup
                           (e.g. flask-messenger only creates its sqlite
                           schema inside `if __name__ == '__main__':`), so
                           we run the entry script directly as a subprocess
                           rather than importing it, and accept whatever
                           host/port it itself hardcodes.

Run:
    python3 build.py start --cap CAP-0001
    python3 build.py status
    python3 build.py stop
"""

import argparse
import ast
import glob
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
DEFAULT_HOST = "127.0.0.1"
SMTP_DEBUG_PORT = 1025
VENV_PYTHON = config.PROJECT_ROOT / ".venv" / "bin" / "python3"
# Some harvested apps use syntax their own author only ever ran on a newer
# CPython than this pipeline's default venv (e.g. PEP 701's relaxed
# f-string quoting, Python 3.12+) -- not a bug in the app, a real
# interpreter-compatibility requirement. Rather than force every app onto
# one Python version, a runner may set "python_version" to pick one of
# these; default is "3.11" (VENV_PYTHON) when unset.
PYTHON_BY_VERSION = {
    "3.11": VENV_PYTHON,
    "3.12": config.PROJECT_ROOT / ".venv-py312" / "bin" / "python3",
}
BUILD_DB_PATH = config.OUTPUT_ROOT / "build_run.db"  # used only by flask_factory apps with a DATABASE_URL env var
# Some apps resolve their own data directory from $HOME (e.g. an
# XDG-style `~/.local/share/<app>`) rather than anything inside the
# cloned repo -- a real, deliberate app behaviour, not something to work
# around. A runner whose "env" references {isolated_home} gets HOME
# pointed at this directory instead, reset fresh before every build the
# same way BUILD_DB_PATH is, so the app's own real resolution logic still
# runs untouched but always starts clean.
ISOLATED_HOME = config.OUTPUT_ROOT / "isolated_home"
MANIFEST_PATH = config.OUTPUT_ROOT / "build_manifest.json"
SERVER_LOG_PATH = config.OUTPUT_ROOT / "server.log"
SMTP_LOG_PATH = config.OUTPUT_ROOT / "smtp_debug.log"
LAUNCHER_PATH = config.OUTPUT_ROOT / "_launch_server.py"
READY_TIMEOUT_SECONDS = 20
# ----------------------------------------------------------------------------


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _harvested_body_only(impl_path: Path) -> str:
    text = impl_path.read_text(encoding="utf-8")
    marker = "\n\n"
    idx = text.index(marker)
    return text[idx + len(marker):].rstrip("\n")


def verify(cap_id: str):
    registry_path = config.REGISTRY_ROOT / f"{cap_id}.json"
    if not registry_path.exists():
        raise SystemExit(f"ABORT: {registry_path} not found -- run shelf_records.py first")
    registry = config.load_json(registry_path)
    impl_meta = registry["implementations"][0]

    provenance = config.load_json(config.PROJECT_ROOT / impl_meta["provenance_path"])
    shelf_dir = config.PROJECT_ROOT / impl_meta["shelf_path"]
    impl_path = shelf_dir / "implementation.py"

    harvested_body = _harvested_body_only(impl_path)
    shelf_integrity_ok = _sha256_text(harvested_body) == provenance["checksums"]["harvested_source_sha256"]

    app_slug = provenance["application"]["slug"]
    applications = {a["slug"]: a for a in config.load_json(config.REPOSITORY_SOURCE)["applications"]}
    app_record = applications[app_slug]
    live_source_path = Path(app_record["cloned_path"]) / provenance["source"]["file"]
    live_source_text = live_source_path.read_text(encoding="utf-8")
    live_tree = ast.parse(live_source_text, filename=str(live_source_path))

    live_node = None
    for node in ast.walk(live_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == provenance["source"]["symbol"]:
            live_node = node
            break

    drift_detected = True
    live_matches_shelf = False
    if live_node is not None:
        live_segment = ast.get_source_segment(live_source_text, live_node)
        drift_detected = live_node.lineno != provenance["source"]["lineno"]
        live_matches_shelf = (live_segment == harvested_body)

    return {
        "cap_id": cap_id,
        "app_slug": app_slug,
        "shelf_integrity_ok": shelf_integrity_ok,
        "live_symbol_found": live_node is not None,
        "live_lineno_drift_detected": drift_detected,
        "live_source_matches_shelf": live_matches_shelf,
        "commit_at_harvest": provenance["application"]["commit"],
        "cloned_path": app_record["cloned_path"],
        "runner": app_record["runner"],
        "verified": shelf_integrity_ok and live_node is not None and live_matches_shelf,
    }


FLASK_MODULE_ATTR_LAUNCHER = """
import sys
sys.path.insert(0, {app_dir!r})
from {app_module} import {app_attr} as application
if __name__ == "__main__":
    application.run(host={host!r}, port={port}, debug=False, use_reloader=False)
"""

FLASK_FACTORY_LAUNCHER = """
import os
import sys
sys.path.insert(0, {app_dir!r})
{env_lines}
from {factory_module} import {factory_func}
application = {factory_func}()
if __name__ == "__main__":
    application.run(host={host!r}, port={port}, debug=False, use_reloader=False)
"""

SMTP_DEBUG_LAUNCHER = """
import smtpd
import asyncore
server = smtpd.DebuggingServer(('127.0.0.1', {smtp_port}), None)
asyncore.loop()
"""


def _reset_files(cloned_path: Path, reset_globs):
    for pattern in reset_globs or []:
        for match in glob.glob(str(cloned_path / pattern)):
            Path(match).unlink()
            print(f"  reset: removed stale {match}")


def _resolve_python(runner: dict) -> Path:
    version = runner.get("python_version", "3.11")
    python_exe = PYTHON_BY_VERSION.get(version)
    if python_exe is None:
        raise SystemExit(f"ABORT: unknown python_version {version!r} in runner config -- add it to PYTHON_BY_VERSION")
    if not python_exe.exists():
        raise SystemExit(f"ABORT: {python_exe} not found -- create that venv and install the app's deps first")
    return python_exe


def _resolve_env(runner: dict) -> dict:
    """The same env overrides the launched server gets (e.g. DATABASE_URL
    pointing at a fresh BUILD_DB_PATH), formatted once so setup scripts
    that touch the same database agree with the server on where it is."""
    return {
        k: v.format(db_path=str(BUILD_DB_PATH), smtp_host="127.0.0.1", smtp_port=SMTP_DEBUG_PORT, isolated_home=str(ISOLATED_HOME))
        for k, v in runner.get("env", {}).items()
    }


def _run_setup_scripts(cloned_path: Path, setup_scripts, python_exe: Path, env_overrides: dict):
    for script in setup_scripts or []:
        print(f"  setup: running {script}")
        # "-m package.module" runs it the way `python -m` does: sys.path[0]
        # is the cwd, not the script's own directory. Some apps' scripts
        # (e.g. one that does `from wsgi import app` where wsgi.py itself
        # does `from app import create_app`, expecting the REPO ROOT on
        # sys.path) only import correctly that way -- running them as a
        # bare script path puts the script's own directory on sys.path[0]
        # instead, which is a real, different Python behaviour, not a bug
        # to work around with sys.path hacks.
        if script.startswith("-m "):
            argv = [str(python_exe), "-m", script[len("-m "):]]
        elif script.startswith("-c "):
            argv = [str(python_exe), "-c", script[len("-c "):]]
        else:
            argv = [str(python_exe), script]
        result = subprocess.run(
            argv, cwd=str(cloned_path), capture_output=True, text=True,
            env={**os.environ, **env_overrides},
        )
        if result.returncode != 0:
            raise SystemExit(
                f"ABORT: setup script {script} failed (exit {result.returncode})\n"
                f"stdout={result.stdout}\nstderr={result.stderr}"
            )


def _prepare_launch(runner: dict, cloned_path: Path, host: str, port: int, python_exe: Path):
    """
    Returns (argv, cwd, actual_host, actual_port). `cloned_path` here is
    already app_subdir-adjusted by the caller (start()) -- some real apps
    put their actual application root in a subdirectory (e.g. backend/
    next to a separate frontend/), where the app's own modules use bare
    relative imports (`from database import db`) that only resolve with
    that subdirectory itself on sys.path/cwd, not the repo root.
    """
    kind = runner["kind"]

    if kind == "flask_module_attr":
        launcher = FLASK_MODULE_ATTR_LAUNCHER.format(
            app_dir=str(cloned_path), app_module=runner["app_module"], app_attr=runner.get("app_attr", "app"),
            host=host, port=port,
        )
        LAUNCHER_PATH.write_text(launcher, encoding="utf-8")
        return [str(python_exe), str(LAUNCHER_PATH)], str(cloned_path), host, port

    if kind == "flask_factory":
        env_lines = "\n".join(f'os.environ[{k!r}] = {v!r}' for k, v in _resolve_env(runner).items())
        launcher = FLASK_FACTORY_LAUNCHER.format(
            app_dir=str(cloned_path), env_lines=env_lines,
            factory_module=runner["factory_module"], factory_func=runner["factory_func"],
            host=host, port=port,
        )
        LAUNCHER_PATH.write_text(launcher, encoding="utf-8")
        return [str(python_exe), str(LAUNCHER_PATH)], str(cloned_path), host, port

    if kind == "script_entrypoint":
        entry = cloned_path / runner["entry_script"]
        actual_host = runner.get("known_host", host)
        actual_port = runner.get("known_port", port)
        return [str(python_exe), str(entry)], str(cloned_path), actual_host, actual_port

    raise SystemExit(f"ABORT: unknown runner kind {kind!r}")


def start(cap_id: str, host: str, port: int):
    config.ensure_dirs()
    config.print_roots(__file__)

    result = verify(cap_id)
    print(f"Verification for {cap_id}:")
    for k, v in result.items():
        print(f"  {k:28s} = {v}")
    if not result["verified"]:
        raise SystemExit("ABORT: verification failed -- refusing to build/start an unverified composition")

    runner = result["runner"]
    # Applied once, here: reset/setup/launch must all agree on the app's
    # real root, which for some apps is a subdirectory (see app_subdir in
    # _prepare_launch's docstring) -- not the repo root harvest_parts.py
    # and detect_capability.py use for provenance.
    cloned_path = Path(result["cloned_path"]) / runner.get("app_subdir", "")
    python_exe = _resolve_python(runner)

    if BUILD_DB_PATH.exists():
        BUILD_DB_PATH.unlink()
    if "{isolated_home}" in str(runner.get("env", {}).values()):
        import shutil
        if ISOLATED_HOME.exists():
            shutil.rmtree(ISOLATED_HOME)
        ISOLATED_HOME.mkdir(parents=True)
    _reset_files(cloned_path, runner.get("reset_globs"))
    _run_setup_scripts(cloned_path, runner.get("setup_scripts"), python_exe, _resolve_env(runner))

    smtp_proc = None
    if runner.get("needs_smtp"):
        smtp_launcher_path = config.OUTPUT_ROOT / "_launch_smtp_debug.py"
        smtp_launcher_path.write_text(SMTP_DEBUG_LAUNCHER.format(smtp_port=SMTP_DEBUG_PORT), encoding="utf-8")
        smtp_log_fh = open(SMTP_LOG_PATH, "w", encoding="utf-8")
        smtp_proc = subprocess.Popen([str(VENV_PYTHON), str(smtp_launcher_path)], stdout=smtp_log_fh, stderr=subprocess.STDOUT)
        time.sleep(0.5)

    argv, cwd, actual_host, actual_port = _prepare_launch(runner, cloned_path, host, port, python_exe)

    log_fh = open(SERVER_LOG_PATH, "w", encoding="utf-8")
    proc = subprocess.Popen(argv, stdout=log_fh, stderr=subprocess.STDOUT, cwd=cwd)

    manifest = {
        "cap_id": cap_id,
        "host": actual_host,
        "port": actual_port,
        "pid": proc.pid,
        "smtp_debug_pid": smtp_proc.pid if smtp_proc else None,
        "smtp_debug_port": SMTP_DEBUG_PORT if smtp_proc else None,
        "verification": result,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "server_log": str(SERVER_LOG_PATH),
        "smtp_debug_log": str(SMTP_LOG_PATH) if smtp_proc else None,
        "db_path": str(BUILD_DB_PATH) if runner["kind"] == "flask_factory" else None,
    }
    config.write_json(MANIFEST_PATH, manifest)

    readiness_path = runner.get("readiness_path", "/")
    deadline = time.time() + READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{actual_host}:{actual_port}{readiness_path}", timeout=1)
            print(f"Composed app is up: http://{actual_host}:{actual_port}  (pid={proc.pid})")
            return 0
        except urllib.error.HTTPError:
            print(f"Composed app is up (non-200 on {readiness_path}, but responding): http://{actual_host}:{actual_port}  (pid={proc.pid})")
            return 0
        except urllib.error.URLError:
            time.sleep(0.3)
    raise SystemExit(f"ABORT: server did not become ready within {READY_TIMEOUT_SECONDS}s -- see {SERVER_LOG_PATH}")


def stop():
    if not MANIFEST_PATH.exists():
        print("No build manifest -- nothing to stop.")
        return 0
    manifest = config.load_json(MANIFEST_PATH)
    for key in ("pid", "smtp_debug_pid"):
        pid = manifest.get(key)
        if pid is None:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped {key}={pid}")
        except ProcessLookupError:
            print(f"{key}={pid} was already gone")
    return 0


def status():
    if not MANIFEST_PATH.exists():
        print("No build manifest.")
        return 1
    manifest = config.load_json(MANIFEST_PATH)
    pid = manifest["pid"]
    alive = False
    try:
        os.kill(pid, 0)
        alive = True
    except ProcessLookupError:
        alive = False
    print(json.dumps({**manifest, "alive": alive}, indent=2))
    return 0 if alive else 1


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_start = sub.add_parser("start")
    p_start.add_argument("--cap", default="CAP-0001")
    p_start.add_argument("--host", default=DEFAULT_HOST)
    p_start.add_argument("--port", type=int, default=5057)
    sub.add_parser("stop")
    sub.add_parser("status")
    args = parser.parse_args()

    if args.command == "start":
        return start(args.cap, args.host, args.port)
    if args.command == "stop":
        return stop()
    if args.command == "status":
        return status()


if __name__ == "__main__":
    sys.exit(main())
