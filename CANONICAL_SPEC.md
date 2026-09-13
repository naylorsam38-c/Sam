# CANONICAL BUILD-TO-LIBRARY SPECIFICATION — locked, 2026-09-12

This is the single spec Sam asked for after round 5: the Master Build-to-Library Specification
as he supplied it, unedited, plus every open decision it raised now resolved and layered on top as
an explicit amendment — nothing in Part A is rewritten (the same don't-touch discipline that
governs an approved template applies to a locked spec), and every place Part B changes or narrows
something Part A says is called out by section number, not left implicit.

**Read order: Part A is the spec. Part B is what's since been decided about it. Where they seem to
disagree, Part B wins — it is later and it is Sam's own rulings (RULINGS_ROUND5.md) plus what
build.py actually, provably does today.**

⸻

# PART A — the Master Build-to-Library Specification (verbatim, as supplied 2026-09-12)

COMMAND DESK — MASTER BUILD-TO-LIBRARY SPECIFICATION

Status: Planning and execution specification
Purpose: Define the complete process that takes the existing 43-app reference catalogue and produces 43 real, working, browser-tested applications in the app library.

⸻

1. OBJECTIVE

Produce a library containing 43 working app types.

An app may be marked READY only when:

1. Its app type is registered.
2. Its template is complete.
3. Every required capability is bound to a real approved capability.
4. Every required implementation exists.
5. The app builds successfully.
6. The app starts successfully.
7. The app passes real browser tests.
8. Its evidence is recorded.
9. It is stored in the library.
10. Its registry status is updated to READY.

The system must not claim that an app is working merely because:

* a template exists;
* a capability is described;
* a fixture passes;
* a build script completes;
* a simulated response is returned;
* a placeholder implementation exists;
* a browser test was skipped.

⸻

2. AUTHORITY ORDER

The execution system must read and obey the existing authority documents in this order:

1. THE BIBLE
2. BUILD CHAIN SPECIFICATION
3. NUMBERING.md
4. TEMPLATE BUILD GUIDE
5. HARVEST SPECIFICATION
6. CONSTITUTION AND GOVERNANCE FILES
7. THIS MASTER BUILD-TO-LIBRARY SPECIFICATION

If two documents conflict:

1. Do not silently choose.
2. Record the conflict.
3. Apply the higher authority.
4. Stop only where the conflict prevents safe execution.
5. Do not rewrite the Locked Goal.

This specification coordinates the build process. It does not replace the existing Constitution, Bible, Build Chain, numbering rules, or template rules.

⸻

3. LOCKED GOAL

The Locked Goal is:

Convert the 43-app reference catalogue into 43 complete, independently working, browser-tested applications and place the proven applications into the app library.

The Locked Goal must not be:

* broadened;
* narrowed;
* replaced;
* reinterpreted;
* silently reduced to a demo;
* declared complete with only reference documents;
* declared complete with only fixtures;
* declared complete with only partial applications.

⸻

4. CURRENT INPUTS

The execution system must inspect the supplied files and existing project before making changes.

Known inputs include:

* the 43-app reference catalogue;
* the existing single-app builder;
* the existing verification scripts;
* the existing governance documents;
* the existing numbering rules;
* the existing template rules;
* the existing capability and implementation shelf, if present;
* the existing app library, if present.

The reference catalogue is not itself the finished application library.

It must be converted into executable templates and then connected to real implementations.

⸻

5. REQUIRED FINAL OUTPUT

The final library must contain 43 registered app units:

APP-001
APP-002
APP-003
...
APP-043

Each app unit must contain:

app/
├── app manifest
├── selected template
├── bound capability list
├── implementation manifest
├── source files
├── configuration
├── database/migrations if required
├── start command
├── health check
├── browser test suite
├── test evidence
├── build report
└── readiness status

The library must also contain:

templates/
capabilities/
implementations/
registries/
browser-tests/
build-reports/
test-evidence/
failure-reports/

⸻

