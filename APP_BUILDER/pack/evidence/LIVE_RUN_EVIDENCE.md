# Live run evidence

Everything below was produced by running real software against a real
database. No mocks, no simulated providers, no synthesised data. Where a
figure appears it was printed by the run, not written by hand.

## The stack that was stood up

| Piece | What was actually used |
|---|---|
| Source application | Indico 3.3.13, installed from PyPI as a real wheel |
| Source repo | `indico/indico` @ `eb90264caec7d1210959c453d1f93ad88a98e6ce`, MIT |
| Database | PostgreSQL 16.15, real server, database `indico` created |
| Cache / broker | Redis, real server, `redis-cli ping` -> PONG |
| Schema | `db.create_all()` -> 172 real Indico tables |
| Config | a real config file at `INDICO_CONFIG`, not testing mode |

A note on testing mode, because it cost time: `make_app(testing=True)`
silently swaps PostgreSQL for SQLite. That is not the datastore Rule A
names, so every run here used a real config file instead.

## Step 1 -- the parts import

All ten harvested capabilities import and expose real handler classes.

Loading required Indico's own model loader first
(`import_all_models()`), because SQLAlchemy cannot resolve its mappers
until every model is registered. Without it the import fails with
`InvalidRequestError: expression 'EventSeries' failed to locate a name`.

Result: **10/10 import.** CAP-0004 exposes `RHAPISearch`,
`RHAPISearchOptions`; CAP-0008 exposes `RHCheckinAPIBase`,
`RHCheckinAPIEventDetails`, `RHCheckinAPIRegFormBase`; the auth parts
expose 13 handlers each; the registration-list parts 50 each.

Importing is not serving. That is what step 2 is for.

## Step 2 -- the parts answer real HTTP

The application built with **1130 live routes**. Requests were made and
answered:

| Capability | Request | Result |
|---|---|---|
| CAP-0001 register account | `GET /register/` | 200, 92411 bytes |
| CAP-0002 log in | `GET /login/` | 200, 6755 bytes |
| CAP-0003 log out | `GET /logout/` | 302, 189 bytes |
| CAP-0004 search records | `GET /search/api/search?q=test` | 422, malformed query correctly rejected |
| CAP-0008 scan barcode | `GET /api/checkin/ticket/<uuid>` | 404, no such ticket, correct on an empty database |

Two things found here are worth keeping:

- The check-in route was first reported missing. It was not. It is
  `/api/checkin/event/<int:event_id>/` **with a trailing slash**, and the
  check compared the string without one. Eight real check-in routes are
  live. The fault was in the comparison, not the code.
- A run of 500s traced to PostgreSQL having stopped, not to any part:
  `psycopg2.OperationalError: connection to server on socket
  "/var/run/postgresql/.s.PGSQL.5432" failed`. Restarting it resolved
  every one to a proper status code.

## Step 3 -- the host serves the shelf

`4_host/host.py` is the join between the shelf and a running server.

A harvested part stands on its source package -- that is what the
whole-module harvest established. So the host does not try to run a part
in a vacuum. It builds the source application's own stack, then serves
**only** the routes belonging to capabilities on the shelf. Everything
else the source ships is refused at dispatch.

That is what makes it a host rather than the source app running: the
shelf decides what the app is.

Proven over a real socket by `4_host/host_test.py`:

```
shelf admits 10 capabilities; 10 routes kept, 1120 refused

  ON THE SHELF -- must answer:
    CAP-0002 log in              200   6755     served by CAP-0002
    CAP-0003 log out             302   189      served by CAP-0003
    CAP-0001 register account    200   92411    served by CAP-0001
    CAP-0004 search records      422   89673    served by CAP-0004
    CAP-0008 scan barcode        404   139      served by CAP-0008

  NOT ON THE SHELF -- must be refused:
    /admin/                        404   refused
    /categories/                   404   refused
    /about/                        404   refused

failures: 0
```

Every response served by a shelf capability carries an
`X-Shelf-Capability` header naming the number that served it. That is
how a handler answering "no such record" is told apart from the host
refusing a route that is not on the shelf -- the first carries the
header, the second does not. It is why CAP-0008's 404 counts as the
capability working.

## Faults found by running it

Three were mine, and all three were only visible because the thing ran:

1. The first host rebuilt the source application's URL map. That threw
   away routing behaviour the parts depend on and every route returned
   500. Fixed by refusing at dispatch and leaving the source map alone.
2. The first test ran on a different port from the source's `BASE_URL`.
   The source sets Flask's `SERVER_NAME` from it and Flask refuses any
   request whose Host header does not match, so every route 404'd for a
   reason that had nothing to do with the shelf.
3. The first test followed redirects, so log out looked broken when it
   was working -- the redirect landed on a route not on the shelf and was
   correctly refused.

## What this does not yet prove

The capabilities answer, and the shelf governs what exists. Assembling a
second app from the same shelf has not been run.

---

## The test rewritten to the Script Standard (2026-09-15)

`4_host/host_test.py` was rewritten to meet the Script Standard. The previous
version failed it on three counts: it printed its own output format, it drove
HTTP where a person would drive a browser, and it reused whatever database and
directories the last run left behind.

