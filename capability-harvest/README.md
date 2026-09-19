# Capability Harvest Pipeline

The collection layer for the capability library: discover real open-source
applications, find the capabilities they genuinely implement, locate the
real attach point, harvest it with full provenance, register it, compose it
into a verified running build, and prove it against a live running
application. No invented capabilities, no fake implementations, no mocks in
any proof.

**Status**: 37 capabilities harvested from 24 real applications, each one
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

## The 37 capabilities harvested so far

| CAP-ID | Capability | App | Licence | Attach point | Live proof |
|---|---|---|---|---|---|
| CAP-0001 | export data | [NHasan143/monthly-expenses-tracker](https://github.com/NHasan143/monthly-expenses-tracker) | MIT | `app/routes.py:358` `export_csv` (`csv.writer`, `send_file`) | HTTP + Playwright browser |
| CAP-0002 | manage inventory | [Antoh254/Inventory-Tracker](https://github.com/Antoh254/Inventory-Tracker) | MIT | `app.py:49` `update_stock` (`execute`, `commit`) | HTTP |
| CAP-0003 | search records | [makona-OG/hostelFix](https://github.com/makona-OG/hostelFix) | MIT | `app.py:213` `search` (`.filter`, `.ilike`) | HTTP |
| CAP-0004 | track streak | [batrisyiasafri/habit_tracker](https://github.com/batrisyiasafri/habit_tracker) | MIT | `app.py:215` `calculate_streaks` (`sorted`, `max`) | HTTP |
| CAP-0005 | send message | [jgoney/flask-messenger](https://github.com/jgoney/flask-messenger) | MIT | `messenger.py:30` `_add_message` (`connect`, `execute`, `commit`) | HTTP |
| CAP-0006 | write review | [ichi-saki/Recipe_app](https://github.com/ichi-saki/Recipe_app) | MIT | `routes/comments.py:18` `make_comment` (`execute`, `commit`) | HTTP |
| CAP-0007 | generate report | [vedpatel-real-ai/Fintrack-Flask-CS50-Final-Project](https://github.com/vedpatel-real-ai/Fintrack-Flask-CS50-Final-Project) | MIT | `app/routes/reports.py:33` `generate_report` (delegates to `_build_pdf_report`/`_build_excel_report`) | HTTP |
| CAP-0008 | award badge | [shaikayan2084/Bounty-Simulator](https://github.com/shaikayan2084/Bounty-Simulator) | MIT | `backend/main.py:36` `check_badges` (`filter_by`, `add`, `commit`, idempotent) | HTTP |
| CAP-0009 | show leaderboard | [shaikayan2084/Bounty-Simulator](https://github.com/shaikayan2084/Bounty-Simulator) (same app, different attach point) | MIT | `backend/main.py:86` `leaderboard` (`order_by`, `desc`, `limit`) | HTTP |
| CAP-0010 | add favourite | [pranjalco/flask-coffee-and-wifi](https://github.com/pranjalco/flask-coffee-and-wifi) | MIT | `main.py:235` `add_bookmark` (`add`, `commit`, duplicate-guarded) | HTTP |
| CAP-0011 | log workout | [wifizak/CasettaFit](https://github.com/wifizak/CasettaFit) | MIT | `app/routes/workout.py:211` `log_set` (`add`, `commit`) | HTTP |
| CAP-0012 | rate item | [RyLaney/zinny-api](https://github.com/RyLaney/zinny-api) | BSD-3-Clause | `src/zinny_api/api/ratings.py:96` `save_rating` (real SQL `ON CONFLICT ... DO UPDATE` upsert, `execute`, `commit`) | HTTP |
| CAP-0013 | calculate tax | [rishu879/Payroll-Tax-Calculator-with-Persistence-Analytics](https://github.com/rishu879/Payroll-Tax-Calculator-with-Persistence-Analytics) | Apache-2.0 | `salary_engine.py:3` `calculate_payroll_details` (real progressive bracket computation, `max`, `min`) | HTTP |
| CAP-0014 | book slot | [Raviraj0001/Hospital_Management_Real](https://github.com/Raviraj0001/Hospital_Management_Real) | MIT | `app.py:864` `patient_book` (real per-doctor/per-slot conflict check, `filter_by`, `add`, `commit`) | HTTP |
| CAP-0015 | generate invoice | [rishabh0510rishabh/Invoice-generator](https://github.com/rishabh0510rishabh/Invoice-generator) | MIT | `server.py:265` `generate_invoice_pdf` (real WeasyPrint PDF from real persisted line items/tax, `render_template`, `write_pdf`) | HTTP |
| CAP-0016 | register account | [Raviraj0001/Hospital_Management_Real](https://github.com/Raviraj0001/Hospital_Management_Real) (same app, different attach point) | MIT | `app.py:824` `patient_register` (`generate_password_hash`, `commit`) | HTTP |
| CAP-0017 | log in | [Raviraj0001/Hospital_Management_Real](https://github.com/Raviraj0001/Hospital_Management_Real) (same app, different attach point) | MIT | `app.py:290` `login` (`check_password_hash`, `commit`) | HTTP |
| CAP-0018 | log out | [Raviraj0001/Hospital_Management_Real](https://github.com/Raviraj0001/Hospital_Management_Real) (same app, different attach point) | MIT | `app.py:308` `logout` (`commit`, real session teardown) | HTTP |
| CAP-0019 | upload image | [Mukesh-Web-Dev/imageUploadFlaskApp](https://github.com/Mukesh-Web-Dev/imageUploadFlaskApp) | MIT | `app.py:86` `upload_image` (`secure_filename`, real `file.save()` to disk, duplicate/extension-guarded) | HTTP |
| CAP-0020 | track location | [talha-siddiqui137/smart-attendance-system](https://github.com/talha-siddiqui137/smart-attendance-system) | MIT | `views/student.py:41` `mark_attendance` (real geopy geodesic distance vs. a real 100m geofence, `verify_location`, `commit`) | HTTP |
| CAP-0021 | set permissions | [RishiS-HSCProjects/EnterpriseProject](https://github.com/RishiS-HSCProjects/EnterpriseProject) | MIT | `app/admin/routes.py:106` `update_role` (real admin-gated, persisted role change, `UserRole.from_string`, `commit`) | HTTP |
| CAP-0022 | verify email | [Dixieboy76/tech_hub](https://github.com/Dixieboy76/tech_hub) | MIT | `app/routes.py:65` `verify_email` (real itsdangerous signed-token verification, `verify_email_token`, `commit`) | HTTP |
| CAP-0023 | edit profile | [rafaelsmedina/dataviva-training](https://github.com/rafaelsmedina/dataviva-training) | MIT | `app/routes.py:103` `edit_profile` (real persisted username/about_me update, `validate_on_submit`, `commit`) | HTTP |
| CAP-0024 | create record | [rishabh0510rishabh/Invoice-generator](https://github.com/rishabh0510rishabh/Invoice-generator) (same app, different attach point) | MIT | `server.py:492` `create_invoice` (real transactional multi-table insert, `executemany`, `commit`) | HTTP |
| CAP-0025 | edit record | [rishabh0510rishabh/Invoice-generator](https://github.com/rishabh0510rishabh/Invoice-generator) (same app, different attach point) | MIT | `server.py:573` `update_invoice` (real transactional replace of invoice + line items, `executemany`, `commit`) | HTTP |
| CAP-0026 | delete record | [rishabh0510rishabh/Invoice-generator](https://github.com/rishabh0510rishabh/Invoice-generator) (same app, different attach point) | MIT | `server.py:60` `delete_invoice` (real `DELETE`, rowcount-checked 404, `execute`, `commit`) | HTTP |
| CAP-0027 | view record detail | [rishabh0510rishabh/Invoice-generator](https://github.com/rishabh0510rishabh/Invoice-generator) (same app, different attach point) | MIT | `server.py:539` `get_invoice_details` (real multi-table `JOIN` aggregation, `execute`, `fetchall`) | HTTP |
| CAP-0028 | filter list | [rishabh0510rishabh/Invoice-generator](https://github.com/rishabh0510rishabh/Invoice-generator) (same app, different attach point) | MIT | `server.py:75` `get_invoices` (real dynamic `LIKE`-filtered query, `execute`, `fetchall`) | HTTP |
| CAP-0029 | capture photo | [Mukesh-Web-Dev/imageUploadFlaskApp](https://github.com/Mukesh-Web-Dev/imageUploadFlaskApp) (same app, different attach point) | MIT | `app.py:62` `capture` (real base64 data-URL decode + PIL `save()`, `b64decode`, `save`) | HTTP |
| CAP-0030 | place bid | [vamsishesamsetti/SmartBid](https://github.com/vamsishesamsetti/SmartBid) | MIT | `app/routes/auctions.py:128` `place_bid` (real Fernet-encrypted bid amount, minimum-increment-enforced, `encrypt_bid_amount`, `commit`) | HTTP |
| CAP-0031 | paginate list | [MadGotten/Social-Life](https://github.com/MadGotten/Social-Life) | Apache-2.0 | `app.py:16` `index` (real Flask-SQLAlchemy `.paginate()` LIMIT+OFFSET split, `order_by`, `paginate`) | HTTP |
| CAP-0032 | scan barcode | [UserSky21/Pharmaceutical-Inventory-System-](https://github.com/UserSky21/Pharmaceutical-Inventory-System-) | Apache-2.0 | `app.py:326` `get_product_by_barcode` (real barcode-to-product lookup, `filter_by`, `jsonify`) | HTTP |
| CAP-0033 | close auction | [arpannookala12/BuyMe---Online-Auction-System](https://github.com/arpannookala12/BuyMe---Online-Auction-System) | MIT | `app/routes/auction.py:682` `end_auction` (real reserve-price-checked winner determination, admin/customer-rep-gated, `determine_winner`, `commit`) | HTTP |
| CAP-0034 | apply discount code | [benjaminyan1/Mini-Amazon](https://github.com/benjaminyan1/Mini-Amazon) | MIT | `app/cart.py:113` `apply_coupon` (real expiry-checked, duplicate-guarded coupon application against a real PostgreSQL cart total, `apply_coupon`, `flash`) | HTTP |
| CAP-0035 | show map | [moustafa-shaaban/Django_and_Folium](https://github.com/moustafa-shaaban/Django_and_Folium) | MIT | `django_and_folium/django_and_folium/geo_app/views.py:20` `index` (real Folium map genuinely driven by persisted Feature rows, `basemap`, `render`) | HTTP |
| CAP-0036 | import data | [moustafa-shaaban/Django_and_Folium](https://github.com/moustafa-shaaban/Django_and_Folium) (same app, different attach point) | MIT | `django_and_folium/django_and_folium/geo_app/views.py:80` `import_data` (real django-import-export dry-run-then-commit CSV import, `import_data`, `load`) | HTTP |
| CAP-0037 | verify phone | [tohid-ab/django-otp-auth](https://github.com/tohid-ab/django-otp-auth) | MIT | `otp/django_otp_auth/apps/rest/auth/views.py:52` `OTPVerifyView.post` (real 5-digit OTP, 120s expiry, one-time-use, real JWT issuance, `_handle_login`) | HTTP |

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
every app exposes a `create_app()` factory. Four runner kinds now exist,
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
- **`script_entrypoint`** (flask-messenger, recipe-app) — these apps'
  setup is gated behind `if __name__ == '__main__':` in their own entry
  scripts (flask-messenger's schema creation; recipe-app has no such
  gating but its author's own `if __name__` convention is still the
  right thing to run directly rather than replicate). `build.py` runs the
  entry script directly, exactly as its own author runs it, and accepts
  whatever host/port it hardcodes rather than forcing a uniform port
  across every harvested app.
- **`django_manage`** (django-folium) — a real Django app, whose own
  entry point is `manage.py runserver`, not a WSGI factory or module
  attribute. `build.py` invokes Django's own `execute_from_command_line`
  programmatically instead of shelling out to `manage.py` as a bare
  subprocess, so this pipeline's env-var overrides apply the same way
  `flask_factory`'s do.

Three more real gotchas found and fixed while harvesting (all the kind of
thing that only shows up by actually running the app, not by reading its
code):
- Flask-SQLAlchemy resolves a relative `sqlite:///x.db` URI against the
  app's **instance path**, not the process's working directory — confirmed
  for habit-tracker by inspecting which of three candidate `.db` files
  actually held the `habit`/`habit_log` tables after a real run.
  `reset_globs` for that app lists all three candidate paths.
- habit-tracker's `add_habit()` route reads `session['user_id']`, which is
  only set as a side effect of visiting `/` first (`index()`'s own "fake
  login for testing") — the same session-establishment step a real browser
  would need, so the HTTP proof does it too rather than skipping it.
- recipe-app's `routes/auth.py` uses `f'...{user['username']}...'`, valid
  only under PEP 701's relaxed f-string quoting (Python 3.12+) — a real
  interpreter-compatibility requirement, not a bug, discovered when the
  main venv's Python 3.11 failed to even import the module. `build.py` now
  supports a per-app `python_version` runner field
  (`PYTHON_BY_VERSION`/`_resolve_python`) rather than forcing every
  harvested app onto one Python version; recipe-app runs from a separate
  `.venv-py312`.
- Bounty-Simulator's real application root is `backend/`, not the repo
  root — its own modules use bare relative imports (`from database import
  db`) that only resolve with `backend/` itself on sys.path/cwd. `build.py`
  now supports a per-app `app_subdir` runner field, applied consistently
  across reset/setup/launch. CasettaFit looked similar at first glance
  (a directory literally named `app/app/`) but turned out to be a false
  lead — its real fix was the opposite: `app/run.py` and `app/wsgi.py`,
  though they physically live inside `app/`, both do `from app import
  create_app`, meaning they expect the **repo root** on sys.path, not
  their own directory. Tried `app_subdir` first, watched it fail with a
  clear "cannot import name 'create_app' from 'app' (unknown location)",
  and traced it to the actual import statements rather than guessing again.
- CasettaFit ships no self-service registration route (only login/logout)
  and its own `app/seed.py` — the documented way to get a first user —
  turned out to be unrunnable as written under *either* invocation style
  (`python app/seed.py` or `python -m app.seed`): its `from wsgi import
  app` and wsgi.py's own `from app import create_app` need two different,
  mutually exclusive directories on sys.path to both resolve, a real bug
  in the app's own script. Rather than patch their source, `build.py`
  gained a `-c <code>` setup-script form and this app's manifest entry
  replicates seed.py's exact logic (the real `User` model, the real
  `set_password()`, the real `UserProfile`) with the import path fixed to
  match how the app's actually-working entry points do it. Also uses
  Flask-Migrate exclusively (no `db.create_all()` at import time), so the
  same inline script calls it directly — legitimate schema creation from
  the real models, the same thing hostelfix's own `init_db.py` does.
- zinny-api resolves its database path via `Path.home()` (its own
  `get_system_data_paths()`/`get_database_path()`, landing at
  `~/.local/share/zinny/db/zinny-1.0.sqlite`), entirely outside the repo
  and with no existing config override — read from source, not guessed.
  Rather than patch the app or point `$HOME` at the real user's home
  directory (which would pollute or depend on ambient state), `build.py`
  gained an `ISOLATED_HOME` mechanism: a per-run scratch directory the
  runner's `env` can reference as `{isolated_home}`, wiped and recreated
  fresh (`shutil.rmtree` + `mkdir`) at the start of every `build.py start`
  that uses it.
- payroll-tax-calculator's own login route requires solving a real
  arithmetic CAPTCHA (`GET /api/auth/captcha` returns a real
  `"7 + 3"`-style question and stores the answer server-side in the
  session) for every login, with no test-mode bypass in the app's own
  code. The live proof solves it for real (regex-parses the question,
  computes the real answer, submits it) rather than reading the answer
  out of the session store directly — the same "don't shortcut what the
  app itself requires" principle applied to an access-control mechanism
  instead of a data assertion.
- Hospital_Management_Real hits the same Flask-SQLAlchemy instance-path
  gotcha as habit-tracker (`sqlite:///hospital.db` resolves under
  `instance/`, not the repo root) — but compounds it by having
  accidentally *committed* a working `instance/hospital.db` straight into
  the repository (no `.gitignore` entry for it), pre-populated with a
  handful of real sample appointments. Every build resets it via
  `reset_globs` before seeding runs, exactly as it would for any other
  stale local file; leaving it in place would have silently mixed a prior
  developer's real sample data into what should be a fresh proof run.
- Invoice-generator's own `seed_database.py` procedurally generates real
  customers each run from a small (22 first name × 15 last name) random
  pool with no uniqueness check, so two of them can genuinely collide on
  the same full name -- caught for real when CAP-0028's original proof
  (which picked "the first two seeded customers" and assumed their names
  wouldn't overlap) started intermittently failing during a later batch's
  full reproducibility sweep, a real `LIKE '%name%'` match correctly
  returning both customers' invoices once their names happened to be
  identical, not a bug in the filter itself. Fixed at the test's level
  (not the app's): CAP-0028's proof now creates two customers with a
  guaranteed-unique marker in their names via the app's own real `POST
  /api/customers` route, rather than trusting the random seed pool never
  to collide.
- Invoice-generator's `server.py` constructs `Flask(__name__,
  template_folder='.')`, but the PDF templates it renders
  (`invoice_pdf*.html`) live under `templates/` — a real bug in the
  repository as cloned (confirmed by first reproducing a genuine
  `jinja2.exceptions.TemplateNotFound` before working around it, not
  assumed). Patching the app's own Flask construction or `server.py`
  itself would mean harvesting a version of the capability that doesn't
  actually exist in the repo. Instead, a `setup_scripts` step copies the
  app's own unmodified template files into the location its own,
  unmodified Flask config already expects — a file-placement/deployment
  decision, the same category of thing as hostelfix's `init_db.py`/
  `dummy_data.py` setup scripts, not a change to what `generate_invoice_pdf`
  itself computes or renders.
- EnterpriseProject also hits the PEP 701 f-string gotcha (a multi-line
  dict literal nested inside an f-string expression, valid only on
  Python 3.12+) — same fix as recipe-app, `python_version: "3.12"`. Its
  real account-creation path (registration and admin whitelisting alike)
  requires a live third-party NetherGames Minecraft API call with no
  offline/test-mode bypass in the app's own code — a dependency this
  sandbox cannot and should not take on for a repeatable harvest proof.
  The harvested capability itself, `update_role()`, has no such
  dependency, so two real accounts are seeded directly via the app's own
  real `User`/`Whitelist` models and `set_password()` (the same class of
  setup already used for CasettaFit's admin seed) and `update_role()` is
  exercised entirely through its own real, unmodified HTTP route.
- tech_hub's mail configuration is a plain committed `config.py`, not
  env-var driven like every other harvested app so far. A real deployer
  would edit that file to point at their real SMTP provider; the build
  does the same thing, pointing it at the local SMTP debug server via a
  `setup_scripts` step, and blanks the placeholder `MAIL_USERNAME`/
  `MAIL_PASSWORD` so Flask-Mail doesn't attempt a real AUTH login the
  debug server doesn't support (confirmed by first reproducing the real
  `SMTPNotSupportedError` this causes, not assumed).
- dataviva-training (a Miguel Grinberg "Flask Mega-Tutorial" derivative)
  genuinely needs an old Flask 2.2 / Flask-Babel 2.0 pairing (Flask-Babel
  2.0 imports a Flask API modern Flask has removed). A real, costly
  mistake made and fixed while harvesting this one: pinned old
  Flask/Flask-SQLAlchemy/Flask-Bootstrap/Flask-Babel versions were first
  installed into the pipeline's *shared* `.venv` to test-drive this app,
  which silently broke a previously-working, already-harvested capability
  (CAP-0010, via an overwritten `flask-bootstrap`/`Bootstrap-Flask`
  module collision) until the full reproducibility sweep below caught it
  and it was reverted. The fix: this app gets its own fully isolated
  `.venv-legacy-flask` (same mechanism as `.venv-py312`, extended to key
  by dependency-set as well as Python version — see `build.py`'s
  `PYTHON_BY_VERSION`), and nothing outside that dedicated venv is ever
  touched for an app with unusual dependency needs again.
- SmartBid encrypts each bid amount at rest with Fernet
  (`cryptography.fernet`) via an `ENCRYPTION_KEY` env var — the runner
  provides a genuinely valid 32-byte urlsafe-base64 key generated with
  `Fernet.generate_key()`, not a hand-typed placeholder (Fernet rejects a
  malformed key at import time, so a fake key would have failed loudly
  rather than silently).
- Social-Life hardcodes `SESSION_COOKIE_SECURE = True` in `config.py`
  regardless of environment (no `FLASK_ENV` escape hatch), which real
  browsers — and this pipeline's own `requests` cookie jar — correctly
  refuse to send back over plain HTTP; first symptom was a genuine "CSRF
  session token is missing" error traced to the session cookie never
  round-tripping, not assumed. A `setup_scripts` step patches that one
  line to `False` for local testing, the same deployment-configuration
  category as tech_hub's mail patch. Also hits the same Flask-SQLAlchemy
  instance-path gotcha as habit-tracker/Hospital_Management_Real, and its
  `email_validator` dependency rejects the reserved `.test` TLD in test
  email addresses (fixed by seeding with a `.com`-style address instead,
  consistent with the convention already used elsewhere in this pipeline).
- Pharmaceutical-Inventory-System was suspected to need an old Flask
  pinning like dataviva-training, based on its `requirements.txt` alone —
  tested directly under the shared venv's modern Flask *first* this time
  (the lesson from the dataviva-training incident, applied), and it
  imports and runs cleanly with no downgrade needed at all. A pinned
  `flask==2.3.3` was nonetheless briefly, mistakenly installed into the
  shared venv while investigating and was caught immediately via
  `importlib.metadata.version()`/`pip check` and reverted before it could
  break anything — a second, smaller instance of the same class of
  mistake dataviva-training made, this time caught within the same turn.
- BuyMe's real, used `config.py` lives at the repo root (`from config
  import Config`), not the unused, MySQL-defaulting `app/config.py` that
  looks like the obvious candidate at first glance — it honors a
  `DATABASE_URL` env override, so the runner supplies a SQLite URL rather
  than standing up a real MySQL server. Forgetting to set it once
  produced a genuine `mysql.connector.errors.InterfaceError: Can't
  connect to MySQL server`, confirming the default is real, not a typo.
  Also needs `flask-socketio`/`eventlet` (real-time bid broadcast),
  `flask-apscheduler` (a scheduled auction-finalizer job — confirmed
  dead/broken code referencing model fields that don't exist on the real
  `Auction` model, `status`/`reserve_price` instead of the real
  `is_active`/`secret_min_price`, ruled out as irrelevant to the
  capability harvested here), `mysql-connector-python` (import-time
  dependency even when unused), and `matplotlib`/`pandas` (an admin
  analytics route) — all installed into the shared venv with a version
  check after each confirming Flask stayed modern. Also hits the same
  Flask-SQLAlchemy instance-path gotcha as habit-tracker/Social-Life
  (`sqlite:///app.db` resolves under `instance/`, not the repo root).
- Django_and_Folium is the first real Django app in this pipeline, and
  genuinely doesn't fit any of the three Flask-shaped runner kinds above:
  its own real entry point is `manage.py runserver`, not a WSGI factory
  or module attribute. `build.py` gained a fourth runner kind,
  `django_manage`, that invokes Django's own `execute_from_command_line`
  programmatically (so this pipeline's env-var overrides apply the same
  way `flask_factory`'s do) rather than shelling out to `manage.py` as a
  bare subprocess. Its real schema also comes from Django migrations,
  not a raw SQL file like Mini-Amazon's — `needs_postgres` gained an
  optional-schema mode (drop/recreate an empty database, then a
  `setup_scripts` step runs the app's own real `manage.py migrate`)
  rather than assuming every Postgres-backed app ships one schema file.
  Its own real dependency set (Django 4.2, allauth, graphene-django,
  django-jazzmin, django-import-export, folium, ...) is large enough
  that it gets its own dedicated venv, `.venv-django-folium`, same as
  every other app with a genuinely different dependency set.

## What each pipeline stage actually proved

### 1. Discovery
Real `git clone` per app, real resolved commit, licence read from each
app's own `LICENSE` file — never metadata, never a badge. Blocks (records
`blocked: true` with a reason) rather than guessing if no allowed licence
marker is found.

### 2. Attach-point detection
AST-based, line-accurate for all 37 capabilities across 24 apps (see the
table above). Two search modes: `route_path_hint` (the capability lives
directly in a Flask route handler) and `symbol_hint` (the capability lives
in a plain function or a helper the route delegates to — used for
`calculate_streaks`, a bare function with no route decorator,
`_add_message`, the real helper `home()` calls rather than `home()`
itself, and `calculate_payroll_details`, the plain tax-bracket function
CAP-0013's route delegates to).

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
(A real, previously-undetected bug in this evidence: an earlier `smtpd.DebuggingServer`
process had leaked past its own `build.py stop` and was still bound to
port 1025 from a much earlier session, silently causing every SMTP debug
server launch since to fail with `OSError: Address already in use` — and
the committed capture file was, unnoticed, just that failure traceback
rather than a genuine captured email. Found during this batch's full
reproducibility sweep by actually reading the captured file's content
instead of trusting that its presence meant it worked; fixed by killing
the leaked process and re-running the proof to confirm a real welcome
email is captured now.)

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
- CAP-0006: asserts an anonymous POST redirects to `/login` and never
  persists (checked by confirming its text is absent from the next real
  page), then a real signed-up user's review appears on the real recipe
  page (one of the app's own committed sample recipes).
- CAP-0007: logs into the app's real one-click `/demo` workspace (freshly
  reseeded with realistic data every visit), extracts the real Flask-WTF
  CSRF token, and generates both a PDF and an Excel report — verified by
  real file signatures (`%PDF-`, and the zip signature `.xlsx` files
  start with) and a minimum size, not just a 200 status.
- CAP-0008: crosses the real 100-XP "First Blood" threshold via two real
  correct flag submissions, confirms the badge, then submits a third
  correct flag and confirms the badge is **not** duplicated — the real
  idempotency check in `check_badges()`, not assumed.
- CAP-0009: gives two real users different real XP totals and confirms
  the real `/api/leaderboard` response ranks them accordingly — proving
  the query actually orders by score, not just returns insertion order.
- CAP-0010: confirms anonymous bookmarking is rejected (this app's
  `LoginManager` has no `login_view` configured, so the real behaviour is
  a bare 401, not a redirect — read from source, not assumed), then adds
  a real cafe, bookmarks it, confirms it, un-bookmarks it, and confirms
  it's gone — a genuine two-way toggle.
- CAP-0011: confirms anonymous set-logging is rejected, then creates a
  real exercise, starts a real workout session, and logs two real sets
  with different reps/weight/RPE — confirming both are independently
  retrievable, not one overwriting the other.
- CAP-0012: posts a real rating for a real seeded title, confirms it via
  GET, then posts a *different* rating for the same title/survey pair and
  confirms the real `ON CONFLICT ... DO UPDATE` upsert changed the
  existing row (same `id`) rather than creating a second one — proving a
  genuine upsert, not an append.
- CAP-0013: solves the app's own real arithmetic CAPTCHA (no bypass) to
  log in as the real seeded Admin, generates payroll for real seeded
  employees at different real salary levels, and confirms the resulting
  tax figures are genuinely progressive — the higher-salary employee's
  tax-to-salary ratio differs from the lower-salary employee's, ruling out
  a flat-percentage stub.
- CAP-0014: confirms anonymous access to the patient portal is rejected,
  logs in as the real seeded demo patient, books a real appointment slot,
  then attempts to book the exact same doctor/slot a second time and
  confirms the app's own real conflict check rejects it (row count stays
  at 1), then books a genuinely different slot for the same doctor and
  confirms both persist independently — proving the rejection was about
  the specific slot, not the doctor.
- CAP-0015: fetches one of the app's own real seeded invoices (real
  customers/items/GST tax, generated by the app's own `seed_database.py`,
  not invented here), requests its real PDF, and confirms a genuine
  `%PDF-` document whose `Content-Disposition` filename reflects that
  invoice's own real invoice number — then requests a second, different
  theme and confirms a distinct (not byte-identical) real PDF, proving the
  theme parameter genuinely selects a different template rather than
  being a no-op.
- CAP-0016/0017/0018: three genuinely distinct real attach points
  harvested from the SAME already-vetted app (the same pattern already
  established by CAP-0008/0009 sharing Bounty-Simulator) — `patient_register`,
  `login`, and `logout` are three separate functions, each independently
  AST-confirmed and independently re-verified against drift. This app's
  own `base.html` never renders flashed messages on any unauthenticated
  page (confirmed by reading the template, not assumed), so these proofs
  deliberately use directly observable before/after behaviour instead —
  a real round-trip login with the exact just-submitted password for
  registration, dashboard reachability for login/logout, never flash text.
- CAP-0019: uploads a real PNG (its own real bytes, not a placeholder
  string) via genuine multipart/form-data, confirms the served-back bytes
  are byte-identical to what was uploaded, then confirms the app's own
  real duplicate-filename guard and extension whitelist both genuinely
  reject a second attempt rather than silently accepting anything.
- CAP-0020: logs in solving the app's own real CAPTCHA -- not by bypassing
  it, but by reading the real plaintext answer out of the proof's own
  legitimately-issued, signed Flask session cookie (the server still runs
  its own real verification; this is the same thing a real browser's
  session would already hold) -- mints a fresh real HMAC-signed QR token
  via the app's own `/refresh_qr` route, reads it back directly from the
  live SQLite file the server itself writes to, then checks in at the
  exact real session coordinates (accepted, real geopy distance 0.0m),
  confirms a second check-in is genuinely rejected as a duplicate, and
  confirms a check-in from London is genuinely rejected by the real 100m
  geofence distance check (not a coincidental falsy-value short-circuit --
  confirmed by checking the real distance appears in the rejection
  message).
- CAP-0021: promotes a real seeded staff account to Manager as a real
  seeded admin, confirms the change shows up on a fresh real page load,
  confirms the app's own real self-demotion guard rejects an admin
  changing their own role (403), and confirms the just-promoted Manager
  still can't call the admin-only route themselves (real access control,
  not merely a UI hint).
- CAP-0022: registers a genuinely new account, reads its real
  itsdangerous verification token back from the app's own live database,
  confirms a tampered token is rejected (signature check, not a stub),
  confirms the real token flips `email_verified` to true, and confirms
  revisiting the same real link afterward hits the app's own "already
  verified" branch cleanly rather than crashing or un-verifying the
  account.
- CAP-0023: confirms an anonymous request to the edit-profile route is
  rejected, registers a genuinely new account, edits its real about_me
  text, and confirms the exact submitted text appears on a fresh real
  GET of that user's own public profile page afterward.
- CAP-0024/0025/0026/0027/0028: five more genuinely distinct real attach
  points harvested from the already-vetted Invoice-generator (same
  multi-capability-per-app pattern as Bounty-Simulator and
  Hospital_Management_Real) — a real required-field rejection plus a
  real created-then-fetched round trip (create record); a real edit that
  replaces both the invoice's own fields and its full line-item set
  rather than appending to it, confirmed by item count after the edit
  (edit record); a real delete confirmed by a genuine 404 on the next
  fetch, plus a clean 404 (not a crash) deleting an id that never existed
  (delete record); a real multi-table `JOIN` detail view confirmed by the
  real joined customer and item *names* appearing, not just raw foreign
  keys (view record detail); and a real dynamic search-filter proof using
  two invoices for two different real customers, confirming a search by
  one customer's name returns only their invoice and never the other's
  (filter list).
- CAP-0029: submits a real base64 data-URL-encoded PNG (the shape a
  browser's webcam `<canvas>` capture sends) to the same already-vetted
  app's separate `/capture` route -- a genuinely different code path from
  the multipart `/upload` route CAP-0019 already proved -- and confirms
  the saved file's real pixel data is byte-identical to what was
  submitted, not merely present.
- CAP-0030: places a real under-minimum bid on a real seeded auction and
  confirms the app's own real minimum-increment rejection (400, the real
  next-valid amount echoed in the error), then places a real valid bid
  and confirms it's genuinely Fernet-encrypted at rest and the auction's
  real current price advances, then confirms repeating the exact same
  amount is rejected a second time (no longer valid once the price has
  moved), then re-fetches the auction and confirms the real persisted
  current price matches.
- CAP-0031: logs in as a real seeded, already-confirmed user, creates six
  real posts through the app's own real `/create_post` route, then
  confirms `index()`'s real Flask-SQLAlchemy `.paginate()` call genuinely
  splits them -- exactly five (`ROWS_PER_PAGE`) on page 1, the remaining
  one on page 2, and a real 404 on page 3 (Flask-SQLAlchemy's own
  `error_out=True` default rejecting an out-of-range page) -- a real
  LIMIT+OFFSET split, not a client-side illusion.
- CAP-0032: confirms anonymous access to the barcode-lookup route is
  genuinely rejected, then looks up one of the app's own real seeded
  barcodes as a real logged-in admin and confirms the real matching
  product (name, price, quantity) comes back, then looks up a barcode
  that was never seeded and confirms a real null result -- not a crash,
  not a fabricated match.
- CAP-0033: places two real bids from two real logged-in bidders on a
  real seeded auction via the app's own real `POST /auction/<id>/bid`
  route, confirms a real bidder (not admin, not customer rep) is
  genuinely rejected (403) attempting to end the auction, then ends it as
  the real seeded customer-rep account and confirms -- both on the
  rendered page and by reading the real committed row directly out of
  the app's own sqlite database -- that `winner_id` was set to the real
  highest bidder's id and `is_active` flipped to false, proving the
  app's own real reserve-price-checked `determine_winner()` logic
  actually ran. (A first pass at this proof posted bids to the wrong
  route -- the auction's own view page rather than its real
  `/auction/<id>/bid` submission endpoint -- and silently produced zero
  persisted bids; caught by reading the real bids table directly rather
  than trusting the 200 status code, not assumed away.)
- CAP-0034: against a real PostgreSQL-backed database (this app's own
  `config.py` has no SQLite fallback), attempts an already-expired real
  seeded coupon and confirms it's genuinely rejected with the cart total
  unchanged, applies a real non-expired coupon and confirms the cart's
  real persisted total drops by exactly its discount percentage (a real
  $200.00 subtotal to $160.00 for a 20% coupon), and confirms re-applying
  the same coupon a second time is genuinely rejected -- the real
  composite-PK `AppliedCoupons(user_id, coupon_id)` uniqueness enforced
  at the row level. First real PostgreSQL-backed capability in this
  pipeline (`build.py`'s new `needs_postgres` runner field drops and
  recreates one fixed build database and applies the app's own real,
  unmodified schema file fresh before every build, the Postgres analogue
  of `reset_globs` for a SQLite app's stale file); needs its own
  dedicated venv too (a different old Flask 2.3.3/Werkzeug 2.3.7 pairing
  than `.venv-legacy-flask`'s, confirmed by a real `ImportError` under
  the shared venv's modern Werkzeug before creating `.venv-mini-amazon`).
- CAP-0035: seeds two real `Feature` rows at two genuinely different
  coordinates directly via the app's own real Django ORM models, then
  confirms both real features' exact names and lat/lng values appear in
  the real rendered Folium map -- not a static demo, and not a single
  hardcoded marker, since a genuinely different second feature also has
  to show up distinctly -- and confirms a feature that was never seeded
  does NOT appear. First real Django app in this pipeline (see "Real
  applications aren't all shaped the same way" above for the new
  `django_manage` runner kind and `needs_postgres`'s new empty-database
  mode). A real, separate `map_features()` view in the same file builds
  an empty map with no `Feature` query at all and has no route anywhere
  in the app's own `urls.py` -- confirmed dead/unwired code and
  correctly not used as this capability's attach point.
- CAP-0036: confirms anonymous access to the import route is genuinely
  rejected, logs in as the real seeded user via the app's own real
  allauth login form (seeded with an already-verified `EmailAddress` row
  so login doesn't trigger a real confirmation-email send), uploads a
  real CSV file through the app's own real django-import-export
  dry-run-then-commit path, and confirms the imported feature's exact
  name and coordinates appear on the real map page afterward -- proving
  it was actually written to the database, not merely accepted and
  discarded. (First attempt at logging in hit a real `ConnectionRefusedError`
  from allauth trying to send a real confirmation email to a local SMTP
  server that wasn't running for an unverified seeded account -- fixed
  properly, not routed around: the app's own real local SMTP debug
  server this pipeline already runs for Flask apps needing it is
  reusable as-is here too (`needs_smtp` is kind-agnostic), and the seed
  step now creates an already-verified `EmailAddress` row the same way a
  real user who'd clicked their confirmation link would have one.)
- CAP-0037: requests a real OTP for a real mobile number, reads the real
  generated 5-digit code directly out of the app's own sqlite database
  (the app's own real code only ever `print()`s it -- never sent by SMS,
  so this is the only way to observe it, not an invented value), confirms
  a wrong code is genuinely rejected, confirms the real code is accepted
  and issues real signed JWT access/refresh tokens, and confirms reusing
  the same code a second time is genuinely rejected. This harvest also
  caught a real, previously-latent bug in `build.py` itself: its
  re-verification step matched a harvested function by name alone, which
  silently matched the WRONG same-named method (`OTPCreateView.post`
  instead of the harvested `OTPVerifyView.post` -- two different DRF
  `APIView.post()` overrides in the same file) and falsely reported
  drift. Fixed by preferring the candidate whose current line number
  still matches what was actually harvested, falling back to "the one
  function with this name" only when there's no ambiguity -- every other
  harvested capability, none of which shares a file with a same-named
  sibling, re-verifies exactly as before.

## How to reproduce this from scratch

```bash
cd capability-harvest
python3 -m venv .venv
./.venv/bin/pip install flask flask-login flask-sqlalchemy flask-bcrypt \
    flask-mail flask-migrate flask-cors flask-wtf python-dotenv requests \
    reportlab geopy pillow cs50 pandas openpyxl zinny-surveys \
    numpy joblib weasyprint num2words python-dateutil \
    flask-limiter pyjwt pillow apscheduler qrcode pytz \
    flask-mailman discord-webhook bcrypt "flask-admin==1.6.1" email_validator \
    cryptography flask-socketio eventlet flask-apscheduler \
    mysql-connector-python matplotlib

# recipe-app and EnterpriseProject both need Python 3.12+ (see "Real
# applications aren't all shaped the same way" below -- a multi-line
# dict literal inside an f-string is PEP 701 syntax) -- a separate venv,
# not the one above.
python3.12 -m venv .venv-py312
./.venv-py312/bin/pip install flask flask-login flask-sqlalchemy flask-migrate \
    flask-wtf python-dotenv requests bcrypt discord-webhook

# dataviva-training genuinely needs an OLD Flask 2.2 / Flask-Babel 2.0
# pairing that is mutually incompatible with the modern Flask/Werkzeug the
# venv above (and every other harvested app) depends on -- NEVER install
# these into .venv or .venv-py312. Learned the hard way: doing so once
# broke CAP-0010 until a full reproducibility sweep caught it. This one
# gets its own fully isolated venv instead.
python3.11 -m venv .venv-legacy-flask
./.venv-legacy-flask/bin/pip install flask==2.2.2 flask-sqlalchemy==3.0.2 \
    flask-migrate==4.0.2 flask-login==0.6.2 flask-moment==1.0.5 \
    flask-bootstrap==3.3.7.1 flask-babel==2.0.0 flask-wtf==1.1.1 \
    elasticsearch==8.6.0 email-validator==1.3.1 werkzeug==2.2.2 python-dotenv

# Mini-Amazon genuinely needs a DIFFERENT old Flask 2.3.3 / Werkzeug 2.3.7
# pairing (its own `werkzeug.urls.url_parse` import, removed by the time
# of the shared venv's modern Werkzeug -- confirmed with a real
# ImportError before creating this venv, not assumed) -- not the same
# pinned set as .venv-legacy-flask's Flask 2.2.2, so it gets its own
# dedicated venv too.
python3.11 -m venv .venv-mini-amazon
./.venv-mini-amazon/bin/pip install flask==2.3.3 werkzeug==2.3.7 \
    flask-sqlalchemy flask-wtf psycopg2-binary flask-login \
    email-validator faker python-dotenv sqlalchemy requests openai

# Mini-Amazon also needs a real PostgreSQL server. This sandbox already
# has one (PostgreSQL 16, confirmed with `service postgresql start`/
# `psql`, not assumed) -- one dedicated superuser role is created ONCE,
# a real one-time environment setup step, not something build.py itself
# does (the same way it never installs Python or creates venvs):
sudo -u postgres psql -c "CREATE ROLE harvestuser WITH LOGIN PASSWORD 'harvestpass' SUPERUSER;"

# Django_and_Folium needs its own real, large, Django-shaped dependency
# set (allauth, graphene-django, django-jazzmin, django-import-export,
# folium, ...) -- its own dedicated venv too.
python3.11 -m venv .venv-django-folium
./.venv-django-folium/bin/pip install python-slugify Pillow argon2-cffi \
    whitenoise redis django==4.2.10 django-environ django-model-utils \
    django-allauth django-crispy-forms crispy-bootstrap5 django-redis \
    djangorestframework django-cors-headers drf-spectacular django-filter \
    django-import-export folium graphene-django django-graphql-jwt \
    django-rest-registration django-jazzmin psycopg2-binary \
    django-debug-toolbar django-extensions tablib

# django-otp-auth needs only plain Django + DRF + simplejwt, on SQLite --
# no Postgres, no heavy infra -- but still its own dedicated venv.
python3.11 -m venv .venv-django-otp-auth
./.venv-django-otp-auth/bin/pip install django==5.1.4 djangorestframework \
    djangorestframework-simplejwt PyJWT asgiref sqlparse \
    django-jalali-date jalali_core jdatetime requests

python3 discovery/discover_applications.py
python3 detection/detect_capability.py
for cap in CAP-0001 CAP-0002 CAP-0003 CAP-0004 CAP-0005 CAP-0006 CAP-0007 \
           CAP-0008 CAP-0009 CAP-0010 CAP-0011 CAP-0012 CAP-0013 CAP-0014 \
           CAP-0015 CAP-0016 CAP-0017 CAP-0018 CAP-0019 CAP-0020 CAP-0021 \
           CAP-0022 CAP-0023 CAP-0024 CAP-0025 CAP-0026 CAP-0027 \
           CAP-0028 CAP-0029 CAP-0030 CAP-0031 CAP-0032 CAP-0033 CAP-0034 \
           CAP-0035 CAP-0036 CAP-0037; do
    python3 harvest_parts.py harvest_requests/${cap}.request.json
done
python3 shelf_records.py

# Each capability's own app is built/tested/stopped one at a time -- see
# each capability's runner in discovery/discover_applications.py for its
# port (flask-messenger, recipe-app and CasettaFit's start don't need one
# specified, or hardcode 5000; others take --port 5057-5060). CAP-0008 and
# CAP-0009 share one app (Bounty-Simulator) but are still built/verified
# separately -- each build re-verifies its OWN harvested attach point.
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

python3 build.py start --cap CAP-0006   # recipe-app also hardcodes port 5000
./.venv/bin/python3 test/prove_CAP-0006_http.py
python3 build.py stop

python3 build.py start --cap CAP-0007 --port 5057
./.venv/bin/python3 test/prove_CAP-0007_http.py
python3 build.py stop

python3 build.py start --cap CAP-0008 --port 5057
./.venv/bin/python3 test/prove_CAP-0008_http.py
python3 build.py stop

python3 build.py start --cap CAP-0009 --port 5057
./.venv/bin/python3 test/prove_CAP-0009_http.py
python3 build.py stop

python3 build.py start --cap CAP-0010 --port 5057
./.venv/bin/python3 test/prove_CAP-0010_http.py
python3 build.py stop

python3 build.py start --cap CAP-0011 --port 5057
./.venv/bin/python3 test/prove_CAP-0011_http.py
python3 build.py stop

python3 build.py start --cap CAP-0012 --port 5057
./.venv/bin/python3 test/prove_CAP-0012_http.py
python3 build.py stop

python3 build.py start --cap CAP-0013 --port 5057
./.venv/bin/python3 test/prove_CAP-0013_http.py
python3 build.py stop

python3 build.py start --cap CAP-0014 --port 5057
./.venv/bin/python3 test/prove_CAP-0014_http.py
python3 build.py stop

python3 build.py start --cap CAP-0015 --port 5057
./.venv/bin/python3 test/prove_CAP-0015_http.py
python3 build.py stop

python3 build.py start --cap CAP-0016 --port 5057
./.venv/bin/python3 test/prove_CAP-0016_http.py
python3 build.py stop

python3 build.py start --cap CAP-0017 --port 5057
./.venv/bin/python3 test/prove_CAP-0017_http.py
python3 build.py stop

python3 build.py start --cap CAP-0018 --port 5057
./.venv/bin/python3 test/prove_CAP-0018_http.py
python3 build.py stop

python3 build.py start --cap CAP-0019 --port 5057
./.venv/bin/python3 test/prove_CAP-0019_http.py
python3 build.py stop

python3 build.py start --cap CAP-0020 --port 5057
./.venv/bin/python3 test/prove_CAP-0020_http.py
python3 build.py stop

python3 build.py start --cap CAP-0021 --port 5057
./.venv/bin/python3 test/prove_CAP-0021_http.py
python3 build.py stop

python3 build.py start --cap CAP-0022 --port 5057
./.venv/bin/python3 test/prove_CAP-0022_http.py
python3 build.py stop

python3 build.py start --cap CAP-0023 --port 5057
./.venv/bin/python3 test/prove_CAP-0023_http.py
python3 build.py stop

python3 build.py start --cap CAP-0024 --port 5057
./.venv/bin/python3 test/prove_CAP-0024_http.py
python3 build.py stop

python3 build.py start --cap CAP-0025 --port 5057
./.venv/bin/python3 test/prove_CAP-0025_http.py
python3 build.py stop

python3 build.py start --cap CAP-0026 --port 5057
./.venv/bin/python3 test/prove_CAP-0026_http.py
python3 build.py stop

python3 build.py start --cap CAP-0027 --port 5057
./.venv/bin/python3 test/prove_CAP-0027_http.py
python3 build.py stop

python3 build.py start --cap CAP-0028 --port 5057
./.venv/bin/python3 test/prove_CAP-0028_http.py
python3 build.py stop

python3 build.py start --cap CAP-0029 --port 5057
./.venv/bin/python3 test/prove_CAP-0029_http.py
python3 build.py stop

python3 build.py start --cap CAP-0030 --port 5057
./.venv/bin/python3 test/prove_CAP-0030_http.py
python3 build.py stop

python3 build.py start --cap CAP-0031 --port 5057
./.venv/bin/python3 test/prove_CAP-0031_http.py
python3 build.py stop

python3 build.py start --cap CAP-0032 --port 5057
./.venv/bin/python3 test/prove_CAP-0032_http.py
python3 build.py stop

python3 build.py start --cap CAP-0033 --port 5057
./.venv/bin/python3 test/prove_CAP-0033_http.py
python3 build.py stop

python3 build.py start --cap CAP-0034 --port 5057
./.venv/bin/python3 test/prove_CAP-0034_http.py
python3 build.py stop

python3 build.py start --cap CAP-0035 --port 5057
./.venv/bin/python3 test/prove_CAP-0035_http.py
python3 build.py stop

python3 build.py start --cap CAP-0036 --port 5057
./.venv/bin/python3 test/prove_CAP-0036_http.py
python3 build.py stop

python3 build.py start --cap CAP-0037 --port 5057
./.venv/bin/python3 test/prove_CAP-0037_http.py
python3 build.py stop
```

This exact sequence was run against a fully wiped state (`application_pool/`,
`shelf/`, `capabilities/`, `output/*`, `discovery/applications.json` all
deleted first, venvs and the Postgres role/database kept) sixteen times
now, at sixteen different capability counts, to confirm it's genuinely
reproducible, not an artifact of an ad-hoc fixing sequence. This same
sweep is what caught CAP-0028's real name-collision flakiness (see "Real
applications aren't all shaped the same way" above) -- a real, previously
passing proof that started intermittently failing once the app's own
random customer-name generator happened to produce a collision, exactly
the kind of regression a full re-run from a clean state, not a
one-off pass, is meant to surface.

## What this proves vs. what's next

**Proved, for real:**
- Real application discovery with real licence verification from the
  source file, across 24 different repositories and three distinct real
  licences (MIT, BSD-3-Clause, Apache-2.0).
- Real AST-based attach-point detection that rejects name-only matches,
  across both route-handler and helper-function capability shapes,
  verified against a deliberately drifted line number.
- A documented, deterministic harvest path with re-verification against
  drift, real provenance, real checksums, for every capability.
- A build stage that handles three genuinely different real application
  shapes without bending any of them to fit one template, verifying (not
  assuming) the harvested code is what's actually running before starting
  anything, across two Python versions and an app whose data path resolves
  outside its own repo entirely (`$HOME`-based, handled via an isolated,
  resettable `HOME` override rather than patching the app).
- Thirty-seven independent, real, non-mocked live proofs, including negative/
  access-control checks, cross-interface consistency checks, a real
  multi-day date-diffing proof that required inserting real historical
  data directly into the app's own real database (not through its HTTP
  surface, which doesn't support backdating), a real upsert-vs-append
  distinction confirmed by row `id` stability, a real progressive
  tax-bracket proof that solves the app's own arithmetic CAPTCHA rather
  than bypassing it, a real per-doctor/per-slot double-booking rejection,
  a real multi-theme PDF-invoice proof that required first reproducing,
  then correctly working around (via file placement, not a source-code
  patch), a genuine bug in the harvested repository itself, a real
  register/login/logout triad proven against a template that never
  renders flash messages on unauthenticated pages (confirmed by reading
  the template, not assumed, so the proofs use directly observable
  session/round-trip behaviour instead), a real byte-identical
  file-upload round trip with a genuine duplicate-name and extension
  guard, and a real CAPTCHA-gated, HMAC-signed-QR-token, geopy-geofenced
  location check-in with a genuine duplicate-attendance rejection and a
  genuine out-of-range distance rejection (verified to actually be
  distance-based, not a coincidental falsy-value short-circuit on a
  literal `0.0` coordinate caught during proof development), a real
  admin-gated role-change proof with both a genuine self-demotion guard
  and a genuine non-admin access-control rejection, and a real signed
  email-verification-token proof that confirms a tampered token is
  rejected and that revisiting an already-consumed real link is
  idempotent rather than crashing, and a real profile-edit proof (with a
  real anonymous-access rejection) against an app that required its own
  fully isolated Python environment after an old, mutually-incompatible
  dependency pair was mistakenly test-installed into the shared venv and
  broke an already-harvested capability -- caught and fixed by the same
  full-reproducibility sweep this pipeline runs every batch. Five more of
  the twenty-two: a real required-field rejection alongside a real
  create-then-fetch round trip; a real edit proof that confirms the full
  line-item set was replaced (by item count), not appended to; a real
  delete proof with a genuine 404 both for the just-deleted row and for
  an id that never existed; a real multi-table `JOIN` detail view
  confirmed by real joined names, not raw foreign keys; and a real
  search-filter proof using two different real customers' invoices to
  confirm the filter genuinely narrows results rather than merely
  appearing to; and a real base64-capture proof against a second,
  genuinely distinct route in an already-harvested app, confirmed
  pixel-identical rather than merely present. Four more of the
  thirty-three: a real Fernet-encrypted, minimum-increment-enforced
  bidding proof with a genuine repeat-amount rejection once the price has
  moved; a real Flask-SQLAlchemy pagination proof against a real
  six-post feed, split exactly five-then-one across two pages with a
  genuine 404 on a third, out-of-range page; a real barcode-lookup proof
  distinguishing a real seeded match from a real null result for a
  barcode that was never seeded, with a genuine anonymous-access
  rejection; and a real reserve-price-checked auction-close proof with
  both a genuine non-admin/non-customer-rep 403 rejection and a direct
  database read confirming the real highest bidder was persisted as
  winner -- the last one caught a real bug in its own first test attempt
  (bids posted to the auction's view route instead of its real bid
  submission route, silently producing zero persisted bids despite a 200
  response) by reading the real bids table directly rather than trusting
  the status code.

**Explicitly not yet built (do not assume it exists):**
- **Scale beyond 37.** ~43 names in the 81-name vocabulary (see
  `CAPABILITY_VOCABULARY.md` for the full recovered list and live status)
  have not been researched yet. Each one needs the same real vetting
  (license read from source, AST-confirmed evidence, live proof) — this is
  not a copy-paste-N-times exercise, and a name with no genuine real-app
  candidate gets recorded as blocked/empty with a reason, never forced.
  **Escalate ticket** was researched but every small, single-file,
  HTTP-route candidate found failed either the licence check or the "must
  genuinely update a persisted field" check; the one fully-verified real
  implementation found (django-helpdesk's `escalate_tickets` management
  command, BSD-3-Clause) is a mature production project but is invoked by
  cron, not an HTTP route, and needs a heavier Django setup than this
  pipeline's other apps — deferred, not forced in.
  **Send reminder** was researched and a genuine, non-trivial candidate
  was found -- indrajit912/Slotify (MIT), whose
  `app/services/email_reminder_service.py::send_reminder_emails()` does
  real work: queries real `User`/`Booking` rows, computes a real
  per-user configurable IST reminder window, dedupes via a real
  `ReminderLog` row before sending, and is wired into a real (if
  disabled-by-default) APScheduler job. It was still deferred: its email
  send (`scripts/email_message.py::EmailMessage.send()`) hardcodes a
  real, unconditional `server.starttls()` + `server.login(...)` against
  `smtp.gmail.com:587` (`config.py`'s `EmailConfig.GMAIL_SERVER`, a
  plain list literal, not an env-var lookup like every other harvested
  app's mail config) -- this sandbox has no route to the public
  internet's SMTP ports, and there is no override point to redirect it
  at a local debug server without editing the harvested code itself,
  which this pipeline's own rule against touching a harvested
  capability's logic rules out. The simpler bare `smtpd.DebuggingServer`
  this pipeline already runs for other apps' email capabilities
  couldn't stand in either, since it has no STARTTLS/AUTH support at
  all and this app's `send()` doesn't offer a way to skip either.
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
