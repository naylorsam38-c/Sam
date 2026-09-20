#!/usr/bin/env python3
"""teardown.py — stop and remove every container left running by
install_startup.py for the screens/capabilities stages, and prune the images
built along the way so disk doesn't fill up across 52 apps. Run once after
capabilities.py finishes."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE_FILE = HERE / "live_containers.json"


def run(argv, timeout=300):
    try:
        subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except Exception:
        pass


def main():
    if not LIVE_FILE.exists():
        print("no live_containers.json - nothing to tear down")
        return
    live = json.loads(LIVE_FILE.read_text())
    for entry in live:
        project = entry["project"]
        print(f"tearing down {entry['app_id']} (project {project})")
        run(["docker", "compose", "-p", project, "down", "-v", "-t", "5"])
        run(["docker", "rm", "-f", "-t", "5", project])
    run(["docker", "image", "prune", "-af"], timeout=600)
    print(f"torn down {len(live)} app(s)")


if __name__ == "__main__":
    main()
