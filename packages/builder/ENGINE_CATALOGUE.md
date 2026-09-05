# Engine catalogue — the parts library the Builder selects from

This is a parts library, not a framework: every entry below is one
already-implemented, already-proven Python module in
`packages/builder/engines/`. The Builder (`builder.py`) picks the entries a
numbered item needs, by name, and wires them into the generated app. **It
never writes an engine during a job** — if a numbered item names no entry
here, or names one whose kind has no engine, the Builder refuses (same
`BuildRefused` discipline as every other unregistered kind), listing the
item's own permanent number. See `packages/requirements-engine/BINDINGS.md`
for the actual name -> engine bindings across all five locked templates, and
`packages/builder/PROOFS.md` for every entry's real, just-run evidence in
full.

Populated from two sources, per directive: (1) every specialist engine
already declared across the five locked templates
(`packages/requirements-engine/SPECIALIST_ENGINES.md`) — 8 of the 17 below;
(2) the engines those five apps actually run that the templates never
captured (document generation, PDF form filling, OCR, e-signature, payment
processing, bank feed and email parsing, file conversion, calendar sync,
scheduled jobs, import/export, search, audit trail) — of which 9 more are
registered below, and 3 real capabilities from that same list (OCR, live
payment processing, live e-signature) plus one from the specialist-engine
side (live third-party calendar OAuth sync) are explicitly **not**, named
at the bottom, with the real reason.

---

## audit_trail

**What it does**: Logs every create/edit/delete mutation against a real
table (before/after state, timestamp), queryable back as an ordered history.
**Inputs**: a real sqlite `Connection`; `table_name`, `row_id`, `action`
(`"create"`/`"edit"`/`"delete"`), `before`/`after` (dicts or `None`).
**Outputs**: nothing on write; `history_for()` returns an ordered list of
`{action, before, after, at}`.
**Failure cases**: none raised by design — a missing `before`/`after` is
recorded as `null`, not rejected (an audit log must never itself block a
real mutation).
**Location**: `packages/builder/engines/audit_trail.py` — `ensure_table()`,
`record()`, `history_for()`.
**Evidence**: 3 real mutations against a real sqlite table, logged and
replayed exactly (`PROOFS.md#audit_trail`).

## stage_history

**What it does**: Records the real timestamp a record entered a workflow
stage; computes rate-over-a-period metrics (e.g. "win rate") straight from
that history.
**Inputs**: sqlite `Connection`; `record_table`, `row_id`, `stage`,
optional `at`. `rate_between()` additionally takes `numerator_stage`,
`denominator_stages`, `since`/`until`.
**Outputs**: `entered_at()` -> a real epoch timestamp or `None`;
`rate_between()` -> a float in `[0, 1]` or `None` if the denominator is 0.
**Failure cases**: `rate_between()` returns `None` (not a `ZeroDivisionError`)
when nothing entered any denominator stage in the window.
**Location**: `packages/builder/engines/stage_history.py`.
**Evidence**: 3 simulated real Deals; computed win rate 0.5, hand-verified
(`PROOFS.md#stage_history`).

## stage_conditional_requiredness

**What it does**: Enforces "field X becomes required only once the record
reaches stage Y" at write time — a rule R.02's fixed `required` flag cannot
express.
**Inputs**: `rules` (`{stage: [field_name, ...]}`), the record's real
current `stage` and `fields` dict.
**Outputs**: `None` on success.
**Failure cases**: raises `RequirednessViolation`, naming every missing
field, if the record is at a ruled stage and any required field is falsy.
**Location**: `packages/builder/engines/stage_conditional_requiredness.py`.
**Evidence**: a Lost deal missing `Lost reason` rejected with a real,
specific message; the same deal with it set accepted
(`PROOFS.md#stage_conditional_requiredness`).

## record_cloning

