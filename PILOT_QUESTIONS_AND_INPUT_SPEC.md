# Pilot Questions and Input Specification

**Status:** Read-only inspection document. No application code, tests, generated apps, or
canonical specifications were modified to produce this document. No deployment was performed.

**Scope:** The first product target is **note_taking** (`build_note_taking()` in
`verification/app_defs.py:297`, capabilities CAP-0201–CAP-0204). Its exact generated frontend
(`body_inner`/`script` in `app_defs.py:340-382`) and exact API bodies were read directly for this
document. Where the pilot's own login requirement (Sam's deployment direction) is not yet wired
into note_taking, that gap is stated plainly rather than assumed solved — see
`PRODUCT_DEPLOYMENT_DECISIONS.md` §4/§7 and `API_KEY_AND_INPUT_REQUIREMENTS.md` for the underlying
evidence this document builds on.

---

## 1. Product-user questions

These are the actual input fields a tester answers while using note_taking, taken directly from
the generated UI (`app_defs.py:340-350`) and the API bodies behind it (`app_defs.py:297-338`).

**Important frontend fact confirmed by code**: the generated UI wires only **Create** (the
title/body inputs and "Add note" button) and **Delete** (a per-row button, no text input) to
visible controls. **CAP-0203 (Update Note) has no UI entry point at all** — it exists only as an
API endpoint (`POST /api/note_taking/notes/update`) that the generated page's own JavaScript never
calls. A tester using the rendered app cannot edit an existing note; only create and delete are
reachable through the UI today.

### Q1 — Note title

- **Exact question wording** (as rendered): the input's placeholder text, `"Title"` (`app_defs.py:341`).
- **Why it is needed**: CAP-0202 (Create Note) requires a non-empty title; the shared library's
  own handler returns `400 {'error': 'title is required'}` otherwise (`app_defs.py:314`).
- **Required or optional**: Required.
- **Expected answer type**: Free-text string.
- **Validation rules**: Server-side only — `title.strip()` must be non-empty (`app_defs.py:311`).
  The client-side script also short-circuits on an empty/whitespace title (`if (!title.trim())
  return;`, `app_defs.py:379`) so the request is never sent at all in that case — this is a UX
  convenience, not a security boundary; the server check is the real one. No length cap, no
  character restriction, no HTML-escaping is applied anywhere in the code.
- **Where the answer is used**: Stored verbatim (after stripping) as the `title` field of the note
  record in `notes.json`; echoed back in the Create response and in every subsequent List Notes
  response.
- **What happens if the answer is missing**: The client never sends the request (see above); if
  bypassed (e.g., a direct API call), the server returns `400` and no note is created.
- **Confirmed by code or recommended**: Confirmed by code.

### Q2 — Note body

- **Exact question wording** (as rendered): the textarea's placeholder text, `"Write your
  note..."` (`app_defs.py:342`).
- **Why it is needed**: Free-text content of the note itself.
- **Required or optional**: Optional. `body` defaults to `''` if omitted or blank
  (`app_defs.py:312`: `text = (body.get('body') or '').strip()`).
- **Expected answer type**: Free-text string, may be empty or multi-line.
- **Validation rules**: None beyond the server's own `.strip()` on create. No length cap, no
  format restriction, no HTML-escaping.
- **Where the answer is used**: Stored as the `body` field of the note record; echoed back in
  Create/List responses; rendered directly into the page as `textContent` (not `innerHTML`), so
  the browser does not interpret it as HTML — confirmed by code (`app_defs.py:359`:
  `p.textContent = n.body;`).
- **What happens if the answer is missing**: The note is created with an empty body; no error.
- **Confirmed by code or recommended**: Confirmed by code.

### Q3 — Delete confirmation (not a text question)

- **Exact wording**: The button label is `"Delete"` (`app_defs.py:358`). There is no confirmation
  dialog — clicking it immediately sends the delete request for that note's `id`.
- **Why it is needed**: n/a — this is an action, not an input a tester types an answer to. Listed
  here because it is part of the minimum tester-facing workflow and because its lack of a
  confirmation step is a real, code-confirmed fact worth surfacing before pilot testers use it.
- **Required or optional**: n/a.
- **Expected answer type**: n/a (button click).
- **Validation rules**: None — no "are you sure?" step exists in the generated UI.
- **Where the answer is used**: `id` is read from the row's own `dataset.id` (set from the note
  the server returned), not typed by the tester, and sent to `POST /api/note_taking/notes/delete`.
