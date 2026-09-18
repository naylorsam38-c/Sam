SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Reason: Historical evidence report for a completed build round. Its operative rules and current test evidence are now stated directly in God_Mode_Specification.md and GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md. Nothing in this document was found to conflict with the current implementation; preserved as the historical record of how the current state was reached.
Original path: `review.md` (repo root)
Archived: 2026-09-13

---

# build.py — BUILD REPORT

Built from scratch against `build.py SPEC v1 (2026-09-11)`, the spec that
supersedes both `BUILD_CHAIN_SPEC.md` v2 (chain.py/layer1/layer2/layer3) and
`ASSEMBLER_SPEC.md` v1.1 (assemble.py) — this is the merged, single-script
replacement for both.

Tested by running the real `build.py` as a real subprocess against a real
shelf, real templates, and a real browser (Playwright/Chromium) — never
called in-process, never asserted without the actual captured stdout pasted
(Bible rules 2 and 3). No stubs anywhere: every "failing capability" is a
real Flask route with a real bug in it; every "fix" is a real file that
replaces it; the browser check is a real click in a real page, not a
simulated one. Verification kit: `verification/` — regenerate the fixtures
and rerun the whole table anytime with:

```
python3 verification/gen_fixtures.py
python3 verification/verify_build.py
```

## Standing: 26/26 real checks pass (23 proving-table rows, row 21 split into
its two named cases, plus 2 extra hardening rows pushed past what the table
asks for)

Ran clean, from a freshly regenerated fixture set, several times over, with
a dead-import cleanup pass and a real bug fix in between — same result each
time. Full output of the most recent run is in
`verification/last_run_output.txt`.

| # | Requirement | Result |
|---|---|---|
| 1 | `LAYER3_MODEL` empty → BROKEN missing setting, before stage 1 | PASS — `BROKEN  missing setting  LAYER3_MODEL`, no `builds/`, no `registry.json` written; same for an empty `LAYER3_ENDPOINT` |
| 2 | `LAYER3_CREDENTIAL` never in argv/stdout/reports/ledger | PASS — ran a real HELD-with-model-call attempt using a fake key; grepped stdout, stderr, every `reports/*.json`, and `run_ledger.jsonl` for the literal secret — zero hits. The endpoint is a local port with nothing listening; the real call failed honestly (`model unreachable: URLError: ... Connection refused`) rather than fabricating a response, and the HELD app is `candidate` in the canonical registry |
| 3 | choice.json missing / unreadable / no name → BROKEN choice `<field>` | PASS — three real variants, `BROKEN  choice  file` / `BROKEN  choice  unreadable` / `BROKEN  choice  name`, exit 2, no traceback |
| 4 | app_type not in APPS_LIST.md → BROKEN choice app_type | PASS |
| 5 | template not accepted → BROKEN template not accepted | PASS |
| 6 | required CAP with no shelf IMPL → BROKEN no approved IMPL | PASS |
| 7 | BTN contract matches no CAP → HELD, nothing patched/wrapped | PASS — `HELD  CAP candidate  APP-001/SCR-001/BTN-001 -> CAP-0001: missing required input fields: {'due_date'}  awaiting approval`; confirmed `app.json` was never written and the canonical registry shows the app VOIDed, not forced through |
| 8 | run twice → APP-002, RUN-0002, never repeat/reuse | PASS |
| 9 | registry written, 13/13 invariants, correct shapes | PASS — real `builds/APP-002/registry.json` pasted and every record's key list compared to §3.3–3.7 as transcribed from the standard into the verifier (not to build.py's own output); statuses checked against §6.2; canonical registry `active` for both BUILT apps |
| 10 | app.json → exactly start/port/health | PASS |
| 11 | template with no tests → BROKEN template has no tests | PASS |
| 12 | template tests fail → BROKEN template tests failed, output pasted | PASS — `template tests failing on purpose` (the real subprocess's own stdout) appears before `BROKEN  template tests failed  code 1` |
| 13 | app never answers health → BROKEN app did not start, no checks claimed, process killed | PASS — confirmed no lingering `modules/CAP-0001/app.py` process survives |
| 14 | check fails, no shelf part, `ALLOW_LAYER3=False` → HELD GAP-0001 ... layer three disabled | PASS |
| 15 | pattern-mapped repair → repair, then BUILT | PASS — real fix found and applied by `FAILURE_PATTERN_MAP`, real restart, real re-run of every check, `"matched_by": "pattern"` in the ledger |
| 16 | structural-match-only repair → repair, restart, BUILT | PASS — repaired "Feature Beta" using the separately-shelved "Feature Beta Alt" capability, found purely by matching data shape, `"matched_by": "structural"` in the ledger |
| 17 | a repair that doesn't fix its failure → BROKEN loop guard, both run numbers named | PASS — `BROKEN  loop guard  CHK-013 still fails after feature_gamma_fix@1.0.0 (applied RUN-0001)` |
| 18 | a repair that breaks a passing check → BROKEN regression, immediately | PASS — `BROKEN  regression  CHK-002`, real: the "fix" for one capability really did overwrite a shared file and really did break a check that had really passed the run before |
| 19 | `MAX_RESTARTS=2`, three independently-fixable failures → exactly two repairs then BROKEN restart ceiling | PASS — two real repairs recorded, the third genuinely fixable failure never got a repair attempt at all |
| 20 | same gap raised in two separate invocations of the script → BROKEN repeated gap | PASS — two real, separate `python3 build.py` process runs from the same directory; the second reads the ledger and refuses before touching the model again |
| 21 | no browser check present, or it fails → never BUILT | PASS in both shapes tested: (a) a suite with no browser check at all → `BROKEN  no browser check present in the suite`; (b) a suite where the browser check itself genuinely fails (a real broken button, no `onclick`) → never reaches BUILT (see note below on exactly which path it takes) |
| 22 | the app's process is gone after every exit path, including BROKEN | PASS — checked after a BUILT run and three different BROKEN/HELD paths; no lingering process each time |
| 23 | the whole thing, real shelf, real choice → BUILT, and the journey is completable | PASS — real BUILT run, then a separate hand-equivalent HTTP replay against a freshly-started instance of the same real app, transcript below |

Row 23's hand-equivalent replay (a long-lived instance of the exact same
`modules/CAP-0001/app.py` build.py just assembled, hit the way a person
opening it and clicking the button would):

