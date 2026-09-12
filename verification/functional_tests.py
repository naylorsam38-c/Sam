#!/usr/bin/env python3
"""
functional_tests.py — real, reusable end-to-end functional tests, run
against real running Flask processes over real HTTP. This is the shipped,
reproducible form of the ad hoc checks used during development (never left
as one-off terminal commands) so a third party can re-run the exact same
proof, not just trust that it was once run somewhere.

Every app is tested against a DISPOSABLE COPY under a temp/scratch
directory, never against OUTPUT_LIBRARY or NEW_APPS_FROM_LIBRARY directly
-- starting the real app writes real new records into its real data files,
which would otherwise mutate the shipped, committed library.

Requires the apps to already be built under verification/library_build/
(via build_batch.py and the three new_app_*.py scripts) -- this script only
exercises already-assembled apps, it doesn't build anything itself.
"""
import json
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIBRARY_BUILD = HERE / "library_build"
SCRATCH = HERE / "functest_scratch"


def fresh_copy(project_slug: str) -> Path:
    src = LIBRARY_BUILD / project_slug / "library" / "APP-001"
    if not src.is_dir():
        raise FileNotFoundError(f"{src} does not exist -- build {project_slug} first")
    dest = SCRATCH / project_slug
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    for f in (dest / "data").glob("*.json"):
        f.write_text("[]")
    return dest


