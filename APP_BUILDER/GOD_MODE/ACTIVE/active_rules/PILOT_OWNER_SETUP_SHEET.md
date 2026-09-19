# Pilot Owner Setup Sheet

**Status:** Planning and configuration checklist. Produced without modifying code, tests,
generated apps, deployment files, or AWS configuration. Not committed — pending Sam's explicit
approval.

**Authoritative implementation baseline:** commit `a1653ea3e8094257a558c666a47956b56cb0d597`. All
facts below are read from that exact committed state, not the working tree.

**Uncommitted pending changes exist** (Bootstrap Admin token-gating, the Login-failure journey
retarget, an additive `build.py` check, and 12 new tests). They are **proposed and reviewed, not
approved, not committed, and not treated as active anywhere in this document** except in §3 and
§6, where their status is stated explicitly. Do not read any other section as assuming they exist.

**Relationship to the prior version of this document:** committed at `501174a`, written before
note_taking had login, isolation, or admin-provisioning. §7 records the material differences.

> **Never enter API keys, passwords, access tokens, private keys, or other secret values into
> this document, into chat, or into any Builder message.**

---

## 1. Pilot identity and access

| Item | Status |
|---|---|
| Temporary pilot URL | **Does not exist.** No deployment has occurred. Every app still binds to `app.run(host="127.0.0.1", ...)` — confirmed unchanged at the current baseline. |
| AWS account/instance reference | **Still no AWS evidence anywhere in the repository.** Unchanged from the prior version of this document. |
| Pilot owner | Sam. |
| General login arrangement | **Implemented and committed**: email + password, PBKDF2-hashed, NIST-blocklist-screened. Sam is the sole administrator; testers hold non-admin accounts. **The mechanism for Sam to become that admin (Bootstrap Admin) is currently unprotected — see §3.** |
| Tester access method | **Implemented, but with a real workflow gap**: admin-gated account creation exists (`POST /api/note_taking/auth/register`, requires Sam's own session), but **no UI exists for it** — Sam must call it directly. Not a decision left open; a confirmed, current limitation of what's built. |
| Shared login vs. separate accounts | **Resolved and implemented**: separate accounts per tester; per-tester note isolation is real and tested (32/32 at the committed baseline). |
| Admin permissions | Real: `required_role="admin"` gates account creation. No other admin-only action exists in note_taking today (no admin panel, no audit-log view, no user-management UI). |
| Tester permissions | Real: default (non-admin) role: create/view/delete only their own notes; cannot create accounts (`403`, confirmed by test) or see other testers' notes (confirmed by test). |
| Logout/session requirements | **Confirmed, implemented, tested**: 12-hour session lifetime (`session_ttl_minutes=720`), immediate real server-side invalidation on logout. |
| Password reset policy | **Confirmed absent, and now confirmed to be a hard gap, not merely a soft policy question**: no password-reset, password-change, or delete-account capability exists anywhere in the code. Once a tester's account is created with a given password, there is no way to change or recover it through the application. |
| No-email-verification decision | **Confirmed absent, unchanged**: any non-empty string is accepted as an "email," no format validation. |

---

## 2. Product configuration

| Item | Status |
|---|---|
| Product name | note_taking ("Real Notes"). |
| Purpose | Private, per-tester note-taking: create, view, delete short text notes, now with real login and real isolation. |
| Enabled capabilities | List/Create/Delete Notes (UI + API), Login/Logout/Me (UI + API), admin-gated Register / "Create User" (**API only, no UI**), Bootstrap Admin (UI + API, **currently unprotected — §3**). |
| Disabled capabilities | Update Note has no UI (API-only, unchanged from the prior version of this document). |
| Required user inputs | Note title (tester); email + password (everyone, at login); email + password (Sam, at bootstrap and at each tester's creation). |
| Optional user inputs | Note body. |
| Data testers may enter | **Recommendation, unchanged**: non-sensitive test content only — notes remain plain, unencrypted JSON; `encrypt_value()`/`decrypt_value()` still exist but are still not called by any note_taking capability. |
| Data testers must not enter | **Recommendation, strengthened**: still no encryption at rest and no backup; isolation between testers is now real and tested, which narrows but does not eliminate this recommendation (a compromised admin account, or the still-open Bootstrap Admin gap, would expose everything). |
| Data retention and deletion rules | Unchanged: no automated retention/deletion; delete is instant and irreversible per note. No way to delete a whole account. |
| Maximum pilot tester count | Not specified; open question for Sam. |
| Pilot start and review date | Not specified; open question for Sam. |

---

## 3. External services and API-key inventory

**Finding, confirmed by code at the committed baseline, re-verified for this document**:
note_taking, the shared CAP-0000 library, and every capability newly added for the pilot (login,
isolation, admin-gated registration, Bootstrap Admin) reference **zero external providers,
services, or credentials**. Re-confirmed by direct search of the actual committed
`gen_common.py`/`app_defs.py` for `os.environ`/`getenv`, `requests.`/`urllib`, runtime
`http://`/`https://` calls, and provider-name strings — all zero at the committed baseline.

| Provider/service | Purpose | Env var / config name | Required for pilot | Genuinely necessary? | Who supplies the credential | Feature affected if absent | Where to configure | No-key/self-hosted alternative |
|---|---|---|---|---|---|---|---|---|
| *(none — not required for the initial pilot)* | — | — | No | No external service is used anywhere in the committed code | n/a | n/a | n/a | Everything is already self-hosted/local |

**One item that is NOT yet part of the committed baseline, disclosed for completeness and not to
be treated as active**: the proposed, unapproved Bootstrap Admin fix would introduce exactly one
new server-side environment variable, `BOOTSTRAP_SETUP_TOKEN` — not a third-party API key, never
transmitted to any external service, generated and held entirely by Sam if and when the fix is
approved. It does not exist in the committed baseline this sheet otherwise describes.

**How credentials are kept hidden — confirmed mechanisms, at the committed baseline:**

- Passwords are hashed (PBKDF2-HMAC-SHA256, salted) before storage; `hash_password()`'s own output
  is stripped from every API response that could otherwise echo it (`register`/`bootstrap-admin`
  both explicitly exclude `password_hash` from their returned object).
- Session tokens are 256-bit random values (`secrets.token_urlsafe(32)`), never derived from or
  containing the password.
- **A real, confirmed gap, unchanged from the prior version of this document**: the host
  dispatcher's exception handler, at the committed baseline, still returns the raw exception
  message to the client on an unhandled error — recorded here again because it remains true today,
  not resolved by the note_taking work. (An uncommitted, unapproved fix for this also exists in the
  working tree but is not active — see the parallel note in the questions document §7.)
- No structured logging exists at the committed baseline, so there is no log file to leak a
  credential into — but also no audit visibility beyond direct file inspection of
  `data/audit_log.json` on the server (no in-app view of it exists).
- Generated frontend source at the committed baseline contains no secret value of any kind — the
  Bootstrap Admin password field carries only a non-secret placeholder value (`"correcthorse"`),
  disclosed here plainly as a real, low-sensitivity convenience value, not a real credential.

---

## 4. Secret-handling rules

Unchanged in substance from the prior version of this document — restated because it remains the
correct procedure regardless of the note_taking changes:

1. Sam obtains any needed credential directly from its source.
2. Sam enters it directly into the AWS secret store or server environment — never into this
   document, chat, or any Builder message.
3. Never pasted into Git, source files, or the app UI.
4. Read server-side only.
5. Logs must redact credentials (moot today: no log file exists yet at the committed baseline).
6. The frontend must never receive provider secrets (confirmed: none exist to receive).
7. Testers must not be able to inspect environment variables, server files, API responses, or
   debug output.
8. Rotate or revoke credentials after the pilot if any are ever introduced.

**Recommended AWS-native secret storage approach** *(recommendation only; no AWS configuration
exists in this codebase)*: AWS Secrets Manager or SSM Parameter Store, read via the instance's own
role — unchanged from the prior version of this document, and now the actual, concrete destination
for `BOOTSTRAP_SETUP_TOKEN` if and when that proposed fix is approved.

---

## 5. Owner questions requiring Sam's answers

> **Never enter API keys, passwords, access tokens, private keys, or other secret values here.**

- Pilot URL: ______________________
- AWS deployment confirmation (account/region/compute target): ______________________
- Owner login identifier (bootstrap admin email): ______________________
- **Do you approve the Bootstrap Admin protection fix reviewed in this session (§3/§6), before any
  deployment?** ☐ Yes, approve and commit it  ☐ No, hold  ☐ Need changes first: ______________________
- **How should tester accounts actually be created**, given no UI exists today? ☐ Accept
  curl/API-only for this pilot  ☐ Build a minimal "Create User" UI first  ☐ Other: ______________________
- Tester count: ______________________
- Allowed tester data: ______________________
- Prohibited tester data: ______________________
- Required providers: ______________________ (confirmed: none required by the code today)
- Approved secret storage method for `BOOTSTRAP_SETUP_TOKEN`, if approved: ☐ AWS Secrets Manager
  ☐ AWS SSM Parameter Store  ☐ other: ______________________
- Backup preference: ______________________ (confirmed: still no backup mechanism exists)
- Session timeout: ☐ accept 12 hours (implemented)  ☐ other: ______________________
- **Account-recovery policy**, given no reset/change/delete mechanism exists: ______________________
- Pilot end/review date: ______________________
- Support/contact process for testers: ______________________

---

## 6. Readiness gate

| Check | Status |
|---|---|
| All required providers identified | ✅ Yes — none exist in the committed code today. |
| No unknown mandatory API keys | ✅ Yes. |
| Secrets configured outside source control | ⬜ Not yet applicable — no real secret exists in the committed baseline; `BOOTSTRAP_SETUP_TOKEN` would only apply once the proposed fix is approved. |
| Login configured | ✅ **Yes, committed and tested** (32/32 at `a1653ea`) — a real change from the prior version of this document. |
| Tester access defined | ⚠️ **Partially** — the mechanism exists and is tested, but has no UI; Sam must decide whether that's acceptable (§5). |
| Data boundaries defined | ✅ **Yes, committed and tested** — real, server-resolved `owner_id` isolation. |
| **Bootstrap Admin protected against an unauthenticated remote race** | ❌ **No — confirmed open in the committed baseline.** A fix has been reviewed and drafted but is **not committed or approved**. This is the single blocking item before any deployment. |
| Account recovery defined | ❌ **Not done — and not merely undecided: no mechanism exists in the code to build a policy around yet** (no reset/change/delete capability at all). |
| Backups addressed | ❌ Not done — unchanged. |
| HTTPS addressed | ❌ Not done — unchanged, and now more urgent than before: real passwords and session tokens exist and would travel in plaintext over HTTP. |
| Logs redacted | ⬜ Not applicable yet — no log file exists; the more pressing, still-open issue is the raw-exception-to-client gap (§3). |
| Frontend secret exposure checked | ✅ Yes — confirmed clean at the committed baseline. |
| Rollback plan documented | ❌ Not done — no deployment exists yet. |

**Overall: the pilot cannot proceed to AWS deployment or tester invitations yet.** Login and
isolation — the two largest pieces of prior missing work — are now real, committed, and tested.
What remains is a shorter but still blocking list: approve (or replace) the Bootstrap Admin fix,
decide the tester-account-creation workflow, decide an account-recovery policy, and complete the
already-known AWS/HTTPS/backup work. None of the four uncommitted files in the working tree should
be treated as resolving any of these until explicitly approved.

---

## 7. What changed from the prior version of this document (`501174a`)

| Prior document said | Now (committed baseline `a1653ea`) |
|---|---|
| "General login arrangement: Not yet implemented" | Implemented, committed, tested |
| "Data boundaries defined: ❌ Not done" | ✅ Done — real, tested `owner_id` isolation |
| No mention of Bootstrap Admin | New capability exists — and its own missing protection is a newly found, currently unresolved vulnerability (§3/§6) |
| No mention of a "Create User" UI gap | Now a confirmed, real gap (§1) |
| No mention of account recovery | Now a confirmed, real gap: no reset/change/delete mechanism exists at all (§1, §6) |
| Session timeout: 60 minutes (unapplied engine default) | 12 hours, confirmed applied and tested |
| "HTTPS addressed: ❌ Not done" | Still ❌ Not done — and now materially more urgent, since real credentials and session tokens now exist to protect |

The external-services finding (§3 — zero required), the secrets-directory finding, and the
backups/monitoring findings are unchanged and still accurate.