- **What happens if the answer is missing**: n/a — the id is always present because it comes from
  an already-rendered row.
- **Confirmed by code or recommended**: Confirmed by code. **Recommendation** (clearly separated
  from the above facts): consider adding a confirmation step before the pilot, since deletion is
  immediate and irreversible (no soft-delete or undo exists anywhere in the code).

### Q4 — Update Note fields (API-only; recommended if exposed to testers)

CAP-0203 accepts `id` (required — a `404 {'error': f'no note with id {nid!r}'}` is returned if it
doesn't match an existing note, `app_defs.py:327`), and optional `title`/`body` (title is
stripped and falls back to the existing value if blank; body is assigned directly with **no
`.strip()` call**, unlike title and unlike Create — confirmed by code at `app_defs.py:325`: `n['body']
= body.get('body', n['body'])`). This capability is **confirmed by code to exist**, but whether it
is ever surfaced to testers is **recommended, not decided** — it has no UI today (see above), so
this only becomes a real "question a tester answers" if a pilot-only edit UI is built.

### Q5 — Email and password (login/registration; recommended, not yet implemented in note_taking)

Sam's deployment direction requires login for the pilot. Note_taking's own code has no
login capability today (§1's four capabilities are all unauthenticated). The engine that would
provide it, `add_auth_capabilities()` (`gen_common.py:1237`), already exists, is tested elsewhere
(`security_tests.py`, per `NEXT_PHASE_READINESS.md`), and is what `PRODUCT_DEPLOYMENT_DECISIONS.md`
§4/§7 recommends promoting into note_taking — but this is not yet done. The two fields below are
listed here because the pilot cannot ship without login per Sam's own direction, and their exact
behavior is fully confirmed by the existing engine code, even though note_taking does not call it
yet.

- **Exact question wording**: not yet rendered anywhere (no auth UI exists for note_taking yet);
  the engine's API fields are `email` and `password` (`gen_common.py:1315-1316`).
- **Why needed**: Register/Login both require both fields (`400 {'error': 'email and password are
  required'}` otherwise, `gen_common.py:1318`).
- **Required or optional**: Both required.
- **Expected answer type**: `email` — free-text string, lowercased and stripped server-side
  (**no email-format validation exists in the code** — any non-empty string, including one with
  no `@`, is accepted as an "email," confirmed by code: `email = (body.get('email') or
  '').strip().lower()` with no regex or format check anywhere in `gen_common.py`). `password` —
  free-text string.
- **Validation rules**: Password must be at least 8 characters (`gen_common.py:1319`) and must not
  match the common/breached-password blocklist checked by `is_common_password()`
  (`gen_common.py:1320`, NIST SP 800-63B-cited). No email format validation, no password complexity
  rule (uppercase/digit/symbol) beyond length + blocklist.
- **Where the answer is used**: `email` becomes the account's unique identifier (registration
  rejects a duplicate with `409`, `gen_common.py:1321`); `password` is hashed
  (PBKDF2-HMAC-SHA256, salted, `hash_password()`) and never stored or returned in plaintext.
- **What happens if the answer is missing**: `400` on register/login; no account created, no
  session issued.
- **Confirmed by code or recommended**: The field behavior is confirmed by code (in the reusable
  engine). Its application to note_taking is a recommendation, not yet implemented.

---

## 2. Pilot-owner decisions

Each item is a decision Sam must make. Recommended defaults are clearly labeled as
recommendations, never as facts already decided.

