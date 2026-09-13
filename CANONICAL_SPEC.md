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

⸻

# PART C — Infrastructure Contracts (new, round 7, explicitly authorized 2026-09-13)

**This is not a reconciliation of an absent historical document.** Part A's authority order (§2)
never named "capability contract," "shared library contract," "host dispatch contract," etc. as
slots to fill, and B.9 already closed the only two genuinely missing historical documents (Harvest
Specification, Constitution) as N/A. Part C is new: seven contracts describing, for the first time
in writing at this level of precision, the real infrastructure `build.py` and `gen_common.py`
already implement and this session's regression already proves. Each contract was written from
direct inspection of the actual source (function names, line-level behavior, and exact test
commands are cited, not paraphrased from memory) immediately before being written down.

**Amendment rule for Part C, matching Part B's own discipline**: nothing here is invented ahead of
the code — a Part C contract may only assert what the cited code and test evidence already do. A
future round that changes the underlying code amends the matching C.n section, cited by subsection,
the same way B.1–B.9 amend Part A. Part C never overrides Part A or Part B; where a Part C contract
touches the same subject as a Part B section (e.g., C.7 and B.2/B.3), Part B's ruling governs and
Part C states the contract in Part B's terms rather than re-deciding it.

**Nothing in Part C requires, permits, or was written to justify changing any working, tested
code.** Where a contract exposes a real gap, it is recorded under that contract's own "Genuine
gaps" heading, not fixed here.

## C.1 — The Capability Record Contract

**Purpose.** The one shape every capability in the library — currently 294 across 49 canonical/
composed projects, plus every coverage-expansion probe — must satisfy to be admitted into a build
at all. This is the contract `build.py`'s own name for it ("Common Capability Contract v2") already
describes; C.1 is its formal write-up.

**Components governed.** Every `CAP-XXXX.json` record and its paired `route.py`/`app.py`
implementation.

