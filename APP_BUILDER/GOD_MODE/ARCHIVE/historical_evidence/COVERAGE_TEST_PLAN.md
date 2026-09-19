SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Reason: Historical evidence report for a completed build round. Its operative rules and current test evidence are now stated directly in God_Mode_Specification.md and GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md. Nothing in this document was found to conflict with the current implementation; preserved as the historical record of how the current state was reached.
Original path: `COVERAGE_TEST_PLAN.md` (repo root)
Archived: 2026-09-13

---

# Coverage Test Plan — Phase 2

The compatibility phase is closed: 294 capabilities, 49 projects, 0 route collisions, 0 silent
shadows, 0 capability failures, verification suite green. That proves the library is *internally
consistent*. It says nothing about how *broad* it is. This plan is the next, harder question: pick
genuinely new app requests — the kind a real person would actually ask for — and find out whether
`build.py` can assemble them from what already exists, or whether the library has to grow to answer
them honestly.

**This is a plan only. Nothing below has been built yet.** Each test is specified in full first; the
report on what actually happened when they were run is a separate, later deliverable — because
"predicted composable" and "actually composable" are not the same claim, and this project's whole
practice this session has been to prove that gap empirically rather than assume it closed.

## Reference: what the library can actually do today

Before predicting anything, here is the real, current capability surface — not a guess:

| Engine (`gen_common.py`) | Real shape | Real precedent(s) |
|---|---|---|
| `add_capability` | any one-off CRUD/action, hand-written body | ~140 uses across 46 apps |
| `add_exceeds_threshold_capability` | proposed value must exceed a current value | auction bid |
| `add_bounded_counter_capability` | increment a field, reject at/over a limit on the same record | event_ticketing, RSVP, Join, Enroll (4 real uses) |
| `add_unbounded_counter_capability` | increment a field, no limit | social_feed/photo_sharing likes, recipe_box likes |
| `add_status_transition_capability` | set a named field from input, default fallback, **no transition validation** | crm stage, bug_tracker status |
| `add_symmetric_relationship_capability` | one-way proposal + mutual-match detection | dating swipe, fitness buddy match |
| `add_notification_capabilities` | create/list/mark-read, recipient is a free-text string | 6 real uses |
| `add_calendar_event_capabilities` | create/list/delete with real ISO-8601 validation | 3 real uses |
| `reuse_capability_verbatim` | copy another app's real capability byte-for-byte, keeps its route namespace | team_chat messages (2x), fitness_tracking workouts, online_course_lms courses, quiz cards |
| `CAP-0000` shared library | JSON load/save, error-code mapping, `notify()` | every capability depends on this |

What is **confirmed absent**, checked directly against the real code, not assumed:

- **No real identity/auth.** `gen_common.py`'s `_make_ctx()` always returns
  `{"user": None, "authenticated": False}`. Every "recipient" or "author" field anywhere in the
  library is a free-text string the client sends, never a real logged-in identity, session, or
  permission check.
- **No aggregation/report engine.** Nothing sums, averages, or derives a computed value across a
  collection (`accounting_ledger`'s "Ledger Balance" and `payroll`'s net-pay math are one-off
  hand-written `add_capability` bodies, never generalized, never reused elsewhere).
- **No scheduling or background/time-driven state change.** Every capability only ever runs in
  response to an HTTP request; nothing changes state on its own because a clock ticked past a
  deadline.
- **No validated state-machine.** `add_status_transition_capability` accepts any string as the new
  status — faithfully reproducing its real precedents, none of which validate transitions either.
- **No dedicated binary/file storage.** `file_storage_and_sync`'s "Upload File" stores a `content`
  field inside the ordinary JSON array (a real string can hold base64, so it isn't strictly
  impossible to smuggle small binary data through, but there is no real streaming upload, no
  content-type-aware download route, and no engine anyone else could reuse for "store a blob").
- **No document/PDF generation of any kind.**
- **No graph/tree relationship beyond one-way and symmetric pairs** (`add_symmetric_relationship_
  capability` models exactly two-party mutual state; nothing models a tree, a directed multi-hop
  graph, or a parent/child hierarchy).

Every test below is chosen to press on one or more of these real edges, not on capabilities already
proven to work.

## Governance standard — how a gap gets closed, every time, no exceptions

This is stated once here rather than repeated in every test row below. When a test finds a real,
missing capability:

