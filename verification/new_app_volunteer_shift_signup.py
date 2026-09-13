#!/usr/bin/env python3
"""
new_app_volunteer_shift_signup.py — coverage-testing round, app 3 of 3: the
positive-coverage case. A genuinely new domain, composed ENTIRELY from
capabilities that already existed BEFORE this coverage-testing round -- zero
new generic engines, answering directly whether the builder can create a
brand-new app type from the existing capability library alone.

  - add_calendar_event_capabilities (existing shared type) for shift
    scheduling, real ISO-8601 validation, extended with a capacity/
    volunteers pair -- the same engine community_event_board and
    course_enrollment_hub already used, in a third, unrelated domain.
  - add_bounded_counter_capability (existing engine) for shift sign-up
    capacity -- its FIFTH real use across the library (auction is not a
    bounded-counter use; the prior four are event_ticketing, community_
    event_board's RSVP, fitness_challenge_board's Join Challenge, and
    course_enrollment_hub's Enroll).
  - add_notification_capabilities (existing shared type) for shift
    reminders.
  - A real, unmodified capability file reused verbatim from team_chat
    (CAP-1201/1202/1203, List/Post/Delete Message) for a volunteer
    discussion board -- the SECOND independent app to reuse this exact
    capability (community_event_board was the first), proving reuse works
    many-to-one, not just once.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_common import AppBuilder, page_skeleton  # noqa: E402

ROOT = HERE / "library_build"


def build(root: Path):
    b = AppBuilder(root, "volunteer_shift_signup", "volunteer shift signup", "9620")

    b.add_calendar_event_capabilities(
        "9621", "9622", "9623",
        data_filename="shifts.json",
        slot_id="shift_list", selector="#shift-list",
        extra_fields=[
            {"name": "capacity", "input_key": "capacity", "default": 4, "cast": "int"},
            {"name": "volunteers", "input_key": None, "default": 0, "cast": None},
        ])
    b.add_bounded_counter_capability("9624", "Sign Up For Shift", "/api/shifts/signup",
        id_field="id", counter_field="volunteers", limit_field="capacity",
        fail_message="shift is full", entity_noun="shift", data_filename="shifts.json")
    b.add_notification_capabilities("9625", "9626", "9627")

    team_chat_shelf = HERE / "library_build" / "team_chat" / "shelf"
    b.reuse_capability_verbatim(team_chat_shelf, "CAP-1201")  # List Messages
    b.reuse_capability_verbatim(team_chat_shelf, "CAP-1202", slot_id="discussion_list",
                                 selector="#discussion-list", side_effects=("creates_record",))
    b.reuse_capability_verbatim(team_chat_shelf, "CAP-1203")  # Delete Message

    body_inner = '''<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Shifts</h2>
  <div class="row">
    <input id="shift-title" placeholder="Shift title" data-slot="shift_title">
    <input id="shift-start" type="datetime-local" value="2026-12-01T09:00" data-slot="shift_start">
    <input id="shift-capacity" type="number" value="4" placeholder="Capacity" data-slot="shift_capacity" style="width:90px">
    <button id="add-shift-btn" data-slot="add_shift">Create shift</button>
  </div>
  <ul id="shift-list" data-slot="shift_list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Your notifications</h2>
  <ul id="notification-list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Discussion <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from team_chat)</span></h2>
  <div class="row">
    <input id="discussion-text" placeholder="Post a message" data-slot="discussion_text" style="flex:1">
    <button id="post-discussion-btn" data-slot="post_discussion">Post</button>
  </div>
  <ul id="discussion-list" data-slot="discussion_list"></ul>
</div>'''
    script = '''
const ME = "volunteer@example.com";
function refreshShifts() {
  fetch("/api/volunteer_shift_signup/events").then(r => r.json()).then(data => {
    const list = document.getElementById("shift-list");
    list.innerHTML = "";
    (data.events || []).forEach(s => {
      const li = document.createElement("li");
      li.textContent = s.title + " -- " + s.volunteers + "/" + s.capacity + " signed up";
      const signup = document.createElement("button");
      signup.textContent = "Sign up"; signup.style.marginLeft = "8px";
      signup.addEventListener("click", () => {
        fetch("/api/volunteer_shift_signup/shifts/signup", {method: "POST",
          headers: {"Content-Type": "application/json"}, body: JSON.stringify({id: s.id})})
          .then(r2 => r2.json()).then(result => {
            const msg = result.error ? ("Sign-up failed for " + s.title + ": " + JSON.stringify(result.error))
                                      : ("You're signed up for " + s.title);
            fetch("/api/volunteer_shift_signup/notifications", {method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({recipient: ME, message: msg})});
            refreshShifts(); refreshNotifications();
          });
      });
      li.appendChild(signup);
      list.appendChild(li);
    });
  });
}
function refreshNotifications() {
  fetch("/api/volunteer_shift_signup/notifications?recipient=" + encodeURIComponent(ME))
    .then(r => r.json()).then(data => {
      const list = document.getElementById("notification-list");
      list.innerHTML = "";
      (data.notifications || []).forEach(n => {
        const li = document.createElement("li");
        li.textContent = (n.read ? "" : "\\u25cf ") + n.message;
        list.appendChild(li);
      });
    });
}
function refreshDiscussion() {
  fetch("/api/team_chat/messages").then(r => r.json()).then(data => {
    const list = document.getElementById("discussion-list");
    list.innerHTML = "";
    (data.messages || []).forEach(m => {
      const li = document.createElement("li");
      li.textContent = m.author + ": " + m.text;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-shift-btn").addEventListener("click", () => {
  const title = document.getElementById("shift-title").value;
  const start = document.getElementById("shift-start").value;
  const capacity = document.getElementById("shift-capacity").value;
  if (!title.trim()) return;
  fetch("/api/volunteer_shift_signup/events", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, start: start, capacity: capacity})}).then(() => {
      document.getElementById("shift-title").value = "";
      refreshShifts();
    });
});
document.getElementById("post-discussion-btn").addEventListener("click", () => {
  const text = document.getElementById("discussion-text").value;
  if (!text.trim()) return;
  fetch("/api/team_chat/messages", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: text, author: "Volunteer"})}).then(() => {
      document.getElementById("discussion-text").value = "";
      refreshDiscussion();
    });
});
refreshShifts(); refreshNotifications(); refreshDiscussion();
'''
    html = page_skeleton("Volunteer Shift Signup", "", body_inner, script)
    journey = {
        "input_selector": "#shift-title", "input_value": "Saturday Food Bank",
        "action_selector": "#add-shift-btn",
        "confirm_selector": "text=Saturday Food Bank", "confirm_contains": "Saturday Food Bank",
    }
    b.finish(html, journey, "Volunteer Shift Signup", port=5994)


if __name__ == "__main__":
    if not (ROOT / "team_chat").exists():
        print("team_chat must be built first (python3 build_batch.py team_chat) so its real "
              "capability files exist on disk to reuse verbatim.")
        raise SystemExit(2)
    build(ROOT)
    project = ROOT / "volunteer_shift_signup"
    build_py_src = (HERE.parent / "build.py").read_text().replace(
        "ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project))
    raise SystemExit(res.returncode)
