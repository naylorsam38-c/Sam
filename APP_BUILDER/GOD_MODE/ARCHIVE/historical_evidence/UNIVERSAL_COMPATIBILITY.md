SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Reason: Historical evidence report for a completed build round. Its operative rules and current test evidence are now stated directly in God_Mode_Specification.md and GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md. Nothing in this document was found to conflict with the current implementation; preserved as the historical record of how the current state was reached.
Original path: `UNIVERSAL_COMPATIBILITY.md` (repo root)
Archived: 2026-09-13

---

# Universal compatibility — a compatible library, not a compatibility report

This closes out the instruction: stop classifying capabilities as green/yellow/orange/red and
tolerating the non-green ones; change the library until every capability in it conforms to one
common contract by construction, enforce that at admission time, and prove it by building things
that were never built before. Nothing here was achieved by relabeling — every claim below is backed
by a real build, a real regression test, or a real adversarial test that was confirmed to fail
correctly before it was confirmed to pass.

**Scope boundary, stated once, plainly**: `build.py`'s own internal proving-table fixtures (the
`CAP-0001`-style records `verify_build.py` builds and deliberately breaks, to prove build.py itself
correctly rejects malformed input) are not part of the capability library. They are testing
infrastructure for the builder, several of them deliberately non-conformant on purpose. The new gate
below never touches them — `verify_build.py`'s 29/29 passes completely unchanged, proving that.

## What changed

### 1. One real shared library capability (`CAP-0000`), not N duplicated copies

Every capability in the audited library duplicated its own copy of `_load()`/`_save()` — proven
byte-identical except a filename, but still N copies, not one. `CAP-0000` is now a real shelf
capability, written once per app, holding the actual, single-source implementation of storage
(`load`/`save`), the error-code mapping, and a `notify()` primitive any capability can call directly.
Every other capability's generated `_load()`/`_save()` are now thin wrappers that dynamically import
`CAP-0000`'s real module — the same file-based dynamic-loading technique the host already used to
discover sibling capabilities, just invoked from a capability instead of the host. Because the call
surface (`_load()`, `_save(rows)`) didn't change, **zero of the library's ~140 hand-written handler
bodies needed to be touched** to make this real.

### 2. Standardized errors and identity/context — centrally, not per capability

`modules/<host>/app.py`'s `dispatch()` now normalizes every capability's error response into one
shape, `{"error": {"code": "...", "message": "..."}}`, and introspects each handler's arity to pass a
real `ctx` object (`{"user": None, "authenticated": False}`) to any handler that declares it wants
one. Both changes live in one place — the host template — so no capability body needed editing for
either. Proven live, same request, before and after:

```
delete missing (standard error shape): (404, {'error': {'code': 'NOT_FOUND', 'message': 'no todo with id 999'}})
not found route (standard error shape): (404, {'error': {'code': 'NOT_FOUND', 'message': 'not found'}})
```

### 3. The Common Capability Contract v2 — a real, checked schema

Every capability's shelf record now carries, inside the existing (already free-form, so no top-level
schema break — `build.py`'s own §3.6 record shape is exact-match enforced) `data_shape` and
`error_contract` fields:

- `data_shape.contract_version` — the real opt-in marker.
- `data_shape.data_access` — exactly which named entity/store this capability reads or writes, and
  how. Derived automatically from facts already passed to the generator (its data filename, its side
  effects) — never hand-typed, so it can't drift from what the code actually does.
- `data_shape.context_fields` — identity/context fields this capability would read (empty everywhere
  today, correctly, since nothing has real auth yet — but declared, not silently absent).
- `error_contract.error_codes` — the real error codes this capability can actually return, including
  `INTERNAL_ERROR` for every capability (genuinely possible for any of them) and `NOT_FOUND`/
  `VALIDATION_ERROR` only where the capability's own shape can actually produce them.

### 4. A real compatibility gate inside `build.py` — admission control, not a report