6. COMPLETE PIPELINE

The system must execute the following stages in order.

DISCOVER
→ READ AUTHORITY
→ INVENTORY EXISTING FILES
→ VALIDATE 43 APP TYPES
→ HARVEST CAPABILITIES
→ CREATE TEMPLATES
→ RESOLVE CAPABILITIES
→ IMPLEMENT MISSING CAPABILITIES
→ APPROVE CAPABILITIES
→ BIND TEMPLATES
→ BUILD APPS
→ START APPS
→ RUN REAL BROWSER TESTS
→ REPAIR FAILURES
→ RETEST
→ STORE PROVEN APPS
→ UPDATE LIBRARY
→ PRODUCE FINAL REPORT

No stage may be silently skipped.

⸻

7. STAGE 1 — DISCOVERY

Before building anything, the system must inspect:

* all supplied files;
* all project directories;
* all existing templates;
* all existing CAP records;
* all existing IMPL records;
* all registries;
* all build scripts;
* all test scripts;
* all start commands;
* all database definitions;
* all browser-test definitions;
* all existing app-library entries.

The discovery report must state:

FOUND
MISSING
INCOMPLETE
DUPLICATE
CONFLICTING
UNUSED
BROKEN

The system must not invent files that it has not found.

⸻

8. STAGE 2 — VALIDATE THE 43 APP TYPES

The system must verify that exactly 43 app types are present.

Expected app types:

1. todo list
2. note taking
3. habit tracker
4. calendar and scheduling
5. expense tracker
6. invoicing
7. accounting ledger
8. CRM
9. helpdesk ticketing
10. payroll
11. project management
12. team chat
13. video conferencing
14. email client
15. file storage and sync
16. collaborative document editor
17. spreadsheet
18. form builder and survey
19. e-commerce storefront
20. multi-vendor marketplace
21. auction
22. food delivery
23. ride hailing
24. parcel tracking
25. appointment booking
26. property rental
27. event ticketing
28. restaurant POS
29. inventory and warehouse
30. fleet tracking
31. dating
32. social feed
33. photo sharing
34. short video feed
35. music streaming
36. video streaming
37. podcast
38. fitness tracking
39. meditation and wellbeing
40. language learning
41. online course LMS
42. quiz and flashcards
43. recipe and meal planning

The exact canonical names must follow the existing numbering authority if it differs from the display names above.

The system must report:

EXPECTED: 43
FOUND: [number]
DUPLICATES: [number]
MISSING: [list]
EXTRA: [list]

⸻

9. STAGE 3 — HARVEST

For each app type, use the Harvest Specification.

Harvesting must record actual capabilities found in real comparable applications.

Each capability must be:

* generic;
* lowercase;
* verb plus object;
* independent of brand names;
* tied to a real app behaviour;
* marked required or optional;
* supported by provenance;
* assigned to the correct app type.

The harvest stage must not build the application.

It produces the capability reference set used by the template stage.

⸻

10. STAGE 4 — CREATE COMPLETE TEMPLATES

Every app type must receive one complete numbered template.

Each template must follow the existing template rules exactly.

A template must include the required seven fields defined by the Template Build Guide.

Where required by the form rules, it must also include:

tpl_id
app_type
exemplars

Every template must define:

* app identity;
* interface slots;
* required capabilities;
* optional capabilities;
* target capabilities;
* contracts;
* data requirements;
* event requirements;
* API requirements;
* start command;
* health check;
* browser test entry point;
* expected output;
* library destination.

A template is not complete if it contains only a description or capability list.

⸻

11. STAGE 5 — CAPABILITY RESOLUTION

For every template capability:

1. Search the existing capability shelf.
2. Match by canonical capability identity.
3. Verify the CAP number.
4. Verify the implementation number.
5. Verify approval status.
6. Verify active status.
7. Verify contract compatibility.
8. Verify test coverage.
9. Bind the template to the approved CAP.

A capability must remain:

UNBOUND

until a real approved capability and implementation are verified.