**What it does**: Copies a real row into a new real row, with named columns
overridden to fixed values and a title column suffixed.
**Inputs**: sqlite `Connection`; `table`, `row_id`, `id_column`,
`overrides` (dict), `title_column`, `title_suffix`.
**Outputs**: the new row's real generated id (a UUID4 string).
**Failure cases**: raises `ValueError` if the source row does not exist.
**Location**: `packages/builder/engines/record_cloning.py`.
**Evidence**: a real Task row cloned; the clone reset to `To do` with
`(copy)` appended, the original untouched (`PROOFS.md#record_cloning`).

## scheduling_availability

**What it does**: Real interval-overlap conflict detection for a resource
(e.g. staff member) over a time range, scoped per resource.
**Inputs**: sqlite `Connection`; `table`, `staff_column`, `start_column`,
`duration_minutes`, `staff`, `proposed_start_epoch`, optional `exclude_id`.
**Outputs**: a list of the real conflicting rows (empty if none).
**Failure cases**: none raised — an empty conflict list IS the "no
conflict" answer, by design.
**Location**: `packages/builder/engines/scheduling_availability.py`.
**Evidence**: an overlapping proposed booking flagged; a clear slot and a
different staff member's identical time both correctly not flagged
(`PROOFS.md#scheduling_availability`).

## scheduled_jobs

**What it does**: Runs a real function on a real background thread after a
real delay — timeouts, reminders, and every one of the five templates' own
D11 recurring-ops (`OPS-nnn`) entries need this primitive.
**Inputs**: `delay_seconds`, `fn`, `*args`, `**kwargs`.
**Outputs**: a `ScheduledJob` handle (`.cancel()`, `.join()`).
**Failure cases**: `fn` raising is not caught here — it surfaces exactly as
`threading.Timer` itself surfaces it (printed to stderr on the background
thread); the caller's `fn` is responsible for its own error handling,
same as any other scheduled callback.
**Location**: `packages/builder/engines/scheduled_jobs.py`.
**Evidence**: a real 0.3s job over a real 0.6s wait really fired; a job
whose condition became false before it fired did not act; a cancelled job
never fired (`PROOFS.md#scheduled_jobs`) — this proof also caught and fixed
a real cross-thread sqlite3 connection bug (`check_same_thread=False` is
required when a background thread touches the same connection).

## stock_ledger

**What it does**: Atomic stock-quantity adjustment on order-line
fulfilment, plus reorder-point condition evaluation.
**Inputs**: sqlite `Connection`; `table`, `product_id`, `quantity`,
`direction` (`"receive"`/`"ship"`), column names.
**Outputs**: `apply_order_line()` -> `(new_stock, reorder_needed: bool)`.
**Failure cases**: `needs_reorder()` raises `ValueError` if the product
does not exist.
**Location**: `packages/builder/engines/stock_ledger.py`.
**Evidence**: stock 10 -> ship 6 -> 4 (reorder needed) -> receive 20 -> 24
(no longer needed) (`PROOFS.md#stock_ledger`).

## ledger_balancing

**What it does**: Sums real Payment rows applied against a real Invoice/
Bill and compares to its total — the actual condition behind "Payments
applied ... reach its total".
**Inputs**: sqlite `Connection`; `payments_table`, `target_column`,
`target_id`/`invoice_id`, `total_column`, column names.
**Outputs**: `applied_total()` -> a real sum; `is_paid()` -> bool.
**Failure cases**: `is_paid()` raises `ValueError` if the invoice does not
exist.
**Location**: `packages/builder/engines/ledger_balancing.py`.
**Evidence**: Invoice total 100.00; 40 applied -> not Paid; +60 applied ->
Paid (`PROOFS.md#ledger_balancing`). Initiating a live charge is a separate,
unregistered concern (see bottom of this file).

## search_fts

