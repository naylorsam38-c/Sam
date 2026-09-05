# Where this is, exactly — and where it goes next

Written 2026-09-05, measured against `commanddeskshelflifecycle.zip` (the
reference run) and its own HANDOFF.md, which is the standard.

---

## 0. The standard

From the reference zip's own `HANDOFF.md`, in its words:

> Builder builds a numbered item, tester proves it live on the real box against
> the acceptance criteria in the spec, fails go back to builder, and the loop
> does not stop for any reason other than every item passing. **No mocks, no
> simulations, no synthetic data. A test that never touched the real running
> system is not a test.**
>
> **Done means** every screen, action, notification, report and agent in the
> answers file exists, works end to end, and the tester has passed it.
>
> Do not report progress. Report done, or report the exact item that is stuck
> and why.

Everything below obeys the last line. Nothing here is "in progress" — each item
is either done and proven, or named as stuck with the reason.

---

## 1. The starting line — what was in the reference zip

217 files. Ten packages. **No user interface of any kind**, which is the gap you
named.

| | Reference zip |
|---|---|
| Parts on the shelf | 33 |
| PRODUCT_QUALIFIED | **4** — `crud_list_detail`, `reporting_engine`, `oauth_connect`, `api_key_connect` |
| Templates that could be **built** | **1** (command-desk) |
| Templates that merely **bound** | 6 |
| Tests | 209 in 11 files |
| Interfaces | none |
| Front door | none |

The five families bound cleanly but **the Builder refused all five**. Verified,
not assumed — the templates carried no executable report specs, no executable
custom actions, and the Builder had no generation rule for four of the parts
they were bound to. Binding proved a part *had been chosen*; it never proved the
Builder could *make* it. Only command-desk carried the executable half.

---

## 2. What exists now

227 tests + 1 skipped, passing, 5m41s. Twelve packages.

### 2.1 The chain (unchanged in shape, extended in capability)

```
requirements-engine  → 122-question graph, 6 templates, lock, bind
assembly-engine      → completed answers → one numbered spec
builder              → numbered spec → a real stdlib app + the parts shelf
playwright-tester    → live tester + seam journeys (the only thing that qualifies a part)
loop                 → fix-and-retest + Definition of Done
specgate / spec-writer / crawler / defect-report / hands   (unchanged)
interfaces           ← NEW
frontdoor            ← NEW
```

### 2.2 All five families now build

Every one assembles, builds, runs and is driven. Verified end to end.

| Family | Records | Screens | Actions | Binding |
|---|---|---|---|---|
| pm-teamwork (Teamwork) | 3 | 8 | 14 | 36/36 CLEAN |
| crm-pipeline (Pipeline) | 4 | 10 | 21 | 44/44 CLEAN |
| booking-frontdesk (Front Desk) | 3 | 9 | 15 | 40/40 CLEAN |
| erp-backbone (Backbone) | 8 | 19 | 31 | 70/70 CLEAN |
| accounting-ledger (Ledger) | 5 | 10 | 23 | 46/46 CLEAN |
| command-desk (untouched) | 7 | 23 | 47 | 99/99 CLEAN |

**What had to be built to make that true** — all in template *source*, so it
regenerates:

- executable report specs for every metric (generic engine, or naming the
  specialist part: `stage_history` rates and sales-by-month, `stock_ledger`
  reorder count)
- executable effects on every custom action: `clone` (Duplicate),
  `set_fields_from_input` (Reassign — value supplied at press time),
  `generate_document` (Send)
- `transition_effects` — ERP stock applied on Received / Shipped
- `create_effects` — a Payment settles its Invoice/Bill and fires the declared
  automatic edge
- Builder rules that did not exist: stage history on every create and move,
  transition/create effects, three custom-action ops, report metrics run by the
  part their spec names, `GET /api/approvals/…`, `GET /api/history/…`, served
  PDFs, and detail screens that show the stage and offer every declared control

**Two real bugs found by running, not reading:**
1. The Builder resolved a record's workflow **by name** (`<record> lifecycle`).
   crm-pipeline's is "Deal pipeline" — so every Deal move route was missing.
   Now resolved by declared stages.
2. `assemble()` passed the locked structure through verbatim, so the customer's
   app name and brand (answered *after* locking, by design) never reached the
   build. Every app was called "App".

### 2.3 Fifteen interfaces — `packages/interfaces/`

Three genuinely different products per family, on the same routes:

- **Console** — sidebar, data tables, slide-over detail. Desk work.
- **Board** — a kanban column per stage, move chips on cards, modal detail.
- **Pocket** — phone-first, bottom tabs, 44px+ targets, full-screen pages.

Each does: role switch, create/edit/delete where allowed, stage moves that only
appear for declared movers, approve/decline at gates, the declared custom
actions, related records from the parent's page, public forms, reports,
activity trail. Opened as a plain file with no server, an in-browser demo store
follows **the same declared rules** and says so in a banner.

