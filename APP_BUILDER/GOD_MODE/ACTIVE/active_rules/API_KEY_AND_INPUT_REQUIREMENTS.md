# API Key and Input Requirements

**Status:** Read-only inspection document. No application code, tests, generated apps, or
canonical specifications were modified to produce this document.

**Scope:** The first product target is **note_taking** (`build_note_taking()` in
`verification/app_defs.py`), provisionally confirmed in `PRODUCT_DEPLOYMENT_DECISIONS.md`.
`PRODUCT_DEPLOYMENT_DECISIONS.md` also recommended (as a recommendation, not yet a decision)
promoting two currently-disposable capabilities — `add_auth_capabilities()` (login/session) and
`add_audit_log_capability()` (audit trail) — from `verification/gen_common.py` into the pilot
build, since the pilot requires login. This document therefore inspects **both** the note_taking
app's own code and the shared CAP-0000 primitives / auth capability that a login-gated pilot
would need to add, because both are "the actual first-product code" once login is included.

Every item below is sourced from a direct code inspection command run against this repository on
2026-09-13. No item was inferred, assumed, or carried over from outside the codebase.

---

## 1. Confirmed from code

### 1.1 External services or API integrations

**Finding: none.**

- `verification/app_defs.py`'s `build_note_taking()` (line 297) defines four capabilities
  (CAP-0201 List Notes, CAP-0202 Create Note, CAP-0203 Update Note, CAP-0204 Delete Note). Their
  route bodies only call the shared `load()`/`save()` primitives against a local JSON data file.
  No HTTP client, SDK, or external service call appears in any of them.
- A repository-wide search of `verification/gen_common.py` (the file containing every generic
  capability engine, including `add_auth_capabilities()` and `add_audit_log_capability()`, and
  the CAP-0000 shared library itself) for `requests.`, `urllib`, `http://`, `https://` found zero
  runtime calls to any non-local host. The only `https://` strings present are citation URLs
  inside docstrings (NIST SP 800-63B, OWASP cheat sheets, Stripe/GitHub API-key convention
  references) used as design justification in comments — none are fetched or called at runtime.
- `notify()` (`verification/gen_common.py:227`) — the shared notification primitive some
  capabilities call — writes to a local `notifications.json` file. It is not an email, SMS, or
  push-notification integration.
- `audit()` (`verification/gen_common.py:240`) writes to a local `audit_log.json` file. It is not
  a third-party logging/observability service.
- A repository-wide case-insensitive search for `smtp`, `sendgrid`, `twilio`, `stripe`, `boto3`,
  `aws_`, `s3.`, `ses.` in `gen_common.py` matched only three docstring mentions of "Stripe",
  "GitHub", and "AWS" used purely as *naming-convention citations* for the API-key format design
  (e.g. "the same real-format pattern as Stripe/GitHub/AWS key issuance") — not as integrations.