The system must not fake a binding.

The system must not silently substitute an unrelated capability.

The system must not treat a description as an implementation.

⸻

12. STAGE 6 — MISSING CAPABILITIES

If a required capability has no valid implementation, create a capability work item.

Each work item must state:

app_type
capability
required_or_optional
missing_CAP
missing_IMPL
required_contract
required_files
required_tests
blocking_apps
status

Missing capability work must be handled in this order:

1. Reuse an existing compatible implementation.
2. Adapt an existing implementation only if permitted by the authority documents.
3. Create a new numbered CAP.
4. Create its implementation.
5. Add tests.
6. Obtain required approval.
7. Activate it on the shelf.
8. Bind it to the relevant templates.

No app may be marked READY while a required capability remains unresolved.

Optional capabilities may remain unbound only where the template explicitly permits that.

⸻

13. STAGE 7 — CONTRACT VALIDATION

Every capability and implementation must be checked against the required contract axes.

The contract validator must check:

* identity;
* purpose;
* inputs;
* outputs;
* state;
* errors;
* permissions;
* persistence;
* events;
* UI interaction;
* integration boundaries;
* tests.

The system must reject:

* missing contract fields;
* ambiguous capability names;
* unapproved implementations;
* mismatched input/output contracts;
* missing permissions;
* missing persistence rules;
* missing error behaviour;
* missing tests.

⸻

14. STAGE 8 — BUILD ONE APP

The existing single-app builder must remain the canonical builder unless the authority documents require a replacement.

For each app:

1. Create its build choice.
2. Select its canonical template.
3. Resolve all required CAPs.
4. Resolve all required implementations.
5. Validate the complete build manifest.
6. Assemble the app.
7. Generate configuration.
8. Generate database structures if required.
9. Generate API routes if required.
10. Generate the interface.
11. Generate the test entry point.
12. Produce a build report.

The builder must fail loudly if:

* the app type is unknown;
* the template is missing;
* a required CAP is unbound;
* an implementation is missing;
* an implementation is not approved;
* a contract is invalid;
* a required file is absent;
* the start command is absent;
* the health check is absent.

⸻

15. STAGE 9 — BUILD ALL 43

Create a separate orchestration process around the existing single-app builder.

The orchestrator must process every app type independently.

Pseudocode:

for app_type in canonical_43_app_types:
    load authority documents
    load app template
    validate template
    resolve required capabilities
    validate implementations
    create isolated build workspace
    run the existing single-app builder
    capture stdout
    capture stderr
    capture exit code
    save build report
    if build failed:
        record failure
        continue to next app
    start app
    wait for health check
    if health check failed:
        record failure
        stop app
        continue to next app
    run real browser tests
    save browser evidence
    if browser tests failed:
        record failure
        stop app
        continue to next app
    mark app as PROVEN
    store app in library
    update registry

The orchestrator must not stop after the first app.

It must not overwrite one app with another.

Every app must have an isolated workspace and unique identifier.

⸻

16. STAGE 10 — REAL RUNTIME TESTING

Runtime testing must use a real running application.

The following do not count as runtime proof:

* fixture generation;
* static file inspection;
* unit tests alone;
* mocked browser responses;
* canned envelopes;
* simulation mode;
* fake health responses;
* checking that a build directory exists.

Each app must have browser tests that verify its actual required workflows.

Minimum browser test categories:

1. app loads;
2. main interface renders;
3. user can perform the primary action;
4. data is created or changed;
5. data persists after reload;
6. required navigation works;
7. required error handling works;
8. required permissions are respected;
9. required integrations work or are explicitly marked unavailable;
10. app can be closed and restarted without corrupting data.

Tests must use the actual generated app.

⸻

17. STAGE 11 — FAILURE REPAIR

Every failure must create a failure record.

Required fields:

failure_id
app_id
app_type
stage
command
exit_code
error_output
expected_result
actual_result
probable_cause
repair_required
repair_status
retest_status

