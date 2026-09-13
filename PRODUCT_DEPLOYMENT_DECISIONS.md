# Product Deployment Decisions

Read-only inspection of the repository at commit `3191a8b`, produced before promoting identity,
audit logging, or any other round-7 capability into a durable app (per `NEXT_PHASE_READINESS.md`).
No code, test, generated app, or specification was changed to produce this document. Every "Options"
list is exhaustive against what the request named; every "Evidence" line cites the exact command or
file that supports it. Where the repository is silent, that silence is stated plainly, not filled in.

---

## 1. Deployment target

**Decision required**: where will the first real, auth-bearing app actually run?

**Options**: local/self-hosted · single VPS/EC2 · containerized deployment · other existing path evidenced in the repo.

**Evidence**:
- `grep -n 'app.run' verification/gen_common.py` → `app.run(host="127.0.0.1", port=args.port)` — every app starts as a local Flask process bound to loopback only.
- `find . -iname "Dockerfile*" -o -iname "docker-compose*" -o -iname "Procfile" -o -iname "*.service"` → zero results anywhere in the repository.
- `grep -rli "EC2\|VPS\|AWS\|azure\|google cloud\|heroku"` across `verification/*.py` and every `.md` → the only hits are citations of Stripe/GitHub/AWS as *examples of API-key practice* in `gen_common.py` and `IDENTITY_AND_LOGIN_TYPES_SPEC.md`, not deployment evidence.

**What is known**: nothing beyond "runs locally, on loopback, as a bare Flask process" is evidenced anywhere in this repository.

**What is unknown**: every one of the four named options is equally unevidenced beyond "local." This is a pure decision, not a fact this repository already contains.

**Consequence of each option**:
- *Local/self-hosted*: zero new infrastructure, but no real multi-user access from outside the host machine (matches item 1.1/1.2 in `NEXT_PHASE_READINESS.md`).
- *Single VPS/EC2*: real external access; requires the WSGI/TLS/process-supervision work in §6 below regardless of which cloud is chosen.
- *Containerized*: same §6 requirements, packaged for portability; requires writing a `Dockerfile` that does not currently exist.
- *Other path*: cannot be evaluated — none is evidenced.

**Recommended default** *(recommendation, not fact)*: local/self-hosted for the first promotion (§7), specifically because it defers the WSGI/TLS/process-supervision investment (§6) until the tenancy and exposure decisions (§2/§3) are actually made — building real infrastructure before knowing who it serves risks real, wasted rework, the same caution `NEXT_PHASE_READINESS.md` §6 already raised.

**Exact information needed from Sam**: which of the four options is intended, and if VPS/EC2/container, which specific provider/environment (this changes nothing about the code, but determines which §6 items are prerequisites vs. already handled by a managed platform).

---

## 2. Application exposure

**Decision required**: who can reach this once deployed?

**Options**: private/internal use · public internet · customer-facing SaaS · single operator vs. multiple users.

**Evidence**:
- `COMPATIBILITY_AUDIT.md:47`: *"every app is single-tenant and unauthenticated by construction."*
- The only multi-user-capable code that exists (`add_auth_capabilities`, `add_audit_log_capability`) is proven in disposable probe apps only (`security_tests.py` 45/45), never in a durable app — confirmed by `grep -rl "add_auth_capabilities" verification/app_defs.py verification/new_app_*.py` returning zero matches.
- No public-internet exposure exists today: `127.0.0.1` binding (§1) makes this a structural fact, not a policy choice, until changed.

**What is known**: today, exposure is "none beyond the local machine," by construction.

**What is unknown**: whether the real intent is ever public-internet or SaaS-facing, or whether this remains an internal/operator tool.

**Consequence of each option**:
- *Private/internal*: §1's local/VPS-behind-a-firewall options suffice; §6's TLS/rate-limiting become lower-urgency (still good practice, not urgent).
- *Public internet*: §6's TLS and rate-limiting (already flagged as required-before-production in `NEXT_PHASE_READINESS.md` items 1.2/1.3) become mandatory, not optional.
- *Customer-facing SaaS*: additionally forces a real answer to §3 (tenancy) — "single-tenant by construction" cannot remain true for a SaaS product serving multiple customers from one instance, unless "SaaS" here means "one instance per customer," which is a real, valid, much smaller answer worth stating explicitly as an option Sam may intend.
- *Single operator vs. multiple users*: a single operator using one instance privately has categorically different auth/tenancy needs than a product with self-service signup.

**Recommended default** *(recommendation, not fact)*: none — this decision has no safe technical default; it is a business decision this document will not guess.

**Exact information needed from Sam**: is the near-term goal an internal tool for a known, small set of users, or a public product? If SaaS, is it "one shared instance for many customer organizations" or "one instance deployed per customer"?

---

