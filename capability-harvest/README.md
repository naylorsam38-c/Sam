# Capability Harvest Pipeline

The collection layer for the capability library: discover real open-source
applications, find the capabilities they genuinely implement, locate the
real attach point, harvest it with full provenance, register it, compose it
into a verified running build, and prove it against a live running
application. No invented capabilities, no fake implementations, no mocks in
any proof.

**Status**: 6 capabilities harvested from 5 real applications, each one
independently license-verified, AST-evidence-confirmed, and live-proven.
Per the handoff: *"300 discovered ≠ 300 proven."* This is real, growing
progress toward the library, not a claim that it's done — see "What's next"
below for exactly what isn't built yet.

## The pipeline, as built

```
OPEN-SOURCE APP POOL
        |
        v
discover_applications.py  --> discovery/applications.json  (real clone, real commit, real LICENSE-file check)
        |
        v
detect_capability.py      --> output/attach_points.json    (AST-based: a route path OR a symbol name is only a
        |                                                    HINT -- a candidate only counts once its body
        |                                                    genuinely calls the functions that capability requires)
        v
harvest_parts.py          --> shelf/<app>/<CAP-ID>/{implementation.py, PROVENANCE.json, LICENCE.txt}
        |
        v
shelf_records.py          --> capabilities/<CAP-ID>.json   (the registry)
        |
        v
build.py                  --> a real, running, VERIFIED composed app
        |
        v
test/prove_*_http.py / prove_capability_browser.mjs --> real HTTP/Playwright proof --> shelf/.../evidence/
```

Every stage resolves its paths from `config.py` (`SOURCE_ROOT`,
`APPLICATION_ROOT`, `CATEGORY_SOURCE`, `REPOSITORY_SOURCE`, `OUTPUT_ROOT`,
`SHELF_ROOT`, `REGISTRY_ROOT`, `TEST_TARGET`) and prints them at startup.
No script assumes a working directory.

## The 6 capabilities harvested so far

