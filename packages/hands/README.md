# Hands — the paperwork-execution engine

The customer buys a job, not an agent. A session is bound to a **defined
workflow**, and the engine executes only what that workflow permits. The
API cannot express "do this thing to that document": a caller starts a
session, supplies information, and decides approvals. What happens is
decided by the workflow and the engine.

```
packages/hands/
  hands/config.py       every tunable rule, one comment per setting
  hands/workflow.py     the workflow object + the workflows that exist
  hands/provenance.py   where each value came from; MISSING stops work
  hands/session.py      the lifecycle state machine, in real sqlite
  hands/trust_gate.py   backend-enforced approval, bound to the payload
  hands/fields.py       real AcroForm field detection (name, value, rect)
  hands/documents.py    write-once originals, separate completed copy
  hands/engine.py       the execution loop
  hands/api.py          the real HTTP server
  hands/shelf.py        loads the Builder's parts at their real location
  web/                  the operator screen
  tests/                29 tests, all against a live server
```

## Running it

```bash
export HANDS_API_TOKEN=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")
python3 -m hands.api            # from packages/hands/
# http://127.0.0.1:8799 — paste the token into the screen
```

```bash
pytest packages/hands/tests     # 29 tests: 25 API/engine, 4 real-browser
```

## The five rules it enforces rather than documents

**A workflow, never a command.** `workflow.py` refuses at definition time
any workflow that permits an action no code performs, permits and
prohibits the same action, or has no completion conditions. `engine.py`
refuses any action the session's workflow does not permit — a read-only
review workflow cannot fill a field, and the refusal is a 409, not a
silent skip.

**Missing information is asked for, never guessed.** Every value carries a
provenance — KNOWN, SUPPLIED_BY_CUSTOMER, DERIVED, MISSING,
REQUIRES_APPROVAL — validated before it can be stored. There is
deliberately no "assumed" or "default". A DERIVED value must name what it
was derived from, or it will not go in the database.

**The Trust Gate is the backend.** An approval opens the gate only if it
belongs to this session and action, carries the hash of *exactly* the
payload about to execute, has not expired, and has not been used. So
approving "fill the name with SAM NAYLOR" does not authorise filling it
with anything else; change one value after approving and the session stops
and asks again. One approval authorises one execution — proven under two
concurrent requests racing for the same approval. A customer also cannot
approve a payload the engine never showed them.

**No automatic declarations.** Any field whose name marks a declaration in
the customer's name — signature, declaration, consent, certification,
competency, induction-complete — is `REQUIRES_APPROVAL` even when the
value is known, and supplying the value is not approving it. The markers
are a list in `config.py`, so the rule is tunable without touching code.

**The original is preserved.** Originals are write-once; the completed
copy is a new file in a different directory; both hashes are recorded at
write time and re-checked before a session may complete. A filename with
a path in it is refused rather than rewritten.

## Lifecycle

```
CREATED → INTAKE → WAITING_FOR_INFORMATION → READY → EXECUTING
                → ACTION_REQUIRED → REVIEW → COMPLETED
terminal: COMPLETED · DECLINED · CANCELLED · FAILED
```

`session.transition()` is the only writer of `state`, and it refuses any
move the table does not allow. **A declined approval lands in DECLINED —
an outcome of the product, not a failure of it.**

## Reused from the parts shelf

Loaded from `packages/builder/engines/` at their real location, never
copied (`hands/shelf.py` fails loudly if the shelf moves):
`pdf_form_filling` renders and reads the real PDF, `document_signing`
attests the completed copy's real bytes, `audit_trail` records every
mutation.

## Scope, stated

No payment processing (no provider credentials exist here). No
legally-binding e-signature — `document_signing` is an HMAC integrity
attestation and says so. Filling regenerates the PDF rather than patching
an arbitrary third-party file in place, inherited from the shelf part.
**No model is involved anywhere**: detection reads the document's bytes,
so there is no provider to fake and nothing to simulate.
