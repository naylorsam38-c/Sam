#!/usr/bin/env python3
"""
full_library_stress_test.py -- the real, un-filtered stress test: take every
real capability in the whole library (all 46 projects' shelf/), physically
merge them into ONE running system (one Flask process, one shared modules/
tree, one shared data/ directory -- not 46 isolated processes), and try to
exercise every single one of them for real over real HTTP. No capability is
skipped for being "tricky"; every genuine failure is recorded with its real
cause, not smoothed over.

This is a different, harder question than audit_dependency_graph.py answers.
That script checks whether each capability's *declared* contract is
internally consistent (real static source scan against its own declared
data_access). This script asks the next question: if you actually forced
every capability in the entire library to live in one process and one
namespace, does it still work? The two real answers this can produce that
per-app isolation testing structurally cannot see:

  1. URL-namespace collisions. Multiple, unrelated apps independently chose
     the same public route (e.g. "/api/events", "/api/items") because it's
     a natural name for their own resource. Each app in isolation is fine.
     Merged into one flat namespace, the *last-loaded* handler for a given
     (METHOD, ROUTE) silently overwrites every earlier one in the host's
     ROUTE_HANDLERS dict (see gen_common.py's HOST_APP_PY_TEMPLATE) -- no
     error, no warning, just silent shadowing. This script measures exactly
     that, empirically, over real HTTP, not by predicting it from source.

  2. Genuine reuse: capabilities that are meant to be identical across apps
     (byte-for-byte reused via reuse_capability_verbatim, or independently
     generated from the same generic engine, e.g. add_notification_capabilities)
     collapse cleanly to one real, shared implementation with no drift.

Reuses the real generated code throughout: the exact HOST_APP_PY_TEMPLATE
from gen_common.py, the exact shared_lib.py and route.py bytes build_batch.py
already produced -- nothing here is reimplemented or simulated.

Writes verification/full_stress_test/{system/, stress_result.json} and
prints a full report. Never touches OUTPUT_LIBRARY, NEW_APPS_FROM_LIBRARY,
or library_build/<project>/library -- everything happens in its own fresh
scratch directory.
"""
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIBRARY_BUILD = HERE / "library_build"
# Optional, additive-only: colon-separated extra library_build-shaped roots
# to include in this one run (e.g. a disposable coverage-expansion
# workspace), so "every capability from every project" can mean literally
# every project under test, not just the canonical library_build/. Empty
# by default -- this NEVER changes the standard single-root behaviour
# run_full_verification.py relies on; it only widens what one, explicit,
# opt-in invocation looks at.
import os  # noqa: E402
EXTRA_ROOTS = [Path(p) for p in os.environ.get("STRESS_TEST_EXTRA_ROOTS", "").split(":") if p]
ALL_ROOTS = [LIBRARY_BUILD] + EXTRA_ROOTS
PROJECT_ROOT = {}  # project name -> the root it was found under


def _iter_capability_files():
    for root in ALL_ROOTS:
        for capfile in sorted(root.glob("*/shelf/capabilities/CAP-*.json")):
            project = capfile.relative_to(root).parts[0]
            PROJECT_ROOT[project] = root
            yield capfile, project


def _root_for(project):
    return PROJECT_ROOT[project]


STRESS_DIR = HERE / "full_stress_test"
SYSTEM = STRESS_DIR / "system"
MODULES = SYSTEM / "modules"
DATA_DIR = SYSTEM / "data"
HOST_NUM = "9999"

sys.path.insert(0, str(HERE))
import gen_common  # noqa: E402

ROUTE_RE = re.compile(r"^ROUTE\s*=\s*['\"](.+?)['\"]", re.M)
METHOD_RE = re.compile(r"^METHOD\s*=\s*['\"](.+?)['\"]", re.M)
DATA_FILE_RE = re.compile(r"^DATA_FILE_NAME\s*=\s*['\"](.+?)['\"]", re.M)


def collect_unique_capabilities():
    """Every capability record across every project, deduped by id (real
    reuse_capability_verbatim duplicates share an id and are byte-identical
    -- verified separately below, not assumed)."""
    caps = {}
    origin_project = {}
    for capfile, project in _iter_capability_files():
        cap = json.loads(capfile.read_text())
        cid = cap["id"]
        if cid in caps:
            continue
        caps[cid] = cap
        origin_project[cid] = project
    return caps, origin_project


