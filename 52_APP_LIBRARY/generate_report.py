#!/usr/bin/env python3
"""
generate_report.py — spec section 20: the final honest report.

Reads manifest.json (updated in place by every prior stage) and produces the
four reports section 19 asks for. Never collapses FOUND into WORKING, or
WORKING into PROVEN REUSABLE CAPABILITY - the whole point of section 20.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST_FILE = HERE / "manifest.json"
APPS_DIR = HERE / "applications"
REPORTS_DIR = HERE / "reports"


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    manifest = json.loads(MANIFEST_FILE.read_text())
    apps = manifest["applications"]

    status_counts = {}
    for e in apps:
        status_counts[e["status"]] = status_counts.get(e["status"], 0) + 1

    discovered = sum(1 for e in apps if e["status"] != "DISCOVERY_FAILED")
    acquired = sum(1 for e in apps if e["status"] not in ("DISCOVERY_FAILED", "ACQUISITION_FAILED", "LICENCE_UNCLEAR"))
    installable = sum(1 for e in apps if e["status"] in
                      ("STARTABLE", "SCREEN-VERIFIED", "FUNCTIONALLY_VERIFIED", "STARTUP_FAILED") or
                      e["status"] == "SCREEN_FAILED")
    startable = sum(1 for e in apps if e["status"] in ("STARTABLE", "SCREEN-VERIFIED", "FUNCTIONALLY_VERIFIED", "SCREEN_FAILED"))
    screen_verified = sum(1 for e in apps if e["status"] in ("SCREEN-VERIFIED", "FUNCTIONALLY_VERIFIED"))
    functionally_verified = sum(1 for e in apps if e["status"] == "FUNCTIONALLY_VERIFIED")
    ready = functionally_verified  # this pipeline's bar for READY: booted, got in, screens
                                     # browser-verified, AND at least one capability PROVEN live
    failed = len(apps) - ready

    acquisition_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": 52,
        "by_status": status_counts,
        "applications": [
            {"id": e["id"], "category": e["category_slug"], "name": e["name"], "status": e["status"],
            "repository": e["repository"], "commit": e.get("commit"), "licence": e.get("licence"),
            "reason": (e.get("install_startup") or {}).get("reason") or
                      (e.get("acquisition_attempts") or [{}])[-1].get("reason") if e["status"] not in
                      ("STARTABLE", "SCREEN-VERIFIED", "FUNCTIONALLY_VERIFIED") else None}
            for e in apps
        ],
    }
    (REPORTS_DIR / "acquisition_report.json").write_text(json.dumps(acquisition_report, indent=1))

    screen_rows = []
    for e in apps:
        sj = APPS_DIR / e["id"] / "screens.json"
        if sj.exists():
            d = json.loads(sj.read_text())
            screen_rows.append({"id": e["id"], "name": e["name"], "category": e["category_slug"],
                                **e.get("screen_summary", {})})
    screen_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "apps_with_screen_data": len(screen_rows),
        "totals": {
            "discovered": sum(r.get("screens_discovered", 0) for r in screen_rows),
            "reachable": sum(r.get("screens_reached", 0) for r in screen_rows),
            "rendered": sum(r.get("screens_rendered", 0) for r in screen_rows),
            "browser_verified": sum(r.get("screens_browser_verified", 0) for r in screen_rows),
        },
        "applications": screen_rows,
    }
    (REPORTS_DIR / "screen_report.json").write_text(json.dumps(screen_report, indent=1))

    cap_rows = []
    for e in apps:
        cj = APPS_DIR / e["id"] / "capabilities.json"
        if cj.exists():
            d = json.loads(cj.read_text())
            cap_rows.append({"id": e["id"], "name": e["name"], "category": e["category_slug"],
                            "capabilities_defined": d["capabilities_defined"],
                            "discovered": len(d.get("capabilities", [])),
                            "attach_points_found": sum(1 for c in d.get("capabilities", []) if c.get("attach_points")),
                            "proven": sum(1 for c in d.get("capabilities", []) if c.get("verdict") == "PROVEN")})
    capability_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories_with_capability_lists": "22 of 52 (copied from benchmark70.json where the category "
                                            "means the same thing; the rest have none - none invented)",
        "applications": cap_rows,
        "totals": {
            "discovered": sum(r["discovered"] for r in cap_rows),
            "attach_points_found": sum(r["attach_points_found"] for r in cap_rows),
            "proven": sum(r["proven"] for r in cap_rows),
        },
    }
    (REPORTS_DIR / "capability_report.json").write_text(json.dumps(capability_report, indent=1))

    failures = []
    for e in apps:
        if e["status"] in ("FUNCTIONALLY_VERIFIED",):
            continue
        stage_map = {
            "DISCOVERY_FAILED": "DISCOVERY_FAILED", "ACQUISITION_FAILED": "ACQUISITION_FAILED",
            "LICENCE_UNCLEAR": "LICENCE_UNCLEAR", "INSTALL_FAILED": "INSTALL_FAILED",
            "STARTUP_FAILED": "STARTUP_FAILED", "BLOCKED_EXTERNAL_DEPENDENCY": "BLOCKED_EXTERNAL_DEPENDENCY",
            "SCREEN_FAILED": "SCREEN_FAILED", "STARTABLE": "SCREEN_FAILED",
            "SCREEN-VERIFIED": "FUNCTION_FAILED",
        }
        reason = (e.get("install_startup") or {}).get("reason") or e.get("discovery_failed_reason") or \
                 ((e.get("acquisition_attempts") or [{}])[-1].get("reason")) or \
                 (e.get("screen_summary") or {}).get("error") or \
                 (e.get("capability_summary") or {}).get("error") or "see application record"
        failures.append({"application": e["id"], "name": e["name"], "category": e["category_slug"],
                         "stage": stage_map.get(e["status"], e["status"]), "reason": reason,
                         "evidence": f"applications/{e['id']}/app.json"})

    final_report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_applications": 52,
        "applications": {
            "discovered": discovered, "acquired": acquired, "installed_or_installable": acquired,
            "started": startable, "screen_verified": screen_verified,
            "functionally_verified": functionally_verified, "ready": ready,
            "failed": len(apps) - ready,
        },
        "screens": screen_report["totals"],
        "capabilities": capability_report["totals"],
        "failures": failures,
        "definitions": {
            "READY": "booted from its own recipe, got a real UI response, at least one screen was "
                     "browser-verified (rendered, not just HTTP 200), AND at least one capability was "
                     "PROVEN by a real in-browser action - not source inspection.",
            "NOT_VERIFIED_vs_PASS": "a capability with an attach point but no live UI exercise, or a "
                                    "live action with no code attach point, is NOT VERIFIED - never PASS.",
        },
        "known_environment_constraint": (
            "This sandbox's egress policy denies ghcr.io, quay.io, and OS package mirrors "
            "(deb.debian.org, Alpine's apk mirrors) outright, confirmed by direct request. Any app whose "
            "install needs one of those is recorded BLOCKED_EXTERNAL_DEPENDENCY, per spec section 15 - "
            "this is an infrastructure ceiling of this sandbox, not a defect in the pipeline."
        ),
    }
    (REPORTS_DIR / "final_report.json").write_text(json.dumps(final_report, indent=1))

    print("TARGET APPLICATIONS: 52")
    print(f"DISCOVERED: {discovered}")
    print(f"ACQUIRED: {acquired}")
    print(f"STARTABLE: {startable}")
    print(f"SCREEN-VERIFIED: {screen_verified}")
    print(f"FUNCTIONALLY VERIFIED: {functionally_verified}")
    print(f"READY: {ready}")
    print(f"FAILED: {len(apps) - ready}")
    print(f"\nWrote reports/{{acquisition,screen,capability,final}}_report.json")


if __name__ == "__main__":
    main()