- **`add_auth_capabilities()` and `add_audit_log_capability()` are not currently used by any
  canonical or composed app in `verification/app_defs.py`.** A direct grep for both function
  names inside `app_defs.py` returned zero matches. This confirms `NEXT_PHASE_READINESS.md`'s
  finding: these capabilities exist only in the disposable `verification/coverage_expansion/`
  workspace today. Promoting them into note_taking for the pilot (per
  `PRODUCT_DEPLOYMENT_DECISIONS.md`'s recommendation) is real, not-yet-done implementation work,
  separate from this document.

### 1.2 Environment variables expected by the code

**Finding: one, and it is unrelated to the running application.**

- `build.py:1164`: `_chromium_path = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")`. This is a
  build/test-harness variable that tells the Playwright browser-journey test where to find a
  Chromium binary. It is read only by the verification tooling, never by a generated Flask app,
  and has no effect on note_taking, login, or any runtime request path.
- A repository-wide search of `gen_common.py` and `app_defs.py` for `os.environ` / `os.getenv`
  found no other occurrences. **No application-level environment variable currently exists
  anywhere in this codebase** — not for note_taking, not for the auth capability, not for any of
  the 43 canonical or 6 composed apps.

### 1.3 Credentials or API keys required

**Finding: none required by note_taking's own code. One local (non-third-party) key exists in
the shared library that login would depend on.**

- `_master_key()` (`verification/gen_common.py:513`) generates a random 256-bit AES key on first
  use and persists it to a local file, `secrets/master_key.bin`, relative to the repository root
  (`SECRETS_DIR = Path(__file__).resolve().parents[2] / "secrets"`, `gen_common.py:157`). It sets
  owner-only file permissions (`0o600`) where the OS supports it. This key is used by
  `encrypt_value()` / `decrypt_value()` for at-rest encryption of specific fields.
  - This is **not** a third-party API key or credential. It is generated locally, never
    transmitted, never hardcoded, and never committed (the `secrets/` directory does not exist
    in the repository checkout — it is created on first use, at runtime).
  - The function's own docstring is explicit about its limits: "a single local, random, 256-bit
    key generated on first use... deliberately NOT a real KMS: single key, no rotation, no
    per-tenant separation, held on the same disk as the ciphertext it protects." For a pilot with
    a small invited group this is a recorded, honest limitation, not a hidden one.
  - Note_taking's own four capabilities do not call `encrypt_value()`/`decrypt_value()` today —
    this key only becomes relevant to note_taking if the pilot build encrypts note content or
    stores auth secrets (e.g. session tokens) via this mechanism.
- `add_auth_capabilities()` uses `hash_password()` / `verify_password()` (both in the CAP-0000
  shared library) for password storage — real salted hashing, not a third-party auth provider.
  This introduces no external credential either.
- **No third-party API key of any kind (payment, email, SMS, cloud storage, analytics, error
  tracking, etc.) is referenced, imported, or required anywhere in the inspected code.**

### 1.4 Software dependencies (for completeness, since these gate what can run at all)

From `verification/requirements.txt` (pinned, vendored, offline-installable):
`flask==3.1.3`, `werkzeug==3.1.8`, `jinja2==3.1.6`, `markupsafe==3.0.3`, `itsdangerous==2.2.0`,
`click==8.5.0`, `blinker==1.9.0` (Flask and its direct dependencies — required to run any app),
`playwright==1.62.0`, `pyee==13.0.1`, `greenlet==3.5.5`, `typing_extensions==4.16.0`
(browser-journey testing only — not needed at pilot runtime), and `cryptography==50.0.1`,
`cffi==2.1.1`, `pycparser==3.0` (needed only if `encrypt_value()`/`decrypt_value()` is exercised).
None of these require an API key or account to install or run; all are installable from the
vendored wheels with no network access.

---

## 2. Recommended for the pilot

These are recommendations only, clearly separated from the confirmed facts above. None has been
decided or implemented.

- **If login is added for the pilot** (as `PRODUCT_DEPLOYMENT_DECISIONS.md`'s direction requires),
  promote `add_auth_capabilities()` into the note_taking build rather than writing new
  auth code, since it is already implemented and tested in the disposable workspace per
  `NEXT_PHASE_READINESS.md`.
- Store `secrets/master_key.bin` (if encryption-at-rest is used for notes or session data) on
  durable, non-ephemeral storage in whatever AWS compute target is chosen — the key must survive
  restarts/redeploys or already-encrypted data becomes unrecoverable. This is an operational
  requirement, not a new code requirement.
- If a production-style secrets manager (e.g. AWS Secrets Manager, SSM Parameter Store) is later
  desired to hold this key instead of a local file, that is new work not present in the codebase
  today — record it as a gap rather than assuming it is already handled.
- No environment variable scheme currently exists for the application; if the pilot needs any
  configurable value (e.g. a session-cookie lifetime, an admin allow-list of invited testers),
  that plumbing does not exist yet and would need to be designed and built, not merely configured.

---

## 3. Missing information from Sam

The following cannot be determined from the repository and must come from Sam before pilot
implementation begins. None of these has been guessed or assumed anywhere in this document.

1. **Invited testers list**: who exactly is in the "small group of invited testers" — names/email
   addresses for account provisioning — is not defined anywhere in the repository and was
   explicitly flagged as undefined in the deployment direction itself.
2. **API keys and user-question flows**: the deployment direction states these "have not yet been
   defined." Since note_taking's own code needs none today, this item only becomes relevant if
   the pilot's scope grows beyond the four existing note capabilities (e.g. adding AI-assisted
   note features, search, or export) — Sam has not specified whether any such expansion is in
   scope for the pilot.
3. **Whether encryption-at-rest is required for the pilot**: note_taking does not currently call
   `encrypt_value()`. Whether pilot notes must be encrypted at rest (and therefore whether
   `secrets/master_key.bin` durability becomes a hard requirement) is undecided.
4. **Session/cookie lifetime and password policy specifics for the pilot**: `add_auth_capabilities()`
   supports configurable roles and reuses CAP-0000's password/session primitives, but pilot-specific
   values (session length, whether MFA is required for a private pilot) are policy decisions, not
   code facts, and are not addressed here (see `PILOT_DEPLOYMENT_PLAN.md` for the login/session
   framing at the architecture level).

---

## 4. Explicitly deferred until after the pilot

- Any real third-party API integration (payment processing, email delivery, SMS, cloud storage
  beyond local disk, analytics, error tracking) — none exists in the code today, and none is
  needed for a private, invite-only pilot of the four existing note_taking capabilities.
- A production-grade secrets manager (AWS Secrets Manager/SSM) to replace the local
  `secrets/master_key.bin` file — deferred because no such integration exists in the codebase and
  the pilot's small, invited scope does not require it; recorded here as a known future gap, not a
  pilot blocker.
- Multi-tenant key separation / per-tenant encryption keys — `_master_key()`'s own docstring
  already records single-key, no-per-tenant-separation as a known limitation; out of scope until
  the product moves beyond a single-tenant pilot.
- Defining and building any AI/API-key-dependent "user-question flows" referenced in the
  deployment direction — explicitly undefined by Sam and explicitly out of scope for this
  document, which only reports what the code requires today.