**Proof: 1244 checks, 0 failed, 0 browser errors, across 18 runs** (15 served +
3 opened as files). Every control pressed in real Chromium; every outcome
re-read from the app's own data, never from what the screen claims.

### 2.4 The front door — `packages/frontdoor/`

Eight questions (seven when one piece is picked). One typed, one named, six
tapped. Verified: **14/14 in real Chromium**, plus 10 unit tests.

The mechanism that makes it safe: `catalogue.py` **refuses to load** if a card
names a record, workflow, report, form or notification the real templates do
not declare. A model helping someone may only ever offer a card from it. It
cannot promise something the builder could not make.

It also says no properly — nine things it cannot build (chat, matching, card
payments, sign-in, video, maps, App Store, sending email, going live), each with
why and **what is offered instead**, shown at the moment of choosing.

### 2.5 The shelf: 4 → 14 qualified

Every one earned by a browser receipt, not a claim.

**PRODUCT_QUALIFIED (14):** `crud_list_detail` · `reporting_engine` ·
`oauth_connect` · `api_key_connect` · `workflow_executor` ·
`system_triggered_transition` · `stage_approval_gate` ·
`custom_action_execution` · `form_render_submit` · `stage_history` ·
`stock_ledger` · `ledger_balancing` · `record_cloning` · `document_generation`

Five new seam journeys were written to earn the last five: stock moving on the
screen, a payment settling its target on the screen, a clone appearing in the
list, a sent document stamped on the screen, a rate report reflecting moves made
on the screen.

---

## 3. How "no dead buttons" is actually enforced

Not by care. By four mechanisms that each **refuse**:

1. **The Builder refuses to build at all** if any numbered item has no real
   generation rule. It names every offending item by its permanent id. This is
   exactly why all five families were unbuildable at the start — the refusal
   was working.
2. **`registration_gaps`** blocks a numbered item whose *kind* is registered but
   which lacks what its rule needs (a report with no executable spec, a custom
   action with no executable effect). Recognising the name is not enough.
3. **The interfaces render a control only when the current role may really
   press it** — the same rule the route enforces. A button that would be refused
   is never drawn.
4. **The numbering makes "every one" checkable**: `SCR-nnn` screens, `ACT-nnn`
   actions, `RPT-nnn` reports, `OPS-nnn` recurring ops, `TRN-nnn` transitions,
   `STG-nnn` stages — permanent, template-prefixed, never renumbered. The driver
   sweeps every control kind ever rendered and **fails if one was never
   pressed**. That is the "number structured system" doing its job.

---

## 4. What is NOT done — the exact items, and why each is stuck

Ordered by how much they block handing this to a real customer.

### 4.1 Nobody can see a notification · **STUCK: needs a route and a screen**
`notification_delivery` is used by all five families and stays TESTED. Every
family declares real notifications (task due, low stock, payment reminder) and
the engine is proven in isolation — but **no route exposes them and no screen
shows them**, so no browser journey can drive one. A person using the app today
would never see a notification.
**Needs:** `GET /api/notifications` + a bell/inbox in the three interfaces + a
seam journey. Then the part qualifies.

### 4.2 Nothing runs on a schedule · **STUCK: needs a runner and a route**
`scheduled_jobs` is used by all five and stays TESTED. Every family declares
recurring ops (`OPS-001…`) — retention purges, reminders, timeouts. The engine
is proven, but nothing **runs** them in a generated app and no route triggers
one. The app does not act on its own today.
**Needs:** a tick loop in the generated `app.py` + `POST /api/jobs/run` + a
screen showing what ran. Then the part qualifies.

### 4.3 There is no sign-in · **STUCK: declared everywhere, built by nothing**
Every template answers the full `AU.*` block — invite modes, password rules,
lockout, session length, deletion. **None of it is built.** The app is told who
is acting; it enforces what that role may do, but nothing proves who the person
is. This is the single biggest gap between "works" and "you can give it to
someone".
**Needs:** a real decision from you first (see §6), then an auth part on the
shelf, generation rules, and journeys.

### 4.4 The Builder's own list screens have no create form
The generated `SCR-nnn` list screens show rows; **creating happens over the
API**. The three interfaces do have create forms and are fully driven, so this
is not user-facing today — but the Builder's own screens are weaker than the
interfaces on top of them, and the seam journeys have to write rows over the API
and say so in every report.

### 4.5 `audit_trail` stays TESTED
The history route exists and the interfaces show the trail. The Builder's own
generated screens do not, so the journey that would qualify it has nowhere to
look.
**Needs:** the trail on the generated detail screen. Small.

### 4.6 `email_parsing` stays TESTED
Bound to accounting's `Send`, but nothing in any family parses inbound mail.
Honest position: it is bound because Send's document half needs it; the parsing
half has no user-facing seam. Either give it one or unbind it.

