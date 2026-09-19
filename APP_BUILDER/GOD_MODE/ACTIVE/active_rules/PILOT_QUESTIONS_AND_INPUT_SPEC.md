# Pilot Questions and Input Specification

**Status:** Read-only inspection document. Produced without modifying code, tests, generated
apps, deployment files, or AWS configuration. Not committed — pending Sam's explicit approval.

**Authoritative implementation baseline:** commit `a1653ea3e8094257a558c666a47956b56cb0d597`
("Promote real per-user isolation, login, and admin-provisioned accounts to note_taking"). Every
fact below is read from that exact committed state (`git show a1653ea:...`), not from the working
tree.

**Uncommitted pending changes exist on top of this baseline** (`build.py`,
`verification/app_defs.py`, `verification/gen_common.py`,
`verification/note_taking_pilot_security_tests.py`) and are addressed in one place only — §7 below
— clearly labeled as **proposed and unapproved**. Nowhere else in this document does a fact
description rely on them. In particular: **Bootstrap Admin is described below exactly as it
behaves in the committed baseline — fully open, with no setup-token protection — because that is
the real, current, deployable state.** The reviewed token-gating fix, the Login-failure
browser-journey retarget, and their new tests are real work product but are not active in the
baseline and are not treated as implemented anywhere in this document outside §7.

**Relationship to the prior version of this document:** this replaces the version committed at
`4feb2dd`, which was written before note_taking had any login, isolation, or admin-provisioning
capability. §8 records exactly what changed and why line-by-line reconciliation was necessary.

---

## 1. Exact pilot purpose

A private, invite-only pilot of **note_taking** ("Real Notes" branding) — a minimal, personal
note-taking tool (create, view, delete short text notes) — for Sam and a small group of invited
testers, to validate the application-level security model (real per-tester isolation, real login)
before any public or commercial use. Confirmed from the deployment direction already on record and
`build_note_taking()`'s own capability set; no additional purpose is inferred or invented.

---

## 2. Exact tester journey (as the committed baseline actually behaves)

This is the literal, current sequence — not an idealized one. Two real gaps in this sequence are
called out inline because they affect whether the journey is actually usable as shipped.

1. **Sam bootstraps his own admin account.** Sam opens the pilot URL, finds the "Admin setup
   (first run only)" section on the homepage, and submits an email and password through the
   rendered form (`#bootstrap-email`, `#bootstrap-password`, `#bootstrap-btn`). This calls
   `POST /api/note_taking/auth/bootstrap-admin` with no authentication of any kind — it succeeds
   because no admin account exists yet, not because of who is asking.
   **Real, current gap**: in the committed baseline, this endpoint has **no protection beyond
   that state check** — any remote caller who reaches it first, before Sam does, becomes the
   permanent admin instead of Sam. See §7.
2. **Sam creates each tester's account.** The only account-creation path is the admin-gated
   `POST /api/note_taking/auth/register`, which requires Sam's own session token and, in the same
   call, the tester's email **and a password Sam himself sets**.
   **Real, current gap**: **no UI exists for this at all.** The generated frontend has no "Create
   User" form — Sam must call this endpoint directly (e.g., with `curl`, supplying his own
   `Authorization: Bearer <token>` header), which is a real operational step this document cannot
   soften or assume away.
3. **Sam gives each tester their email and the password he chose**, out of band (the app has no
   invite-link or email-delivery mechanism of any kind).
4. **Tester logs in** via the rendered login form (`#login-email`, `#login-password`,
   `#login-btn`), which calls `POST /api/note_taking/auth/login`.
5. **Tester uses the Notes UI**: creates notes (title required, body optional), sees only their
   own notes (`GET /api/note_taking/notes`, filtered server-side by `owner_id`), deletes their own
   notes (no confirmation dialog — deletion is immediate and irreversible). Editing an existing
   note has no UI (the capability exists at the API only — `POST /api/note_taking/notes/update`).
6. **Tester logs out** via the "Log out" button, which genuinely invalidates the session
   server-side (confirmed: the same token fails immediately afterward).
7. **Session lasts up to 12 hours** (`session_ttl_minutes=720`), after which the tester must log
   in again. There is no "remember me," no shorter/longer per-user option.
8. **If a tester forgets their password, or Sam mistypes one while creating an account, there is
   no recovery path.** No password-reset, password-change, or delete-account capability exists
   anywhere in the code. A duplicate email is permanently rejected (`409`) with no way to remove
   the earlier record through the app. This is a real, current gap, not a hypothetical one — see
   §6.

---

## 3. Every question shown to testers (verbatim, from the rendered page)

| Field | Rendered placeholder/label | Required? | Where it goes |
|---|---|---|---|
| Login email | `"Email"` (`#login-email`) | Required | `POST /api/note_taking/auth/login` |
| Login password | `"Password"` (`#login-password`) | Required | Same call |
| Note title | `"Title"` (`#note-title`) | Required (`400` if blank after trim) | `POST /api/note_taking/notes` |
| Note body | `"Write your note..."` (`#note-body`) | Optional | Same call |
| Delete | button, no text field | n/a — instant, no confirmation | `POST /api/note_taking/notes/delete` |

No question exists for account creation from the tester's side — testers never see a registration
form; their account is created entirely by Sam, out of band, before they ever load the page.

---

## 4. Every tester input — full detail

Unchanged in substance from the prior version of this document for **Note title** and **Note
body** (Q1/Q2 there); repeated here for completeness, now correctly noting that both calls now
require a valid session:

- **Note title**: free-text string, required, server-checks non-empty after `.strip()`; no length
  cap, no character restriction, no HTML-escaping; stored verbatim; **now additionally requires
  authentication (401 if missing/invalid)**, a real change from the prior document's baseline.
