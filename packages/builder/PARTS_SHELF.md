# Parts shelf

A part is real, already-running code — never a description, a stub, or a
placeholder. `parts_shelf.json` is the machine-readable version this
directory's tooling reads; this is the human-readable index of the same 32
parts. (This line previously said 18 while the tables below listed 19 —
corrected, along with the "sixteen engines" count, which was always 17.) Every numbered item across the five locked templates binds to one of
these by `part_id`, written directly into that item's own entry in its
assembled spec (`packages/requirements-engine/build/<template>/BOUND_SPEC.json`)
— never a separate document.

Three parts are generic, existing Builder rules (not new code, not
duplicated — referenced at their real location in `builder.py`):

| part_id | what it does | real location |
|---|---|---|
| `crud_list_detail` | Record CRUD: sqlite table, `/api/<record>s` routes, list+detail HTML pages | `builder.py::{build_schema,crud_routes,render_crud_handler,_render_list_screen,_render_detail_screen}` |
| `oauth_connect` | OAuth start/callback/status routes + integration-status page | `builder.py::{oauth_routes,render_oauth_handler,_render_integration_screen,_resolve_provider}` |
| `api_key_connect` | Pasted-key linked service: key field, store route, status that never echoes the key | `builder.py::{api_key_routes,render_api_key_handler,_render_api_key_screen}` — registered 2026-09-05; it was generating real screens while absent from the shelf |

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
| `audit_trail` | Real mutation log, queryable back | on the shelf, not currently bound |
| `scheduling_availability` | Real interval-overlap conflict detection | on the shelf, not currently bound |
| `search_fts` | Real sqlite FTS5 full-text search | on the shelf, not currently bound |
| `import_export` | Real CSV export/import round-trip | on the shelf, not currently bound |
| `file_conversion` | CSV ↔ JSON | on the shelf, not currently bound |
| `bank_feed_ofx` | Real OFX 2.x bank-statement parsing | on the shelf, not currently bound |
| `calendar_ics` | Real RFC 5545 iCalendar generate/parse | on the shelf, not currently bound |
| `document_signing` | Real HMAC-SHA256 sign/verify | on the shelf, not currently bound |
| `pdf_form_filling` | Real AcroForm PDF generate/fill | on the shelf, not currently bound |

Three are the generic Builder runtime capabilities that used to be missing
entirely -- a workflow executor, a reporting engine, and notification
delivery -- built this pass, real code, no per-item logic:

| part_id | what it does | real location |
|---|---|---|
| `workflow_executor` | Moves a real record one real stage when a person triggers it; refuses anything not a declared (from, to, role) transition; logs via `audit_trail` (reused) | `packages/builder/engines/workflow_executor.py::transition` |
| `reporting_engine` | One generic parameterised SQL aggregation (count/sum/avg/min/max, filter, group-by), driven by a structured ReportSpec — no per-report code | `packages/builder/engines/reporting_engine.py::run_report` |
| `notification_delivery` | Real in-app record + real SMTP send | `packages/builder/engines/notification_delivery.py::deliver` |

Three more finish that runtime — the automatic half of a lifecycle, the
custom buttons, and form screens — each proven against a real database, and
the form one against real Chromium typing into the real rendered form:

| part_id | what it does | real location |
|---|---|---|
| `system_triggered_transition` | Fires a `mover: automatic` edge on the system's own declared event; refuses an undeclared event, an edge a person owns, and an ambiguous workflow | `packages/builder/engines/system_triggered_transition.py::{fire,edges_from}` |
| `custom_action_execution` | Runs a record's own declared extra button (set_fields / clear_fields / reset_to_stage); refuses an actor the action does not name, an effect with no code, a column that does not exist | `packages/builder/engines/custom_action_execution.py::run` |
| `form_render_submit` | Renders a real form from the record's declared fields and turns a real submission into a real row; required/number/email/unique enforced, undeclared fields refused | `packages/builder/engines/form_render_submit.py::{render_form,validate,submit,read_back}` |
| `stage_approval_gate` | A gated stage will not move on until a declared approver has really decided; a decline sends the record to the workflow's own back_to stage | `packages/builder/engines/stage_approval_gate.py::{decide,check_may_leave,decision_for}` |

Six are Hands — the paperwork-execution engine in `packages/hands/`. Each
is real running code with a live test named as its evidence; none of them
runs against a model, a mock or a stub. See `packages/hands/PROOFS.md`.

