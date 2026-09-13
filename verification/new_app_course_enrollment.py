#!/usr/bin/env python3
"""
new_app_course_enrollment.py — third new app, a third distinct combination:

  - add_calendar_event_capabilities (new shared type) for session
    scheduling, with real ISO-8601 validation and an extra `seats` field.
  - add_bounded_counter_capability reused a FOURTH time (session seat
    limits) -- proving it is a genuinely generic engine, not tuned to any
    one of its first three uses.
  - Real, unmodified capability files reused verbatim from
    online_course_lms (CAP-4101/4102, List/Create Course) -- a fourth
    different source app.
  - Real, unmodified capability files reused verbatim from
    quiz_and_flashcards (CAP-4201/4202, List/Create Card) -- repurposed
    here as post-session feedback prompts, a genuinely different use of
    the exact same capability than the one it shipped with.
  - The shared Notification capability, for enrollment confirmation.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_common import AppBuilder, page_skeleton  # noqa: E402

ROOT = HERE / "library_build"


def build(root: Path):
    b = AppBuilder(root, "course_enrollment_hub", "course enrollment hub", "9700")

    lms_shelf = HERE / "library_build" / "online_course_lms" / "shelf"
    b.reuse_capability_verbatim(lms_shelf, "CAP-4101")  # List Courses
    b.reuse_capability_verbatim(lms_shelf, "CAP-4102", slot_id="course_list",
                                 selector="#course-list", side_effects=("creates_record",))  # Create Course

    quiz_shelf = HERE / "library_build" / "quiz_and_flashcards" / "shelf"
    b.reuse_capability_verbatim(quiz_shelf, "CAP-4201")  # List Cards
    b.reuse_capability_verbatim(quiz_shelf, "CAP-4202")  # Create Card (feedback prompts here)

    b.add_calendar_event_capabilities(
        "9701", "9702", "9703",
        data_filename="sessions.json",
        slot_id="session_list", selector="#session-list",
        extra_fields=[
            {"name": "seats", "input_key": "seats", "default": 20, "cast": "int"},
            {"name": "enrolled", "input_key": None, "default": 0, "cast": None},
        ])
    b.add_bounded_counter_capability("9704", "Enroll in Session", "/api/events/enroll",
        id_field="id", counter_field="enrolled", limit_field="seats",
        fail_message="session is full", entity_noun="session", data_filename="sessions.json")

    b.add_notification_capabilities("9705", "9706", "9707")

    body_inner = '''<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Courses <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from online_course_lms)</span></h2>
  <div class="row">
    <input id="course-title" placeholder="Course title" data-slot="course_title">
    <button id="add-course-btn" data-slot="add_course">Create course</button>
  </div>
  <ul id="course-list" data-slot="course_list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Sessions</h2>
  <div class="row">
    <input id="sess-title" placeholder="Session title" data-slot="sess_title">
    <input id="sess-start" type="datetime-local" value="2026-12-10T14:00" data-slot="sess_start">
    <input id="sess-seats" type="number" value="2" placeholder="Seats" data-slot="sess_seats" style="width:80px">
    <button id="add-session-btn" data-slot="add_session">Schedule session</button>
  </div>
  <ul id="session-list" data-slot="session_list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Feedback prompts <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from quiz_and_flashcards)</span></h2>
  <div class="row">
    <input id="fb-question" placeholder="Feedback question" data-slot="fb_question">
    <button id="add-fb-btn" data-slot="add_fb">Add prompt</button>
  </div>
  <ul id="fb-list"></ul>
</div>'''
    script = '''
const ME = "learner@example.com";
function refreshCourses() {
  fetch("/api/online_course_lms/courses").then(r => r.json()).then(data => {
    const list = document.getElementById("course-list");
    list.innerHTML = "";
    (data.courses || []).forEach(c => { const li = document.createElement("li"); li.textContent = c.title; list.appendChild(li); });
  });
}
function refreshSessions() {
  fetch("/api/course_enrollment_hub/events").then(r => r.json()).then(data => {
    const list = document.getElementById("session-list");
    list.innerHTML = "";
    (data.events || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = e.title + " -- " + e.enrolled + "/" + e.seats + " enrolled";
      const enroll = document.createElement("button"); enroll.textContent = "Enroll"; enroll.style.marginLeft = "8px";
      enroll.addEventListener("click", () => {
        fetch("/api/course_enrollment_hub/events/enroll", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: e.id})}).then(r => r.json()).then(result => {
            const msg = result.error ? ("Enrollment failed: " + JSON.stringify(result.error)) : ("Enrolled in " + e.title);
            fetch("/api/course_enrollment_hub/notifications", {method: "POST", headers: {"Content-Type": "application/json"},
              body: JSON.stringify({recipient: ME, message: msg})});
            refreshSessions();
          });
      });
      li.appendChild(enroll);
      list.appendChild(li);
    });
  });
}
function refreshFeedback() {
  fetch("/api/quiz_and_flashcards/cards").then(r => r.json()).then(data => {
    const list = document.getElementById("fb-list");
    list.innerHTML = "";
    (data.cards || []).forEach(c => { const li = document.createElement("li"); li.textContent = c.question; list.appendChild(li); });
  });
}
document.getElementById("add-course-btn").addEventListener("click", () => {
  const title = document.getElementById("course-title").value;
  if (!title.trim()) return;
  fetch("/api/online_course_lms/courses", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => { document.getElementById("course-title").value = ""; refreshCourses(); });
});
document.getElementById("add-session-btn").addEventListener("click", () => {
  const title = document.getElementById("sess-title").value;
  const start = document.getElementById("sess-start").value;
  const seats = document.getElementById("sess-seats").value;
  if (!title.trim()) return;
  fetch("/api/course_enrollment_hub/events", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, start: start, seats: seats})}).then(() => { document.getElementById("sess-title").value = ""; refreshSessions(); });
});
document.getElementById("add-fb-btn").addEventListener("click", () => {
  const question = document.getElementById("fb-question").value;
  if (!question.trim()) return;
  fetch("/api/quiz_and_flashcards/cards", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question: question})}).then(() => { document.getElementById("fb-question").value = ""; refreshFeedback(); });
});
refreshCourses(); refreshSessions(); refreshFeedback();
'''
    html = page_skeleton("Course Enrollment Hub", "", body_inner, script)
    journey = {
        "input_selector": "#course-title", "input_value": "Intro to Composability",
        "action_selector": "#add-course-btn",
        "confirm_selector": "text=Intro to Composability", "confirm_contains": "Intro to Composability",
    }
    b.finish(html, journey, "Course Enrollment Hub", port=5997)


if __name__ == "__main__":
    for dep in ("online_course_lms", "quiz_and_flashcards"):
        if not (ROOT / dep).exists():
            print(f"{dep} must be built first (python3 build_batch.py {dep})")
            raise SystemExit(2)
    build(ROOT)
    project = ROOT / "course_enrollment_hub"
    build_py_src = (HERE.parent / "build.py").read_text().replace(
        "ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project))
    raise SystemExit(res.returncode)
