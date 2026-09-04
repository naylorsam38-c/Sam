# Parts shelf

A part is real, already-running code — never a description, a stub, or a
placeholder. `parts_shelf.json` is the machine-readable version this
directory's tooling reads; this is the human-readable index of the same 22
parts. Every numbered item across the five locked templates binds to one of
these by `part_id`, written directly into that item's own entry in its
assembled spec (`packages/requirements-engine/build/<template>/BOUND_SPEC.json`)
— never a separate document.

Two parts are generic, existing Builder rules (not new code, not
duplicated — referenced at their real location in `builder.py`):

| part_id | what it does | real location |
|---|---|---|
| `crud_list_detail` | Record CRUD: sqlite table, `/api/<record>s` routes, list+detail HTML pages | `builder.py::{build_schema,crud_routes,render_crud_handler,_render_list_screen,_render_detail_screen}` |
| `oauth_connect` | OAuth start/callback/status routes + integration-status page | `builder.py::{oauth_routes,render_oauth_handler,_render_integration_screen,_resolve_provider}` |

Three are the generic Builder runtime capabilities that used to be missing
entirely -- a workflow executor, a reporting engine, and notification
delivery -- built this pass, real code, no per-item logic:

| part_id | what it does | real location |
|---|---|---|
| `workflow_executor` | Moves a real record one real stage when a person triggers it; refuses anything not a declared (from, to, role) transition; logs via `audit_trail` (reused) | `packages/builder/engines/workflow_executor.py::transition` |
| `reporting_engine` | One generic parameterised SQL aggregation (count/sum/avg/min/max, filter, group-by), driven by a structured ReportSpec — no per-report code | `packages/builder/engines/reporting_engine.py::run_report` |
| `notification_delivery` | Real in-app record + real SMTP send | `packages/builder/engines/notification_delivery.py::deliver` |

Seventeen are the specialist/generic engines built and proven earlier this
session (`packages/builder/engines/`), each real, stdlib-only, with its own
`prove()` already run for real (see `PROOFS.md`):

| part_id | what it does | bound to (numbered items across the 5 templates) |
|---|---|---|
| `record_cloning` | Copies a real sqlite row, resets/suffixes named columns | pm-teamwork `Duplicate` |
| `stage_history` | Real stage-entry timestamps + rate-over-period metrics | crm-pipeline `Win rate`, booking-frontdesk `No-show rate`, erp-backbone `Sales by month` |
| `stage_conditional_requiredness` | "Field required only once stage X" at write time | crm-pipeline `Lost reason` |
| `stock_ledger` | Atomic stock adjustment + reorder-point check | erp-backbone PO Confirmed→Received, SO Confirmed→Shipped, `Stock on hand` |
| `ledger_balancing` | Sums real Payments against a real Invoice/Bill total | accounting-ledger Invoice/Bill Awaiting payment→Paid |
| `scheduled_jobs` | Real function on a real background thread after a real delay | every `OPS-nnn` job across all 5 templates; relative-to-date/schedule notification timing |
| `document_generation` | Real HTML + a real minimal PDF | accounting-ledger `Send` (document half) |
| `email_parsing` | Real RFC 5322/MIME parsing | accounting-ledger `Send` (message half) |
| `audit_trail` | Real mutation log, queryable back | reused internally by `workflow_executor`; not itself bound to a numbered item |
| `scheduling_availability` | Real interval-overlap conflict detection | on the shelf, not currently bound |
| `search_fts` | Real sqlite FTS5 full-text search | on the shelf, not currently bound |
| `import_export` | Real CSV export/import round-trip | on the shelf, not currently bound |
| `file_conversion` | CSV ↔ JSON | on the shelf, not currently bound |
| `bank_feed_ofx` | Real OFX 2.x bank-statement parsing | on the shelf, not currently bound |
| `calendar_ics` | Real RFC 5545 iCalendar generate/parse | on the shelf, not currently bound |
| `document_signing` | Real HMAC-SHA256 sign/verify | on the shelf, not currently bound |
| `pdf_form_filling` | Real AcroForm PDF generate/fill | on the shelf, not currently bound |

No `app_engine.py` runtime or "foundation modules" exist in this repository
— those names belong to a different codebase. This repo's own real runtime
is `builder.py` (CRUD + OAuth) plus the 20 engines above — which, since
this pass, includes a generic workflow executor, a generic reporting
engine, and real notification delivery, so plain person-triggered
transitions and single-table aggregation reports are now genuinely covered
where they fit that scope. What's still correctly unbound: `approve`/
`cancel` actions (no declared rule for either kind at all, not even a
generic one); the `Reassign` custom action (a plain field edit with no
custom-action execution rule); automatic transitions gated on a live
external event (Acuity's deposit-triggered confirm — needs real payment
processing, not on the shelf); and reports whose own metric needs a
cross-table join, a computed value, or bucketing (`Profit and loss`,
`Aged receivables`) — genuinely outside `reporting_engine`'s real,
single-table scope, not forced through it. None of these is invented or
stubbed; each is named with its real reason in
`packages/requirements-engine/build/<template>/CHECK_OUTPUT.txt`.