def start(app_dir: Path, port: int):
    app_json = json.loads((app_dir / "app.json").read_text())
    proc = subprocess.Popen(app_json["start"] + ["--port", str(port)], cwd=str(app_dir),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(1.2)
    return proc


def call(port, method, path, body=None):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"} if data else {})
    try:
        r = urllib.request.urlopen(req, timeout=5)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def check(label, actual, predicate, results):
    ok = predicate(actual)
    results.append((label, ok, actual))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: {actual}")
    return ok


def test_todo_list(port, results):
    print("\n=== todo_list ===")
    app_dir = fresh_copy("todo_list")
    proc = start(app_dir, port)
    try:
        check("create todo", call(port, "POST", "/api/todo_list/todos", {"title": "Buy milk"}),
              lambda r: r[0] == 201 and r[1]["title"] == "Buy milk", results)
        check("toggle todo", call(port, "POST", "/api/todo_list/todos/toggle", {"id": 1}),
              lambda r: r[0] == 200 and r[1]["completed"] is True, results)
        check("standard error shape on 404", call(port, "POST", "/api/todo_list/todos/delete", {"id": 999}),
              lambda r: r[0] == 404 and r[1]["error"]["code"] == "NOT_FOUND", results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_payroll(port, results):
    print("\n=== payroll (cross-entity access via the shared library) ===")
    app_dir = fresh_copy("payroll")
    proc = start(app_dir, port)
    try:
        call(port, "POST", "/api/payroll/employees", {"name": "Alex", "salary": 1000})
        call(port, "POST", "/api/payroll/employees", {"name": "Sam", "salary": 2000})
        check("run payroll for 2 employees", call(port, "POST", "/api/payroll/payroll/run"),
              lambda r: r[0] == 200 and r[1]["created"] == 2, results)
        check("pay records have correct 80% net", call(port, "GET", "/api/payroll/payroll/records"),
              lambda r: r[0] == 200 and {rec["net"] for rec in r[1]["records"]} == {800.0, 1600.0}, results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_dating(port, results):
    print("\n=== dating (symmetric-relationship engine) ===")
    app_dir = fresh_copy("dating")
    proc = start(app_dir, port)
    try:
        call(port, "POST", "/api/dating/profiles", {"name": "Alice"})
        call(port, "POST", "/api/dating/profiles", {"name": "Bob"})
        check("one-way like is not yet a match", call(port, "POST", "/api/dating/swipes",
              {"profile_id": 1, "target_id": 2, "liked": True}),
              lambda r: r[0] == 200 and r[1]["match"] is False, results)
        check("reciprocal like is a real match", call(port, "POST", "/api/dating/swipes",
              {"profile_id": 2, "target_id": 1, "liked": True}),
              lambda r: r[0] == 200 and r[1]["match"] is True, results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_community_event_board(port, results):
    print("\n=== community_event_board (new app: calendar + bounded-counter + notification + reused team_chat) ===")
    app_dir = fresh_copy("community_event_board")
    proc = start(app_dir, port)
    try:
        call(port, "POST", "/api/community_event_board/events",
             {"title": "Tiny Picnic", "start": "2026-12-05T12:00:00", "capacity": 1})
        check("first RSVP succeeds", call(port, "POST", "/api/community_event_board/events/rsvp", {"id": 1}),
              lambda r: r[0] == 200 and r[1]["attendees"] == 1, results)
        check("second RSVP correctly rejected (full)",
              call(port, "POST", "/api/community_event_board/events/rsvp", {"id": 1}),
              lambda r: r[0] == 400 and r[1]["error"]["message"] == "event is full", results)
        check("announcement reused verbatim from team_chat", call(port, "POST", "/api/team_chat/messages",
              {"text": "Moved indoors", "author": "Organizer"}),
              lambda r: r[0] == 201 and r[1]["text"] == "Moved indoors", results)
        check("invalid date rejected by real ISO-8601 validation",
              call(port, "POST", "/api/community_event_board/events",
              {"title": "Bad", "start": "not-a-date"}),
              lambda r: r[0] == 400 and "ISO-8601" in r[1]["error"]["message"], results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_fitness_challenge_board(port, results):
    print("\n=== fitness_challenge_board (new app: bounded-counter x3 + symmetric-relationship x2 + reused fitness_tracking) ===")
    app_dir = fresh_copy("fitness_challenge_board")
    proc = start(app_dir, port)
    try:
        check("workout logged via reused fitness_tracking capability",
              call(port, "POST", "/api/fitness_tracking/workouts", {"type": "Run", "duration": 30}),
              lambda r: r[0] == 201 and r[1]["type"] == "Run", results)
        call(port, "POST", "/api/fitness_challenge_board/challenges",
             {"title": "Plank Challenge", "max_participants": 1})
        check("first join succeeds",
              call(port, "POST", "/api/fitness_challenge_board/challenges/join", {"id": 1}),
              lambda r: r[0] == 200 and r[1]["participants"] == 1, results)
        check("second join correctly rejected (full)",
              call(port, "POST", "/api/fitness_challenge_board/challenges/join", {"id": 1}),
              lambda r: r[0] == 400 and r[1]["error"]["message"] == "challenge is full", results)
        call(port, "POST", "/api/fitness_challenge_board/buddy_requests",
             {"requester_id": 1, "target_id": 2, "interested": True})
        check("reciprocal buddy request pairs", call(port, "POST", "/api/fitness_challenge_board/buddy_requests",
              {"requester_id": 2, "target_id": 1, "interested": True}),
              lambda r: r[0] == 200 and r[1]["paired"] is True, results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_course_enrollment_hub(port, results):
    print("\n=== course_enrollment_hub (new app: calendar + bounded-counter x4 + reused lms + reused quiz) ===")
    app_dir = fresh_copy("course_enrollment_hub")
    proc = start(app_dir, port)
    try:
        check("course reused verbatim from online_course_lms",
              call(port, "POST", "/api/online_course_lms/courses", {"title": "Composable Systems 101"}),
              lambda r: r[0] == 201 and r[1]["title"] == "Composable Systems 101", results)
        call(port, "POST", "/api/course_enrollment_hub/events",
             {"title": "Live Q&A", "start": "2026-12-10T14:00:00", "seats": 1})
        check("first enrollment succeeds",
              call(port, "POST", "/api/course_enrollment_hub/events/enroll", {"id": 1}),
              lambda r: r[0] == 200 and r[1]["enrolled"] == 1, results)
        check("second enrollment correctly rejected (full)",
              call(port, "POST", "/api/course_enrollment_hub/events/enroll", {"id": 1}),
              lambda r: r[0] == 400 and r[1]["error"]["message"] == "session is full", results)
        check("quiz card reused verbatim, repurposed as feedback prompt",
              call(port, "POST", "/api/quiz_and_flashcards/cards",
              {"question": "How was the session?"}),
              lambda r: r[0] == 201 and r[1]["question"] == "How was the session?", results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_recipe_box(port, results):
    print("\n=== recipe_box (coverage-testing round: new add_unbounded_counter_capability engine) ===")
    app_dir = fresh_copy("recipe_box")
    proc = start(app_dir, port)
    try:
        check("create recipe", call(port, "POST", "/api/recipe_box/recipes", {"title": "Chili"}),
              lambda r: r[0] == 201 and r[1]["likes"] == 0, results)
        check("like once", call(port, "POST", "/api/recipe_box/recipes/like", {"id": 1}),
              lambda r: r[0] == 200 and r[1]["likes"] == 1, results)
        check("like again (unbounded, no cap)", call(port, "POST", "/api/recipe_box/recipes/like", {"id": 1}),
              lambda r: r[0] == 200 and r[1]["likes"] == 2, results)
        check("like missing recipe", call(port, "POST", "/api/recipe_box/recipes/like", {"id": 999}),
              lambda r: r[0] == 404 and r[1]["error"]["code"] == "NOT_FOUND", results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_bug_tracker(port, results):
    print("\n=== bug_tracker (coverage-testing round: new add_status_transition_capability engine) ===")
    app_dir = fresh_copy("bug_tracker")
    proc = start(app_dir, port)
    try:
        check("create bug", call(port, "POST", "/api/bug_tracker/bugs", {"title": "Login broken"}),
              lambda r: r[0] == 201 and r[1]["status"] == "open", results)
        check("advance to in_progress",
              call(port, "POST", "/api/bug_tracker/bugs/status", {"id": 1, "status": "in_progress"}),
              lambda r: r[0] == 200 and r[1]["status"] == "in_progress", results)
        check("advance to resolved",
              call(port, "POST", "/api/bug_tracker/bugs/status", {"id": 1, "status": "resolved"}),
              lambda r: r[0] == 200 and r[1]["status"] == "resolved", results)
        check("transition on missing bug", call(port, "POST", "/api/bug_tracker/bugs/status", {"id": 999}),
              lambda r: r[0] == 404 and r[1]["error"]["code"] == "NOT_FOUND", results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def test_volunteer_shift_signup(port, results):
    print("\n=== volunteer_shift_signup (coverage-testing round: fully composed from the pre-existing library) ===")
    app_dir = fresh_copy("volunteer_shift_signup")
    proc = start(app_dir, port)
    try:
        call(port, "POST", "/api/volunteer_shift_signup/events",
             {"title": "Food Bank", "start": "2026-12-05T09:00:00", "capacity": 1})
        check("first sign-up succeeds",
              call(port, "POST", "/api/volunteer_shift_signup/shifts/signup", {"id": 1}),
              lambda r: r[0] == 200 and r[1]["volunteers"] == 1, results)
        check("second sign-up correctly rejected (full)",
              call(port, "POST", "/api/volunteer_shift_signup/shifts/signup", {"id": 1}),
              lambda r: r[0] == 400 and r[1]["error"]["message"] == "shift is full", results)
        check("discussion board reused verbatim from team_chat (2nd independent reuse)",
              call(port, "POST", "/api/team_chat/messages", {"text": "Bring gloves", "author": "Volunteer"}),
              lambda r: r[0] == 201 and r[1]["text"] == "Bring gloves", results)
    finally:
        proc.terminate(); proc.wait(timeout=5)


def main():
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir()
    results = []
    test_todo_list(7910, results)
    test_payroll(7911, results)
    test_dating(7912, results)
    test_community_event_board(7913, results)
    test_fitness_challenge_board(7914, results)
    test_course_enrollment_hub(7915, results)
    test_recipe_box(7916, results)
    test_bug_tracker(7917, results)
    test_volunteer_shift_signup(7918, results)

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'=' * 70}\n{passed}/{total} functional checks passed\n{'=' * 70}")
    return {"passed": passed, "total": total,
            "checks": [{"label": l, "pass": ok} for l, ok, _ in results]}


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
    raise SystemExit(0 if result["passed"] == result["total"] else 1)
