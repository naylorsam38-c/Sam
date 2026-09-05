# Building spec: what's left, verified fresh against the merged repo

Written 2026-09-05, against commit `707915a` — the consolidated branch
(6 templates, `frontdoor`, `interfaces`, `hands`, `governance`). Every
line below was checked directly against this codebase just now, not
copied from an earlier report. Full suite passes: **227 tests + 1
skipped, 0 failed.**

## What's real and working (don't re-build this)

- All 6 templates build, run, and pass their checker CLEAN (0 FAIL each)
- `packages/frontdoor` — 8-question intake, real cross-template merging,
  refuses to promise what templates don't declare
- `packages/interfaces` — Console/Board/Pocket per family, 1244
  browser-verified checks, standalone demo-store mode
- `packages/hands` — paperwork engine, backend-enforced approval, 29/29
  tests
- 33 shelf parts, 14 `PRODUCT_QUALIFIED` by real browser receipt
- `reporting_engine` handles joins, computed values, ratio/difference/
  age-bucket composites

## Stuck items, each re-verified just now, most to least severe

**1. Nobody can see a notification.** Confirmed by grep: no
`/api/notifications` route in `builder.py`, no bell/inbox anywhere in
`packages/interfaces/src/` (checked `.py`, `.html`, `.js`). Every family
declares real notifications; `notification_delivery` is proven; nothing
surfaces one to a person using the app. Needs: `GET /api/notifications`
in `builder.py`'s route table, a bell/inbox view in each of the three
interface layouts, one seam journey proving a person sees a real one.

**2. Nothing runs on a schedule.** Confirmed: no `/api/jobs` or
`jobs/run` route. Every family declares `OPS-nnn` recurring work
(purges, reminders, timeouts); `scheduled_jobs` is proven; nothing
triggers it inside a generated app. The apps are inert until a person
clicks something. Needs: a tick loop in generated `app.py`, a
`POST /api/jobs/run` route (or an actual background thread), a screen
showing what ran, one seam journey.

**3. There is no sign-in.** Confirmed: zero session/login/cookie/
current-user code anywhere in `builder.py`. Every template answers the
full access-control question block; none of it is enforced at request
time — the app is simply told who's acting. **This needs your decision
before it's buildable**: staff-only or customers too; email+password,
invite link, or Google. Not a coding gap, a product one.

**4. Builder's own screens have no create form.** Confirmed:
`_render_list_screen`'s output contains no `<form`. The `interfaces`
layer has real forms and is fully driven, so this isn't user-facing
today — but the Builder's raw output is weaker than the layer sitting on
top of it, and any seam journey against the Builder's own screens (not
`interfaces`) has to write rows over the API instead of through a form.

**5. Audit trail has a route, no screen.** Confirmed: `GET
/api/history/<table>/` exists; no generated screen or interface view
reads it back. Small — a table plus a link.

**6. `email_parsing` is unused.** Bound to accounting-ledger's `Send`
action; nothing parses inbound mail. Either give it a real seam or
unbind it — leaving it bound-but-untested contradicts the shelf's own
qualification standard.

**7. Command Desk's own recorded defects — left alone deliberately,
still there.** `SCR-017` (upload form JSON-encodes a File object, sqlite
dies) and `ACT-024` (an action claims an effect it doesn't have).
Confirmed still referenced in the templates/qualification files. Command
Desk is explicitly the one template nobody is supposed to touch.

**8. 19 shelf parts are `TESTED` but never exercised by a real family.**
Confirmed by counting `parts_shelf.json` directly: 19 of 33. Unused
inventory, not a defect — `search_fts`, `import_export`,
`file_conversion`, `bank_feed_ofx`, `calendar_ics`, `document_signing`,
`pdf_form_filling`, `scheduling_availability`,
`stage_conditional_requiredness`, `email_parsing`, plus others. They
qualify the moment a template's own numbered item actually needs one.

**9. A Payment can name both an Invoice and a Bill.** Both links are
declared optional; nothing enforces "exactly one." Needs your decision:
allow both, or require exactly one.

**10. Deployment is out of reach.** Proven locally only; no route to a
real box, no real SMTP/payment credentials in this sandbox.

## Decisions only you can make

1. Sign-in shape — who, and how (email+password / invite / Google)
2. Payment rule — one payment can settle both an invoice and a bill, or exactly one
3. Where this deploys once sign-in exists
4. Priority order below, if not the one proposed

## Proposed order (cheapest, highest-impact first)

**Phase A — make the apps act on their own.** Closes items 1, 2, 5.
Both engines (`notification_delivery`, `scheduled_jobs`) are already
proven; they need a route, a screen, and a seam journey each — no new
engine logic. Qualifies 3 more parts. Today all six apps are silent
until someone clicks.

**Phase B — sign-in.** Closes item 3. Blocked on your decision above;
this is the line between "proven" and "something you can hand to
someone else."

**Phase C — Builder's own screens get a real create form.** Closes item
4. Makes the Builder's raw output stand on its own without the
`interfaces` layer on top.

**Phase D — resolve or unbind `email_parsing`; decide the Payment
rule.** Closes items 6 and 9. Cheap, mostly a decision plus a small fix.

**Phase E — widen the catalogue.** Give the 19 unused parts a real
template need, one at a time, each proven the same way as everything
else here — never speculatively.

Unless told otherwise, Phase A is the next concrete work: `GET
/api/notifications` + `POST /api/jobs/run` in `builder.py`, a bell/"what
ran on its own" view in the three interfaces, two seam journeys.
