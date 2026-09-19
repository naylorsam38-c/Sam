SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Reason: Historical evidence report for a completed build round. Its operative rules and current test evidence are now stated directly in God_Mode_Specification.md and GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md. Nothing in this document was found to conflict with the current implementation; preserved as the historical record of how the current state was reached.
Original path: `STAGE_CROSS_REFERENCE.md` (repo root)
Archived: 2026-09-13

---

# Stage-by-stage input/output cross-reference — build.py, round 6

Every field named below is read directly from `build.py`'s source (function and line references
given), not inferred or assumed. This covers the three real stages `build.py` itself implements
end to end in one process, one script, one real run: **assemble → prove → readiness/library**. See
`CANONICAL_SPEC.md` Part B.7 for the honest scope boundary — harvesting and template generation are
upstream stages this file does not cover, because their real code isn't part of this session.

A handoff is "proven" here in the strict sense Sam asked for: the exact file + field a stage
writes is the exact file + field the next stage reads, confirmed by grep against the real source
lines, not by two documents merely agreeing in prose.

⸻

## Stage 0 (external, before build.py runs at all) — what must already exist

| What | Where | Written by |
|---|---|---|
| The approved app-type list | `APPS_LIST.md` (bulleted) | hand-maintained / harvest (not in this session) |
| One template per app type | `templates/<slug>.json`, `accepted: true` | hand-authored in this session's fixtures; `make_templates.py` upstream, not built |
| Approved shelf capabilities | `shelf/capabilities/CAP-*.json` | hand-authored in this session's fixtures; `harvest.py` upstream, not in this session |
| Approved shelf implementations | `shelf/implementations/<IMPL-id>.json` + payload dir | same as above |
| The person's choice | `choice.json` | hand-written (front door out of scope, per Sam's 2026-09-11 decision) |

⸻

## Stage 1 — ASSEMBLE (`stage1_assemble()`, build.py:576–759)

| Step | Reads (file → field) | Writes (file → field) | Real guard if missing/wrong |
|---|---|---|---|
| 1. Read choice | `choice.json` → `app_type`, `skin_id`, `skin_version`, `arrangement`, `branding.name`, `branding.color` | — | `BROKEN choice <field>` / `BROKEN choice file` / `BROKEN choice unreadable` |
| 2. Validate app_type | `choice.json.app_type` against `APPS_LIST.md`'s bullet list | — | `BROKEN choice app_type` |
| 3. Resolve template | `templates/<slugified app_type>.json` → `accepted`, `required_capabilities`, `entry_screen_name`, `entry_route`, `interface_slots[]`, `health_endpoint`, `start_command`, `port`, `test_command` | — | `BROKEN template not found <slug>` / `BROKEN template unreadable <slug>` / `BROKEN template not accepted <slug>` |
| 4. Allocate APP id | `registry.json` (canonical) → next unused `APP-nnn` | `registry.json` (canonical) → new `{id, name, status: candidate}` application entry | — |
| 5. Copy shelf parts | `shelf/capabilities/<CAP-id>.json` → `status`, `qualification.status`, `implementations[]`; `shelf/implementations/<IMPL-id>.json` → `status`, `release.approved`, `capability_id`; the IMPL's payload directory | `builds/<APP-id>/modules/<CAP-id>/` ← copied payload | `BROKEN no approved IMPL <cid>` (no usable CAP, or no exactly-one active+approved IMPL) |
| 6. Lay skin | `choice.json` → `skin_id`, `skin_version`, `branding`, `arrangement` | `builds/<APP-id>/skin.json` → `{skin_id, skin_version, branding, arrangement}` | — |
| 7. Wire SCR/BTN + contract match | template's `interface_slots[]` → `target_capability`, `name`, `slot_id`, `selector`, `expected_contract`; the loaded CAP/IMPL's `data_shape`, `permissions`, `requires_auth`, `dependencies`, `handled_errors`, `security_constraints`, `side_effects`, `min_version` | in-memory `screen`, `buttons[]` records; `builds/<APP-id>/locators.json` → `{screens: {SCR-id: {route}}, buttons: {BTN-id: {selector, slot, position}}}` | `BROKEN template entry_screen_name`; `BROKEN template slot name <slot_id>`; **`HELD <BTN-id> -> <CAP-id>: <reason>`** if `match_contract()` (the 12-axis check, H-T3-loosened on 2 of the 12) fails |
| 9. Registry + invariants | the step-7 in-memory records | `builds/<APP-id>/registry.json` → `{applications:[...], screens:[...], buttons:[...], capabilities:[...], implementations:[...]}` (§3.3–3.7 shapes exactly) | `verify_registry_invariants()` — 13/13 must pass or `BROKEN registry <which invariant>` |
| 10. app.json + locators.json | template's `start_command`, `port`, `health_endpoint` | `builds/<APP-id>/app.json` → `{start, port, health}` | `BROKEN template start_command/port` |
| 11. Template's own tests | `test_command` from the template | real subprocess run, stdout/exit code only (not persisted as its own file — captured in the run's own terminal output) | `BROKEN template has no tests` / `BROKEN template test_command must be an argument list` / `BROKEN template tests failed code <n>` |
| 12. Return | — | returns `(app_id, app_dir, registry, locators)` **in-process, directly into stage two — no file round-trip for this handoff** | — |

