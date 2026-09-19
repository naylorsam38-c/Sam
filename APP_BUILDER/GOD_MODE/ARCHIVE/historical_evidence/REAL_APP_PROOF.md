SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Reason: Historical evidence report for a completed build round. Its operative rules and current test evidence are now stated directly in God_Mode_Specification.md and GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md. Nothing in this document was found to conflict with the current implementation; preserved as the historical record of how the current state was reached.
Original path: `REAL_APP_PROOF.md` (repo root)
Archived: 2026-09-13

---

# Real-app proof — round 7, 2026-09-12

## Why this document exists

Every proving-table row through round 6 (`verification/verify_build.py`, 29/29;
`verification/test_readiness.py`, 20/20) exercises `build.py` against ONE fixture
app -- CAP-0001, an "item list" toy Flask app invented for this engagement, not
one of Sam's real 43 catalogue app types. That was flagged honestly at the time
(`END_TO_END_PROOF.md`: "this run demonstrates the mechanism is sound using the
same real ... fixture this session's whole proving table is built on"), but when
asked directly -- "is the system built, full proof, ready to go, run this" -- the
honest answer was "yes and no": the machinery is real and proven, but nothing had
been built for any of the 43 real app types.

Sam's response: **"Rules no fake no synthetic ever so what do you mean yes or no?
Can you pick one and test it?"** -- a direct, correct callout of a hedge (his own
standing rule is no hedging, yes/no where a yes/no exists), and a direct
instruction. This document is that: one real app type, built and proven for real.

## What "real" means here, concretely