It now starts PostgreSQL and Redis itself, drops and recreates every table,
rebuilds the storage and scratch directories, serves the host on its own port,
drives a real chromium browser through the log in page, and shuts the process
down on the way out including on failure.

```
host on 127.0.0.1:8000  --  shelf admits 10 capabilities, 10 routes kept, 1120 refused

PASS  every capability on the shelf reached a live route          10 of 10
PASS  a person can open the log in page                           200, served by CAP-0002
PASS  logging out sends the person onward                         302, served by CAP-0003
PASS  a person can open the register page                         200, served by CAP-0001
PASS  a search with no valid query is rejected, not crashed       422, served by CAP-0004
PASS  scanning a ticket that does not exist says so               404, served by CAP-0008
PASS  the admin area the shelf never admitted stays gone          404, refused
PASS  the category browser the shelf never admitted stays gone    404, refused
PASS  the about page the shelf never admitted stays gone          404, refused
PASS  a person can use the app in a real browser                  opened /login/ in chromium
PASS  the page a person lands on throws no javascript errors

11/11 checks passed -- PASS, the shelf governs the app and a person can use it
```

### Two real defects the browser check found

Neither was visible over HTTP. Both pages returned 200 the whole time.

**1. The host was refusing every stylesheet and script on the page.** The
static test in `host.py` matched on the route's path. Indico serves all of its
assets through one converter rule --
`/<any(css,dist,images,fonts):folder>/<path:filename>.<fileext>` -- whose path
begins with none of the literal prefixes the test looked for, so every
stylesheet, script and image was refused while the page itself still rendered
200. Fixed by matching on the endpoint's blueprint, with the blueprint names in
the config block as `STATIC_ENDPOINT_NAMES`.

**2. The source application's cache directory did not exist.** Indico generates
per-version javascript into `CACHE_DIR` at request time and raises
`FileNotFoundError` when the directory is absent, costing the landing page its
scripts without costing it its status code. The test now rebuilds the source
application's own scratch directories alongside the database, listed in the
config block as `SOURCE_SCRATCH_DIRS`.

### The six breaks, run for real (Script Standard §7)

A script never seen to fail has not been tested.

| Break | Result |
|---|---|
| No real config supplied | exit 2, `0 checks claimed -- UNPROVEN`, refused to substitute a testing config |
| Level-1 browser check switched off | `SKIP`, exit 3, `no level-1 check ran` -- never reported as a pass |
| A capability pointed at a route that does not exist | exit 1, named `CAP-0002`, and said the host refused it rather than the capability serving it |
| Shelf restriction switched off | exit 1, every shelf and refusal check failed -- the stamp is what proves a capability served, not the status code |
| The stylesheet fix reverted | exit 1, browser caught 16 javascript errors, first a 404 on a resource |
| PostgreSQL stopped | exit 2, named the socket in the failure, claimed no checks |

Restored after each. Final run: 11/11, exit 0.

---

## 2026-09-15 — `watch.py` built and break-tested

The audit now exists as a script, not just a spec. Read-only: it never repairs,
never writes to the shelf, never calls a model, never touches the app.

**The run-record contract had to be defined first.** Nothing in the chain wrote
a record a run could be audited from. `run_record.py` is that contract, and
`host_test.py` now writes one on every exit path — including the paths where it
could not start, because a run that leaves no record cannot be audited and a run
that cannot be audited is not BUILT.

**Audited against a real run.** RUN-0001 onward are real runs of the real host
against real PostgreSQL, real Redis and real chromium. Part origins are read off
each part's own `PROVENANCE.json` — all ten harvested, none assumed.

### The break tests, run for real

| Break | What was done to a real run | Result |
|---|---|---|
| 1 | browser check switched off | `W-05`, `W-06`, `W-07` FAIL — exit 1 |
| 2 | database not rebuilt between runs | `W-01` FAIL — exit 1. **`host_test.py` exited 0 and reported PASS; the audit refused it anyway.** |
| 3 | a part's `PROVENANCE.json` removed | `W-22` FAIL — origin recorded as unknown, never quietly assumed harvested |
| 4 | the static fix in `host.py` reverted | `W-07` and `W-21` FAIL — caught both the javascript errors and the regression against the previous passing run |
| 5 | run record truncated mid-JSON | exit 2, `NOT AUDITED, and therefore not BUILT` — claims nothing |
| 6 | run record deleted | exit 2, same |
| 7 | `W-06` switched off in the config block | `NARROWED: 1 check(s) switched off -- W-06` printed before anything else |

Restored after each. Final state: `host_test.py` 11/11 exit 0, `watch.py` 12/22
passed with 10 not applicable, exit 0.

### What has not been proved

`W-13` to `W-19` audit layer three — gap records, what the model was sent, how
many candidates were generated, whether the winner was driven through the chain.
**No real run has entered layer three, because `layer3_gap.py` does not exist
yet.** Those seven checks have never fired against real data and were not
exercised by fabricating a gap that never happened. They stay unproven until the
chain can raise a real one.
