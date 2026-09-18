# Spec — harvest two more apps, and prove the shelf is a library

**Written 2026-09-15. For whoever runs this next.**

The shelf currently holds ten parts from one source, serving one app. That is
not yet a library — it is one app's parts sitting in a folder shaped like a
library. This spec proves or disproves that, by putting two more apps through
the same machine and seeing whether anything breaks.

The host was changed on 2026-09-15 so that no application is named anywhere in
it. That change is the reason this test is worth running now, and this test is
what proves the change was real.

---

## The rule that governs everything below

**You fill in forms. The harvester fetches the code. You never write a part.**

If you find yourself opening a source file and copying a function into the
shelf, stop — that is the failure this whole system exists to prevent. Your job
is to fill in a form accurately and run `harvest_parts.py`. The harvester does
the fetching, the admission check, the provenance and the writing.

A second rule, equally hard: **if it refuses, that is a result, not an
obstacle.** Do not edit the scripts, loosen the admission config, or pick an
easier source to get a green run. A refusal recorded honestly is worth more
than a pass that was arranged.

---

## The two apps

Both were chosen against the Harvest Admission Rule — Flask, PostgreSQL,
permissive licence, published REST API docs, structural match to a commercial
exemplar. Both are real products people run, not tutorials or boilerplate.

They were chosen to be as unlike each other, and as unlike the existing app, as
possible. If the shelf holds up across these three, it is a library.

### App one — Redash

| | |
|---|---|
| `app_slug` | `data-dashboard` |
| Repository | `getredash/redash` — https://github.com/getredash/redash |
| Licence | BSD-2-Clause |
| Framework / datastore | Flask / PostgreSQL |
| API docs | https://redash.io/help/user-guides/integrations-and-api/api |
| Commercial exemplar | Metabase Cloud / Looker Studio |

**Structural match, for the form's `structural_match` field:** connect a data
source, write a query against it, turn the result into a visualisation, pin
visualisations onto a shared dashboard, and give other people a link — the same
connect / query / chart / share shape as Metabase, minus the hosted
infrastructure.

### App two — CTFd

| | |
|---|---|
| `app_slug` | `challenge-platform` |
| Repository | `CTFd/CTFd` — https://github.com/CTFd/CTFd |
| Licence | Apache-2.0 |
| Framework / datastore | Flask / PostgreSQL |
| API docs | Swagger, served by the app at `/api/v1/swagger.json` |
| Commercial exemplar | TryHackMe / HackerRank |

**Structural match:** a competitor registers, joins or forms a team, browses
challenges worth points, submits an answer which is graded right or wrong, and
a leaderboard ranks teams by score over time — the same register / attempt /
score / rank shape as TryHackMe, minus the hosted content library.

### Why these two

Three app types, three genuinely different shapes:

- existing — **ticketing**: book a place at an event and prove it at the door
- Redash — **reporting**: ask a database a question and publish the answer
- CTFd — **competition**: attempt a task, get graded, get ranked

They overlap on identity and not much else, which is exactly what makes them a
test. If log in and register turn out to be reusable across all three, the
shelf is a library. If every app needs its own copy of everything, it is not,
and it is much better to learn that now.

---

## Before you start — verify, do not trust this document

This document names a licence and a stack for each source. **Check both against
the repository itself before filling anything in.** Licences change, projects
migrate, and a document written on one date is not evidence about another.

If either source turns out not to be Flask, not to support PostgreSQL, or not
to carry a permissive licence, **stop on that app and report it**. Do not
substitute a different source without saying so. Do not carry on with one app
and quietly drop the other.

---

## Step 1 — write the two forms

One form per app, at `forms/data-dashboard.form.json` and
`forms/challenge-platform.form.json`.

Copy the shape from `forms/event-ticketing.form.json`, which is the only form
known to work end to end. Every top-level key it has, yours needs.

**`harvest_source` must carry all of these.** The last three are what the host
reads to build a runtime, and the 2026-09-15 change means the host has no
fallback if they are missing — it refuses rather than guessing:

```
repo_name, repo_url, licence, branch, commit,
framework, datastore, api_docs_url, structural_match,
app_factory        <- "module.path:callable" that builds the app
models_loader      <- "module.path:callable" that must run before a part loads
                      (empty string if that app needs none)
view_adapter       <- "module.path:callable" that makes an entry point servable
                      (empty string if entry points are already servable)
```

