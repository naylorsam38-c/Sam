# Assembly Engine — component 2 of the chain

Requirements Engine (component 1) asks questions and records answers as
evidence. It does not decide what a good app looks like — that was decided
once, in `question_graph_v3.json`'s `fills`/`system_defaults`/`derivations`,
and is not re-decided here.

**This script no longer derives a build model from raw answers at assembly
time.** It used to: every run of `assemble()` called `derive()`/
`build_model()` fresh, which meant a screen or action's number was never
actually permanent — reorder an inventory list and every id downstream could
shift. That computation (`derive()`/`build_model()`, still defined in this
file, still the one place it is implemented) now runs exactly **once** per
template, offline, via `requirements-engine/lock_structure.py`, which writes
the result back into the template file as a frozen `structure` block with
permanent, template-prefixed ids (`pm-teamwork/SCR-001` — never renumbered by
a later run, proven by `tests/test_requirements_engine.py`'s idempotency and
reorder tests). `assemble()` here only loads that `structure` whole and
configures it: spec id, title, deploy inputs, `numbered_fields` traceability.
It does not recompute a single screen or action id.

## Contract

**Input**: a completed instance JSON — same shape as
`requirements-engine/templates/*.json` (`inventory`, `answers`,
`per_instance`, `ask_customer`, `features`, **`structure`**), with
`ask_customer == []` and a locked `structure` already present. Several such
instances may be unioned with `--combine`, reconciling shared record names
with `--reconcile OldName=NewName` (see `requirements-engine/CONFIG_MAP.md`'s
combination rule) — `--combine` merges each instance's already-frozen
`structure` blocks directly (concatenation, never a renumber, since every id
is already permanently prefixed with its own template's name).

**Refuses (exit 2), never guesses**, when:
- the instance does not fit the graph — re-runs `check_template.check()`,
  the requirements engine's own coverage/reference validator, imported, not
  reimplemented;
- the instance has no locked `structure` — run `lock_structure.py` first;
  assemble.py will not derive one on the fly to route around a missing lock;
- any numbered screen or action in that structure has a `kind` the Builder
  has no registered rendering rule for (`REGISTERED_SCREEN_KINDS` /
  `REGISTERED_ACTION_KINDS`, kept in lockstep with `packages/builder`'s own
  real rules) — blocks and lists every offending item's own permanent id,
  never silently skips or pretends it will be handled;
- `ask_customer` is non-empty — the front door has not finished;
- combining two templates leaves a real product decision unresolved (e.g. a
  role that was the super role in one template is an ordinary role in the
  merge, and now needs authority answers it never needed alone).

**Output** (`-o DIR`):
- `SPEC.json` — every one of the graph's 222 spec fields, traced to the
  question/default/derivation/deploy-input that owns it, plus a `build_model`
  with the concrete, expanded structures the Builder actually reads: records
  with storage types and access rules, roles with permitted/forbidden
  actions, workflows with transition graphs, a numbered actions inventory
  (`ACT-nnn`), a numbered screens inventory (`SCR-nnn`), and a generated test
  plan (`QA-nnn`) — the direct implementation of the graph's own D15
  ("for every numbered action and transition: perform it as each role,
  assert the declared outcome and location"). The Live Playwright Tester
  (component 4) reads `QA-nnn` directly.
- `SPEC.md` — the same thing, numbered, grouped, human-readable.

## Derivations

All 15 (D01–D15) are implemented in `derive()`, each function documented
with the graph's own `rule` text so the mapping from graph to code stays
checkable by inspection. D12 (actions), D13 (screens), D15 (generated tests)
and D04 (permissions) are exercised by every path in this repo's tests; D09
(tenancy) and D10 (billing) are implemented but only lightly exercised, since
none of the five templates or the Command Desk instance need them deeply.

## Usage

```bash
# once per template, after authoring or editing it:
python ../requirements-engine/lock_structure.py templates/pm-teamwork.json
# every time after that:
python assemble.py instance.json -o out/
python assemble.py --combine templates/booking-frontdesk.json templates/accounting-ledger.json \
                    --reconcile Customer=Contact -o out/
```

## The block-with-numbers consequence, stated plainly

`packages/builder/builder.py` only has real generation rules for two things
today: a record's CRUD screens/actions, and an OAuth `connect` action. None
of the five templates' real workflows, custom record actions, notifications,
or reports have a Builder rule yet. Locking a template's real, full structure
(`lock_structure.py --all`) freezes those unbuildable items into `structure`
exactly as declared — it does not trim them — so assembling any of the five
templates at **full, unfiltered scope is refused today**, listing every
report screen, transition, custom action, etc. by its own permanent id. That
is not a bug in this file: it is `registration_gaps()` finally saying, before
handoff to the Builder, what used to only surface deep inside
`build_screens()` (or get silently filtered out of a test fixture) — never
let a build look done when the thing it claims isn't real yet.

## Regression-tested against real data only

`tests/test_assembly_engine.py` (repo root) runs the derivations directly
against the five requirements-engine templates exactly as shipped —
reverse-engineered from real apps (Asana, Pipedrive, Acuity, Odoo, Xero),
never completed or fabricated for the test — checking each derived value
against the real recorded fact it must trace back to (a field's real
declared type, a role's real recorded grant, a record's real relations).
The two refusal paths are tested the same way validate_graph.py's and
check_template.py's own `--selftest` prove their refuse-paths: a real
template's real (non-empty) `ask_customer` list, and a deliberately invalid
structure — never a fabricated stand-in for a real product. The combine path
is tested against the real, unmodified booking-frontdesk and
accounting-ledger templates, which on their own surface a real unresolved
decision (accounting's super role stops being super once merged with
booking's, and needs authority answers it never needed alone) — a
consequence of a real merge, not a staged one.

That discipline caught three real bugs before anything downstream ever saw
this script: a `roles_scoped` answer of `"nobody"` (a legal string, not a
list) crashed the permissions derivation; `F.03`'s extra-field key is
`field`, not `name`; and `--reconcile` renamed an inventory list entry but
missed the same record name referenced independently inside a link field's
`target_record` and a relation's `target` — found by combining booking's and
accounting's real Appointment/Contact data, not by inventing a scenario for it.

No answer set that stands in for a real customer's decisions is ever
fabricated here, including for testing. The only place a *complete* instance
gets assembled end to end is against real answers — see component 8, built
from Command Desk's own already-approved spec, never invented.
