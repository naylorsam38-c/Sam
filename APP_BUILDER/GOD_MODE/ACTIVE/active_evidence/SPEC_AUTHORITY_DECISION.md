# SPEC AUTHORITY DECISION

## Decision: **HOLD**

Neither the date test nor the alignment test resolves cleanly in favor of promotion. Both are addressed in full below, with exact evidence, per §6 (Phase C) of the work order.

---

## C.1 — Date test

**Strongest available evidence, in the required priority order:**

1. **Git history** (used — this is decisive and sufficient on its own):
   - `CANONICAL_SPEC.md` was first added in commit `ba9389b`, 2026-09-12 19:10:50 UTC, in the **same commit** as the first "build and prove all 43 canonical app types" work. Git records commit-level, not intra-commit, ordering — this fact alone is **neutral**, not evidence for either side.
   - `CANONICAL_SPEC.md` received **six further commits**, the last being `22e5f92`, 2026-09-13 01:34:56 UTC.
   - Real, substantive app-library work continued **after** that last spec commit:
     - Commit `a1653ea` (`HEAD`), 2026-09-13 02:47:14 UTC — *"Promote real per-user isolation, login, and admin-provisioned accounts to note_taking"* — not reflected in `CANONICAL_SPEC.md` at all.
     - The current **uncommitted working tree** goes further still: `git diff --stat HEAD` shows **336 files changed, 21,710 insertions(+), 1,509 deletions(-)**, touching `build.py`, `verification/gen_common.py`, `verification/app_defs.py`, `verification/full_library_stress_test.py`, `verification/run_full_verification.py`, and every app's regenerated `OUTPUT_LIBRARY` output. None of this exists in any commit; none of it is reflected in `CANONICAL_SPEC.md`.
   - Direct confirmation that `HEAD` itself lags real, later-superseded plans: `git show HEAD:verification/app_defs.py` shows `note_taking`'s primary journey still targets `#bootstrap-email`/`#bootstrap-btn` — the mechanism the uncommitted working tree has since replaced with a Login-failure journey, for a real, documented security reason (Bootstrap Admin now requires a secret the journey must never see).

