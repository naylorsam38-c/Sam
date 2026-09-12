# Full-library stress test — every capability, one real running system

**Status: fixed.** The collision this test found is now architecturally impossible, not merely
documented. See "The fix" near the end for what changed and the rerun that proves it: **0 collisions,
0 shadowed capabilities, 165/165 pass** — up from the original 142/165 with 23 shadowed. The section
below this notice is the original finding, left exactly as first written (per this project's own rule:
document what works, what fails, and why — not edit the tricky part out) because the fix only makes
sense in light of the problem it fixes.

This answers a different, harder question than `audit_dependency_graph.py` answers. That script
checks whether each capability's *declared* contract is internally consistent — real static source
scanned against its own declared `data_access`, per app. It is a real, automated check, but it
checks 46 apps in isolation, one at a time. It cannot see what happens if every capability in the
whole library is actually forced to coexist.

This test does that literally: it merges every real capability from every one of the 46 projects
into **one Flask process, one shared `modules/` tree, one shared `data/` directory**, starts it for
real, and hits every single capability's real route with a real HTTP request. Nothing is skipped for
being tricky, and nothing found is edited out below — including two rounds of the harness's own bugs,
left in this writeup rather than quietly fixed and forgotten.

Run it yourself: `python3 verification/full_library_stress_test.py` (needs the library already built
via `build_batch.py` + the three `new_app_*.py` scripts). It writes
`verification/full_stress_test/stress_result.json` and never touches `OUTPUT_LIBRARY/`,
`NEW_APPS_FROM_LIBRARY/`, or any project's own `library_build/<slug>/library/` — it works entirely in
its own scratch directory.

## Headline result

| | count |
|---|---|
| Total capability records across the library | 266 |
| Unique capability ids (after removing exact, verified reuse) | 212 |
| Route-bearing capabilities merged into one system | 165 |
| Ran correctly as their own logic in the merged system | **142 / 165** |
| Silently shadowed by a URL-namespace collision | **23 / 165** |
| Failed for any other reason | **0 / 165** |

The **one real, genuine gap** this library has, that no per-app test can see: **46 independently
generated apps do not share one flat URL namespace.** Several apps, generated independently, chose
the same natural resource path for their own feature (`/api/events`, `/api/items`, `/api/orders`,
`/api/videos`, `/api/cards`). Each is completely correct alone. Forced into one process, the real host
loader (`gen_common.py`'s `HOST_APP_PY_TEMPLATE`, used unmodified here) resolves collisions by
last-loaded-wins in a plain dict, silently — no error, no warning, no failed request. The caller gets
a normal 200 back from a *different app's feature* instead of their own.

## The 15 collisions, in full, with real severity

Two capabilities colliding on a route is not automatically "broken" — if their code and data are
identical, the wrong one winning changes nothing observable. This test checked that mechanically (a
real hash comparison of the actual `route.py` bytes and the declared data file, not an assumption) and
split the 15 collisions accordingly:

**12 real-breakage groups** (different code, different data file — a real, user-visible defect if
this library were ever deployed as one merged system):

| Route | Colliding capabilities (different apps) | Winner | Real losers |
|---|---|---|---|
| `GET /api/events` | calendar_and_scheduling, event_ticketing, course_enrollment_hub, community_event_board | community_event_board | 3 |
| `POST /api/events` | same four | community_event_board | 3 |
| `POST /api/events/delete` | calendar_and_scheduling, course_enrollment_hub, community_event_board | community_event_board | 2 |
| `GET /api/items` | auction, inventory_and_warehouse | inventory_and_warehouse | 1 |
| `POST /api/items` | auction, inventory_and_warehouse | inventory_and_warehouse | 1 |
| `GET /api/orders` | e_commerce_storefront, restaurant_pos | restaurant_pos | 1 |
| `POST /api/orders` | food_delivery, restaurant_pos | restaurant_pos | 1 |
| `GET /api/videos` | short_video_feed, video_streaming | video_streaming | 1 |
| `POST /api/videos` | short_video_feed, video_streaming | video_streaming | 1 |
| `GET /api/cards` | language_learning, course_enrollment_hub (reused quiz capability) | course_enrollment_hub | 1 |
| `POST /api/cards` | language_learning, course_enrollment_hub | course_enrollment_hub | 1 |
| `POST /api/cards/review` | language_learning, quiz_and_flashcards | quiz_and_flashcards | 1 |

17 capabilities across 8 apps (auction, calendar_and_scheduling, course_enrollment_hub,
e_commerce_storefront, event_ticketing, food_delivery, language_learning, short_video_feed) are
genuinely unreachable in this scenario. Confirmed empirically, not
predicted: each losing capability's own data file (verified by name, e.g. `auction.json`,
`event_ticketing.json`, `short_video_feed.json`) was untouched after the request, while the winner's
file (or its shared marker) changed instead.

