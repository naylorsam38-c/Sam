**Superseded — this was the interim checkpoint. The build finished: 17
engines total (the 5 below plus `scheduled_jobs`, `stock_ledger`,
`ledger_balancing`, `search_fts`, `import_export`, `file_conversion`,
`email_parsing`, `bank_feed_ofx`, `calendar_ics`, `document_signing`,
`document_generation`, `pdf_form_filling`) are implemented and proven. See
`packages/builder/ENGINE_CATALOGUE.md` (the
parts library), `packages/builder/PROOFS.md` (every engine's real captured
proof output), and `packages/requirements-engine/BINDINGS.md` (every
numbered item across the five templates bound by name, and what's still
blocking). Left below as the real historical record of the mid-build state.**

---

# Engine library — interim handoff

Mid-build checkpoint for the current directive: "Build the capability
catalogue as a parts library the builder selects from... Populate it from
two sources [the five templates' specialist engines, plus document
generation/PDF form filling/OCR/e-signature/payment processing/bank feed
and email parsing/file conversion/calendar sync/scheduled jobs/import and
export/search/audit trail]... Test every engine live against a real
system... Bind every numbered item... Re-run the assembler... Report
anything still blocking."

## Environment recon (done, real, informs everything below)

Checked directly in this sandbox, not assumed:

| Capability | Status | Evidence |
|---|---|---|
| `tesseract` binary (OCR) | **Not installed** | `which tesseract` → nothing |
| Any PDF library (`pypdf`, `fitz`, `reportlab`) | **Not installed** | `ModuleNotFoundError` on all three |
| Python stdlib (`email`, `csv`, `sqlite3`, `hmac`, `hashlib`, `xml.etree`, `zlib`, `struct`, `threading`, `socket`) | **All present** | imported cleanly |
| sqlite3 FTS5 (full-text search) | **Available** | `CREATE VIRTUAL TABLE ... USING fts5` succeeded, real query matched |
| `icalendar` / `vobject` (calendar libs) | **Not installed** | `ModuleNotFoundError` on both |
| Stripe API (`api.stripe.com`) | **Blocked at the proxy** | `curl` → `CONNECT tunnel failed, response 403` (an organisation policy denial — per this environment's own rule, not to be retried) |
| Google Calendar API | Reachable, but **no real OAuth credential** | `curl` → real `401` (same "honest edge without a human" limit already established for Command Desk's own OAuth) |

This is why the plan below splits cleanly into **provable-for-real-with-stdlib** engines and a small, explicitly **unregistered** set — nothing here is worked around or faked; where a real system genuinely isn't reachable or authorised, the engine is left out and named as such, per "unproven means unregistered."

## Done so far — 5 engines, each implemented AND proven (not just written)

All in `packages/builder/engines/`, each a real stdlib-only module with a `prove()` that runs a real scenario (not a mock) and asserts on the real observed result. Every one below has actually been executed just now, including catching and fixing one real bug in `scheduling_availability`'s own proof data (a unit mismatch — 1000 epoch-seconds later still overlapped a 30-minute-long appointment; fixed by using the appointment's own real end time).

1. **`audit_trail.py`** — logs create/edit/delete against a real sqlite table (before/after JSON, timestamp), queries history back. Proven: 3 real mutations logged and replayed correctly.
2. **`stage_history.py`** — records the real timestamp a record entered a stage; computes crm-pipeline's own "win rate" definition (entered Won ÷ entered Won-or-Lost in a window) mechanically from that history. Proven: 3 simulated real Deals, win rate computed = 0.5, matching hand-checked arithmetic.
3. **`stage_conditional_requiredness.py`** — enforces crm-pipeline's "Lost reason becomes required [only] once Lost" rule at write time. Proven: a Lost deal missing the field is rejected with a real, specific error; the same deal with it set passes; a Won deal (no rule) needs nothing extra.
4. **`record_cloning.py`** — pm-teamwork's `Duplicate` action: copies a real sqlite row, resets one column, appends a suffix to another. Proven: real clone is a distinct row, correctly reset/suffixed; original untouched.
5. **`scheduling_availability.py`** — booking-frontdesk's "the slot is released" requirement: real interval-overlap conflict check over real sqlite rows, scoped per staff member. Proven: an overlapping proposed booking is flagged, a clear one and a different staff member's identical time are not.

## Not yet started (the rest of the plan, unchanged, to resume next)

Still to implement + prove, in this order:
- `scheduled_jobs.py` — a real `threading.Timer`-based delayed job, proven against real elapsed wall-clock time (booking-frontdesk's 24-hour-timeout shape, tested at a short real duration, not simulated time).
- `stock_ledger.py` — erp-backbone's stock arithmetic + reorder-point alerting.
- `ledger_balancing.py` — accounting-ledger's payment-applied-vs-total auto-transition logic.
- `search_fts.py` — sqlite FTS5, proven with a real indexed/queried dataset.
- `import_export.py` — real CSV export/import round-trip against a real sqlite table.
- `file_conversion.py` — CSV↔JSON round-trip (the one narrowly-scoped, stdlib-only slice of "file conversion" that's honestly buildable without a new dependency).
- `email_parsing.py` — stdlib `email` module against a real RFC 5322 MIME message (with a real attachment).
- `bank_feed_ofx.py` — stdlib `xml.etree` against a real, spec-compliant OFX 2.x sample.
- `calendar_ics.py` — hand-rolled RFC 5545 generate/parse round-trip (no live third-party calendar account — same class of limit as Google Calendar above).
- `document_generation.py` — real HTML rendering plus a minimal, hand-built, genuinely valid PDF (own stdlib generator AND own stdlib verifier, since no PDF library is installed).
- `document_signing.py` — HMAC-SHA256 sign/verify: a real, working integrity/authenticity primitive, explicitly **not** claimed to be legally-binding e-signature.

Then: write `ENGINE_CATALOGUE.md`/`.json` (name, what it does, inputs, outputs, failure cases, location, evidence — one entry per proven engine, numbered items bind by name), bind every numbered screen/action across the five locked templates to a catalogue entry, re-run `assemble.py`'s `registration_gaps()` against each, and report what (if anything) still has no bound engine.

## Confirmed unregistered already (not attempted further — stated, not faked)

- **OCR** — no `tesseract` binary, no stdlib OCR, no reachable/authorised OCR API.
- **Live payment processing** (an actual charge against a real gateway) — Stripe blocked at the proxy, a real organisation-policy denial, not to be retried. (A real, distinct **payment *webhook signature* verification** engine — HMAC-based, the same real mechanism Stripe itself uses to sign webhooks — is still planned above and is provable without reaching Stripe at all.)
- **Live e-signature** (a legally-binding, identity-verified signature via a provider like DocuSign) — no provider credentials exist in this session. (The planned `document_signing.py` is a real, working, *different and narrower* capability — cryptographic integrity/authenticity, not identity-verified e-signature — and will be registered under its own honest name, not as a substitute for the real thing.)
- **Live third-party calendar sync** (OAuth against a real Google/Outlook account) — reachable at the network level but no real user consent is possible without a human, same honest limit already established for Command Desk's own OAuth flow. The file-format-level engine (`calendar_ics.py`, real RFC 5545 generate/parse) is still in scope and does not depend on this.

Resuming the remaining build now.
