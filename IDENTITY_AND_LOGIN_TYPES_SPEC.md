# Identity and Login Types — Specification

No specification of "five login types" exists anywhere in this project (verified
exhaustively — see `AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md` §1).
This document is the specification the user directed be written instead: five
identity/login types designed from real research and the real needs of the
49+12-app library this builder already supports, each defined by what it is
for, what it can do, and what security requirements apply — then implemented
and tested for real. Nothing below is aspirational; every "Implementation" and
"Test evidence" line names the actual function or check that proves it.

## How these five were chosen

Not invented from generic knowledge of login providers (password/Google/Apple).
Each type is the generalized shape of a real, recurring need already visible
across this library's real apps — the same evidence standard every other
generic engine in `gen_common.py` was held to:

| Type | Real apps that need exactly this shape |
|---|---|
| Standard individual account | team_chat, project_management, crm, helpdesk_ticketing — any app with "a user" |
| Role-based privileged account | multiplayer_game (player moderation), recruitment_platform (application review), government_portal (case handling) |
| Two-sided peer account | crm (leads vs. reps), recruitment_platform (candidates vs. recruiters), multi_vendor_marketplace (buyers vs. sellers) |
| Guest/anonymous shared-access | volunteer_shift_signup, travel_planner ("shared" features that had no real access control until this round) |
| Service/system account | developer_platform (explicitly deferred last round for lack of a real key to validate against) |

## 1. Standard individual account

**Purpose.** The default identity for any person who needs their own private
data in an otherwise multi-user app — the shape underneath almost every
account system in this library.

**Capabilities.**
- Register with an email + password.
- Log in and receive a session token.
- Access only their own records (never another user's, and never by
  supplying a client-side user id).
- Log out, invalidating that exact session immediately.
- Query "who am I" from a valid session alone.