**What it does**: Real full-text search and ranking over a record's text
fields, via sqlite's own built-in FTS5 virtual table.
**Inputs**: sqlite `Connection`; `index_name`, `columns` to index; `query`
string to search.
**Outputs**: a list of matching real row ids, best match first (`bm25`
ranking).
**Failure cases**: an FTS5 syntax error in `query` propagates as
`sqlite3.OperationalError` — not swallowed.
**Location**: `packages/builder/engines/search_fts.py`.
**Evidence**: 3 real indexed rows; a query for "invoice" matched only the
one real row that mentions it; an absent word matched nothing
(`PROOFS.md#search_fts`).

## import_export

**What it does**: Real CSV export from, and import into, a record's real
sqlite table.
**Inputs**: sqlite `Connection`; `table`, `columns`, a real file `path`.
**Outputs**: row counts written/read.
**Failure cases**: `import_csv()` raises `ValueError` naming every missing
required column, rather than inserting a partial row.
**Location**: `packages/builder/engines/import_export.py`.
**Evidence**: 3 real rows exported to a real temp CSV file, table wiped,
re-imported from that same file, round-trip verified row for row
(`PROOFS.md#import_export`).

## file_conversion

**What it does**: CSV <-> JSON conversion — the one slice of "file
conversion" genuinely buildable without a new dependency.
**Inputs**: real file paths (csv/json).
**Outputs**: row counts converted.
**Failure cases**: `json_to_csv()` raises `ValueError` if the JSON array is
empty (no columns to infer).
**Location**: `packages/builder/engines/file_conversion.py`.
**Evidence**: a real CSV file -> real JSON -> real CSV again, exact
round-trip (`PROOFS.md#file_conversion`). General image/office-document/
media format conversion needs real codec libraries this project's "no new
dependencies" rule does not allow — not attempted.

## email_parsing

**What it does**: Parses a real RFC 5322/MIME message (headers, body,
attachments) via Python's own stdlib `email` module.
**Inputs**: raw message bytes.
**Outputs**: `{subject, from, to, body, attachments: [{filename,
content_type, size}]}`.
**Failure cases**: malformed bytes surface whatever `email.parser` itself
raises — not caught or reinterpreted here.
**Location**: `packages/builder/engines/email_parsing.py`.
**Evidence**: a real MIME multipart message with a real PDF attachment,
serialised and parsed back, every field exact
(`PROOFS.md#email_parsing`).

## bank_feed_ofx

**What it does**: Parses a real OFX 2.x (XML) bank statement export into
real transactions.
**Inputs**: real OFX 2.x XML bytes.
**Outputs**: a list of `{fitid, type, date, amount, memo}`.
**Failure cases**: malformed XML raises `xml.etree.ElementTree.ParseError`
— not caught here.
**Location**: `packages/builder/engines/bank_feed_ofx.py`.
**Evidence**: a real, spec-shaped OFX 2.0 sample statement with 2 real
transactions, both extracted exactly (`PROOFS.md#bank_feed_ofx`).

## calendar_ics

**What it does**: Generates and parses real RFC 5545 (iCalendar) text —
hand-written to the published standard (line folding, escaping) since no
calendar library is installed.
**Inputs**: `generate_ics()` takes a list of `{uid, summary, dtstart,
dtend}`; `parse_ics()` takes real iCalendar text.
**Outputs**: real CRLF-terminated `.ics` text, or the same event dicts
parsed back.
**Failure cases**: an unrecognised property line is silently skipped
(RFC 5545 itself requires unknown properties to be ignored, not rejected).
**Location**: `packages/builder/engines/calendar_ics.py`.
**Evidence**: 2 real events (one with commas/semicolons needing real
escaping) round-tripped exactly (`PROOFS.md#calendar_ics`). Live OAuth
sync against a real third-party calendar account is not attempted (see
bottom of this file).

## document_signing