- **The app type**: "todo list" -- item #1, verbatim, of `canonical_app_types.py`'s
  real 43-item list (Sam's real catalogue, not invented).
- **The requirements**: sourced from the real, canonical, widely-used TodoMVC
  functional specification, fetched live and read in full --
  `https://github.com/tastejs/todomvc/blob/master/app-spec.md` -- not
  reconstructed from memory, not invented. The persisted fields (`id`, `title`,
  `completed`) are exactly the three properties that spec names. The seven
  real server-side actions below are exactly the seven real state changes the
  spec describes a todo list making. Filtering (`#/`, `#/active`, `#/completed`)
  is deliberately NOT a server capability, because the real spec places
  filtering at the model/client level -- inventing a server endpoint for it
  would have been adding a requirement the real spec doesn't have.
- **The build**: a real Flask host app, seven real Flask route modules, a real
  JSON-file-backed data store, a real HTML/CSS/JS frontend that actually
  implements add/toggle/edit/delete/toggle-all/clear-completed/hash-routing,
  run through the real, unmodified three-stage `build.py` pipeline -- real
  subprocess, real HTTP calls, real Playwright browser interaction.
- **Generator**: `verification/gen_real_todo_app.py` (rerunnable; not shipped
  with its generated output, same convention as `gen_fixtures.py`).

## The real gap this surfaced (found by reading the code, not guessed)

Pointing a genuinely different real app at `build.py` immediately surfaced a real,
previously undocumented limitation in `build_checks()` -- exactly the kind of
thing "pick one and test it" was supposed to surface:

1. **CHK-001/CHK-002/CHK-020 were gated on the literal string `"CAP-0001"`.**
   A real host module with a different capability id would silently get NONE of
   these checks -- not fail them, just never generate them, which is worse
   (a BUILT app with an unverified entry screen and no browser check at all).

2. **CHK-002 (the create-item check) is fixture-specific by design, not by
   accident.** CAP-0001's own fixture app.py bakes a create-item route directly
   into the host module itself (`GET`+`POST /api/items` on one route), bypassing
   the shelf route-module convention entirely -- flagged as a real design smell
   in build_checks()'s own round-4 docstring, not a pattern to generalize or
   copy. The real todo app deliberately does NOT repeat this: `create_todo` is
   its own real shelf capability (CAP-0102), covered by the existing generic
   compute-check loop instead.

3. **The generic compute-capability check generator (round 4) had only ever
   been proven against zero-input GET capabilities.** Pointed at real POST
   capabilities that require a real body (`create_todo` needs a `title`,
   `toggle_todo`/`edit_todo`/`delete_todo` need an `id`), it called every route
   with no body at all and failed every one of them -- not because the real
   capabilities were broken, but because the check generator had a real,
   previously unexercised gap.

4. **The generic compute-capability check generator also hardcoded `code != 200`
   as its only definition of success.** A real `POST` that creates a resource
   correctly returns `201 Created`, not `200` -- standard REST, not an invented
   requirement. The old check would have failed a correctly-behaving real
   endpoint.

None of these were worked around by warping the real app to fit the old checks
(e.g. renaming real TodoMVC fields to match the fixture's `text`/`created`, or
returning `200` instead of the correct `201`) -- that would have been exactly the
kind of fake accommodation Sam's rule forbids. All four were fixed properly in
`build.py` itself, generalized, and reproven against the full existing 29/29 +
20/20 suite with zero regressions before being proven against the real app.

## The fix, summarized (full diff is in `build.py` itself)

- `_detect_host_capability_id(app_json, registry)` -- new. Identifies the host
  module from a real, already-available fact: which capability's active IMPL
  entrypoint is the exact module `app.json`'s own `start` command launches (no
  capability id is hardcoded). Requires real evidence of a UI journey to check
  -- either the module is wired to a button (the old fixture's own pattern), or
  the template explicitly declares one via a new, optional, additive
  `primary_journey` field (the real-app pattern, for a host page that is pure
  infrastructure with every real action in its own separate, wired capability).
- CHK-001 and CHK-020 now key off `host_cap_id` instead of the literal string
  `"CAP-0001"`. CHK-020's browser interaction is now template-driven when
  `primary_journey` is declared (real selectors, real typed text, a real
  keypress -- e.g. Enter -- or a real click, whichever the real UI actually
  uses) and falls back to the exact original hardcoded CAP-0001 fixture journey,
  unchanged, when it isn't declared -- so every existing proven row keeps its
  exact original behavior.
- CHK-002 stays scoped to exactly `host_cap_id == "CAP-0001"` -- it is not a
  generalized check; it is the one true test of one fixture's one specific
  legacy baked-in-route pattern, and a host module that doesn't replicate that
  pattern correctly gets no such check, because there is nothing of that shape
  to check.
- The generic compute-capability check generator now reads
  `data_shape.input.required` off the capability's own shelf record and, when
  non-empty, sends a real request body built from it -- a fixed, generic probe
  value per field (an "id"-named field probes with `1`; anything else probes
  with a short real string naming the field), the same kind of arbitrary-but-
  real example data the original fixture already used (`"milk"`), not an
  invented capability or requirement. It also now accepts any `2xx` status,
  not only the literal `200`.

## The real run (clean room, `/tmp/real_app_cleanroom/proof/`, exit 0)

```
$ python3 build.py
2  choice read  app_type='todo list'
3  template resolved  todo_list
4  APP-001  allocated
1  fresh directory  .../builds/APP-001
5  parts copied  CAP-0100, CAP-0101, CAP-0102, CAP-0103, CAP-0104, CAP-0105, CAP-0106, CAP-0107
6  skin laid  skin-001@1.0.0
7  wired  1 screen, 7 button(s)
9  registry written  13/13 invariants passed
10  app.json + locators.json written
real todo list app -- no template-level tests declared beyond build.py's own proving run
11  template tests passed
12  APP-001  assembled  .../builds/APP-001

RUN-0001
PASS  a person arrives and sees the entry screen
PASS  List Todos responds and returns its declared output fields
PASS  Create Todo responds and returns its declared output fields
PASS  Toggle Todo responds and returns its declared output fields
PASS  Edit Todo responds and returns its declared output fields
PASS  Delete Todo responds and returns its declared output fields
PASS  Toggle All Todos responds and returns its declared output fields
PASS  Clear Completed Todos responds and returns its declared output fields
PASS  a person completes the declared primary journey and sees the result
9/9 checks passed — PASS
RUN-0001   build finished
BUILT
promoted  promoted APP-001 to library/APP-001 with 1 evidence run(s)
readiness  READY  --  promoted, with registry/app/locators and at least one evidence run report present

EXIT CODE: 0
```

Nine real checks, all real: one host-page render, six real HTTP round trips
against six real Flask route modules (list/create/toggle/edit/delete/toggle-all/
clear-completed), and one real Playwright browser session that typed real text
into the real `#new-todo` input, pressed a real Enter key -- no invented "Add"
button, because real TodoMVC has none -- and confirmed the real text appeared in
the real rendered `#todo-list`.

`reports/RUN-0001.json`, written unconditionally by stage two before any
promotion decision:
```json
{"run": "RUN-0001",
 "checks_passed": ["CHK-001", "CHK-201", "CHK-202", "CHK-203", "CHK-204",
                    "CHK-205", "CHK-206", "CHK-207", "CHK-020"],
 "checks_failed": [], "browser_check_present": true, "browser_check_passed": true}
```

The real, final persisted state, `builds/APP-001/data/todos.json` -- traceable
exactly from the real, sequential effect of every check above (create id=1 ->
toggle -> edit -> **delete** empties the store -> toggle-all/clear-completed are
no-ops on an empty store -> the browser check's own real create is the only
survivor, back at id=1 since the store was empty):
```json
[{"id": 1, "title": "Buy real milk from the real store", "completed": false}]
```

## Restart-survives-data (Master Spec §16 requirement #10), proven separately

A completely separate real proof, not part of the build run above: the real
assembled app process was started, queried, cleanly terminated (`SIGTERM`), and
a **second, brand-new process** started against the same real data directory:

```
run 1: health ok = True
run 1: GET /api/todos -> {'todos': [{'completed': False, 'id': 1, 'title': 'Buy real milk from the real store'}]}
run 1: process exited, returncode=-15
run 2: health ok = True
run 2: GET /api/todos -> {'todos': [{'completed': False, 'id': 1, 'title': 'Buy real milk from the real store'}]}
run 2: process exited, returncode=-15
```

The second, independently-started process reads back exactly the same real data
the first process wrote -- real persistence across a real process restart, not
asserted, not mocked.

## Real-machine readiness: what "will this run on Sam's laptop" actually needs

Everything above was proven in this session's own cloud sandbox, twice (a dev
directory and a genuinely fresh zip unzip) -- not yet on Sam's own machine,
because this session has no link to it. What actually determines whether it
runs there, with no guessing:

