# Pilot Owner Setup Sheet

**Status:** Planning and configuration checklist, not an implementation task. No login,
deployment, API integration, or code change was performed to produce this document. No test,
generated app, or canonical specification was modified.

**Purpose:** Identify every decision, service, credential, and secret required for the private
AWS pilot, while keeping secret values entirely out of chat, documents, source, logs, and the
product UI. This document records **provider names, variable names, and presence/absence status
only** — never a secret value.

> **Never enter API keys, passwords, access tokens, private keys, or other secret values into
> this document, into chat, or into any Builder message. This rule is repeated at the start of
> every fill-in section below.**

---

## 1. Pilot identity and access

| Item | Status |
|---|---|
| Temporary pilot URL | **Does not exist.** No deployment has occurred anywhere in this repository. Confirmed by code: every generated app binds to `app.run(host="127.0.0.1", port=args.port)` (`verification/gen_common.py`) — loopback only, no public address of any kind. |
| AWS account/instance reference | **No AWS evidence exists in this repository.** A repository-wide search for `EC2\|VPS\|AWS\|azure\|google cloud\|heroku` found only docstring citations of "Stripe/GitHub/AWS" as *API-key-format examples*, never deployment configuration (`PRODUCT_DEPLOYMENT_DECISIONS.md` §1). This item is entirely unfilled pending Sam's actual AWS account/region/compute choice. |
| Pilot owner | Sam (per the deployment direction: "Sam has provided the initial deployment direction... Allow Sam and a small group of invited testers"). |
| General login arrangement | **Not yet implemented.** Note_taking (CAP-0201–0204) has no login capability today — confirmed by code (none of its four handler bodies reference any session/user context). The reusable engine that would add it, `add_auth_capabilities()` (`gen_common.py:1237`), is tested elsewhere but not yet applied to note_taking (`NEXT_PHASE_READINESS.md`, `PRODUCT_DEPLOYMENT_DECISIONS.md` §4/§7). |
| Tester access method | Undecided — open question in §5 below (admin-provisioned vs. self-registration). |
| Shared login vs. separate accounts | Undecided — open question in §5 below. **Recommendation** (labeled, not a fact): separate accounts per tester, since the only tested isolation pattern (`identity_and_access_demo`) depends on each user having their own account. |
| Admin permissions | The engine supports a `default_role` baked in at registration (`add_auth_capabilities(..., default_role=...)`) and `required_role`-gated capabilities (`add_capability(..., required_role=...)`) — both real and tested elsewhere, but no admin-gated capability exists in note_taking today. |
| Tester permissions | Same gap as above — no role model exists in note_taking yet. |
| Logout/session requirements | **Confirmed by code (in the reusable engine, not yet wired into note_taking):** sessions default to a 60-minute expiry (`create_session(..., ttl_minutes=60, ...)`, `gen_common.py:333`); logout genuinely invalidates the exact token server-side (`invalidate_session()`, `gen_common.py:428`) — not a soft flag. |
| Password reset policy | **Confirmed absent.** No "forgot password" flow, no email-transport integration, anywhere in the codebase (`NEXT_PHASE_READINESS.md` item 1.7, re-confirmed this pass). |
| No-email-verification decision | **Confirmed absent, and this is already the current behavior, not a choice yet to be made in code**: a repository-wide search for email-verification logic (`verify.*email`, `email_verified`, `confirm.*email`) returned zero matches. Registration accepts any non-empty string as an "email" with no format check at all (`gen_common.py:1315`: `email = (body.get('email') or '').strip().lower()`, no regex). Sam should treat "no email verification, no format validation" as the current real behavior when deciding whether that's acceptable for the pilot. |

---

## 2. Product configuration