Find those three by reading how the source application boots itself — its
`wsgi.py`, its `create_app`, its blueprint registration. Do not guess them. If
you cannot find one, leave it empty, run anyway, and record exactly what the
host said when it refused. That refusal is a finding about the source, and it
is worth more than an invented value.

**`commit` must be a real full commit SHA** that you resolved from the
repository, pinned at the moment you harvest. Not `master`, not `HEAD`.

### The capabilities

Pick **six to ten capabilities per app**. Fewer than six does not test
anything; more is not needed to learn what this run is for.

Include, for both apps, whatever they have of: **register account, log in, log
out**. Those three are the overlap with the existing app, and whether they turn
out to be reusable is the single most interesting thing this exercise will
tell you.

Then the capabilities that make each app what it is:

- Redash — create a data source, run a query, create a visualisation, add to a
  dashboard, share a dashboard
- CTFd — list challenges, submit a flag, view the scoreboard, create a team,
  join a team

Each capability needs every key the existing form's capabilities have:
`cap_id, cap_name, engine, exemplar_target, what_it_does, route, method,
data_filename, binary_response, shared_lib_calls, data_shape, provenance,
variant`.

**`provenance` is the part that matters most:**

```
"provenance": {
  "source_file":   "path/within/the/repo.py",
  "source_symbol": "TheClassOrFunctionThatServesTheRoute",
  "source_lines":  "120-186"
}
```

`source_symbol` is what the host binds. Read the source and confirm the symbol
actually exists and actually serves that route. Where a capability genuinely
needs two symbols, write both separated by ` / ` — the host reads that form and
takes the class that serves the route. Where a symbol is a method, write it
dotted (`TheClass.the_method`); the host resolves the class that owns it.

**Numbers.** Capabilities are numbered once, globally, across the whole
library — not restarted per app. The existing app holds `CAP-0001` to
`CAP-0010`, so the next one issued is `CAP-0011`. Check
`pack/number_registry.json` for the true high-water mark before you assign
anything, and never reuse a number.

**Route strings must match the source's real routing exactly**, including
converters (`<int:query_id>`) and trailing slashes. The host resolves a form's
route against the built app's route table; a route that does not match resolves
to nothing and the capability is refused.

`journey_cap_id` should name the capability the browser journey drives. For
both apps, make it log in — it is the one you can drive without fixtures.

---

## Step 2 — harvest, and let it refuse you

From `pack/`:

```
python3 1_harvest/harvest_parts.py forms/data-dashboard.form.json
python3 1_harvest/harvest_parts.py forms/challenge-platform.form.json
```

Run them **one at a time**, not as a batch, so that a refusal on one is
unambiguous.

The admission check runs first and is all-or-nothing: a source failing any rule
is refused and **nothing is written** — it exits before anything is fetched.

Capture the complete output of both runs verbatim. If either is refused, record
the exact refusal text and the rule it names. **Do not fix it by changing
`ENFORCE_ADMISSION` or by editing `ALLOWED_LICENCES`.** If a source is refused,
it is refused, and that is the finding.

After a successful harvest, confirm for each app:

- `shelf/<app_slug>/CAP-XXXX/source.py` exists for every capability
- `PROVENANCE.json` beside it, with `symbol_verified` true
- `LICENCE.txt` beside it, carrying the source's real licence text
- every `source.py` parses: `python3 -c "import ast,sys;ast.parse(open(sys.argv[1]).read())" <file>`

A part whose `symbol_verified` is false means the harvester could not find the
symbol you named. Fix the form, not the part.

---

## Step 3 — numbering and shelf records

```
python3 2_numbering/assign_numbers.py
python3 shelf_records.py
```

Then confirm `shelf/capabilities/` and `shelf/implementations/` gained records
for the new capabilities, and that `shelf/aliases.json` is still a list under
the key `"aliases"`.

---

## Step 4 — install each source's runtime

A harvested part runs as its source wrote it, which means it needs its source's
library installed. Both apps will need their dependencies present, a real
PostgreSQL database, and a real config file.

Do this properly, the way it was done for the existing app:

- real PostgreSQL, real database, real schema created
- a **real config file** — never the source's own testing mode. The existing
  app's testing flag silently swapped PostgreSQL for SQLite, which made every
  result meaningless until it was caught. Assume the same trap exists here and
  check for it explicitly.
- whatever scratch directories the app writes to at request time must exist
  before it serves anything

Record exactly what you installed and what you had to create. That record is
what makes the run repeatable.

---

## Step 5 — run the host, then the chain

Per app:

```
python3 4_host/host.py --app data-dashboard --check
python3 4_host/host.py --app challenge-platform --check
```

