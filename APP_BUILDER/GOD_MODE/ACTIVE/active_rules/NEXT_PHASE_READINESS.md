# Next-Phase Readiness Assessment

Read-only inspection of the accepted, verified system (`CANONICAL_SPEC.md` Parts A–C, `IDENTITY_AND_LOGIN_TYPES_SPEC.md`, `AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md`, and the actual repository state as of commit `22e5f92`). No code, test, generated app, or specification was changed to produce this document. Every claim below cites the exact file/line/command that supports it; nothing is inferred from memory or invented because it "should" be true of a system like this.

**Scope note, stated up front**: this system is a *capability library and proof harness* — 43 canonical + 6 composed apps in `OUTPUT_LIBRARY/`/`NEW_APPS_FROM_LIBRARY/`, each a standalone, single-tenant, unauthenticated demo app (`COMPATIBILITY_AUDIT.md:47`: *"every app is single-tenant and unauthenticated by construction"*) — not a deployed product. Every item below is evaluated against that reality, not against what a SaaS product roadmap would assume.

---

## 1. Security, isolation, or correctness risks still worth addressing

| # | Item | Evidence | Risk/impact | Required before production? | Dependencies | Size | Acceptance tests |
|---|---|---|---|---|---|---|---|
| 1.1 | Flask development server used for every app | `verification/gen_common.py:750`: `app.run(host="127.0.0.1", port=args.port)` — Flask's own documentation states this server is not production-safe. No `gunicorn`/`uwsgi`/`waitress` in `verification/requirements.txt` (grep confirms zero occurrences); zero `Dockerfile`/`docker-compose`/`Procfile`/`*.service` anywhere in the repo | High if any app is ever exposed beyond localhost: no concurrency handling, no crash resilience, explicitly unsupported for real traffic by Flask's own docs | **Yes** — this blocks any real deployment claim regardless of feature completeness | None — purely additive (a WSGI wrapper around the existing Flask `app` object) | Small | Start one app via `gunicorn app:app` instead of `python3 app.py`; run `functional_tests.py`'s existing checks against it unmodified; confirm identical HTTP responses |
| 1.2 | No TLS/HTTPS anywhere | `grep -rli "ssl_context\|https\b"` across `gen_common.py`/`build.py`: zero matches | High if exposed beyond localhost: credentials (passwords at registration, session tokens, API keys) travel in plaintext | **Yes**, for anything beyond localhost | 1.1 (a real WSGI/reverse-proxy setup is the natural place to terminate TLS) | Small–Medium (depends on chosen deployment topology) | A real HTTPS request against the deployed app returns the same response as the current HTTP one; an HTTP request is rejected or redirected |
| 1.3 | No rate-limiting or brute-force lockout on login | Already recorded honestly in `IDENTITY_AND_LOGIN_TYPES_SPEC.md`'s "Honest limitations" and `verification/gen_common.py:273`; re-confirmed absent by fresh grep this pass | Medium: credential-stuffing/brute-force against `identity_and_access_demo`'s real password hashes is unthrottled | **Yes**, before any auth-bearing app is exposed publicly | The identity engine (`add_auth_capabilities`) already exists and is where this would attach | Small–Medium | A scripted burst of N failed logins against one account is throttled/locked after a defined threshold; a real test proving the Nth+1 attempt is rejected regardless of correct credentials |
| 1.4 | No CSRF protection | `verification/gen_common.py:273` docstring names this gap explicitly; confirmed absent by fresh grep | Low today (no browser-session-based auth flow exists that a CSRF attack would target — sessions are Bearer-token, not cookie-based), but relevant if a future capability adds cookie-based auth | Conditional — required only if cookie/session-based (not Bearer-token) auth is ever added | None currently | Small, if/when needed | N/A until cookie-based auth exists — flagged, not designed |
| 1.5 | Residual cross-domain data-filename collision (see item 2 below — kept separate per your explicit instruction) | — | — | — | — | — | — |
| 1.6 | `_master_key()` single local key, no rotation, no external KMS | `CANONICAL_SPEC.md` C.2 "Genuine gaps"; `verification/gen_common.py` `_master_key()` docstring | Medium: a compromised host exposes both ciphertext and key together; no rotation story if a key is ever suspected compromised | Conditional — required before storing anything genuinely sensitive for real users; not required for the current demo/proof scope | None blocking; a real fix needs a decision on KMS provider (business/infra decision, not a code question) | Medium–Large (real KMS integration) | A rotated key still decrypts old ciphertext (re-encrypted under the new key) and a real KMS round-trip test |
| 1.7 | No account-recovery ("forgot password") flow | Not found anywhere — `IDENTITY_AND_LOGIN_TYPES_SPEC.md` defines register/login/logout/me only | Low today (demo scope, test-created accounts); would be a real gap for actual users | Conditional — required before real end users manage their own accounts | Needs an email/notification channel (`notify()` exists generically but no real email transport is wired to it) | Medium | A user who "forgets" a password can regain access via a real, tested token-based reset flow |

