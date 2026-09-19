# SelfHostIndex → tested → completed library

One script: `top_selfhostindex_apps.py`. It sits beside `find_library_apps.py` and
`walk_library_apps.py` and uses their code for every gate, boot and login — no rule is
written twice.

## What it does, per category (all 55 on selfhostindex.com)

1. Reads the category page live. Ranks apps by SelfHostIndex's health score, then stars.
2. Drops archived apps and apps whose listed licence isn't in the allowed list.
3. Top app first: clones it at a pinned commit and runs the finder's gates — licence
   read from the repo's own file, screens + login, container recipe.
4. Deep licence check: every licence file in the repo, plus mixed-licence wording in the
   root file. (This is what caught Rocket.Chat — MIT on the front, Enterprise licence inside.)
5. Boots it from its own recipe, opens it in Playwright Chromium, gets in.
6. Visits every screen it can reach, clicks every button and link, screenshots every
   screen and every click that changed something, records what each click did.
7. **Pass** = booted, got in, at least 5 clicks, no click caused a server error or a
   crashed/blank page. JS errors are recorded but don't fail it (config switch).
8. Pass → copied into `library_completed/<category>/` (ENTRY.json, TEST_REPORT.md,
   screenshots). Fail at any step → next app down the list. Up to 6 apps per category,
   then NONE ADMITTED.

Destructive buttons (delete, logout, reset, uninstall…) are recorded but not clicked.
The list is in config.

## Run

    python3 top_selfhostindex_apps.py --list          # the 55 categories and counts
    python3 top_selfhostindex_apps.py                 # all 55
    python3 top_selfhostindex_apps.py crm-erp wikis   # just these

Stop it any time. Rerun and it skips categories already in the library.

## Results

- `library_completed/LIBRARY.md` — the completed library, one row per admitted app
- `selfhostindex/TOP_APPS.md` — all 55 rows, including NONE ADMITTED and why
- `selfhostindex/tests/<category>/<app>/TEST_REPORT.md` — every screen, every click,
  for every app tested, passed or failed
- `selfhostindex/categories/<slug>.json` — every refusal with its reason

## Machine setup (Linux)

    apt-get install -y podman runc git
    pip install podman-compose pyyaml playwright --break-system-packages
    python3 -m playwright install chromium

    # podman must pull Docker Hub short names
    echo 'unqualified-search-registries = ["docker.io"]' >> /etc/containers/registries.conf

On hosts with hybrid cgroups (crun fails with "cgroups in hybrid mode not supported"),
put this in `/etc/containers/containers.conf` — found and proven on 2026-09-19, nginx
served 200 after it:

    [containers]
    volumes = ["/etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro"]
    [engine]
    runtime = "runc"
    cgroup_manager = "cgroupfs"
    events_logger = "file"

The script checks podman, compose and image pulls before it starts and stops with the
fix if any is broken.

## What's proven, what isn't

Proven live 2026-09-19: the category read (55 categories, 3,530 listings, matches the
site), the gate + deep licence stages on Team Chat and Project Management (Rocket.Chat
refused on its Enterprise licence, Zulip picked; Super Productivity picked).

Not yet run: the Playwright button test and library admission. Written and lint-clean,
not executed — first real run is the test.
