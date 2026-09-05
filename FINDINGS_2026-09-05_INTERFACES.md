# Findings — the five families built end to end, 15 working interfaces (2026-09-05)

Everything below was produced by running code, not by reading it.
Whole repo: **217 tests passing** (was 209, 3 of them failing at the start).
Interfaces: **1244 browser checks, 0 failed, 0 browser errors** across 18 runs.
Shelf: **14 parts PRODUCT_QUALIFIED** by real browser receipts (was 4).

## The ask, and what it really needed

"Three interfaces for each of the five categories that actually work, plug and
play, each button functional." Every button working means a backend for every
button. At the start, the five families **bound** cleanly but **could not be
built**: the Builder refused all five, because their reports carried no
executable ReportSpec, their custom actions (Duplicate, Reassign, Send) had no
executable effect, the customer questions (name, brand…) were unanswered, and
the Builder had no rule at all for the parts four of them are bound to
(stage_history, stock_ledger, record_cloning, ledger_balancing,
document_generation). Command Desk was the only template carrying all of that.
So the work was: finish the pipeline for the five, then the 15 interfaces on
top, then drive every button in a real browser.

## 1. The templates are generated — the earlier JSON edits were not real

`build_templates.py` writes `templates/*.json`; the previous session's fixes
(ERP cancel off, booking's payment transition removed, accounting's two
reports removed) were made in the generated JSON, so `build_templates.py`
overwrote them and the byte-reproducibility test failed. All of it is now in
the source, plus what the five needed to build:

- `report_specs` for every report metric, in the reporting engine's own shape
  or naming the specialist part (`stage_history` rates and sales-by-month,
  `stock_ledger` reorder count) — validated by `check_template.py` against
  each report's own RP.04 metrics (a metric with no executable spec fails the check).
- `execution` on every custom action: Duplicate → `clone` (record_cloning),
  Reassign → `set_fields_from_input` (the new Owner is supplied at press time),
  Send → `generate_document` (document rendered, `Sent at` stamped, PDF served;
  email **not** dispatched — no outbound-mail part is on the shelf, and the
  action says so rather than claiming it sent).
- `transition_effects` (ERP: stock applied on Received / Shipped) and
  `create_effects` (accounting: a Payment settles the Invoice/Bill it names and
  fires the declared automatic edge) — the executable form of FL.08 / FL.03 prose.
- **Product decisions made to match Command Desk's working pattern, all in
  the template source and visible:** no cancel actions (booking, ERP);
  booking's Booked → Confirmed is a staff-moved transition (the source app also
  confirmed on a deposit payment; live payment processing is not on the shelf);
  booking's form drops the deposit-payment step for the same reason;
  accounting's "Profit and loss" and "Aged receivables" are out (cross-table
  joins, arithmetic between metrics, age bucketing — outside every reporting
  part on the shelf, as the reporting engine's own scope note says); Invoice
  gained a `Sent at` field because Send "stamps the sent time" and had nowhere to.

## 2. Builder rules that did not exist

`packages/builder/builder.py` now generates: stage history on every create and
every move (so rates and by-month reports have data); declared transition
effects and create effects; custom-action ops `clone`, `generate_document`,
`set_fields_from_input`; report metrics run by the part their spec names;
`GET /api/approvals/<table>/<id>` (the decision a row carries — a screen can say
"waiting for Operations" truthfully) and `GET /api/history/<table>/<id>` (the
trail; the earlier FINDINGS gap "audit_trail has no route or screen"); served
`/documents/*.pdf`; and detail screens that show the stage and offer every
declared control, labelled with the role that presses it (the earlier FINDINGS'
"the generated screens carry no lifecycle stage and no action controls").

Two bugs found by running, not reading:
- **The Builder resolved a record's workflow by name** (`<record> lifecycle`);
  crm-pipeline's is "Deal pipeline", so every Deal move route was missing.
  Now resolved by declared stages, the same rule `check_template.py` uses.
- **`assemble()` handed the locked structure through verbatim**, so the
  customer's app name and brand (answered after locking, by design) never
  reached the build — every app was called "App". Overlaid now; they mint no ids.

Engines extended (each bumped to 1.1.0 on the shelf, proven in its own
`prove()`): stage_history (`rate_over_last_days`, `line_value_by_month`),
stock_ledger (`apply_order_lines`, `count_at_or_below_reorder`),
ledger_balancing (`line_total`, `settles`), custom_action_execution
(`set_fields_from_input`). `crud_list_detail` was bumped to 1.1.0 because its
source moved — the lifecycle caught the drift, as designed — and re-qualified.

## 3. The 15 interfaces

`packages/interfaces/` — see its README. One generator, three designs that are
different products (Console / Board / Pocket), one runtime, every control on a
`data-act` dispatcher, an in-browser demo store for when the file is opened
with no server. Every button appears only when the current role really may
press it; every press goes to the real route.

Defects the browser run found in the interfaces, all fixed then re-run:
- Board's modal used `stopPropagation`, which silenced every button inside it.
- Titles that are a link (Invoice by Contact, PO by Supplier) showed raw UUIDs.
- Percentages rendered `0%` for the API's `0.0`; one decimal everywhere now.
- "Activitys": labels now pluralise properly (table names keep the Builder's rule).
- The history route only existed for records with a lifecycle → 404 opening a Project.
- The generated detail screen's result text was hidden by its own reload.

## 4. The driver caught itself, three times

Reading the green log showed the accounting run had declined at the gate and
then taken Draft → Voided, so approve → Awaiting payment → Paid was never driven
through the UI; and the coverage sweep let `approve:APPROVED` pass on
`approve:DECLINED`'s prefix. Both tightened; the accounting journey now
part-pays and settles an Invoice and a Bill to Paid from the target's own page.
The stock check compared per line instead of per product (two lines on one
product) — the product was right, the driver was wrong.

## 5. Surfaced, not guessed

- **A Payment can name both an Invoice and a Bill.** The template declares both
  links optional and nothing says "exactly one"; the API and the UI accept it.
  Whether a payment applies to one target only is a product decision — needs
  an answer in the template (a rule on R.02:Payment), not a guess in the code.
- **Reference customer answers** (`packages/interfaces/build_families.py`):
  the app names Teamwork / Pipeline / Front Desk / Backbone / Ledger, tones,
  region. Labelled as reference answers; change them and rebuild.
- **Still TESTED, and why:** `notification_delivery` and `scheduled_jobs` are
  used by every family but no route or screen exposes a notification or a
  scheduled run, so no journey can drive them; `audit_trail` is read by the new
  history route but the generated screens do not show it (the interfaces do);
  `email_parsing` is bound to Send but nothing parses mail. The Definition of
  Done stays NOT DONE for the five until those have a seam a person can press.
- Command Desk's own two seam FAILs (the upload form, "Open source document")
  are its own recorded product defects; nothing of Command Desk was changed.

## Next failure points

1. Notifications and scheduled jobs have no user-facing seam — the next parts
   to qualify need a route (`/api/notifications`, `/api/jobs/run`) and a screen.
2. The generated apps have no sign-in: the role is chosen on the screen and
   sent with the request; the routes enforce the declared roles, but nothing
   proves who the person is. Auth (AU.*) is answered in every template and built
   by nothing.
3. Generated list screens have no create form; every creation on the Builder's
   own screens is over the API. The interfaces create; the seams write rows over
   the API and say so in every report.
