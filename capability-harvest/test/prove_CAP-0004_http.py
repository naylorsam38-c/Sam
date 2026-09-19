#!/usr/bin/env python3
"""
prove_CAP-0004_http.py — real HTTP proof for CAP-0004 (track streak),
harvested from batrisyiasafri/habit_tracker.

No mocks. Against the real running composed app (build.py start --cap
CAP-0004): creates a real habit via POST /add_habit, marks it done today
via GET /mark_done/<id> (real INSERT into the real HabitLog table), and
confirms the real homepage shows "Current Streak: 1".

The app's own HTTP surface has no way to log a PAST day (mark_done always
logs today; there is no backdating endpoint), so to prove the multi-day
consecutive-day branch of calculate_streaks (not just the trivial
single-day case), two further HabitLog rows are inserted directly into the
SAME real SQLite file the live server reads from, for yesterday and the
day before -- using the app's own real schema (via sqlalchemy against the
same file), not a mock of the streak function. calculate_streaks() itself
is never touched; it processes these real rows for real and its real
output is what's asserted on the next real GET /.
"""

import sqlite3
import sys
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

CAP_ID = "CAP-0004"


def _extract_streak(html: str, habit_name: str) -> int:
    # Real rendered fragment from templates/index.html: the habit's card
    # contains its name and, nearby, "Current Streak: N".
    idx = html.index(habit_name)
    window = html[idx: idx + 800]
    import re
    match = re.search(r"Current\s*Streak:?\s*</?\w*>?\s*(\d+)", window, re.IGNORECASE)
    assert match, f"could not find a 'Current Streak' figure near {habit_name!r} in the real page HTML"
    return int(match.group(1))


def main():
    config.print_roots(__file__)
    manifest = config.load_json(config.OUTPUT_ROOT / "build_manifest.json")
    if not manifest["verification"]["verified"]:
        raise SystemExit("ABORT: build manifest says the composed app was not verified -- refusing to test it")
    base_url = f"http://{manifest['host']}:{manifest['port']}"
    cloned_path = Path(manifest["verification"]["cloned_path"])
    # Flask-SQLAlchemy resolves a relative sqlite:/// URI against the app's
    # instance path, not the process cwd -- confirmed by inspecting which
    # of the candidate .db files actually contains the habit/habit_log
    # tables after a real run.
    db_path = cloned_path / "instance" / "habits.db"

    session = requests.Session()
    stamp = int(datetime.now(timezone.utc).timestamp())
    habit_name = f"HarvestProofHabit{stamp}"
    evidence = {"cap_id": CAP_ID, "base_url": base_url, "steps": []}

    def record(step, response, extra=None):
        entry = {"step": step, "method": response.request.method, "url": response.request.url, "status_code": response.status_code}
        if extra:
            entry.update(extra)
        evidence["steps"].append(entry)
        print(f"  [{step}] {response.request.method} {response.request.url} -> {response.status_code}")

    # index() is what sets session['user_id'] = 1 (the app's own "fake
    # login for testing" per its code comment) -- add_habit() reads that
    # session key and 500s without it, same as a real browser would need
    # to visit the homepage before the session cookie exists.
    r = session.get(f"{base_url}/")
    record("establish_session", r)

    r = session.post(f"{base_url}/add_habit", data={"habit_name": habit_name}, allow_redirects=True)
    record("add_habit", r)
    assert habit_name in r.text

    conn = sqlite3.connect(str(db_path))
    habit_id = conn.execute("SELECT id FROM habit WHERE name = ?", (habit_name,)).fetchone()[0]
    conn.close()

    r = session.get(f"{base_url}/mark_done/{habit_id}", allow_redirects=True)
    record("mark_done_today", r, {"habit_id": habit_id})
    streak_after_one_day = _extract_streak(r.text, habit_name)
    assert streak_after_one_day == 1, f"expected streak 1 after logging today only, got {streak_after_one_day}"

    # Real historical rows, inserted directly into the app's own real
    # SQLite file/schema (habit_log table columns: id, habit_id, date,
    # status) -- see docstring for why HTTP alone can't backdate this.
    yesterday = date.today() - timedelta(days=1)
    day_before = date.today() - timedelta(days=2)
    conn = sqlite3.connect(str(db_path))
    conn.execute("INSERT INTO habit_log (habit_id, date, status) VALUES (?, ?, 'done')", (habit_id, yesterday.isoformat()))
    conn.execute("INSERT INTO habit_log (habit_id, date, status) VALUES (?, ?, 'done')", (habit_id, day_before.isoformat()))
    conn.commit()
    conn.close()

    r = session.get(f"{base_url}/", allow_redirects=True)
    record("homepage_after_backfill", r, {"backfilled_dates": [yesterday.isoformat(), day_before.isoformat()]})
    streak_after_backfill = _extract_streak(r.text, habit_name)
    assert streak_after_backfill == 3, f"expected streak 3 after 3 real consecutive days logged, got {streak_after_backfill}"

    evidence["streaks_observed"] = {"after_one_day": streak_after_one_day, "after_three_consecutive_days": streak_after_backfill}
    evidence["result"] = "PASS"
    evidence["verified_at"] = datetime.now(timezone.utc).isoformat()

    out_dir = config.SHELF_ROOT / manifest["verification"]["app_slug"] / CAP_ID / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    config.write_json(out_dir / "TEST_EVIDENCE_HTTP.json", evidence)
    print(f"\nPASS -- wrote {out_dir / 'TEST_EVIDENCE_HTTP.json'}")
    print(f"Real streak trail: 1 (today only) -> {streak_after_backfill} (3 real consecutive days)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
