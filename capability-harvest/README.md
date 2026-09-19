# Capability Harvest Pipeline — Stage 1 walking skeleton

This is the collection layer for the capability library: discover real
open-source applications, find the capabilities they genuinely implement,
locate the real attach point, harvest it with full provenance, register it,
compose it into a verified running build, and prove it against a live
running application. No invented capabilities, no fake implementations, no
mocks in the proof.

**Scope of this PR, deliberately**: one real application, one real
capability, taken all the way through every stage of the architecture. Per
the handoff: *"300 discovered ≠ 300 proven."* This proves the pipeline
end to end before it's pointed at more applications. Widening it is
explicitly future work, not started here — see "What's next" below.

## The pipeline, as built

```
OPEN-SOURCE APP POOL
        |
        v
discover_applications.py  --> discovery/applications.json  (real clone, real commit, real LICENSE-file check)
        |
        v
detect_capability.py      --> output/attach_points.json    (AST-based: route path is a HINT, not a match --
        |                                                    a candidate only counts once its body genuinely
        |                                                    calls the functions that capability requires)
        v
harvest_parts.py          --> shelf/<app>/<CAP-ID>/{implementation.py, PROVENANCE.json, LICENCE.txt}
        |
        v
shelf_records.py          --> capabilities/<CAP-ID>.json   (the registry)
        |
        v
build.py                  --> a real, running, VERIFIED composed Flask app
        |
        v
test/prove_capability_http.py     --> real HTTP proof    --> shelf/.../evidence/TEST_EVIDENCE_HTTP.json
test/prove_capability_browser.mjs --> real Playwright proof --> shelf/.../evidence/TEST_EVIDENCE_BROWSER.json
```

Every stage resolves its paths from `config.py` (`SOURCE_ROOT`,
`APPLICATION_ROOT`, `CATEGORY_SOURCE`, `REPOSITORY_SOURCE`, `OUTPUT_ROOT`,
`SHELF_ROOT`, `REGISTRY_ROOT`, `TEST_TARGET`) and prints them at startup.
No script assumes a working directory.

## The one capability harvested here

**CAP-0001 — "export data"** (capability #13 in the earlier 81-name
vocabulary), harvested from
[NHasan143/monthly-expenses-tracker](https://github.com/NHasan143/monthly-expenses-tracker)
(MIT licence, verified from its own `LICENSE` file — see
`shelf/monthly-expenses-tracker/CAP-0001/LICENCE.txt`), commit
`7fd04edb0756e8dda501ee01b98dc30de2d238b6`.

It was picked (not invented) because it's a real, working Flask app —
flask-login auth, flask-sqlalchemy models, a SQLite dev fallback so no
external database is required — with a genuine `GET /export` route
(`app/routes.py:358-381`, function `export_csv`) that builds a real CSV of
the user's expenses via `csv.writer` and returns it via `send_file`,
protected by `@login_required`.

## What each stage actually proved (re-run yourself to reproduce)

### 1. Discovery (`discovery/discover_applications.py`)
Clones the app for real, resolves the exact commit fetched, and reads
`LICENSE` — never metadata — to determine licence. Blocks (never guesses)
if no allowed licence marker is found. Output: `discovery/applications.json`.

### 2. Attach-point detection (`detection/detect_capability.py`)
Parses `app/routes.py` with Python's `ast` module. A route path
(`/export`) only narrows which function is a *candidate* — it is only
recorded as a real attach point once its body is shown to call `csv.writer`
and `send_file`. This is the same "evidence must be in the real construct,
not just nearby" principle behind the capability-evidence matcher fixed in
PR #11, applied here to routes instead of declarations. Output:
`output/attach_points.json` (line-accurate: `358-381`, matching the real
file).

### 3. Harvest (`harvest_parts.py`)
The deterministic input → output path is documented in full inside the
script's own header comment (input request JSON → applications.json +
attach_points.json lookup → absolute source path → **re-verified** symbol/
line (not trusted blindly from step 2) → `ast.get_source_segment` extraction
→ deterministic `shelf/<app>/<CAP-ID>/` output paths → serialization).

**Adversarially tested**: fed a deliberately stale line number and confirmed
it aborts loudly (`ABORT: attach point for CAP-0001 has drifted...`) rather
than silently harvesting whatever now happens to sit at that line.

Output: `shelf/monthly-expenses-tracker/CAP-0001/{implementation.py,
PROVENANCE.json, LICENCE.txt}` — provenance includes the real repo/commit/
file/symbol/line-range/licence/checksums/dependency chain.

### 4. Registry (`shelf_records.py`)
Scans the shelf, writes `capabilities/CAP-0001.json` with the one
implementation and its aliases.

