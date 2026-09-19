# Library finder + walker

Two scripts. Both open with an editable config block — one comment per setting.

## 1. find_library_apps.py — finds candidates
    pip install pyyaml --break-system-packages
    python3 find_library_apps.py                 # all 70 categories
    python3 find_library_apps.py crm blogging    # some
    python3 find_library_apps.py --regate        # re-apply the category gate to shortlists already on disk (no re-clone)
    python3 find_library_apps.py --list

Gates, in order: pre-filter (stars, last update, archived, directory licence) → licence read from the repo's own
LICENSE file → screens (user-facing template files + login evidence) → runs (compose/Dockerfile in repo)
→ CATEGORY (the app must declare itself as this kind of app in its description/README head, product names only
count as "alternative to X", and every anchor capability must be in its structural code) → robustness score →
capability coverage → rank. Output: shortlist/<slug>.json (survivors with evidence, every refusal with reason),
reports/LIBRARY_TABLE.md, reports/RUN_OUTPUT.txt.

Category vocabulary lives in categories/benchmark70.json: `keywords` (discovery), `declares` (the gate),
`capabilities` (first ANCHOR_COUNT are anchors; the whole list is walked by the walker).

## 2. walk_library_apps.py — proves them
    pip install pyyaml playwright --break-system-packages && playwright install chromium
    # needs podman (+ podman-compose) or docker; see CONTAINER_TOOL / COMPOSE_TOOL_ARGV in the config
    python3 walk_library_apps.py                 # every category with a survivor
    python3 walk_library_apps.py crm             # one
    python3 walk_library_apps.py --list

Per app: re-clone at the recorded commit → stand up from its own compose/Dockerfile → wait for the UI →
real headless Chromium → fill whatever setup/register/login forms are in the way → click through every
capability in the row → screenshots. Output: walks/<slug>/<app>/WALKTHROUGH.md, result.json, screenshots/,
reports/WALK_TABLE.md. Verdicts: BOOTED / BOOT FAILED (with the reason), gate IN / STUCK, and per capability
REACHED / SEEN / ABSENT. It proves boot, screens, get-in and reachable screens. It does not yet prove each
feature end to end — that is the next level.

Podman without systemd: put `unqualified-search-registries = ["docker.io"]` in /etc/containers/registries.conf;
the walker runs container healthchecks itself (podman only runs them under systemd).
