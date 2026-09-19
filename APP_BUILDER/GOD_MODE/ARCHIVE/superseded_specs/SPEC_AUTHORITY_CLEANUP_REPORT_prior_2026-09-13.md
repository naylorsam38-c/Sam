SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `SPEC_AUTHORITY_DECISION.md` and the regenerated `SPEC_AUTHORITY_CLEANUP_REPORT.md`
(root), both produced under the "Canonical Authority & Specification Cleanup Specification"
work order, 2026-09-13. Archived here verbatim; conclusion (HOLD) unchanged, superseded only
because a more formal, rule-by-rule decision record now exists.
Original path: `SPEC_AUTHORITY_CLEANUP_REPORT.md` (repo root)
Archived: 2026-09-13
SHA-256 of this file's content at archival time (pre-notice): computed and recorded in
`SPEC_AUTHORITY_INVENTORY.json`.

---

# SPEC AUTHORITY & CLEANUP REPORT

**Generated:** 2026-09-13
**Scope:** Whether `CANONICAL_SPEC.md` should be promoted to sole governing specification for the app builder.
**Decision rule applied, verbatim:** Promote only if (a) `CANONICAL_SPEC.md` was created after the app library was built, AND (b) it aligns with the actual finished apps and their verified standards. If either cannot be established, HOLD.

---

## AUTHORITY DECISION: **HOLD**

Neither precondition can be established as true. Both are contradicted by direct evidence, not merely unproven. See §3 and §4.

No file was promoted, archived, deleted, or rewritten. No active specification index was created or changed, per the constraints ("If HOLD or FAIL, leave the active governing set unchanged").

---

## 1. Specification set and active indexes — inspected

**Active index: none exists.** `README.md` (repo root) is two lines (`# Sam` / `AIRE`) — not an index. `verification/README.md` is a clean-room bootstrap/reproduction guide, not a specification index. No file anywhere in the repository declares itself, or any other file, as "the governing specification." This is itself a finding: there was nothing for this work order to update even if the decision had been PASS, until one is created as part of a PASS outcome — which did not happen here.

**Full specification/report inventory** (repo root, `.md` files that are specs or evidence reports, with last real commit date — see §2 for why commit date, not filesystem mtime, is the authoritative timestamp):

| File | Last commit (UTC) |
|---|---|
| `RULINGS_ROUND5.md` | 2026-09-12 19:10:50 |
| `FULL_LIBRARY_STRESS_TEST.md` | 2026-09-12 22:24:01 |
| `COVERAGE_EXPANSION_REPORT.md` | 2026-09-12 23:32:15 |
| `IDENTITY_AND_LOGIN_TYPES_SPEC.md` | 2026-09-13 00:41:16 |
| `CANONICAL_SPEC.md` | 2026-09-13 01:34:56 |
| `NEXT_PHASE_READINESS.md` | 2026-09-13 01:47:51 |
| `PRODUCT_DEPLOYMENT_DECISIONS.md` | 2026-09-13 01:51:41 |
| `PRIVATE_PILOT_SAFETY_MILESTONE.md` | 2026-09-13 02:09:53 |
| `PILOT_OWNER_DECISION_SHEET.md` | 2026-09-13 02:16:45 |

Plus `API_KEY_AND_INPUT_REQUIREMENTS.md`, `PILOT_OWNER_SETUP_SHEET.md`, `PILOT_QUESTIONS_AND_INPUT_SPEC.md`, `COMPATIBILITY_AUDIT.md`, `COVERAGE_TEST_PLAN.md`, `COVERAGE_TESTING_AND_EXTENSION.md`, `END_TO_END_PROOF.md`, `INTEROPERABILITY_UPGRADE.md`, `REAL_APP_PROOF.md`, `STAGE_CROSS_REFERENCE.md`, `UNIVERSAL_COMPATIBILITY.md`, `AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md`, `review.md` — all narrower-scope reports/decision sheets, none claiming or contested for governing status; not further evaluated against the promotion rule because the work order names `CANONICAL_SPEC.md` specifically.

**Confirmed absent, re-checked fresh for this report** (whole-filesystem search, not from memory): "the Bible", `BUILD_PY_SPEC_v1.md`, `NUMBERING.md`, `TEMPLATE_STANDARD.md`, `APP-BUILDER-ready.zip`, `app-builder-complete.zip`. Zero matches. These cannot be part of any alignment analysis because they do not exist on this machine.

---

## 2. Actual creation date of `CANONICAL_SPEC.md`

Read from `git log --follow --diff-filter=A`, not filesystem mtime (mtime is unreliable here: this container has extensive **uncommitted** working-tree edits from the current session, so "when was this file last touched on disk" and "when was this fact actually established" are different questions for several files).

