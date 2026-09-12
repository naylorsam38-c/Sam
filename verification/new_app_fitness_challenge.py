#!/usr/bin/env python3
"""
new_app_fitness_challenge.py — second new app, proving a DIFFERENT
combination than community_event_board: capabilities/engines never
combined with each other before.

  - add_bounded_counter_capability (generalized from event_ticketing,
    proven equivalent by regression test) reused again, in a THIRD domain
    now (challenge participant slots -- not ticket sales, not RSVPs).
  - add_symmetric_relationship_capability (generalized from dating) reused
    for "workout buddy" mutual matching -- a domain with nothing to do with
    dating, proving the engine generalizes past the one thing it was built
    to replace.
  - A real, unmodified capability FILE reused verbatim from fitness_tracking
    (CAP-3801/3802, List/Log Workout) -- a different source app than
    community_event_board's team_chat reuse.
  - The shared Notification capability, for a buddy-match alert.
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
    b = AppBuilder(root, "fitness_challenge_board", "fitness challenge board", "9800")

    # Real, unmodified capability files reused verbatim from fitness_tracking.
    fitness_shelf = HERE / "library_build" / "fitness_tracking" / "shelf"
    b.reuse_capability_verbatim(fitness_shelf, "CAP-3801")  # List Workouts
    b.reuse_capability_verbatim(fitness_shelf, "CAP-3802", slot_id="workout_list",
                                 selector="#workout-list", side_effects=("creates_record",))  # Log Workout

    # Challenges, with a participant-slot bounded counter -- generalized
    # engine, third distinct domain.
    b.add_capability("9801", "List Challenges", "/api/challenges", "GET",
        "def handle(request):\n    return 200, {'challenges': _load()}\n",
        output_fields=("challenges",), data_filename="challenges.json")
    b.add_capability("9802", "Create Challenge", "/api/challenges", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    try:\n        max_participants = int(body.get('max_participants', 4) or 4)\n"
        "    except (TypeError, ValueError):\n        max_participants = 4\n"
        "    challenges = _load()\n"
        "    next_id = (max([c['id'] for c in challenges], default=0)) + 1\n"
        "    ch = {'id': next_id, 'title': title, 'max_participants': max_participants, 'participants': 0}\n"
        "    challenges.append(ch)\n    _save(challenges)\n    return 201, ch\n",
        output_fields=("id", "title", "max_participants", "participants"), required_input=("title",),
        side_effects=("creates_record",), data_filename="challenges.json",
        slot_id="challenge_list", selector="#challenge-list")
    b.add_bounded_counter_capability("9803", "Join Challenge", "/api/challenges/join",
        id_field="id", counter_field="participants", limit_field="max_participants",
        fail_message="challenge is full", entity_noun="challenge", extra_output_fields=("title",),
        data_filename="challenges.json")

    # Workout-buddy matching -- symmetric-relationship engine, new domain.
    b.add_symmetric_relationship_capability("9804", "Propose Workout Buddy", "/api/buddy_requests",
        from_field="requester_id", to_field="target_id", positive_field="interested",
        match_field="paired")

    # Shared Notification capability.
    b.add_notification_capabilities("9805", "9806", "9807")

    body_inner = '''<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Challenges</h2>
  <div class="row">
    <input id="ch-title" placeholder="Challenge title" data-slot="ch_title">
    <input id="ch-max" type="number" value="2" placeholder="Max participants" data-slot="ch_max" style="width:90px">
    <button id="add-challenge-btn" data-slot="add_challenge">Create challenge</button>
  </div>
  <ul id="challenge-list" data-slot="challenge_list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Workouts <span style="font-weight:normal;color:#888;font-size:12px">(reused verbatim from fitness_tracking)</span></h2>
  <ul id="workout-list" data-slot="workout_list"></ul>
</div>'''
    script = '''
function refreshChallenges() {
  fetch("/api/fitness_challenge_board/challenges").then(r => r.json()).then(data => {
    const list = document.getElementById("challenge-list");
    list.innerHTML = "";
    (data.challenges || []).forEach(c => {
      const li = document.createElement("li");
      li.textContent = c.title + " -- " + c.participants + "/" + c.max_participants;
      const join = document.createElement("button"); join.textContent = "Join"; join.style.marginLeft = "8px";
      join.addEventListener("click", () => {
        fetch("/api/fitness_challenge_board/challenges/join", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: c.id})}).then(refreshChallenges);
      });
      li.appendChild(join);
      list.appendChild(li);
    });
  });
}
function refreshWorkouts() {
  fetch("/api/fitness_tracking/workouts").then(r => r.json()).then(data => {
    const list = document.getElementById("workout-list");
    list.innerHTML = "";
    (data.workouts || []).forEach(w => {
      const li = document.createElement("li");
      li.textContent = w.type + " -- " + w.duration + " min";
      list.appendChild(li);
    });
  });
}
document.getElementById("add-challenge-btn").addEventListener("click", () => {
  const title = document.getElementById("ch-title").value;
  const max_participants = document.getElementById("ch-max").value;
  if (!title.trim()) return;
  fetch("/api/fitness_challenge_board/challenges", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, max_participants: max_participants})}).then(() => {
      document.getElementById("ch-title").value = "";
      refreshChallenges();
    });
});
refreshChallenges(); refreshWorkouts();
'''
    html = page_skeleton("Fitness Challenge Board", "", body_inner, script)
    journey = {
        "input_selector": "#ch-title", "input_value": "5K Steps Challenge",
        "action_selector": "#add-challenge-btn",
        "confirm_selector": "text=5K Steps Challenge", "confirm_contains": "5K Steps Challenge",
    }
    b.finish(html, journey, "Fitness Challenge Board", port=5998)


if __name__ == "__main__":
    if not (ROOT / "fitness_tracking").exists():
        print("fitness_tracking must be built first (python3 build_batch.py fitness_tracking)")
        raise SystemExit(2)
    build(ROOT)
    project = ROOT / "fitness_challenge_board"
    build_py_src = (HERE.parent / "build.py").read_text().replace(
        "ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project))
    raise SystemExit(res.returncode)