Repair rules:

1. Do not hide failures.
2. Do not downgrade required features to optional.
3. Do not replace real tests with simulations.
4. Do not mark an app READY after a failed test.
5. Retest after every repair.
6. Preserve the original failure evidence.
7. Record the repair and retest result.

⸻

18. STAGE 12 — APP READINESS STATES

Every app must have one of these states:

REFERENCE_ONLY
HARVESTED
TEMPLATE_COMPLETE
CAPABILITIES_UNBOUND
CAPABILITIES_READY
BUILD_FAILED
BUILT
START_FAILED
RUNTIME_FAILED
BROWSER_TEST_FAILED
PROVEN
LIBRARY_STORED
READY

Only this state may be presented as a working library app:

READY

BUILT does not mean working.

PROVEN does not mean stored.

LIBRARY_STORED does not mean READY unless all evidence is present.

⸻

19. LIBRARY ADMISSION RULE

An app may enter the working library only when all conditions are true:

template_complete = true
required_capabilities_bound = true
required_implementations_present = true
contracts_valid = true
build_passed = true
start_passed = true
health_check_passed = true
browser_tests_passed = true
evidence_saved = true
registry_updated = true

If any condition is false:

library_status = NOT_READY

The library must distinguish:

reference catalogue
in-progress builds
failed builds
proven apps
ready apps

⸻

20. REQUIRED REGISTRIES

Maintain these registries:

app_registry.json
template_registry.json
capability_registry.json
implementation_registry.json
build_registry.json
test_registry.json
library_registry.json

Every registry entry must include:

* stable identifier;
* name;
* status;
* version;
* source;
* dependencies;
* owner;
* timestamps;
* evidence references;
* failure references where applicable.

⸻

21. REQUIRED REPORTS

The final process must produce:

discovery_report.md
authority_validation_report.md
app_type_validation_report.md
harvest_report.md
template_completion_report.md
capability_resolution_report.md
implementation_report.md
build_all_report.md
runtime_test_report.md
browser_test_report.md
failure_repair_report.md
library_admission_report.md
final_43_app_status.md

The final status report must show every app:

App	Template	CAPs	Build	Start	Browser Test	Library	Status

No aggregate “43 complete” statement is permitted without 43 individual records.

⸻

22. COMPLETION CONDITION

The project is complete only when:

43 app types found
43 templates complete
0 required capabilities unbound
0 required implementations missing
43 builds passed
43 apps started
43 health checks passed
43 browser test suites passed
43 evidence packages saved
43 apps stored in the library
43 registry entries marked READY

If the result is lower than 43, the final report must state the exact number and list every blocker.

⸻

23. NON-NEGOTIABLE RULES

The execution system must not:

* redesign the Locked Goal;
* remove required capabilities to make a build pass;
* invent CAP numbers;
* invent implementation numbers;
* mark placeholders as working;
* treat fixture tests as browser proof;
* use simulation as production validation;
* skip failed apps;
* silently substitute another app type;
* overwrite existing apps without versioning;
* claim all 43 are ready without individual evidence;
* stop after building only one app;
* confuse the reference catalogue with the finished library.

⸻

24. EXECUTION HANDOFF

This specification is a handoff to the build agent or build operator.

The handoff instruction is:

Read all authority documents and inspect all existing files first. Do not begin application construction until the discovery and gap reports are complete. Then execute the full pipeline defined in this specification: validate the 43 app types, create complete templates, resolve or implement required capabilities, bind approved implementations, build every app using the existing builder, start every app, run real browser tests, repair failures, and store only proven applications in the library. Continue until all 43 apps are READY or produce a complete blocker report showing exactly what prevents completion. Do not claim completion without 43 individual evidence packages.

⸻

25. FINAL SUCCESS RESULT

The desired final result is:

43 real app types
43 complete templates
real capability bindings
real implementations
43 successful builds
43 real running apps
43 passing browser test suites
43 evidence packages
43 READY library entries

