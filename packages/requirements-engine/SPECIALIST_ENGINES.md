# Specialist engines the ten parts do not cover

The ten parts (per `AUDIT_FINDINGS.md`, line 71): **Auth (AU), Forms (F), Records (R),
Permissions (P), Notify (N), Files (FI), Reports (RP), Flow (FL+FLX), Billing (B),
Client (C)**. Each of the five templates answers all ten parts. What follows is not
a re-listing of that — it is the real logic each source app runs that answering
those ten parts still leaves as English text, not something a generic
interpreter of the ten parts' own data can execute. Evidence is the template's
own real `per_instance` answer, quoted, not paraphrased or invented.

A person-triggered stage move with a declared list of permitted roles (e.g.
Task lifecycle's To do → In progress) is fully covered by Flow's own data — a
generic state-machine executor can run it from FL.02/FL.03 alone. What follows
is only the residue: places where FL.03's `event`, FL.08's `on_complete`,
FI/R.15's `effect`, or RP.05's metric `definition` is a sentence describing a
real computation, with no field anywhere in the ten parts that already holds
its result.

## pm-teamwork (Asana)

**Record Cloning Engine.** The `Duplicate` custom action's declared effect:
> "creates a copy of the task in stage 'To do' with '(copy)' appended to the
> title" (`R.15:Task`)

Copying a record's fields, resetting one field (its lifecycle stage) to a
fixed value, and mutating another (appending text to the title) is not a CRUD
verb Records (R) declares — R only grants who may create/view/edit/delete, it
does not describe a copy-with-transform operation.

## crm-pipeline (Pipedrive)

**Stage-Entry History Engine.** The `Win rate` metric's definition:
> "deals that entered Won divided by deals that entered Won or Lost, in the
> selected period, attributed to **the date the deal reached that stage**"
> (`RP.05:Win rate:win rate`)

No record field anywhere holds "the date this Deal entered its current
stage" — Records' own audit fields (`sys_audit_fields`) are `created_at`/
`updated_at` only. Computing this metric for real requires a transition
history log the ten parts never ask for.

**Stage-Conditional Field Requiredness Engine.** Deal pipeline's on_complete:
> "Won: the deal locks and counts toward revenue reporting. **Lost: Lost
> reason becomes required.**" (`FL.08:Deal pipeline`)

`R.02`'s `required` flag on the Lost reason field is fixed at authoring
time; it cannot become required only once a specific record reaches a
specific workflow stage. That is domain logic Records/Flow together do not
express.

## booking-frontdesk (Acuity Scheduling)

**Payment/Deposit Processing Engine.** The automatic transition:
> "Booked → Confirmed ... event: **the deposit payment succeeds**, or a
> staff member confirms manually" (`FL.03:Appointment lifecycle`)

Billing (B) declares that a deposit exists and its amount; it does not
process a charge or detect its success. Something has to actually run the
charge and observe the result — Billing's own data model stops at "what is
billed," not "how a specific charge attempt resolves."

**Scheduling/Availability Engine.** The 24-hour timeout's own text:
> "if the deposit is unpaid, the appointment moves to Cancelled **and the
> slot is released**" (`FL.10:Appointment lifecycle`)

"The slot" implies a real calendar/availability model (no two Appointments
for the same Staff member at an overlapping time) that no part of Records,
Client, or Flow declares — none of the ten parts have a concept of a
time-slot conflict at all.

**Timeout/Scheduled-Job Engine.** The same timeout entry requires something
that is not a person clicking a button or an event firing inside a request —
it requires a clock: wait 24 hours from Booked, then check a condition, then
transition. Flow (FL.10) declares that this rule exists; nothing in the ten
parts runs a clock.

## erp-backbone (Odoo core)

**Stock/Inventory Ledger Engine.** Both workflows' on_complete:
> "On Received, each line's Quantity is added to its Product's Stock on
> hand." (`FL.08:Purchase order lifecycle`)
> "On Shipped, each line's Quantity is subtracted from its Product's Stock
> on hand." (`FL.08:Sales order lifecycle`)

and the alert this feeds:
> "a Product's Stock on hand falls to or below its Reorder point"
> (`N.01:Low stock alert`)

Mutating one record's numeric field (Product.Stock on hand) as a side effect
of a *different* record (a Purchase/Sales order line) reaching a workflow
stage, then evaluating a live two-field comparison to decide whether to
notify, is arithmetic and condition-evaluation no part of Records, Flow, or
Notify performs by itself — each only declares that it should happen.

**Stage-Entry History Engine** (same engine class as CRM's). The `Sales by
month` metric:
> "sum of (Quantity x Unit price) over Sales order lines whose Sales order
> **reached Shipped in the month**" (`RP.05:Sales by month:sales value`)

Same gap as Pipedrive's win rate: "reached Shipped" needs a stage-entry
timestamp no record field holds.

## accounting-ledger (Xero core)

**Payment Application / Ledger Balancing Engine.** Both workflows' automatic
transitions:
> "Awaiting payment → Paid ... event: **Payments applied to the invoice
> reach its total**" (`FL.03:Invoice lifecycle`)
> "... Payments applied to the bill reach its total" (`FL.03:Bill lifecycle`)

Matching Payment records against an Invoice or Bill, summing what has been
applied, comparing to the total, and firing the transition when they meet is
the core of what makes this an accounting app — Records/Flow only declare
that the rule exists, not the running balance that decides when it is true.
(The two reports, Profit and loss and Aged receivables, both anchor on real
date fields — Issue date, Due date — and filter by workflow stage, which a
generic reporting engine over Records+Flow data can already do; they need
this engine's real Paid/balance state as an input, not a new engine of
their own.)

**Document Rendering + Email Delivery Engine.** The `Send` custom action:
> "emails the invoice document to the Contact and stamps the sent time"
> (`R.15:Invoice`)

Rendering a specific financial document from a record's data and delivering
it by email is real document-generation and delivery capability; Notify (N)
only fires templated, structured notifications from a fixed trigger/
recipient/channel shape — it is not a document renderer.

---

Nothing above is a request to build these — this is the list, stopped here,
as instructed.