```
GET / (what a person would see, first 300 chars)
<!doctype html>
<html><head><title>Todo</title></head>
<body>
<h1>Todo List</h1>
<button id="add-item-btn" data-slot="main_list" onclick="addItem()">Add milk</button>
<ul id="item-list"></ul>
...

POST /api/items {"text": "milk"}  (what clicking the button does)
{"created": true, "id": 1, "text": "milk"}

GET /api/items  (what the list now shows)
[{"created": true, "id": 1, "text": "milk"}]
```

## Sam's three fixes — applied 2026-09-12, 26/26 rerun

**One — the registry records are the Numbering Standard's, word for word.**
APP/SCR/BTN/CAP/IMPL records now carry exactly the §3.3–3.7 field sets
(transcribed from `CAPABILITY_NUMBERING_STANDARD.md`, not typed from
memory), the registry's top-level entity is `applications` (§3.2), and every
status is a §6.2 word — `candidate`, `approved`, `active`, `deprecated`,
`retired` — plus `void` for a failed allocation (§6.1 rule 14). The shelf is
read in the same §3.6/§3.7 shape: a CAP's wired implementation is the one
IMPL in its `implementations` list whose status is `active`; a shelf fix an
alias can reach for is `approved`. Aliases are no longer a field on an IMPL
record (§3.7 has none, §7.3: an alias is not an identity) — they live in
`shelf/aliases.json`, the §3.2 `aliases` entity. Row 9 of the verifier now
checks every record against the standard's own key lists, transcribed into
the verifier independently of build.py.

Two values the standard requires that nothing in the spec's inputs carried:
a screen name (§3.4) and a button name (§3.5). They come from the template —
`entry_screen_name`, and `name` on each interface slot — and are BROKEN
`template  entry_screen_name` / `template  slot name  <slot>` if absent.
Not invented, not derived. Two more places I had to pick something because
the standard defers or is silent: (a) §3.6 says `data_shape` uses the
Unified Feature Structure's seven-layer definition, which isn't in the
package — its internals here (`input.required/types`, `output.fields/types`,
`nullable`, `requires_auth`, `security_constraints`) are the minimum the §4.4
twelve-axis match reads; (b) `owner` is `"builder"`, the §3.3 example's own
value. And the BTN's `expected_contract` holds the twelve-axis declaration it
was validated against, not a `contract.*` reference string like the §3.5
example — there is no contract catalogue anywhere in the package to
reference into, and inventing one would be exactly the wrong fix.

**Two — nothing provider-specific.** `LAYER3_ENDPOINT` is a config-block
setting, empty by default, `BROKEN  missing setting  LAYER3_ENDPOINT` if
empty. `call_layer3_model()` POSTs `{"model": LAYER3_MODEL, "messages":
[...]}` to it with the credential as `Authorization: Bearer`, and treats any
2xx as reached, returning the raw body. `grep -i anthropic build.py` finds
nothing. Row 1 now also proves the empty-endpoint refusal; row 2 points the
endpoint at a local port with nothing listening and proves the honest
`model unreachable: URLError: ... Connection refused` path with no credential
leak — no provider involved at all.

**Three — candidate until proven.** An APP is allocated as a §3.3 record in
the `candidate` state, stays `candidate` through assembly, and only a BUILT
run writes `active` — in the canonical registry and in the app's own
`builds/APP-nnn/registry.json`. A HELD or BROKEN in stage two leaves it
`candidate`. A stage-one failure (bad choice, template, shelf, contract) is
`void` per §6.1 rule 14. Numbers are never reused: void and candidate
entries keep their number, the next allocation reads the highest number
present. Proven for real in rows 2, 7, 8/9, 14, 17, 18, 20 — the canonical
registry after each is in `verification/last_run_output.txt`.

Real output, all 26 rows: `verification/last_run_output.txt`. Rerun with
`cd verification && python3 gen_fixtures.py && python3 verify_build.py`.

## Two extra rows, past the 23 the table asks for

Sam's instruction was to keep testing until it's foolproof, not just satisfy
the table once, so two more real scenarios were built and run:

| Extra row | Requirement | Result |
|---|---|---|
| A | A child process that ignores SIGTERM must still be reaped (`proc.kill()` fallback), not left running | PASS — real app installs `signal.SIG_IGN` for SIGTERM; the run took 7.5s instead of the usual ~1.2s (the 5s `terminate()` timeout genuinely elapsed before `kill()` fired), and no process was left running afterward |
| B | Two shelf capabilities that structurally tie for the same repair — see the bug below | PASS, after a real fix (below) |

## Three real bugs found by running it, fixed and reproven

**1. `next_run_id()` skipped a run number after every repair.** The
function scanned both the `"run"` field and the `"restarted_as"` field in
the ledger to find the highest run number in use. But `"restarted_as"` is a
*reservation* for the next run, written by the current run — not a run
that has actually happened yet. Counting it too meant the number got
claimed twice: caught on row 15, live —

```
RUN-0001
...
      repaired by shelf part feature_alpha_fix@1.0.0 -> CAP-0002/IMPL-02 (layer 2, pattern)

RUN-0003        <-- should have been RUN-0002
```

Every single repair in the script, in every scenario, would have silently
skipped a run number this way. Fixed by having `next_run_id()` read only
the `"run"` field — the number of a run that has actually been consumed.
Reran rows 15, 16, 19 (the three rows that exercise a real repair-and-restart)
after the fix — RUN-0002 appears correctly in all three now.

**2. Four unused imports** (`os`, `io`, `signal`, `hashlib`) — none used
anywhere in the file (checked by parsing the AST for every import and
grepping for attribute access on each). Removed.

**3. Two shelf parts that structurally tie for the same repair got silently
resolved to whichever one sorted first, with zero record that a choice was
even made.** Built a real fixture where two independent, unrelated
capabilities both declare the exact shape a failing check's `wants` needs.
`find_structural_match()` walked the shelf and returned the first hit —
correct by its own logic, but the *caller* then applied that "fix" exactly
like a certain one, with nothing in the ledger, the reports, or stdout
saying a second, equally-valid candidate existed and was passed over. That
is precisely what Bible rule 4 rules out — "if something is unknown, do not
guess... surface it clearly" — and a wrong-but-plausible-looking automatic
repair is a worse outcome than a human noticing.