### 5. Build (`build.py`)
Before starting anything, **verifies**: (a) the shelf's harvested text still
hashes to what `PROVENANCE.json` recorded, and (b) re-extracting the same
function from the live checkout right now is byte-identical to the shelved
copy. Only then does it import the app's own `create_app()` factory and
start a real Flask dev server — so what the live test below exercises is
provably the exact capability that was harvested, not merely "the app,
which happens to still work."

A real, local SMTP debug server (Python's own `smtpd.DebuggingServer`) is
started alongside it: registering a user triggers this app's own real
`send_welcome_email()` call, and this sandbox has no route to the public
internet's SMTP ports — pointing `MAIL_SERVER` at `smtp.gmail.com`
(the app's default) meant every registration blocked for a real multi-second
connect timeout. Rather than mock or skip that code path, the app's own
real `MAIL_SERVER`/`MAIL_PORT`/`MAIL_USE_TLS` env-var configuration surface
is pointed at a real (if local) SMTP server, so flask-mail still performs a
genuine SMTP conversation — it just terminates locally. The received
welcome email is captured verbatim in
`shelf/.../evidence/welcome_email_smtp_capture.log`.

### 6. Live proof (`test/prove_capability_http.py`, `test/prove_capability_browser.mjs`)

Two independent real proofs against the same running app, no mocks in
either:

- **HTTP** (`./.venv/bin/python3 test/prove_capability_http.py`): asserts
  `GET /export` redirects anonymous requests to `/login` (real access
  control, checked adversarially, not assumed), then registers a real user,
  logs in, adds a real expense via `POST /add`, requests `GET /export`, and
  parses the real CSV body to confirm the expense is in it.
- **Browser** (`node test/prove_capability_browser.mjs`, Chromium via the
  environment's pre-installed Playwright): registers through the real
  `/register` form, opens the real "+ Add Expense" modal and submits a real
  expense, navigates to `/settings`, clicks the real "Download CSV" link,
  and verifies the real downloaded file.

Both write their evidence (steps, status codes, response headers, the
actual CSV rows/content observed) to
`shelf/monthly-expenses-tracker/CAP-0001/evidence/`.

## How to reproduce this from scratch

```bash
cd capability-harvest
python3 -m venv .venv
./.venv/bin/pip install flask flask-login flask-sqlalchemy flask-bcrypt flask-mail python-dotenv requests

python3 discovery/discover_applications.py
python3 detection/detect_capability.py
python3 harvest_parts.py harvest_requests/CAP-0001.request.json
python3 shelf_records.py
python3 build.py start --cap CAP-0001

./.venv/bin/python3 test/prove_capability_http.py
NODE_PATH=/opt/node22/lib/node_modules node test/prove_capability_browser.mjs   # or adjust the absolute
                                                                                  # Playwright import path
                                                                                  # in the script for your
                                                                                  # environment

python3 build.py stop
```

## What this proves vs. what's next

**Proved, for real, in this PR:**
- Real application discovery with real licence verification from the
  source file (never metadata).
- Real AST-based attach-point detection that rejects name-only matches
  (verified against a deliberately drifted line number).
- A documented, deterministic harvest path with re-verification against
  drift, real provenance, real checksums.
- A registry stage linking shelf → capability record.
- A build stage that verifies (not assumes) the harvested code is what's
  actually running, before starting anything.
- Two independent, real, non-mocked proofs (HTTP and browser) against the
  live composed app, including a genuine negative/access-control check.

**Explicitly not yet built (do not assume it exists):**
- **Scale.** One application, one capability. Widening `categories.json`
  and `APPLICATION_MANIFEST` to the real category set and running this
  against many applications is the next real piece of work, not a copy-paste
  exercise — the licence-blocking, drift-detection, and evidence-writing all
  need to hold up under volume, not just one clean example.
- **Cross-application composition.** `build.py` verifies and mounts the
  harvested route within its *own* source application. Grafting a harvested
  capability onto a *different*, unrelated host application needs the
  dependency-binding/adapter system the original handoff calls out as
  needing the "later AST-based detection work" — this PR's AST-based
  attach-point detector is a real step toward that, but the binding layer
  itself (resolving `load_data`, `calculate_balance`, `current_user` etc.
  against a different host app's own equivalents) is not built here.
- **Non-Python, non-Flask-route capability shapes.** The attach-point
  detector currently only understands Python `ast` + Flask-style
  `@blueprint.route(...)` decorators. Other frameworks/languages need their
  own detectors following the same "evidence must be in the real construct"
  principle, not copy-pasted regex.
- **MPL-2.0 sign-off.** `config.ALLOWED_LICENCE_MARKERS` includes MPL-2.0
  but flags it (`LICENCES_REQUIRING_SIGN_OFF`) rather than silently
  accepting it, per the standing rule from the earlier capability-stockpile
  handoff. No MPL-2.0 application has been harvested here, so this hasn't
  been exercised against a real one yet.