1. **Confirm it's real, not a one-off.** Check whether the same shape already recurs elsewhere in
   the library (like the six-times-repeated "like" pattern and five-times-repeated "status" pattern
   found last round) or is a genuinely new, foundational gap (like real auth). Both are legitimate
   reasons to build something; "I can imagine wanting this once" is not.
2. **Route it through the one real choke point.** Any new generic engine calls `self.add_capability()`
   internally, exactly like every existing engine — this is what makes the namespace-collision fix,
   the Common Capability Contract v2, and dependency declaration automatic, not something to
   re-implement per engine.
3. **Prove it, not just ship it.**
   - If a real hand-written precedent already exists somewhere in the library: build a disposable
     "_v2"-style regression harness and replay an identical HTTP sequence against the original and
     the new generic engine, asserting byte-identical responses (`prove_generalization.py`'s
     established method).
   - If there is no precedent (a genuinely new capability *class*, like real auth or PDF generation):
     prove it the way every brand-new app is proven — real `build.py` assembly, a real Playwright
     browser journey, and real HTTP functional tests — since there is no "original" to regression-test
     against.
4. **Rerun the whole suite, not just the new part.** `run_full_verification.py` (all sections) must
   stay fully green, and `full_library_stress_test.py` must still report 0 collisions and 0 shadowed
   capabilities with the new capability merged in.
5. **Some gaps are legitimately out of scope, and that's a valid outcome, not a failure.** The
   original 43-app round already established this precedent for payment settlement, live video
   transport, and real email delivery: implement the real, honest local logic, state plainly in-app
   and in the report that a genuine third-party integration was not faked. The same standard applies
   here — if a test reveals a gap that would require, say, a real external payment processor or a
   genuine multi-tenant auth system with real password storage, the right outcome may be "built the
   real local logic, documented the deliberate boundary," not "faked a fuller answer."
6. **Document every outcome honestly**, including where a capability was judged out of scope, in a
   dated report following this session's own convention — nothing gets edited out for being
   inconvenient.

## The 14 tests

Each test lists: the request, what it's meant to discover, which existing capabilities are expected
to apply, what "success" means, what happens if something's missing, and — for tests likely to expose
a real gap — how that specific kind of gap would be closed under the governance standard above.

---

### Category 1 — Simple personal apps

#### Test 1.1 — Budget Envelope Tracker
- **Request**: "I want to split my paycheck into named envelopes (Rent, Groceries, Fun) and spend
  from them. Don't let me overspend an envelope."
- **Discovery intent**: every existing "bounded" engine (`add_bounded_counter_capability`) only ever
  *increments toward* a limit and rejects at/over it. Spending an envelope is the mirror image:
  *decrement toward zero*, reject *below* it. Tests whether that mirror shape already exists or is a
  real gap.
- **Expected existing capabilities**: plain CRUD (`add_capability`) for creating envelopes and
  setting a starting balance.
- **Success means**: create envelope, spend within balance succeeds and decrements it, spend beyond
  balance is rejected with a clear error, real Playwright journey completes.
- **If missing**: no engine decrements-with-a-floor today; expect this to surface as a real gap.
- **How it would be built**: a new `add_bounded_decrement_capability` (or a `direction` parameter on
  the existing bounded-counter engine, whichever keeps the choke point singular) — reject when
  `current - amount < floor` instead of `current >= limit`. No existing hand-written precedent to
  regression-test against, so proven via real build + browser journey + functional test instead, per
  governance step 3's second path.

#### Test 1.2 — Reading Progress Tracker
- **Request**: "Track books I'm reading, log pages read, and mark a book finished."
- **Discovery intent**: a positive-composability check — does "log an incremental number" plus "flip
  a status" compose cleanly from what already exists with zero new engines?
- **Expected existing capabilities**: `add_capability` (create book), `add_unbounded_counter_
  capability` (pages read — no upper bound, matches its real shape), `add_status_transition_
  capability` (reading → finished).
- **Success means**: fully composed, zero new engines, READY on first real build/browser-test pass.
- **If missing**: nothing expected to be missing; a failure here would itself be a notable finding
  (a regression in engines proven fine last round).
- **How it would be built**: n/a if it composes cleanly, which is the expected and desired outcome.

---

### Category 2 — Business applications