`validate_v2_contract()`, called for every capability a template requires, checks structural
completeness AND cross-checks declared `data_access` against the *real, already-copied* source (not
the shelf's unverified claim about itself) for anything it touches but never declared. Gated on
`contract_version == "2.0"`, so it is inert for legacy fixtures and fully enforced for everything in
the library. Proven with two deliberate, real violations — not asserted, actually tried and confirmed
to fail correctly:

```
$ python3 build.py   # payroll's employees.json access stripped from its own declared data_access
BROKEN  contract violation  CAP-1003  touches undeclared data: ['employees.json']

$ python3 build.py   # payroll's real employees.json read reverted to a hand-rolled path, bypassing CAP-0000
BROKEN  contract violation  CAP-1003  bypasses the shared storage interface (constructs its own data path instead of using CAP-0000)
```

### 5. Remediated, not labeled: the one real ORANGE and every real YELLOW/RED

- **`payroll`'s "Run Payroll"** — the one real undeclared coupling the original audit found — no
  longer embeds its own bespoke `EMP_FILE`/`_load_employees()`. It calls `_shared.load('employees.json')`
  directly (the exact same shared primitive every other capability uses), and its access is now
  declared via `extra_data_access` and checked by the gate. Re-verified functionally correct after the
  rewrite: 2 employees in, 2 correct payroll records out (`net = gross * 0.8`), same as before.
- **The 3 RED capabilities** (auction's bid rule, event_ticketing's capacity rule, dating's
  reciprocity rule) were already generalized into real, parameterized engines
  (`add_exceeds_threshold_capability`, `add_bounded_counter_capability`,
  `add_symmetric_relationship_capability`) in the prior round; this round folded them into the same
  v2 contract and CAP-0000 storage as everything else, and reused each engine again in genuinely new
  domains below — not just reproducing the app it replaced.
- **`todo_list`** was the one app still generated by a standalone, pre-`gen_common.py` script,
  outside the shared machinery entirely — "0 incompatible capabilities" can't be true library-wide
  while one app's capabilities are generated by different code than everything else. Ported onto
  `AppBuilder` (real TodoMVC HTML/CSS/JS preserved verbatim — independently justified by the real
  published spec it's sourced from, no reason to touch it); its 7 capabilities now carry the same v2
  contract and CAP-0000 dependency as the rest. Reproven: 9/9 checks, exact parity with the original
  round-7 proof, plus a fresh functional pass confirming the standardized error shape end to end.
- **Every other capability** (create/list/update/delete, ~140 of them) already shared byte-identical
  logic; they now also share the real storage implementation and the real contract, closing the gap
  between "generated similarly" and "genuinely the same interface."

### 6. A real, automated recursive audit — not a grep

`verification/audit_dependency_graph.py` walks every capability's dependency graph across the *whole*
library at once (not one app's build at a time), checking for missing targets, cycles, and running
`build.py`'s own `validate_v2_contract()` — imported, not reimplemented, so there is exactly one
definition of "compatible" in this codebase — against every v2 capability's real shelf source
directly. Proven to have real teeth with two independent, deliberate breaks before trusting a clean
result:

```
Missing dependency targets: 1
  dating: CAP-3101 depends on missing CAP-9999
Hidden/undeclared data access: 1
  payroll: CAP-1003: contract violation  CAP-1003  touches undeclared data: ['employees.json']
```

Real, current result across the whole library:

```
Total capabilities across the library: 266
Total dependency edges checked: 221
Missing dependency targets: 0
Dependency cycles: 0
Contract v2 structural violations: 0
Hidden/undeclared data access: 0
CLEAN: 0 missing targets, 0 cycles, 0 contract violations, 0 hidden data access across 266 capabilities in 46 projects.
```

## The proof: three new apps, combinations never tried before

Not one demonstration — three, each mixing capabilities and engines that had never been combined
with each other, built through the real, unmodified `build.py` pipeline to `READY`, then exercised
live beyond the automated checks:

| New app | What's genuinely new about the combination |
|---|---|
| `community_event_board` | Calendar/Event (new) + bounded-counter engine (1st reuse, RSVP capacity) + Notification (new) + `team_chat`'s message capability reused byte-for-byte |
| `fitness_challenge_board` | bounded-counter engine (**3rd** distinct domain: challenge slots) + symmetric-relationship engine (**2nd** domain: workout buddies, nothing to do with dating) + `fitness_tracking`'s workout capability reused byte-for-byte |
| `course_enrollment_hub` | Calendar/Event + bounded-counter engine (**4th** distinct domain: session seats) + `online_course_lms`'s course capability reused byte-for-byte + `quiz_and_flashcards`'s card capability reused byte-for-byte, **repurposed** as session-feedback prompts |

Each was proven live, not just built:

```
join (1st):                (200, {'participants': 1, ...})
join (2nd, full):           (400, {'error': {'code': 'VALIDATION_ERROR', 'message': 'challenge is full'}})
buddy propose A->B:         (200, {'paired': False, ...})
buddy propose B->A:         (200, {'paired': True, ...})   # mutual -> real match

enroll (1st):                (200, {'enrolled': 1, 'seats': 1, ...})
enroll (2nd, full):          (400, {'error': {'code': 'VALIDATION_ERROR', 'message': 'session is full'}})
add feedback prompt (reused verbatim, repurposed): (201, {'question': 'How was the session?', ...})
invalid session date still rejected: (400, {'error': {'code': 'VALIDATION_ERROR', 'message': "start is not a valid ISO-8601 timestamp: 'nope'"}})
```

The bounded-counter engine alone is now proven across **four** unrelated domains (ticket sales, RSVP
capacity, challenge slots, session seats) from the exact same generator call, parameterized
differently each time — the real definition of "universally composable," demonstrated, not asserted.

## Full regression, re-run clean-room, after every change above

```
verify_build.py:          29/29  (unchanged -- the gate never touches these fixtures)
test_readiness.py:        20/20  (unchanged)
build_batch.py (43 apps): 43/43 READY
prove_generalization.py:  3/3 MATCH (auction, event_ticketing, dating engines vs. their originals)
audit_dependency_graph.py: 0 problems across 266 capabilities, 46 projects
3 new composed apps:       3/3 BUILT -> READY -> promoted, each functionally re-verified live
```

## Acceptance criterion, checked against what was actually run

| Criterion | Result |
|---|---|
| 0 incompatible capabilities | Every capability in the library (not build.py's own test fixtures) carries contract v2 and passes the gate — checked individually for all 266, not sampled |
| 0 undeclared dependencies | `dependencies` fully populated; the one real case (payroll) found, fixed, and now enforced |
| 0 unresolved dependencies | 221 dependency edges checked, 0 missing targets |
| 0 capabilities requiring a permanent compatibility exception | None exist; the 3 previously-RED capabilities are now generic engines, `todo_list` is on the shared machinery, payroll's coupling is declared and routed through the shared library like everything else |
| Every capability independently usable and composable | Demonstrated three times, across four domains for the bounded-counter engine alone, including two capabilities (`quiz_and_flashcards`' card, `fitness_tracking`'s workout) reused verbatim in a context their original app never anticipated |

What this still does not claim, honestly: no shared identity/auth layer exists yet (every
`context_fields` declaration is correctly empty), and browser-side cross-*app* combination (as
opposed to the file-level and generator-level composition proven here, all within one assembled app)
still needs CORS headers or a gateway if someone wants two *separately deployed* apps' frontends to
talk to each other live. Nothing above claimed otherwise.
