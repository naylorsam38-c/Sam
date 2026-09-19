# RULE REGISTER

Every operative rule currently in force, by source section of `GOD_MODE/ACTIVE/God_Mode_Specification.md`, with its provenance marker (`[CARRIED]` / `[CORRECTED]` / `[NEW]`, defined in that document's own §0).

| § | Rule | Provenance | Status |
|---|---|---|---|
| 1 | App Readiness & Library Admission (12-state translation over `candidate/approved/active/deprecated/retired/void`; `promote_to_library()` auto-invoked on BUILT) | CARRIED | Active |
| 2 | Capability Record Contract (`cap_record`, `validate_v2_contract`, `match_contract`'s thirteen axes — a 13th, attach-point coverage against `cap['attaches_to']`, added 2026-09-19 per Rule G below) | CARRIED, 13th axis NEW | Active |
| 3 | Shared Library Contract (CAP-0000's full public API, byte-identical across projects) | CARRIED | Active |
| 4 | Host Dispatch Contract (`dispatch`, `_make_ctx`, binary-response path, standard error shape) | CARRIED | Active |
| 5 | Cross-App Isolation Contract — route namespacing, reserved-filename guard, **plus the new domain-filename namespacing + generation-time assertion** | CORRECTED | Active |
| 6 | Identity & Session Contract (live role re-resolution, fail-closed on deleted account) | CARRIED | Active |
| 7 | App Assembly Contract — `AppBuilder` engine set, **with the journey-vs-compute-check auth distinction now stated** | CORRECTED | Active |
| 8 | Authenticated Slot Proving Contract (`_acquire_test_session`, `BOOTSTRAP_SETUP_TOKEN` injection) | NEW | Active |
| 9 | Arrangement Rendering Contract (`_arrangement_css`, generic `{selector, position}` read path) | NEW | Active |
| 10 | Numbering — observed 100-block-per-app pattern | **Superseded** by `GOD_MODE_RULE_NUMBERING.md` (see below); the 100-block scheme is void | Retired as an observation |

## Rules in force outside the specification's numbered sections

| Rule | File | Provenance | Status |
|---|---|---|---|
| Harvest Admission (A one stack Django+PostgreSQL — rewritten 2026-09-19, was Flask+PostgreSQL; B published API docs; C permissive licence; D structural match; E one source per app; F write the part where no exemplar exists; G attach points declared at admission via ATTACH_POINTS.md, MIN_HOOKS enforced; payload runs as its source wrote it, unproven for Django — see that file's "payload question" section) | `GOD_MODE/ACTIVE/GOD_MODE_RULE_HARVEST_ADMISSION.md` | NEW | Active — partially enforced, see that file's enforcement table |
| Numbering (N1-N6; capabilities numbered once globally; the 100-block-per-app scheme is void) | `GOD_MODE_RULE_NUMBERING.md` | NEW | Active |

## Rules explicitly retired (not deleted — see `ARCHIVE_REGISTER.md`)

| Former rule | Where it lived | Why retired |
|---|---|---|
| "Cross-app domain-filename collisions require manually running `full_library_stress_test.py`; no generation-time guard exists" | `CANONICAL_SPEC.md` §C.4 "genuine gaps" | Factually superseded — see Rule §5 above. The *document* is archived as a whole; this specific claim is the reason. |
| "An authenticated capability cannot be the target of ANY auto-generated check" (stated without distinguishing journey vs. compute-check) | `CANONICAL_SPEC.md` §C.6 "genuine gaps" (1) | Narrowed to correctly apply only to the Playwright journey — see Rule §7/§8 above. |
| Spec-authority HOLD-state assumptions (no active manifest may exist) | `verification/spec_authority_check.py` | The state it asserted (HOLD) is no longer current now that God Mode is active. |

## Rules still correctly recorded as open (not closed by this activation)

- No login rate-limiting/lockout anywhere in the library (§6).
- `secure_vault` uses none of the five identity types (§6).
- `_master_key()`: one local key, no rotation, no KMS (§3).
- `dispatch()` supports `GET`/`POST` only (§4).
- `_RAW_PATH_BYPASS_RE` covers one bypass shape only, not `data/blobs/`/`secrets/` (§2).
- A multipart file-upload capability still cannot be a journey target (§7).
- Harvest admission Rules A (PostgreSQL half), E and F are in force but not
  checked by `check_form_godmode.py` — the form has no `datastore` field and no
  harvested-vs-written field (§Harvest Admission).
- `build.py`'s `_extract_route_meta` reads `ROUTE`/`METHOD` literals; Flask
  declares routes by decorator. Unresolved (§Harvest Admission).


## Standards in force

Locked documents that govern how work is built and proved, rather than what may
enter the shelf. Both are active and neither is superseded.

| Standard | Locked | Governs |
|---|---|---|
| `ACTIVE/active_standards/SCRIPT_STANDARD.md` | 2026-09-08 | Every script written for this system, by anyone. Seven hard rules, three-layer architecture, output contract, environment hygiene, verification before delivery. |
| `ACTIVE/active_standards/BUILD_CHAIN_STANDARD.md` | 2026-09-08 | The one command and the five scripts under it. Terminal states, loop guard, candidate generation, handoff records, and the breaks that must be demonstrated. |

Where the two disagree with anything else in this tree, the Script Standard's
own rule applies: hand it to whoever is building, and if they push back the
answer is no. The Build Chain Standard defers to god mode where they disagree. It no
longer defers to the Bible, which is not in this tree and is not an
authority over anything here.

**Repointed 2026-09-15.** The Build Chain Standard was written as a companion
to THE BIBLE v3, which is not in this tree. Every Bible reference now points at
the Script Standard instead, and each claim was verified to exist there before
the reference was changed — none were mapped on assumption.

Three had no equivalent and were not invented. Two of them (a repair never
resumes; a regression stops the chain) the chain states and enforces itself, so
they stand on their own.

**The third is closed as of 2026-09-15.** `watch.py` now has a full
specification in the Build Chain Standard — twenty-two checks across three
groups: did the run really run, was it actually proved, and did the loop behave.
It was written fresh at Sam's direction and derived from god mode; it is not a
recovery of the missing document and claims no lineage to it. The script itself
has not been built, so a chain reaching BUILT today still has not been audited.

The passage below is the record of the hole while it was open. `watch.py` is named in the
script table and in the BUILT condition and cannot be built from what is here.

Until it is written, a chain reaching BUILT has passed layer one and a level-1
journey and has **not** been audited by `watch.py`.
