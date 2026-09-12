#!/usr/bin/env python3
"""
new_app_event_board.py — the decisive proof: a genuinely NEW app type (not
one of Sam's original 43), assembled from the upgraded capability library
rather than hand-built from scratch. Every capability below is either:

  (a) a NEW shared capability type that didn't exist anywhere in the 43-app
      library (Calendar/Event, Notification) -- built once in gen_common.py,
      proven by direct behavioural regression test and a real build.py run;
  (b) the generalized replacement for one of the 3 RED (not-reusable)
      capabilities the compatibility audit found -- add_bounded_counter_
      capability, called here UNMODIFIED, in a genuinely different domain
      (event RSVP capacity, not event_ticketing's ticket sales) from the one
      it was proven equivalent against;
  (c) a REAL, UNMODIFIED capability file reused verbatim from a different
      already-shipped app (team_chat's List/Post/Delete Message, CAP-1201/
      1202/1203) -- the same mechanism the audit's Test A proved live, now
      shipped in a real app instead of a disposable experiment.

Nothing here is hand-written CRUD for a new domain the way the original 43
apps were. The app's own JS composes two independently-built capabilities
client-side (RSVP, then notify) -- real composition, not new backend
coupling.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_common import AppBuilder, page_skeleton  # noqa: E402

ROOT = HERE / "library_build"


def build(root: Path):
    b = AppBuilder(root, "community_event_board", "community event board", "9900")

    # (a) NEW Calendar/Event capability -- real ISO-8601 date validation,
    # extended with a capacity/attendees pair for the RSVP capability below.
    b.add_calendar_event_capabilities(
        "9901", "9902", "9903",
        data_filename="events.json",
        slot_id="event_list", selector="#event-list",
        extra_fields=[
            {"name": "capacity", "input_key": "capacity", "default": 10, "cast": "int"},
            {"name": "attendees", "input_key": None, "default": 0, "cast": None},
        ])

    # (b) The generalized RED-capability replacement, called UNMODIFIED, in
    # a new domain (RSVP capacity, not ticket sales) -- proves this is a
    # genuinely reusable engine, not a one-off fit to event_ticketing.
    b.add_bounded_counter_capability(
        "9904", "RSVP to Event", "/api/events/rsvp", id_field="id",
        counter_field="attendees", limit_field="capacity", fail_message="event is full",
        entity_noun="event", data_filename="events.json")

    # (a) NEW Notification capability.
    notif_create_id = b.add_notification_capabilities("9905", "9906", "9907")

    # (c) Real, unmodified capability files reused verbatim from team_chat --
    # same ids, same code, not regenerated. Announcements for the board.
    team_chat_shelf = HERE / "library_build" / "team_chat" / "shelf"
    b.reuse_capability_verbatim(team_chat_shelf, "CAP-1201")  # List Messages
    b.reuse_capability_verbatim(team_chat_shelf, "CAP-1202", slot_id="announcement_list",
                                 selector="#announcement-list", side_effects=("creates_record",))
    b.reuse_capability_verbatim(team_chat_shelf, "CAP-1203")  # Delete Message

    body_inner = f'''<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Events</h2>
  <div class="row">
    <input id="ev-title" placeholder="Event title" data-slot="ev_title">
    <input id="ev-start" type="datetime-local" value="2026-12-01T18:00" data-slot="ev_start">
    <input id="ev-capacity" type="number" value="10" placeholder="Capacity" data-slot="ev_capacity" style="width:90px">
    <button id="add-event-btn" data-slot="add_event">Create event</button>
  </div>
  <ul id="event-list" data-slot="event_list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Your notifications</h2>
  <ul id="notification-list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Announcements <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from team_chat)</span></h2>
  <div class="row">
    <input id="announce-text" placeholder="Post an announcement" data-slot="announce_text" style="flex:1">
    <button id="post-announce-btn" data-slot="post_announce">Post</button>
  </div>
  <ul id="announcement-list" data-slot="announcement_list"></ul>
</div>'''

    script = '''
const ME = "organizer@example.com";

function refreshEvents() {
  fetch("/api/community_event_board/events").then(r => r.json()).then(data => {
    const list = document.getElementById("event-list");
    list.innerHTML = "";
    (data.events || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = e.title + " -- " + e.attendees + "/" + e.capacity + " attending";
      const rsvp = document.createElement("button");
      rsvp.textContent = "RSVP"; rsvp.style.marginLeft = "8px";
      rsvp.addEventListener("click", () => {
        fetch("/api/community_event_board/events/rsvp", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: e.id})}).then(r => r.json()).then(result => {
            if (result.error) {
              fetch("/api/community_event_board/notifications", {method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({recipient: ME, message: "RSVP failed for " + e.title + ": " + result.error})});
            } else {
              fetch("/api/community_event_board/notifications", {method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({recipient: ME, message: "You are confirmed for " + e.title})});
            }
            refreshEvents(); refreshNotifications();
          });
      });
      li.appendChild(rsvp);
      list.appendChild(li);
    });
  });
}
function refreshNotifications() {
  fetch("/api/community_event_board/notifications?recipient=" + encodeURIComponent(ME)).then(r => r.json()).then(data => {
    const list = document.getElementById("notification-list");
    list.innerHTML = "";
    (data.notifications || []).forEach(n => {
      const li = document.createElement("li");
      li.textContent = (n.read ? "" : "\\u25cf ") + n.message;
      list.appendChild(li);
    });
  });
}
function refreshAnnouncements() {
  fetch("/api/team_chat/messages").then(r => r.json()).then(data => {
    const list = document.getElementById("announcement-list");
    list.innerHTML = "";
    (data.messages || []).forEach(m => {
      const li = document.createElement("li");
      li.textContent = m.author + ": " + m.text;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-event-btn").addEventListener("click", () => {
  const title = document.getElementById("ev-title").value;
  const start = document.getElementById("ev-start").value;
  const capacity = document.getElementById("ev-capacity").value;
  if (!title.trim()) return;
  fetch("/api/community_event_board/events", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, start: start, capacity: capacity})}).then(() => {
      document.getElementById("ev-title").value = "";
      refreshEvents();
    });
});
document.getElementById("post-announce-btn").addEventListener("click", () => {
  const text = document.getElementById("announce-text").value;
  if (!text.trim()) return;
  fetch("/api/team_chat/messages", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: text, author: "Organizer"})}).then(() => {
      document.getElementById("announce-text").value = "";
      refreshAnnouncements();
    });
});
refreshEvents(); refreshNotifications(); refreshAnnouncements();
'''
    html = page_skeleton("Community Event Board", "", body_inner, script)
    journey = {
        "input_selector": "#ev-title", "input_value": "Neighborhood Picnic",
        "action_selector": "#add-event-btn",
        "confirm_selector": "text=Neighborhood Picnic", "confirm_contains": "Neighborhood Picnic",
    }
    b.finish(html, journey, "Community Event Board", port=5999)


if __name__ == "__main__":
    if not (ROOT / "team_chat").exists():
        print("team_chat must be built first (python3 build_batch.py team_chat) so its real "
              "capability files exist on disk to reuse verbatim.")
        raise SystemExit(2)
    build(ROOT)
    project = ROOT / "community_event_board"
    build_py_src = (HERE.parent / "build.py").read_text().replace(
        "ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project))
    raise SystemExit(res.returncode)