- **Python 3** on PATH (build.py itself is standard-library only; nothing
  else about it is environment-sensitive).
- **`pip install flask playwright`** -- both the real assembled app (Flask)
  and build.py's own real browser-driven check (Playwright) need them.
- **`playwright install chromium`** -- Playwright's Python package alone
  does not include the actual browser binary; this is a separate, required
  step, easy to miss.

**A real gap found and fixed by actually breaking it, not by inspection
alone**: before this round, if any of the above were missing, the real
assembled app's subprocess would crash immediately on its own real
`ModuleNotFoundError`, but `run_layer_one()` threw that real output away
unread and reported only a bare `BROKEN app did not start` -- true, but
useless for figuring out why. Tested by deliberately breaking a real import
in a real copy of the app (`from flask import Flask` -> a bad module name)
and running the real build:

```
RUN-0001
BROKEN  app did not start
real process output:
Traceback (most recent call last):
  File ".../modules/CAP-0100/app.py", line 11, in <module>
    from flask_totally_not_installed import Flask, jsonify, request, Response
ModuleNotFoundError: No module named 'flask_totally_not_installed'
```

Fixed in `build.py` itself (`_wait_for_health()` now also watches the real
subprocess's own exit, `run_layer_one()` now reads and surfaces its real
captured stdout/stderr the moment health-checking gives up) -- so a missing
dependency on any machine, Sam's included, now names itself instead of
hiding behind a generic timeout message. Reproven against the full 29/29 +
20/20 suite afterward (row 13's exact "no real output, bare message" path is
preserved unchanged) -- zero regressions.

This closes the "why did it fail" gap. It does not, on its own, prove the
real laptop has every real dependency already installed -- that still needs
either a real run on that machine, or Sam running the three commands above
and pasting back whatever build.py's own real output says.

## Full existing suite, reproven after every fix above, zero regressions

```
29/29 pass          (verification/verify_build.py)
all readiness/library checks passed   (verification/test_readiness.py, 20/20)
```

## What this does and does not claim

Does: proves, for real -- real Flask, real Playwright, real subprocess,
real file-backed persistence, real restart -- that `build.py` builds a
genuinely different real app (not the CAP-0001 fixture) drawn from Sam's real
43-app list, sourced from a real published specification, all the way to
`READY` and library promotion, with zero regression to every previously proven
row.

Does not: claim every one of the 43 real app types is now buildable -- one was
picked and proven, per the direct instruction ("can you pick one and test it").
Does not claim the generic compute-check generator's input-probing convention
(id fields -> `1`, other fields -> a short descriptive string) is the last word
on the subject -- it is a real, working, generically-derived first version,
proven against six real capabilities with real required-input fields it had
never seen before, and any future real app with different input shapes (e.g. a
required boolean or number field that isn't an id) would be the next honest
thing to prove it against, not a case to guess past now.