## 2. The documented cross-domain filename collision limitation

**Exact current state** (`CANONICAL_SPEC.md` C.4, "Genuine gaps," verified live this session, not restated from memory):

- The specific, historical collision (a domain capability accidentally reusing one of CAP-0000's own internal primitive filenames) now has a real, generation-time guard: `RESERVED_SHARED_LIB_FILENAMES = frozenset({"auth_sessions.json", "blobs.json"})`, enforced in `add_capability()` (`verification/gen_common.py`).
- **What remains open, confirmed present by direct inspection this session**: `course_enrollment_hub` (`verification/library_build/course_enrollment_hub/shelf/implementations/CAP-9701..9704/`) and `multiplayer_game` (`verification/coverage_expansion/library_build/multiplayer_game/shelf/implementations/CAP-9012/CAP-9013/`) both still declare `DATA_FILE_NAME = "sessions.json"` for two entirely unrelated concepts (class sessions vs. game sessions). This is **not** hypothetical — it is real, present code, confirmed by `grep` in the prior verification pass, and it is only harmless today because neither capability's field access currently crashes on the other's row shape (both happen to include an `id` field).
- **Risk/impact**: Low today (no crash currently reproducible), but structurally fragile — a future edit to either capability's schema (e.g., `multiplayer_game` adding a field access that assumes every row has a `mode` field) could reintroduce the exact `KeyError` class of failure this round already found once, and nothing would catch it except re-running `full_library_stress_test.py` with that specific combination of apps.
- **Required before production?** Not urgent in isolation (these two apps are independently deployed with isolated `data/` directories in real per-app deployment — the collision only manifests inside `full_library_stress_test.py`'s deliberate single-shared-directory merge topology, not in normal per-app deployment). **Becomes required** if this library is ever deployed as a single merged multi-app process/gateway sharing one data store — a real, if not-yet-committed-to, architectural direction implied by `_namespace_route()`'s own existence.
- **Dependencies**: none blocking; a real fix is either (a) renaming one of the two capabilities' filenames (small, but touches committed canonical-library code, which is currently frozen per your "do not modify the verified implementation" instruction), or (b) extending `full_library_stress_test.py`'s own merge logic to namespace data directories per-app the same way it already namespaces routes (matches this document's read-only mandate: proposed, not implemented, here).
- **Size**: Small (either fix).
- **Acceptance tests**: `full_library_stress_test.py` re-run showing this specific pair no longer sharing a physical data file in the merged system; existing 323/323 result preserved.

## 3. Missing production-readiness requirements, by area

| Area | Verified current state | Evidence | Gap | Required before production? | Size |
|---|---|---|---|---|---|
| **Deployment** | Flask dev server, `127.0.0.1`-bound, no containerization, no process manager | 1.1 above | No real deployment path exists at all | Yes | Small–Medium |
| **Authentication and authorization** | Real, tested (45/45), but applied to **0 of the 49 durable library apps** | `grep -rl "add_auth_capabilities" verification/app_defs.py verification/new_app_*.py` → zero matches; confirmed same for `encrypt_value`/`save_blob`/`add_ranking_capability`/`create_session` against `OUTPUT_LIBRARY/*/modules/*/route.py` and `NEW_APPS_FROM_LIBRARY/*/modules/*/route.py` → zero matches | Every one of round 7's new capabilities exists only in the gitignored, disposable `verification/coverage_expansion/` workspace, never in the committed product | See §4 — this is the central finding of this whole assessment | Medium (per app) |
| **Tenant isolation** | None — explicitly single-tenant by construction | `COMPATIBILITY_AUDIT.md:47` | No multi-tenant concept exists anywhere in the codebase | Conditional — only if multi-tenant SaaS is the actual product direction (unknown — see §6) | Large, if needed |
| **Secrets and encryption** | Real AES-256-GCM exists (proven, 9/9), applied to 1 disposable demo app (`secure_vault`), never a durable one | `CANONICAL_SPEC.md` C.2; grep above | Same "proven but not promoted" pattern as auth | Yes, before any real sensitive data is stored in a durable app | Small (promoting), Medium–Large (real KMS per 1.6) |
| **Audit logging** | Real generic engine exists (`add_audit_log_capability`), applied to 0 of 49 durable apps | grep above (zero matches in `app_defs.py`/`new_app_*.py`) | Same pattern | Conditional — genuinely required only where auth/sensitive-data capabilities are promoted (item above) | Small (engine already exists, is proven, and funnels through the same `add_capability()` contract) |
| **Backups and recovery** | None found | `grep -rli "backup"` → only a docstring mention of NOT sweeping the key into a backup, no actual backup mechanism | No backup/restore capability exists for any app's JSON data | Yes, before any app holds real, non-reconstructable user data | Medium |
| **Observability and failure handling** | A `/health` endpoint exists (`verification/gen_common.py`); no structured logging, no metrics, no error tracking beyond Flask's default stderr traceback on a 500 | `grep -n "import logging\|prometheus\|sentry\|metrics"` → zero matches | No way to observe a real deployment's health beyond manually curling `/health` | Yes, before real operational use | Small–Medium |
| **API and frontend integration** | Plain server-rendered HTML + inline vanilla JS (`page_skeleton()`), one page per app, no SPA framework, no OpenAPI/Swagger spec anywhere | `grep -rli "openapi\|swagger"` → zero matches; `page_skeleton()` source inspected directly | Real, working, but not integration-friendly for a separate frontend team or third-party API consumers | Conditional — depends on whether a real, separate frontend is ever wanted (unknown — see §6) | Medium–Large, if needed |
| **Real-user end-to-end workflows** | `functional_tests.py` has 9 narrow, single-capability tests; each app's Playwright journey covers exactly one primary action | `verification/functional_tests.py` (9 `test_` functions); `AppBuilder.finish()`'s single `primary_journey` parameter | No test exercises a realistic multi-step session (e.g., register → log in → do several things → log out) end to end in one continuous browser session | Conditional — genuinely valuable once any app has real multi-step user value to protect | Medium |

## 4. Capabilities/apps built and verified but not yet product-ready

**This is the single most concrete, highest-confidence finding of this assessment.** Every one of round 7's new capabilities is real, tested, and committed to `verification/gen_common.py` (the actual, shared, git-tracked engine) — but **none of them have been applied to any of the 43 canonical or 6 composed apps that make up the actual durable product** (`OUTPUT_LIBRARY/`, `NEW_APPS_FROM_LIBRARY/`). They exist only inside `verification/coverage_expansion/`, which is gitignored by explicit, established convention (`COVERAGE_EXPANSION_REPORT.md`: *"a capability is promoted; a probe app is not"*).

| Capability | Proven where | Test evidence | In the durable product? |
|---|---|---|---|
| Five identity/login types | `identity_and_access_demo`, `guest_and_service_demo` (disposable) | `security_tests.py` 45/45 | No |
| Encryption at rest | `secure_vault` (disposable) | `encryption_tests.py` 9/9 | No |
| Real binary/document storage | `document_storage_demo` (disposable) | `document_tests.py` 12/12 | No |
| Rankings/leaderboard | `multiplayer_game` (disposable) | `ranking_tests.py` 9/9 | No |
| Auth audit logging | `identity_and_access_demo` (disposable) | folded into `security_tests.py`'s 45 | No |

This is not a defect — it is the established, deliberate project convention working exactly as designed (probes stay disposable; only generalized engines get promoted). But it means that, today, **a real end user interacting with any of the 49 committed apps experiences none of this round's work at all.** The capabilities are proven to work; they are not yet part of the product anyone would actually use.

## 5. The smallest safe next milestone with meaningful value

**Candidates considered, with reasoning:**

- **Promote a production WSGI server (1.1)**: small, safe, foundational — but pure infrastructure, no visible user/business value on its own.
- **Apply the identity/auth engine to one real canonical or composed app**: converts already-proven, already-tested capability into something a real user of the actual product could experience for the first time. Reuses fully-tested engines (`add_auth_capabilities`, `add_audit_log_capability`) — no new capability design required. The one known constraint (from `CANONICAL_SPEC.md` C.6): the app's existing primary browser-journey slot cannot itself be an authenticated capability, so the journey binding would need to point at the public Register step, exactly as `identity_and_access_demo` already demonstrates.
- **Close the residual `sessions.json` collision (§2)**: small, safe, pure risk-reduction — no user-facing value.
- **Add observability**: valuable operationally, not user-facing.

**Recommendation: promote real authentication + audit logging into one real, already-existing composed app** (a strong candidate, evidence-based rather than picked arbitrarily: `crm` or a similar app with a genuine "who owns this record" concept already in its data shape — the exact concept `identity_and_access_demo`'s "Create Task"/"List My Tasks" pattern already proved end-to-end). This is the smallest change that converts *proven* work into *product* work, without touching anything currently verified and accepted.

- **Dependencies**: none blocking — the engines exist, are tested, and funnel through the same `add_capability()` contract every existing capability already uses.
- **Size**: Medium (one app's generator script gains 4 new capabilities + a journey-binding change + a new regression pass).
- **Acceptance tests required**: the app's own existing Playwright journey (rebound to Register) continues to pass; a new, app-specific security test suite (matching `security_tests.py`'s methodology) proving real registration/login/logout/session-expiry/cross-user-isolation on this specific app; full regression (`run_full_verification.py`) reconfirmed unchanged for every other app; merged stress test reconfirmed at the same or better collision/shadow/failure counts.

---

## Verified facts (from this session's direct, live inspection)

- Every app runs on Flask's development server, bound to `127.0.0.1`, with zero deployment artifacts anywhere in the repository.
- No TLS, no rate-limiting, no CSRF protection exists anywhere.
- Zero of the 49 durable library apps (canonical + composed) use any round-7 capability (auth, encryption, document storage, ranking, audit logging) — confirmed by direct grep against their actual generated `route.py` files.
- `course_enrollment_hub` and `multiplayer_game` currently, actively, both use `DATA_FILE_NAME = "sessions.json"` for unrelated concepts — confirmed present, not hypothetical.
- No backup mechanism, no structured observability, no OpenAPI spec, and no multi-tenant concept exist anywhere in the codebase.

## Known limitations (already documented elsewhere, restated here for completeness, not renegotiated)

- `_master_key()`'s minimal key management (`CANONICAL_SPEC.md` C.2).
- No login rate-limiting/lockout, `secure_vault`'s lack of its own login, the demo's public admin-registration endpoint (`IDENTITY_AND_LOGIN_TYPES_SPEC.md`).
- The residual `sessions.json` cross-domain collision (`CANONICAL_SPEC.md` C.4).

## Recommendations (this document's own judgment, clearly separated from verified fact)

1. Treat "promote real auth to one durable app" as the next milestone (§5).
2. Treat the WSGI/TLS/rate-limiting trio (1.1–1.3) as a required, parallel-track hardening pass **before** any app — auth-bearing or not — is ever exposed beyond localhost, regardless of which feature milestone ships first.
3. Do not invest in multi-tenancy, a separate frontend/API-consumer surface, or real KMS integration until the unknowns in §6 are resolved — building any of these without knowing the actual product direction risks real, wasted rework.

## Unknowns requiring a decision (not answerable from the repository alone)

1. **Is this system meant to become a real, deployed, multi-user product, or does it remain a technical capability-proving library/reference catalog?** This single decision determines whether items like multi-tenancy, real KMS, a separate frontend, and backups are "required before production" or "not applicable, ever."
2. **If it becomes a real product, is it single-tenant-per-deployment (one organization runs one instance) or multi-tenant SaaS (one instance serves many organizations)?** This determines whether tenant isolation is a real requirement or a non-issue.
3. **Which specific durable app(s) should receive the promoted auth/audit capabilities first?** This document proposes an evidence-based candidate shape (an app with an existing "ownership" concept in its data) but does not pick one on your behalf.
4. **Is real email/SMTP delivery ever in scope** (needed for password reset, item 1.7)? The existing `notify()` primitive is real but has no actual email transport behind it, and adding one is an external-integration decision this project's own established boundary (payment/weather/AI-inference/maps) has consistently deferred.

---

## Explicit items that should NOT be changed yet

- **Part A of `CANONICAL_SPEC.md`** — frozen, as established.
- **Any of the 43 canonical or 6 composed apps' existing capabilities** — verified, accepted, and outside this assessment's mandate to touch.
- **The `RESERVED_SHARED_LIB_FILENAMES` guard and its scope** — correctly narrow per its own contract; do not broaden it speculatively without the cross-app registry design this document deliberately left as a read-only proposal, not an implementation.
- **`course_enrollment_hub`'s or `multiplayer_game`'s `sessions.json` filenames** — real, working, tested code; renaming either requires a real regression pass this document did not run (read-only mandate) and should be its own deliberate, separately-authorized change per §2, not a side effect of this assessment.
- **Any multi-tenancy, real KMS, or separate-frontend work** — blocked on the unknowns in §6, not on any technical gap.