That is the definition of the finished 43-app working library.
⸻

# PART B — resolutions (round 5/6, 2026-09-12)

Every open item Part A raised or implied, resolved. Full reasoning for each is in
`RULINGS_ROUND5.md`; this section states the resolution and, where it changes what Part A's own
words would otherwise mean, says so plainly.

## B.1 — Section 2 (Authority Order): resolved, not a conflict

Sam's real, locked authority order — Bible → `BUILD_PY_SPEC_v1.md` → `NUMBERING.md` →
`TEMPLATE_STANDARD.md` — maps cleanly onto Part A §2's seven-slot order, in the same relative
positions:

| Part A's slot | Real document |
|---|---|
| 1. THE BIBLE | The Bible |
| 2. BUILD CHAIN SPECIFICATION | `BUILD_PY_SPEC_v1.md` |
| 3. NUMBERING.md | `NUMBERING.md` |
| 4. TEMPLATE BUILD GUIDE | `TEMPLATE_STANDARD.md` |
| 5. HARVEST SPECIFICATION | **N/A — see B.9** |
| 6. CONSTITUTION AND GOVERNANCE FILES | **N/A — see B.9** |
| 7. THIS MASTER SPECIFICATION | Part A itself (correctly last already) |

Slots 5 and 6 were formally closed as N/A in B.9 below, on Sam's explicit instruction, after a third
independent search confirmed the same result this table originally recorded.

## B.2 — Section 18 (App Readiness States): resolved, implemented, proven

Part A's twelve states are implemented, for real, in `build.py` itself (folded in this round —
see B.5) as a **read-only translation layer** over build.py's own proven §6.2 registry vocabulary
(`candidate/approved/active/deprecated/retired/void`), which stays the source of truth build.py
writes. `compute_readiness()`/`compute_readiness_with_library()` return exactly one of Part A's
twelve names; `promote_to_library()` is Section 19's library-admission step, which nothing built
before round 5 provided. See `STAGE_CROSS_REFERENCE.md` for exactly what each state reads to
decide, and `verification/test_readiness.py` for the 13-state, 20-check real proving table.

One narrowing of Part A's own words, stated plainly: **TEMPLATE_COMPLETE is not independently
observable** in this data model. A template's `required_capabilities` and each slot's
`target_capability` are already part of the accepted template record, so the instant a template is
`accepted`, capability binding is already computable — there is no on-disk moment where a template
is complete but binding is still unknown. `compute_readiness()` reports the furthest state it can
actually determine (`CAPABILITIES_UNBOUND`/`CAPABILITIES_READY`) rather than inventing a pause at
`TEMPLATE_COMPLETE`. If Sam's intent is a genuinely separate, persisted milestone, that needs its
own on-disk marker this data model doesn't currently have — flagged, not silently decided.

## B.3 — Section 19 (Library Admission Rule): resolved, implemented, proven

`promote_to_library()` (in `build.py`, round 6) is this section's real implementation. It copies a
build's own proof — `registry.json`, `app.json`, `locators.json`, `modules/`, `skin.json`, and every
`reports/RUN-*.json` whose ledger entry names that app — into `library/<app_id>/`, but only when
build.py's own canonical registry already says that app is `active` (a real BUILT run, meaning
build_passed/start_passed/health_check_passed/browser_tests_passed are already satisfied by
definition of having reached BUILT). It writes a `PROMOTED.json` marker recording when and from
which run, closing `evidence_saved`/`registry_updated`. Auto-invoked at the end of every real build
run that reaches BUILT (round 6) — Section 19's admission rule now runs automatically, not as a
separate manual step.

## B.4 — Sections 20/21 (Registries/Reports): still open, correctly