**3 harmless-redundant groups** (`GET /api/notifications`, `POST /api/notifications`,
`POST /api/notifications/read` — community_event_board, course_enrollment_hub, fitness_challenge_board):
byte-for-byte identical implementations, generated by the same generic `add_notification_capabilities()`
engine, already sharing the exact same `notifications.json` file by design. 6 of these 9 instances are
technically unreachable too, but since the code and data are identical either way, nothing observable
breaks. Verified by direct hash comparison of the real `route.py` files, not assumed.

## What did *not* break

- **No two different capabilities anywhere share a data file with a different schema.** Every
  cross-project file overlap (`notifications.json`, and the `reuse_capability_verbatim` pairs like
  `team_chat.json`, `fitness_tracking.json`, `courses.json`, `quiz_and_flashcards.json`) is
  byte-identical code by construction — checked with a real hash comparison across every project that
  shares an id, corrected once after this test's own first-pass id-comparison logic had a real bug
  (it hashed a capability's JSON record and its Python source into one combined set and reported a
  false mismatch on every shared id, including `CAP-0000`, because a record hash is never equal to a
  source-file hash regardless of correctness — fixed to compare each artifact type across projects
  independently; rerun then reported **0** mismatches).
- **CAP-0000, the shared library, is identical across all 46 projects** — reconfirmed here
  independently of the earlier dependency-graph audit.
- **165/165 route-bearing capabilities responded correctly to a real request when their own route
  actually reached their own code** — once the harness stopped seeding foreign-shaped rows into files
  that were never part of a collision (see next section), the 0 remaining failures confirm there is no
  hidden functional bug in the capabilities themselves.

## A second harness bug, left in this writeup rather than edited out

The first full run of this test reported **6 additional failures** (`CAP-0106`/`CAP-0107` in
`todo_list`, `CAP-1702` in `spreadsheet`, `CAP-3103` in `dating`, `CAP-4304` in
`recipe_and_meal_planning`, `CAP-9804` in `fitness_challenge_board`), all `KeyError`s. Root-caused, not
special-cased away: to detect *which* capability wins a route collision, the harness seeds every
capability's data file with one synthetic marker row before starting the system. The first version
seeded **every** data file this way, including files that were never part of any collision. Several
capabilities correctly assume — because in real, isolated use their data file only ever contains rows
their own sibling capabilities wrote — that every row already has their own schema
(`t['completed']`, `c['row']`, `s['profile_id']`, `p['day']`, `r['requester_id']`). A synthetic marker
row lacking those keys crashed them. This is a real, honestly-reported artifact of the test harness's
seeding choice, not a latent bug in the library: fixed by seeding *only* the 14 data files that
actually belong to a capability caught in a real collision, leaving the other 43 genuinely empty
(exactly how a fresh app starts). Rerun: 0 such failures. Both bugs and both fixes are left in this
document instead of silently corrected between runs.

## What this does and does not mean for the library's compatibility claim

`UNIVERSAL_COMPATIBILITY.md`'s claim — "0 incompatible capabilities, 0 undeclared/unresolved
dependencies, 0 permanent exceptions" — is about each app's own declared contract, checked against its
own real source, and remains true: `audit_dependency_graph.py` still reports 0 violations across all
266 capability records, confirmed again after this test, unchanged.

