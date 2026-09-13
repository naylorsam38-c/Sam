# Authentication + Next Five Foundational Capabilities — Work Package Report

Real login/identity infrastructure for the capability library, plus the next five
most important missing foundational capabilities, selected from actual evidence
in this project (not invented). Every number below comes from an executable run
whose command is given alongside it, the same standard `COVERAGE_EXPANSION_REPORT.md`
established.

**See `IDENTITY_AND_LOGIN_TYPES_SPEC.md`** for the formal specification of each
of the five identity/login types below: what it is for, what it can do, and
the specific, cited security requirement each one meets (NIST SP 800-63B,
OWASP's Session Management and Authorization Cheat Sheets, and real API-key
security practice) — produced after this report's first version, in response
to an explicit follow-up request to define these properties clearly rather
than leave them implicit in prose. That follow-up review also found and fixed
two further real gaps against those cited standards, folded into §4/§6/§7
below: password blocklist screening, and live (not session-frozen) role
re-resolution.

## 1. The five login/identity types

**No pre-existing specification of "five login types" exists anywhere in this
project.** This was verified exhaustively, not assumed: every `.md` file at the
repo root, `canonical_app_types.py`, the full `build.py` source, every
`verification/*.py` file, `audit/capability_catalog.json`, and `git log --all`
across every branch were searched for login/auth specs, identity/account types,
roles, session-handling design, or prior login discussions. None exist. Before
this round, `CAP-0000`'s `ctx` object was a hardcoded stub
(`{"user": None, "authenticated": False}`) — this was already recorded as the
single most consequential gap in `COVERAGE_EXPANSION_REPORT.md` §5.1, found
independently by five different probes in the prior round, but never designed
further than "this needs a real login capability."

Per the explicit instruction not to invent types or assume generic defaults
(password/Google/Apple) without evidence, this was raised to the user as a
genuine blocker rather than guessed. The user selected **"Design five myself,
evidence-informed"** — authorizing five identity/login types chosen from real
patterns already visible across the 49+12 apps in this library, clearly labeled
as this session's own selection, not a recovered spec.

The five types, and the real evidence behind each:

1. **Standard individual account** — the default identity shape underlying
   almost every multi-user app in the library (team_chat, project_management,
   crm, helpdesk_ticketing, and every probe from the coverage-expansion round
   that needed "a user").
2. **Role-based privileged account (admin)** — the same population with a
   privilege tier, evidenced by every app with an implicit "someone moderates
   this" need (multiplayer_game's player moderation, recruitment_platform's
   application review, government_portal's case handling).
