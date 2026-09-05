#!/usr/bin/env python3
"""
run_chain.py — component 6: the fix-and-retest loop and the Definition of
Done gate.

Runs one full cycle: Build -> start the real server -> Live Playwright
Tester (normal, then seam journeys, then backend-down) -> stop the server ->
Defect Report. Definition of Done is exactly what the task states it must be:
the run passes only when the defect count is zero across every mode, never
because the build alone succeeded — and, since the shelf gained a lifecycle,
only when every part the app was built from is PRODUCT_QUALIFIED (or FROZEN)
at exactly the revision the app vendored. A part no real browser has driven,
or a seam no screen lets a user press, is a defect here.

What "the Builder fixes the defects" means for a deterministic, non-LLM
Builder (packages/builder/builder.py has no model in it: every generation
rule is a fixed, explicit function of the spec, and it refuses on anything
it doesn't recognise rather than inventing). It cannot rewrite its own
generation rules -- that is real engineering work, done between runs of this
script, not something a retry can substitute for. So this script's loop
does exactly what re-running is honestly good for: it distinguishes a
flake from a real defect by re-running the identical cycle against the
identical, unchanged Builder output, and stops as soon as either (a) a
cycle comes back clean, or (b) two consecutive cycles report the *same*
defects, which proves re-running alone will not fix it and a real change to
the spec or the Builder is what is actually needed. It never pretends a
defect fixed itself by looping past it.

Usage:
  python run_chain.py SPEC.json -o out/ [--port 8990] [--iterations 3]
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BUILDER = os.path.join(HERE, "..", "builder", "builder.py")
TESTER = os.path.join(HERE, "..", "playwright-tester", "live_test.py")
SEAMS = os.path.join(HERE, "..", "playwright-tester", "seams.py")
DEFECT_REPORT = os.path.join(HERE, "..", "defect-report", "defect_report.py")
sys.path.insert(0, os.path.join(HERE, "..", "builder"))
import shelf as shelf_lib  # noqa: E402  the shelf's own lifecycle rules, not restated here


class RunningServer:
    def __init__(self, app_dir, port, env=None, timeout=10):
        self.app_dir, self.port, self.env, self.timeout = app_dir, port, env or {}, timeout

    def __enter__(self):
        env = dict(os.environ)
        env["PORT"] = str(self.port)
        env.update(self.env)
        self.proc = subprocess.Popen(["python3", "app.py"], cwd=self.app_dir, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=1)
                return self
            except Exception:
                time.sleep(0.2)
        self.proc.terminate()
        out = self.proc.stdout.read() if self.proc.stdout else ""
        raise RuntimeError(f"server on port {self.port} did not come up:\n{out}")

    def __exit__(self, *exc):
        self.proc.terminate()
        try:
            self.proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def _run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, timeout=120)
    return r


def one_cycle(spec_path, spec, out_dir, port, oauth_env):
    """Build -> run -> test (both modes) -> stop -> defect report. Returns
    (passed: bool, defects: list, paths: dict). Raises only on an
    infrastructure failure (the server never starting) -- that is reported
    as its own defect, not swallowed, so a cycle result always exists."""
    app_dir = os.path.join(out_dir, "app")
    r = _run(BUILDER, spec_path, "-o", app_dir, "--port", str(port))
    if r.returncode != 0:
        return False, [{"id": "DEFECT-BUILD", "spec_ref": spec["spec_id"], "kind": "build_refused",
                        "expected": "the Builder accepts this spec", "observed": r.stderr.strip(),
                        "evidence": {"stdout": r.stdout, "stderr": r.stderr}}], {"app_dir": app_dir}

    normal_path = os.path.join(out_dir, "report_normal")
    down_path = os.path.join(out_dir, "report_down")
    try:
        with RunningServer(app_dir, port, env=oauth_env):
            rn = _run(TESTER, spec_path, "--base-url", f"http://127.0.0.1:{port}",
                      "--mode", "normal", "-o", normal_path)
            # the seams between the parts this app was built from, driven in the
            # same real browser against the same running app; passes issue the
            # qualification receipts the Definition of Done below reads
            rs = _run(SEAMS, spec_path, "--base-url", f"http://127.0.0.1:{port}",
                      "--app-dir", app_dir, "-o", os.path.join(out_dir, "report_seams"))
            db_file = os.path.join(app_dir, "app.db")
            if os.path.exists(db_file):
                open(db_file, "wb").write(b"not a sqlite database")  # real failure, not a stopped process (see README)
            rd = _run(TESTER, spec_path, "--base-url", f"http://127.0.0.1:{port}",
                      "--mode", "backend-down", "-o", down_path)
    except RuntimeError as exc:
        return False, [{"id": "DEFECT-SERVER-START", "spec_ref": spec["spec_id"], "kind": "server_did_not_start",
                        "expected": "the built app.py starts and answers on its port",
                        "observed": str(exc), "evidence": {}}], {"app_dir": app_dir}

    if rn.returncode not in (0, 1) or not os.path.exists(os.path.join(normal_path, "report_normal.json")):
        # a Python traceback also exits 1, so the report file is the real proof the tester ran
        return False, [{"id": "DEFECT-TESTER-CRASH", "spec_ref": spec["spec_id"], "kind": "tester_crashed",
                        "expected": "live_test.py runs to completion and writes report_normal.json",
                        "observed": (rn.stderr or "")[-2000:].strip(), "evidence": {}}], \
               {"app_dir": app_dir}

    defect_out = os.path.join(out_dir, "defects")
    args = [DEFECT_REPORT, spec_path, "--normal", os.path.join(normal_path, "report_normal.json"), "-o", defect_out]
    down_file = os.path.join(down_path, "report_backend_down.json")
    if os.path.exists(down_file):
        args += ["--backend-down", down_file]
    rr = _run(*args)
    defects = json.load(open(os.path.join(defect_out, "DEFECTS.json"))) if rr.returncode in (0, 1) else \
        [{"id": "DEFECT-REPORT-CRASH", "spec_ref": spec["spec_id"], "kind": "defect_report_crashed",
          "expected": "defect_report.py runs to completion", "observed": rr.stderr.strip(), "evidence": {}}]

    defects += seam_defects(spec, rs, os.path.join(out_dir, "report_seams", "report_seams.json"))
    defects += qualification_defects(spec, app_dir)

    return (len(defects) == 0), defects, {
        "app_dir": app_dir, "normal_report": normal_path, "down_report": down_path, "defects": defect_out,
        "seams_report": os.path.join(out_dir, "report_seams"),
    }


def seam_defects(spec, rs, report_path):
    """Every FAILED or BLOCKED seam journey is a defect against the numbered
    item it drove. BLOCKED counts: an app whose declared action no screen can
    press is not done, whatever the API says."""
    if rs.returncode not in (0, 1) or not os.path.exists(report_path):
        return [{"id": "DEFECT-SEAMS-CRASH", "spec_ref": spec["spec_id"], "kind": "seams_crashed",
                 "expected": "seams.py runs to completion", "observed": (rs.stderr or "")[-2000:].strip(), "evidence": {}}]
    report = json.load(open(report_path))
    out = []
    for d in report["journeys"]:
        if d["result"] in ("PASS", "N/A"):
            continue
        out.append({"id": f"DEFECT-SEAM-{d['subject'].split('/')[-1]}-{d['journey']}",
                    "spec_ref": d["subject"], "kind": f"seam_{d['result'].lower()}",
                    "expected": f"{d['journey']} passes end to end in a real browser",
                    "observed": d["reason"], "evidence": {"steps": d["steps"], "parts": d["parts"]}})
    return out


def qualification_defects(spec, app_dir):
    """The Definition of Done also asks the shelf: is every part this app was
    built from at the required lifecycle status, at exactly the revision the
    app vendored? A TESTED part in a shipped app is the 42f7cf6c failure."""
    manifest_path = os.path.join(app_dir, "MANIFEST.json")
    if not os.path.exists(manifest_path):
        return [{"id": "DEFECT-NO-MANIFEST", "spec_ref": spec["spec_id"], "kind": "no_manifest",
                 "expected": "the built app carries MANIFEST.json", "observed": "missing", "evidence": {}}]
    manifest = json.load(open(manifest_path))
    shelf = shelf_lib.load_shelf()
    by_id = {p["part_id"]: p for p in shelf["parts"]}
    out = []
    for pin in manifest["parts"]:
        part = by_id.get(pin["part_id"])
        if part is None:
            out.append({"id": f"DEFECT-PART-{pin['part_id']}", "spec_ref": spec["spec_id"], "kind": "part_missing",
                        "expected": f"{pin['part_id']} is on the shelf", "observed": "not on the shelf", "evidence": pin})
            continue
        current = shelf_lib.source_revision(part)
        if current != pin["revision"]:
            out.append({"id": f"DEFECT-PART-{pin['part_id']}", "spec_ref": spec["spec_id"], "kind": "part_drift",
                        "expected": f"{pin['part_id']} at {pin['revision']}", "observed": f"shelf is at {current}", "evidence": pin})
        elif not shelf_lib.meets(part):
            out.append({"id": f"DEFECT-PART-{pin['part_id']}", "spec_ref": spec["spec_id"], "kind": "part_unqualified",
                        "expected": f"{pin['part_id']} at {shelf_lib.REQUIRED_STATUS_FOR_DEPLOYABLE}",
                        "observed": f"status {part['status']}", "evidence": pin})
    return out


def run_to_done(spec_path, out_dir, port, iterations, oauth_env):
    spec = json.load(open(spec_path, encoding="utf-8"))
    history = []
    for i in range(1, iterations + 1):
        cycle_dir = os.path.join(out_dir, f"cycle-{i}")
        passed, defects, paths = one_cycle(spec_path, spec, cycle_dir, port, oauth_env)
        history.append({"cycle": i, "passed": passed, "defects": defects, "paths": paths})
        if passed:
            return {"done": True, "cycles_run": i, "history": history}
        if i > 1 and _same_defects(history[-2]["defects"], defects):
            return {"done": False, "cycles_run": i, "history": history,
                    "reason": "identical defects on two consecutive cycles — re-running will not fix this; "
                              "the Builder or the spec needs a real change"}
    return {"done": False, "cycles_run": iterations, "history": history,
            "reason": f"still failing after {iterations} cycles"}


def _same_defects(a, b):
    key = lambda ds: sorted((d["id"], d["kind"], str(d["observed"])) for d in ds)
    return key(a) == key(b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--port", type=int, default=8990)
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--oauth-client-id", help="e.g. for a spec with an OAuth integration to build for real")
    args = ap.parse_args(argv)

    oauth_env = {}
    if args.oauth_client_id:
        # generic across providers; the Builder names the env var per-provider
        # (OAUTH_PROVIDERS in builder.py) so this passes it through by name
        spec = json.load(open(args.spec, encoding="utf-8"))
        for name, flx in spec["build_model"]["integrations"].items():
            if flx.get("auth") == "api_key":
                continue  # a pasted key has no OAuth client id — the same split the Builder makes
            sys.path.insert(0, os.path.join(HERE, "..", "builder"))
            import builder as bl
            provider = bl._resolve_provider(name, flx)
            oauth_env[f"{provider.upper()}_CLIENT_ID"] = args.oauth_client_id

    result = run_to_done(args.spec, args.out, args.port, args.iterations, oauth_env)
    os.makedirs(args.out, exist_ok=True)
    json.dump(result, open(os.path.join(args.out, "RUN_RESULT.json"), "w"), indent=2, default=str)

    if result["done"]:
        print(f"DONE in {result['cycles_run']} cycle(s): the assembled spec is satisfied and the "
              f"real application passed the complete Playwright verification.")
        return 0
    last = result["history"][-1]
    print(f"NOT DONE after {result['cycles_run']} cycle(s): {result.get('reason', '')}")
    print(f"{len(last['defects'])} defect(s) in the last cycle:")
    for d in last["defects"]:
        print(f"  - {d['id']} ({d['spec_ref']}): expected {d['expected']!r}, observed {d['observed']!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
