# Building spec: what's left, verified fresh against the merged repo

Written 2026-09-05, against commit `707915a` — the consolidated branch
(6 templates, `frontdoor`, `interfaces`, `hands`, `governance`). Every
line below was checked directly against this codebase just now, not
copied from an earlier report. Full suite passes: **227 tests + 1
skipped, 0 failed.**

## Update — Phase A's engine half is done (commit `078bc68`)

A delta applied and independently verified: every generated app now has
real `notify()`/`run_job()` functions, `GET /api/notifications`, and
`POST /api/jobs/run`, wired into create/update/move/action handlers.
Verified myself, not taken on claim — built booking-frontdesk fresh,
created a real unpaid-deposit appointment and a paid control case,
backdated real stage-history rows past the declared 24h window, and hit
both routes over real HTTP: the unpaid appointment auto-cancelled and
delivered a real in-app notification; the paid one was untouched; a
second job run did not refire. Item 1 and 2 below are now **engine-done,
UI-open** rather than fully stuck — `notification_delivery` and
`scheduled_jobs` stay `TESTED` (not `PRODUCT_QUALIFIED`) until a bell/
inbox and a job-trigger screen exist and a real seam journey drives them.
Item 5 (audit trail) is unaffected by this delta and still fully open.

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

**1. Nobody can see a notification — engine now real, UI still open.**
`GET /api/notifications` exists and works (verified live). Still needed:
a bell/inbox view in each of the three interface layouts, one seam
journey proving a person sees a real one in a browser.

**2. Nothing runs on a schedule — engine now real, UI still open.**
`POST /api/jobs/run` exists and works (verified live: a real 24h
unpaid-deposit timeout auto-cancelled a real appointment and notified
the right people; a second run didn't refire). Still needed: something
to actually call this on a timer (today it's triggered manually, not by
a tick loop), a screen showing what ran, one seam journey.

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

**Phase A — make the apps act on their own.** Engine half done (commit
`078bc68`, verified live). What's left to fully close items 1, 2: a
bell/inbox screen in the three interfaces, an actual timer/tick loop
(today `/api/jobs/run` has to be called, it doesn't fire itself), and
one seam journey per part so `notification_delivery`/`scheduled_jobs`
move from `TESTED` to `PRODUCT_QUALIFIED`. Item 5 (audit trail) is
separate and still fully open.

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

Unless told otherwise, finishing Phase A's UI half is next: a bell/"what
ran on its own" view in the three interfaces, an actual timer to call
`/api/jobs/run` on its own, and two seam journeys.
