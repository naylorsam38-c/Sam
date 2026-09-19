SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Reason: Historical evidence report for a completed build round. Its operative rules and current test evidence are now stated directly in God_Mode_Specification.md and GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md. Nothing in this document was found to conflict with the current implementation; preserved as the historical record of how the current state was reached.
Original path: `INTEROPERABILITY_UPGRADE.md` (repo root)
Archived: 2026-09-13

---

# Interoperability upgrade — from audited library to composable library

This is the follow-up to `COMPATIBILITY_AUDIT.md`. That audit found a real architectural idiom shared
across the 43 apps but not yet a composable ecosystem, and named exactly what was missing. This upgrade
closes each gap for real and proves it — the 43 apps were not thrown away or rebuilt; the library
underneath them was upgraded, and one genuinely new app was assembled from it as the decisive proof.

## What changed

### 1. Every capability now declares its dependencies — and build.py enforces them

The audit found the shelf's `dependencies` field empty in all 187 capabilities, including the one real case
where it mattered: `payroll`'s "Run Payroll" reads a sibling capability's data file (`employees.json`) with
no declared dependency. `gen_common.py`'s `cap_record()`/`add_capability()` now accept a real `dependencies`
parameter, and `payroll`'s "Run Payroll" now declares `["CAP-1002"]` — the one capability in the library that
actually needed to.

That declaration is no longer decorative. `build.py`'s `stage1_assemble()` now checks, for every capability a
template requires, that everything it declares as a dependency is *also* required by that same template —
and refuses to build if not:

```
$ python3 build.py     # payroll's template edited to require "Run Payroll" without "Add Employee"
2  choice read  app_type='payroll'
3  template resolved  payroll
4  APP-001  allocated
1  fresh directory  /tmp/dep_test/builds/APP-001
5  parts copied  CAP-1000, CAP-1001, CAP-1003, CAP-1004
BROKEN  missing declared dependency  CAP-1003 requires CAP-1002
EXIT: 2
```

Before this change, that same template would have built successfully and silently produced `{created: 0}`
forever — exactly the failure mode the audit warned about. Reproven after the change: **29/29**
(`verify_build.py`), **20/20** (`test_readiness.py`), zero regressions.

### 2. The 3 RED (non-reusable) capabilities are now generic, reusable engines

The audit found three capabilities with real, domain-specific business rules and no reusable shape:
`auction`'s bid validation, `event_ticketing`'s capacity check, `dating`'s reciprocal-match search. Each is
now a generic, parameterized generator in `gen_common.py`:

- `add_exceeds_threshold_capability` — "a proposed value only takes effect if it beats the current one,"
  generalized from auction's bid rule.
- `add_bounded_counter_capability` — "increment a counter only while it stays below a limit," generalized
  from event_ticketing's capacity rule.
- `add_symmetric_relationship_capability` — "record a one-way proposal, detect a reciprocal one,"
  generalized from dating's match rule.

**Proven, not asserted**: `verification/prove_generalization.py` builds a disposable variant of each original
app where only that one capability is swapped for the new generic generator, runs both the original and the
variant through the real, unmodified `build.py` pipeline, and replays an identical real HTTP sequence against
both real running processes:

```
MATCH  create item        (201, {'current_bid': 10.0, 'highest_bidder': None, 'id': 1, 'title': 'Regression Test Lamp'})
MATCH  bid too low (5 <= 10)   (400, {'error': 'bid too low'})
MATCH  bid higher (20 > 10)    (200, {'current_bid': 20.0, 'highest_bidder': 'bob', ...})
MATCH  bid not higher (20 <= 20)   (400, {'error': 'bid too low'})
MATCH  bid on missing item     (404, {'error': 'no item with id 999'})
...
ALL MATCH
```

All three: byte-for-byte identical behavior across every real request, original vs. generic generator.

### 3. Two capability types that didn't exist anywhere now do

The audit found zero notification or calendar capabilities anywhere in the 187. Both are now real, generic,
parameterized generators:

- `add_notification_capabilities` — create/list (filterable by recipient)/mark-read, an append-only real data
  store.
- `add_calendar_event_capabilities` — create/list/delete, with **real ISO-8601 validation** (rejects a
  malformed date with a 400 instead of silently storing it — a genuine capability upgrade over the two
  original ad hoc date fields, not just a rename), and an `extra_fields` mechanism so a caller can extend the
  event schema (e.g. a capacity field) without forking the generator.

Proving these surfaced a real, second interoperability gap: `build.py`'s generic compute-check prober sends a
plain string (`"probe value for start"`) for any required field it doesn't recognize — correct for a normal
text field, wrong for a field that does real semantic validation. Fixed the same way the existing "id" special
case was: a field recognizably date/time-shaped by name now gets a real, valid ISO-8601 probe. Reproven
afterward: 29/29 + 20/20, zero regressions.