| # | Decision | Recommended default | Consequence of each answer | Blocks implementation? |
|---|---|---|---|---|
| 1 | General login identifier and password arrangement | Email + password, one account per tester (matches the only implemented mechanism, `add_auth_capabilities()`) | A shared single login loses per-tester audit trail and the already-built per-user isolation pattern (`identity_and_access_demo`); individual accounts use exactly what's already tested. | Yes — auth cannot be promoted into note_taking without knowing which shape to build. |
| 2 | How tester access is provided | Sam (or an admin account) registers each tester's email, or testers self-register against a private URL only shared with invitees | Self-registration needs no new capability (the engine already supports it); admin-provisioned accounts need a new role-gated "Create User" capability (small new work, per `PRODUCT_DEPLOYMENT_DECISIONS.md` §4). | Yes — determines whether new capability work is needed before pilot start. |
| 3 | Whether all testers share one login or receive separate invited logins | Separate logins per tester | A shared login makes per-user data isolation (owner_id-based, already the proven pattern) meaningless — every tester would see every other tester's notes. Separate logins is required to use the already-tested isolation pattern at all. | Yes — this decides whether the "add owner_id + ownership check" work in `PRODUCT_DEPLOYMENT_DECISIONS.md` §7 is meaningful or moot. |
| 4 | Current temporary pilot URL | None exists — no deployment has occurred anywhere in this repository (confirmed: `app.run(host="127.0.0.1", ...)` only; no Dockerfile, no cloud config, no domain reference anywhere) | n/a until §1 (deployment target) of `PRODUCT_DEPLOYMENT_DECISIONS.md` is decided and executed. | Yes — cannot be answered until deployment happens; recorded here as explicitly unknown, not guessed. |
| 5 | AWS deployment details already evidenced by the project | None exist. A repository-wide search for `EC2\|VPS\|AWS\|azure\|google cloud\|heroku` found only citation mentions of "Stripe/GitHub/AWS" as API-key-format examples in docstrings (`PRODUCT_DEPLOYMENT_DECISIONS.md` §1) — not deployment configuration. | n/a — this is a pure gap, not a decision with options. | Yes — AWS account/region/compute choice must come entirely from Sam; nothing in the repo informs it. |
| 6 | Session timeout | 60 minutes — the engine's own default (`create_session(..., ttl_minutes=60, ...)`, `gen_common.py:333`), already in effect wherever the engine is used | A shorter timeout increases friction for testers re-logging in during a work session; a longer one increases the window an unattended, logged-in browser stays valid. 60 minutes is untouched, tested behavior; changing it is a one-parameter code change, not new design. | No — has a safe, already-tested default; only blocks if Sam wants a different value before promotion. |
| 7 | Logout behavior | Real, immediate server-side invalidation — already implemented (`invalidate_session()`, `gen_common.py:428`): "the exact same token used again after this genuinely fails validate_session()." | None — this is already a real, tested behavior, not an open question, once the auth engine is promoted. | No. |
| 8 | Password reset policy | None exists in the code today (`NEXT_PHASE_READINESS.md` item 1.7; confirmed again this pass — no "forgot password" flow, no email-transport integration anywhere). Recommendation: accept "no self-service reset; Sam manually resets by contacting the tester" for the pilot, given the small, invited group. | Building real self-service reset requires a real email-transport integration — a new external-integration decision this project has consistently deferred (see §3 below). Accepting manual reset for the pilot avoids that decision entirely. | No, if the manual-reset recommendation is accepted; Yes, if self-service reset is required before pilot start (forces an email-provider decision first). |
| 9 | Tester permissions | All testers get the same, non-admin role (`default_role=None` in `add_auth_capabilities()`); Sam alone holds an admin-role account for any admin-gated capability. | A single shared role for all testers is the smallest change from the currently tested pattern (`identity_and_access_demo`'s two-role model: default + admin). | No — the engine already supports exactly this with no new design. |
| 10 | Data visibility between testers | **Currently: full visibility — note_taking has no `owner_id` field or ownership check of any kind today** (confirmed by code: none of CAP-0201–0204's bodies reference any user/session context). Recommendation: add `owner_id` + ownership checks (already the proven pattern in `identity_and_access_demo`) before any tester sees another tester's notes. | Without this change, every tester's notes are visible to every other tester and to any authenticated account — a real, currently-true fact that would surprise a pilot tester expecting privacy. | **Yes — this must be resolved (implemented or explicitly accepted as shared) before the pilot admits more than one tester**, since it directly determines what testers will actually experience. |
| 11 | Data retention and deletion | No retention policy or scheduled deletion exists anywhere in the code (the library has no background/scheduled execution mechanism at all — `is_expired()`'s own docstring: "no background timer, no scheduled job"). Recommendation: manually wipe `data/note_taking/notes.json` at pilot end; no automated purge exists to rely on. | Accepting "delete is a manual, one-time cleanup step" avoids new work; anything automated (e.g., auto-expiring old notes) would be new capability design out of this pilot's scope. | No, if manual end-of-pilot cleanup is accepted. |
| 12 | Acceptable test data | Recommendation: no real personal, financial, or sensitive data — notes are stored as plain, unencrypted JSON (`encrypt_value()`/`decrypt_value()` exist but are not called by note_taking's own capabilities today), with no access control (pending #10) and no backup (confirmed absent, `PRODUCT_DEPLOYMENT_DECISIONS.md` §5). | Real/sensitive test data would be exposed by the very same gaps already documented (no encryption applied, no isolation yet, no backup). | No — a policy decision, not a blocker to starting the pilot, but should be communicated to testers before they enter anything. |
| 13 | Whether external integrations are enabled | None exist to enable — confirmed by code (`API_KEY_AND_INPUT_REQUIREMENTS.md` §1): zero external service/API calls anywhere in `gen_common.py` or `app_defs.py`'s note_taking build. | n/a. | No. |
| 14 | Which API keys are genuinely required | **None** — confirmed by code; the only key-like artifact is `secrets/master_key.bin`, generated locally at runtime, never a third-party credential. | n/a. | No. |
| 15 | What happens when an API key is absent | n/a for note_taking today — no code path checks for or depends on any external API key. `_master_key()` generates its own key locally on first use rather than reading one from configuration, so there is no "absent key" failure mode to define for the pilot. | n/a. | No. |

---

## 3. API-key and integration questions

**Finding, confirmed by code**: note_taking, the shared CAP-0000 library, and every generic
engine inspected (`gen_common.py`, `app_defs.py`) reference **zero external providers, services,
or credentials**. This was independently re-confirmed for this document via direct grep for
`os.environ`/`getenv`, `requests.`/`urllib`, `http://`/`https://` (runtime calls, not docstring
citations), and provider-name strings (`smtp`, `sendgrid`, `twilio`, `stripe`, `boto3`, `aws_`,
`s3.`, `ses.`) — see `API_KEY_AND_INPUT_REQUIREMENTS.md` §1 for the full command-level evidence
trail. No table row exists below because there is nothing to list — inventing a placeholder
provider or key would violate this document's own instruction not to invent one.

| Provider/service | Exact env var / config name | Required for pilot? | Functionality affected if absent | Secret storage recommendation | No-key/self-hosted alternative exists? |
|---|---|---|---|---|---|
| *(none found)* | *(none found)* | n/a | n/a | n/a | n/a — everything the code does today is already self-hosted/local by construction |

The one local, non-third-party artifact worth recording for completeness (not a "provider" in the
sense this section asks about, but relevant to secret-handling planning):

- **Local encryption key** (`secrets/master_key.bin`, `gen_common.py:513`): not an API key, not
  tied to any external account. Generated automatically on first use; required only if a future
  change calls `encrypt_value()`/`decrypt_value()` (note_taking's current four capabilities do
  not). If it were ever absent, it is regenerated fresh on next use (with the honest consequence
  that anything previously encrypted under the old key becomes unrecoverable) — not a hard
  failure, but a real data-loss risk worth flagging for pilot operational planning.

---

## 4. Minimum pilot questionnaire

The following is the short, user-facing list Sam needs to answer now, before any deployment or
promotion work begins. Nothing below has been answered on Sam's behalf.

1. Login identifier/password arrangement: one account per tester, email + password? (yes/no; if
   no, describe the alternative)
2. Tester access: does Sam register each tester's account, or do testers self-register at a
   private URL Sam shares with them?
3. Shared login or separate logins per tester? (separate is required for any per-tester data
   privacy)
4. Is per-tester data privacy (notes not visible to other testers) required before the pilot
   starts, or is a shared, fully-visible note pool acceptable for this pilot?
5. Is a 60-minute session timeout acceptable, or should it be shorter/longer?
6. Is "no self-service password reset — Sam resets manually" acceptable for the pilot?
7. Should Delete get a confirmation step before pilot testers use it? (currently instant, no undo)
8. What is the actual AWS account/region/compute target? (nothing in the repository evidences
   this; it must come entirely from Sam)
9. What is the intended pilot URL/domain, if any, or is a bare IP/default cloud hostname
   acceptable for a private pilot?
10. Any explicit instruction on what test data testers may or may not enter, given that notes are
    stored unencrypted with no access control until item 4 above is resolved?