**Existing code and interfaces.**
- `cap_record(cap_id, name, category, impl_ids, output_fields=(), required_input=(), side_effects=(), approval_ref=..., dependencies=(), error_codes=(), data_access=(), requires_auth=False, context_fields=())` (`verification/gen_common.py:36`) — the record shape itself. New v2 fields (`data_access`, `context_fields`, `contract_version`) live nested inside the pre-existing `data_shape` dict, never as new top-level keys, so this is provably backward-compatible with build.py's own pre-v2 internal proving-table fixtures.
- `validate_v2_contract(cap_id, cap, app_dir)` (`build.py:603`) — the real compatibility gate. Only runs for a capability that opted in (`data_shape.contract_version == "2.0"`); enforces `data_access` is a well-formed list, `context_fields` is a list, `error_contract.error_codes` is a non-empty list, and — the real teeth — a static regex scan of the capability's *actual copied source* for `_shared.load/save(...)` calls and `DATA_FILE_NAME =` assignments, raising `Broken` (a hard failure, not a warning) if the source touches any entity not declared in `data_access`, or bypasses the shared storage interface entirely (`_RAW_PATH_BYPASS_RE`).
- `match_contract(expected, cap, impl)` (`build.py:520`) — the twelve-axis slot-to-capability compatibility check: required-input subset, input/output type equality, output-field subset, a *directional* nullable-fields subset (H-T3's ruling: a capability may be stricter than required, never looser), permissions equality, `requires_auth` equality, dependency subset, error-code subset, a directional security-constraints dict-subset, side-effects equality, and semantic-version comparison.

**Test evidence.** `audit_dependency_graph.py`: CLEAN, 0 missing targets / 0 cycles / 0 contract violations / 0 hidden data access across 294 capabilities in 49 projects (re-run live during this session's audit). `verify_build.py` rows G1–G3, H-T3 (29/29 pass, live-reconfirmed): a capability stricter or broader than required binds cleanly; a genuinely unmet security constraint still HELDs.

**Proposed new requirements.** None — every clause above is already enforced as a hard failure, not a recommendation.

**Genuine gaps.** `_RAW_PATH_BYPASS_RE` only recognizes one bypass shape (`parents[2] / "data"`, i.e. reaching around `_shared.load()/save()` to touch `data/` directly). It predates `save_blob()`/`load_blob()` and `encrypt_value()`/`_master_key()` (this round's own additions) and does not recognize an equivalent bypass of `data/blobs/` or `secrets/` (e.g. a capability that constructs `Path(__file__).resolve().parents[2] / "secrets"` directly instead of calling `_shared.encrypt_value()`). No capability does this today — confirmed by the same audit that found 0 hidden access — but the static check does not yet structurally prevent a *future* one from doing so undetected.

## C.2 — The Shared Library Contract (CAP-0000)

**Purpose.** The single, shared, non-duplicated implementation every capability imports rather than reimplementing — storage, blob storage, notifications, audit logging, and the full auth/crypto primitive set.

**Components governed.** `modules/CAP-0000/shared_lib.py`, byte-identical across every project in a given build (verified 0 non-identical duplicate ids in the final merged stress test).

**Existing code and interfaces** — the complete public API, enumerated directly from `SHARED_LIB_SOURCE`:
`load(filename)`, `save(filename, rows)`, `code_for_status(status)`, `save_blob(raw_bytes, content_type, filename_hint, index_filename)`, `load_blob(blob_id, index_filename)`, `notify(recipient, message, filename)`, `audit(actor, action, entity, entity_id, details, filename)`, `hash_password(password)`, `is_common_password(password)`, `verify_password(password, stored)`, `create_session(user_id, extra, ttl_minutes, filename, role_source)`, `is_expired(expires_at_iso)`, `validate_session(token, filename)`, `invalidate_session(token, filename)`, `generate_api_key(service_name, filename, ttl_minutes)`, `validate_api_key(raw_key, filename)`, `generate_share_token(resource_type, resource_id, filename, ttl_minutes)`, `validate_share_token(token, resource_type, filename)`, `_master_key(key_filename)`, `encrypt_value(plaintext, key_filename)`, `decrypt_value(token, key_filename)`.

**Test evidence.** `security_tests.py` 45/45 (password hashing/blocklist, session create/validate/invalidate, live role-resolution, API keys, share tokens, all with real file inspection). `encryption_tests.py` 9/9 (real AES-256-GCM round-trip and tamper rejection). `document_tests.py` 12/12 (real blob storage, binary-safe). All live-reconfirmed this session.

**Proposed new requirements.** None retroactive. A future, purely additive requirement worth recording as a design intent, not a present obligation: any new CAP-0000 primitive that writes a new top-level `data/<name>.json` or `data/<dir>/` should be checked against every existing `DATA_FILE_NAME`/blob-directory name across the library before being added, the same way C.4 now requires for capabilities generally — this generalizes the lesson `auth_sessions.json` (C.4) already had to learn once.

**Genuine gaps.** `_master_key()`'s key management is real (random, never hardcoded, never committed) but minimal: one local key, no rotation, no per-tenant separation, no external KMS — stated in the key's own docstring and restated, not narrowed, here.

## C.3 — The Host Dispatch Contract

**Purpose.** The actual wire protocol connecting an incoming HTTP request to a capability's `handle()` function, and a capability's return value back to a real HTTP response.

**Components governed.** `HOST_APP_PY_TEMPLATE`'s Flask app: `health()`, `index()`, `load_modules()`, `_make_ctx(request)`, `_error_body(status, message)`, `dispatch(subpath)`.

**Existing code and interfaces.**
- `dispatch()` is the one catch-all route (`GET`/`POST` only — see Genuine gaps), keyed by `(request.method, path)` into `ROUTE_HANDLERS`, calling `handler(request, _make_ctx(request))` when `HANDLER_WANTS_CTX` marks that route as ctx-aware, else the plain `handler(request)`.
- `_make_ctx(request)` resolves a real `Authorization: Bearer <token>` into a validated session (via `_shared.validate_session()`) and a real `X-API-Key` header into a validated key (via `_shared.validate_api_key()`), returning `{"user", "authenticated", "role", "token", "service"}` — never a hardcoded stub (the pre-round-7 state B.8 documents).
- The binary-response path: a handler returning `{"__binary__": True, "data": <bytes>, "content_type": <str>}` is served via `Response(...)` instead of `jsonify(...)` — a sentinel no pre-existing handler ever returns, so this is additive and does not change any prior capability's behavior.
- The standard error shape: any handler returning the older bare `{"error": "<string>"}` form is normalized centrally to `{"error": {"code": ..., "message": ...}}`.

**Test evidence.** `full_library_stress_test.py` (323/323, live-reconfirmed): every route-bearing capability across the merged system dispatches correctly. `document_tests.py`: the binary-response path serves the exact original bytes with the exact stored `Content-Type` (12/12).

**Proposed new requirements.** None.

**Genuine gaps.** `dispatch()`'s route is registered for `methods=["GET", "POST"]` only — there is no structural support for `PUT`/`DELETE`/`PATCH`. Every capability in the library today expresses updates and deletes as `POST` to an action-shaped sub-route (e.g. `/tasks/delete`), which works and is fully tested, but a capability author reaching for a REST-conventional verb would find it silently unsupported (a 404 from Flask's own routing, not a contract violation `build.py` would catch).

## C.4 — The Cross-App Isolation Contract

**Purpose.** The whole-library property that no single app's own build or test can see: that merging every capability from every project into one real running system produces zero URL-route collisions and zero data-file collisions. This is the contract this session's own work most directly tested — and broke, twice, before fixing.

**Components governed.** `_namespace_route()` (route strings), the same-app `(route, method)` collision assertion in `add_capability()` (added this round), and every capability's own choice of `DATA_FILE_NAME`.

**Existing code and interfaces.**
- `_namespace_route(route)` rewrites every capability's route to `/api/<slug><rest>`, making cross-*app* route collision structurally impossible (found and fixed in an earlier round, per `FULL_LIBRARY_STRESS_TEST.md`).
- The same-app collision assertion (added this round, in response to a real bug): `AppBuilder` tracks `(namespaced_route, method)` per app and raises `AssertionError` at generation time if two capabilities in the *same* app claim the same pair — closing the gap that let `add_auth_capabilities()`'s three same-app instances silently shadow each other before `route_prefix` existed.
- `full_library_stress_test.py` is this contract's actual enforcement mechanism at the *whole-library* level: it merges every real capability from every real project into one process and one shared `data/` directory and reports collision groups, predicted-shadowed capabilities, and — separately — duplicate capability ids that are not byte-identical.

**Test evidence.** Two real, historical violations, both found by this exact mechanism and both fixed:
1. Same-app route collision (`add_auth_capabilities()` before `route_prefix` existed) — fixed; the assertion above now prevents recurrence at generation time, before a build even runs.
2. Cross-capability data-file collision (`sessions.json`, shared by the new auth mechanism and two unrelated pre-existing capabilities) — fixed by renaming to `auth_sessions.json`.

Final state, live-reconfirmed this session: 323/323 capabilities across the full merged library (canonical + all 15 coverage-expansion apps), 0 collisions, 0 shadowed, 0 other failures, 0 non-byte-identical duplicate ids.

**Proposed new requirements.** None that would change tested behavior.

**Genuine gaps — the most concrete one this audit found.** Bug #1 (routes) now has a real, structural, generation-time guard that makes recurrence impossible. **Bug #2 (data files) does not.** The fix was a rename; nothing in `add_capability()` or `AppBuilder` checks a new capability's `DATA_FILE_NAME` (or blob/secrets directory name) against every other capability's choice across the library the way the route-collision assertion now does automatically. Today, catching a repeat of bug #2 depends on someone remembering to run `full_library_stress_test.py` with the specific combination of apps involved — exactly what caught it this time, but not a structural guarantee the way C.1's static bypass check or the route-collision assertion are. This is recorded as the single most important "required future improvement" this audit identified, precisely because it is the same class of bug that already happened once, for real, in the code this contract governs.

## C.5 — The Identity & Session Contract

**Purpose.** The wire-level contract behind `IDENTITY_AND_LOGIN_TYPES_SPEC.md`'s five identity types — what `ctx` actually contains and how its fields are resolved, kept separate from that document's human-facing purpose/capabilities framing.

**Components governed.** `ctx` as produced by `_make_ctx()` (C.3) and consumed by any two-argument `handle(request, ctx)`; the `role_source` live-resolution mechanism; TTL/expiry on sessions, API keys, and share tokens.

**Existing code and interfaces.** `create_session(..., role_source=(data_filename, id_field))` stores `_role_source` on the session row; `validate_session()` re-reads the *live* record from that file on every call and returns the *current* role, or `None` (fail closed) if the account no longer exists — not the role frozen at login time. `is_expired()` is the one shared lazy-evaluation check used identically by sessions, API keys, and share tokens.

**Test evidence.** `security_tests.py` 45/45, including the three checks added this round specifically for live-resolution: promoting bob's live user record grants access on his *already-issued* token with no re-login; demoting revokes it just as immediately; deleting the account invalidates the token (fail closed). Live-reconfirmed.

**Proposed new requirements.** None.

**Genuine gaps.** Restated verbatim from `IDENTITY_AND_LOGIN_TYPES_SPEC.md`, not narrowed: no login rate-limiting/lockout exists anywhere in this library; `secure_vault` does not use any of these five types itself; the demo app's admin-registration endpoint is a public, unauthenticated convenience, not a production pattern.

## C.6 — The App Assembly Contract (AppBuilder)

**Purpose.** How a new app type is composed, at generation time, from reusable capability engines rather than hand-written per app.

**Components governed.** `AppBuilder`'s full method set: `add_host`, `add_capability`, `add_exceeds_threshold_capability`, `add_bounded_counter_capability`, `add_unbounded_counter_capability`, `add_status_transition_capability`, `add_bounded_decrement_capability`, `add_validated_status_transition_capability`, `add_search_capability`, `add_audit_log_capability`, `add_auth_capabilities`, `add_share_token_capability`, `add_api_key_capability`, `add_document_storage_capabilities`, `add_ranking_capability`, `reuse_capability_verbatim`, `add_notification_capabilities`, `add_calendar_event_capabilities`, `add_symmetric_relationship_capability`, `write_template`, `write_choice`, `finish`.

**Existing code and interfaces.** Every `add_*` engine funnels through `add_capability()` (the one place `cap_record()`, `_namespace_route()`, and the C.4 collision assertion all run), so every engine automatically inherits the Capability Record Contract (C.1) and the Cross-App Isolation Contract (C.4) with no per-engine extra work. `reuse_capability_verbatim()` is the one exception by design: it copies another app's real, already-proven capability byte-for-byte, keeping the *original* app's namespace — real reuse, not a new capability pretending to be independent.

**Test evidence.** Every one of 43 canonical + 6 composed + 15 coverage-expansion apps was built through this exact mechanism and reached BUILT/READY (live-reconfirmed this session for all 64).

**Proposed new requirements.** None.

**Genuine gaps.** Two structural facts about the auto-generated primary browser-journey slot, both found the hard way this round and both stated honestly in the relevant demo apps' own docstrings rather than fixed by weakening the journey mechanism: (1) an authenticated capability (`context_fields_override` or `required_role` set) cannot be the target of the primary journey slot, because the generic Playwright-driven journey has no way to carry an `Authorization` header; (2) a real multipart file-upload capability (`add_document_storage_capabilities`) cannot be either, because the journey driver only knows how to type text into an input and click a button, not attach a file. Every app built on this contract keeps its journey bound to a plain, unauthenticated, text-based capability for this reason.

## C.7 — The Build-to-Library Lifecycle Contract

**Purpose.** Formalizes, as a contract, what B.2 and B.3 already established as a ruling — stated here in contract terms so C.1–C.6 have a matching lifecycle-level contract, not to re-decide anything B.2/B.3 settled.

**Components governed.** `stage1_assemble()`, `stage2_prove()`, `stage3_readiness_and_promote()`, `compute_readiness()`/`compute_readiness_with_library()`, `promote_to_library()`.

**Existing code and interfaces.** One script, `build.py`, takes an already-populated shelf and an already-accepted template's `choice.json` through assembly → proving → readiness/promotion in one process (B.6). `promote_to_library()` copies a build's own proof (`registry.json`, `app.json`, `locators.json`, `modules/`, `skin.json`, every relevant `RUN-*.json`) into `library/<app_id>/` only when the app has genuinely reached `active` (a real BUILT run), writing a `PROMOTED.json` marker — auto-invoked at the end of every run that reaches BUILT, per B.3.

**Test evidence.** `verify_build.py` 29/29, `test_readiness.py` 20/20, `run_full_verification.py`'s full 7-section suite — all live-reconfirmed this session, identical to the pre-existing baseline.

**Proposed new requirements.** None.

**Genuine gaps.** Unchanged from B.4: the seven named registry files and thirteen named reports an earlier document (Part A) asks for remain an export/formatting layer over real, complete underlying data (`run_ledger.jsonl`, `reports/RUN-*.json`, `registry.json`) — not yet built, correctly recorded as out of scope rather than silently dropped.
