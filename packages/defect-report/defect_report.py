#!/usr/bin/env python3
"""
defect_report.py — component 5: a precise defect report tied back to the
numbered spec, from the Live Playwright Tester's real reports.

Turns report_normal.json / report_backend_down.json (packages/playwright-tester)
into a list of defects, each naming the exact numbered id it traces back to
(SCR-nnn, ACT-nnn) with what the spec declared and what was actually
observed — evidence, not prose. This is what the fix-and-retest loop
(component 6) sends back to the Builder, and what closes a run at
Definition of Done: zero defects, not "the build succeeded."

No judgement calls here — every rule below is a direct, named comparison
between the spec's own declared value and the Playwright report's own
recorded value. Anything the reports don't cover is not reported on.

Usage:
  python defect_report.py SPEC.json --normal report_normal.json \\
                           [--backend-down report_backend_down.json] -o out/
"""

import argparse
import json
import os
import sys


def from_normal_report(spec, report):
    defects = []
    for screen in report.get("screens", []):
        sid = screen["screen_id"]
        if screen.get("status") not in (200, None) or "error" in screen:
            defects.append({
                "id": f"DEFECT-{sid}-LOAD",
                "spec_ref": sid,
                "kind": "screen_load_failed",
                "expected": "HTTP 200",
                "observed": screen.get("status") or screen.get("error"),
                "evidence": {"url": screen.get("url")},
            })
        for err in screen.get("console_errors", []):
            defects.append({
                "id": f"DEFECT-{sid}-CONSOLE-{len(defects)}",
                "spec_ref": sid,
                "kind": "console_error",
                "expected": "no console errors on load",
                "observed": err,
                "evidence": {"url": screen.get("url")},
            })
        for err in screen.get("page_errors", []):
            defects.append({
                "id": f"DEFECT-{sid}-PAGEERR-{len(defects)}",
                "spec_ref": sid,
                "kind": "page_error",
                "expected": "no uncaught page errors",
                "observed": err,
                "evidence": {"url": screen.get("url")},
            })
        for fr in screen.get("failed_requests", []):
            # A failed onward request to a third party (e.g. this sandbox's
            # own egress policy denying accounts.google.com) is not this
            # app's defect — see packages/playwright-tester/README.md. Only
            # a failed request to our own origin is reported.
            url = fr.get("url", "")
            if _same_origin(screen.get("url", ""), url):
                defects.append({
                    "id": f"DEFECT-{sid}-REQ-{len(defects)}",
                    "spec_ref": sid,
                    "kind": "failed_request",
                    "expected": "no failed same-origin requests",
                    "observed": fr.get("error"),
                    "evidence": {"url": url},
                })

    for v in report.get("actions_verified", []):
        if not v.get("verified"):
            defects.append({
                "id": f"DEFECT-{v['action_id']}-UNVERIFIED",
                "spec_ref": v["action_id"],
                "kind": "action_not_verified",
                "expected": "the declared action's endpoint responds as the spec requires",
                "observed": v.get("evidence"),
                "evidence": v,
            })

    for screen in report.get("screens", []):
        for c in screen.get("controls", []):
            if c.get("result") in ("control_not_found", "no_navigation", "no_302_response"):
                defects.append({
                    "id": f"DEFECT-{c['action_id']}-CONTROL",
                    "spec_ref": c["action_id"],
                    "kind": "control_not_actionable",
                    "expected": f"a real control for {c['action_id']} on {screen['screen_id']}",
                    "observed": c.get("result"),
                    "evidence": c,
                })

    return defects


def from_backend_down_report(report):
    defects = []
    for screen in report.get("screens", []):
        if not screen.get("passed"):
            defects.append({
                "id": f"DEFECT-{screen['screen_id']}-UNAVAILABLE-STATE",
                "spec_ref": screen["screen_id"],
                "kind": "unavailable_state_wrong",
                "expected": screen.get("expected_message"),
                "observed": screen.get("observed_text") or screen.get("error"),
                "evidence": screen,
            })
    return defects


def _same_origin(a, b):
    try:
        from urllib.parse import urlparse
        pa, pb = urlparse(a), urlparse(b)
        return pa.scheme == pb.scheme and pa.netloc == pb.netloc
    except Exception:
        return False


def render_markdown(spec, defects):
    if not defects:
        return f"# Defect report — {spec['spec_id']}\n\nNo defects. Every check the Live Playwright Tester ran passed.\n"
    out = [f"# Defect report — {spec['spec_id']}", "", f"{len(defects)} defect(s), each tied to a numbered spec id.", ""]
    for d in defects:
        out.append(f"## {d['id']} — {d['spec_ref']}")
        out.append(f"- kind: `{d['kind']}`")
        out.append(f"- expected: {d['expected']}")
        out.append(f"- observed: {d['observed']}")
        out.append(f"- evidence: `{json.dumps(d['evidence'], default=str)}`")
        out.append("")
    return "\n".join(out)


def build(spec, normal_report, backend_down_report=None):
    defects = from_normal_report(spec, normal_report)
    if backend_down_report is not None:
        defects += from_backend_down_report(backend_down_report)
    return defects


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--normal", required=True)
    ap.add_argument("--backend-down")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)

    spec = json.load(open(args.spec, encoding="utf-8"))
    normal_report = json.load(open(args.normal, encoding="utf-8"))
    backend_down_report = json.load(open(args.backend_down, encoding="utf-8")) if args.backend_down else None

    defects = build(spec, normal_report, backend_down_report)

    os.makedirs(args.out, exist_ok=True)
    json.dump(defects, open(os.path.join(args.out, "DEFECTS.json"), "w"), indent=2, default=str)
    open(os.path.join(args.out, "DEFECTS.md"), "w").write(render_markdown(spec, defects))

    print(f"{len(defects)} defect(s) -> {args.out}/")
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
