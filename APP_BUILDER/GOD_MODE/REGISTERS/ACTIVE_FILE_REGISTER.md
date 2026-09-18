# ACTIVE FILE REGISTER

Every file or directory this register lists is the current, authoritative location for that content. Nothing listed here was copied — each entry was moved from its prior location; the move was verified byte-identical (SHA-256 compared before and after) before this register was written.

## Governing specification

- `GOD_MODE/ACTIVE/God_Mode_Specification.md` — the single active ruleset. Supersedes `CANONICAL_SPEC.md` (archived, see `ARCHIVE_REGISTER.md`). Moved from repo root, byte-identical (verified).

## Standing rules adjacent to the specification

Build/library rules in force, kept beside `God_Mode_Specification.md` because
they govern admission and numbering rather than sitting inside a numbered
section of it.

- `GOD_MODE/ACTIVE/GOD_MODE_RULE_HARVEST_ADMISSION.md` — what may enter the
  shelf. Supersedes the earlier proposed version that admitted by framework
  alone and left the payload question open.
- `GOD_MODE_RULE_NUMBERING.md` — N1-N6.

## `active_rules/` — still-open decision and planning documents

Not build/library rules themselves; these are live, unresolved decision-tracking documents this document set stays adjacent to `God_Mode_Specification.md` because they are not superseded, not historical, and still in active use.

- `GOD_MODE/ACTIVE/active_rules/PRODUCT_DEPLOYMENT_DECISIONS.md`
- `GOD_MODE/ACTIVE/active_rules/NEXT_PHASE_READINESS.md`
- `GOD_MODE/ACTIVE/active_rules/PILOT_OWNER_DECISION_SHEET.md`
- `GOD_MODE/ACTIVE/active_rules/PILOT_OWNER_SETUP_SHEET.md` (itself mid-revision, uncommitted vs. `HEAD` — see its own header)
- `GOD_MODE/ACTIVE/active_rules/PILOT_QUESTIONS_AND_INPUT_SPEC.md` (same)
- `GOD_MODE/ACTIVE/active_rules/API_KEY_AND_INPUT_REQUIREMENTS.md`

## `active_standards/` — real, tested security mechanism specifications

The two documents specifically preserved per Sam's explicit instruction to keep real security mechanisms active, not archived.

- `GOD_MODE/ACTIVE/active_standards/IDENTITY_AND_LOGIN_TYPES_SPEC.md` — the five identity types' human-facing purpose/capabilities framing; wire-level contract now lives in `God_Mode_Specification.md` §6.
- `GOD_MODE/ACTIVE/active_standards/PRIVATE_PILOT_SAFETY_MILESTONE.md` — the Bootstrap Admin token-gating / Login-failure-journey security review; its plan is now implemented (§8 of `God_Mode_Specification.md`).
- `GOD_MODE/ACTIVE/active_standards/SCRIPT_STANDARD.md` — **LOCKED 2026-09-08.**
  What every script written for this system must meet, by anyone. Hard rules
  (no mocks, testing means running it, config block, do not guess, do not
  reconstruct a document from memory, touch only what was asked, deliver only
  after testing passes), the three-layer architecture, the repair-hides-nothing
  rule, the output contract, environment hygiene, and verification before
  delivery. Not advice: a script that does not meet it is not finished.
- `GOD_MODE/ACTIVE/active_standards/BUILD_CHAIN_STANDARD.md` — **LOCKED
  2026-09-08.** The machinery that runs under the Script Standard. One command,
  three terminal states (BUILT / HELD / BROKEN), five scripts, candidate
  generation, handoff record contracts, and the seven breaks the chain must be
  seen to produce before delivery. Supersedes the earlier four-script build
  chain spec, which did not include `watch.py`.

## `active_evidence/` — hand-authored evidence reports (not auto-regenerated)

- `GOD_MODE/ACTIVE/active_evidence/SPEC_AUTHORITY_DECISION.md`
- `GOD_MODE/ACTIVE/active_evidence/SPEC_AUTHORITY_CLEANUP_REPORT.md`
- `GOD_MODE/ACTIVE/active_evidence/SPEC_AUTHORITY_INVENTORY.json`
- `GOD_MODE/ACTIVE/active_evidence/SPEC_AUTHORITY_INVENTORY.md`
- `GOD_MODE/ACTIVE/active_evidence/APP_BASELINE_ALIGNMENT_REPORT.md`

**Not moved into `active_evidence/`, deliberately:** `verification/verification_result.json`. This file is live-regenerated in place by `run_full_verification.py` on every run; moving it would break that script's write path. It remains the authoritative live evidence source, referenced (not copied) by `godmode_alignment_check.py`.

## `active_apps/` — manifest only, not a physical copy

Physically relocating the real, built app library (127+ MB across `OUTPUT_LIBRARY/`, `verification/library_build/`, `verification/coverage_expansion/`) was deliberately **not** attempted: `consolidate_library.py`, `run_full_verification.py`, and `build_batch.py` all reference these directories by fixed relative path, and moving them would break the real build/verification pipeline for no benefit. See `GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md` for the real, current locations of all 43 canonical + 6 composed + 15 coverage-expansion apps.

## Left in place, deliberately not relocated

- `README.md` (repo root) — trivial two-line placeholder, unclear purpose. Per the standing instruction ("nothing with uncertain purpose gets archived automatically"), left exactly where it is rather than guessed into either ACTIVE or ARCHIVE.
- `verification/README.md`, `verification/vendor/README.md` — real, active, operational instructions tightly coupled to their directories (a person is told to `cd verification && python3 bootstrap.py` from that README, in that location). Relocating either would break real operational discoverability for no benefit. Confirmed active by content inspection, referenced here rather than moved.
- All `build.py`/`verification/*.py` scripts, `OUTPUT_LIBRARY/`, `NEW_APPS_FROM_LIBRARY/`, `verification/library_build/`, `verification/coverage_expansion/` — the real, working application and its real, built output. Out of scope for relocation under this work order (application code / generated output, not specification material).
