#!/usr/bin/env python3
"""
build.py — Build / Adapter stage.

Consumes a REGISTERED capability (capabilities/<CAP-ID>.json) and produces a
real, running composed application -- not a simulation, not a stand-in.

What "verified composition" means in this walking skeleton (documented
honestly, see README "What this proves vs. what's next"): it does not yet
graft a harvested route onto an unrelated host application (that needs the
dependency-binding/adapter system referenced in the handoff as future work).
What it DOES do, for real, every run:

  1. Integrity-checks the shelf record itself (the harvested text on disk
     still hashes to what PROVENANCE.json says was harvested).
  2. Re-extracts the same function from the live application checkout,
     right now, the same way harvest_parts.py did, and requires it to be
     BYTE-IDENTICAL to the shelved copy -- if the live source has drifted
     since harvest, this is reported, not silently ignored.
  3. Only then imports the application's own create_app() factory and
     starts a real Flask dev server, so the exact, verified, harvested
     route is what a live HTTP/Playwright test below actually exercises.

Run:
    python3 build.py start --cap CAP-0001
    python3 build.py status
    python3 build.py stop
"""

import argparse
import ast
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5057
SMTP_DEBUG_PORT = 1025  # a real local SMTP server the composed app really talks to (see note below)
VENV_PYTHON = config.PROJECT_ROOT / ".venv" / "bin" / "python3"
BUILD_DB_PATH = config.OUTPUT_ROOT / "build_run.db"  # fresh SQLite file for each build, never the vendored one
MANIFEST_PATH = config.OUTPUT_ROOT / "build_manifest.json"
SERVER_LOG_PATH = config.OUTPUT_ROOT / "server.log"
SMTP_LOG_PATH = config.OUTPUT_ROOT / "smtp_debug.log"
LAUNCHER_PATH = config.OUTPUT_ROOT / "_launch_server.py"
# The harvested capability (export data) has nothing to do with email, but
# registering a user (a real prerequisite of reaching /export, since it's
# @login_required) triggers this app's own real send_welcome_email() call.
# This sandbox has no route to the public internet's SMTP ports, so pointing
# MAIL_SERVER at smtp.gmail.com (the app's default) means every registration
# blocks for a real multi-second TCP connect timeout before giving up.
# Rather than mock or skip that code path, we run a real local SMTP debug
# server (Python's own stdlib smtpd.DebuggingServer) and point the app's
# real MAIL_SERVER/MAIL_PORT/MAIL_USE_TLS env vars at it -- flask-mail still
# performs a genuine SMTP conversation, it just terminates locally instead of
# at Gmail. The received message is logged for real to smtp_debug.log.
# ----------------------------------------------------------------------------


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _harvested_body_only(impl_path: Path) -> str:
    """implementation.py is a provenance header + blank line + verbatim body."""
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
        "verified": shelf_integrity_ok and live_node is not None and live_matches_shelf,
    }


LAUNCHER_TEMPLATE = """
import os
import sys
sys.path.insert(0, {app_dir!r})
os.environ["DATABASE_URL"] = "sqlite:///{db_path}"
os.environ["FLASK_SECRET_KEY"] = "capability-harvest-build-run"
os.environ["MAIL_SERVER"] = {smtp_host!r}
os.environ["MAIL_PORT"] = "{smtp_port}"
os.environ["MAIL_USE_TLS"] = "false"
os.environ["MAIL_USE_SSL"] = "false"
from app import create_app
application = create_app()
if __name__ == "__main__":
    application.run(host={host!r}, port={port}, debug=False, use_reloader=False)
"""

SMTP_DEBUG_LAUNCHER = """
import smtpd
import asyncore
server = smtpd.DebuggingServer(('127.0.0.1', {smtp_port}), None)
asyncore.loop()
"""


def start(cap_id: str, host: str, port: int):
    config.ensure_dirs()
    config.print_roots(__file__)

    result = verify(cap_id)
    print(f"Verification for {cap_id}:")
    for k, v in result.items():
        print(f"  {k:28s} = {v}")
    if not result["verified"]:
        raise SystemExit("ABORT: verification failed -- refusing to build/start an unverified composition")

    if BUILD_DB_PATH.exists():
        BUILD_DB_PATH.unlink()  # fresh database for every build, never reuse stale state

    if not VENV_PYTHON.exists():
        raise SystemExit(f"ABORT: {VENV_PYTHON} not found -- create the venv and install the app's deps first")

    smtp_launcher_path = config.OUTPUT_ROOT / "_launch_smtp_debug.py"
    smtp_launcher_path.write_text(SMTP_DEBUG_LAUNCHER.format(smtp_port=SMTP_DEBUG_PORT), encoding="utf-8")
    smtp_log_fh = open(SMTP_LOG_PATH, "w", encoding="utf-8")
    smtp_proc = subprocess.Popen(
        [str(VENV_PYTHON), str(smtp_launcher_path)],
        stdout=smtp_log_fh, stderr=subprocess.STDOUT,
    )
    time.sleep(0.5)  # let the SMTP debug server bind its port before the app tries to talk to it

    launcher = LAUNCHER_TEMPLATE.format(
        app_dir=result["cloned_path"], db_path=str(BUILD_DB_PATH), host=host, port=port,
        smtp_host="127.0.0.1", smtp_port=SMTP_DEBUG_PORT,
    )
    LAUNCHER_PATH.write_text(launcher, encoding="utf-8")

    log_fh = open(SERVER_LOG_PATH, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(VENV_PYTHON), str(LAUNCHER_PATH)],
        stdout=log_fh, stderr=subprocess.STDOUT,
        cwd=str(Path(result["cloned_path"])),
    )

    manifest = {
        "cap_id": cap_id,
        "host": host,
        "port": port,
        "pid": proc.pid,
        "smtp_debug_pid": smtp_proc.pid,
        "smtp_debug_port": SMTP_DEBUG_PORT,
        "verification": result,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "server_log": str(SERVER_LOG_PATH),
        "smtp_debug_log": str(SMTP_LOG_PATH),
        "db_path": str(BUILD_DB_PATH),
    }
    config.write_json(MANIFEST_PATH, manifest)

    # Poll for real readiness rather than sleeping a guessed duration.
    import urllib.request
    import urllib.error
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{host}:{port}/login", timeout=1)
            print(f"Composed app is up: http://{host}:{port}  (pid={proc.pid})")
            return 0
        except urllib.error.URLError:
            time.sleep(0.3)
        except Exception:
            time.sleep(0.3)
    raise SystemExit(f"ABORT: server did not become ready within 20s -- see {SERVER_LOG_PATH}")


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
    p_start.add_argument("--port", type=int, default=DEFAULT_PORT)
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