| part_id | what it does | real location |
|---|---|---|
| `document_field_detection` | Reads a real PDF's real fields — name, value **and** geometry — and gives each one a provenance | `hands/fields.py::{detect,classify}` |
| `paperwork_session_lifecycle` | The sqlite-backed session state machine; one writer, illegal moves refused, terminal states final | `hands/session.py::{TRANSITIONS,transition,trail}` |
| `trust_gate_approval` | Backend-enforced approval bound to the SHA-256 of the exact payload; single-use, expiring, un-pre-approvable | `hands/trust_gate.py::{request,decide,check}` |
| `value_provenance` | KNOWN / SUPPLIED_BY_CUSTOMER / DERIVED / MISSING / REQUIRES_APPROVAL, validated before storage | `hands/provenance.py::{check,blocks_execution}` |
| `defined_workflow_containment` | Permitted/prohibited actions, gates and completion conditions, checked at definition and at execution | `hands/workflow.py::{Workflow,get}` + `hands/engine.py::_require_permitted` |
| `preserved_original_document_store` | Write-once originals, hash re-checked at completion, completed copy as a separate attested file | `hands/documents.py::{store_original,write_completed,attest,original_intact,safe_filename}` |

Hands does not duplicate what is already here: it calls `pdf_form_filling`,
`document_signing` and `audit_trail` at their real locations in
`packages/builder/engines/`, and `hands/shelf.py` fails loudly rather than
falling back to a copy if the shelf moves.

No `app_engine.py` runtime or "foundation modules" exist in this repository
— those names belong to a different codebase. This repo's own existing,
real runtime is `builder.py` (CRUD + OAuth only) plus the engines above.
The Builder-runtime gap this file used to describe — no workflow executor,
no reporting engine, no notification delivery, no custom-action rule, no
form rule — is now closed by the six generic parts above, all real, all
proven. What is still genuinely missing is named where it is missing: a
report whose number no record actually stores has nothing to sum, and that
is a hole in the answers, not a hole in the shelf. Hands'
`trust_gate_approval` and `paperwork_session_lifecycle` remain specific to
paperwork sessions and are bound to that, not offered as the generic
executor.


## Lifecycle — how a part earns "reusable" (added 2026-09-05)

Every part now carries `version`, `status`, `qualified_revision`,
`provenance` and `seam_journeys`. `packages/builder/shelf.py` owns the rules;
its config block at the top is the place to tune them.

```
IMPLEMENTED -> TESTED -> PRODUCT_QUALIFIED -> FROZEN        (DEPRECATED at any point)
```

| status | who grants it | what it means |
|---|---|---|
| `TESTED` | initialisation, or `bump` | the part's own tests pass; no real browser has driven it in an assembled app |
| `PRODUCT_QUALIFIED` | **only** a receipt written by `packages/playwright-tester/seams.py` | a seam journey PASSED in real Chromium against a real running app, at exactly the part's current bytes; the receipt is `qualification/<part_id>@<version>.json` |
| `FROZEN` | `python shelf.py freeze <part_id>` — one-time, owner's action | the qualified bytes are pinned; any change under the same version is reported by `shelf.py check`, and `bump` is the only way forward |

The status is never typed in by hand. Why: Command Desk `42f7cf6ce72f63fa`
(9 Aug) passed every test and gate and threw on the first real click,
because nothing between the tests and the product opened a browser. A part
proven only by tests is `TESTED` and says so.

**Revision.** `source_revision(part)` is a sha256 over the exact source of
every `location` the part names (`file::symbol` hashes that symbol's source
only, so a change elsewhere in `builder.py` does not move `crud_list_detail`).
Bound specs pin it (`part_bindings.pins`), the Builder writes it into every
built app's `MANIFEST.json`, and the checker / the loop's Definition of Done
report DRIFT when the shelf no longer holds the pinned bytes.

**Seam journeys** ship with the part (`seam_journeys`, mirrored from
`seams.py JOURNEYS`) and are re-run at every assembled app's own seams: a part
qualified in one app is still dropped into a different page in the next.
A journey ends PASS (browser-verified, end to end, re-read), BLOCKED (the app
gives the browser no way to do or see a step — a product finding, printed,
never a pass), FAIL (charged to the part whose step failed), or N/A.

**Provenance.** `read_from` names the reference application(s) the part's
structure was read from; `implementation` says whose code it is (all of it is
original; nothing was copied from Asana, Pipedrive, Acuity, Odoo or Xero);
`licence` is the owner's default (all rights reserved) until the owner decides
otherwise.

Commands: `python shelf.py check | revision <part> | freeze <part> | bump <part> <ver>`;
`python check_capability_bindings.py BOUND_SPEC.json [--require-qualified]`;
`python seams.py SPEC.json --base-url ... --app-dir <built app> -o out/`.