#### Test 2.1 — Cash Register / Till Reconciliation
- **Request**: "Ring up sales through the day, then close the till and show today's total."
- **Discovery intent**: every "total" in the library today (`accounting_ledger`'s Ledger Balance,
  `payroll`'s net pay) is a one-off hand-written sum, never generalized. Tests whether a *second*,
  independent app needing "sum a numeric field across records" reveals this as a real, recurring gap
  worth generalizing (matching how the like/status shapes were found: only worth generalizing once
  real repetition shows up).
- **Expected existing capabilities**: `add_capability` for ringing up a sale (create a record with an
  amount).
- **Success means**: sales recorded individually; a close-till action reports a real, correct sum.
- **If missing**: a generic "sum a field across records matching a filter" capability does not exist;
  expect this test plus `accounting_ledger`'s existing precedent to justify generalizing it (2
  real-world precedents, the same bar the like/status engines cleared).
- **How it would be built**: `add_aggregate_capability(id_field=None, group_by=None, sum_field=...)`
  — proven against `accounting_ledger`'s real "Ledger Balance" by regression test, then used fresh
  here.

#### Test 2.2 — Lead Scoring With Hot-Lead Alerts
- **Request**: "Score each lead 0–100. When a lead crosses 80, alert the sales team."
- **Discovery intent**: a positive-composability check combining a threshold rule with notification —
  proves `add_exceeds_threshold_capability` (built for auction bids) and `add_notification_
  capabilities` genuinely generalize to an unrelated business domain when combined, not just
  individually.