Fixed: the sweep (renamed `find_structural_matches`, plural) now returns
every match instead of stopping at the first. When there's more than one,
`run_layer_two` no longer picks — it raises HELD, naming every tied
candidate by alias and id, and confirms neither gets applied:

```
HELD  CHK-011: ambiguous structural repair -- 2 shelf parts match equally
(feature_beta_alt@1.0.0 -> CAP-0005/IMPL-01, feature_beta_second_alt@1.0.0 -> CAP-0007/IMPL-01)  awaiting approval
```

Reran the full 26-row suite after this change, including row 16 (the
legitimate single-candidate structural match, unaffected since it only ever
had one tied part) — no regressions.

## Judgment calls flagged in the first round (the API choice and the registry-status question are now settled by Sam's fixes above; kept for the record)

- **`call_layer3_model()` calls the Anthropic Messages API specifically**
  (`https://api.anthropic.com/v1/messages`, `x-api-key` header,
  `anthropic-version: 2023-06-01`). The spec names `LAYER3_MODEL` as a
  config value Sam fills in but doesn't name which API the script should
  call to reach it. I picked the Anthropic API because `LAYER3_MODEL` reads
  like an Anthropic model name and Sam is talking to me through Claude — but
  that's an inference, not something the spec states. If the actual target
  is a different provider or a self-hosted endpoint, this needs to change,
  and the credential-secrecy proof (row 2) and the honest-failure-on-unreachable
  behavior would carry over to whatever endpoint replaces it.
- **The concrete repair-matching mechanics** (`FAILURE_PATTERN_MAP`'s
  message-substring → shelf alias lookup, and `find_structural_match()`'s
  exact-set comparison of `category`/`output_fields`/`side_effects`) are my
  design for satisfying the spec's stated *intent* ("layer two's first pass:
  pattern map; second pass: structural sweep") — the spec doesn't give exact
  matching semantics. Building the test fixtures for this actually caught my
  own assumption too fragile at first: an early version of the fixtures gave
  several unrelated capabilities the identical declared output shape, and
  `find_structural_match()` correctly (by its own logic) picked whichever one
  came first alphabetically — including, once, a capability's own *broken*
  implementation as a "fix" for a different capability's failure. That's not
  a bug in the matching logic itself (it did exactly what an exact-set
  structural match should do); it means shelf capabilities need genuinely
  distinct declared shapes for anyone relying on this repair path, which
  isn't written down anywhere in the spec as a shelf-curation requirement. I'd
  raise this explicitly before this goes live: a bad shelf entry could
  currently cause a wrong-but-plausible-looking repair to be applied silently.
- **Row 21's "browser check fails" path currently reaches BROKEN via the
  ordinary gap pipeline (HELD, then BROKEN on a repeat), not via a dedicated
  "browser check not verified" message.** Reading `stage2_prove()` closely:
  the line `raise Broken("incomplete record  browser check not verified")`
  can only fire when a run has *zero* failures but the browser check still
  didn't pass — and given the checks currently defined, a browser check
  either passes (counted) or fails (goes into the ordinary `failures` list,
  which is repaired or gapped like anything else). There's currently no way
  to reach "zero failures, unverified browser check" with the checks as
  written. That line isn't wrong, but it's dead code today — it's exactly
  the right defense if a future check can legitimately `SKIP`, and I'd leave
  it in rather than remove it, but wanted this named rather than silently
  assumed to be exercised by row 21b the way I first guessed it would be.

## A fourth thing noticed, not changed — flagging rather than guessing

**An app that HELDs during proving (stage two) stays `"status": "APPROVED",
"active": true` in the canonical `registry.json` forever** — indistinguishable
from an app that actually reached BUILT. Confirmed for real: ran the
gap/HELD scenario (row 14) and the new ambiguous-repair HELD, and both times
the canonical registry shows the app as APPROVED/active, with no trace that
it never got past proving. The real, correct verdict (HELD, and why) is
recorded faithfully in `run_ledger.jsonl` and `reports/RUN-nnnn.json` — so
this may be intentional: the canonical registry's job might only ever have
been "this APP-nnn number was successfully assembled and isn't void," with
the ledger being the actual source of truth for build verdicts. But nothing
I have access to says that explicitly, and if anyone treats "APPROVED" in
the canonical registry as "this app works," they'd be wrong. Per Bible rule
4 I'm surfacing this rather than guessing at a fix — voiding on a
proving-stage HELD would be a real behavior change to cross-run bookkeeping,
and I'd want to know what "APPROVED" is supposed to mean there before
touching it.

## What I did not test