### 4. The decisive proof: a new app assembled from the library, not rebuilt

`NEW_APPS_FROM_LIBRARY/community_event_board/` is a genuinely new app type — not one of Sam's original 43 —
built almost entirely by composing existing and upgraded library pieces:

| Piece | Source |
|---|---|
| Event creation/listing, real date validation | NEW `add_calendar_event_capabilities` |
| RSVP capacity limit | `add_bounded_counter_capability`, called **unmodified**, in a new domain (RSVP, not ticket sales) from the one it was regression-tested against |
| Notifications | NEW `add_notification_capabilities` |
| Announcements feed | **CAP-1201/1202/1203, byte-for-byte unmodified files reused verbatim from `team_chat`** — the same mechanism the audit's Test A proved live, now shipped in a real app |

Composition happens two ways here, both real: the RSVP and Notification capabilities are independently
built and combined by the new app's own frontend JS (call RSVP, then call Notify) — no new backend coupling
invented; the announcement capability is reused at the file level, the same id, same code, copied verbatim
into this app's shelf.

Built through the real, completely unmodified `build.py` pipeline:

```
5  parts copied  CAP-9900, CAP-9901, CAP-9902, CAP-9903, CAP-9904, CAP-9905, CAP-9906, CAP-9907, CAP-1201, CAP-1202, CAP-1203
...
RUN-0001
PASS  a person arrives and sees the entry screen
PASS  Create Event responds and returns its declared output fields
PASS  Post Message responds and returns its declared output fields
PASS  a person completes the declared primary journey and sees the result
4/4 checks passed — PASS
BUILT
promoted  promoted APP-001 to library/APP-001 with 1 evidence run(s)
readiness  READY  --  promoted, with registry/app/locators and at least one evidence run report present
```

And exercised end to end, for real, beyond the automated checks (disposable copy, never the committed app):

```
1. create event, capacity=1:        (201, {'attendees': 0, 'capacity': 1, ...})
2. RSVP (1st, should succeed):      (200, {'attendees': 1, 'capacity': 1, ...})
2b. notify on success:              (201, {'message': 'You are confirmed for Tiny Picnic', ...})
3. RSVP (2nd, should fail -- full): (400, {'error': 'event is full'})
3b. notify on failure:              (201, {'message': 'RSVP failed for Tiny Picnic: event is full', ...})
5. post announcement (team_chat's own capability, unmodified): (201, {'author': 'Organizer', ...})
7. invalid date still rejected:     (400, {'error': "start is not a valid ISO-8601 timestamp: 'not-a-real-date'"})
```

Every real thing this app does — the capacity limit, the notification, the announcement — is either an
upgraded shared capability or an unmodified capability borrowed from another app. Nothing here was hand-built
CRUD for a new domain the way the original 43 were.

**One honest, visible byproduct of true unmodified reuse**: the borrowed team_chat capability files still
reference their original data filename (`data/team_chat.json`) rather than something board-specific. That's
not a bug to paper over — it's the real, transparent cost of literal file-level reuse, worth knowing about
before reusing a capability this way at larger scale.

## Two real mistakes caught and fixed along the way

- `dating`'s committed `OUTPUT_LIBRARY` data was found to contain manual test artifacts (from an earlier
  verification pass, committed by oversight) — not the pristine output of a real build. Regenerated from the
  same unmodified generator and replaced; the fix is a 2-line diff (`data/profiles.json`, `data/swipes.json`,
  plus a timestamp in `registry.json`).
- The regression-proof harness itself originally started test processes directly against `OUTPUT_LIBRARY`,
  which would have written real test data into committed files again — fixed to always run against disposable
  copies with data reset to empty before comparison, so both sides of every regression test start from
  identical real state.

## What this does and does not claim

**Does**: every fix above is proven by a real build.py run, a real regression comparison against real HTTP
responses, or both — never by code-reading alone. The existing 43-app library was re-verified with zero
regressions at every step (29/29, 20/20, 43/43 apps, re-run clean-room from scratch at the end).

**Does not** claim the ecosystem question from `COMPATIBILITY_AUDIT.md` is now fully closed. Still real,
still open: no shared identity/auth layer, no shared cross-app ID/reference scheme, and browser-side
combination (as opposed to the file-level and orchestration-level composition proven here) still needs CORS
headers or a gateway. What this upgrade proves is narrower and real: the specific gaps the audit could name
concretely (undeclared dependencies, 3 non-reusable capabilities, 2 missing capability types) are now fixed
and demonstrated, and a new app can be assembled from the library today — proven by actually doing it, not by
arguing it should work.