No change since the original audit: the underlying data (`run_ledger.jsonl`, `reports/RUN-*.json`,
`registry.json`, the shelf's own per-CAP/IMPL files) is real and complete; the seven named registry
files and thirteen named reports Part A asks for are an export/formatting layer nothing has built
yet. Not attempted this round — out of scope for "finish the other three."

## B.5 — the held decisions (H1–H5, H-T1–H-T6): resolved in `RULINGS_ROUND5.md`

All eleven ruled on except **H4** (what the NOT-/RPT-/WFL- prefixes were proposed to number),
which stays genuinely open — unresolvable from this session's memory record, not guessed. H-T3 (the
contract-matching strictness question) is implemented in `match_contract()`, proven by rows G2/G3.
See `RULINGS_ROUND5.md` for the full reasoning behind each.

## B.6 — architecture: build.py is now the one script for stages 1–3 (round 6)

Sam's 2026-09-11 decision ("why can't it just be one script") is now honored all the way through:
round 5 had split readiness/library into a second file (`readiness_and_library.py`); round 6 folds
that into `build.py` itself as stage three, auto-invoked at the end of every run. `build.py` is now
the single script that, given an already-populated shelf and an already-accepted template, takes a
`choice.json` all the way to a `library/<app_id>/READY` app (or to an honestly-classified failure
state) in one real process. See `STAGE_CROSS_REFERENCE.md` for what that does and doesn't cover.

## B.7 — scope boundary: what this canonical spec does NOT yet prove end to end

Stated plainly, not glossed over. `build.py` assumes an already-populated shelf and an
already-accepted template for the app type in `choice.json`. Two stages upstream of that — real
GitHub/Gemini-driven harvesting (`harvest.py`) and real template generation from harvested research
(`make_templates.py`) — were built or spec'd in a **separate prior session** ("One-Click Library")
and are not present in this session's working files. Neither is reconstructed here from memory (per
the standing rule: never present a memory reconstruction as Sam's actual file). If Sam wants those
included in a genuine end-to-end proof, the source files need to be supplied, or `harvest.py` needs
real GitHub/Gemini credentials to build and test against for real — no mocked harvest, ever. Until
then, this canonical spec's real, provable scope is stages 1–3 (assemble → prove → readiness/
library), which `STAGE_CROSS_REFERENCE.md` and the clean-room run below cover completely.

## B.8 — real identity/auth + five foundational capabilities (round 7): implemented, proven, additive to the Locked Goal

Layered on top of B.1–B.7 without touching Part A or narrowing the Locked Goal (still exactly
"convert the 43-app reference catalogue into 43 complete, independently working, browser-tested
applications and place the proven applications into the app library" — this round adds shared
library capability, not a new goal). Full reasoning and evidence for each item below lives in
`AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md` and `IDENTITY_AND_LOGIN_TYPES_SPEC.md`;
this section states the resolution, the same convention B.2/B.3/B.5 already use for
`RULINGS_ROUND5.md`.

- **`ctx` is no longer a stub.** Every previous canonical-spec section that touched `CAP-0000`
  assumed `{"user": None, "authenticated": False}` was permanent (the single most-recurring gap
  named across the coverage-expansion round, `COVERAGE_EXPANSION_REPORT.md` §5.1). It is now real:
  `_make_ctx()` in `HOST_APP_PY_TEMPLATE` resolves a real, validated session or API key from the
  request. This is additive — no canonical app's existing behavior changed (reconfirmed by the full
  regression below), because none of the 43+6 previously called anything auth-related.
- **Five identity/login types**, designed evidence-first (no spec for these existed anywhere in
  this project — searched exhaustively, same discipline as B.1's Constitution/Harvest-Spec finding
  — so the user explicitly authorized designing five from real recurring need rather than guessing
  or defaulting to generic providers), each with a written purpose/capabilities/security-requirement
  spec: see `IDENTITY_AND_LOGIN_TYPES_SPEC.md`.
- **Two real defects found and fixed by this round's own testing, not by inspection**: a same-app
  route collision in `add_auth_capabilities()` (fixed with `route_prefix` + a new same-app
  `(route, method)` collision assertion in `add_capability()`), and a cross-capability data-file
  collision (`sessions.json`, renamed to `auth_sessions.json`). Both are architecture-level findings
  the merged stress test exists to catch — see B.6's "one script for stages 1-3" framing: this is
  the same "prove the whole system, not just each part in isolation" discipline, extended from
  routes to data files.
