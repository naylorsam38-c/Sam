#!/usr/bin/env python3
"""
serve.py — the front door, running.

Serves the eight-question page, and when the person presses "Build it" it
really builds: their answers -> a complete instance -> the real checker ->
the numbered spec -> a real running app -> the three interfaces -> a
plain-English summary. Then it starts their app on its own port and hands
them the link.

Nothing is faked and nothing is queued: if the build refuses, the page shows
the refusal in the same words the chain used, and nothing half-built is left.

Stdlib only, like everything else the builder produces.

Usage:
  python serve.py                 # http://127.0.0.1:8700
  python serve.py --port 8700 --apps-from 8901
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
BUILT = os.path.join(HERE, "built")
sys.path.insert(0, HERE)
import catalogue as cat   # noqa: E402
import intake             # noqa: E402
import assemble as ae     # noqa: E402  (intake put it on the path)
import builder as bl      # noqa: E402

STATE = {"next_port": 8901, "apps": {}}
LOCK = threading.Lock()


def _start_app(app_dir, port):
    """Runs the app the person just had built, on its own port, and waits for it
    to really answer before the link is handed over."""
    proc = subprocess.Popen(["python3", "app.py"], cwd=app_dir, env=dict(os.environ, PORT=str(port)),
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            return proc
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("the app was built but did not start")


def do_build(answers):
    name = answers.get("name") or "app"
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-") or "app"
    with LOCK:
        port = STATE["next_port"]
        STATE["next_port"] += 1
    out = os.path.join(BUILT, f"{slug}-{port}")
    spec, app_dir, result, filled = intake.run(answers, out, port=port)
    proc = _start_app(app_dir, port)
    with LOCK:
        STATE["apps"][port] = proc
    bm = spec["build_model"]
    return {
        "name": name,
        "records": len(result["records_built"]),
        "screens": result["screens_built"],
        "actions": len(bm["actions_inventory"]),
        "filled": len(filled),
        "open": f"http://127.0.0.1:{port}/",
        "summary": f"/built/{os.path.basename(out)}/YOUR_APP.md",
        "dir": out,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        try:
            return json.loads(self.rfile.read(n)) if n else {}
        except Exception:
            return {}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            return self._send(200, open(os.path.join(WEB, "index.html"), encoding="utf-8").read(), "text/html; charset=utf-8")
        if path == "/api/catalogue":
            return self._send(200, cat.as_json())
        if path.startswith("/shots/"):
            fp = os.path.join(WEB, "shots", os.path.basename(path))
            if not os.path.isfile(fp):
                return self._send(404, {"error": "no such picture"})
            body = open(fp, "rb").read()
            self.send_response(200); self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body))); self.end_headers()
            return self.wfile.write(body)
        if path.startswith("/built/"):
            fp = os.path.join(BUILT, *path[len("/built/"):].split("/"))
            if not os.path.abspath(fp).startswith(os.path.abspath(BUILT)) or not os.path.isfile(fp):
                return self._send(404, {"error": "not found"})
            return self._send(200, open(fp, encoding="utf-8").read(), "text/plain; charset=utf-8")
        return self._send(404, {"error": "no route"})

    def do_POST(self):
        if self.path == "/api/questions":
            return self._send(200, {"questions": intake.questions(self._body())})
        if self.path == "/api/build":
            answers = self._body()
            try:
                return self._send(200, do_build(answers))
            except (intake.IntakeRefused, ae.Refused, bl.BuildRefused) as e:
                return self._send(200, {"error": str(e)})
            except Exception as e:                      # a real fault, not a refusal
                return self._send(200, {"error": f"{type(e).__name__}: {e}"})
        return self._send(404, {"error": "no route"})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8700)
    ap.add_argument("--apps-from", type=int, default=8901)
    args = ap.parse_args(argv)
    STATE["next_port"] = args.apps_from
    os.makedirs(BUILT, exist_ok=True)
    cat.verify()
    print(f"front door on http://127.0.0.1:{args.port}   (apps will start from {args.apps_from})")
    try:
        ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        for p in STATE["apps"].values():
            p.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