## 3. Tenancy model

**Decision required**: what tenancy shape does the first promoted app need?

**Options**: single-user · single organization · multi-user shared instance · multi-tenant isolation.

**Evidence, precisely separated**:
- **What the 49 durable library apps support today**: none of the above in any real sense — `COMPATIBILITY_AUDIT.md:47`'s "single-tenant and unauthenticated by construction" means every record in every app's data file is visible to anyone who can reach the app at all. There is no user boundary of any kind.
- **What the tested-but-not-yet-promoted identity engine already supports** (`security_tests.py`, 45/45, live-reconfirmed): a real **multi-user shared instance** — `identity_and_access_demo` proves multiple real accounts (`alice`, `bob`, an admin, an external client) sharing one running app instance, with real per-user data isolation (`"bob sees only his own task (cross-user isolation)"`, confirmed passing) and real role-based access control.
- **Multi-tenant isolation** (many separate organizations, each with their own users, sharing one instance without seeing each other's data at all) is **not implemented anywhere** — `grep -rli "tenant"` across the codebase returns only gap-documentation mentions (`CANONICAL_SPEC.md` C.2, `AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md`), never a real `tenant_id`-shaped data model.

**The minimum model supported by current, tested code, if promoted as-is**: **multi-user shared instance** (single organization) — one level above single-user, one level below multi-tenant.

**Consequence of each option**:
- *Single-user*: simplest; wastes the already-built, already-tested multi-user isolation work.
- *Single organization / multi-user shared instance*: matches exactly what's already proven; zero new capability design needed.
- *Multi-tenant isolation*: would require a real, new `tenant_id` dimension threaded through every data file and every auth check — a genuinely new capability, not a promotion of existing work, and explicitly out of `NEXT_PHASE_READINESS.md`'s "smallest safe milestone" scope.

**Recommended default** *(recommendation, not fact)*: multi-user shared instance (single organization) — it is the only option that requires zero new capability design, being exactly what `identity_and_access_demo` already proves.

**Exact information needed from Sam**: confirm whether "single organization, multiple real users" is sufficient for the first promotion, or whether multi-tenant isolation is a hard requirement from day one (which would change §7's scope substantially, per `NEXT_PHASE_READINESS.md`'s own "Large, if needed" sizing for tenancy work).

---

## 4. Authentication model

**Decision required**: which of the identity mechanisms already designed should the first promoted app actually use, and what's missing?

**Options named**: local credentials · OAuth · magic links · administrator-created accounts · session model · account recovery requirements.

**Evidence**:
- **Local credentials (email + password)**: the only implemented mechanism. `IDENTITY_AND_LOGIN_TYPES_SPEC.md` types 1–3; PBKDF2-HMAC-SHA256 hashing, NIST SP 800-63B-cited length + common-password blocklist (`is_common_password()`), proven (`security_tests.py` 45/45).
- **OAuth**: `grep -rli "oauth"` across the entire repository → zero matches. Not designed, not implemented, not referenced anywhere.
- **Magic links**: `grep -rli "magic link"` → zero matches. Not designed anywhere. (Note: the *share-token* mechanism, type 4 in the identity spec, is a real, unguessable, resource-scoped link — but it authenticates access to *one resource*, not a user identity; it is not a magic-link login mechanism and should not be conflated with one.)
- **Administrator-created accounts**: not implemented. The closest existing pattern — `identity_and_access_demo`'s "Register Admin" — is *self-service registration at a separate, admin-scoped endpoint*, not one administrator creating an account on another user's behalf. `IDENTITY_AND_LOGIN_TYPES_SPEC.md`'s own "Honest limitations" already states this is "a demo convenience, not a production pattern."
- **Session model**: real, implemented, proven. Bearer tokens (`secrets.token_urlsafe(32)`, 256 bits), real server-enforced expiry, and — per this round's own hardening — live role re-resolution on every request (`CANONICAL_SPEC.md` C.5), not a snapshot frozen at login.
- **Account recovery**: not implemented anywhere (`NEXT_PHASE_READINESS.md` item 1.7). No "forgot password" flow, no real email-transport integration behind the existing generic `notify()` primitive.

**Consequence of each option**:
- *Local credentials only*: ships today with zero new work; real users who forget passwords have no self-service recovery path (support burden falls on whoever operates the instance).
- *Adding OAuth*: real new work — no existing primitive to build on; requires choosing and integrating a real provider (Google/GitHub/etc.), an external-integration category this project has consistently deferred (payment, weather, AI inference, maps — `COVERAGE_EXPANSION_REPORT.md` §5.5).
- *Adding magic links*: smaller new work than OAuth (could reuse `generate_share_token`-style token generation plus real email transport), but still requires the same email-transport decision as account recovery.
- *Administrator-created accounts*: small new work — a role-gated "Create User" capability, following the same `required_role="admin"` pattern already proven for "Delete Any Task."

**Recommended default** *(recommendation, not fact)*: ship with local credentials + the existing session model only, for the first promotion — it is the only option requiring zero new design. Treat account recovery and administrator-created accounts as fast-follow candidates once real users exist; treat OAuth/magic links as deferred until a real email/OAuth-provider integration is separately authorized (matching this project's own established external-integration boundary).

**Exact information needed from Sam**: is local-credentials-only acceptable for the first real users, or is account recovery a hard launch requirement? Is administrator-provisioning (vs. self-service registration) required from day one?

---

## 5. Data and secrets

**Decision required**: where does real data and key material live, and what's the encryption/backup story?

**Evidence**:
- **Application data location**: `DATA_DIR = Path(__file__).resolve().parents[2] / "data"` (`verification/gen_common.py`, `SHARED_LIB_SOURCE`) — plain JSON files, one directory per app, physically under that app's own deployment root. Confirmed: no database, no external storage service, anywhere.
- **Secrets location**: `SECRETS_DIR = Path(__file__).resolve().parents[2] / "secrets"` — a real, randomly generated key file (`master_key.bin`, 256 bits, `_secrets.token_bytes(32)`), created on first use, never hardcoded or committed (`CANONICAL_SPEC.md` C.2).
- **Encryption boundary**: real AES-256-GCM (`encrypt_value()`/`decrypt_value()`), proven (`encryption_tests.py` 9/9: plaintext never on disk, tamper detection via `InvalidTag`) — but applied only to `secure_vault` (a disposable probe), and only to one field (`secret`) in one app. Password hashes (PBKDF2) and session/API-key tokens are separately, already protected by their own primitives regardless of this encryption layer.
- **Backup and recovery**: `grep -rli "backup"` → zero real mechanism found (only a docstring noting the key file is deliberately *excluded* from being swept into a hypothetical future backup of `data/`). No backup of `data/` itself exists either.
- **External KMS**: not used. `_master_key()`'s own docstring states plainly: *"deliberately NOT a real KMS: single key, no rotation, no per-tenant separation... For a genuinely multi-tenant or compliance-grade deployment this is the honestly-recorded next gap."* This is a stated limitation, not a stated intentional permanent exclusion — the repository does not claim KMS will never be needed, only that it isn't built.

**Consequence of each option** (backup and KMS, the two genuinely open sub-decisions):
- *No backup, accept data-loss risk*: zero new work; acceptable only if the first promoted app's data is genuinely low-stakes/reconstructable.
- *Add real backup*: `NEXT_PHASE_READINESS.md` sizes this Medium; required before any app holds real, non-reconstructable user data.
- *No KMS, keep local key*: zero new work; acceptable for a single-operator or low-sensitivity deployment.
- *Add real KMS*: Medium–Large; only justified once real, sensitive, multi-tenant data exists — premature for the first promotion under the recommended tenancy model in §3.

**Recommended default** *(recommendation, not fact)*: keep the local-key model and defer real backup/KMS investment until after the first promotion has real users and real data worth protecting — building either speculatively, before real usage exists, risks the same wasted-rework pattern `NEXT_PHASE_READINESS.md` warns about.

**Exact information needed from Sam**: is any data the first promoted app will hold sensitive enough (PII, financial, health-adjacent) to require backup/KMS from day one, regardless of user count? If yes, that overrides the deferral recommendation above.

---

## 6. Production serving

**Decision required**: what actually serves real traffic once this is deployed beyond a developer's own machine?

**Evidence** (all confirmed absent by direct inspection):
- **WSGI/ASGI server**: none. `app.run()` is Flask's own development server; `grep -i "gunicorn\|uwsgi\|waitress"` against `verification/requirements.txt` → zero matches.
- **Reverse proxy**: none configured or referenced anywhere.
- **TLS**: none. `grep -rli "ssl_context\|https\b"` → zero matches.
- **Rate limiting**: none. Confirmed absent by fresh grep this pass (only docstring acknowledgments of the gap).
- **Process supervision**: none — no `systemd` unit, no `supervisor`/`pm2` config, no restart-on-crash mechanism found anywhere.
- **Health checks**: **real and present** — `/health` (`verification/gen_common.py`'s `health()` function), returning `{"ok": True}`, exercised by every stress-test run in this project's own regression suite.
- **Logging and monitoring**: none beyond Flask's default stderr traceback on an unhandled exception. `grep -n "import logging\|prometheus\|sentry\|metrics"` → zero matches.

**Consequence of each option**: this section is not a set of alternatives to choose between — every one of WSGI/TLS/rate-limiting/process-supervision/logging is a real, independent gap that `NEXT_PHASE_READINESS.md` §3 already scored "Small–Medium" individually and named as required once exposure moves beyond localhost (§2).

**Recommended default** *(recommendation, not fact)*: treat all five as one parallel-track hardening pass, gated on §1/§2's actual deployment/exposure decision — do not build any of them speculatively before that decision is made, since the right reverse-proxy/TLS-termination setup depends entirely on which deployment target (§1) is chosen.

**Exact information needed from Sam**: none beyond §1/§2's answers — this section has no independent decision of its own, only a dependency on those two.

---

## 7. First product target

**Decision required**: which one existing durable app receives the first real promotion of identity/audit capabilities?

**Candidates actually inspected** (`verification/app_defs.py`), not picked arbitrarily:

| App | Capabilities | Frontend | Notable evidence |
|---|---|---|---|
| `todo_list` | 7 (`CAP-0101`–`0107`) | **Externally-sourced, "preserved verbatim" TodoMVC spec HTML/CSS/JS** — `app_defs.py:208-216`'s own docstring: *"independently justified by the real published spec it was built from, not something this upgrade has any reason to change."* Journey completes via a real keypress (`"action_key": "Enter"`), not the click-based pattern every other app uses. | The most historically significant, most-tested app in the entire project (round 7's original proof) — but that same status is exactly why its docstring flags it as something to leave alone. |
| `note_taking` | 4 (`CAP-0201`–`0204`) | Standard, shared `page_skeleton()` template — the same pattern `identity_and_access_demo` and every coverage-expansion app already use successfully with real auth capabilities added alongside it | Smallest capability surface of any candidate reviewed; no "preserved verbatim" constraint; a private per-user notes concept is exactly as natural and meaningful as todo_list's per-user todos |

**Recommendation** *(recommendation, not fact)*: **`note_taking`**, not `todo_list`. Reasoning, stated plainly: `todo_list` is the *safer choice by test-history depth* but the *riskier choice by change-surface and by the project's own explicit "don't touch" framing* of its externally-sourced frontend and non-standard journey mechanism. `note_taking` has the smaller capability surface (4 vs. 7), uses the exact same standard template/journey pattern already proven compatible with real auth in `identity_and_access_demo`, and offers the same quality of genuine, meaningful "my own private records" value.

**Exact capabilities to promote** (reusing existing, proven engines only — no new capability design):
- `add_auth_capabilities()` (register/login/logout/me) — one instance, standard individual account (`IDENTITY_AND_LOGIN_TYPES_SPEC.md` type 1). Register bound to the primary journey slot, per `CANONICAL_SPEC.md` C.6's constraint (an authenticated capability cannot itself be the journey target).
- `add_audit_log_capability()` — records real register/login/logout events, the same composition already proven in `identity_and_access_demo`.
- The four existing note capabilities (`CAP-0201`–`0204`) modified to add `owner_id` (from real, server-resolved `ctx['user']`, never client-supplied — the exact pattern `identity_and_access_demo`'s "Create Task"/"List My Tasks" already proves) and a ctx-aware ownership check on Update/Delete.

**What must remain untouched**:
- `todo_list` and every other of the 48 remaining durable apps — this promotion touches exactly one app.
- `CANONICAL_SPEC.md` Part A, and Part C's contract text (this is an *application* of an existing contract, not a change to it).
- The `RESERVED_SHARED_LIB_FILENAMES` guard and every other Part C mechanism — `note_taking`'s new capabilities must pick a `data_filename` (e.g., `notes.json`, already its default) that doesn't collide with `users.json`/`auth_sessions.json`/`audit_log.json`, exactly as the guard already enforces.
- `note_taking`'s existing 4 capability IDs (`CAP-0201`–`0204`) and their existing output contracts — ownership becomes an *additional* field and check, not a breaking change to what already passes `verify_build.py`'s proving table.

---

## Decision sheet — questions Sam must answer before implementation begins

1. **Deployment target** (§1): local/self-hosted, single VPS/EC2, containerized, or another specific path — and if cloud, which provider?
2. **Exposure** (§2): internal/private tool, public internet, or customer-facing SaaS — and single operator or multiple real users?
3. **Tenancy** (§3): is "multi-user shared instance, single organization" sufficient for the first promotion, or is multi-tenant isolation a hard day-one requirement?
4. **Authentication** (§4): is local-credentials-only acceptable at launch, or is account recovery (forgot-password) required from day one? Is administrator-provisioned account creation required, or is self-service registration sufficient?
5. **Data and secrets** (§5): does the first promoted app's data require real backup and/or external KMS from day one because of its sensitivity, or can both be deferred until real usage exists?
6. **First product target** (§7): do you accept `note_taking` as the first promotion candidate, or do you want `todo_list` (or a different app) instead, accepting its "preserved verbatim" frontend as a real constraint on the work?