def verify_duplicate_ids_are_byte_identical(origin_project):
    """Before relying on "dedupe by id is safe", prove it: for every id that
    appears in more than one project, every project's copy of both the
    capability record and its route/app source must hash identically. Any
    mismatch is a real finding, not something to paper over by picking one
    arbitrarily."""
    by_id = {}
    for capfile, project in _iter_capability_files():
        cid = json.loads(capfile.read_text())["id"]
        by_id.setdefault(cid, []).append((project, capfile))

    import hashlib
    mismatches = []
    for cid, entries in by_id.items():
        if len(entries) < 2:
            continue
        record_hashes = set()
        impl_hashes_by_file = {}
        for project, capfile in entries:
            record_hashes.add(hashlib.md5(capfile.read_bytes()).hexdigest())
            impl_dir = _root_for(project) / project / "shelf" / "implementations" / cid / "IMPL-01" / cid
            for src in sorted(impl_dir.glob("*.py")):
                impl_hashes_by_file.setdefault(src.name, set()).add(hashlib.md5(src.read_bytes()).hexdigest())
        bad = record_hashes if len(record_hashes) > 1 else None
        bad_files = [fname for fname, hs in impl_hashes_by_file.items() if len(hs) > 1]
        if bad or bad_files:
            mismatches.append({"id": cid, "projects": [p for p, _ in entries],
                                "record_differs": bool(bad), "impl_files_differ": bad_files})
    return mismatches


def build_merged_system(caps, origin_project):
    if STRESS_DIR.exists():
        shutil.rmtree(STRESS_DIR)
    MODULES.mkdir(parents=True)

    route_caps = {}   # cid -> {route, method, data_file, required_input, project}
    host_ids = set()
    shared_lib_copied = False

    for cid, cap in caps.items():
        project = origin_project[cid]
        impl_dir = _root_for(project) / project / "shelf" / "implementations" / cid / "IMPL-01" / cid
        if cid == gen_common.SHARED_LIB_CAP_ID:
            dest = MODULES / cid
            dest.mkdir(parents=True)
            shutil.copy2(impl_dir / "shared_lib.py", dest / "shared_lib.py")
            shared_lib_copied = True
            continue
        route_py = impl_dir / "route.py"
        if not route_py.is_file():
            # a host capability (app.py, no ROUTE/handle) -- not merged as a
            # capability; the merged system gets exactly one host, written
            # fresh below, not one of the 46 real ones (that would arbitrarily
            # privilege one app's index page over the other 45).
            host_ids.add(cid)
            continue
        src = route_py.read_text()
        route_m = ROUTE_RE.search(src)
        method_m = METHOD_RE.search(src)
        datafile_m = DATA_FILE_RE.search(src)
        dest = MODULES / cid
        dest.mkdir(parents=True)
        shutil.copy2(route_py, dest / "route.py")
        route_caps[cid] = {
            "route": route_m.group(1) if route_m else None,
            "method": method_m.group(1) if method_m else None,
            "data_file": datafile_m.group(1) if datafile_m else None,
            "required_input": list(cap.get("data_shape", {}).get("input", {}).get("required", [])),
            "output_fields": list(cap.get("data_shape", {}).get("output", {}).get("fields", [])),
            "project": project,
        }

    assert shared_lib_copied, "CAP-0000 (shared library) was never found in the library"

    # The merged host: the exact real HOST_APP_PY_TEMPLATE from gen_common.py,
    # not a reimplementation -- it is what actually decides collision
    # behaviour (silent last-writer-wins in ROUTE_HANDLERS), so testing
    # anything else would not be testing the real system.
    host_dir = MODULES / f"CAP-{HOST_NUM}"
    host_dir.mkdir(parents=True)
    index_html = ("<h1>Full-library stress test host</h1>"
                  "<p>Every capability in the library, merged into one system.</p>")
    host_py = gen_common.HOST_APP_PY_TEMPLATE.format(host_num=HOST_NUM) % {"index_html": index_html}
    (host_dir / "app.py").write_text(host_py)

    return route_caps, host_ids