- A model call that actually *reaches* the API and returns a candidate fix
  (row 2 and row 20 both prove the honest-failure and gap-guard paths for
  real, but neither exercises a live, successful model round-trip, since I
  don't have a working key to spend on this). If Sam wants that leg proven
  too, I'd need a real key and Sam's go-ahead to spend real API cost on it.
- Deliberately unresponsive child processes (SIGTERM ignored, forcing the
  `proc.kill()` fallback in `run_layer_one`'s cleanup) — the code path exists
  and is simple, but I didn't construct a fixture that ignores SIGTERM to
  drive it for real.
- Concurrent/simultaneous invocations of `build.py` against the same
  directory — the spec describes one build at a time and nothing suggests
  concurrency is in scope, so I didn't build a race-condition fixture for it.

## Files

- `build.py` — the script, fixed and reproven.
- `verification/gen_fixtures.py` — rebuilds the entire real fixture set
  (shelf, templates, choice.json, APPS_LIST.md) from nothing.
- `verification/verify_build.py` — runs all 23 rows plus the 2 extra
  hardening rows for real, prints the actual subprocess output for each, and
  a pass/fail summary.
- `verification/last_run_output.txt` — the full transcript of the run this
  report is based on.


---

# Round 4 — 2026-09-12

# build.py round 4 — what got built from the audit's five decision points

You said "build those five things, test it all." Two of the five were real
engineering and got built and tested for real, below. The other three are
rulings on your own locked standard, not code — I did not guess at those;
here's exactly why, and what I'd need to actually resolve them rather than
invent an answer.

## 1. Built and tested: app-type name canonicalization

New file: `canonical_app_types.py`. One canonical spelling for all 43 app
types (I picked "and" — the Master Spec's own wording, and the one with no
special character for build.py's filename slugifier to mangle), a
`KNOWN_ALIASES` table mapping the 7 "&"-spelled names to their canonical
form, and a `normalize()` that resolves either spelling and *refuses*
(raises, never guesses) anything it doesn't recognize.

Tested for real against the actual 43-item lists, not made-up examples — I
diffed the Master Spec's literal list and TEMPLATE_REFERENCE.md's literal
list against it:

```
Master Spec's 43: 43 exact, 0 normalized via known alias, 0 UNRESOLVED
TEMPLATE_REFERENCE.md's 43: 36 exact, 7 normalized via known alias, 0 UNRESOLVED
  normalized: ['calendar & scheduling', 'file storage & sync', 'form builder & survey',
  'inventory & warehouse', 'meditation & wellbeing', 'quiz & flashcards', 'recipe & meal planning']
Both real 43-item lists resolve cleanly to the same 43 canonical names.
```

This is a one-file decision. If you want "&" instead of "and," change
`CANONICAL_APP_TYPES` in that one file and every future consumer inherits it
— nothing else needs touching.

## 2. Built and tested: the generic compute-capability check generator

This was the real blocker the audit flagged: `build_checks()` only knew how
to test the 9 specific CAP-ids invented for build.py's own proof fixture.
Every one of the 43 real apps would have hit `BROKEN incomplete record no
checks defined for this registry` the moment it reached stage two.

**What changed in build.py:** the six hardcoded per-CAP-id blocks (CAP-0002,
0003, 0004, 0006, 0008, 0009) are gone, replaced by one loop that generates a
check for *any* wired capability whose `category` is `"compute"` — driven
entirely by what that capability has already declared on the shelf:

- its route and HTTP method, read statically off its active implementation's
  own module file (an AST read of the `ROUTE`/`METHOD` constants every
  route-module shelf part already declares — never executed, never guessed),
- what counts as a pass, read off the CAP record's own
  `data_shape.output.fields` — the same field list `match_contract()` already
  trusts for contract matching.

A capability whose active module declares no `ROUTE`/`METHOD` gets **no
check generated for it** — not a guessed one. That's a deliberate refusal,
tested below, not an oversight.

CAP-0001 (the app's own entry screen) stays hand-written, on purpose — it's
architecturally the host, not a shelf route-module capability, and there's
no declared convention yet for what a UI journey's "it worked" state looks
like on an arbitrary screen. I did not invent one. See "What's still open"
below.

**Proof it actually generalizes** (not just "should," a real run): I added
two brand-new capabilities to the test fixture — Feature Zeta and Feature
Eta — with their own distinct declared output shapes, that `build_checks()`
has never had a line of code written for by name. Plus a third, Feature
Theta, whose module deliberately declares no `ROUTE`/`METHOD`, to prove the
skip path. Fresh run, this session:

```
PASS  row G1  generic compute-check generator: correct checks for two capabilities
it has never seen by id, correct skip (not a guess) for one with no declared route
```

**A real bug this surfaced and I fixed, not routed around:** switching to
checks that trust a capability's *actual* declared `data_shape.output.fields`
(instead of the old hand-picked, incomplete subsets the hardcoded checks used
— e.g. the old alpha check only ever verified `ok`/`value`, silently
ignoring that CAP-0002 itself declares a third field, `source`) exposed that
four of the fixture's own "fixed" implementations were fixtures that
*declared* a field their real response never actually returned — alpha
(`source`), the regression-trap capability (`trap`), delta (`config`), and
epsilon (`timeout`). That's a genuine, previously-invisible shelf-data
inconsistency: a capability's own record disagreeing with what its own code
produces, hidden by checks that never verified the full declared contract.
I fixed the four route modules to actually return what their own CAP record
already claimed, rather than loosening the generic checker to tolerate the
mismatch — loosening it would have quietly reintroduced the exact "declared
contract nobody actually checks" gap this whole change exists to close.

**Full regression, fresh, this session, after the fix:**

```
27/27 pass
```

All 26 of the original rows (including the three that broke immediately
after the change — 15, 19, 21a, all for this exact reason) plus the new
genericity row, rerun clean from a freshly regenerated fixture set.

### What's still open in check generation — flagged, not guessed

- **UI journeys beyond CAP-0001.** A generic "click the declared button, then
  verify the declared thing happened" check needs a declared success signal
  — which selector or text proves the action worked — and nothing in the
  current schema states one. I'd propose adding an optional
  `success_indicator` (a selector + expected-text pair) to an interface
  slot's declaration, generated the same way `expected_contract` already is,
  but that's a schema addition and I'm naming it as a proposal for you to
  approve, not something I added silently.
- **A "data" category capability beyond CAP-0001's own `/api/items`.** The
  shelf's route-module convention today is one `ROUTE`/`METHOD` pair per
  module file — fine for a single-method "compute" capability, but a real
  CRUD capability needs at least GET (list) and POST (create) on one
  resource. Extending the convention to multiple routes per module (or one
  module per method) is a real design choice about the shelf's own module
  contract, not something to invent inside a check generator.

## 3–5. Not built — these are rulings on your own locked standard, not code

You asked me to build and test "those five things." Three of the five —
the authority-order conflict, the readiness-state conflict, and the still-
open NUMBERING/Template Standard held decisions — aren't things I can build.
They're decisions the project's own rule (echoed in build.py itself: *"if
something is unknown, do not guess... surface it"*) reserves for you, and in
two of the three cases I don't have the actual documents in front of me to
rule on responsibly — only summaries. Guessing at a numbering or authority
format that's meant to be permanent is a worse outcome than asking. Here's
where each one actually stands, with my recommendation where I have enough
to make one, so you only need to say yes or pick:

- **Authority order (Master Spec §2 vs. your locked order).** My
  recommendation: your own order wins — Bible → build.py's own spec
  (`BUILD_PY_SPEC_v1.md`, which you personally decided on 2026-09-11 should
  supersede the old chain/layer split) → NUMBERING → Template Standard — and
  the Master Spec's citations of "Build Chain Specification," "Template
  Build Guide," and "Harvest Specification" get treated as references to
  whichever of your four real documents actually covers that ground, not as
  separate documents to go find or write. Say yes and this is settled;
  say no and tell me which of those three names points at something real
  that I haven't seen.
- **Readiness states (Master Spec §18's 12-value enum vs. build.py's proven
  §6.2 five-value lifecycle + void).** My recommendation: keep build.py's
  states as the source of truth — you already ruled on this exact vocabulary
  round 3 ("candidate until proven"), and it's tested. If you want the Master
  Spec's richer vocabulary visible somewhere (e.g. in the per-app build
  report, for a human reading the library's status), that can be a
  *display-layer* mapping on top of the real §6.2 status, not a rewrite of
  what build.py itself tracks. Say yes and I'd build that mapping next; say
  no and tell me what you actually want build.py's own state-writing to do
  differently.
- **The still-open H1–H5 (NUMBERING.md) and H-T1–H-T6 (Template Standard)
  held decisions.** I only have summaries of these in memory, not the actual
  documents with their full option text. Ruling on them from a summary would
  be exactly the kind of guess this whole project's standard exists to
  prevent — these are permanent, non-reusable format decisions. If you want
  these resolved, the fastest path is you ruling on them directly (you've
  done this quickly before, one line each) or attaching the actual documents
  so I can lay out the real options rather than my memory of them.

## Files in this delivery

- `build.py` — round 4: generic compute-check generator, everything else
  unchanged from round 3 (still `grep -i anthropic build.py` clean, still
  nothing touched outside `build_checks()`/its new helper and the one call
  site that now passes `app_dir` through).
- `canonical_app_types.py` — the 43-name canonicalization, tested above.
- `verification/` — `gen_fixtures.py` (+3 new capabilities proving
  genericity, +4 real fixture bugs fixed), `verify_build.py` (+row G1, one
  check-id reference updated to match the new numbering), `README.md`,
  `last_run_output.txt` (this session's real 27/27 transcript).

# Round 5 — 2026-09-12

Sam's follow-up to round 4: "Can you finish the other three now, please?" — the three items
round 4 explicitly left undone (build+test, but not resolve): H-T3 (the contract-matching
strictness question), the readiness-state translation, and the authority-order/held-decisions
rulings. All three are finished this round.

## H-T3 — implemented in `match_contract()`, not just ruled on

Loosened two of the twelve contract axes from exact equality to a **directional subset match**:

- `nullable_fields` — a capability may declare a field nullable only if the caller already
  expects it nullable (`cap_nullable ⊆ exp_nullable`); a capability being *stricter* (fewer
  nullable fields than the caller allows) is safe and now binds. Being *looser* than the caller
  expects still HELDs.
- `security_constraints` — every constraint key:value the caller requires must be present and
  equal on the capability; the capability may declare *additional* constraints the caller didn't
  ask for. A capability missing a required constraint still HELDs.

The other five previously-exact-equality axes (`input_types`, `output_types`, `permissions`,
`requires_auth`, `side_effects`) stay exact — none of them have a defensible "safe direction" the
way nullability and security constraints do (e.g. a permission the caller didn't ask for is not
obviously safe to grant silently).

Proven with two new real fixtures, not just asserted:

- **CAP-0013 (Feature Iota) / row G2** — declares `nullable: ["iota_value"]` and
  `security_constraints: {"encrypted_at_rest": true}`; its slot's `expected_contract` requires
  the broader `nullable_fields: ["ok", "iota_value"]` and the same security constraint. Under the
  *old* exact-equality rule this would have failed to bind (`["ok","iota_value"] != ["iota_value"]`
  is a real mismatch under `==`). Under the new subset rule it binds correctly — this is the
  positive case the whole change exists for.
- **CAP-0014 (Feature Kappa Underdeclared) / row G3** — declares no security constraints at all;
  its slot requires `{"encrypted_at_rest": true}`. Correctly still HELDs — proving the loosening
  is directional, not "anything goes."

First run of row G2 actually failed — my own fixture had the nullable-subset check backwards
(the slot's `expected_contract` was narrower than the capability's declared nullable set, which
correctly HELDs under the new rule, but wasn't testing the case I meant to prove). Fixed the
fixture, not the rule, and reran: 29/29.

## Readiness states — `readiness_and_library.py`, built and tested against real build.py output

Master Spec Section 18's 12-value readiness enum (`REFERENCE_ONLY` ... `READY`) is now a
**display-layer translation** on top of build.py's own proven §6.2 states, per the recommendation
Sam approved round 4 — build.py's own status vocabulary is untouched. Two functions:

- `compute_readiness(project_dir, app_type, app_id=None)` — reads the template file, the shelf
  (capability binding), the canonical registry, `run_ledger.jsonl`, and `reports/` — never invents
  a state it can't support from what's actually on disk.
- `promote_to_library(project_dir, app_id)` — the one genuinely new behavior: copies a proven
  (canonical status `active`) app's build directory plus its evidence run reports into
  `library/<app_id>/`, refusing anything not already `active`. This is Section 19's actual gap
  (no library/ promotion step exists anywhere else in this package).
- `compute_readiness_with_library()` — extends the above to `LIBRARY_STORED`/`READY`.

**A real bug found and fixed while building this, not glossed over.** `compute_readiness()`'s
first draft assumed every app-tagged run outcome lands in `run_ledger.jsonl` as an `"outcome"`
record. Reading `stage2_prove()`/`run_layer_two()`/`run_layer_three()` directly (not assumed) shows
that's only true for four of its exit paths (BUILT, regression, restart ceiling, no/failed browser
check with zero other failures) — the **loop guard**, **repeated gap**, and **layer-three-
disabled/exhausted-candidates HELD** exits all raise without ever writing one. Confirmed for real:
running the draft against `row17_loop_guard` and `row21b_browser_check_fails` reported
`START_FAILED` for both — wrong; both are real check failures (a loop-guard-stuck check and a
failing browser journey, respectively), not a health-check-never-returned case.

Fixed properly, not patched around: `run_layer_one()`'s failure records now carry an `is_browser`
field (an additive, non-behavior-changing change to build.py itself — confirmed by rerunning the
full 27-row round-4 suite unchanged afterward: 27/27, then 29/29 with H-T3's two new rows added).
`reports/RUN-*.json` is written *unconditionally* by `run_layer_one()` for every run that gets
checks defined, regardless of what `stage2_prove()` does with the result afterward — so
`compute_readiness()` now falls back to the latest report file (excluding any run already claimed
by a *different* app's own outcome record, the one cross-app safety this ledger schema supports
without guessing) whenever no ledger outcome exists, and uses the new `is_browser` field to
correctly distinguish `BROWSER_TEST_FAILED` from `RUNTIME_FAILED` either way. True `START_FAILED`
(health check never returns) is now correctly distinguished by the complete *absence* of even a
report file — confirmed by reading `run_layer_one()`: it raises `Broken("app did not start")`
before the report dict is ever built, so neither a ledger outcome nor a `reports/RUN-*.json` exists
for that specific failure.

**Also flagged, not silently decided:** the Master Spec lists `TEMPLATE_COMPLETE` as its own state
between `HARVESTED` and `CAPABILITIES_UNBOUND`/`CAPABILITIES_READY`. In this data model a
template's `required_capabilities` and each slot's `target_capability` are already part of the
accepted template record, so the moment a template is `accepted`, capability binding is already
computable in the same instant — there is no on-disk state where a template is complete but
binding is still unknown. `compute_readiness()` therefore reports the furthest state it can
actually determine rather than pausing at `TEMPLATE_COMPLETE`. Documented in the code as a real
design choice, not an omission — if Sam's intent is a genuinely separate, persisted milestone,
that needs its own on-disk marker this file doesn't invent.

New test file `verification/test_readiness.py` — a proving table, not ad-hoc manual runs — checks
`compute_readiness()` against 13 real fixture rows spanning `CAPABILITIES_UNBOUND` through
`PROVEN`, plus `promote_to_library()`'s accept/refuse paths and the `PROVEN → LIBRARY_STORED →
READY` promotion sequence against a real `BUILT` app, run against the real evidence
`reports/RUN-0001.json` it copies. 20/20 pass. Rerun anytime with:

```
cd verification && python3 gen_fixtures.py && python3 verify_build.py && python3 test_readiness.py
```

Full clean-room rerun this round (fresh `work/`, fresh fixtures, nothing left over from round 4):
**29/29** build-chain proving rows + **20/20** readiness/library checks, all real subprocess runs
against a real server and real browser — transcript in `verification/last_run_output.txt`.

## Authority order + the held decisions — ruled on, not guessed

Written up in full in `RULINGS_ROUND5.md`, delivered alongside this file. Summary:

- **Authority order**: not actually in conflict — Sam's real 4-document order (Bible →
  `BUILD_PY_SPEC_v1.md` → `NUMBERING.md` → `TEMPLATE_STANDARD.md`) maps cleanly onto the Master
  Spec's 7-slot order in the same relative positions. The two Master-Spec-named documents with no
  real-document match ("Harvest Specification", "Constitution and Governance Files") are flagged as
  not-on-record rather than silently substituted or assumed absent.
- **H1** — cite `BUILD_PY_SPEC_v1.md`, not the Bible, for "a repair never resumes."
- **H2** — retire `watch.py`; superseded by `build.py`'s own `stage2_prove()`.
- **H3** — moot given H2.
- **H4** — **left open.** What the NOT-/RPT-/WFL- prefixes were proposed to number is genuinely
  unresolvable from this session's memory record; ruling on it would be a guess, which is exactly
  what this project's own standard forbids. Needs the original proposal.
- **H5** — fold `UNPROVEN` in; build.py's real, tested checks use only PASS/FAIL/SKIP.
- **H-T1** — `TPL-nnnn`, 4 digits (matches CAP-/GAP-'s convention).
- **H-T2** — approved as-is; `TEMPLATE_REFERENCE.md` already proves the definition works, 43/43.
- **H-T3** — implemented in code this round (above).
- **H-T4** — `templates/` stays a peer of `shelf/`.
- **H-T5** — yes, a template can be approved with unbound capabilities; design-lock and
  capability-binding are separate concerns, and build.py's own assembly step already refuses to
  build an app whose capabilities aren't bound regardless (proven again this round,
  `row06_missing_shelf_cap`).
- **H-T6** — Q-variation trigger list given in full in `RULINGS_ROUND5.md`.

## Files in this delivery

- `build.py` — round 5: one additive change, `is_browser` on `run_layer_one()`'s failure records
  (see above); the H-T3 subset-match change to `match_contract()`. Everything else unchanged from
  round 4. Still `grep -i anthropic build.py` clean.
- `canonical_app_types.py` — unchanged from round 4.
- `readiness_and_library.py` — new this round: `compute_readiness()`, `promote_to_library()`,
  `compute_readiness_with_library()`.
- `RULINGS_ROUND5.md` — the authority-order and held-decision rulings, in full.
- `verification/` — `gen_fixtures.py` (+CAP-0013/0014, +2 templates), `verify_build.py` (+rows
  G2/G3), `test_readiness.py` (new — the readiness/library proving table), `README.md`,
  `last_run_output.txt` (this session's real 29/29 + 20/20 transcript).

# Round 6 — 2026-09-12

Sam's follow-up: "You need a single end-to-end proving test. So not just unit tests, the whole
startup script, every stage, real handoffs... we need one clear canonical spec agreed. Then a
cross-reference of each stage's inputs and outputs. And then a clean room run, unzip the package
fresh, run the real script, and prove each handoff works." Four deliverables, in the order asked.

## 1. One script, all the way through — `readiness_and_library.py` folded into `build.py`

Round 5 left readiness/library as a second file, which quietly broke Sam's own 2026-09-11
architecture decision ("why can't it just be one script"). Fixed properly rather than left as a
second script alongside build.py: `compute_readiness()`, `promote_to_library()`,
`compute_readiness_with_library()`, and their helpers now live inside `build.py` itself as **stage
three**, reusing build.py's own real functions where they already existed (`_cap_is_bound()` now
calls the exact same `read_shelf_cap()`/`cap_is_usable()`/`active_impl_for()` that Stage 1's real
assembly uses, instead of a parallel reimplementation — so "readiness says bound" can never drift
from "assembly would actually succeed"). `main()` now calls `stage3_readiness_and_promote(app_id)`
after Stage 2, **on every path** (BUILT, HELD, BROKEN) — every real run now ends with a Master-Spec-
vocabulary readiness line, not just successful ones. Added `python3 build.py --readiness <app_type>
[app_id]` and `python3 build.py --promote <app_id>` for standalone queries against files a
completed run already left behind.

This changed build.py's own printed output shape (a `promoted`/`readiness` line now follows `BUILT`
or `BROKEN ...` on every run that got as far as allocating an app_id), which broke several
existing test assertions that checked stdout's *last line* exactly. Found and fixed for real, not
worked around: seven `== "BUILT"`/`!= "BUILT"` assertions became "`BUILT` appears as its own line
somewhere" checks (rows 15/16/22/23/G1/G2/X-sigterm); two `endswith(...)`/exact-last-line BROKEN
assertions (rows 13, 21a) became the same "appears as its own line" form; and row 13's `"FAIL" not
in res.stdout` check was rewritten to check for an actual `FAIL  ` check-result line, because the
new readiness state name `START_FAILED` itself contains the substring "FAIL" and was tripping a
false failure — a genuine collision between a bare substring check and the new (correct) readiness
vocabulary, not a build.py bug. Full suite rerun clean after each fix in turn: 29/29 + 20/20.

`test_readiness.py` itself was rewritten to invoke `build.py --readiness`/`--promote` as **real
subprocesses with `cwd=<project dir>`**, matching exactly how a human runs it and how build.py's
own config-block paths are meant to be resolved (against the process's cwd, the same convention
every other part of build.py already uses) — stronger proof than the round 5 version's in-process
function calls, and it surfaced that auto-promotion now happens inside the same invocation that
reaches BUILT, so three of its expected readiness states moved from `PROVEN` to `READY` (correctly
— that's the new, better behavior, not a test weakening).

## 2. One canonical spec — `CANONICAL_SPEC.md`

Part A is the Master Build-to-Library Specification exactly as Sam supplied it (734 lines,
verbatim, never rewritten — same don't-touch discipline as an approved template). Part B is every
resolution since, laid against Part A section by section: the authority-order mapping (§2), the
readiness-state implementation and its one honest narrowing (§18 — TEMPLATE_COMPLETE isn't
independently observable in this data model, explained why), the library-admission implementation
(§19), what's still genuinely unbuilt (§20/21 — registries/reports export layer), all eleven
resolved held decisions plus the one left open (H4), the one-script architecture note, and an
explicit scope boundary: harvesting and template generation live in a separate prior session and
aren't reconstructed here from memory.

## 3. Stage cross-reference — `STAGE_CROSS_REFERENCE.md`

Every real stage build.py implements (assemble / prove / readiness+library), file-and-field exact,
grounded in the actual source lines (function names + line numbers given), not summarized from
memory. Each stage's table names exactly what it reads and exactly what it writes, and the
handoff into the next stage is stated as either "proven by construction" (Stage 1→2 passes Python
objects directly, no serialize/re-read to drift) or explains precisely why it's a deliberate
disk re-read instead (Stage 2→3, so `--readiness`/`--promote` work standalone later). The one real
gap found in round 5 (some `run_ledger.jsonl` exit paths write no outcome record) is documented
in the table itself, not hidden in a changelog — a cross-reference that hides its own sharp edge
isn't actually proving the handoffs.

## 4. Clean-room run — `END_TO_END_PROOF.md`

Completely fresh unzip, isolated directory, one config edit (`ALLOW_LAYER3` off — this scenario has
no failure to repair, and Bible rule 13 correctly refuses to run at all with empty layer-three
credentials, which is real behavior, not a workaround), then `python3 build.py` — the real script,
run once, no harness, no in-process shortcuts. One command, one process: assemble → prove (real
Flask subprocess, real HTTP checks, real Playwright browser check) → `BUILT` → auto-promoted →
`readiness  READY`. Every claimed handoff then verified by inspecting the actual files each stage
left behind: `app.json` (what Stage 2 used to start the app), `reports/RUN-0001.json` (Stage 2's
unconditional write), `run_ledger.jsonl` + canonical `registry.json`'s `candidate → active` flip
(what gates Stage 3's promotion), `library/APP-001/PROMOTED.json` naming the exact evidence run it
copied. Two further real checks in the same clean room: a standalone `--readiness` query against
files a finished run already left behind, and a genuine second end-to-end run proving APP-001 is
never reused and APP-002 allocates and proves cleanly alongside it.

**Scope stated plainly, not glossed over**: this proves stages 1–3, everything build.py itself
implements. It does not prove harvest → template-generation, because `harvest.py`/`run.py`/
`make_templates.py` are not part of this session's working files (built or spec'd in a separate
prior session, "One-Click Library") — reconstructing them from memory and presenting that as real
code would violate the standing rule against ever doing that. If Sam wants that included in a
genuine end-to-end proof, those source files need to be supplied, or `harvest.py` needs real
GitHub/Gemini credentials to build and test against for real.

## Files in this delivery

- `build.py` — round 6: readiness/library folded in as stage three (see above); `--readiness`/
  `--promote` CLI flags added. `grep -i anthropic build.py` still clean.
- `canonical_app_types.py` — unchanged from round 4.
- `CANONICAL_SPEC.md` — the one locked spec Sam asked for (Part A verbatim + Part B resolutions).
- `STAGE_CROSS_REFERENCE.md` — the stage input/output table.
- `END_TO_END_PROOF.md` — the clean-room run + handoff evidence.
- `RULINGS_ROUND5.md` — unchanged, still the full reasoning behind every held decision.
- `verification/` — `gen_fixtures.py`, `verify_build.py` (7 assertions fixed for the new stage-three
  output shape, 1 fixed for a substring collision with the new readiness vocabulary), `test_readiness.py`
  (rewritten to real-subprocess `--readiness`/`--promote` calls), `README.md`, `last_run_output.txt`
  (this session's real 29/29 + 20/20 transcript).

## Round 7 — 2026-09-12

Sam, directly: **"Rules no fake no synthetic ever so what do you mean yes or no? Can you pick one
and test it?"** — called out, correctly, that the previous turn's "yes and no" answer to "is the
system built, full proof, ready to go, run this" was a hedge, against his own standing rule (no
hedging, yes/no where a yes/no exists). The honest yes/no: **yes**, build.py's own machinery
(stages 1–3, every proving-table row) is real and proven; **no**, nothing had yet been built for
any of Sam's real 43 catalogue app types — every prior round's proof used the CAP-0001 fixture, an
invented "item list" toy app, never one of the 43 real ones. That gap is closed this round.

**What was built and proven, for real, no synthesis**: "todo list" — item #1, verbatim, of
`canonical_app_types.py`'s real list — sourced from the real, canonical TodoMVC functional
specification (fetched live, read in full: `https://github.com/tastejs/todomvc/blob/master/app-spec.md`,
not reconstructed from memory). Full detail, full transcripts, the real restart-survives-data
proof, and the exact reasoning behind every fix is in the new `REAL_APP_PROOF.md` — this section is
the summary.

**The real gap this surfaced** (found by reading build_checks()'s own source, not guessed):
`build_checks()`'s host-page/browser-journey checks (CHK-001/CHK-002/CHK-020) were gated on the
literal string `"CAP-0001"`, and the round-4 generic compute-capability check generator — proven
only against zero-input GET capabilities until now — called every route with no body and accepted
only a literal `200`, both wrong for real `POST` actions that need real input and correctly answer
`201 Created`. None of this was worked around by warping the real app to fit the old checks (no
renamed fields, no fake "Add" button where real TodoMVC has none, no downgrading a correct `201` to
`200`) — every one of the four was a real, generalized fix to `build.py` itself:

1. `_detect_host_capability_id()` — new. Finds the host module from a real fact already on disk
   (which capability's active IMPL entrypoint is the exact module `app.json`'s own `start` command
   launches), never from a hardcoded id. Requires real evidence of a UI journey — wired to a button
   (the old fixture's own pattern) or a template-declared `primary_journey` (new, optional, additive
   field — real selectors, real typed input, a real keypress or click, whichever the real UI uses).
2. CHK-001/CHK-020 key off the detected host id, not a literal string; CHK-020 drives the declared
   journey when present and falls back to the exact original hardcoded CAP-0001 behavior, unchanged,
   when it isn't — every existing proven row keeps its exact original behavior and claim text.
3. CHK-002 stays scoped to exactly `host_cap_id == "CAP-0001"` — it tests one fixture's one specific
   legacy baked-in-route pattern (create-item baked directly into the host module, bypassing the
   shelf route-module convention — flagged as a design smell in round 4's own docstring, not copied
   into the real app). A host that doesn't replicate that pattern correctly gets no such check.
4. The generic compute-check generator now builds a real request body from a capability's own
   declared `data_shape.input.required` fields (a deterministic, generic probe per field — an
   "id"-named field gets `1`, anything else gets a short descriptive string — the same kind of
   arbitrary-but-real example data the original fixture already used, `"milk"`, never an invented
   capability or requirement), and accepts any `2xx` status instead of only the literal `200`.

**The real build**: one host Flask module (CAP-0100) plus seven real, separate shelf capabilities —
list/create/toggle/edit/delete/toggle-all/clear-completed todos (CAP-0101–0107), each its own real
`route.py`, each covered by the existing, unmodified round-4 generic check loop — a real HTML/CSS/JS
frontend that actually implements the spec (hover-reveal delete, double-click-to-edit with
autofocus/blur-save/Escape-cancel, pluralized counter, hash-based `#/`/`#/active`/`#/completed`
filtering), and a real JSON-file-backed store. Filtering was deliberately left server-less, because
the real spec places it at the client/model level — adding a server endpoint for it would have been
inventing a requirement the real spec doesn't have.

**Proven, real, clean room** (`/tmp/real_app_cleanroom/proof/`, freshly assembled, no pre-existing
`builds/`/`library/`): `python3 build.py` → 9/9 real checks pass (one host-page render, six real
HTTP round trips against six real route modules, one real Playwright session that typed real text
and pressed a real Enter key into the real `#new-todo` input) → `BUILT` → promoted → `READY`, exit
code 0. Separately, a real restart-survives-data proof (Master Spec §16 requirement #10): the
assembled app was started, queried, cleanly `SIGTERM`-ed, and a second, brand-new process started
against the same real data directory — it read back exactly the same real todo the first process
wrote.

**Zero regression**: the full existing suite was rerun after every fix above, not just at the end —
29/29 (`verify_build.py`) + 20/20 (`test_readiness.py`), unchanged.

**What this does not claim**: one of the 43 real app types was picked and proven, per the direct
instruction ("can you pick one and test it") — not all 43. The generic check generator's new
input-probing convention is a real, working first version proven against six real capabilities it
had never seen before, not a claim that every possible real input shape is now handled — a future
real app with a different required-input shape (a boolean, a number that isn't an id) is the next
honest thing to prove it against, not a case to guess past now.

**Follow-up, same round**: Sam asked, correctly, how this gets tested to make sure it will actually
run on his own laptop start to finish. Answer given plainly: proven twice in this session's own
sandbox, not yet on his machine, since this session has no link to it. What real-machine readiness
actually needs — Python 3, `pip install flask playwright`, `playwright install chromium` — was
stated without guessing, and a real gap was found and fixed by deliberately breaking it: a missing
dependency used to crash the real assembled app silently, with `run_layer_one()` reporting only a
bare `BROKEN app did not start` and discarding the process's own real stdout/stderr unread. Fixed
in `build.py` (`_wait_for_health()` now watches the real subprocess's own exit; the failure path now
reads and surfaces its real captured output) and proven by actually breaking a real import and
running the real build — the real `ModuleNotFoundError` now prints directly. Reproven against the
full 29/29 + 20/20 suite (row 13's exact original message is preserved unchanged for the
no-real-output case). Offered Sam the real test: link this session to his laptop and run it there
directly, or he pastes back the real output of the three commands above.

## Files added this round

- `REAL_APP_PROOF.md` — the full real-app proof: the gap found, the fix, the real build, every real
  transcript (build run, restart-survives-data), and the honest scope statement.
- `verification/gen_real_todo_app.py` — the real, rerunnable generator for the real todo-list app
  (shelf capabilities, real Flask route modules, real HTML/CSS/JS frontend, real template). Not
  shipped with its generated output (`real_todo_proof/`), same convention as `gen_fixtures.py`.
- `build.py` — updated: `_detect_host_capability_id()`, generalized CHK-001/CHK-020, the generic
  compute-check generator's real-input-probing + any-2xx acceptance, and an optional, additive
  `primary_journey` template field threaded through `app.json`. `grep -i anthropic build.py` clean;
  no duplicate definitions; compiles clean.