- **Four honest, still-open gaps** (none closed, reinterpreted, or hidden by this section):
  encryption-at-rest key management is real but minimal (one local key, no rotation/KMS);
  `secure_vault` does not use any of the five identity types itself; no login rate-limiting/lockout
  exists anywhere in this library; the demo app's admin-registration endpoint is a demo convenience,
  not a production pattern. Restated verbatim from `IDENTITY_AND_LOGIN_TYPES_SPEC.md`'s own "Honest
  limitations" section — not narrowed here.
- **Regression proof, reconfirmed live**: canonical apps 43/43 READY, composed apps 6/6, proving
  table 29/29, functional tests 30/30, isolated stress test 184/184, full merged stress test
  (canonical + all coverage-expansion apps) 323/323 with 0 collisions / 0 shadowed / 0 other
  failures, and the new `security_tests.py` suite at 45/45 — all identical to the pre-existing
  baseline on every canonical-app number, confirming this round is additive, not a rewrite.

**Slots 5 (Harvest Specification) and 6 (Constitution and Governance Files) in B.1's authority-order
table are unchanged by this round: still "no document on record."** This was searched for again,
independently, before this section was written (not assumed from B.1's prior finding) and the
result is the same. See B.9 for the formal closure of this question.

## B.9 — Slots 5 and 6 (Harvest Specification; Constitution and Governance Files): formally closed as N/A, with evidence trail

Closed on Sam's explicit instruction (2026-09-13), given as a direct response to this section's own
audit finding, after confirming three independent searches — not one — found the same result:

1. **2026-09-12, `RULINGS_ROUND5.md`** (round 5's own audit): *"Do Constitution/Governance files
   exist? ... nothing under this name has been seen in this engagement. Flagged, not guessed."*
   Same treatment given to the Harvest Specification.
2. **2026-09-12, `CANONICAL_SPEC.md` B.1** (this document, same round): restates the identical
   finding when mapping Part A's seven-slot authority order onto Sam's real four-document order.
3. **2026-09-13, this audit** (round 7, independent re-search before B.8/B.9 were written): a fresh,
   repository-wide search — not a re-read of B.1's prior conclusion — for "Constitution",
   "Harvest Specification", "Master Build", "Bible", `BUILD_PY_SPEC_v1.md`, `NUMBERING.md`,
   `TEMPLATE_STANDARD.md` across every file in the repository (`find`/`grep`, unrestricted). Result:
   `Constitution`/`Harvest Specification` still absent by name and content; `BUILD_PY_SPEC_v1.md`,
   `NUMBERING.md`, `TEMPLATE_STANDARD.md`, and a file literally named "the Bible" are **also absent
   as files on disk today**, despite B.1 recording them as "Exact match" — flagged here as a
   separate, narrower finding (those three-plus-the-Bible were evidently supplied as content in an
   earlier conversation and never persisted as repository files, not proof they never existed) that
   does **not** change slots 5/6's determination, which was independently negative all three times.

**Determination**: slots 5 (HARVEST SPECIFICATION) and 6 (CONSTITUTION AND GOVERNANCE FILES) are
**N/A** in Part A §2's authority order. This is a closure of a document-existence question, not an
invention of the missing documents and not a reduction of Part A's own authority-order rule (Part A
§2 itself remains unedited above; this section only supplies the factual answer to the "does the
document exist" question Part A's own rule depends on, exactly as B.1 said the question would be
resolved). If Sam later supplies genuine Harvest Specification or Constitution/Governance content,
it re-opens these slots and is reconciled against the proven working system through this same B.n
amendment process — not by retroactively editing this section.

**No part of this closure touches or narrows the Locked Goal (Part A §3), and no working code,
test, or proven capability changed as a result of it.**