- **Note body**: free-text string, optional, defaults to `''`; rendered via `textContent` (safe
  from HTML injection in the browser); same new authentication requirement.
- **Delete**: no tester-typed input; `id` comes from the already-rendered row, never typed;
  **now additionally requires the caller to own the note** (`403` otherwise, confirmed by test).
- **Login email/password**: free-text strings; no email-format validation exists anywhere in the
  code (any non-empty string is accepted as an "email"); password is only ever checked against the
  stored hash, never validated for shape at login time.

---

## 5. Every Sam/owner input

- **Bootstrap admin email + password** (via the open bootstrap form — see the gap in §2.1).
- **Each tester's email + initial password**, entered directly into an API call (`curl` or
  equivalent) against `POST /api/note_taking/auth/register`, authenticated with Sam's own admin
  bearer token obtained from his own login response. No UI exists for this step.
- **No other owner input exists in the application today** — no admin dashboard, no settings
  page, no visible audit log (see §6).

---

## 6. Outputs and success criteria

No success criteria were specified by Sam for this pilot; the following is a **recommendation**,
clearly not a decision made on Sam's behalf:

- Sam can bootstrap exactly one admin account, and that account is genuinely his own (blocked
  entirely until §7's fix is approved and deployed — see the readiness gate in the owner sheet).
- Sam can provision each tester's account (currently only via direct API call — a real, disclosed
  workflow gap, not assumed away).
- Each tester can log in, create/view/delete only their own notes, and log out, with zero
  cross-tester visibility (already tested, 32/32, at the committed baseline).
- No account-recovery incident occurs during the pilot (there is no way to recover from one right
  now — see the "no recovery path" gap in §2.8). **Recommendation**: Sam should treat every tester
  account as effectively permanent for the pilot's duration and take care entering each password.
- Sam can, if needed, inspect `data/audit_log.json` directly on the server for a record of
  register/login/logout events — **no in-app view of this log exists**, confirmed by code (no
  `add_audit_log_capability()` call anywhere in `build_note_taking()`).

---

## 7. Bootstrap Admin — current state vs. proposed, unapproved fix

**Current committed behavior (real, deployable today):** `add_bootstrap_admin_capability()`
(`gen_common.py`, as committed at `a1653ea`) gates account creation *only* on "does an admin
already exist" — there is no check of caller identity, origin, or any secret. Any remote caller
who reaches the endpoint before Sam does becomes the permanent admin instead of him. This was
found and reviewed in this same session and is a **real, currently unresolved vulnerability in the
committed baseline** — not a hypothetical concern.

**Proposed fix (drafted, reviewed, NOT committed, NOT approved, NOT active):** a working-tree-only
change requiring a `BOOTSTRAP_SETUP_TOKEN` environment variable (server-side only, never
hardcoded) and a matching `X-Setup-Token` request header, compared with `hmac.compare_digest`,
failing closed if the environment variable is unset. A companion, also-uncommitted change retargets
the browser-proving journey to a Login-failure path and adds a small, additive `build.py` check
exception for it. A new test file addition (44 checks, up from the committed 32) was run
successfully against this uncommitted code, **but neither the code nor its tests are approved or
part of the baseline this document describes.**

**This document does not treat the proposed fix as available.** Until it (or an equivalent) is
explicitly approved and committed, Bootstrap Admin must be treated as unsafe to expose on any
network Sam does not fully control — see the readiness gate in the owner sheet.

---

## 8. What changed from the prior version of this document (`4feb2dd`)

The prior version was written when note_taking had **zero** login, isolation, or admin
capabilities — every one of its findings described a system that has since materially changed:

| Prior document said | Now (committed baseline `a1653ea`) |
|---|---|
| "Note_taking's own code has no login capability today" | Login/Logout/Me exist and are real (`CAP-0207`–`0209`) |
| "note_taking has no `owner_id` field or ownership check of any kind" | Real, tested, server-resolved `owner_id` isolation on all four note capabilities |
| "The only implemented registration path is open self-registration" | Registration is now admin-gated (`register_required_role="admin"`); no public self-registration exists |
| Session timeout: 60 minutes (engine default, unapplied) | 720 minutes (12 hours), confirmed applied and tested |
| No mention of a first-admin bootstrap problem | A real, new Bootstrap Admin capability exists — and its own **lack of protection is a newly found, currently unresolved vulnerability** (§7) |
| No mention of a "Create User" UI gap | Now a confirmed, real gap: no such UI exists (§2.2) |
| No mention of password reset/change/delete-account | Now a confirmed, real gap: none of these exist at all (§2.8, §6) |

Everything about the API/frontend surface, the encryption findings (§3 of the prior document —
`secrets/master_key.bin`, no external services), and the "no HTTPS/backup/monitoring" findings in
the owner sheet remains **unchanged and still accurate**, since none of that was touched by the
note_taking work.

---

## 9. Unresolved decisions and explicit approval points

1. **Approve or reject the Bootstrap Admin protection fix** (§7) before any AWS deployment —
   this is the single highest-priority open item.
2. **How should Sam actually create tester accounts** — accept the current curl-only workflow, or
   authorize building a "Create User" UI first?
3. **What is the account-recovery policy**, given no reset/change/delete mechanism exists at all
   (§2.8)?
4. **Is 12-hour session length acceptable**, or should the pilot use a shorter value?
5. All decisions already carried over, unresolved, from `PRODUCT_DEPLOYMENT_DECISIONS.md` and
   `PILOT_OWNER_DECISION_SHEET.md` that this document does not re-litigate: AWS deployment target,
   pilot URL, backup/monitoring approach.

No answer above has been assumed or decided on Sam's behalf.