**First commit adding `CANONICAL_SPEC.md`:** `ba9389b`, **2026-09-12 19:10:50 UTC** — commit message: *"Build and prove all 43 canonical app types end to end via build.py"*. The spec file and the first proof of all 43 apps were introduced in the **same commit**. Git cannot distinguish authorship order within one commit, so this alone is neutral, not evidence for either side.

**What is not neutral:** `CANONICAL_SPEC.md` was committed to **six more times** after that, most recently `22e5f92`, **2026-09-13 01:34:56 UTC** ("CANONICAL_SPEC.md C.4: record the verified reserved-filename guard"). Real library work continued **after** that final spec commit and is captured nowhere in it:

- Commit `a1653ea`, 2026-09-13 02:47:14 — *"Promote real per-user isolation, login, and admin-provisioned accounts to note_taking"* — the current `HEAD`. Not reflected in `CANONICAL_SPEC.md`.
- Substantial further work exists **only in the current uncommitted working tree**, done in this session, after `HEAD`: `git diff --stat HEAD` shows **336 files changed, 21,710 insertions(+), 1,509 deletions(-)** against `build.py`, `verification/gen_common.py`, `verification/app_defs.py`, `verification/full_library_stress_test.py`, `verification/run_full_verification.py`, and all 43 apps' regenerated `OUTPUT_LIBRARY` output. None of this is in any commit, let alone reflected in `CANONICAL_SPEC.md`.

**Conclusion:** the app library did not stop changing before `CANONICAL_SPEC.md`'s creation or its last edit — it kept changing after, including changes happening in this literal session that are not committed anywhere. There is no fixed "the app library was built" instant to compare the spec's creation date against. **Precondition (a) cannot be established.**

---

## 3. Actual completion date of the app library

There isn't one. Evidence:

