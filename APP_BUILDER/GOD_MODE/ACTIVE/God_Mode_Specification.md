# GOD MODE SPECIFICATION

**Status:** DRAFT — produced against Sam's instruction to consolidate one authoritative ruleset. Not yet formally activated: `CANONICAL_SPEC.md` has not been deleted, edited, or marked superseded, no active-specification index has been created or changed, and nothing here has been treated as governing by any build or verification script. Activating this document (see §7) is a separate, later action.

**What this is:** the corrected, current, single ruleset for the app builder and capability library — built from `CANONICAL_SPEC.md`'s own Part C infrastructure contracts, with the two stale passages `SPEC_AUTHORITY_DECISION.md` identified corrected in place, and the two real mechanisms it found undocumented added. Nothing is deleted. `CANONICAL_SPEC.md` itself, and every other existing specification, remains on disk exactly as it was.

**Explicitly out of scope for this document:** front-door wiring, skins, and AWS deployment. These are real, open, tracked elsewhere (`SPEC_AUTHORITY_CLEANUP_REPORT.md`'s open issues, the Builder Ready-to-Deploy work), and deliberately not addressed here.

---

## 0. Provenance

Every rule below is one of exactly three things, marked as such:

- **[CARRIED]** — transcribed from `CANONICAL_SPEC.md` Part C, unchanged, because `SPEC_AUTHORITY_DECISION.md`'s rule-by-rule comparison found it PASS (matches the real, current, verified implementation).
- **[CORRECTED]** — was a **FAIL** row in `SPEC_AUTHORITY_DECISION.md` §C.2: the source spec asserted something the current, real, tested code no longer does. Rewritten here to match the verified implementation, with the original wording and the correction both stated.
- **[NEW]** — a real, implemented, tested mechanism `SPEC_AUTHORITY_DECISION.md` found had no corresponding rule anywhere. Added here for the first time, from direct inspection of the current source, the same discipline `CANONICAL_SPEC.md` Part C itself uses ("nothing here is invented ahead of the code").

Capability/project counts below use the **current** verified figures (`verification/verification_result.json`, this session): **300 capabilities across 49 projects**, not `CANONICAL_SPEC.md` C.1's stale **294** — the difference is real, additive capability work (e.g. `CAP-0210` admin-reset-password) done since C.1 was last written, not a discrepancy to explain away.

---

## 1. App Readiness & Library Admission — [CARRIED]

*(Source: `CANONICAL_SPEC.md` B.2, B.3 — unchanged, no FAIL found here.)*

Part A's twelve readiness states are implemented as a read-only translation layer over `build.py`'s own registry vocabulary (`candidate/approved/active/deprecated/retired/void`), which remains the source of truth. `compute_readiness()`/`compute_readiness_with_library()` return exactly one of the twelve names. **TEMPLATE_COMPLETE is not independently observable** in this data model — a template's capability bindings are already computable the instant it is `accepted`, so `compute_readiness()` reports the furthest state it can actually determine rather than inventing a pause.

`promote_to_library()` copies a build's own proof (`registry.json`, `app.json`, `locators.json`, `modules/`, `skin.json`, every relevant `reports/RUN-*.json`) into `library/<app_id>/`, only when the app has genuinely reached `active`/BUILT, and writes a `PROMOTED.json` marker. Auto-invoked at the end of every build run that reaches BUILT.

**Test evidence:** `verification/test_readiness.py`, 13-state/20-check proving table, part of the 29/29 `proving_table` figure reconfirmed this session.

---

## 2. The Capability Record Contract — [CARRIED]

*(Source: `CANONICAL_SPEC.md` C.1.)*

**Purpose.** The one shape every capability must satisfy to be admitted into a build — "Common Capability Contract v2."

**Components governed.** Every `CAP-XXXX.json` record and its paired `route.py`/`app.py` implementation.

**Mechanism.**
- `cap_record(...)` (`verification/gen_common.py:36`) — the record shape. v2 fields (`data_access`, `context_fields`, `contract_version`) nest inside `data_shape`, never as new top-level keys — backward-compatible with pre-v2 fixtures.
- `validate_v2_contract(cap_id, cap, app_dir)` (`build.py:603`) — the real compatibility gate for any capability declaring `contract_version == "2.0"`: enforces well-formed `data_access`/`context_fields`/`error_contract.error_codes`, and statically scans the capability's actual copied source for `_shared.load/save(...)` calls and `DATA_FILE_NAME =` assignments, raising a hard `Broken` if the source touches an undeclared entity or bypasses shared storage (`_RAW_PATH_BYPASS_RE`).
- `match_contract(expected, cap, impl)` (`build.py:520`) — the twelve-axis slot-to-capability compatibility check (required-input subset, input/output type equality, output-field subset, directional nullable-fields subset, permissions equality, `requires_auth` equality, dependency subset, error-code subset, directional security-constraints subset, side-effects equality, semver comparison).

**Test evidence.** `audit_dependency_graph.py`: CLEAN — 0 missing targets, 0 cycles, 0 contract violations, 0 hidden data access, **300 capabilities across 49 projects** (current figure). `verify_build.py` rows G1–G3, H-T3.

**Genuine gap, unchanged.** `_RAW_PATH_BYPASS_RE` recognizes only one bypass shape (`parents[2] / "data"`). It does not recognize an equivalent bypass of `data/blobs/` or `secrets/`. No capability does this today (confirmed by the same 0-hidden-access audit), but the static check does not structurally prevent a future one from doing so undetected. Recorded as open — not closed by this document.

---

## 3. The Shared Library Contract (CAP-0000) — [CARRIED]

*(Source: `CANONICAL_SPEC.md` C.2.)*

**Purpose.** The single, shared, byte-identical-across-every-project implementation every capability imports rather than reimplementing.

**Full public API** (`modules/CAP-0000/shared_lib.py`): `load`, `save`, `code_for_status`, `save_blob`, `load_blob`, `notify`, `audit`, `hash_password`, `is_common_password`, `verify_password`, `create_session`, `is_expired`, `validate_session`, `invalidate_session`, `generate_api_key`, `validate_api_key`, `generate_share_token`, `validate_share_token`, `_master_key`, `encrypt_value`, `decrypt_value`.

**Test evidence.** `security_tests.py` 45/45, `encryption_tests.py` 9/9 (real AES-256-GCM round-trip + tamper rejection), `document_tests.py` 12/12 (real binary-safe blob storage).

**Genuine gap, unchanged.** `_master_key()` is real (random, never hardcoded/committed) but minimal: one local key, no rotation, no per-tenant separation, no external KMS. Stated in the key's own docstring; not closed here.

---

## 4. The Host Dispatch Contract — [CARRIED]

*(Source: `CANONICAL_SPEC.md` C.3.)*

**Purpose.** The wire protocol connecting an incoming HTTP request to a capability's `handle()` and back to a real HTTP response.

**Mechanism.** `dispatch(subpath)` is the one catch-all route (`GET`/`POST` only — see gap below), keyed by `(method, path)` into `ROUTE_HANDLERS`. `_make_ctx(request)` resolves a real `Authorization: Bearer <token>` against `_shared.validate_session()` and a real `X-API-Key` against `_shared.validate_api_key()`, returning `{"user", "authenticated", "role", "token", "service"}` — never a hardcoded stub. A handler returning `{"__binary__": True, "data": ..., "content_type": ...}` is served via `Response(...)`. Any bare `{"error": "<string>"}` is normalized to `{"error": {"code": ..., "message": ...}}`.

**Test evidence.** `full_library_stress_test.py`: 329/329 (current figure), every route-bearing capability dispatches correctly across the merged system. `document_tests.py` 12/12 for the binary path.

**Genuine gap, unchanged.** `dispatch()` supports `GET`/`POST` only — no structural `PUT`/`DELETE`/`PATCH`. Every capability today expresses updates/deletes as `POST` to an action-shaped sub-route, fully tested; a REST-conventional verb would silently 404.

---

## 5. The Cross-App Isolation Contract — [CORRECTED]

*(Source: `CANONICAL_SPEC.md` C.4. This section's "genuine gaps" paragraph was the first FAIL row in `SPEC_AUTHORITY_DECISION.md` §C.2.)*

**Purpose.** No app's own build or test can see this: that merging every capability from every project into one running system produces zero URL-route collisions and zero data-file collisions.

**Mechanism — unchanged, carried forward:**
- `_namespace_route(route)` — rewrites every route to `/api/<slug><rest>`, making cross-*app* route collision structurally impossible.
- Same-app `(namespaced_route, method)` collision assertion in `add_capability()`.
- `RESERVED_SHARED_LIB_FILENAMES = frozenset({"auth_sessions.json", "blobs.json"})`, enforced in `add_capability()` — raises `AssertionError` if any capability's resolved data filename collides with CAP-0000's own two reserved internal-primitive filenames.
- `full_library_stress_test.py` — the whole-library enforcement mechanism: merges every real capability from every real project into one process and one shared `data/` directory.

**Mechanism — new since the source document, closing what it called an open gap:**
- `_namespace_data_filename(raw_filename)` (`verification/gen_common.py`) — every **domain** capability's own `data_filename` (not just CAP-0000's two reserved names) is namespaced by owning app slug (`f"{self.slug}__{raw_filename}"`).
- `_assert_all_data_filenames_namespaced()` — a generation-time assertion, run from `AppBuilder.finish()`, that scans every generated `.py` file under `shelf/implementations/` (excluding `shared_lib.py`, which is legitimately shared) for a data-filename literal lacking the `__` namespace separator and not on the short, explicit `_GLOBAL_DATA_FILENAMES` allowlist (the five build-metadata files — `locators.json`, `skin.json`, `app.json`, `registry.json`, `choice.json` — plus CAP-0000's own reserved names). Raises a hard `AssertionError` naming the offending file and literal.
- `KNOWN_SAFE_DATA_FILE_COLLISIONS` (`verification/full_library_stress_test.py`) — a named, per-entry-justified allowlist replacing an earlier inferred "harmless vs. real" severity heuristic. Exactly one entry today: `quiz_and_flashcards__quiz_and_flashcards.json`, justified by `reuse_capability_verbatim()` correctly preserving the original app's own embedded namespace when copying its capability byte-for-byte into a second app.

**What this corrects:** `CANONICAL_SPEC.md` C.4 states, as **currently open**: *"this guard only covers collisions against CAP-0000's own two reserved names. It does not protect against two arbitrary domain capabilities in different apps independently choosing the same data filename... Catching that broader class still depends on running `full_library_stress_test.py`."* **This is no longer true.** The mechanism above closes it structurally, at generation time, for every future capability — not just at whole-library merge time. Proven this session by real break/restore: a raw, unnamespaced data-filename literal was injected into a real capability (`habit_tracker`'s "List Habits"), the rebuild raised the real `AssertionError` naming the exact offending file and literal, the injection was reverted (`diff` confirmed byte-identical), and the rebuild succeeded cleanly.

**Test evidence.** `full_library_stress_test.py`, current figure: **329/329 pass, 0 shadowed, 0 other_fail, 1 allowlisted data-file collision (justified above), 0 unallowlisted (real-breakage) collisions.** `data_filename_namespacing_tests.py`: 21/21 — 10 mechanism-proof checks (including the false-positive-avoidance check for legitimate verbatim reuse) plus 10 named regression tests, one per real historical collision pair.

**Genuine gap, still open, correctly unchanged from the source document.** The reserved-filename guard (CAP-0000's own two names) and the new namespacing guard are two different mechanisms for two different collision classes; both are now closed. What remains open is unrelated to either: nothing in this contract governs *route-path* collisions against a future, not-yet-invented naming scheme — only the two collision classes actually observed and tested are covered.

---

## 6. The Identity & Session Contract — [CARRIED]

*(Source: `CANONICAL_SPEC.md` C.5. This is the real security mechanism Sam's instruction specifically called out to preserve.)*

**Purpose.** The wire-level contract behind the five identity types — what `ctx` actually contains and how its fields are resolved.

**Mechanism.** `create_session(..., role_source=(data_filename, id_field))` stores `_role_source` on the session row; `validate_session()` re-reads the *live* record from that file on every call, returning the *current* role, or `None` (fail closed) if the account no longer exists — never the role frozen at login time. `is_expired()` is the one shared lazy-evaluation check used identically by sessions, API keys, and share tokens.

**Test evidence.** `security_tests.py` 45/45, including live-resolution checks: promoting a user's live record grants access on an already-issued token with no re-login; demoting revokes it immediately; deleting the account invalidates the token (fail closed). `note_taking_pilot_security_tests.py` 64/64 (re-run this session, unchanged), directly exercising this contract: forged-token rejection, cross-user isolation, and real session revocation on password reset.

**Genuine gaps, unchanged.** No login rate-limiting/lockout exists anywhere in this library. `secure_vault` does not use any of these five identity types itself. The demo apps' admin-registration endpoint is a public, unauthenticated convenience in some builds, not a production pattern.

---

## 7. The App Assembly Contract (AppBuilder) — [CORRECTED]

*(Source: `CANONICAL_SPEC.md` C.6. Gap item (1) was the second FAIL row in `SPEC_AUTHORITY_DECISION.md` §C.2.)*

**Purpose.** How a new app type is composed, at generation time, from reusable capability engines.

**Mechanism — unchanged, carried forward.** Every `add_*` engine funnels through `add_capability()`, so every engine automatically inherits the Capability Record Contract (§2) and the Cross-App Isolation Contract (§5). `reuse_capability_verbatim()` copies another app's already-proven capability byte-for-byte, keeping the *original* app's namespace.

**Test evidence.** All 43 canonical + 6 composed + 15 coverage-expansion apps built through this mechanism, current figures: **43/43 READY, 6/6, 15/15.**

**What this corrects:** the source document's "genuine gaps" listed, as one undifferentiated limitation: *"an authenticated capability... cannot be the target of the primary journey slot, because the generic Playwright-driven journey has no way to carry an Authorization header."* This is **still exactly true** for the Playwright-driven browser journey (`CHK-020`) — untouched by this session's work, and correctly still binding: every app's journey must stay bound to a plain, unauthenticated, text-based capability. It is **no longer true** for the separate, generic **per-slot compute check** family (`CHK-1xx`+, `make_generic_compute_check()` in `build.py`) — see §8, a new contract this document adds because the source document did not distinguish these two mechanisms.

**Genuine gap, unchanged.** A real multipart file-upload capability (`add_document_storage_capabilities`) still cannot be the journey target either — the journey driver only knows how to type text and click, not attach a file.

---

## 8. The Authenticated Slot Proving Contract — [NEW]

**Purpose.** How the build-time proving mechanism verifies a slot-wired capability that requires authentication, without which any such capability's generic check would always and only fail with a real, correct 401 — a genuine, structural collision, not a bug, discovered and closed this session.

**Why this exists.** `slot()` (`verification/gen_common.py:109`) has always accepted a `requires_auth` parameter, and `add_capability()`'s call site has always wired it through correctly from `required_role`/`context_fields_override` — this was already correct before this session and is unchanged. What was missing was any use of that information at proving time: `make_generic_compute_check()` called every wired capability with no `Authorization` header at all, so wiring *any* authenticated capability to a UI slot was structurally impossible until now — confirmed as a universal, deliberate, unbroken pattern across the entire library (144 `add_capability()` calls checked; zero, before this session, combined `slot_id=` with an auth gate).

**Mechanism.**
- `_http_json()` (`build.py`) now accepts an optional `headers` dict.
- `_acquire_test_session(base_url, registry, app_dir, setup_token)` (`build.py`) — generic across the whole library, driven only by the standard engines' own consistent, real capability names (`"Bootstrap Admin"` / `"Register"` / `"Login"`), never an app slug or hardcoded route. Prefers Bootstrap Admin with a real setup token; falls back to an open Register if present and unauthenticated. Generates a fresh, real probe identity per process; caches one real Bearer token per running process (Bootstrap Admin is genuinely one-time — a second attempt gets a real 403 by design).
- `run_layer_one()` generates a fresh `secrets.token_urlsafe(32)` setup token per proving process and injects it as `BOOTSTRAP_SETUP_TOKEN` into the spawned app's own environment — deliberately overriding, not merely defaulting, so a real operator secret can never leak into a build run. Harmless for every app without a Bootstrap Admin capability.
- `make_generic_compute_check()` reads the capability's own `data_shape.requires_auth` and, when true, acquires and attaches a real Bearer token before probing.

**Test evidence.** Real build, real HTTP: `note_taking` re-wired with 3 real slots (`note_list`/`add_note`/`delete_note`, all `requires_auth: True`, confirmed by direct inspection of the generated template — contrasted with `todo_list`'s 7 slots, all `requires_auth: False`) — 5/5 checks pass, `locators.json` populated, `READY`. Break/restore: forcing an invalid token produced real `401 UNAUTHORIZED` failures on all three; restoring produced real passes on all three. Full-suite regression after the change: **zero numbers moved** across all 8 sections (`proving_table` 29/29, `canonical_apps` 43/43, `new_composed_apps` 6/6, `dependency_graph_audit` CLEAN 300/49, `functional_tests` 30/30, `coverage_expansion_apps` 15/15, `full_library_stress_test` 329/329, `overall` PASS).

**Genuine gap.** This mechanism covers the per-slot compute check only. It does not, and was not intended to, extend to the Playwright browser journey (`CHK-020`) — that remains governed by §7's carried-forward limitation.

---

## 9. The Arrangement Rendering Contract — [NEW]

**Purpose.** How a person's questionnaire choice of element position (`choice.json`'s `arrangement` array) actually reaches the rendered page, closing a gap the source document never mentions at all: until this session, `arrangement` was written into both `skin.json` and `locators.json` but read back by nothing — proven by a real A/B build and a byte-identical live HTTP diff, not inferred.

**Mechanism.** `_arrangement_css()`, present identically in both `gen_common.py`'s `HOST_APP_PY_TEMPLATE` and `gen_fixtures.py`'s independent `LOADER_APP_PY` (two separately-maintained host templates, both fixed). At process import time, reads `<app_dir>/locators.json`, generically iterates every top-level section's entries looking for any dict carrying both `selector` and `position` — no notion of "button" or any other element kind is built in — and maps `position` to a small `position_css` dict (`left`/`center`/`right` → real margin-based CSS), injecting the resulting `<style>` block into `INDEX_HTML` before `</head>`.

**Design constraint satisfied.** The read path is generic by construction: extending arrangement to a future element type (a menu, a screen choice) requires only that `locators.json` gain more `{selector, position}`-shaped entries — zero changes to `_arrangement_css()` itself.

**Test evidence.** `arrangement_rendering_tests.py`, 3/3 pass: two real disposable builds of the Todo fixture through the real `build.py`, differing only in `choice.json`'s `arrangement`; `locators.json` differs; live HTTP `/` differs; the `"left"` build's real rendered page contains the real `margin-left:0` rule the `"center"` build's does not.

**Explicitly out of scope, deferred, not part of this contract:** navigation menu order (drag-to-reorder), which screen is the entry point, and all non-button/non-tested element movement. The mechanism is adaptable to them by data; this contract does not certify that it has been exercised for anything but the button case actually tested.

---

## 10. Numbering — observed pattern, not a written rule

No `NUMBERING.md` exists anywhere on this machine — confirmed by exhaustive filesystem search, more than once, across this whole engagement. This section records what is **observed and consistent** in the real generated capabilities, not a rule anything enforces:

One 100-number `CAP-XXXX` block per canonical app, sequential: `0100` `todo_list`, `0200` `note_taking`, `0300` `habit_tracker`, `0400` `calendar_and_scheduling`, … through `4300` `recipe_and_meal_planning`; coverage-expansion apps use `8000`–`9999`. Zero collisions across this range, confirmed independently by both `audit_dependency_graph.py` (CLEAN, 300 capabilities/49 projects) and `full_library_stress_test.py` (329/329, 0 shadowed).

**This document does not promote this pattern into a binding rule.** Doing so would be inventing a requirement the evidence only shows as an observed convention, not a written specification — exactly the discipline Part C of `CANONICAL_SPEC.md` itself commits to ("nothing here is invented ahead of the code"). If Sam wants this made binding, that is a decision to state explicitly, not one this document makes on its own.

---

## 11. What is explicitly NOT covered here

- **Front-door wiring** (the questionnaire → `choice.json` contract for a real, uploaded front-door package) — no such package exists on this machine (confirmed, repeatedly, by exhaustive search); this document makes no claim about it.
- **Skins** — only `skin-001` exists; not addressed.
- **AWS / deployment** — gated on decisions named elsewhere (`PRODUCT_DEPLOYMENT_DECISIONS.md`); not addressed.
- **The four externally-named documents** (the Bible, `BUILD_PY_SPEC_v1.md`, `NUMBERING.md`, `TEMPLATE_STANDARD.md`) — still confirmed absent from this machine. They are no longer treated as authorities over this document: Sam ruled on 2026-09-15 that god mode is the authority, and every reference that pointed at them has been repointed here. Alignment with them is not claimed and is not required.

---

## 12. Activation status

**Activated 2026-09-15 by Sam's ruling: god mode is the authority.** The Script Standard
and the Build Chain Standard sit under `ACTIVE/active_standards/` and are in force; every
reference in this tree and in the build pack that previously pointed at the Bible now
points here. `CANONICAL_SPEC.md` sits in `ARCHIVE/superseded_specs/`.

What follows is the record of the state this document was drafted in, kept because it is
what was true at the time and the activation above is what changed it:

- `CANONICAL_SPEC.md` is untouched — not edited, not marked superseded, not archived.
- No `spec/active/` directory or manifest has been created for this document.
- No build or verification script references this document's filename.
- Nothing was deleted at any point in producing it.

Making this the governing document — updating an active-specification index, formally marking `CANONICAL_SPEC.md` superseded (not deleted), and wiring any script that should cite it — is a distinct, separate action for Sam to direct explicitly, the same discipline `SPEC_AUTHORITY_DECISION.md`'s own HOLD rested on: a decision like that is made once, deliberately, not as a side effect of drafting the document it would act on.
