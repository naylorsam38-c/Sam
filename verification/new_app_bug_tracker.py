#!/usr/bin/env python3
"""
new_app_bug_tracker.py — coverage-testing round, app 2 of 3: a genuinely new
domain (a small issue tracker) that needed exactly ONE new generic engine to
compose cleanly.

  - Bugs list/create are plain, one-off CRUD (add_capability).
  - "Update Bug Status" uses the NEW add_status_transition_capability engine
    (gen_common.py), generalized this round from five real hand-written
    precedents (crm's stage, project_management's/ride_hailing's status,
    invoicing's mark-paid, parcel_tracking's status+history) found by real
    audit, never generalized until now. Proven behaviourally identical to
    crm's original "Update Contact Stage" by direct regression test
    (prove_generalization.py).
  - The shared Notification capability, for a status-change alert.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_common import AppBuilder, page_skeleton  # noqa: E402

ROOT = HERE / "library_build"


def build(root: Path):
    b = AppBuilder(root, "bug_tracker", "bug tracker", "9610")

    b.add_capability("9611", "List Bugs", "/api/bugs", "GET",
        "def handle(request):\n    return 200, {'bugs': _load()}\n", output_fields=("bugs",))
    b.add_capability("9612", "Create Bug", "/api/bugs", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    bugs = _load()\n"
        "    next_id = (max([b['id'] for b in bugs], default=0)) + 1\n"
        "    bug = {'id': next_id, 'title': title, 'status': 'open'}\n"
        "    bugs.append(bug)\n    _save(bugs)\n    return 201, bug\n",
        output_fields=("id", "title", "status"), required_input=("title",),
        side_effects=("creates_record",), slot_id="bug_list", selector="#bug-list")
    # THE NEW GENERIC ENGINE this app exists to prove out.
    b.add_status_transition_capability("9613", "Update Bug Status", "/api/bugs/status",
        id_field="id", status_field="status", status_input="status", default_status="open",
        extra_output_fields=("title",), entity_noun="bug")

    b.add_notification_capabilities("9614", "9615", "9616")

    body_inner = '''<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Bugs</h2>
  <div class="row">
    <input id="bug-title" placeholder="Bug title" data-slot="bug_title">
    <button id="add-bug-btn" data-slot="add_bug">Report bug</button>
  </div>
  <ul id="bug-list" data-slot="bug_list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Your notifications</h2>
  <ul id="notification-list"></ul>
</div>'''
    script = '''
const ME = "dev@example.com";
const NEXT_STATUS = {open: "in_progress", in_progress: "resolved", resolved: "closed", closed: "closed"};
function refreshBugs() {
  fetch("/api/bug_tracker/bugs").then(r => r.json()).then(data => {
    const list = document.getElementById("bug-list");
    list.innerHTML = "";
    (data.bugs || []).forEach(bug => {
      const li = document.createElement("li");
      li.textContent = bug.title + " -- " + bug.status;
      const advance = document.createElement("button");
      advance.textContent = "Advance"; advance.style.marginLeft = "8px";
      advance.addEventListener("click", () => {
        const next = NEXT_STATUS[bug.status] || "open";
        fetch("/api/bug_tracker/bugs/status", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: bug.id, status: next})}).then(r2 => r2.json()).then(updated => {
            fetch("/api/bug_tracker/notifications", {method: "POST", headers: {"Content-Type": "application/json"},
              body: JSON.stringify({recipient: ME, message: updated.title + " is now " + updated.status})});
            refreshBugs(); refreshNotifications();
          });
      });
      li.appendChild(advance);
      list.appendChild(li);
    });
  });
}
function refreshNotifications() {
  fetch("/api/bug_tracker/notifications?recipient=" + encodeURIComponent(ME)).then(r => r.json()).then(data => {
    const list = document.getElementById("notification-list");
    list.innerHTML = "";
    (data.notifications || []).forEach(n => {
      const li = document.createElement("li");
      li.textContent = (n.read ? "" : "\\u25cf ") + n.message;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-bug-btn").addEventListener("click", () => {
  const title = document.getElementById("bug-title").value;
  if (!title.trim()) return;
  fetch("/api/bug_tracker/bugs", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => {
      document.getElementById("bug-title").value = "";
      refreshBugs();
    });
});
refreshBugs(); refreshNotifications();
'''
    html = page_skeleton("Bug Tracker", "", body_inner, script)
    journey = {
        "input_selector": "#bug-title", "input_value": "Login button unresponsive",
        "action_selector": "#add-bug-btn",
        "confirm_selector": "text=Login button unresponsive", "confirm_contains": "Login button unresponsive",
    }
    b.finish(html, journey, "Bug Tracker", port=5995)


if __name__ == "__main__":
    build(ROOT)
    project = ROOT / "bug_tracker"
    build_py_src = (HERE.parent / "build.py").read_text().replace(
        "ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project))
    raise SystemExit(res.returncode)
