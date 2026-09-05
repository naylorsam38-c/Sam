#!/usr/bin/env python3
"""run_seams.py — the shelf's own seam journeys, run against every built
family in turn (each on its own fresh server), writing qualification receipts
for the parts whose journeys PASS. Usage: python run_seams.py [family ...]"""
import os, subprocess, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_families import FAMILIES, PORTS
SEAMS = os.path.join(HERE, "..", "playwright-tester", "seams.py")

def main(argv):
    rc = 0
    for family in (argv or FAMILIES):
        app = os.path.join(HERE, "build", family, "app"); db = os.path.join(app, "app.db")
        if os.path.exists(db): os.remove(db)
        port = PORTS[family] + 100
        proc = subprocess.Popen(["python3", "app.py"], cwd=app, env=dict(os.environ, PORT=str(port)), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                try: urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1); break
                except Exception: time.sleep(0.1)
            print(f"=== {family}")
            r = subprocess.run([sys.executable, SEAMS, os.path.join(HERE, "build", family, "SPEC.json"), "--base-url", f"http://127.0.0.1:{port}",
                                "--app-dir", app, "-o", os.path.join(HERE, "evidence", "seams", family)], capture_output=True, text=True, timeout=900)
            print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if l.strip()))
            rc = rc or r.returncode
        finally:
            proc.terminate(); proc.wait(timeout=5)
    return rc

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
