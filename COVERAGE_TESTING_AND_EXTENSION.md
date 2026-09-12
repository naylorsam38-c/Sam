# Coverage testing — can the builder create new apps from the existing library?

After `FULL_LIBRARY_STRESS_TEST.md` closed the cross-app namespace-collision gap, the next real
question is coverage: pick genuinely new app domains, none of the 46 already built, and see whether
`build.py` can assemble them from the existing capability library — and where it can't, extend the
library safely (evidence-backed, regression-proven, zero regressions) rather than falling back to
one-off hand-written code by default.

## Method

Before inventing new app ideas, the library itself was audited for capability *shapes* that already
recur across multiple apps but were never generalized into a shared engine — real evidence, not a
guess about what a new engine "might" be useful for:

- **Unbounded increment** (`field += 1`, no upper limit, find-by-id): hand-written **six** separate
  times — `social_feed`'s "Like Post" and `photo_sharing`'s "Like Photo" (`likes`), `short_video_feed`'s
  "View Video" and `video_streaming`'s "Watch Video" (`views`), `music_streaming`'s "Play Track" and
  `podcast`'s "Play Episode" (`plays`) — never generalized.
- **Status transition** (set a named field to an input value, default fallback, find-by-id): hand-written
  **five** separate times — `crm`'s "Update Contact Stage", `project_management`'s "Update Task Status",
  `ride_hailing`'s "Update Ride Status", `invoicing`'s "Mark Invoice Paid", `parcel_tracking`'s "Update
  Parcel Status" (the one variant that also appends to a history list) — never generalized.

Two new generic engines were built to close these — evidence-backed, not speculative — then **three**
new apps were built, in genuinely new domains, to test coverage for real:

## Results

| New app | Domain | What it needed | Result |
|---|---|---|---|
| `recipe_box` | shared recipe box with likes | 1 new engine (`add_unbounded_counter_capability`) + plain CRUD + existing Notification engine | READY |
| `bug_tracker` | small issue tracker | 1 new engine (`add_status_transition_capability`) + plain CRUD + existing Notification engine | READY |
| `volunteer_shift_signup` | shift scheduling + sign-up | **zero** new engines — composed entirely from capabilities that already existed before this round | READY |

**`volunteer_shift_signup` is the direct, positive answer to "can the builder create new apps from the
existing library?"**: it composes `add_calendar_event_capabilities` (shift scheduling, real ISO-8601
validation — its 3rd real shipped use, after `community_event_board` and `course_enrollment_hub`),
`add_bounded_counter_capability` (sign-up capacity — its 4th real shipped use, after
`community_event_board`'s RSVP, `fitness_challenge_board`'s Join Challenge, and
`course_enrollment_hub`'s Enroll; `event_ticketing` itself still ships its own original hand-written
capability — the engine was proven equivalent to it by regression test, not substituted into the real
app), `add_notification_capabilities` (shift reminders), and a real,
byte-for-byte `reuse_capability_verbatim` of `team_chat`'s List/Post/Delete Message capabilities for a
discussion board — the **second independent app** to reuse that exact capability (`community_event_board`
was the first), proving reuse works many-to-one, not just once. No hand-written business logic beyond
the plain create/list boilerplate every app has some of.

## The two new engines, proven not just built

Both new engines (`gen_common.py`) funnel through the same `add_capability()` choke point every other
engine already uses, so they automatically inherit the namespace-collision fix, the Common Capability
Contract v2, and dependency declaration — no separate compatibility work needed.

- **`add_unbounded_counter_capability`**: proven behaviourally identical to `social_feed`'s real,
  original "Like Post" capability by direct regression test (`prove_generalization.py`, same
  methodology already established for the three RED-capability generalizations) — identical create,
  first like, second like (proving no upper bound), and 404-on-missing-record responses, byte for byte.
- **`add_status_transition_capability`**: proven behaviourally identical to `crm`'s real, original
  "Update Contact Stage" capability the same way, including a real, faithfully-reproduced quirk: an
  omitted status value resets to the hardcoded default rather than leaving the current value
  unchanged, because that's what the real original does — the point of the regression test is exact
  behavioural equivalence, not a silent "improvement."

## One real bug found and fixed along the way

`volunteer_shift_signup`'s first build failed its real Playwright browser check: the create-shift
click never showed the new shift. Root cause, not papered over: `add_calendar_event_capabilities` was
called with its default route (`/api/events`), but the app's own hand-written frontend JS called
`/shifts` — a mismatch in this app's own code, not a builder or engine defect. Fixed by correcting the
JS to call the capability's real, declared route. Left in this document rather than silently corrected,
per this project's own standard.

## Full reverification, nothing skipped

```
proving_table:              29/29 pass, readiness 20/20
canonical_apps:              43/43 READY (unchanged, untouched)
new_composed_apps:            6/6 READY (3 from the interoperability round + 3 from this round)
generalization_regression:  ALL MATCH (5 proofs: auction, event_ticketing, dating, social_feed, crm)
dependency_graph_audit:     CLEAN -- 0 missing targets, 0 cycles, 0 contract violations, 0 hidden
                             access across 294 capabilities in 49 projects
functional_tests:           30/30 passed (19 existing + 11 new)
full_library_stress_test:   184/184 passed, 0 collisions, 0 shadowed, 0 other failures
```

`OUTPUT_LIBRARY/` (still exactly the 43 canonical apps, untouched) and `NEW_APPS_FROM_LIBRARY/` (now 6
composed apps) are regenerated from the current generator so the committed, durable deliverable
matches. `run_full_verification.py` builds and stress-tests all 6 composed apps on every run, so this
stays checked automatically, not by memory.

## Honest scope note

Two capability shapes were generalized because they recurred **five and six times already** — real,
counted evidence, not a hunch. Plenty of other one-off logic in the library (e.g. payroll's 80% net
calculation, dating's reciprocal-match check) appears exactly once and was correctly left as
hand-written `add_capability` code — not every capability needs to be a shared engine, only the ones
that actually repeat. This coverage round did not attempt to enumerate every conceivable future app
domain; it tested three concrete, genuinely new ones and generalized exactly what real repetition
already justified.