- **Expected existing capabilities**: `add_capability` (create lead), `add_exceeds_threshold_
  capability` (score update, "exceeds" reframed as "score above 80" — needs checking whether the
  engine's exact shape, "new value must exceed old value," fits "any update landing above a fixed
  threshold," or whether that's a subtly different shape worth noting even if not blocking).
  `add_notification_capabilities` for the alert.
- **Success means**: composes from existing engines (possibly with the threshold shape used in a
  slightly novel way, worth documenting either way); real journey completes.
- **If missing**: if the threshold engine's shape doesn't actually fit ("exceeds the previous value"
  is not the same claim as "exceeds a fixed constant"), that mismatch is itself a finding — possibly
  needing a small, honestly-scoped variant rather than a whole new engine.
- **How it would be built**: if needed, a `fixed_threshold` mode/parameter on the existing engine
  (still one choke point), proven against a constructed scenario since there's no existing "score
  crosses a fixed threshold" precedent to regression-test against.

---

### Category 3 — Workflow-heavy applications

#### Test 3.1 — Purchase Order Approval Workflow
- **Request**: "A purchase order moves draft → submitted → approved or rejected → paid. Don't let it
  skip steps or go backwards."
- **Discovery intent**: `add_status_transition_capability` accepts *any* string, unconditionally —
  faithful to its five real precedents, none of which validate transitions. This is the most likely
  test in the whole plan to expose a real, meaningful gap: a genuine state machine with legality
  rules.
- **Expected existing capabilities**: `add_capability` (create PO), `add_status_transition_
  capability` for the naive version (expected to fail the "don't skip steps" requirement).
- **Success means**: an illegal transition (draft → paid directly) is rejected with a clear error; a
  legal one succeeds.
- **If missing** (expected): the existing engine will happily accept the illegal jump — a real,
  demonstrable failure, not a hypothetical one.
- **How it would be built**: a new `add_validated_status_transition_capability` (or an
  `allowed_transitions` parameter on the existing engine) taking an explicit `{from: [to, to]}` map
  and rejecting anything not listed. No real precedent exists anywhere in the library for validated
  transitions, so proven via real build + browser journey + functional test (including a real,
  asserted-rejected illegal transition) rather than regression comparison.

#### Test 3.2 — Sequential Onboarding Checklist
- **Request**: "New hires complete steps in order: paperwork, training, equipment, account setup.
  Show progress and don't let them skip ahead."
- **Discovery intent**: a second, independent test of ordered/sequential constraints (distinct from
  3.1's finite state machine — this is "N steps in a fixed line," not "a graph of legal transitions").
  Tests whether one new engine covers both shapes or whether ordered-sequence is genuinely different.
- **Expected existing capabilities**: `add_capability` (create checklist items), possibly the new
  engine from 3.1 if its shape turns out to generalize to "next allowed step is checklist[i+1]."
- **Success means**: completing steps out of order is rejected; in-order completion succeeds and
  reports real progress.
- **If missing**: if 3.1's engine doesn't cleanly cover this (ordered sequence vs. arbitrary legal
  graph are different data shapes — a linear list of steps vs. a transition map), document that
  distinction rather than force-fitting one engine to both.
- **How it would be built**: reuse 3.1's engine if it fits; otherwise a distinct, evidence-justified
  `add_sequential_checklist_capability`, proven the same way (no precedent → real build + browser +
  functional proof).

---

### Category 4 — Document and PDF applications

#### Test 4.1 — Contract Generator
- **Request**: "Fill in a contract template with a client's name and terms, and give me a PDF."
- **Discovery intent**: the most likely test in the plan to hit a hard architectural boundary. No
  capability anywhere generates a binary document of any kind. Tests whether this is (a) a real,
  buildable gap (a template-fill + PDF-render capability, needing a real PDF-generation dependency —
  note `bootstrap.py`/`requirements.txt` would need a new vendored dependency, the same rigor already
  applied to Flask/Playwright), or (b) a case for the "explicitly out of scope, documented plainly"
  outcome the governance standard allows.
- **Expected existing capabilities**: `add_capability` for storing the contract's field values (title,
  client, terms) — the data side is ordinary CRUD; the gap is specifically the rendering side.
- **Success means**: EITHER a real PDF is generated and downloadable (a new, real, working capability,
  fully vendored offline per this project's own dependency-vendoring standard), OR a clear, honest
  decision that PDF rendering is out of scope for this round, with the real local data-modeling half
  still implemented and the boundary stated plainly in the app and the report — never a faked
  "PDF-shaped" response that isn't a real file.
- **How it would be built (if in scope)**: a new capability class (not just a generic engine — this
  needs a real PDF library, e.g., vendored the same way Flask/Playwright were: exact pinned version,
  wheel vendored into `verification/vendor/wheels/`, `requirements.txt`/`bootstrap.py` updated, full
  offline-install proof rerun). Proven via real build + browser journey (download link resolves to
  a real binary with a valid PDF header) since there's no existing precedent to regression-test.

#### Test 4.2 — Document Sign-off Tracker
- **Request**: "Track who has signed off on a document and when, and show who's still pending."
- **Discovery intent**: tests whether *tracking* signatures (metadata only, no actual document
  rendering or cryptographic signing) is already fully composable — a deliberately lower bar than
  4.1, to separate "can't track sign-off state" from "can't generate documents," since those are two
  different claims easy to conflate.
- **Expected existing capabilities**: `add_capability` (create document + list of required
  signatories), `add_status_transition_capability` or a small one-off (mark one signatory's line as
  signed), `add_notification_capabilities` (notify remaining signatories).
- **Success means**: composes fully from existing capabilities; no PDF or real cryptographic
  signature is claimed or needed for this narrower, metadata-only request.
- **If missing**: not expected; a real finding here would be surprising given how close this is to
  already-proven shapes (crm's stage, notifications).

---

### Category 5 — Multi-user applications

#### Test 5.1 — Shared Shopping List With Roles
- **Request**: "My household shares a shopping list. Anyone can add items, but only the list owner
  can delete the whole list."
- **Discovery intent**: this is expected to be the plan's clearest hit on the confirmed-absent real
  auth/identity gap. `_make_ctx()` always returns `{"user": None, "authenticated": False}` — there is
  no real login, session, or per-user identity anywhere in the library, so "only the owner can delete"
  cannot be honestly enforced today; any capability claiming to check it would be checking a client-
  supplied string, not a real identity.
- **Expected existing capabilities**: `add_capability` for the list/items themselves; the *access
  control* half has nothing to draw on.
- **Success means**: EITHER a real identity/session mechanism exists and the owner-only rule is
  genuinely enforced server-side against it, OR the honest documented outcome: items/list CRUD works,
  but "only the owner can delete" is explicitly flagged as unenforceable without real auth, and not
  faked via a client-supplied "am I the owner?" flag the server just trusts.
- **How it would be built (if pursued)**: this is a foundational addition, not a small generic
  engine — a real, minimal identity/session primitive in `CAP-0000` (e.g., a real login capability,
  a real session token, `_make_ctx()` actually populated from it instead of hardcoded) that every
  future permission check could build on. Given the size, this would warrant its own dedicated round
  with its own plan, not a single test's worth of code — this test's job is to establish definitively
  whether the gap is real (expected: yes) and how large it is, not to close it inline.

#### Test 5.2 — Team Task Board With Real @Mentions
- **Request**: "Assign tasks to specific teammates and notify them when they're mentioned."
- **Discovery intent**: a second angle on the same gap — `add_notification_capabilities`'s
  `recipient` field is already a free-text string with no real identity behind it (confirmed in the
  reference table above), so "notify the right teammate" today means "trust whatever string the
  client sends," not a real, verified user. Tests whether this matters in practice for a concrete
  request, distinct from 5.1's ownership/permission angle.
- **Expected existing capabilities**: `add_capability` (tasks), `add_notification_capabilities`
  (mentions).
- **Success means**: task assignment and notification-on-mention work exactly as well as they did in
  every existing app (which is to say: real record-keeping, but "recipient" is still a trusted
  free-text string, not a verified identity) — success here means clearly *documenting* that
  distinction, not silently letting a demo "look multi-user" while quietly not being one.
- **If missing**: same foundational gap as 5.1; not re-solved here, just re-confirmed from a second
  angle to make sure 5.1's finding wasn't domain-specific.

---

### Category 6 — Apps requiring several existing capabilities together

#### Test 6.1 — Multi-Track Conference Platform
- **Request**: "Sessions across multiple tracks, limited seats per session, a networking chat, and
  reminders before each session starts."
- **Discovery intent**: a deliberate "kitchen sink" — combine calendar-event, bounded-counter,
  notification, and verbatim reuse all in one app, more of them at once than any single app has used
  before (`community_event_board`/`course_enrollment_hub` each combine three; this combines four),
  to pressure-test whether heavy composition itself introduces problems the individual-engine proofs
  wouldn't catch (e.g., two engines sharing a data file in ways not yet exercised, or the namespace
  fix under a busier route table).
- **Expected existing capabilities**: `add_calendar_event_capabilities` (sessions), `add_bounded_
  counter_capability` (seats per session), `add_notification_capabilities` (reminders),
  `reuse_capability_verbatim` (chat, reused from `team_chat` — a third independent reuse).
- **Success means**: fully composes with zero new engines; real build + browser journey passes;
  `full_library_stress_test.py` still reports 0 collisions with this app's larger route table merged
  in.
- **If missing**: not expected to need anything new; a failure here would indicate a real regression
  or an interaction bug between engines, not a missing capability class — worth root-causing
  precisely if it happens, the same way `volunteer_shift_signup`'s route-mismatch bug was root-caused
  last round rather than papered over.

---

### Category 7 — Apps likely to expose missing capabilities

#### Test 7.1 — Time-Boxed Auction With Auto-Close
- **Request**: "Bidding opens now and closes automatically at a set time — no more bids accepted
  after that, even if nobody visits the site to close it."
- **Discovery intent**: every capability in the library only changes state in response to an incoming
  HTTP request (confirmed absent: no scheduling/background/time-driven mechanism at all). "Auto-close
  with nobody watching" cannot be done by a request-triggered capability alone — it needs something
  to run without a request, which nothing in this Flask-per-app, no-scheduler architecture currently
  provides.
- **Expected existing capabilities**: `add_exceeds_threshold_capability` (the bid-must-exceed-current
  rule, already proven) for the bidding half; the auto-close half has no analog.
  **Success means**: EITHER a real scheduling primitive is added (e.g., a lazy-evaluation pattern —
  compute "is this closed?" from `now() > deadline` on every read/write instead of a true background
  timer, which is a legitimate, real, honestly-scoped way to satisfy the request without adding actual
  cron infrastructure) and proven to actually reject a late bid, OR the gap is documented plainly: a
  literal background timer independent of any request is out of scope for this architecture, and the
  lazy-evaluation alternative is offered and clearly labeled as such rather than silently presented as
  identical to "real-time auto-close."
- **How it would be built**: a `deadline`-aware wrapper — any write capability checks
  `datetime.now() > deadline` and rejects if past it, same pattern as the calendar engine's real
  ISO-8601 validation. Proven via real build + functional test asserting a bid after a past deadline
  is genuinely rejected. If a true "closes itself with zero requests" behavior is specifically
  required, that is the out-of-scope case to document, not fake.

#### Test 7.2 — Profile Picture Upload
- **Request**: "Let a user upload a real photo as their profile picture and see it rendered on the
  page."
- **Discovery intent**: `file_storage_and_sync`'s "Upload File" stores a `content` string field inside
  the ordinary JSON array (confirmed above) — technically capable of holding base64 data, but with no
  real streaming upload, no content-type-aware serving route, and no engine anyone else has reused.
  Tests whether that's actually sufficient for a real image-display use case, or whether it's a gap
  that only looks closed until someone tries to use it for something real.
- **Expected existing capabilities**: `reuse_capability_verbatim` (file_storage_and_sync's Upload
  File, if it turns out sufficient).
- **Success means**: a real photo, uploaded through the real UI, is genuinely re-rendered as an
  `<img>` on the page from what the server actually stored (not a placeholder or a filename-only
  stub).
- **If missing**: if base64-in-JSON turns out too impractical for a real image (payload size against
  the whole array being read/written on every request, no proper `Content-Type` on retrieval), that's
  a real, demonstrable gap distinct from 4.1's document-generation gap — a genuine binary-storage
  primitive, not just a bigger string field.
- **How it would be built**: a real `add_blob_storage_capability` — a dedicated storage path outside
  the JSON array (e.g., `data/blobs/<id>`), a real content-type-aware serving route, proven via real
  build + browser journey (an uploaded image genuinely renders).

---

### Category 8 — Unusual or creative applications

#### Test 8.1 — Branching "Choose Your Own Adventure" Story Builder
- **Request**: "Write story pages, each with 2–3 choices that link to other pages. Let a reader play
  through and reach different endings."
- **Discovery intent**: `add_symmetric_relationship_capability` models exactly one shape — two-party
  mutual state (A likes B, does B like A back?). Nothing in the library models a directed graph where
  one record points to several others (a page's choices point to other pages, not a symmetric pair).
  Tests whether flat CRUD alone can fake this well enough, or whether real graph/reference modeling is
  a genuine, distinct gap.
- **Expected existing capabilities**: `add_capability` for pages (a page record with a list of
  `{choice_text, target_page_id}` — this may already be sufficient, since it's just a field holding a
  list of ids, not a new engine, if no capability needs to *traverse* or *validate* the graph itself).
- **Success means**: pages composable purely from plain CRUD (likely outcome — storing references
  is not the same problem as the library lacking relationship modeling, since a "target_page_id" field
  is just data, not a new capability shape) — a reader can navigate from page to page in the real UI.
- **If missing**: if the app needs the *builder itself* to validate a choice's target actually exists
  (referential integrity) or to detect an unreachable/orphaned page, that specific validation shape
  has no existing precedent and would be the real, narrower finding — not "the whole graph concept is
  missing."
- **How it would be built (if the narrower gap is real)**: a small, targeted validation addition (does
  `target_page_id` exist in the same collection?) — proven via real build + functional test asserting
  a bad reference is rejected.

#### Test 8.2 — Habit Streak Tracker With a Computed Streak Length
- **Request**: "Check in every day I do the habit. Show my CURRENT STREAK — not just a count of
  check-ins, the number of consecutive days including today."
- **Discovery intent**: every counter in the library (bounded or unbounded) stores and returns a raw,
  directly-incremented number. A "current streak" is *computed* from a history of dated records (does
  yesterday's check-in exist? the day before?) — a fundamentally different shape: derive a value from
  a collection at read time, not store-and-increment. Tests whether this "computed/derived report"
  class, like Test 2.1's aggregation gap, is genuinely absent.
- **Expected existing capabilities**: `add_capability` (check-in creates a dated record); nothing
  computes a derived value from a record history.
- **Success means**: the reported streak is genuinely computed from real check-in dates (breaks
  correctly if a day is missed), not a raw incrementing counter mislabeled as a streak.
- **If missing** (expected, and related to Test 2.1's aggregation gap): both point at the same
  underlying absence — no capability class computes a value FROM a collection rather than storing one
  directly.
- **How it would be built**: if Test 2.1 already justified a general `add_aggregate_capability`,
  check first whether a "consecutive-run-ending-today" computation is a mode of that same engine or
  is genuinely a different shape (sum vs. streak are both "derive from history" but not the same
  algorithm) — build only what's evidence-justified, not a maximal do-everything engine assembled from
  two data points.

---

## What happens after this plan

Running these 14 tests, honestly, means some are expected to pass cleanly (1.2, 2.2 probably, 6.1),
some are expected to find small, real, closeable gaps (1.1, 2.1, 3.1/3.2, 7.2, 8.1's narrower case),
and at least two (5.1, 5.2) are expected to surface one real, foundational absence — real
identity/auth — that this plan deliberately does not try to close inline, because a real auth
primitive is large enough to deserve its own dedicated round, plan, and governance pass rather than
being squeezed into one test's fix. Test 4.1 (PDF) and 7.1 (true scheduling) may land on either side
of "build it for real" vs. "document as out of scope" depending on what's actually found — that
determination is deferred to execution, not decided in advance here, per the instruction not to
assume the library's shape before testing it.
