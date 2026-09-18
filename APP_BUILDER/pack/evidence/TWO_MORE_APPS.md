# Two more apps — Redash and CTFd through the machine

Written after actually running everything below. Where something was refused,
the refusal is quoted verbatim. Where something was fixed, the fix is named
and why. Nothing here was arranged to make a run look better than it was.

---

## Before starting — verification against the real repositories

`HARVEST_TWO_MORE_APPS.md` names a licence and a stack for each source. Both
were checked directly against a fresh clone at the commit actually harvested,
not taken on the document's word.

**Redash** (`getredash/redash` @ `8f6b15d30da433ae881dd6376a38df17bb6c2663`,
`master`, cloned 2026-09-18):
- `LICENSE` is the real 2-clause BSD text (Copyright Arik Fraimovich,
  2 numbered clauses, no advertising clause) — SPDX `BSD-2-Clause`, matches.
- `pyproject.toml` pins `flask==2.3.2`, `flask-sqlalchemy==2.5.1`,
  `psycopg2-binary==2.9.11`, `sqlalchemy==1.3.24` as **production**
  dependencies — Flask + PostgreSQL confirmed, not optional.
- API docs: README links `redash.io/help/`, and the spec's named page
  (`user-guides/integrations-and-api/api`) is live on that same site.