2. **Filesystem timestamps** — not relied upon as primary evidence (per the work order's own priority order, git history outranks it), and independently unreliable here: this container has extensive uncommitted edits, so mtimes reflect this session's own edit activity, not a stable "when was this true" fact. Recorded in `SPEC_AUTHORITY_INVENTORY.json` for completeness only.

3. **Existing build reports/manifests** — corroborate the same conclusion: `PILOT_OWNER_SETUP_SHEET.md`'s own current (uncommitted) draft independently states *"Authoritative implementation baseline: commit `a1653ea`... Uncommitted pending changes exist (Bootstrap Admin token-gating, the Login-failure journey retarget, an additive `build.py` check, and 12 new tests)... not committed, and not treated as active anywhere in this document."* This document reached the same commit-vs-working-tree distinction independently, for the same reason.

**Result: creation order not conclusively establishable as "after the app library was built," because the app library has no discrete "built" instant to be after.** It was still changing, in real and substantive ways, after `CANONICAL_SPEC.md`'s last commit — including changes made within this very session that remain uncommitted right now.

---

## C.2 — Alignment test

Rule-by-rule comparison, `CANONICAL_SPEC.md` vs. the actual implementation and `APP_BASELINE_ALIGNMENT_REPORT.md`:

| Rule | Evidence in spec | Evidence in implementation | Result |
|---|---|---|---|
| C.1 Capability Record Contract | §C.1, `cap_record()` schema described | `verification/gen_common.py`, `cap_record()` — matches description | **PASS** |
| C.2 Shared Library Contract (CAP-0000) | §C.2 | `verification/gen_common.py`, `shared_lib.py` generation — matches | **PASS** |
| C.3 Host Dispatch Contract | §C.3, `_make_ctx()` described | `verification/gen_common.py:760-783`, real Bearer-token resolution against real sessions — matches exactly | **PASS** |
| C.4 same-app route collision guard | §C.4, `(route, method)` assertion in `add_capability()` | Present, unchanged, in `gen_common.py` | **PASS** |
| C.4 `RESERVED_SHARED_LIB_FILENAMES` guard | §C.4, frozenset of 2 reserved names | Present, unchanged | **PASS** |
| C.4 "genuine gap": cross-app domain-filename collisions require running the stress test manually, no generation-time guard exists | §C.4, "Genuine gaps" paragraph, stated as **currently open** | **FALSE as currently written.** `KNOWN_SAFE_DATA_FILE_COLLISIONS` (named, per-entry-justified allowlist) + `_assert_all_data_filenames_namespaced()` (generation-time assertion) now close this class structurally — proven this session via real injected-bypass break/restore (see `APP_BASELINE_ALIGNMENT_REPORT.md`). The spec states a limitation that the real code no longer has. | **FAIL — spec obsolete on this point** |
| C.5 Identity & Session Contract, live role re-resolution | §C.5 | `validate_session()` re-reads live record every call — matches | **PASS** |
| C.5 "genuine gaps": no rate-limiting/lockout, `secure_vault` doesn't use these 5 identity types | §C.5, stated as open | Confirmed still true — not touched this session | **PASS (gap correctly still recorded as open)** |
| C.6 `AppBuilder` engine list | §C.6 | Matches current `gen_common.py` method set exactly | **PASS** |
| C.6 "genuine gap" (1): an authenticated capability cannot be the target of ANY auto-generated check, because the check has no way to carry an `Authorization` header | §C.6, stated as a blanket limitation across "the auto-generated primary browser-journey slot" | **Partially false as written.** True and unchanged for the Playwright journey (`CHK-020`) — not touched this session. **False** for the per-slot compute check family (`CHK-1xx`+): this session's `_acquire_test_session()` + auth-aware `make_generic_compute_check()` now authenticates before probing — proven via real bootstrap+login and a real break(401)/restore(pass) cycle. The spec does not distinguish the two check families and, read as written, overstates the current limitation. | **FAIL — spec imprecise/obsolete on this point** |
| C.6 "genuine gap" (2): a multipart file-upload capability cannot be the journey target | §C.6 | Confirmed still true — not touched this session | **PASS (gap correctly still recorded as open)** |
| C.7 Build-to-Library Lifecycle states | §C.7 | Matches observed `BUILT`/`READY`/`HELD`/`RUNTIME_FAILED` states in real build output | **PASS** |
| Arrangement rendering (generic `{selector, position}` mechanism) | **Not mentioned anywhere in `CANONICAL_SPEC.md`** | Real, implemented, proven (`_arrangement_css()`, `arrangement_rendering_tests.py`, 3/3 pass) | **MISSING RULE — not a violation (the mechanism doesn't contradict anything written), but the spec cannot be called complete** |
| Authenticated-slot proving mechanism (`_acquire_test_session`, `BOOTSTRAP_SETUP_TOKEN` injection) | **Not mentioned anywhere** | Real, implemented, proven this session | **MISSING RULE** |
| Numbering conventions | **No `NUMBERING.md` exists; `CANONICAL_SPEC.md` does not itself define a numbering rule** | Observed pattern: one 100-number CAP block per app (0100 `todo_list` … 4300 `recipe_and_meal_planning`, plus 8000s/9000s for coverage-expansion apps), zero collisions per the dependency audit and stress test | **UNKNOWN — pattern observed and consistent, but no written rule exists anywhere to confirm it against, per this project's own §3 confirmation that `NUMBERING.md` does not exist** |

**Result: two named, quoted sections of `CANONICAL_SPEC.md` (§C.4's gap paragraph, §C.6's gap item (1)) assert something that is no longer true of the current, real, verified implementation. This is not "absence of a rule" (excluded from being treated as a violation per the work order's own instruction) — it is an existing, written rule/claim that the evidence contradicts.**

---

## C.3 — Authority decision, restated

**HOLD.**

- **Date evidence:** creation order relative to "the app library was built" cannot be established, because the library has no discrete built/finished state — it changed after the spec's last commit, and is still changing uncommitted, within this session.
- **Alignment evidence:** the implementation does not conflict with `CANONICAL_SPEC.md` broadly (10 of 13 evaluated rule-rows PASS outright, including both of the two gap-rows that are still correctly true), but two specific, named passages are demonstrably stale, and two real mechanisms have no corresponding rule at all. This is short of the "aligns with the actual finished apps and their verified standards" bar as written — not because the code is wrong, but because the document has not kept pace with it.
- **Conflicts:** `CANONICAL_SPEC.md` §C.4 and §C.6 (see table above).
- **Unknowns:** numbering convention (no written rule exists to check against, only an observed, consistent pattern).
- **Exact files inspected:** all 26 documents in `SPEC_AUTHORITY_INVENTORY.json`/`.md`; `verification/gen_common.py`, `build.py`, `verification/app_defs.py` (current working tree); `verification/verification_result.json`; `verification/note_taking_pilot_security_tests.py` (re-run); `git log` for every inventoried document and for the repository as a whole.
- **Recommendation:** commit the current working tree, then in the same or an immediately following commit, correct `CANONICAL_SPEC.md` §C.4 and §C.6 to describe the real, current state, and add the two missing rules (arrangement rendering, the authenticated-slot proving mechanism). Re-run this exact work order after that commit — at that point the date test and the alignment test both have a real chance of resolving to PROMOTE, because the two facts being compared will finally both refer to the same, fixed, dated state.
- **What remains unchanged:** `CANONICAL_SPEC.md` itself (not edited, not promoted, not archived); no active specification index exists or was created; no application code was modified by this work order.

Per the work order's Phase D/E/F: **because the decision is HOLD, none of those phases were executed.** No `spec/active/` directory, no `spec/active/SPEC_MANIFEST.json`, and no superseded-document archival of any *specification* were created — there is nothing to promote and nothing has been demoted from active status, since nothing was active before this work order and nothing is active after it either. (One non-specification artifact — the prior, less formal cleanup report from before this work order — was archived under `spec/archive/reports/`, preserved verbatim with a supersession notice, per "preserve audit history"; this is documented fully in `SPEC_AUTHORITY_CLEANUP_REPORT.md`.)