| Item | Status |
|---|---|
| Product name | note_taking ("Real Notes" is the branding name passed to `b.finish()`, `app_defs.py:382`). |
| Purpose | Private note-taking: create, list, and delete free-text notes (title + body). |
| Enabled capabilities | CAP-0201 List Notes (GET), CAP-0202 Create Note (POST), CAP-0204 Delete Note (POST) — all three are reachable through the generated UI. |
| Disabled capabilities | **CAP-0203 Update Note exists in the API but has no UI entry point** — confirmed by code: the generated page's JavaScript never calls `/api/note_taking/notes/update`. It is reachable only via a direct API call, not through the product UI as shipped. Whether to expose it for the pilot is an open decision (see `PILOT_QUESTIONS_AND_INPUT_SPEC.md` §1, Q4). |
| Required user inputs | Note title (non-empty after trimming) on Create — enforced server-side, returns `400` otherwise. |
| Optional user inputs | Note body — defaults to empty string if omitted. |
| Data testers may enter | **Recommendation** (not a code fact): non-sensitive test content only. Notes are stored as plain, unencrypted JSON (`data/note_taking/notes.json`); `encrypt_value()`/`decrypt_value()` exist in the shared library but are not called by any of note_taking's four capabilities. |
| Data testers must not enter | **Recommendation**: real personal, financial, health, or otherwise sensitive information — there is no encryption at rest, no access control between testers today (no `owner_id` field exists on the note record, confirmed by code), and no backup mechanism (`PRODUCT_DEPLOYMENT_DECISIONS.md` §5). |
| Data retention and deletion rules | No automated retention or scheduled deletion exists anywhere in the code — the library has no background/scheduled execution mechanism at all (`is_expired()`'s own docstring: "no background timer, no scheduled job"). Delete is immediate, server-side, and irreversible (no soft-delete, no undo) once a tester clicks it. **Recommendation**: manual wipe of `data/note_taking/notes.json` at pilot end. |
| Maximum pilot tester count | Not specified anywhere; open question for Sam (see §5). |
| Pilot start and review date | Not specified anywhere; open question for Sam (see §5). |

---

## 3. External services and API-key inventory

**Finding, confirmed by code, re-verified for this document**: note_taking, the shared CAP-0000
library, and every generic engine inspected (`gen_common.py`, `app_defs.py`) reference **zero**
external providers, services, or credentials. Re-confirmed via direct search for
`os.environ`/`getenv`, `requests.`/`urllib`, runtime `http://`/`https://` calls, and provider-name
strings (`smtp`, `sendgrid`, `twilio`, `stripe`, `boto3`, `aws_`, `s3.`, `ses.`) — all zero, aside
from docstring citations that are never executed at runtime.

| Provider/service | Purpose | Env var / config name | Required for pilot | Feature affected if absent | Where to configure | No-key/self-hosted alternative | Verification method (no secret revealed) |
|---|---|---|---|---|---|---|---|
| *(none found)* | — | — | n/a | — | — | Everything the code does today is already self-hosted/local by construction | — |

**One local, non-third-party artifact, recorded for completeness (not a "provider" in scope for
this table, but relevant to secret handling):**

- `secrets/master_key.bin` (`gen_common.py:513`) — a 256-bit key generated automatically on first
  use, stored on local disk, never a third-party credential, never entered by anyone. Only
  relevant if a future change calls `encrypt_value()`/`decrypt_value()`; note_taking's current
  capabilities do not. **Verification method that reveals no secret**: check the file's
  *existence* and *modification time* (`ls -la secrets/master_key.bin`) — never its contents.

**Known, real gap this inventory does not fill in**: the deployment direction states "API keys
and user-question flows have not yet been defined." If the pilot's scope grows beyond
note_taking's existing four capabilities (see `API_KEY_AND_INPUT_REQUIREMENTS.md` §3), any new
provider must be added to this table by name and env-var only, at that time — never invented in
advance.

---

## 4. Secret-handling rules

The following procedure is required for this pilot. It is stated here as a rule set, not
performed by this document:

1. Sam obtains any needed credential directly from the provider.
2. Sam enters it directly into the AWS secret store or server environment — never into this
   document, chat, or any Builder message.
3. The credential is never pasted into ChatGPT, Builder messages, Git, source files, or the app
   UI.
4. The application reads it server-side only.
5. Logs must redact credentials.
6. The frontend must never receive provider secrets.
7. Testers must not be able to inspect environment variables, server files, API responses, or
   debug output.
8. Rotate or revoke credentials after the pilot if necessary.

**Repository-confirmed facts relevant to rules 4–7, separated clearly from recommendation:**

- **Confirmed by code**: no application-level environment variable exists anywhere in
  `gen_common.py` or `app_defs.py` today (the only env var anywhere in the tooling,
  `PLAYWRIGHT_CHROMIUM_EXECUTABLE` in `build.py:1164`, is a test-harness path, read only by the
  verification tooling, never by a generated app).
- **Confirmed by code, a real gap relevant to rule 5/7**: the host dispatcher's error handler
  (`dispatch()`, `gen_common.py:716-737`) returns **the raw exception message** to the HTTP
  client on any unhandled error: `f"handler raised {{type(e).__name__}}: {{e}}"`, at `500`. No
  logging module is used anywhere (`grep -n "import logging"` → zero matches) — errors are
  surfaced to the caller instead of a server-side log. For today's four note_taking capabilities
  this carries low risk (their bodies contain no secrets to leak this way), but **once any
  capability that touches a real secret or credential is added, this exception-message-to-client
  behavior becomes a real disclosure risk and must be addressed before that capability ships** —
  recorded here as a genuine gap, not glossed over.
- **Confirmed by code**: no structured logging, no request/response logging beyond Flask's own
  default development-server console output, exists anywhere. There is currently nothing to
  "redact" because there is no log file — this cuts both ways: no log-based leak exists today, but
  also no audit trail exists today either (`add_audit_log_capability()` is tested elsewhere but
  not wired into note_taking).

**Recommended AWS-native secret storage approach** *(recommendation, clearly separated from the
above facts, since nothing in the repository evidences any AWS configuration at all)*: AWS
Systems Manager Parameter Store (SecureString) or AWS Secrets Manager, read by the server process
at startup via the AWS SDK's own credential chain (instance role), never via a value typed into
source, a document, or chat. This is a recommendation only — no AWS access, SDK usage, or
configuration exists in this codebase today to build on.

---

## 5. Owner questions requiring Sam's answers

> **Never enter API keys, passwords, access tokens, private keys, or other secret values here.**

- Pilot URL: ______________________
- AWS deployment confirmation (account/region/compute target): ______________________
- Owner login identifier (e.g., Sam's own email to use for the admin account): ______________________
- Owner login setup method: ☐ self-register through the same flow as testers  ☐ manually seeded by direct data-file edit  ☐ other: ______________________
- Tester access method: ☐ Sam registers each tester  ☐ testers self-register at a private URL  ☐ other: ______________________
- Tester count: ______________________
- Separate accounts vs. shared login: ☐ separate accounts per tester  ☐ one shared login
- Allowed tester data: ______________________
- Prohibited tester data: ______________________
- Required providers: ______________________ (confirmed: none required by the code today — leave blank unless new scope is added)
- Optional providers: ______________________ (confirmed: none exist today — leave blank unless new scope is added)
- Approved secret storage method: ☐ AWS Secrets Manager  ☐ AWS SSM Parameter Store  ☐ other: ______________________
- Backup preference: ______________________ (confirmed: no backup mechanism exists today)
- Session timeout: ☐ accept the engine's 60-minute default  ☐ other: ______________________
- Pilot end/review date: ______________________
- Support/contact process for testers: ______________________
- Explicit features to keep disabled: ______________________ (e.g., ☐ Update Note UI  ☐ self-service password reset  ☐ other: ______________________)

---

## 6. Readiness gate

| Check | Status |
|---|---|
| All required providers identified | ✅ Yes — none exist in the code today; nothing left unidentified. |
| No unknown mandatory API keys | ✅ Yes — confirmed by exhaustive code search; zero external keys required. |
| Secrets configured outside source control | ⬜ Not yet applicable — no secret currently exists to configure (only the self-generating local `master_key.bin`, which is already outside source control by construction: `secrets/` is not committed). |
| Login configured | ❌ Not done — `add_auth_capabilities()` is not yet wired into note_taking. |
| Tester access defined | ❌ Not done — §5 above is unanswered. |
| Data boundaries defined | ❌ Not done — note_taking has no `owner_id`/isolation mechanism today; every tester would see every other tester's notes if the pilot launched as-is. |
| Backups addressed | ❌ Not done — no backup mechanism exists anywhere in the codebase. |
| HTTPS addressed | ❌ Not done — no TLS configuration exists anywhere; every app binds to loopback HTTP only. |
| Logs redacted | ⬜ Not applicable yet — no logging mechanism exists to redact; the more pressing gap is that unhandled errors return raw exception text to the client (§4), which should be closed before any secret-touching capability ships. |
| Frontend secret exposure checked | ✅ Yes, for today's scope — the generated frontend (`app_defs.py:340-382`) contains no secret of any kind; confirmed by direct reading of its full JavaScript body. |
| Rollback plan documented | ❌ Not done — no deployment exists yet, so no rollback plan for it exists either. |

**Overall: the pilot cannot proceed yet.** Four of the ten applicable checks are unmet (login,
tester access, data boundaries, backups) and two more (HTTPS, rollback) depend on a deployment
that has not happened. The two genuinely "done" items (no unknown API keys, no frontend secret
exposure) are real and code-confirmed, but they are necessary, not sufficient, conditions for
readiness.