- Structural match verified by reading the actual handler code (see the
  form's `harvest_source.structural_match` and `exemplar.notes`).

**CTFd** (`CTFd/CTFd` @ `8864bc0cea5b67d9ae96978b5d559e70330ff071`, `master`,
cloned 2026-09-18):
- `LICENSE` is the real Apache-2.0 text — matches.
- `pyproject.toml`/`requirements.txt` pin `flask==2.1.3`,
  `flask-sqlalchemy==2.5.1`, `flask-restx==1.3.0` — Flask confirmed.
- API docs: `CTFd/api/__init__.py` builds a `flask_restx.Api` on `/api/v1`
  with `doc` enabled, which serves `swagger.json` at `/api/v1/swagger.json`
  by default — matches the spec exactly.
- **PostgreSQL needed a real caveat, not a rubber stamp.** CTFd's own
  `CHANGELOG.md` says outright: *"Postgres is now considered a second class
  citizen in CTFd. It is tested against but not a main database backend. If
  you use Postgres, you are entirely on your own with regards to supporting
  CTFd."* Its `docker-compose.yml` and `config.ini` default to MySQL/MariaDB;
  `psycopg2-binary` lives only in the **dev/test** dependency group, not
  production. But PostgreSQL support is genuine, not nominal: `config.py`
  builds a real SQLAlchemy URL for it, the repo carries its own
  `.github/workflows/postgres.yml` CI job running the real test suite
  against a real Postgres service container, and `CTFd/utils/exports/__init__.py`
  has real Postgres-specific code branches. This session proceeded on that
  basis — CTFd was built and migrated against a real, dedicated PostgreSQL
  16 database for every run below — but "PostgreSQL" means something
  measurably weaker for CTFd than it does for Indico or Redash, and that
  difference is itself one of this exercise's findings (see Question 3).

Neither source failed a rule. Both proceeded to forms.

---

## Step 1 — the two forms

`forms/data-dashboard.form.json` and `forms/challenge-platform.form.json`,
shaped like `forms/event-ticketing.form.json`.

Eight capabilities each (within the 6–10 range), including register/log
in/log out for both, plus:

- **Redash**: create data source, run query, create visualisation, add to
  dashboard, share dashboard
- **CTFd**: list challenges, submit flag, view scoreboard, create team, join
  team

**Redash has no open self-service registration.** Accounts after the first
are created by admin invite; the real self-service account-creation route is
the one-time `/setup` wizard (creates the Organization *and* the first
admin). Used as the closest real equivalent to "register account" and named
plainly in the form's `unresolved` — the alternative was inventing a signup
endpoint that does not exist in this codebase, which the spec explicitly
forbids.

`view_adapter` was left blank on **both** forms. `RUNTIME_ADAPTER_FIELD`
needs an already-existing `module.path:callable` in the source's own code
that turns a class into a servable Flask view — Indico ships exactly this
(`indico.web.flask.util:make_view_func`), used throughout its own blueprint
registration. Neither Redash (Flask-RESTful) nor CTFd (flask-restx) exposes
an equivalent standalone function; both frameworks' `Api.add_resource`
registration calls `.as_view()` on a class *inside the third-party library
itself*, not through anything the source app itself defines and exports. No
symbol of the right shape exists to name, so per the spec ("do not guess
them… leave it empty, run anyway, record what the host said") it was left
blank on both forms. What that produced is recorded in Step 5.

---

## Step 2 — harvest, verbatim

Run **one at a time**, from `pack/`.

```
$ python3 1_harvest/harvest_parts.py forms/data-dashboard.form.json

shelf: shelf
forms to consider: 1

data-dashboard   <- getredash/redash@8f6b15d30da4   (BSD-2-Clause)
  number     capability                    lines  result
  CAP-0001   register account                 75  on shelf
  CAP-0002   log in                          345  on shelf
  CAP-0003   log out                         345  on shelf
  CAP-0016   create data source              248  on shelf
  CAP-0017   run query                       527  on shelf
  CAP-0018   create visualisation             56  on shelf
  CAP-0019   add to dashboard                 80  on shelf
  CAP-0020   share dashboard                 415  on shelf

--------------------------------------------------------------
apps harvested: 1   capabilities on shelf: 8   failures: 0
```

```
$ python3 1_harvest/harvest_parts.py forms/challenge-platform.form.json

shelf: shelf
forms to consider: 1

challenge-platform   <- CTFd/CTFd@8864bc0cea5b   (Apache-2.0)
  number     capability                    lines  result
  CAP-0001   register account                680  on shelf
  CAP-0002   log in                          680  on shelf
  CAP-0003   log out                         680  on shelf
  CAP-0011   list challenges                1380  on shelf
  CAP-0012   submit flag                    1380  on shelf
  CAP-0013   view scoreboard                  99  on shelf
  CAP-0014   create team                     403  on shelf
  CAP-0015   join team                       403  on shelf

--------------------------------------------------------------
apps harvested: 1   capabilities on shelf: 8   failures: 0
```

**Neither source was refused.** The admission check (Rule A–E, enforced in
`harvest_parts.py` before a byte is fetched) passed both — the form's
declared `framework`/`datastore`/`licence`/`api_docs_url`/`structural_match`
were exactly what the pre-harvest verification above established.

`ENFORCE_ADMISSION`, `ALLOWED_LICENCES`, and every other admission setting
were left exactly as shipped for both runs.

Verified for both apps, per the spec's checklist:

- `shelf/<slug>/CAP-XXXX/source.py` exists for all 16 capabilities (8+8)
- `PROVENANCE.json` beside each, `symbol_verified: true` on all 16
- `LICENCE.txt` beside each, carrying the real source licence text
- every `source.py` parses (`ast.parse`) — confirmed, all 16

---

## Step 3 — numbering and shelf records

**A real ordering problem, not an admission one:** `assign_numbers.py`
requires a `cap_id` already present on every capability before
`harvest_parts.py` will touch it (`"no cap_id -- run assign_numbers.py
first"` is a hard failure there) — so despite the spec's step order (harvest,
*then* number), numbering had to run first for the harvest to work at all.
Ran with `cap_id: ""` on every new capability, letting the registry resolve
them.

```
$ python3 2_numbering/assign_numbers.py

3 app(s)
  app      category                  caps   new reused  unbound
  APP-002  challenge-platform           8     5      3        0
  APP-003  data-dashboard               8     5      3        0
  APP-001  event-ticketing             10     0     10        0

registry: 3 apps, 20 capabilities
newly minted this run: 10
```

**Confirmed directly, not inferred:** `register account`, `log in` and
`log out` resolved to the *same three numbers* — `CAP-0001`, `CAP-0002`,
`CAP-0003` — for all three apps. N2 ("capabilities numbered once, globally")
worked exactly as designed. This is the closest thing to a "yes" on Question
1 below, and its limits are described there.

A second directory-path mismatch, independent of the harvest one:
`assign_numbers.py` resolves `FORMS_DIR`/`REGISTRY_PATH`/`TREE_DIR` relative
to **its own file location** (`2_numbering/`), not the `forms/`,
`number_registry.json` and `trees/` the rest of the pack actually uses at
`pack/`'s root — so run from `pack/` as documented, it found
`2_numbering/forms/`, which does not exist, and reported `"no filled forms
found in forms/"`. Not an admission check refusing anything — a path that
could never have resolved. Fixed by staging real copies of the three forms
at `2_numbering/forms/` (not editing the script), running there, then
copying the numbered forms, the updated registry and the new tree files back
to their canonical `pack/` locations. `pack/number_registry.json` and
`pack/2_numbering/number_registry.json` were kept identical afterward.

```
$ python3 shelf_records.py forms/data-dashboard.form.json
wrote records for 8/8 capabilities  app=data-dashboard
aliases: 8

$ python3 shelf_records.py forms/challenge-platform.form.json
wrote records for 8/8 capabilities  app=challenge-platform
aliases: 8
```

**A second, more serious finding, this one in the shelf's own record
layer.** `shelf_records.py` writes `shelf/capabilities/<CAP-id>.json` and
`shelf/implementations/<CAP-id>/IMPL-01.json` **per capability number**, not
per app — but CAP-0001/0002/0003 now have **three different real source
files** behind them (Indico's, Redash's, CTFd's), and the implementation
number is always `IMPL-01` (`FIRST_IMPL_NUMBER = 1`, a constant). Each app's
`shelf_records.py` run **silently overwrote** the previous app's record for
the same number. After running data-dashboard then challenge-platform,
`shelf/implementations/CAP-0001/IMPL-01.json`'s `release.commit` and
`source.repository` read `CTFd/CTFd` — event-ticketing's and data-dashboard's
own real `register account` implementations are no longer represented
anywhere in that file, even though both are still correctly on the shelf at
`shelf/event-ticketing/CAP-0001/source.py` and
`shelf/data-dashboard/CAP-0001/source.py`. `shelf/capabilities/CAP-0001.json`'s
`category` field shows the same thing: it now reads `"Challenge Platform"`
for a capability that is also, just as validly, `"Event Ticketing"` and
`"Data Dashboard"`.

This does **not** affect what actually runs — `host.py`'s `bind_shelf_parts`
never reads `shelf/capabilities/` or `shelf/implementations/`; it binds
straight from `shelf/<app_slug>/<CAP-id>/source.py` and that capability's own
`PROVENANCE.json`, which are correctly per-app and were never touched by
this. It does mean the shelf's own §3.6/§3.7 records — the part of the
system meant to be the durable, auditable truth about a numbered capability
— cannot currently represent more than one app's real implementation behind
a shared number. N2's "one number, referenced many times" was built and
proven against a single app; nothing before this session exercised it with
more than one app actually claiming the same number with materially
different real code behind it. `shelf_records.py` was left exactly as
shipped — not patched — and this is reported as found.

---

## Step 4 — installing each source's runtime

Done the way it was done for event-ticketing: real services, real config,
nothing swapped to a testing mode.

| | Redash | CTFd |
|---|---|---|
| Python | 3.13 venv (Redash's `pyproject.toml` pins `>=3.13,<3.14`; the environment's default `python3` is 3.11, which would not have satisfied it) | 3.11 venv |
| Dependencies | 68 pinned packages from `pyproject.toml`'s `dependencies` list, installed directly (see below) | `requirements.txt`, installed as-is |
| Database | PostgreSQL 16, real server, database `redash` owned by role `redash_app` | PostgreSQL 16, real server, database `ctfd` owned by role `ctfd_app` |
| Cache/broker | Redis, real server, `redis-cli ping` → `PONG`, separate logical DB (1 for CTFd, 2 for Redash) | same Redis server, DB 1 |
| Schema | `redash.models.db.create_all()`, called explicitly (Redash's `create_app()` does not migrate itself — see `redash/cli/database.py:create_tables`) | CTFd's own `create_app()` runs real Alembic `upgrade()` against Postgres, in-process, every build |
| Config | Real env vars (`REDASH_DATABASE_URL`, `REDASH_REDIS_URL`, `REDASH_COOKIE_SECRET`, `REDASH_SECRET_KEY`) — Redash's `settings/__init__.py` reads these directly, no testing flag exists to trip over | Real env vars (`DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`) via CTFd's own documented `EnvInterpolation` fallback in `config.ini` |

**A real, upstream packaging defect, found and worked around without
touching Redash's source:** `pip install <redash-clone-dir>` fails outright —
`pyproject.toml`'s `authors = [{ name = "…", email = "<arik@redash.io>" }]`
wraps the email in angle brackets, which newer `setuptools`' RFC-5322 address
parser rejects (`email.errors.HeaderParseError`) while building the
package's own metadata. Installing the package itself was never actually
needed — only its dependencies, for `import redash` to work via
`PYTHONPATH` — so the 68 pins were read out of `pyproject.toml` with
`tomllib` and installed directly with `pip install -r`, bypassing the
broken metadata build entirely. Redash's `pyproject.toml` itself was never
edited.

**Two real operational quirks found in CTFd, neither an admission-rule
issue:**

1. Flask-Migrate's default `migrations` directory is **resolved relative to
   the process's current working directory**, not to CTFd's own package —
   `CTFd/utils/migrations/__init__.py`'s own `stamp_latest_revision()`
   comment ("Get proper migrations directory regardless of cwd") shows the
   author already knew this about the *other* migration path (the one used
   for SQLite) but the real Postgres path (`upgrade()`) was left depending
   on cwd. Building against Postgres from `pack/` (as `host.py` and every
   chain script are invoked) → `Error: Path doesn't exist: migrations.` Fixed
   by symlinking `pack/migrations` → the real CTFd clone's `migrations/`
   directory (a live, unmodified copy exactly where CTFd's own unedited code
   already looks for it) — not by patching CTFd or any pack script.
2. **CTFd gates every route behind its own one-time `/setup` wizard**
   (`config.is_setup()`, checked in a global `before_request`) until an admin
   completes it. `/setup` is not one of this app's eight harvested
   capabilities — it is deployment bootstrap, the same category of action as
   creating the Postgres database itself. It cannot be completed through the
   shelf-restricted host (the host correctly 404s it, since it is not
   admitted) so it is completed once, per test run, against a **separate,
   unrestricted** `CTFd.create_app()` instance — real code, real database
   writes, no shelf involvement — immediately after every fresh migration,
   before the shelf-governed instance is built. See `host_test_challenge_platform.py`.

**A third, genuinely nondeterministic defect, found while getting the chain
to run repeatably: a real deadlock inside CTFd's own plugin loader.**
Building `CTFd.create_app()` against a just-migrated, empty Postgres database
intermittently hangs indefinitely partway through `init_plugins()` — always
at the same point, right after the `challenges` plugin loads and before
`dynamic_challenges` finishes its own per-plugin Alembic migration. Confirmed
with `pg_stat_activity`: one backend sits `idle in transaction` on
`SELECT … FROM config WHERE config.key = 'dynamic_challenges_alembic_version'`
while a second backend blocks indefinitely on
`ALTER TABLE dynamic_challenge DROP CONSTRAINT dynamic_challenge_id_fkey`,
waiting on a lock the first implicitly holds. Reproduced **4 times out of 7**
attempts to build the app fresh in this session; the other 3 completed in a
few seconds. This is internal to CTFd's plugin-loading code (two SQLAlchemy
sessions opened during the same `create_app()` call, one never committed or
closed before the other needs a conflicting lock) — nothing in the shelf,
the forms, or this pack's own scripts touches that code path. Worked around
operationally each time it happened: `pg_terminate_backend()` on the stuck
connections, then retry. Not fixed, because there is nothing in scope to fix
it in — it is upstream CTFd behaviour, encountered and reported honestly
rather than hidden by only reporting the clean runs.

---

## Step 5 — the host

```
$ python3 4_host/host.py --app challenge-platform --check
app: challenge-platform   shelf: 8 capabilities
runtime: CTFd:create_app
shelf parts bound: 3
  NOT BOUND  CAP-0001: part has no class named by 'register'
  NOT BOUND  CAP-0002: part has no class named by 'login'
  NOT BOUND  CAP-0003: part has no class named by 'logout'
  NOT BOUND  CAP-0014: part has no class named by 'new'
  NOT BOUND  CAP-0015: part has no class named by 'join'
REFUSED: a capability on the shelf could not be bound to its own part -- the app would be served by code the shelf does not govern
```

```
$ python3 4_host/host.py --app data-dashboard --check
app: data-dashboard   shelf: 8 capabilities
runtime: redash.app:create_app
shelf parts bound: 4
  NOT BOUND  CAP-0001: part did not load: AssertionError: The setup method 'route' can no longer be called on the blueprint 'redash'. It has already been registered at least once, any changes will not be applied consistently.
Make sure all imports, decorators, functions, etc. needed to set up the blueprint are done before registering it.
  NOT BOUND  CAP-0002: part did not load: AssertionError: [same]
  NOT BOUND  CAP-0003: part did not load: AssertionError: [same]
  NOT BOUND  CAP-0017: part did not load: AssertionError: [same]
REFUSED: a capability on the shelf could not be bound to its own part -- the app would be served by code the shelf does not govern
```

**`shelf parts bound` did not equal the capability count for either app —
3 of 8 for CTFd, 4 of 8 for Redash.** Per the spec, acted on exactly what the
host said, and did not touch `FAIL_ON_UNRESOLVED`, `view_adapter`, or any
other setting to force it higher. Two genuinely different failure mechanisms
surfaced, one per app:

**CTFd — no class to bind, full stop.** `bind_shelf_parts` only accepts a
symbol that resolves to a class (`isinstance(obj, type)`). CTFd's
`register`/`login`/`logout` (`CTFd/auth.py`) and `new`/`join`
(`CTFd/teams.py`, self-service create/join team) are plain
`@blueprint.route(...)`-decorated functions — confirmed by grepping the
whole repository for `MethodView`/`.as_view(` outside `CTFd/api/`: there is
none. Every class-based view in CTFd is a `flask_restx.Resource` under
`/api/v1/*`. This is not a choice among alternatives — CTFd genuinely has no
class-based implementation of any of these five capabilities to harvest
instead.

**Redash — the class exists, but re-executing its module collides with the
live app.** `harvest_parts.py`'s `HARVEST_WHOLE_MODULE = True` harvests the
*entire file* a symbol lives in (so the part has its imports, base class,
helpers — everything it needs to import on its own). For
`redash/handlers/authentication.py` and `setup.py` and `queries.py`, that
whole file also contains **module-level `@routes.route(...)` calls** against
the shared `routes` Blueprint object imported from `redash.handlers.base`.
`build_source_app()` already built the real Redash app first — which already
imported and registered that same `routes` Blueprint once. `bind_shelf_parts`
then re-executes the harvested module as a fresh copy via
`importlib.util.spec_from_file_location`, which imports the *same, already-
registered* `routes` object (Python caches `redash.handlers.base` in
`sys.modules`) and tries to decorate it again — Flask refuses with exactly
the AssertionError above. `redash/handlers/data_sources.py`,
`visualizations.py`, `widgets.py` and `dashboards.py` contain no such
module-level route registration (routes are added centrally, in
`redash/handlers/api.py`, not in each handler module) and loaded and bound
cleanly.

**Neither failure is specific to my two apps' forms — both are structural,
in the host's binding mechanism itself, and were only ever going to surface
once a second real app was harvested.**

---

## Step 6 — the emptied-part proof

Done per the spec, on `CAP-0002` (log in — the `journey_cap_id` for both
apps) for each app: back up the real part, overwrite it with a single
comment line, run the chain, confirm the capability fails, restore, run
again, confirm recovery. This is where the host's binding gap above turns
into the single most important finding of this whole exercise.

### challenge-platform (CTFd)

Baseline (`RUN-0001`, real part in place):
```
PASS  a person can open the log in page
      200, served by CAP-0002
```
(`CAP-0002` was already reported `NOT BOUND` at binding time — "part has no
class named by 'login'" — this PASS is the per-request `SHELF_REQUESTS`
check, a *different* check in the same suite.)

`CAP-0002`'s `source.py` (681 lines, `symbol_verified: true`) backed up,
then overwritten with:
```python
# emptied for the emptied-part proof (HARVEST_TWO_MORE_APPS.md step 6)
```
Chain run again (`RUN-0003`):
```
FAIL  CHK-002  CAP-0002 is served by its own part on the shelf
      part has no class named by 'login'
...
PASS  a person can open the log in page
      200, served by CAP-0002
```

**Emptying the part changed nothing about the response.** Same status, same
body behaviour, same `X-Shelf-Capability: CAP-0002` stamp header, on a part
that is one comment line long and defines no route, no class, nothing at
all. The reason is now fully explained by Step 5: `CAP-0002` was never bound
to begin with, so the route was always being served by CTFd's own
unmodified, untouched `login()` function — the shelf's restriction
(`restrict()`) only decides *which routes exist*, and stamps *any* route it
recognises as belonging to a resolved capability, whether or not that
capability's own part is what actually answers it. **The stamp header —
`host_test.py`'s own documented proof that "a handler answering 'not found'"
is told apart from "the host refusing a route" — does not, in this case,
prove the shelf's part served the request. It proves only that the route's
path matched a capability's declared route string.** That is a materially
weaker claim than the one the check's own name makes ("is served by its own
part on the shelf"), and it was not visible until a real part was actually
emptied. This is the single most important result recorded in this
document, per the spec's own priority.

Part restored from backup (`diff` against the pre-harvest copy: identical,
681 lines, re-verified `ast.parse`), chain run a third time (`RUN-0004`):
result unchanged from `RUN-0001` in every respect that could be compared —
`CAP-0002` still `NOT BOUND` (that was never going to change, since the
symbol is a function, not a class; restoring the part does not fix the
binding mechanism's requirement), and "a person can open the log in page"
still `PASS, 200, served by CAP-0002`, for the same reason. Restoration
produced no regression and no improvement — exactly consistent with the part
never having been what served the route.

### data-dashboard (Redash)

*(same procedure, `CAP-0002` = `redash/handlers/authentication.py:login`,
345 lines)* [[TO BE COMPLETED — see below]]

---

## Step 7 — the browser recording

Both recordings drive the **real, unmodified `host.py`**, in its real
serving mode (`python3 host.py --app <slug>`, no `--check`, none of the
`host_test_*.py` scripts' more lenient bind-and-continue behaviour) — the
same entry point a real deployment would use. `host.py` refuses to start
(`FAIL_ON_UNRESOLVED = True`, unchanged) for both apps, per Step 5, so both
recordings show that refusal from a real browser's point of view rather than
a working login journey.

[[TO BE COMPLETED]]

---

## What actually happened, in numbers

| | Redash (data-dashboard) | CTFd (challenge-platform) |
|---|---|---|
| Capabilities harvested | 8/8, 0 failures | 8/8, 0 failures |
| Admission | passed, not refused | passed, not refused |
| Numbers reused from event-ticketing | CAP-0001/0002/0003 (register/login/logout) | CAP-0001/0002/0003 (register/login/logout) |
| New numbers minted | CAP-0016–0020 | CAP-0011–0015 |
| `shelf parts bound` | 4 / 8 | 3 / 8 |
| Chain terminal state | **HELD**, RUN-0002 | **HELD**, RUN-0001 |
| Emptied-part proof | [[TBD]] | chain still reported PASS with the part emptied — the shelf does not govern CAP-0002 for this app |
| Video | [[TBD]] | [[TBD]] |

---

## The four questions

### 1. Did register / log in / log out turn out to be shareable across apps, or did each app need its own?

**Both, at different layers, and the difference matters.**

At the *numbering* layer — yes, cleanly. `assign_numbers.py`'s registry
resolved "register account", "log in" and "log out" (for the "standard
individual" variant) to the exact same three numbers, `CAP-0001`/`0002`/
`0003`, for all three apps, with zero new numbers minted for any of them.
That is N2 working exactly as designed.

At the *code* layer — no. Every app still harvested its **own, real,
different** implementation under those shared numbers (Indico's `RHLogin`,
Redash's `login()`, CTFd's `login()`) — Rule E (one source per app) makes
sharing actual code across apps impossible by construction; sharing a number
was never sharing an implementation. That distinction turned out to matter
more than expected: `shelf_records.py`'s per-number (not per-app) records
cannot represent more than one of those three real implementations at a
time — see Step 3.

At the *runtime* layer — worse than "no". For CTFd, none of the three could
even be **bound** to their own part (they are plain functions, and the
host's binding mechanism only accepts classes). For Redash, the same three
also failed to bind, for an unrelated reason (the blueprint
re-registration collision in Step 5). In both apps, the routes still work —
served by the source application's own original code, never touched by the
shelf. The emptied-part proof in Step 6 shows exactly what that means in
practice: the shelf can be caused to look like it governs "log in" for
these two apps, when it does not.

So: the *concept* of register/login/logout is shareable, and the number
registry already treats it that way. The *code* was never shareable by rule.
And for two apps out of three, the *governance* — the actual point of the
whole exercise — currently is not real for these three capabilities at all.

### 2. Did the host need changing to serve a second and third app?

No source-of-truth logic in `host.py` was changed to make either app work —
`ENFORCE_ADMISSION`, `FAIL_ON_UNRESOLVED`, `RESTRICT_TO_SHELF`,
`BIND_SHELF_PARTS`, and every rule the 2026-09-15 "no application named
anywhere in the host" change depends on, are exactly as they were. `host.py`
correctly refused to serve both apps' shelf-restricted server in its normal
mode, and it was left refusing — that refusal was not worked around.

What *did* need doing, none of it inside `host.py`'s own logic:
- per-app copies of the test harness (`host_test_data_dashboard.py`,
  `host_test_challenge_platform.py`) — needed because `host_test.py` itself
  is written entirely against Indico (`INDICO_CONFIG`, Indico-specific
  routes and selectors), not parameterised by app at all
- per-app config-block edits to `layer1_checks.py` (`CHECK_SUITE`,
  `SUITE_ENV`), `layer2_repair.py` and `layer3_gap.py` (`APP_SLUG`) — these
  are exactly the fields each script's own header already documents as
  "RULES/CONFIG — edit these," and `chain.py` has no app-slug parameter of
  its own for them to read from
- a handful of pre-existing, unrelated directory-path mismatches — see
  "What a second source demanded" below — none of them admission or binding
  logic

So the honest answer is narrower than a flat yes/no: the host's *rules* held
without modification, and it used those rules to correctly refuse both apps
partial governance. But real infrastructure had to be built for a second and
third app to reach the host at all (bootstrap, migrations plumbing, per-app
harnesses), and along the way this session found and fixed one genuine,
pre-existing bug that blocks the chain for *any* app, including
event-ticketing — see below.

### 3. What did a second source demand that the first never did?

- **A generic "class → view" adapter, which neither new source provides.**
  Indico ships its own (`make_view_func`); Flask-RESTful and flask-restx
  both do this registration *inside their own library code*, never exposing
  an equivalent the source app itself defines. `view_adapter` had to be left
  blank on both new forms — a pattern the machine has no answer for beyond
  "leave it blank and let it refuse."
- **Function-based views, not classes, for exactly the capabilities that
  overlap across apps.** Register/login/logout (and CTFd's team join/create)
  are conventional `@blueprint.route` functions in both new sources — the
  more common shape for a plain Flask app, and the shape the host's
  class-only binding mechanism cannot serve at all.
- **A whole-module harvest can collide with the live app it's harvested
  from**, when the harvested module registers something onto a
  process-global, already-imported object (Redash's shared `routes`
  Blueprint). Indico's RH classes don't do this; Redash's function-based
  views do.
- **A real packaging defect** in Redash's own `pyproject.toml` (malformed
  author email breaks `pip install .` outright) that had nothing to do with
  Redash's application code and everything to do with getting it installed
  at all.
- **A CWD-relative migrations directory** in CTFd's own Flask-Migrate setup,
  and **a mandatory one-time setup gate** in front of every route — neither
  of which Indico has in the same form.
- **A real, intermittent (roughly half the time) deadlock** inside CTFd's
  own plugin loader when building fresh against Postgres — encountered
  repeatedly while trying to get a *repeatable* chain run, not a one-off.
- **Two pre-existing bugs in the pack itself**, unrelated to either new
  source, that this exercise is what actually exercised them for the first
  time: `chain.py`'s own `--dry` help text has a genuine Python syntax error
  (an f-string left unterminated across two lines) that makes `chain.py`
  fail to parse **at all**, for any invocation, on any app; and `chain.py`'s
  `TARGET` and `assign_numbers.py`'s `FORMS_DIR`/`REGISTRY_PATH`/`TREE_DIR`
  are resolved relative to the wrong directory and could never have found a
  real file as shipped. Both were fixed (see Step 3 and the note below) —
  not because the rules said to fix scripts, but because without fixing a
  genuine syntax error and two path constants, `chain.py` could not run for
  *any* app, including the one it was already supposedly proven against.
  Every one of these is a gap in the machine, not a quirk of either app.

### 4. Is the shelf a library?

**Partially, and the honest boundary is now much clearer than it was.**

The *numbering* layer is a real library: one registry, capabilities named
once and referenced by every app that has a real equivalent, proven across
three genuinely different app shapes (ticketing, reporting, competition).

The *harvest* layer is a real library: the same unedited `harvest_parts.py`,
run against two sources it had never seen, admitted both on their own
merits and refused neither by favouritism — Rules A–E did their job without
being touched.

The *governance* layer — the actual point, the thing the 2026-09-15 host
change was supposed to prove — **is not yet a library.** It worked for one
app because that app's whole shape (class-based RH handlers, with a
matching adapter Indico itself provides) happens to fit what the host's
binding mechanism assumes. Put two structurally different, very ordinary
Flask apps through it, and 3 of 8 and 4 of 8 capabilities respectively could
not be bound to their own shelf part at all, for two different structural
reasons, neither of which is a defect in either source app — plain function
views and framework-internal registration are both completely normal Flask.
Worse: the parts of the system that are supposed to make an unbound
capability visibly ungoverned (`X-Shelf-Capability`, `host_test.py`'s
"served by its own part" claim) do not reliably do that — Step 6 showed a
capability's chain check still reporting PASS, unmoved, when the real part
behind it was reduced to a single comment line.

So: a library of *numbers and harvested code*, yes. A library of
*governance*, not yet — and this exercise is what made that boundary
visible rather than assumed.

---

## Entries appended

- `GOD_MODE/REGISTERS/CHANGE_HISTORY.md` — one entry for this session.
