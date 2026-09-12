#!/usr/bin/env python3
"""
new_app_recipe_box.py — coverage-testing round, app 1 of 3: a genuinely new
domain (a shared recipe box with likes) that needed exactly ONE new generic
engine to compose cleanly.

  - Recipes list/create are plain, one-off CRUD (add_capability) -- the same
    kind every one of the 43 canonical apps already has some of; not every
    capability needs to be a shared engine, only ones that actually recur.
  - "Like Recipe" uses the NEW add_unbounded_counter_capability engine
    (gen_common.py), generalized this round from six real hand-written
    precedents (social_feed/photo_sharing likes, short_video_feed/
    video_streaming views, music_streaming/podcast plays) found by real
    audit, never generalized until now. Proven behaviourally identical to
    social_feed's original "Like Post" by direct regression test
    (prove_generalization.py).
  - The shared Notification capability, for a "recipe of the day" alert.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gen_common import AppBuilder, page_skeleton  # noqa: E402

ROOT = HERE / "library_build"


def build(root: Path):
    b = AppBuilder(root, "recipe_box", "recipe box", "9600")

    b.add_capability("9601", "List Recipes", "/api/recipes", "GET",
        "def handle(request):\n    return 200, {'recipes': _load()}\n", output_fields=("recipes",))
    b.add_capability("9602", "Create Recipe", "/api/recipes", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    recipes = _load()\n"
        "    next_id = (max([r['id'] for r in recipes], default=0)) + 1\n"
        "    recipe = {'id': next_id, 'title': title, 'likes': 0}\n"
        "    recipes.append(recipe)\n    _save(recipes)\n    return 201, recipe\n",
        output_fields=("id", "title", "likes"), required_input=("title",),
        side_effects=("creates_record",), slot_id="recipe_list", selector="#recipe-list")
    # THE NEW GENERIC ENGINE this app exists to prove out.
    b.add_unbounded_counter_capability("9603", "Like Recipe", "/api/recipes/like",
        id_field="id", counter_field="likes", entity_noun="recipe")

    b.add_notification_capabilities("9604", "9605", "9606")

    body_inner = '''<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Recipes</h2>
  <div class="row">
    <input id="recipe-title" placeholder="Recipe title" data-slot="recipe_title">
    <button id="add-recipe-btn" data-slot="add_recipe">Add recipe</button>
  </div>
  <ul id="recipe-list" data-slot="recipe_list"></ul>
</div>
<div class="card">
  <h2 style="font-size:16px;margin:0 0 8px">Your notifications</h2>
  <ul id="notification-list"></ul>
</div>'''
    script = '''
const ME = "cook@example.com";
function refreshRecipes() {
  fetch("/api/recipe_box/recipes").then(r => r.json()).then(data => {
    const list = document.getElementById("recipe-list");
    list.innerHTML = "";
    (data.recipes || []).forEach(r => {
      const li = document.createElement("li");
      li.textContent = r.title + " -- " + r.likes + (r.likes === 1 ? " like" : " likes");
      const like = document.createElement("button"); like.textContent = "Like"; like.style.marginLeft = "8px";
      like.addEventListener("click", () => {
        fetch("/api/recipe_box/recipes/like", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: r.id})}).then(r2 => r2.json()).then(updated => {
            if (updated.likes === 5) {
              fetch("/api/recipe_box/notifications", {method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({recipient: ME, message: updated.title + " just hit 5 likes!"})});
            }
            refreshRecipes(); refreshNotifications();
          });
      });
      li.appendChild(like);
      list.appendChild(li);
    });
  });
}
function refreshNotifications() {
  fetch("/api/recipe_box/notifications?recipient=" + encodeURIComponent(ME)).then(r => r.json()).then(data => {
    const list = document.getElementById("notification-list");
    list.innerHTML = "";
    (data.notifications || []).forEach(n => {
      const li = document.createElement("li");
      li.textContent = (n.read ? "" : "\\u25cf ") + n.message;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-recipe-btn").addEventListener("click", () => {
  const title = document.getElementById("recipe-title").value;
  if (!title.trim()) return;
  fetch("/api/recipe_box/recipes", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => {
      document.getElementById("recipe-title").value = "";
      refreshRecipes();
    });
});
refreshRecipes(); refreshNotifications();
'''
    html = page_skeleton("Recipe Box", "", body_inner, script)
    journey = {
        "input_selector": "#recipe-title", "input_value": "Grandma's Chili",
        "action_selector": "#add-recipe-btn",
        "confirm_selector": "text=Grandma's Chili", "confirm_contains": "Grandma's Chili",
    }
    b.finish(html, journey, "Recipe Box", port=5996)


if __name__ == "__main__":
    build(ROOT)
    project = ROOT / "recipe_box"
    build_py_src = (HERE.parent / "build.py").read_text().replace(
        "ALLOW_LAYER3 = True", "ALLOW_LAYER3 = False")
    (project / "build.py").write_text(build_py_src)
    res = subprocess.run([sys.executable, "build.py"], cwd=str(project))
    raise SystemExit(res.returncode)
