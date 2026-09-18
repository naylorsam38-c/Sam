# APP BASELINE ALIGNMENT REPORT

**Purpose:** Establish the actual, current, evidence-backed state of the app library, for use as the comparison baseline in `SPEC_AUTHORITY_DECISION.md`. Existing evidence is used and labeled where valid; nothing was re-run merely to reproduce an already-current result.

**Primary evidence source:** `verification/verification_result.json`, mtime 2026-09-13 10:42 UTC — confirmed **newer** than the last edits to `build.py` (10:37) and `verification/app_defs.py` (10:36), i.e. this is a fresh run against the current code, not a stale artifact. Produced during this session's own Phase 1A work, immediately preceding this report; unchanged since (no further code edits between that run and this report — checked via `git status`/file mtimes above).

**Important caveat, stated once here and assumed throughout:** every claim below describes the **current uncommitted working tree**, not `HEAD` (`a1653ea3e8094257a558c666a47956b56cb0d597`). `HEAD` itself does not have several of these fixes (see `SPEC_AUTHORITY_DECISION.md` §Date Evidence for specifics — e.g. `note_taking`'s committed journey still targets Bootstrap Admin, not Login-failure).

---

## Checklist against the required baseline items

| Item | Status | Evidence |
|---|---|---|
| 43/43 canonical app types reach READY | **VERIFIED** | `verification_result.json.sections.canonical_apps`: `{"result_line": "43/43 READY", "ok": true, "expected_count": 43}` |
| 6/6 composed apps | **VERIFIED** | `sections.new_composed_apps`: all 6 keys `true` (`new_app_event_board.py`, `new_app_fitness_challenge.py`, `new_app_course_enrollment.py`, `new_app_recipe_box.py`, `new_app_bug_tracker.py`, `new_app_volunteer_shift_signup.py`) |
| 15/15 coverage-expansion apps | **VERIFIED** | `sections.coverage_expansion_apps`: `{"count": 15, "ok": true}`, all 15 individually `true` |
| 300 capabilities across 49 projects | **VERIFIED** | `sections.dependency_graph_audit.output`: `"CLEAN: 0 missing targets, 0 cycles, 0 contract violations, 0 hidden data access across 300 capabilities in 49 projects."` |
| Dependency graph is clean | **VERIFIED** | Same field as above — 0/0/0/0 |
| 329/329 full-library stress test | **VERIFIED** | `sections.full_library_stress_test`: `{"ok": true, "pass": 329, "total": 329, "shadowed": 0, "other_fail": 0}` |
| 30/30 cross-app functional tests | **VERIFIED** | `sections.functional_tests`: `{"ok": true, "passed": 30, "total": 30}` |
| Note-taking security suite | **VERIFIED** | `verification/note_taking_pilot_security_tests.py`, run directly (not one of the 8 orchestrated sections) immediately after the above: **64/64** passed, including forged-token rejection, cross-user isolation, and post-password-reset session revocation. Re-run for this report: unchanged, still 64/64. |
| Data-isolation guard | **VERIFIED** | `KNOWN_SAFE_DATA_FILE_COLLISIONS` allowlist + `_assert_all_data_filenames_namespaced()` generation-time assertion (`verification/gen_common.py`). Proven this session via real break/restore: injected an unnamespaced data-filename bypass into `habit_tracker`'s "List Habits" capability, rebuild raised the real `AssertionError`; reverted, rebuild succeeded. |
| Arrangement rendering | **VERIFIED** | `_arrangement_css()` (`verification/gen_common.py`, `verification/gen_fixtures.py`), proven via two real A/B builds of the Todo fixture differing only in `choice.json`'s `arrangement`, a real live HTTP diff, and a real Playwright bounding-box difference (`verification/arrangement_rendering_tests.py`, 3/3 pass). |
| Authenticated button verification | **VERIFIED** | This session's own Phase 1A work: `_acquire_test_session()` + auth-aware `make_generic_compute_check()` in `build.py`. Proven via real bootstrap+login against a real running process, and via a real break (forced-invalid-token → real 401 FAIL) / restore (real PASS) cycle. `note_taking` rebuilt with 3 real, populated, authenticated buttons (`note_list`, `add_note`, `delete_note`), `locators.json` non-empty, `READY`. |

**No item in the required list is UNVERIFIED.** All ten have direct, current, machine-produced evidence dated within this session.

---

## Overall result

```
overall: PASS
```
(`verification/verification_result.json`, top-level field, read directly — not summarized from memory.)

## What this report does NOT claim

This report establishes that the **current working tree** meets the listed baseline. It does not claim:
- That this state is committed (it is not — see `SPEC_AUTHORITY_DECISION.md`).
- That the baseline is "finished" or will not change further (it has changed multiple times within this single session already).
- Anything about front-door wiring, skins, or AWS deployment — explicitly out of scope for this work order and not touched.