`--check` starts nothing. Read its output closely. It tells you three things:

1. how many capabilities resolved to real routes
2. **`shelf parts bound: N`** — how many are served by their own part on the
   shelf
3. how many routes were kept and how many refused

**`shelf parts bound` must equal the number of capabilities.** Anything less
means the host is refusing to serve a route from code the shelf does not
govern, and it will name which capability and why. That message is precise;
act on exactly what it says.

Then the full chain, per app:

```
python3 5_chain/chain.py
```

Set `TARGET` in `chain.py`'s config block to the app slug before each run, or
pass the app through as that script's config expects. Leave
`ALLOW_LAYER_THREE = True`; if no model endpoint is configured, layer three
will hold and name the setting it lacks, which is the correct behaviour and
costs nothing.

**Expected terminal states:** `BUILT` if everything passes. `HELD` if something
failed that layer two could not repair and layer three could not reach a model
to fix. `BROKEN` if the system would not start. All three are real results.
Record which one you got and the run number.

---

## Step 6 — the proof that the part is what runs

Do this per app, after a clean `BUILT` or after recording whatever state you
reached. It is the same proof that validated the 2026-09-15 change, and it is
the only thing that demonstrates the shelf actually governs the app.

1. Copy one capability's `source.py` somewhere safe.
2. Overwrite it with a single comment line.
3. Run the chain.
4. **That capability must fail.** If the chain still passes, the part is not
   what runs, and everything above is decoration — stop and report that, it is
   the most important finding available.
5. Restore the part. Run the chain again. It must return to its previous state.

Record all of it: which capability, what the failure said, what the run numbers
were, and that the restore came back clean.

---

## Step 7 — the browser recording

This is the deliverable to hand back.

Drive each app with a real browser, through Playwright, against the host
actually serving that app. **Record video.** Not screenshots, not a log of
assertions — video of the journey, saved to a file.

Per app, the journey is the `journey_cap_id` capability, end to end:

- browser opens the route
- the page renders with the element that proves it is the real page
  (for log in, a password field)
- the journey completes

Save to `evidence/<app_slug>/journey.webm` alongside a short
`evidence/<app_slug>/RUN.md` naming the run number, the terminal state, the
date, and what the video shows.

Playwright config, in the script's own config block at the top of the file,
above any logic, one comment per setting:

```
RECORD_VIDEO_DIR   -- where the video is written
HEADLESS           -- True for a machine, False to watch it happen
BASE_URL           -- the host's address, matching HOST_BIND and HOST_PORT
JOURNEY_PATH       -- the route being driven
EXPECT_SELECTOR    -- the element that proves the real page rendered
TIMEOUT_MS         -- how long before a step is called failed
```

**If a journey fails, record the failed video and hand that back.** A video of
the thing not working is evidence. A missing video described in prose is not.

---

## Step 8 — write up what actually happened

`evidence/TWO_MORE_APPS.md`. Write what happened, not what was meant to happen.

For each app, in plain terms:

- every command run, and its real output
- what was refused, and the exact words of the refusal
- how many capabilities resolved, how many bound, how many were served
- the terminal state and run number of every chain run
- the emptied-part proof and its result
- where the video is and what it shows
- everything that went wrong, including anything you fixed and how

Then the four questions this whole exercise exists to answer:

1. **Did register / log in / log out turn out to be shareable across apps, or
   did each app need its own?** This is the library question. Answer it
   directly.
2. **Did the host need changing to serve a second and third app?** It should
   not have. If it did, that is the 2026-09-15 change not holding, and it needs
   saying loudly.
3. **What did a second source demand that the first never did?** Every one of
   those is a gap in the machine, not a quirk of the app.
4. **Is the shelf a library?** Yes or no, and why.

Finally, append one entry to `GOD_MODE/REGISTERS/CHANGE_HISTORY.md` — what was
harvested, what state each app reached, and what was learned.

---

## What counts as done

- two forms written, both naming real commits and real symbols
- both sources put through the harvester, refusals recorded verbatim
- both apps' parts on the shelf, parsing, with verified provenance and licence
- `shelf parts bound` equal to the capability count, for both
- the chain run for both, terminal state recorded
- the emptied-part proof run and recorded, for both
- a real browser video per app, saved to a file
- `TWO_MORE_APPS.md` written, and the four questions answered straight
- nothing invented, no script loosened to make something pass

Anything you could not do, name it and say why. An honest gap is a result. A
gap papered over is the one thing this system was built to make impossible.