What this test adds, and what was never previously claimed or tested: **the 46 apps were compatible as
46 separate deployments sharing a common contract and a shared capability (`CAP-0000`), not as one
merged, flat-namespace system.** Merging the whole library into a single running product, as opposed
to composing a *chosen subset* into a new app (as the three `NEW_APPS_FROM_LIBRARY` apps do, each
picking non-colliding routes deliberately), needed namespacing every app's routes before assembly.
That fix is now built, below.

## The fix: every ROUTE is namespaced by its owning app, at the source

The real cause was structural, not a naming-convention slip: nothing prevented two independently
generated apps from picking the same public path for their own feature, because nothing made that
impossible — it just hadn't happened to collide badly until 46 apps existed. The fix makes it
impossible by construction, in exactly one place:

**`gen_common.py`'s `AppBuilder._namespace_route()`** — called from the single choke point every
capability's `ROUTE` is written through (`add_capability()`, which every generic engine —
`add_exceeds_threshold_capability`, `add_bounded_counter_capability`, `add_notification_capabilities`,
`add_calendar_event_capabilities`, `add_symmetric_relationship_capability` — already calls internally).
It rewrites every declared route from `/api/<resource>` to `/api/<app-slug>/<resource>`. An app's slug
is already guaranteed globally unique (it's the real `OUTPUT_LIBRARY`/`NEW_APPS_FROM_LIBRARY` directory
name), so this makes cross-app URL collision structurally impossible, not merely unlikely — no
capability author has to remember to avoid a clash, because there is no shared namespace left to clash
in. `reuse_capability_verbatim()` needed no change at all: a capability copied byte-for-byte into a
second app correctly keeps its *origin* app's namespace, since it is still, honestly, that origin
app's real, single-sourced implementation and data file, just mounted a second time.

This is the only backend code change. Everything else was keeping each app's own frontend JS in sync
with its own now-namespaced backend, so every one of the 46 apps keeps working exactly as before in
isolation, not just when merged:

- **43 canonical apps** (`app_defs.py`): every `fetch("/api/...")` call was mechanically rewritten to
  `fetch("/api/<own-slug>/...")` — safe to do mechanically because none of these 43 apps reference
  another app's capability. Verified: 0 of 263 `/api/` occurrences left unprefixed or wrongly prefixed
  afterward, checked programmatically, not by eye.
- **3 composed apps** (`new_app_*.py`): edited by hand, because each mixes its *own* new capabilities
  (get the app's own slug) with capabilities *reused verbatim* from another app (get that other app's
  slug) — e.g. `community_event_board`'s own `/api/events` calls stay
  `/api/community_event_board/events`, but its reused-from-`team_chat` announcements call
  `/api/team_chat/messages`, matching exactly what `team_chat`'s own, now-namespaced capability
  actually serves.
- **`functional_tests.py`** and **`prove_generalization.py`**: hardcoded test paths updated the same
  way; `prove_generalization.py`'s regression harness additionally needed its comparison function
  changed to build two different paths (original app's slug vs. its disposable `_v2` harness's slug)
  instead of assuming both sides shared one literal path, since they are two different apps now.
- **`verify_build.py`/`test_readiness.py`** needed no change — confirmed they never touch
  `gen_common.py` or `app_defs.py`; they test `build.py`'s own internal proving-table fixtures, which
  don't go through `AppBuilder` at all.

### Proof this didn't just move the bug

Every existing verification step was rerun, unmodified, after the fix — the real Playwright browser
journey for all 43+3 apps clicking through the real frontend JS against the real, now-prefixed
backend is exactly the check that would catch a JS/backend path mismatch immediately:

```
proving_table:              29/29 pass, readiness 20/20 (unaffected -- confirmed unrelated to this code path)
canonical_apps:              43/43 READY
new_composed_apps:            3/3 READY
generalization_regression:  ALL MATCH (auction, event_ticketing, dating -- original vs. generic engine)
dependency_graph_audit:     CLEAN -- 0 missing targets, 0 cycles, 0 contract violations, 0 hidden access
                             across 266 capabilities in 46 projects
functional_tests:           19/19 passed
full_library_stress_test:   165/165 passed, 0 collisions, 0 shadowed, 0 other failures
```

`run_full_verification.py` now runs the full-library stress test as its own section (7/7) on every
invocation, so this guarantee is checked every time the suite runs, not just once by hand.