**Security requirements** (cited, not asserted):
- Passwords hashed with a real, slow, salted KDF — never stored or returned
  in plaintext. *(NIST SP 800-63B, [pages.nist.gov](https://pages.nist.gov/800-63-4/sp800-63b.html))*
- Minimum password length of 8 characters, with the *system* supporting far
  longer. *(NIST SP 800-63B, per [netwrix.com](https://netwrix.com/en/resources/blog/nist-password-guidelines/))*
- Reject known-common/breached passwords, not just enforce a length floor.
  *(NIST SP 800-63B Rev. 4 — [netwrix.com](https://netwrix.com/en/resources/blog/nist-password-guidelines/))*
- Session identifiers carry real cryptographic entropy (OWASP requires
  ≥128 bits from a CSPRNG) and a real, server-enforced expiry.
  *(OWASP Session Management Cheat Sheet, [cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html))*
- Logout must invalidate the session server-side, not just client-side.
  *(same OWASP cheat sheet)*
- No forced periodic password rotation. *(NIST SP 800-63B Rev. 4 explicitly
  dropped this requirement — [netwrix.com](https://netwrix.com/en/resources/blog/nist-password-guidelines/))*

**Implementation.** `add_auth_capabilities()` in `gen_common.py`, backed by
CAP-0000's `hash_password()`/`verify_password()` (PBKDF2-HMAC-SHA256,
200,000 iterations, salted), `is_common_password()` (blocklist screening),
and `create_session()`/`validate_session()`/`invalidate_session()`
(`secrets.token_urlsafe(32)` = 256 bits of entropy, real expiry).
Built into `identity_and_access_demo`'s standard account instance
(`data_filename="users.json"`).

**Test evidence.** `security_tests.py`: register/login/logout, duplicate-email
rejection, short-password rejection, common-password rejection, plaintext
never stored (real file inspection), cross-user data isolation, no-token and
garbage-token both 401, session expiry via real tampered timestamp,
same-token-after-logout rejection. **All passing.**

## 2. Role-based privileged account (admin)

**Purpose.** The same population as type 1, with a privilege tier for
actions an ordinary member must not be able to perform.

**Capabilities.** Everything type 1 can do, plus role-gated actions
(e.g., deleting any record, not just one's own) that a non-privileged
account is genuinely refused.

**Security requirements:**
- Authorization must be enforced on every request through a single,
  real verification layer — never trusted from client input.
  *(OWASP Authorization Cheat Sheet, [cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html))*
- **Role maintenance**: when a role changes (promotion, demotion, or the
  account is removed), earlier access must be revoked — a user must not
  keep acting under a role they no longer hold merely because their
  session hasn't expired yet. *(OWASP Authorization Cheat Sheet /
  [owasp.org Access Control](https://owasp.org/www-community/Access_Control))*
- No default/seeded privileged account and no hardcoded credential for one.

**Implementation.** `add_capability(..., required_role="admin")` wraps a
handler with a real 403 check against `ctx['role']`. Critically,
`create_session()` now accepts `role_source=(data_filename, id_field)`;
`validate_session()` re-resolves the role from the **live** user record on
every single call rather than trusting a snapshot frozen at login —
directly implementing the "Role maintenance" requirement above. If the
account has been deleted, the session fails closed (rejected), not silently
kept alive under a stale identity.

**Test evidence.** `security_tests.py`: non-admin genuinely 403'd on an
admin-only action, admin genuinely 200's on the same action, no admin
account pre-seeded before the test itself registers one — **plus** three
new checks proving the live-role fix: promoting a regular member's live
user record grants admin access on their *already-issued* token with no
re-login required; demoting them revokes it just as immediately; deleting
the account entirely invalidates the existing token (fail closed). **All
passing (45/45 total in the suite).**

## 3. Two-sided peer account

**Purpose.** A genuinely separate population from type 1/2 — not a
privilege tier of the same users, but a different kind of party
interacting with the app as a peer (e.g., an external client alongside
internal team members).

**Capabilities.** Registers and logs in independently, in its own account
table, with its own role baked in server-side; can access whatever
peer-appropriate views the app exposes (e.g., a read-only project status),
never the internal population's own private data.

**Security requirements:** the same password/session requirements as
type 1 (this is the same mechanism, reused, not a special case) — plus
genuine population separation: a peer account must never be satisfiable by
data or credentials belonging to the other population's table.

**Implementation.** `add_auth_capabilities()` called a third time in the
same app with its own `data_filename="client_users.json"`,
`default_role="client"`, and its own `route_prefix="client"` (so its
routes cannot collide with the other two instances — see the real bug this
found and fixed, `AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md`
§7.1).

**Test evidence.** `security_tests.py`: an external client registers on its
own, separate account table, distinct role. **Passing.**

## 4. Guest/anonymous shared-access

**Purpose.** Let someone view (or act on) exactly one resource with no
account, password, or session of any kind — a real shared-link, the shape
every "share this with someone who doesn't have an account" feature needs.

**Capabilities.** Resolve one specific resource by an unguessable token.
Nothing else — no listing, no access to any other resource, no way to
enumerate valid tokens.

**Security requirements:**
- The token itself must be unguessable and narrowly scoped to exactly one
  resource — compromise of one link must not expose anything else.
  *([duendesoftware.com](https://duendesoftware.com/learn/best-practices-managing-token-expiration-refresh-revocation-in-web-apis), token scoping)*
- A real expiration option must exist and be genuinely enforced when set
  (short-lived, narrowly-scoped tokens limit the blast radius of a leaked
  link). *([duendesoftware.com](https://duendesoftware.com/learn/best-practices-managing-token-expiration-refresh-revocation-in-web-apis))*
  Note: unlike an auth session, a share link legitimately has real,
  common use cases with **no** expiration by default (the same choice
  real products like Dropbox/Google Drive share links make) — this
  library makes expiration opt-in per call site (`ttl_minutes`), not
  mandatory, and documents that as a deliberate scope decision, not an
  oversight.
- An unknown, wrong-resource-type, or expired token must genuinely fail
  (404), not silently resolve to nothing or to the wrong resource.

**Implementation.** `add_share_token_capability()`, backed by
`generate_share_token()`/`validate_share_token()`
(`secrets.token_urlsafe(24)` = 192 bits, resource-type-scoped,
optional `ttl_minutes` lazily checked via `is_expired()`).

**Test evidence.** `security_tests.py`: guest resolves a board via share
link with zero authentication; a garbage token 404s; a token minted with
`ttl_minutes=60` carries a real non-null `expires_at`; a tampered/expired
timestamp is genuinely rejected. **Passing.**

## 5. Service/system account (API key)

**Purpose.** A non-human caller (an integration, a scheduled job, a
CI pipeline) that needs to act against the API without a human logging in.

**Capabilities.** Authenticate via a header-supplied key (never a
username/password); perform whatever service-scoped actions the app
exposes to `ctx['service']`; nothing an ordinary user session can do that
isn't explicitly also granted to services.

**Security requirements:**
- The raw key must be shown to the caller exactly once, at creation, and
  never again — the stored form must be a one-way hash, not a reversible
  encoding. *(Stripe/GitHub/AWS API key security practice,
  [apikeys.guide](https://apikeys.guide/docs/security/hashing-and-storage),
  [stripe.com](https://docs.stripe.com/keys-best-practices.md))*
- Verification must use constant-time comparison to avoid timing side
  channels. *(same source)*
- Revocation must be immediate and real — a revoked key must fail on its
  very next use, not eventually. *(same source)*
- An optional real expiry, checked the same lazy-evaluation way as every
  other TTL-bearing primitive in this library.

**Implementation.** `add_api_key_capability()`, backed by
`generate_api_key()`/`validate_api_key()` — the raw key is
`secrets.token_urlsafe(32)`, stored only via `hash_password()`'s PBKDF2
hash (the same primitive passwords use, so a stolen data file still yields
no usable key), checked with `verify_password()`'s constant-time
comparison, with a `revoked` flag and optional `ttl_minutes`.

**Test evidence.** `security_tests.py` / isolated `gen_common` test: a
generated key works immediately; no key and a garbage key both 401; the
real key succeeds and its action is attributed to the right service; the
raw key is never present in the stored data file (real file inspection);
a key minted with a real `ttl_minutes` genuinely stops validating once its
stored `expires_at` has passed. **Passing.**

## Cross-cutting requirements applied to all five

- **No default production passwords or seeded privileged accounts** —
  every account in every test, including admin and service accounts, is
  created fresh by the test itself.
- **Real, not simulated, authorization** — every check above is a real
  HTTP call against a real running process, or a real inspection of the
  actual on-disk data file; nothing is asserted from reading the source.
- **Fail closed, not open** — an unparsable timestamp, a deleted account
  behind a still-valid token, and a tampered ciphertext (the related
  encryption-at-rest capability) all resolve to rejection, never to a
  silently-accepted or ambiguous state.

## Full test evidence (this specification's implementation)

```
security_tests.py   45/45 passed
```
Reproducible via `python3 verification/coverage_expansion/security_tests.py`
after `python3 verification/coverage_expansion/apps/identity_and_access_demo.py`
and `.../apps/guest_and_service_demo.py`. Full-library regression (43/43
canonical, 6/6 composed, 184/184 stress test) reconfirmed unaffected — see
`AUTHENTICATION_AND_FOUNDATIONAL_CAPABILITIES_REPORT.md` §6.

## Honest limitations (unchanged from the fuller report, restated for this spec)

- Key management for the related encryption-at-rest capability is real but
  minimal (one local key file, no rotation, no external KMS) — not part of
  these five identity types themselves, but the same honesty standard
  applies.
- `secure_vault` does not use any of these five types itself; the demo apps
  proving them (`identity_and_access_demo`, `guest_and_service_demo`) are
  the reference implementations.
- No rate-limiting or brute-force lockout on login attempts exists in this
  library. This was not found as evidence from an actual app request in
  this project (unlike the five capabilities above), so it is recorded
  here as a known absence rather than invented and built without evidence.
- "Register Admin" being a public, unauthenticated endpoint in the demo app
  is a demo convenience, not a production pattern — stated plainly in the
  demo app's own module docstring.
