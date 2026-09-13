#!/usr/bin/env python3
"""
bootstrap.py — deterministic, idempotent setup for a completely fresh
extraction of this project. Run it from anywhere; it locates everything it
needs relative to its own file location, never the current working
directory or any path specific to the original development workspace.

What it does, in order, printing exactly what happened at each step:
  1. Checks the Python version (3.9+; this codebase and its wheels were
     built and proven against 3.11).
  2. Installs Flask + Playwright + their full dependency trees from the
     vendored wheels in verification/vendor/wheels/ -- zero network access
     needed for this step, on Linux x86_64 + CPython 3.11. On any other
     platform, falls back to a normal networked `pip install` automatically
     (the vendored wheels include two platform-specific compiled packages
     that simply won't install elsewhere).
  3. Attempts to provide a real Chromium binary for Playwright's browser
     check. This is the one step that cannot be made to work with zero
     network access without vendoring a ~300-600MB browser binary into the
     repository -- which this project deliberately does not do, the same
     way no real project vendors a browser into its source tree. Tries, in
     order: (a) an existing PLAYWRIGHT_CHROMIUM_EXECUTABLE the caller
     already set, (b) a system Chromium/Chrome already on PATH, (c) a real
     network install via `playwright install chromium`. Reports plainly,
     not silently, if none of these work -- the caller then knows exactly
     what to do (see verification/README.md's "no network at all" section).

Exit code is 0 only if Python + the Python packages are ready. A missing
browser is reported but does not fail this script -- the verification
suite itself reports browser-dependent checks separately (see
run_full_verification.py), so a Python-only environment can still see
partial, honestly-labeled results instead of every step erroring out.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WHEELS = HERE / "vendor" / "wheels"
REQUIREMENTS = HERE / "requirements.txt"


def run(cmd, **kw):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, **kw)


def step(n, title):
    print(f"\n{'=' * 70}\nSTEP {n}: {title}\n{'=' * 70}")


def main():
    step(1, "Python version")
    print(f"python: {sys.executable}")
    print(f"version: {sys.version}")
    if sys.version_info < (3, 9):
        print("FAIL: Python 3.9+ required")
        return 1
    print("OK")

    step(2, "Install Flask + Playwright (Python packages)")
    ok = False
    if WHEELS.is_dir() and any(WHEELS.glob("*.whl")):
        res = run([sys.executable, "-m", "pip", "install", "--no-index",
                   f"--find-links={WHEELS}", "-r", str(REQUIREMENTS)])
        ok = res.returncode == 0
        if ok:
            print("OK -- installed from vendored wheels, zero network access used")
        else:
            print("Vendored wheels did not match this platform/Python version "
                  "(expected on anything but Linux x86_64 + CPython 3.11) -- "
                  "falling back to a normal networked pip install")
    if not ok:
        res = run([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        ok = res.returncode == 0
        print("OK -- installed from PyPI (network was used)" if ok
              else "FAIL -- could not install required Python packages either way")
    if not ok:
        return 1

    step(3, "Provide a real Chromium binary for Playwright")
    import os
    existing = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if existing and Path(existing).is_file():
        print(f"OK -- PLAYWRIGHT_CHROMIUM_EXECUTABLE already set and exists: {existing}")
    else:
        system_browser = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if system_browser:
            print(f"Found a system browser on PATH: {system_browser}")
            print(f"Set this before running verification scripts:")
            print(f"  export PLAYWRIGHT_CHROMIUM_EXECUTABLE={system_browser}")
        else:
            print("No PLAYWRIGHT_CHROMIUM_EXECUTABLE set and no system browser found on PATH.")
            print("Attempting a real network install of Playwright's own Chromium build...")
            res = run([sys.executable, "-m", "playwright", "install", "chromium"])
            if res.returncode == 0:
                print("OK -- Playwright's own Chromium installed; no environment variable needed, "
                      "build.py finds it automatically.")
            else:
                print("Could not install a browser (no network reachable to Playwright's own CDN). "
                      "Browser-dependent checks (the real Playwright UI journey) cannot run until "
                      "one is available. Everything else -- assembly, the compatibility gate, the "
                      "dependency-graph audit, and every HTTP-level functional check -- does not "
                      "need a browser and is unaffected. See verification/README.md.")

    print(f"\n{'=' * 70}\nBOOTSTRAP COMPLETE\n{'=' * 70}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