### 4.7 Command Desk's own two defects — **left alone deliberately**
`SCR-017` (upload form: the browser cannot submit; the `File` object is
JSON-encoded and sqlite dies) and `ACT-024` ("Open source document": declares an
effect that changes nothing). Both are its own recorded product defects. **I
changed nothing of Command Desk**, per your instruction that it worked.

### 4.8 Twelve parts never exercised
`hands`/paperwork family: `trust_gate_approval`, `value_provenance`,
`document_field_detection`, `preserved_original_document_store`,
`paperwork_session_lifecycle`, `defined_workflow_containment`, plus
`search_fts`, `import_export`, `file_conversion`, `bank_feed_ofx`,
`calendar_ics`, `document_signing`, `pdf_form_filling`,
`scheduling_availability`, `stage_conditional_requiredness`. None are used by
the five families. Not defects — unused inventory. They qualify when a family
needs them.

### 4.9 A Payment can name both an Invoice and a Bill · **product decision, yours**
Both links are declared optional and nothing says "exactly one". The API and the
UI accept both. Whether that is legal is a real business rule I will not invent.

### 4.10 Deployment · **out of reach from here**
No route to a real box. The apps run locally and are proven locally.

### 4.11 Two front doors now exist
Another session built a different one (4 questions, single-select category,
layouts named Workbench/Cards/Focus, `FRONT_DOOR_SCRIPT.md`, commit `c2e7e10`).
Mine is 8 questions, multi-select, real screenshots, catches impossible asks,
handles merging two families, and is browser-proven 14/14. **They are not
merged and I have not read theirs.** A decision, not a defect.

---

## 5. Direction — the order I would go, and why

**Phase A — make the app act (closes §4.1, §4.2, §4.5; qualifies 3 parts)**
The app currently only does what someone clicks. Notifications go nowhere and
scheduled work never runs, in *every* family. This is the largest functional
hole and the cheapest to close, because both engines are already proven — they
need a route, a screen and a journey each. After this, 17 of 33 parts are
qualified and the phrase "it works" covers what the app does on its own.

**Phase B — sign-in (closes §4.3)**
The gate between "proven" and "give it to a customer". Needs your decision on
shape first. Everything is already declared; nothing is built.

**Phase C — the Builder's own screens catch up (closes §4.4)**
Create forms on generated list screens, so the Builder's output stands alone
without the interface layer on top, and journeys stop writing rows over the API.

**Phase D — one front door**
Read the other session's, take whichever parts are better, delete the loser.
Two front doors is worse than either.

**Phase E — widen the catalogue**
More capability cards means more apps the front door can offer. Every new card
is a new template or a documented subset — and the catalogue refuses to promise
what does not exist, so this stays honest as it grows.

---

## 6. What I need from you

These are decisions I will not make for you, because guessing them would be the
one thing this system exists to prevent.

1. **Sign-in shape.** Who logs in — your staff only, or customers too? Email +
   password, invite link, or Google? This changes what gets built, and it is
   answered in every template already but by *defaults*, not by you.
2. **Payment rule (§4.9).** May one payment settle both an invoice and a bill,
   or exactly one target?
3. **Which front door survives (§4.11).**
4. **Where this deploys**, when it is time — that unblocks §4.10 and turns
   "proven locally" into "running".
5. **Whether Phase A is the right first move.** I think it is, because today
   every one of the five apps is silent and inert when nobody is clicking. If
   something else matters more to you, say so and I will do that instead.

---

## 7. What is in the zip

```
STATUS_AND_DIRECTION.md          this document
FINDINGS_2026-09-05_INTERFACES.md   what changed and what running it found
START_HERE.md                    how to open the 15 interfaces in one minute
governance/                      the constitution the roles run under
packages/frontdoor/              the eight questions → a built app
  README.md · catalogue.py · intake.py · serve.py · web/ · prove_frontdoor.py
  evidence/FRONTDOOR.md          14/14, with screenshots of every step
packages/interfaces/             the 15 interfaces
  README.md · make_interfaces.py · build_families.py · src/ · out/
  evidence/INTERFACES.md         1244 checks, every step listed
  evidence/shots/                343 screenshots
  evidence/seams/                the qualification receipts, per family
packages/requirements-engine/    graph, 6 templates, lock, bind, build/
packages/assembly-engine/ builder/ playwright-tester/ loop/ + the rest
tests/                           227 tests, 15 files
```

Rebuild everything from source:

```bash
pip install pytest playwright && python -m playwright install chromium
cd packages/requirements-engine && python build_templates.py && python check_template.py --all && python bind_and_assemble.py
cd ../interfaces && python build_families.py && python make_interfaces.py
python drive_interfaces.py     # every control of all 15, real Chromium
python run_seams.py            # the shelf's journeys, writes receipts
cd ../frontdoor && python prove_frontdoor.py
cd ../.. && pytest             # 227
```