3. **Two-sided peer account** — a genuinely separate population, not a
   privilege tier of the first (crm's leads vs. reps, recruitment_platform's
   candidates vs. recruiters, multi_vendor_marketplace's buyers vs. sellers).
4. **Guest/anonymous shared-access** — real, unguessable share links with no
   account at all, the exact pattern `volunteer_shift_signup` and
   `travel_planner`'s "shared" features used **honestly without any real
   access control** last round (recorded as a limitation, not hidden) — this
   round gives that pattern a real backing mechanism.
5. **Service/system account (API key)** — a non-human caller, the exact
   capability `developer_platform`'s coverage-expansion probe explicitly
   declined to build last round specifically because no real auth existed yet
   to validate a key against.

Built as two proof apps in the disposable `verification/coverage_expansion/`
workspace (gitignored, same convention the prior round established — a
capability is promoted into `gen_common.py`; a probe app is not):

- **`identity_and_access_demo`** ("team workspace") — types 1, 2, 3.
- **`guest_and_service_demo`** ("shared board") — types 4, 5.

## 2. The next five foundational capabilities

Selected from two real sources: `COVERAGE_EXPANSION_REPORT.md` §4 (Missing-
capability register) and §5 (Foundational gaps requiring separate design),
ranked by (1) security impact, (2) apps affected, (3) reusability, (4)
production-readiness importance — excluding gap §5.1 (real identity/auth,
closed by Part 1-3 above) and the external-service-integration category
(payment, weather, real AI inference, maps, identity verification), which
that report already correctly scoped as permanently out of bounds for this
library, the same boundary the original 43-app round established.

1. **Encryption at rest** (§5.2) — named alongside identity as "the single
   most consequential, cross-cutting gap" of the entire prior round. Apps
   affected: `secure_vault`, `medical_patient_portal`, `government_portal`,
   and implicitly any app storing sensitive fields. Highest security impact
   of anything left unaddressed.
2. **Real audit logging of authentication events** — not itself in the
   report (auth didn't exist yet when it was written), but the report's own
   audit-log engine (built last round) had nothing to log until this round's
   auth work existed. Composing the two closes a live, self-identified gap:
   before this, nothing recorded who logged in, who failed to, or who logged
   out. Reusability: automatic for every future `add_auth_capabilities()`
   call, zero extra wiring.
3. **Real TTL/expiry for share tokens and API keys** — the concrete,
   "recommended investigating first" slice of §5.3 (real-time/background
   execution): a lazy-evaluation deadline check, the same mechanism session
   expiry already used. Also closes a gap this very session's own new
   mechanisms shipped with (share links and API keys minted with no expiry
   at all).
4. **Real binary/document storage** (§5.4 / §4 row 2) — apps affected:
   `recruitment_platform` (CV upload), `medical_patient_portal`/
   `government_portal` (document submission), `ai_creative_studio` (asset
   storage). Deferred last round specifically because it needed a new
   storage primitive beside the JSON-file store, not because it couldn't be
   built.
5. **Rankings/leaderboard** (§4 row 1) — apps affected: `multiplayer_game`
   (player scores), `personal_finance` (statements). Recorded last round as
   "judged below this round's evidence bar for a 5th new engine," explicitly
   not dropped.

## 3. Existing implementations reused

- `add_capability()`, the Common Capability Contract v2, and `_namespace_route()`
  — every new engine funnels through the same choke point every prior engine
  used; nothing bypasses the compatibility gate.
- `add_audit_log_capability()` and `_shared.audit()` (built last round) —
  reused verbatim for capability #2, only the call sites are new.
- `multiplayer_game` and `secure_vault` — both prior-round probe apps already
  had the exact real gap this round's capabilities #1 and #5 closed, explicitly
  named in their own module docstrings. Both were extended in place rather
  than rebuilt from scratch.
- CAP-0000's existing `load()`/`save()` — `save_blob()`/`load_blob()` are
  built on top of the same `DATA_DIR`, not a separate storage mechanism.

## 4. New implementations built

All in `verification/gen_common.py` (the only tracked file every generated
app's shared infrastructure comes from):

- `hash_password()`/`verify_password()` (PBKDF2-HMAC-SHA256, salted).
- `is_common_password()` — a real (deliberately small, local) blocklist of
  common/breached passwords, closing NIST SP 800-63B's requirement to
  screen for these, not just enforce a length minimum. Wired into
  Register.
- `create_session()`/`validate_session()`/`invalidate_session()` — real,
  expiring, unguessable session tokens. `create_session()` now accepts
  `role_source=(data_filename, id_field)`; `validate_session()` re-resolves
  the role from the LIVE user record on every call instead of trusting a
  snapshot frozen at login, and fails closed if the account no longer
  exists — closing OWASP's Authorization Cheat Sheet "Role Maintenance"
  requirement (a role change must take effect immediately, not only once
  the holder's existing session expires on its own).
- `generate_api_key()`/`validate_api_key()` — hashed service credentials,
  now with optional real `ttl_minutes` expiry.
- `generate_share_token()`/`validate_share_token()` — unguessable,
  resource-scoped guest links, now with optional real `ttl_minutes` expiry.
- `is_expired()` — the shared lazy-evaluation expiry check every TTL-bearing
  primitive above now uses consistently.
- `encrypt_value()`/`decrypt_value()`/`_master_key()` — real AES-256-GCM via
  the `cryptography` library (a real new pinned+vendored dependency — Python's
  stdlib has no vetted symmetric cipher, and hand-rolling one would be exactly
  the fake-security shortcut this project's standard forbids).
- `save_blob()`/`load_blob()` — real binary storage under `data/blobs/<id>`,
  separate from the JSON-array store.
- `_make_ctx()` in `HOST_APP_PY_TEMPLATE` — changed from a hardcoded stub to
  real Bearer-token/X-API-Key resolution.
- `dispatch()` in `HOST_APP_PY_TEMPLATE` — new binary-response path (a
  `{"__binary__": True, ...}` sentinel), fully backward-compatible: no
  pre-existing handler returns that shape, so every existing capability is
  unaffected.
- `add_capability()` — new `required_role`, `context_fields_override`
  parameters, and a same-app `(route, method)` collision assertion (a real
  bug this round found and fixed, see §7).
- New generator engines: `add_auth_capabilities()`, `add_share_token_capability()`,
  `add_api_key_capability()`, `add_document_storage_capabilities()`,
  `add_ranking_capability()`.

## 5. Files changed

- `verification/gen_common.py` — all of §4 above.
- `verification/requirements.txt` — added `cryptography==50.0.1`,
  `cffi==2.1.1`, `pycparser==3.0` (encryption's real dependency).
- `verification/vendor/wheels/` — the three corresponding wheels, vendored
  the same way `flask`/`playwright` already were, so the project's existing
  zero-network-install guarantee (`bootstrap.py`) covers them too.
- `verification/coverage_expansion/` (gitignored, not committed, same
  convention the prior round established): two new proof apps
  (`identity_and_access_demo`, `guest_and_service_demo`), one new app
  (`document_storage_demo`), two extended probe apps (`secure_vault`,
  `multiplayer_game`), and four new test scripts (`security_tests.py`,
  `encryption_tests.py`, `document_tests.py`, `ranking_tests.py`).
- `IDENTITY_AND_LOGIN_TYPES_SPEC.md` (new) — the formal per-type
  specification (purpose/capabilities/security requirements), written and
  committed in response to the explicit follow-up request for one.

## 6. Tests run and exact results

Real HTTP calls (and, where noted, real on-disk file inspection or real
tampering) against real running Flask processes in disposable copies —
never `OUTPUT_LIBRARY`/`NEW_APPS_FROM_LIBRARY`. Exact JSON output for every
suite is reproducible by re-running the named script.

```
security_tests.py            45/45 passed   (identity_and_access_demo + guest_and_service_demo:
                                              registration, login, logout, password hashing,
                                              common-password blocklist, cross-user isolation,
                                              unauthorized access denial, session expiry, admin
                                              authorization, LIVE role re-resolution (promote/
                                              demote/delete an existing token's account), TTL/
                                              expiry on share links, real auth audit trail)
encryption_tests.py           9/9  passed   (secure_vault: real AES-256-GCM at rest)
document_tests.py            12/12 passed   (document_storage_demo: real multipart upload/download)
ranking_tests.py               9/9  passed   (multiplayer_game: real leaderboard)
--------------------------------------------
Total new evidence-based checks           75/75 passed
```

Full regression (`python3 verification/run_full_verification.py`, standard
invocation, canonical library only):

```
proving_table:              29/29 pass, readiness 20/20
canonical_apps:              43/43 READY
new_composed_apps:            6/6 READY
generalization_regression:  ALL MATCH
dependency_graph_audit:     CLEAN
functional_tests:           30/30 passed
full_library_stress_test:   184/184 passed, 0 collisions, 0 shadowed, 0 other failures
overall: PASS
```
Reconfirmed by re-running the exact same command after every `gen_common.py`
change in this work package (including Part 4) — identical figures every
time, byte-for-byte unchanged canonical apps.

Full merged stress test with the entire coverage-expansion workspace
(all 15 apps, including the 3 new/extended this round) rebuilt fresh and
included (`STRESS_TEST_EXTRA_ROOTS=verification/coverage_expansion/library_build
python3 verification/full_library_stress_test.py`):

```
Total capability records across the library: 472
Unique capability ids: 388
Ids shared by >1 project that are NOT byte-identical: 0
Route-bearing capabilities merged into the system: 323
(METHOD, ROUTE) collision groups: 0
323/323 capabilities ran correctly as their own logic in the merged system
0/323 capabilities were silently shadowed by a URL-namespace collision
0/323 capabilities failed for another, genuine reason
```

(An earlier run of this same command, before all 15 coverage-expansion apps
were rebuilt against this round's final `gen_common.py`, correctly reported
`CAP-0000` as 1 non-byte-identical id across projects — a benign, expected
staleness in the disposable, non-canonical workspace, not a contract
violation. Resolved by the rebuild above; left here as the honest record of
that intermediate state, not edited out.)

## 7. Security findings

Four real bugs/gaps were found and fixed during this work package, all by
actually running the code or checking it against a cited external standard
rather than reasoning about it in the abstract — consistent with this
project's standing rule that a clean-looking result must still be verified:

1. **Same-app route collision.** `add_auth_capabilities()` originally
   hardcoded the same route (`/api/auth/register`, etc.) on every call.
   Calling it three times in one app (standard/admin/client) made all three
   collide on identical routes; only the last-registered (client) was
   reachable — the standard and admin auth were silently shadowed despite the
   app building and passing its proving-run cleanly. Found by
   `security_tests.py` actually calling the standard-account endpoint and
   observing it answer with the client instance's data instead. Fixed with a
   `route_prefix` parameter, plus a new same-app `(route, method)` collision
   assertion in `add_capability()` so this class of bug cannot recur
   unnoticed in any future app.
2. **Cross-capability data-file collision.** The new auth session mechanism
   defaulted to `sessions.json` — which two unrelated, pre-existing
   capabilities already used for their own concepts of "session"
   (`course_enrollment_hub`'s class sessions, `multiplayer_game`'s game
   sessions). Invisible in per-app isolation testing; found only by the
   full-library stress test's single shared data directory, which showed a
   genuine `KeyError` when one auth-session row (no `id` field) was read by
   an unrelated capability expecting event-shaped rows. Fixed by renaming to
   `auth_sessions.json`.
3. **No password blocklist screening.** Register only enforced a minimum
   length (8 characters) — `"password1"` and similar known-common passwords
   passed cleanly despite NIST SP 800-63B requiring both. Found by checking
   the implementation against the cited standard (`IDENTITY_AND_LOGIN_TYPES_SPEC.md`'s
   research pass), not by a failing test — there was no test for it because
   there was no requirement written down for it to violate. Fixed with a
   real (if deliberately small, local) common-password blocklist,
   `is_common_password()`, wired into Register.
4. **Session role frozen at login time.** A session's `role` claim was a
   static snapshot taken once at login and never re-checked — an admin
   demoted mid-session kept acting as admin, and a deleted account's
   existing token stayed valid, until that session happened to expire on
   its own (up to 60 minutes later). Violates OWASP's Authorization Cheat
   Sheet "Role Maintenance" requirement. Fixed by having `validate_session()`
   re-resolve the role from the live user record on every call
   (`role_source` parameter) and fail closed if the account no longer
   exists — proven by promoting/demoting/deleting a live user record
   mid-session and confirming the SAME, already-issued token reflects the
   change immediately, with no re-login.

All four fixes were verified: `security_tests.py` re-run clean after each
(45/45), and the merged stress test re-run to confirm 0 other-failures.

Part 3's required security proofs, all with real evidence (not asserted from
reading the code):

- **Registration/login**: real PBKDF2-HMAC-SHA256 hashing, salted, verified
  never stored or returned in plaintext (real file inspection).
- **Logout/session handling**: real token invalidation — the exact same
  token genuinely fails after logout.
- **Password security**: minimum length enforced, hash never round-trips
  to plaintext even under adversarial file inspection.
- **Authorization**: `required_role="admin"`-gated capability returns a real
  403 for a non-admin, 200 for an admin.
- **User data separation**: two users' own records are provably disjoint
  through the real API (never asserted from code review).
- **Unauthorized access denied**: no token and a garbage token both 401.
- **Session expiry / invalid sessions**: a tampered `expires_at` on the real
  stored session file is genuinely rejected on the next request.
- **Admin access restricted**: verified both directions (member denied,
  admin allowed) against the same task.
- **No default production passwords**: every account (including admin) is
  registered fresh by the test itself; nothing is pre-seeded.
- **No fake security claims**: encryption is real AES-256-GCM (tamper
  detection proven via a corrupted ciphertext genuinely rejected with
  `InvalidTag`), not masking; TTL/expiry is a real, working lazy-evaluation
  check, not a documented convention.

## 8. Remaining blockers / honest limitations

- **Key management for encryption at rest is real but minimal**: one local
  AES key file, generated once, never hardcoded — but no rotation, no
  per-tenant separation, no external KMS. Recorded plainly in
  `_master_key()`'s own docstring.
- **`secure_vault` still has no real per-user login of its own** — encryption
  at rest is real, but this specific app never calls
  `add_auth_capabilities()`, so its audit actor is a fixed placeholder, not a
  verified identity. The primitives are available; wiring them into this
  specific app was not in this round's scope.
- **Real background/scheduled job execution** (the broader form of gap §5.3,
  beyond the TTL/expiry slice closed this round) remains open — this
  architecture still has no way to run code independent of an incoming HTTP
  request.
- **External service integrations** (payment/billing, real weather, real AI
  inference, real maps/routing, real identity verification) remain correctly
  out of scope, unchanged from every prior round's boundary.
- **Register Admin being a public, unauthenticated endpoint** in
  `identity_and_access_demo` is a demo convenience, not a production
  pattern — a real deployment would provision its first admin out-of-band.

## 9. Final commit hash

`c959985` — "Add identity-types spec + close two real gaps it surfaced"
(the last commit of this work package; `e9e67f4` and `f34f944` preceded it —
see git log for the full sequence).

## 10. This report

This document. Supersedes nothing — `COVERAGE_EXPANSION_REPORT.md` remains
the record of the prior round's own findings and is cited throughout above
rather than restated.