**Handoff into Stage 2 is proven by construction**: `main()` (build.py:1531–1548) passes the exact
same `app_id, app_dir, registry, locators` objects `stage1_assemble()` returned straight into
`stage2_prove()` as Python call arguments — there is no serialize/re-read step here to drift, only
the two on-disk artifacts (`registry.json`, `app.json`, `locators.json`) stage two also re-reads
independently from disk on every one of its own repair-loop iterations (see below), so a filesystem
inconsistency would surface as a real failure, not be papered over by reusing stale in-memory state.

⸻

## Stage 2 — PROVE (`stage2_prove()` / `run_layer_one/two/three()`, build.py:970–1263)

Runs a loop: `run_layer_one()` (real HTTP + real browser proof) → on failure, `run_layer_two()`
(shelf-pattern or structural repair) → if no repair, `run_layer_three()` (model-driven gap, only if
`ALLOW_LAYER3`) → repeat, up to `MAX_RESTARTS`.

| Step | Reads | Writes | Real guard |
|---|---|---|---|
| Start the app | `builds/<APP-id>/app.json` → `start`, `port`, `health` | real `subprocess.Popen` of the assembled app on a free port | `BROKEN app did not start` if health never returns 200 within `HEALTH_TIMEOUT_SECONDS` |
| Derive checks | `builds/<APP-id>/registry.json` → `capabilities[].category`, `.data_shape.output.fields`, `.id`; `buttons[].capability_id`; `implementations[].source.entrypoint`; the module file itself via AST (`_extract_route_meta()`) for `ROUTE`/`METHOD` constants, never executed; `locators.json` → button selectors for the one hand-written browser check | real HTTP calls (`_http_json()`) and one real Playwright browser interaction per check | a compute capability with no declared `ROUTE`/`METHOD` gets **no check generated** — skipped, never guessed |
| Run checks | — | `reports/RUN-<nnnn>.json` → `{run, checks_passed[], checks_failed[{check, claim, message, module, wants, is_browser}], browser_check_present, browser_check_passed}` — **written unconditionally**, before any repair/gap decision is made | — |
| Record run | the check results above | `run_ledger.jsonl` → appends one line; an **`{run, app, outcome, checks_passed, checks_failed, browser_check_passed}` record only on 4 of the exit paths** (BUILT, regression, restart ceiling, no/failed-browser-with-zero-other-failures) — loop guard / repeated gap / layer-three-disabled HELD write no outcome record (confirmed by reading the code, not assumed — see `RULINGS_ROUND5.md` / review.md Round 5) | — |
| On BUILT | — | `builds/<APP-id>/registry.json` → `applications[0].status = "active"`; `registry.json` (canonical) → same app's `status = "active"` | prints exactly `BUILT` |
| On repair | `shelf/aliases.json` (pattern map) or a full `shelf/capabilities/*.json` sweep (`find_structural_matches()`) | may copy a new payload into `builds/<APP-id>/modules/<CAP-id>/`, restarts the loop as a new `RUN-nnnn` | `BROKEN loop guard <chk> still fails after <part>`; `BROKEN regression <chk>`; `BROKEN restart ceiling` |
| On gap (layer 3) | `LAYER3_ENDPOINT`/`LAYER3_MODEL`/`LAYER3_CREDENTIAL` (config block) | real HTTP POST per candidate framing; `run_ledger.jsonl` → gap record `{gap, run, check, message, missing, proves_it, candidates_tried, candidates_passed}` | `HELD <gap-id> ... layer three disabled` if `ALLOW_LAYER3=False`; `BROKEN repeated gap` if the same gap recurs across invocations |
| On any exit | — | `registry.json` (canonical) → `applications[].status` stays/returns to `"candidate"` for anything short of BUILT (`set_app_status(app_id, "candidate")` in `main()`'s except blocks) | never `"void"` here — `"void"` is Stage 1-only (a rejected allocation before an app ever started) |

**Handoff into Stage 3 is proven by construction, not assumed**: `main()` (build.py:1550–1553)
calls `stage3_readiness_and_promote(app_id)` immediately after Stage 2 returns or raises, on
**every** path — the same `app_id` Stage 1 allocated, still in scope. Stage 3 does not receive
Stage 2's in-memory results directly; it deliberately **re-derives everything from disk**
(`registry.json`, `run_ledger.jsonl`, `reports/*.json`) — this is intentional, not a missed
handoff: it's what makes `--readiness`/`--promote` usable as a standalone query days later, against
files a completed run already left behind, without needing the run still in memory.

⸻

## Stage 3 — READINESS + LIBRARY (`stage3_readiness_and_promote()`, build.py:1490–1511, folded in
round 6 from round 5's separate `readiness_and_library.py`)

| Step | Reads | Writes | Real guard |
|---|---|---|---|
| Re-establish context | `choice.json` → `app_type` (re-read fresh, independent of Stage 1's in-memory copy) | — | prints `readiness  skipped -- choice.json's app_type could not be re-read` and stops, rather than guessing, if this fails |
| Check for promotion | `registry.json` (canonical) → this app's `status` | if `"active"`: `promote_to_library()` — copies `builds/<APP-id>/` → `library/<APP-id>/` (registry.json, app.json, locators.json, skin.json, modules/), plus every `reports/RUN-*.json` whose ledger entry names this app, into `library/<APP-id>/evidence/`, plus `library/<APP-id>/PROMOTED.json` → `{app_id, promoted_from, evidence_runs, canonical_status_at_promotion}` | refuses (prints `promotion refused  <reason>`, no files touched) if status isn't `active`, or the app isn't in the registry, or there's no build directory |
| Compute readiness | `templates/<slug>.json` → `accepted`, `required_capabilities`; `shelf/capabilities/*.json` + `shelf/implementations/*.json` (via the **same** `read_shelf_cap()`/`cap_is_usable()`/`active_impl_for()` Stage 1 itself uses — not a reimplementation, so "readiness says bound" can never drift from "assembly would actually succeed"); `registry.json` (canonical); `run_ledger.jsonl`; `reports/RUN-*.json` (fallback when no ledger outcome record exists, net of runs already claimed by a different app) | prints `readiness  <STATE>  --  <reason>`, one of Part A §18's twelve values | — (read-only; never invents a state it can't support from what's on disk) |

⸻

## The honest gap this table exposes, not hides

Two of `run_ledger.jsonl`'s exit paths (loop guard, repeated gap, layer-three-disabled HELD) never
write an `{app, outcome}` record — only Stage 3's fallback to `reports/RUN-*.json` (which Stage 2
writes unconditionally, before deciding what to do with a failure) recovers the correct
classification for those runs. This was a real bug, found by reading the code and confirmed by
running it (`row17_loop_guard` and `row21b_browser_check_fails` both mis-reported `START_FAILED`
before the fix — see `review.md`, Round 5). It's listed here, in the cross-reference itself, not
just in a changelog, because a cross-reference that hides its own known sharp edge isn't actually
proving the handoffs — it's declaring them proven.

⸻

## What this does NOT cover (see `CANONICAL_SPEC.md` Part B.7)

`harvest.py` (real GitHub/Gemini harvesting into `shelf/`) and `make_templates.py` (template
generation into `templates/`) are upstream of Stage 1 and are not part of this session's working
files — Stage 1 assumes their outputs already exist on disk. No handoff into or out of those two
stages is claimed as proven here.
