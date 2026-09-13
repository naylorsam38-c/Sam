#!/usr/bin/env python3
"""
Real security tests for note_taking's pilot promotion
(PRIVATE_PILOT_SAFETY_MILESTONE.md items 1-3, 8). Every check below is a
real HTTP call (or a real inspection of the actual data file on disk)
against a real running Flask process assembled from the current
app_defs.py/gen_common.py -- nothing here is asserted from reading the
code, only from what actually happened when it ran. Uses a disposable
scratch copy built fresh by this script; never touches OUTPUT_LIBRARY.
"""
import datetime
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIBRARY_BUILD = HERE / "library_build"
SCRATCH = HERE / "note_taking_security_test_scratch"


def fresh_copy() -> Path:
    """Same pattern as coverage_expansion/security_tests.py's fresh_copy():
    a real, already-assembled-and-proven build (produced by build_one.py's
    own stage1_assemble(), not reinvented here) copied into a disposable
    scratch dir with its data files reset to empty, never touching
    OUTPUT_LIBRARY. Requires `python3 build_one.py note_taking` to have
    been run at least once against the current app_defs.py/gen_common.py
    (this project's own established prerequisite for every per-app test
    script, not unique to this one)."""
    src = LIBRARY_BUILD / "note_taking" / "library" / "APP-001"
    if not src.is_dir():
        raise RuntimeError(f"{src} does not exist -- run `python3 build_one.py note_taking` first")
    dest = SCRATCH / "note_taking"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    for f in (dest / "data").glob("*.json"):
        f.write_text("[]")
    return dest