- `HEAD` (`a1653ea`, 2026-09-13 02:47:14) is the last **committed** state, but it is demonstrably not "finished": its own `verification/app_defs.py` still has `note_taking`'s primary journey targeting `#bootstrap-email`/`#bootstrap-btn` (confirmed by reading `git show HEAD:verification/app_defs.py` directly), a mechanism the current working tree has since replaced with a Login-failure journey for a real, documented security reason (Bootstrap Admin now requires a secret the journey must never see). That replacement is **uncommitted**.
- In this same session, further real, verified changes were made and are still uncommitted: a generation-time guard closing the exact "broader" data-filename collision gap `CANONICAL_SPEC.md` §C.4 itself names as still open (see §4 below); the generic arrangement-rendering mechanism; and a fix making the build-time proving check able to authenticate before probing an authenticated capability (proven via real break/restore, full regression re-run, zero movement — see this session's own Phase 1A record).
- The app library is, right now, mid-edit in the same tool session that is writing this report.

**Conclusion: "the app library's completion date" is not an establishable fact — it has no discrete finished state to date. Precondition (a) fails on this ground independently of §2.**

---

## 4. Canonical Spec vs. actual apps/capabilities/verification evidence

Direct textual comparison, not inference:

### Aligned
- **C.1 (Capability Record Contract), C.2 (Shared Library / CAP-0000), C.3 (Host Dispatch), C.5 (Identity & Session), C.7 (Lifecycle)** — read in full; nothing in the current code contradicts these sections. `_make_ctx()`, `validate_session()`'s live role re-resolution, and the lifecycle states described all match current behavior.
- **C.4's documented mechanisms** (`_namespace_route()`, same-app route collision assertion, `RESERVED_SHARED_LIB_FILENAMES` guard) are all present and unchanged in the current code.
- **C.6's documented `AppBuilder` engine list** matches the current `gen_common.py` method set.

### Conflicting / obsolete (the spec asserts something no longer true)
- **C.4, "Genuine gaps" paragraph** states, as currently open: *"this guard only covers collisions against CAP-0000's own two reserved names. It does not protect against two arbitrary domain capabilities in different apps independently choosing the same data filename... Catching that broader class still depends on running `full_library_stress_test.py`..."* — **This gap has since been closed** in the uncommitted working tree: every domain capability's `data_filename` is now namespaced by owning app (`_namespace_data_filename()`), with a generation-time assertion (`_assert_all_data_filenames_namespaced()`) that fails the build if any generated file bypasses it — proven this session via real injected-bypass break/restore. `CANONICAL_SPEC.md` currently states a limitation as permanent that is no longer true of the real code.
- **C.6, "Genuine gaps" item (1)** states an authenticated capability cannot be the target of any auto-generated check because *"the generic Playwright-driven journey has no way to carry an Authorization header."* This remains true specifically for the Playwright journey (`CHK-020`) — untouched this session — but is no longer true of the *other* generic check family (the per-slot compute check, `CHK-1xx`+): this session added a real, generic session-acquisition mechanism (`_acquire_test_session`) so an auth-gated slot-wired capability's compute check now authenticates before probing. The spec does not distinguish these two check families and, read as written, overstates the current limitation.

### Missing (real mechanisms with no rule at all)
- The arrangement-rendering mechanism (`_arrangement_css()`, generic `{selector, position}` → CSS, driven by `locators.json`) — not mentioned anywhere in `CANONICAL_SPEC.md`.
- `KNOWN_SAFE_DATA_FILE_COLLISIONS` (the named, per-entry-justified allowlist that replaced an inferred severity heuristic) — not mentioned.
- The Phase 1A auth-aware build-time check itself, and the `BOOTSTRAP_SETUP_TOKEN` injection it depends on — not mentioned.

### Not evaluated
Every other spec/report file in §1's table beyond `CANONICAL_SPEC.md` — out of this work order's stated scope (it names `CANONICAL_SPEC.md` specifically), but flagged for awareness: `PRIVATE_PILOT_SAFETY_MILESTONE.md` (committed 02:09:53) already anticipates the Login-failure journey change that landed only in the uncommitted working tree — i.e., at least one subordinate document is *more* current than `CANONICAL_SPEC.md` on this specific point.

**Conclusion: precondition (b) also fails** — not "unproven," but affirmatively contradicted in two named, quoted places.

---

## 5. Verification evidence relied on for this comparison

No application code was changed to produce this report. The comparison in §4 is backed by the full-suite run already completed earlier in this same session (unchanged since — confirmed by `git status`/`git diff` showing no further code edits between that run and this report):

- `proving_table`: 29/29 pass
- `canonical_apps`: 43/43 READY
- `new_composed_apps`: 6/6 true
- `generalization_regression`: all_match: true
- `dependency_graph_audit`: CLEAN — 0 missing targets, 0 cycles, 0 contract violations, 0 hidden data access, 300 capabilities / 49 projects
- `functional_tests`: 30/30
- `coverage_expansion_apps`: 15/15 pass
- `full_library_stress_test`: 329/329 pass, 0 shadowed, 0 other_fail
- `overall`: PASS
- `note_taking_pilot_security_tests.py` (not one of the 8 sections, run separately): 64/64

Source: `verification/verification_result.json`, written by the run immediately preceding this report; re-verified present and unmodified before writing this report.

---

## 6. File actions taken

**None.** Per constraint 8 ("Do not cross out or deactivate a specification unless the authority decision and conflict analysis justify it") and the work order's own step 8 ("If HOLD or FAIL, leave the active governing set unchanged"):

- `CANONICAL_SPEC.md` — unchanged, not promoted, not archived.
- No active specification index created (none existed to update).
- No document archived.
- No application code modified by this work order.

---

## 7. Blockers — exact list, required before this decision can be revisited

1. **The app library has no discrete completion state.** As long as `app_defs.py`/`gen_common.py`/`build.py` continue to change without a corresponding commit and spec update in the same unit of work, "created after the app library was built" cannot be evaluated. Resolution: commit the current working tree (336 files, pending), then require every future capability/mechanism change to update `CANONICAL_SPEC.md` in the same commit, going forward.
2. **`CANONICAL_SPEC.md` §C.4's gap paragraph is stale** relative to the now-closed broader data-filename collision guard. Needs rewriting to describe the real, current state (closed, with its own test evidence) before the document can be trusted as authoritative.
3. **`CANONICAL_SPEC.md` §C.6's gap item (1) is imprecise** — it needs to distinguish the Playwright journey (`CHK-020`, still limited exactly as written) from the per-slot compute check (`CHK-1xx`+, no longer limited this way).
4. **No mechanism exists to keep the spec and the code in lockstep** — there is no active specification index, no "spec must be updated in the same commit as code" rule, and no automated check that would catch a future divergence the way `full_library_stress_test.py` catches a route/data collision. Until one exists, any future promotion decision faces the same problem this one did.
5. **The four named authority documents** (the Bible, `BUILD_PY_SPEC_v1.md`, `NUMBERING.md`, `TEMPLATE_STANDARD.md`) still do not exist anywhere on this machine. Not required to resolve *this* HOLD, but any claim that the library aligns with them specifically remains impossible to make until they are supplied.

---

## Completion statement

This report is complete under its own standard: the authority decision (HOLD), the file actions (none), the alignment analysis (§4), and the verification evidence (§5) are all recorded above, with every date and number sourced from `git log` or `verification/verification_result.json`, not memory or inference.