**What it does**: Real HMAC-SHA256 signing and constant-time verification
of a document's real bytes — a working integrity/authenticity primitive
(the same real mechanism payment gateways sign webhooks with).
**Inputs**: `sign(secret, document_bytes)`; `verify(secret, document_bytes,
signature)`.
**Outputs**: a hex digest; a bool.
**Failure cases**: none raised — a wrong secret or tampered document
returns `False`, never raises.
**Location**: `packages/builder/engines/document_signing.py`.
**Evidence**: genuine signature verifies True; one mutated byte -> False;
wrong secret -> False (`PROOFS.md#document_signing`). **This is not
legally-binding e-signature** — no identity verification, no licensed
provider (see bottom of this file).

## document_generation

**What it does**: Renders real HTML, and a real minimal single-page PDF
(hand-built byte structure — no PDF library is installed).
**Inputs**: `render_html(title, lines)`; `render_pdf(path, title, lines)`.
**Outputs**: an HTML string; a real `.pdf` file on disk.
**Failure cases**: none raised in the current scope (single page, Helvetica
only, no images) — a longer document needing pagination is out of scope,
stated, not silently truncated.
**Location**: `packages/builder/engines/document_generation.py` —
`render_pdf()`/`read_pdf_text()` (an independent verifier, not the same
code path, so a match is real proof).
**Evidence**: a real PDF (title + 3 lines, one with real parentheses)
written, its real `%PDF`/`%%EOF`/xref structure checked, then read back by
the separate parser with every line exact (`PROOFS.md#document_generation`)
— this proof caught and fixed two real bugs (an xref off-by-one reading
object 0's placeholder as a real offset; a `.index(b")")` call that found
an escaped `\)` instead of the real closing paren).

## pdf_form_filling

**What it does**: Generates a real PDF with a real, minimal AcroForm (merged
field/widget objects, `/NeedAppearances true`), and fills a named field's
value by re-rendering with an updated field list.
**Inputs**: `render_pdf_with_form(path, title, fields)` — `fields`: list of
`{name, label, value, rect}`. `fill_field(path, title, fields, field_name,
new_value)`.
**Outputs**: a real `.pdf` file with real `/AcroForm`/`/Widget` objects;
`read_form_fields()` -> a list of `{name, value}`.
**Failure cases**: `fill_field()` raises `ValueError` if `field_name` does
not exist among the given fields.
**Scope, stated plainly**: fills by a full, valid re-render of a form this
engine itself generated — not a minimal incremental update to an arbitrary
third-party PDF (the more complex mechanism real PDF editors use). Filling
an externally-sourced PDF's form is not attempted.
**Location**: `packages/builder/engines/pdf_form_filling.py`.
**Evidence**: a real PDF with 2 real blank fields; one filled with a real
value; both fields re-read by the independent parser — only the filled one
changed (`PROOFS.md#pdf_form_filling`).

---

## Not registered — evaluated, not faked

- **OCR** — no `tesseract` binary installed (checked: `which tesseract` ->
  nothing), no OCR in Python's stdlib, no reachable/authorised OCR API in
  this session. Per "unproven means unregistered": absent, not stubbed.
- **Live payment processing** (an actual charge against a real gateway) —
  Stripe's API is blocked at this sandbox's own network proxy (`curl` ->
  `CONNECT tunnel failed, response 403`, a real organisation-policy denial,
  not to be retried per this environment's own rule). `ledger_balancing`
  above covers the real *balancing* logic once payments already exist;
  *initiating* one does not.
- **Live e-signature** (identity-verified, provider-backed, e.g. DocuSign)
  — no such provider's credentials exist in this session. `document_signing`
  above is a real, different, narrower capability (cryptographic integrity),
  registered under its own honest name, not as a substitute.
- **Live third-party calendar sync** (OAuth against a real Google/Outlook
  account) — reachable at the network level (confirmed: a real request to
  `googleapis.com` got a real `401`) but no real human can complete OAuth
  consent inside this session, the same honest limit already established
  for Command Desk's own OAuth flow. `calendar_ics` above is the real,
  file-level capability that does not depend on this.