def start(app_dir: Path, port: int):
    # The generated modules layout is modules/CAP-0000 (shared lib) plus one
    # host module named after this app's host_num ("0200") -- found by glob
    # rather than hardcoded so this script does not silently drift from
    # AppBuilder's own naming if that ever changes.
    host_py = None
    for candidate in (app_dir / "modules").glob("CAP-0*/app.py"):
        if "0200" in str(candidate):
            host_py = candidate
            break
    if host_py is None:
        raise RuntimeError(f"no host module found under {app_dir / 'modules'}")
    proc = subprocess.Popen(["python3", str(host_py), "--port", str(port)], cwd=str(app_dir),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
            return proc
        except Exception:
            time.sleep(0.2)
    out = proc.stdout.read() if proc.stdout else ""
    proc.terminate()
    raise RuntimeError(f"note_taking did not start on port {port}\n{out}")


def call(port, method, path, body=None, token=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, None


results = []


def check(label, actual, predicate):
    ok = bool(predicate(actual))
    results.append((label, ok, actual))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: {actual}")
    return ok


def main():
    port = 6101
    app_dir = fresh_copy()
    proc = start(app_dir, port)
    try:
        print("\n" + "=" * 78 + "\nnote_taking -- pilot isolation/login security tests\n" + "=" * 78)

        # --- admin-provisioned accounts: bootstrap is real but self-limiting ---
        r = call(port, "POST", "/api/note_taking/auth/bootstrap-admin",
                 {"email": "sam@example.com", "password": "correct-horse-1"})
        check("bootstrap first admin succeeds", r, lambda r: r[0] == 201 and r[1]["role"] == "admin")

        r = call(port, "POST", "/api/note_taking/auth/bootstrap-admin",
                 {"email": "someone-else@example.com", "password": "correct-horse-2"})
        check("second bootstrap attempt permanently refused (no public self-registration)", r,
              lambda r: r[0] == 403)

        r = call(port, "POST", "/api/note_taking/auth/login",
                 {"email": "sam@example.com", "password": "correct-horse-1"})
        check("admin login", r, lambda r: r[0] == 200 and r[1].get("token"))
        admin_token = r[1]["token"]

        # --- admin-provisioned tester accounts; no public registration ---
        r = call(port, "POST", "/api/note_taking/auth/register",
                 {"email": "alice@example.com", "password": "tester-pw-1"})
        # required_role's existing, pre-proven wrapping (already used
        # unchanged for identity_and_access_demo's "Delete Any Task",
        # security_tests.py's own "regular member (bob) CANNOT delete a
        # task (admin-only, real 403)") answers a role mismatch with 403,
        # not 401, whether or not the caller is authenticated at all --
        # real, established behavior this reuses as-is, not new code.
        check("Register with no token -> 403 (not open self-registration)", r, lambda r: r[0] == 403)

        r = call(port, "POST", "/api/note_taking/auth/register",
                 {"email": "alice@example.com", "password": "tester-pw-1"}, token=admin_token)
        check("admin creates tester alice", r, lambda r: r[0] == 201 and r[1]["email"] == "alice@example.com"
              and "password" not in r[1] and "password_hash" not in r[1])

        r = call(port, "POST", "/api/note_taking/auth/register",
                 {"email": "bob@example.com", "password": "tester-pw-2"}, token=admin_token)
        check("admin creates tester bob", r, lambda r: r[0] == 201 and r[1]["email"] == "bob@example.com")

        r = call(port, "POST", "/api/note_taking/auth/login", {"email": "alice@example.com", "password": "tester-pw-1"})
        check("alice login", r, lambda r: r[0] == 200 and r[1].get("token"))
        token_a, user_id_a = r[1]["token"], r[1]["user_id"]

        r = call(port, "POST", "/api/note_taking/auth/login", {"email": "bob@example.com", "password": "tester-pw-2"})
        check("bob login", r, lambda r: r[0] == 200 and r[1].get("token"))
        token_b, user_id_b = r[1]["token"], r[1]["user_id"]

        # --- a real tester cannot provision accounts ---
        r = call(port, "POST", "/api/note_taking/auth/register",
                 {"email": "carol@example.com", "password": "tester-pw-3"}, token=token_a)
        check("non-admin tester cannot create accounts", r, lambda r: r[0] == 403)

        # --- unauthenticated requests rejected on every note path ---
        check("List Notes with no token -> 401", call(port, "GET", "/api/note_taking/notes"),
              lambda r: r[0] == 401)
        check("Create Note with no token -> 401", call(port, "POST", "/api/note_taking/notes",
              {"title": "x"}), lambda r: r[0] == 401)
        check("Update Note with no token -> 401", call(port, "POST", "/api/note_taking/notes/update",
              {"id": 1, "title": "x"}), lambda r: r[0] == 401)
        check("Delete Note with no token -> 401", call(port, "POST", "/api/note_taking/notes/delete",
              {"id": 1}), lambda r: r[0] == 401)
        check("garbage token -> 401", call(port, "GET", "/api/note_taking/notes", token="not-a-real-token"),
              lambda r: r[0] == 401)

        # --- real cross-user data isolation ---
        r = call(port, "POST", "/api/note_taking/notes", {"title": "Alice's note", "body": "secret a"},
                  token=token_a)
        check("alice creates a note, real owner_id from her own session (never client-supplied)", r,
              lambda r: r[0] == 201 and r[1]["owner_id"] == user_id_a)
        note_a_id = r[1]["id"]

        r = call(port, "POST", "/api/note_taking/notes", {"title": "Bob's note", "body": "secret b"},
                  token=token_b)
        check("bob creates a note, real owner_id from his own session", r,
              lambda r: r[0] == 201 and r[1]["owner_id"] == user_id_b)
        note_b_id = r[1]["id"]

        r = call(port, "GET", "/api/note_taking/notes", token=token_a)
        check("alice sees only her own note (cross-user isolation)", r,
              lambda r: r[0] == 200 and [n["title"] for n in r[1]["notes"]] == ["Alice's note"])

        r = call(port, "GET", "/api/note_taking/notes", token=token_b)
        check("bob sees only his own note (cross-user isolation)", r,
              lambda r: r[0] == 200 and [n["title"] for n in r[1]["notes"]] == ["Bob's note"])

        # --- one tester cannot read, update, or delete another tester's note ---
        check("bob cannot update alice's note (403, not silently succeeding)",
              call(port, "POST", "/api/note_taking/notes/update",
                   {"id": note_a_id, "title": "tampered"}, token=token_b),
              lambda r: r[0] == 403)
        check("alice's note is genuinely unchanged after bob's rejected update", call(port, "GET",
              "/api/note_taking/notes", token=token_a),
              lambda r: r[0] == 200 and r[1]["notes"][0]["title"] == "Alice's note")

        check("bob cannot delete alice's note (403, not silently succeeding)",
              call(port, "POST", "/api/note_taking/notes/delete", {"id": note_a_id}, token=token_b),
              lambda r: r[0] == 403)
        check("alice's note still exists after bob's rejected delete", call(port, "GET",
              "/api/note_taking/notes", token=token_a),
              lambda r: r[0] == 200 and len(r[1]["notes"]) == 1)

        # --- a tester CAN manage her own note ---
        check("alice can update her own note", call(port, "POST", "/api/note_taking/notes/update",
              {"id": note_a_id, "title": "Alice's note (edited)"}, token=token_a),
              lambda r: r[0] == 200 and r[1]["title"] == "Alice's note (edited)")
        check("alice can delete her own note", call(port, "POST", "/api/note_taking/notes/delete",
              {"id": note_a_id}, token=token_a), lambda r: r[0] == 200 and r[1]["deleted"] is True)
        check("bob's note is untouched by alice's own delete", call(port, "GET",
              "/api/note_taking/notes", token=token_b),
              lambda r: r[0] == 200 and len(r[1]["notes"]) == 1 and r[1]["notes"][0]["id"] == note_b_id)

        # --- logout genuinely invalidates the session ---
        check("me works before logout", call(port, "GET", "/api/note_taking/auth/me", token=token_a),
              lambda r: r[0] == 200)
        check("logout succeeds", call(port, "POST", "/api/note_taking/auth/logout", token=token_a),
              lambda r: r[0] == 200 and r[1]["logged_out"] is True)
        check("same token rejected after logout", call(port, "GET", "/api/note_taking/notes",
              token=token_a), lambda r: r[0] == 401)

        # --- confirmed session lifetime: real inspection of the actual session row ---
        r = call(port, "POST", "/api/note_taking/auth/login", {"email": "bob@example.com", "password": "tester-pw-2"})
        fresh_token = r[1]["token"]
        sessions = json.loads((app_dir / "data" / "auth_sessions.json").read_text())
        row = next(s for s in sessions if s["token"] == fresh_token)
        expires_at = datetime.datetime.fromisoformat(row["expires_at"])
        hours_until_expiry = (expires_at - datetime.datetime.now()).total_seconds() / 3600
        check("session lifetime is the confirmed 12-hour pilot maximum (within a 2-minute tolerance)",
              round(hours_until_expiry, 3), lambda h: 11.95 < h < 12.05)

        # --- passwords never touch disk or the wire in plaintext ---
        users_raw = (app_dir / "data" / "users.json").read_text()
        check("no plaintext password anywhere in the real users.json file", "checked",
              lambda _: "tester-pw-1" not in users_raw and "tester-pw-2" not in users_raw
              and "correct-horse-1" not in users_raw)

        # --- safe client-facing errors: no raw exception text leaks to the client ---
        # note_taking's own handlers are all defensively written (.get()
        # with defaults, silent=True JSON parsing) so a normal malformed
        # request never actually raises -- a REAL unhandled exception is
        # forced here the same way a real deployment could hit one: a
        # corrupt row in the data file (List Notes calls n.get('owner_id')
        # on every row; a bare string has no .get()). This proves
        # dispatch()'s fix on note_taking's actual generated code, not just
        # by reading gen_common.py's source.
        notes_path = app_dir / "data" / "note_taking.json"
        notes_path.write_text(json.dumps(["not-a-real-note-record"]))
        r = call(port, "GET", "/api/note_taking/notes", token=token_b)
        check("a real unhandled exception returns a generic message, status 500", r,
              lambda r: r[0] == 500)
        check("the generic message names no Python exception type or text", r,
              lambda r: "AttributeError" not in json.dumps(r[1]) and "'str' object" not in json.dumps(r[1]))
        notes_path.write_text("[]")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'=' * 78}\n{passed}/{total} note_taking pilot security checks passed\n{'=' * 78}")
    result = {"passed": passed, "total": total, "checks": [{"label": l, "pass": ok} for l, ok, _ in results]}
    print(json.dumps(result))
    raise SystemExit(0 if passed == total else 1)