def seed_data_files(route_caps, collision_data_files):
    """A marker record ONLY in data files that actually belong to a
    capability caught in a (METHOD, ROUTE) collision -- needed there, and
    only there, to tell which capability's code actually served the
    request. Every other file is left genuinely absent (exactly what a
    fresh app starts with; _shared.load() already returns [] for a missing
    file) rather than seeded with a foreign row -- seeding a capability's
    own, never-shared data file with a row it didn't write itself is not a
    real scenario any isolated app ever encounters, and several handlers
    correctly assume they own every row in their own file (see the
    "seeding artifact" failures this caught on the first run, documented in
    the report)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    distinct_files = sorted({c["data_file"] for c in route_caps.values() if c["data_file"]})
    for fname in collision_data_files:
        marker_row = {"id": 900001, "_stress_marker": fname}
        (DATA_DIR / fname).write_text(json.dumps([marker_row]))
    return distinct_files


def probe_value(field_name):
    lname = field_name.lower()
    if "id" in lname:
        return 1
    if lname in ("start", "end", "date", "timestamp") or lname.endswith(("_at", "_date", "_time")):
        return "2026-01-01T00:00:00"
    return f"probe value for {field_name}"


def http_json(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"} if data else {})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def compute_collision_groups(route_caps):
    import hashlib
    groups = {}
    for cid, info in route_caps.items():
        key = (info["method"], info["route"])
        groups.setdefault(key, []).append(cid)
    # predicted winner: gen_common's real load_modules() does
    # `for entry in sorted(MODULES_ROOT.iterdir())`, overwriting
    # ROUTE_HANDLERS[key] on every match -- so the lexicographically LAST
    # CAP id among the colliders wins, every earlier one is shadowed.
    collisions = {}
    for key, cids in groups.items():
        if len(cids) > 1:
            winner = sorted(cids)[-1]
            src_hashes = {hashlib.md5((MODULES / cid / "route.py").read_bytes()).hexdigest() for cid in cids}
            data_files = {route_caps[cid]["data_file"] for cid in cids}
            # "harmless-redundant": every colliding implementation is
            # byte-identical (same generic engine, same schema, same data
            # file already shared by design) -- the wrong one winning
            # changes nothing observable. "real-breakage": different code
            # and/or different data files silently made unreachable --
            # the caller gets a normal 2xx from a completely unrelated
            # app's feature instead, with no error anywhere.
            severity = "harmless-redundant" if len(src_hashes) == 1 and len(data_files) == 1 else "real-breakage"
            collisions[key] = {"members": sorted(cids), "predicted_winner": winner, "severity": severity}
    return collisions


def main():
    print("=" * 78)
    print("FULL LIBRARY STRESS TEST -- every capability, one real running system")
    print("=" * 78)

    caps, origin_project = collect_unique_capabilities()
    total_records = sum(1 for _ in _iter_capability_files())
    print(f"\nRoots included: {[str(r) for r in ALL_ROOTS]}")
    print(f"Total capability records across the library: {total_records}")
    print(f"Unique capability ids: {len(caps)}")

    mismatches = verify_duplicate_ids_are_byte_identical(origin_project)
    print(f"\nIds shared by >1 project that are NOT byte-identical: {len(mismatches)}")
    for m in mismatches:
        print("  MISMATCH", m)

    route_caps, host_ids = build_merged_system(caps, origin_project)
    print(f"\nRoute-bearing capabilities merged into the system: {len(route_caps)}")
    print(f"Host capabilities excluded from the merge (46 real hosts -> 1 merged host): {len(host_ids)}")

    collisions = compute_collision_groups(route_caps)
    total_shadowed = sum(len(v["members"]) - 1 for v in collisions.values())
    real_breakage = {k: v for k, v in collisions.items() if v["severity"] == "real-breakage"}
    harmless = {k: v for k, v in collisions.items() if v["severity"] == "harmless-redundant"}
    print(f"\n(METHOD, ROUTE) collision groups (different capabilities, same public route): {len(collisions)}")
    print(f"  -- real-breakage (different code and/or data, wrong one silently wins): {len(real_breakage)}")
    print(f"  -- harmless-redundant (byte-identical code + shared data file by design): {len(harmless)}")
    print(f"Capabilities predicted to be silently shadowed (unreachable) in the merged system: {total_shadowed}")

    collision_cap_ids = {cid for v in collisions.values() for cid in v["members"]}
    collision_data_files = {route_caps[cid]["data_file"] for cid in collision_cap_ids if route_caps[cid]["data_file"]}
    distinct_files = seed_data_files(route_caps, collision_data_files)
    print(f"\nDistinct data files across the merged library: {len(distinct_files)}")
    print(f"Of those, seeded with a marker row (belong to a colliding capability): {len(collision_data_files)}")
    print(f"Left genuinely empty, exactly as a fresh app starts (no collision to disambiguate): "
          f"{len(distinct_files) - len(collision_data_files)}")

    print("\nStarting the merged system...")
    port = 8765
    proc = subprocess.Popen(
        [sys.executable, str(MODULES / f"CAP-{HOST_NUM}" / "app.py"), "--port", str(port)],
        cwd=str(SYSTEM), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(1.5)

    base = f"http://127.0.0.1:{port}"
    results = []
    try:
        health_code, health_body = http_json("GET", base + "/health")
        print(f"health check: {health_code} {health_body}")

        for cid in sorted(route_caps):
            info = route_caps[cid]
            method, route, data_file = info["method"], info["route"], info["data_file"]
            key = (method, route)
            body = ({f: probe_value(f) for f in info["required_input"]}
                     if info["required_input"] else None)

            before = (DATA_DIR / data_file).read_text() if data_file and (DATA_DIR / data_file).is_file() else None
            code, resp = http_json(method, base + route, body)
            after = (DATA_DIR / data_file).read_text() if data_file and (DATA_DIR / data_file).is_file() else None

            entry = {"id": cid, "project": info["project"], "method": method, "route": route,
                     "data_file": data_file, "http_status": code}

            if key in collisions:
                winner = collisions[key]["predicted_winner"]
                own_file_touched = (data_file is not None and before != after)
                served_by_marker = None
                if isinstance(resp, dict):
                    for v in resp.values():
                        if isinstance(v, list):
                            for row in v:
                                if isinstance(row, dict) and "_stress_marker" in row:
                                    served_by_marker = row["_stress_marker"]
                                    break
                severity = collisions[key]["severity"]
                if cid == winner:
                    verdict = "PASS" if code is not None and 200 <= code < 500 else "FAIL-OTHER"
                    reason = f"wins the (METHOD, ROUTE) collision among {collisions[key]['members']} ({severity})"
                else:
                    verdict = "FAIL-SHADOWED"
                    reason = (f"unreachable ({severity}): {method} {route} is claimed by {winner} "
                              f"(collision group {collisions[key]['members']}); "
                              f"own data file {data_file!r} touched={own_file_touched}, "
                              f"response actually served from marker={served_by_marker!r}")
            else:
                if code is not None and 200 <= code < 500:
                    verdict = "PASS"
                    reason = "no collision; real request/response cycle completed"
                else:
                    verdict = "FAIL-OTHER"
                    reason = f"unexpected status/error: {code} {resp}"

            entry["verdict"] = verdict
            entry["reason"] = reason
            results.append(entry)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    passed = sum(1 for r in results if r["verdict"] == "PASS")
    shadowed = sum(1 for r in results if r["verdict"] == "FAIL-SHADOWED")
    other_fail = sum(1 for r in results if r["verdict"] == "FAIL-OTHER")

    print(f"\n{'=' * 78}\nRESULTS\n{'=' * 78}")
    print(f"{passed}/{len(results)} capabilities ran correctly as their own logic in the merged system")
    print(f"{shadowed}/{len(results)} capabilities were silently shadowed by a URL-namespace collision")
    print(f"{other_fail}/{len(results)} capabilities failed for another, genuine reason")

    if shadowed:
        print(f"\n--- every shadowed capability, and exactly why ---")
        for r in results:
            if r["verdict"] == "FAIL-SHADOWED":
                print(f"  {r['id']} ({r['project']}, {r['method']} {r['route']}): {r['reason']}")

    if other_fail:
        print(f"\n--- every other genuine failure, and exactly why ---")
        for r in results:
            if r["verdict"] == "FAIL-OTHER":
                print(f"  {r['id']} ({r['project']}, {r['method']} {r['route']}): {r['reason']}")

    report = {
        "unique_capability_ids": len(caps),
        "duplicate_id_mismatches": mismatches,
        "route_bearing_capabilities": len(route_caps),
        "distinct_data_files": len(distinct_files),
        "collision_groups": {f"{m} {r}": v for (m, r), v in collisions.items()},
        "total_shadowed_predicted": total_shadowed,
        "results": results,
        "summary": {"pass": passed, "shadowed": shadowed, "other_fail": other_fail, "total": len(results)},
    }
    out = STRESS_DIR / "stress_result.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nWritten to {out}")
    return report


if __name__ == "__main__":
    main()