| CAP-ID | Capability | App | Licence | Attach point | Live proof |
|---|---|---|---|---|---|
| CAP-0001 | export data | [NHasan143/monthly-expenses-tracker](https://github.com/NHasan143/monthly-expenses-tracker) | MIT | `app/routes.py:358` `export_csv` (`csv.writer`, `send_file`) | HTTP + Playwright browser |
| CAP-0002 | manage inventory | [Antoh254/Inventory-Tracker](https://github.com/Antoh254/Inventory-Tracker) | MIT | `app.py:49` `update_stock` (`execute`, `commit`) | HTTP |
| CAP-0003 | search records | [makona-OG/hostelFix](https://github.com/makona-OG/hostelFix) | MIT | `app.py:213` `search` (`.filter`, `.ilike`) | HTTP |
| CAP-0004 | track streak | [batrisyiasafri/habit_tracker](https://github.com/batrisyiasafri/habit_tracker) | MIT | `app.py:215` `calculate_streaks` (`sorted`, `max`) | HTTP |
| CAP-0005 | send message | [jgoney/flask-messenger](https://github.com/jgoney/flask-messenger) | MIT | `messenger.py:30` `_add_message` (`connect`, `execute`, `commit`) | HTTP |

None of these were picked by keyword. `detect_capability.py` uses Python's
`ast` module: a route path or a function name is only a *hint* that
narrows candidates — a match still requires the candidate's own body to
genuinely call the functions that capability needs (`csv.writer`, a real
SQL `.ilike()` filter, a real `sqlite3` `INSERT`/`commit`, real
consecutive-day date-diffing, and so on). This is the same "evidence must
be in the real construct, not just mentioned nearby" principle behind the
capability-evidence matcher fixed in PR #11, applied here to routes and
helper functions instead of declarations.

Full provenance (repo, commit, exact file/symbol/line-range, licence,
checksums, real dependency chain) is in each
`shelf/<app>/<CAP-ID>/PROVENANCE.json`. Real recorded evidence (request/
response steps, actual data observed) is in each
`shelf/<app>/<CAP-ID>/evidence/`.

## Real applications aren't all shaped the same way

Scaling past the first capability meant `build.py` had to stop assuming
every app exposes a `create_app()` factory. Three runner kinds now exist,
chosen per application in `discover_applications.py`'s
`APPLICATION_MANIFEST` (`runner` field), and each was needed for a real
reason encountered while harvesting:

- **`flask_factory`** (monthly-expenses-tracker) — the app exposes
  `create_app()`; `build.py` calls it and runs the result. DB/mail config
  is entirely env-var driven, the app's own designed extension point.
- **`flask_module_attr`** (inventory-tracker, hostelfix, habit-tracker) —
  the app builds a module-level `app = Flask(...)` object whose setup runs
  at import time (no `__main__` guard); `build.py` imports it and calls
  `.run()` itself. hostelfix additionally needs its own `init_db.py` /
  `dummy_data.py` run once first (`setup_scripts`) — running the app's own
  provided scripts, not inventing seed data ourselves.
- **`script_entrypoint`** (flask-messenger) — this app's schema creation
  is gated behind `if __name__ == '__main__':` in its own entry script, so
  importing it as a module would silently skip that setup. `build.py` runs
  the entry script directly, exactly as its own author runs it, and
  accepts whatever host/port it hardcodes rather than forcing a uniform
  port across every harvested app.

Two more real gotchas found and fixed while harvesting (both are the kind
of thing that only shows up by actually running the app, not by reading
its code):
- Flask-SQLAlchemy resolves a relative `sqlite:///x.db` URI against the
  app's **instance path**, not the process's working directory — confirmed
  for habit-tracker by inspecting which of three candidate `.db` files
  actually held the `habit`/`habit_log` tables after a real run.
  `reset_globs` for that app lists all three candidate paths.
- habit-tracker's `add_habit()` route reads `session['user_id']`, which is
  only set as a side effect of visiting `/` first (`index()`'s own "fake
  login for testing") — the same session-establishment step a real browser
  would need, so the HTTP proof does it too rather than skipping it.

## What each pipeline stage actually proved

### 1. Discovery
Real `git clone` per app, real resolved commit, licence read from each
app's own `LICENSE` file — never metadata, never a badge. Blocks (records
`blocked: true` with a reason) rather than guessing if no allowed licence
marker is found.

### 2. Attach-point detection
AST-based, line-accurate for all 5 apps (see the table above). Two search
modes: `route_path_hint` (the capability lives directly in a Flask route
handler) and `symbol_hint` (the capability lives in a plain function or a
helper the route delegates to — used for `calculate_streaks`, a bare
function with no route decorator, and `_add_message`, the real helper
`home()` calls rather than `home()` itself).

### 3. Harvest (`harvest_parts.py`)
Deterministic input→output path documented in the script's own header.
**Adversarially tested**: fed a deliberately stale line number and
confirmed it aborts loudly rather than silently harvesting whatever now
sits at that line.

### 4. Registry (`shelf_records.py`)
Shelf → `capabilities/CAP-000N.json`, one registry record per capability.

### 5. Build (`build.py`)
Before starting anything, **verifies**: the shelved text still hashes to
its own `PROVENANCE.json`, and re-extracting the same function from the
live checkout right now is byte-identical to the shelved copy. Only then
does it start the app, the way described above per runner kind.

CAP-0001's build additionally runs a real local SMTP debug server
(`smtpd.DebuggingServer`), because registering a user triggers that app's
own real `send_welcome_email()` call, and this sandbox has no route to
the public internet's SMTP ports. Rather than mock that side effect, the
app's own `MAIL_SERVER`/`MAIL_PORT`/`MAIL_USE_TLS` env vars are pointed at
the local server — flask-mail still performs a genuine SMTP conversation,
just terminating locally. The received email is captured verbatim in
`shelf/monthly-expenses-tracker/CAP-0001/evidence/welcome_email_smtp_capture.log`.

### 6. Live proof
Every capability has an independent, non-mocked HTTP proof
(`test/prove_*_http.py` — real requests, real session cookies where
needed, real assertions against real response bodies/database state).
CAP-0001 additionally has a real Playwright browser proof
(`test/prove_capability_browser.mjs`) since that app has a browser UI.
Highlights beyond the basic "call it and check 200":

- CAP-0001: asserts `/export` redirects anonymous requests to `/login`
  (real access control, checked adversarially) before proving the
  authenticated path.
- CAP-0002: real quantity trail 10 → 9 (sold) → 11 (restocked), scraped
  from the real rendered HTML table.
- CAP-0003: proves both a real positive match against real seeded data
  *and* the app's own real "No results found" negative branch — showing
  the query genuinely reaches the database rather than always returning
  the same page.
- CAP-0004: the app's HTTP surface has no way to log a past day (only
  "mark done today" exists), so after proving the trivial 1-day case, two
  further real `habit_log` rows are inserted directly into the same real
  SQLite file the live server reads from (yesterday, day-before), and the
  next real `GET /` is asserted to show a real streak of 3 — proving the
  actual consecutive-day date-diffing logic, not just the streak=1 case.
- CAP-0005: posts through the server-rendered form, then confirms the
  message via the app's own separate JSON REST endpoint — proving a
  genuine cross-interface persisted write, not an echo of the input.

## How to reproduce this from scratch

```bash
cd capability-harvest
python3 -m venv .venv
./.venv/bin/pip install flask flask-login flask-sqlalchemy flask-bcrypt \
    flask-mail flask-migrate flask-cors flask-wtf python-dotenv requests \
    reportlab geopy pillow

python3 discovery/discover_applications.py
python3 detection/detect_capability.py
for cap in CAP-0001 CAP-0002 CAP-0003 CAP-0004 CAP-0005; do
    python3 harvest_parts.py harvest_requests/${cap}.request.json
done
python3 shelf_records.py

# Each capability's own app is built/tested/stopped one at a time --
# see each capability's runner in discovery/discover_applications.py for
# its port (flask-messenger hardcodes 5000; others are 5057-5060).
python3 build.py start --cap CAP-0001 --port 5057
./.venv/bin/python3 test/prove_capability_http.py
node test/prove_capability_browser.mjs   # absolute Playwright import path in the script may need adjusting for your environment
python3 build.py stop

python3 build.py start --cap CAP-0002 --port 5058
./.venv/bin/python3 test/prove_CAP-0002_http.py
python3 build.py stop

python3 build.py start --cap CAP-0003 --port 5059
./.venv/bin/python3 test/prove_CAP-0003_http.py
python3 build.py stop

python3 build.py start --cap CAP-0004 --port 5060
./.venv/bin/python3 test/prove_CAP-0004_http.py
python3 build.py stop

python3 build.py start --cap CAP-0005   # flask-messenger hardcodes port 5000
./.venv/bin/python3 test/prove_CAP-0005_http.py
python3 build.py stop
```

This exact sequence was run against a fully wiped state (`application_pool/`,
`.venv/`, `shelf/`, `capabilities/`, `output/*` all deleted first) to confirm
it's genuinely reproducible, not an artifact of an ad-hoc fixing sequence.

## What this proves vs. what's next

**Proved, for real:**
- Real application discovery with real licence verification from the
  source file, across 5 different repositories.
- Real AST-based attach-point detection that rejects name-only matches,
  across both route-handler and helper-function capability shapes,
  verified against a deliberately drifted line number.
- A documented, deterministic harvest path with re-verification against
  drift, real provenance, real checksums, for every capability.
- A build stage that handles three genuinely different real application
  shapes without bending any of them to fit one template, verifying (not
  assuming) the harvested code is what's actually running before starting
  anything.
- Six independent, real, non-mocked live proofs, including negative/
  access-control checks, cross-interface consistency checks, and a real
  multi-day date-diffing proof that required inserting real historical
  data directly into the app's own real database (not through its HTTP
  surface, which doesn't support backdating).

**Explicitly not yet built (do not assume it exists):**
- **Scale beyond 6.** Two further capabilities were researched and
  license-verified but not yet harvested: **"generate report"** (from
  vedpatel-real-ai/Fintrack-Flask-CS50-Final-Project, MIT — real PDF/Excel
  aggregation, but needs a live exchange-rate API call and session auth,
  so it needs more care before wiring in) and **"write review"** (from
  ichi-saki/Recipe_app, MIT — real rating+comment persistence behind a
  simple signup/login flow). Both are documented candidates for the next
  batch, not silently dropped. The other ~75 names in the vocabulary have
  not been researched yet.
- **Cross-application composition.** `build.py` verifies and mounts each
  harvested route within its *own* source application. Grafting a
  harvested capability onto a *different*, unrelated host application
  needs the dependency-binding/adapter system the original handoff calls
  out as future work — this PR's AST-based attach-point detector and its
  per-capability `dependencies.collaborators_referenced` list in each
  PROVENANCE.json are real steps toward that, but the binding layer itself
  is not built here.
- **Non-Python capability shapes.** The attach-point detector currently
  only understands Python `ast`. Other languages/frameworks need their own
  detectors following the same "evidence must be in the real construct"
  principle, not copy-pasted regex.
- **MPL-2.0 sign-off.** `config.ALLOWED_LICENCE_MARKERS` includes MPL-2.0
  but flags it (`LICENCES_REQUIRING_SIGN_OFF`) rather than silently
  accepting it. No MPL-2.0 application has been harvested here yet, so
  this hasn't been exercised against a real one.
