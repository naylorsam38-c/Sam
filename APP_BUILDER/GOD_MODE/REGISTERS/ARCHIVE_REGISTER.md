# ARCHIVE REGISTER

Every file listed here is preserved — content byte-identical to its pre-archival version (verified by SHA-256 comparison before and after the move), never deleted. Each carries a `SUPERSEDED` notice (prepended for `.md` files, a comment header for `.py` files). Nothing was archived on uncertain purpose; `duplicate_material/`, `unused_scripts/`, and `abandoned_builds/` are empty, with the negative check that produced that result recorded below.

## `superseded_specs/`

| File | Original path | SHA-256 of original content (verified unchanged by the move itself; a SUPERSEDED notice was prepended afterward, so the file's current on-disk hash differs from this by design) | Superseded by | Archived |
|---|---|---|---|---|
| `GOD_MODE/ARCHIVE/superseded_specs/CANONICAL_SPEC.md` | `CANONICAL_SPEC.md` (repo root) | `10d1df8aded77283f8da2d551c9c5c7c9bb71b8bc0c3f57b9c2b971cc79ff07a` | `GOD_MODE/ACTIVE/God_Mode_Specification.md` | 2026-09-13 |
| `GOD_MODE/ARCHIVE/superseded_specs/RULINGS_ROUND5.md` | `RULINGS_ROUND5.md` (repo root) | see `GOD_MODE/ACTIVE/active_evidence/SPEC_AUTHORITY_INVENTORY.json` | `God_Mode_Specification.md` (does not carry its Held-Decisions content forward individually; archived as a unit alongside the spec it supported) | 2026-09-13 |
| `GOD_MODE/ARCHIVE/superseded_specs/SPEC_AUTHORITY_CLEANUP_REPORT_prior_2026-09-13.md` | `SPEC_AUTHORITY_CLEANUP_REPORT.md` (repo root, first version) | `daa3964bd062af6f525db477683a7830e3cd7c0a8c7f12f9a58af4adafa6a20d` (pre-notice content) | `GOD_MODE/ACTIVE/active_evidence/SPEC_AUTHORITY_CLEANUP_REPORT.md` (current version) | consolidated into this register 2026-09-13; originally archived under a since-removed `spec/archive/reports/` (superseded by this single `GOD_MODE/ARCHIVE/` hierarchy) |

**Reason for all three:** `SPEC_AUTHORITY_DECISION.md` (HOLD) found `CANONICAL_SPEC.md` stale in two named, quoted places (§C.4, §C.6) relative to the real, current, verified implementation. `God_Mode_Specification.md` carries forward every rule that passed alignment, corrects the two that didn't, and adds the two real mechanisms that had no rule at all — see its own §0 provenance section for the row-by-row accounting.

## `historical_evidence/`

| File | Original path | Reason |
|---|---|---|
| `GOD_MODE/ARCHIVE/historical_evidence/COMPATIBILITY_AUDIT.md` | `COMPATIBILITY_AUDIT.md` (repo root) | Round-4-era audit report; content superseded by later rounds' re-audits (not contradicted, just outdated as the live picture). |
| `GOD_MODE/ARCHIVE/historical_evidence/COVERAGE_TESTING_AND_EXTENSION.md` | `COVERAGE_TESTING_AND_EXTENSION.md` (repo root) | Planning document; its plan was executed and reported in `COVERAGE_EXPANSION_REPORT.md`. |
| `GOD_MODE/ARCHIVE/historical_evidence/COVERAGE_TEST_PLAN.md` | `COVERAGE_TEST_PLAN.md` (repo root) | The 14-test/8-category plan behind the coverage-expansion round; historical once executed. |
| `GOD_MODE/ARCHIVE/historical_evidence/END_TO_END_PROOF.md` | `END_TO_END_PROOF.md` (repo root) | Early-round evidence report (first real commit). |
| `GOD_MODE/ARCHIVE/historical_evidence/INTEROPERABILITY_UPGRADE.md` | `INTEROPERABILITY_UPGRADE.md` (repo root) | Evidence report for the interoperability-upgrade round. |
| `GOD_MODE/ARCHIVE/historical_evidence/REAL_APP_PROOF.md` | `REAL_APP_PROOF.md` (repo root) | Early-round evidence report. |
| `GOD_MODE/ARCHIVE/historical_evidence/STAGE_CROSS_REFERENCE.md` | `STAGE_CROSS_REFERENCE.md` (repo root) | Early-round evidence report. |
| `GOD_MODE/ARCHIVE/historical_evidence/UNIVERSAL_COMPATIBILITY.md` | `UNIVERSAL_COMPATIBILITY.md` (repo root) | Evidence report for the universal-composability round. |
| `GOD_MODE/ARCHIVE/historical_evidence/review.md` | `review.md` (repo root) | Earliest-round review notes. |
| `GOD_MODE/ARCHIVE/historical_evidence/COVERAGE_EXPANSION_REPORT.md` | `COVERAGE_EXPANSION_REPORT.md` (repo root) | Evidence report for the 15 coverage-expansion apps; content now summarized in `God_Mode_Specification.md`'s test-evidence citations and `APP_LIBRARY_MANIFEST.md`. |
| `GOD_MODE/ARCHIVE/historical_evidence/AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md` | `AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md` (repo root) | Evidence report for the round that produced the identity/session work; the operative contract now lives in `God_Mode_Specification.md` §6. |
| `GOD_MODE/ARCHIVE/historical_evidence/FULL_LIBRARY_STRESS_TEST.md` | `FULL_LIBRARY_STRESS_TEST.md` (repo root) | Origin report for `_namespace_route()`; the operative contract now lives in `God_Mode_Specification.md` §5. |

**Common reason for all twelve:** each is a real, valid, historical evidence report for a build round whose operative rules and current test evidence are now stated directly in `God_Mode_Specification.md` and its own evidence citations. None was found to conflict with anything; all are preserved as the historical record of how the current state was reached. Confirmed zero `.py` script references to any of these filenames before archiving (grep, all twelve, zero functional dependents).

## `obsolete_rules/`

| File | Reason |
|---|---|
| `GOD_MODE/ARCHIVE/obsolete_rules/spec_authority_check.py` | Its own checks assert a HOLD state (no active manifest exists) that stopped being true the moment God Mode activated. Superseded by `verification/godmode_alignment_check.py`. Preserved with its last real result (6/6 PASS) noted in its own header comment. |

## `duplicate_material/`, `unused_scripts/`, `abandoned_builds/` — empty, by evidence, not by default

- **Duplicate material:** SHA-256 comparison across every root-level `.md` file and every `verification/*.py` file found **zero exact duplicates**. Not searched further (generated build-output trees under `OUTPUT_LIBRARY/`/`library_build/` intentionally share content like `shared_lib.py` byte-for-byte across apps — that is the system working correctly, not accidental duplication, and is explicitly excluded).
- **Unused scripts:** every one of the 24 scripts under `verification/` was checked for cross-references (grep, both `.py` imports/invocations and `.md` documentation mentions). **Every script has at least one real reference** — including `gen_real_todo_app.py`, which is not imported anywhere but is a documented, directly-runnable tool per `verification/README.md`. None qualified as unused.
- **Abandoned builds:** `verification/gen_prove/*_v2/` was the leading candidate (looked stale — `interface_slots: []`, matches the "abandoned" profile). Checked directly: `verification/prove_generalization.py` regenerates these exact directories on every invocation, and `run_full_verification.py` section 4/8 runs it every time. **Confirmed live, disposable-by-design working scratch, not abandoned.** `verification/work/`, `fixtures/`, `functest_scratch/`, `full_stress_test/` are all `.gitignore`d, regenerable-by-design scratch for the same reason — not archived.
