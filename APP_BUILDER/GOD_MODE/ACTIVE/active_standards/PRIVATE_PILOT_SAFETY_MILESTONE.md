# Private Pilot Safety Milestone — Implementation Plan

**Status:** Planning document only. Produced by read-only inspection of the repository. Nothing
in this document has been implemented. No code, test, generated app, or canonical specification
was modified to produce it. No AWS region, account, instance ID, credential, or deployment URL is
guessed anywhere below — every such item is listed as a decision required from Sam.

**Basis:** This plan is built directly on, and does not re-litigate, the three accepted planning
documents: `PILOT_QUESTIONS_AND_INPUT_SPEC.md` (4feb2dd), `PILOT_OWNER_SETUP_SHEET.md` (501174a),
and `API_KEY_AND_INPUT_REQUIREMENTS.md` (94a15bf). It also relies on the prior evidence trail in
`NEXT_PHASE_READINESS.md` and `PRODUCT_DEPLOYMENT_DECISIONS.md`. Where those documents already
established a fact, this plan cites it rather than re-deriving it; where new inspection was
needed to make an item actionable (exact line numbers, the exact proven isolation pattern), that
inspection was done fresh for this document and is cited directly.

**Confirmed, unchanged from prior documents**: the repository shows no external
provider/API-key dependency for note_taking (`API_KEY_AND_INPUT_REQUIREMENTS.md` §1). This plan
does not collect or configure any API key, and assumes none is needed for the eight items below.

---

## 1. Tester/user data isolation for note_taking

**Exact current code location**: `verification/app_defs.py:297-338`, `build_note_taking()`,
capabilities CAP-0201 (List Notes, line 300), CAP-0202 (Create Note, line 304), CAP-0203 (Update
Note, line 317), CAP-0204 (Delete Note, line 331).

**Current deficiency**: None of the four handler bodies reference any session or user context —
each is a plain `def handle(request):` with no `ctx` parameter. Notes carry no `owner_id` field.
Every note is visible to, and mutable by, anyone who can reach the app at all (confirmed by code;
also the general library-wide fact recorded in `COMPATIBILITY_AUDIT.md:47`, "every app is
single-tenant and unauthenticated by construction").

**Smallest safe implementation**: Reuse the exact, already-proven pattern from
`identity_and_access_demo` (`verification/coverage_expansion/apps/identity_and_access_demo.py:73-89`,
security-tested in `security_tests.py`), not a new design:
- Add `ctx` to CAP-0202's handler; store `owner_id: ctx['user']` — resolved server-side from a
  real, validated session, never from a client-supplied field (`app_defs.py:74-81` pattern in the
  demo app).
- Change CAP-0201 (List Notes) to filter by `n['owner_id'] == ctx['user']` before returning, the
  same pattern as the demo's "List My Tasks" (`identity_and_access_demo.py:83-89`).
- Add an ownership check to CAP-0203 (Update) and CAP-0204 (Delete): reject with `403` if
  `n['owner_id'] != ctx['user']`, before performing the mutation.
- Use `add_capability(..., context_fields_override=("authenticated", "user"))` for List/Create,
  matching the demo's exact declaration style — this is a contract-level declaration, not new
  contract design (`CANONICAL_SPEC.md` Part C already governs `context_fields`).

**Security implications**: This is the single highest-priority item — without it, "tester
privacy" does not exist even if login (item 2) is added, since an authenticated tester could
still list/edit/delete any other tester's notes by id. This item and item 2 must ship together;
login without isolation only adds a login screen in front of a still-shared note pool.

**Migration implications**: Existing entries in `data/note_taking/notes.json` (if any exist from
prior testing/demo runs) have no `owner_id` field. A migration step must either (a) delete/reset
the pilot's `notes.json` before go-live (acceptable per `PILOT_OWNER_SETUP_SHEET.md` §2's
retention recommendation, since no real tester data exists yet), or (b) backfill a placeholder
`owner_id` for any pre-pilot rows. **Recommendation**: reset the data file at pilot start rather
than backfill, since no real tester data predates this change.

**Required tests**: A cross-user isolation test in the same style as
`security_tests.py:118-128` ("bob sees only his own task") — create note as tester A, create note
as tester B, confirm List Notes for each returns only their own; confirm tester B's Update/Delete
attempt against tester A's note id returns `403`, not `200` or `404`. This is also required
verbatim by item 8 below — the two items share one test, not two separate ones.

**Acceptance criteria**: (a) List Notes returns zero cross-tester leakage under a live two-account
test; (b) Update/Delete against another tester's note id returns `403`; (c) the existing four
capability IDs (CAP-0201–0204) and their existing output field names are unchanged (only
`owner_id` is added, and only a ctx-aware wrapper is added) — no breaking change to
`verify_build.py`'s proving table, consistent with `PRODUCT_DEPLOYMENT_DECISIONS.md` §7's own
constraint on this exact change.

**Must be decided by Sam**: none — this item has a fully evidenced, zero-new-design
implementation path. (Sam's only related open decision, from `PILOT_QUESTIONS_AND_INPUT_SPEC.md`
§2 item 10, is whether isolation is required before the pilot starts at all — this plan assumes
yes, since it is item 1 in Sam's own stated priority order.)

---

## 2. Basic login and session handling

**Exact current code location**: The engine exists at `verification/gen_common.py:1237`
(`add_auth_capabilities()`), with session primitives at `gen_common.py:333` (`create_session`,
default `ttl_minutes=60`), `gen_common.py:392` (`validate_session`), `gen_common.py:428`
(`invalidate_session`), and identity resolution at `gen_common.py:683` (`_make_ctx`, real
`Authorization: Bearer <token>` header parsing). **None of this is called anywhere in
`build_note_taking()`** — confirmed by code: zero references to `add_auth_capabilities` in
`app_defs.py`.

**Current deficiency**: note_taking has no register/login/logout/who-am-i capability of any kind.
Sam's deployment direction requires login before the pilot launches.

**Smallest safe implementation**: One call to the existing, tested engine —
`b.add_auth_capabilities("0205", "0206", "0207", "0208", data_filename="users.json")` — added to
`build_note_taking()`, immediately followed by wiring the four new capabilities' output/behavior
into item 1's `ctx['user']` usage. No new engine, no new primitive, no new route pattern: this is
literally the same one-line call already proven in `identity_and_access_demo.py:55-56`. Per
`CANONICAL_SPEC.md` C.6's own constraint (an authenticated capability cannot itself be the journey
target), Register should not be bound to the primary browser-journey slot; the existing Create
Note journey (`app_defs.py:376-381`) is unaffected and should remain the journey target.

**Security implications**: Real, already-tested security properties transfer as-is: PBKDF2-HMAC-
SHA256 salted password hashing (never plaintext, never returned in Register's response), NIST SP
800-63B 8-character minimum plus common-password blocklist screening (`is_common_password()`,
`gen_common.py:314`, the fix already recorded in `IDENTITY_AND_LOGIN_TYPES_SPEC.md`), constant-
time password verification (`hmac.compare_digest`, `gen_common.py:328`), a real 256-bit
unguessable session token, real server-enforced expiry, and genuine server-side logout
invalidation. One real, code-confirmed gap ships with this engine as-is and must be recorded, not
hidden: **no email-format validation exists** (`gen_common.py:1315`, any non-empty string is
accepted) — low severity for a small invited pilot, but should be disclosed to Sam, not silently
carried forward.

**Migration implications**: None — this is new capability addition, not a change to an existing
data shape. `users.json` is a new file; `RESERVED_SHARED_LIB_FILENAMES`
(`gen_common.py:139`) already prevents it from colliding with CAP-0000's own state files.

**Required tests**: Reuse the exact assertions already proven in `security_tests.py` for this
engine (register success, duplicate-email rejection, short/common-password rejection, login
success/failure, `me` requiring a valid session, logout genuinely invalidating the token, garbage
token rejected with `401`) — re-run against note_taking's own build, not re-invented.

**Acceptance criteria**: Register/Login/Logout/Me all pass the same security-test assertions
already proven elsewhere, run live against the note_taking build specifically (not assumed to
transfer from a different app without re-running).

**Must be decided by Sam**: (a) is local-credentials-only (no password reset, no email
verification) acceptable for pilot launch — already flagged as open in
`PILOT_QUESTIONS_AND_INPUT_SPEC.md` §2 items 6 and the "no-email-verification decision" row of
`PILOT_OWNER_SETUP_SHEET.md` §1; (b) session timeout — accept the engine's 60-minute default or
change it (a one-parameter change, not new design).

---

## 3. General pilot access for Sam and a small tester group

**Exact current code location**: `add_auth_capabilities()`'s `default_role` parameter
(`gen_common.py:1238`) and `add_capability(..., required_role=...)`
(`gen_common.py:882-891`) are the only access-control primitives that exist. No account-
provisioning capability (an admin creating another user's account) exists anywhere — confirmed by
code: `identity_and_access_demo`'s own "Register Admin" is explicitly documented as "a demo
convenience, not a production pattern" (`identity_and_access_demo.py:24-27`), since it is a
public, unauthenticated self-registration endpoint, not one user provisioning another.

**Current deficiency**: There is no way today to provision "Sam plus a small named group of
invited testers" as a closed set — the only implemented registration path is open self-
registration (anyone who can reach `/api/note_taking/auth/register` can create an account).

**Smallest safe implementation** (choose one, both are small; the choice is Sam's per §5 of
`PILOT_QUESTIONS_AND_INPUT_SPEC.md`):
- **(a) Self-registration behind a private, unlisted URL** — zero new code; relies entirely on
  the pilot URL not being advertised. Real but weak: anyone who obtains the URL can register.
- **(b) Admin-provisioned accounts** — a new, small, role-gated "Create User" capability
  following the exact `required_role="admin"` pattern already proven for "Delete Any Task"
  (`identity_and_access_demo.py:96-101`): an authenticated admin posts an email; the capability
  generates a random temporary password (or an invite-token flow, a larger variant), hashes it
  with `hash_password()`, and creates the row directly — the tester never self-registers.
  `PRODUCT_DEPLOYMENT_DECISIONS.md` §4 already scores this "small new work," not large.

**Security implications**: Option (a) has a real, disclosed weakness (URL secrecy is not access
control); option (b) is stronger but is new capability code that must itself be tested before the
pilot, not assumed correct by analogy to "Delete Any Task."

**Migration implications**: None — new capability, no existing data shape changes.

**Required tests**: For (b): a non-admin calling "Create User" must receive `403` (the same
assertion style already proven for "Delete Any Task" in `security_tests.py`); an admin calling it
must produce a working, loginable account.

**Acceptance criteria**: Sam and every named tester can log in; no unauthenticated or unlisted
party can create an account (if (b) is chosen) or the private-URL risk is explicitly accepted in
writing by Sam (if (a) is chosen).

**Must be decided by Sam**: (a) vs. (b) — this is the same open question already recorded in
`PILOT_QUESTIONS_AND_INPUT_SPEC.md` §2 item 2 and `PILOT_OWNER_SETUP_SHEET.md` §5; the exact
tester list (names/emails) itself, which cannot be invented here.

---

## 4. Safe client-facing error responses with server-side diagnostic logging

**Exact current code location**: `verification/gen_common.py:711-737` (`_error_body()` and
`dispatch()`). The specific line of concern is inside `dispatch()`'s exception handler:
`return jsonify(_error_body(500, f"handler raised {{type(e).__name__}}: {{e}}")), 500` — this
returns the raw Python exception message to the HTTP client. No `import logging` exists anywhere
in `gen_common.py` (confirmed by direct search) — there is no server-side log to move this
information into.

**Current deficiency**: Any unhandled exception's message text is sent directly to whoever made
the request, and nothing is recorded server-side for an operator to review after the fact. For
today's four (soon six-to-eight, with items 1–3) note_taking capabilities this is low severity —
none of their bodies handle a secret — but it is a real information-disclosure pattern that
becomes dangerous the moment any future capability touches something sensitive, and it leaves
operators blind: an error a tester hits leaves no trace Sam could look up afterward.

**Smallest safe implementation**: In `dispatch()`'s `except Exception as e:` branch: (a) call
`logging.exception(...)` (or an equivalent minimal server-side write) with the full exception
detail, request path, and method, before building the client response; (b) change the client-
facing body to a generic, fixed message (e.g. `"internal error"`) with no exception text, for
`500` responses only — `400`/`401`/`403`/`404` bodies (which already return caller-authored,
non-sensitive messages like `"title is required"`) are unaffected and should not change. This is
a small, localized change to one function, not a new logging framework.

**Security implications**: Closes a real disclosure vector before item 2's login/session code (or
any future capability) could turn an exception message into something sensitive (e.g., a stack
frame revealing a file path, or a caught exception that happens to include partial input). Also
directly enables item 7 (monitoring) and any future incident review — there is currently nothing
to look at after an error occurs.

**Migration implications**: None — no data shape changes. Adds a log destination (a file or
stdout capture) that must be decided alongside deployment (item 5): where does "server-side" log
output actually go once this runs on AWS, not on a developer's own terminal?

**Required tests**: Trigger a genuine unhandled exception (e.g., malformed input that reaches an
unguarded code path) and confirm (a) the HTTP response body no longer contains the exception's
`str(e)` text, and (b) the server-side log captures the same detail that used to be sent to the
client. Re-run the existing full verification suite afterward to confirm no existing test asserts
on the old, now-removed exception-text response shape (a real regression risk worth checking
explicitly, not assuming away).

**Acceptance criteria**: No `500` response body anywhere in the library contains raw exception
text; every `500` is recorded server-side with enough detail (exception type, message, path,
method, timestamp) for Sam to diagnose it after the fact.

**Must be decided by Sam**: where server-side logs are retained once deployed (a log file on the
instance, CloudWatch Logs, or another destination) — this is an AWS-configuration decision, not
guessed here per this document's own constraint.

---

## 5. HTTPS and secure deployment on the existing AWS environment

**Exact current code location**: `verification/gen_common.py:750`:
`app.run(host="127.0.0.1", port=args.port)` — Flask's own development server, loopback-only, no
TLS. Confirmed absent elsewhere: no WSGI/ASGI server (`grep -i "gunicorn\|uwsgi\|waitress"` against
`verification/requirements.txt` → zero matches), no reverse proxy, no `ssl_context`, no rate
limiting, no process supervision (`PRODUCT_DEPLOYMENT_DECISIONS.md` §6, re-confirmed this pass).

**Current deficiency**: Nothing in this repository can serve real HTTPS traffic or survive a
crash/restart unattended. This is the largest single gap standing between "code that has these
security properties" and "a pilot testers can actually reach."

**Smallest safe implementation** (scoped to what is knowable without guessing AWS specifics):
1. Front the existing Flask app with a real WSGI server (e.g. `gunicorn`, already absent from
   `requirements.txt` and would need adding — a small, well-understood dependency addition, not
   new application logic).
2. Terminate TLS at a reverse proxy or load balancer in front of it (the exact AWS mechanism —
   an Application Load Balancer with ACM certificate, or a reverse proxy like nginx on the same
   instance — is an AWS-configuration decision this document does not make).
3. Add process supervision (e.g. `systemd`, or the AWS service's own restart policy) so the app
   process survives a crash without manual intervention.
4. Bind the Flask/WSGI process to a private interface reachable only by the reverse proxy/load
   balancer, not directly to the public internet — preserving the loopback-only-by-default
   posture as far into the stack as the AWS topology allows.

**Security implications**: Without TLS, login credentials (item 2) and session tokens travel in
plaintext over the network — this item is a hard prerequisite for item 2 to be safe in a real
deployment, not merely a nice-to-have layered on afterward. A private pilot is not exempt from
this: "private" controls who is invited, not whether their traffic is encrypted in transit.

**Migration implications**: This is infrastructure, not application data — no data migration.
However, the application's own config (host/port binding) changes from `127.0.0.1` to whatever
the chosen topology requires; this must be a deliberate, reviewed change, not a default left over
from the development-only `app.run()` call.

**Required tests**: A live HTTPS request against the deployed pilot URL succeeds and returns a
valid certificate chain; an attempt to reach the application directly (bypassing the reverse
proxy/load balancer, if the network topology allows testing this) is not exposed on the public
internet; `/health` (item 7) responds correctly through the full TLS-terminated path, not just on
loopback.

**Acceptance criteria**: Pilot testers can reach the app only via HTTPS; the process is supervised
and auto-restarts on crash; the application itself is not directly reachable on the public
internet outside the TLS-terminating layer.

**Must be decided by Sam**: exact AWS deployment target (EC2/ECS/Elastic Beanstalk/other), region,
account, instance sizing, domain name (if any) vs. bare cloud-provided hostname, and TLS
certificate source (ACM vs. another CA) — none of this is evidenced anywhere in the repository
(`PRODUCT_DEPLOYMENT_DECISIONS.md` §1) and none of it is guessed here.

---

## 6. Minimum backup and rollback procedure

**Exact current code location**: Data lives at `DATA_DIR = Path(__file__).resolve().parents[2] /
"data"` (`gen_common.py:156`), plain JSON files, one per app/data-filename. No backup mechanism
exists anywhere in the repository (`grep -rli "backup"` → zero real mechanism, only a docstring
noting the key file is deliberately excluded from a hypothetical future backup,
`PRODUCT_DEPLOYMENT_DECISIONS.md` §5).

**Current deficiency**: If `data/note_taking/notes.json` (or `users.json`/`auth_sessions.json`
once item 2 ships) is lost or corrupted, there is no recovery path of any kind. There is also no
rollback plan for a bad deployment, because no deployment mechanism exists yet (item 5).

**Smallest safe implementation**: Given the data is flat JSON files on disk, the minimum safe
procedure is a scheduled file-level copy (e.g. a periodic `cp`/sync of the `data/` directory to a
separate location — an S3 bucket, or an EBS snapshot if the compute target is EC2) plus a
documented manual restore procedure (stop the app, replace the JSON files from the last known-good
copy, restart). For rollback of the application itself: keep the previous deployed build
artifact/AMI/container image available so a bad release can be reverted by redeploying the prior
version, rather than requiring a fresh code fix under pressure. Neither of these requires new
application code — both are operational procedures layered on top of the existing file-based data
model.

**Security implications**: A backup copy of `data/` must be stored with the same access
restrictions as the live data (it contains the same tester notes and, once item 2 ships, password
hashes and session tokens) — a backup is not exempt from the isolation/confidentiality
expectations of the live system.

**Migration implications**: None to existing code; this is a new operational procedure, not a
schema change.

**Required tests**: A real restore drill — take a backup, deliberately corrupt or delete the live
`data/` directory in a non-production copy, restore from the backup, and confirm the app comes
back with the correct data. An untested backup is not a backup.

**Acceptance criteria**: A documented, exercised (not merely written) restore procedure exists; a
previous known-good deployment artifact is retained and its rollback procedure has been performed
at least once before the pilot goes live, not left as a theoretical plan.

**Must be decided by Sam**: where backups are stored (which AWS service, e.g. S3), the retention
window, and how often the backup runs — all AWS-configuration decisions this document does not
guess.

---

## 7. Health checks and basic monitoring

**Exact current code location**: `verification/gen_common.py:638-639`:
```
def health():
    return jsonify({"ok": True}), 200
```
Already real, already present, already exercised by this project's own stress-test suite
(`PRODUCT_DEPLOYMENT_DECISIONS.md` §6 confirms this is the one production-serving item already
in place). No logging/metrics/alerting exists beyond this single endpoint (confirmed absent:
`grep -n "import logging\|prometheus\|sentry\|metrics"` → zero matches).

**Current deficiency**: `/health` exists but nothing currently polls it in a deployed context, and
there is no alerting if it starts failing. There is also no metric of any kind (request counts,
error rates, latency) beyond what item 4's new server-side error log would incidentally provide.

**Smallest safe implementation**: Configure the chosen AWS compute target's own native health-
check mechanism (e.g. an Application Load Balancer target-group health check, or an EC2/ECS
service health check) to poll the existing `/health` endpoint — no application code change is
needed, since the endpoint already exists and already returns the correct shape. For monitoring,
the minimum safe addition is routing item 4's new server-side error log to a place Sam can see it
(e.g. CloudWatch Logs) and a basic alert on a sustained health-check failure or an elevated `500`
rate — both are AWS-configuration additions, not new application code.

**Security implications**: None directly; this item's value is operational visibility, which
indirectly supports every other item (a login or isolation bug is far more likely to be caught
quickly if errors are actually visible to Sam).

**Migration implications**: None.

**Required tests**: Confirm the configured health check genuinely fails when the app process is
stopped (not just that it passes when everything is fine) — a health check that only ever reports
healthy proves nothing.

**Acceptance criteria**: `/health` is polled by the actual deployed infrastructure, and a real,
deliberate app-stop during a test window is reflected in the monitoring within the health check's
configured interval.

**Must be decided by Sam**: which AWS monitoring service to use (CloudWatch or another), and who
receives alerts.

---

## 8. Tests proving that one tester cannot access another tester's notes

**Exact current code location**: No such test exists for note_taking today — it has no isolation
mechanism to test (item 1). The proven test pattern to reuse lives in
`verification/coverage_expansion/security_tests.py:118-128` (`identity_and_access_demo`'s
cross-user isolation assertions).

**Current deficiency**: Zero test coverage of tester-to-tester data isolation for note_taking,
because the underlying capability (item 1) does not exist yet.

**Smallest safe implementation**: A new test module (or an addition to an existing suite) that,
against a live note_taking build with items 1 and 2 implemented:
1. Registers two real accounts (tester A, tester B) via the new auth endpoints.
2. Tester A creates a note; tester B creates a different note.
3. Asserts tester A's List Notes returns only tester A's note (not tester B's).
4. Asserts tester B's List Notes returns only tester B's note.
5. Asserts tester B's attempt to Update or Delete tester A's note id returns `403`, not success.
6. Asserts an unauthenticated request to List/Create/Update/Delete returns `401`, not the old
   unauthenticated-success behavior.

This is the same structure as `security_tests.py:118-128`, applied to note_taking's own routes
and data shape rather than `identity_and_access_demo`'s tasks.

**Security implications**: This test is the actual proof that item 1 works, not merely that it
was written — matching this project's own established standard throughout (e.g. the password-
blocklist and session-role-staleness fixes were each proven this same way, not just implemented).

**Migration implications**: None — this is a new test, not a code change to the product itself.

**Required tests**: This item *is* the required test for item 1; no further sub-tests are needed
beyond what's listed above, plus a full-library regression re-run (existing verification suite +
merged stress test) afterward to confirm items 1–3 introduced no cross-app regression, matching
this project's own established "regression after every change" discipline
(`NEXT_PHASE_READINESS.md`, `CANONICAL_SPEC.md` C.4/C.5 hardening precedent).

**Acceptance criteria**: The test suite above passes live (not merely by code inspection) against
the actual promoted note_taking build, and the existing full verification suite + merged stress
test both remain at their pre-change pass counts (zero regressions), the same standard already
applied to every prior change in this project (B.8, C.4, C.5 in `CANONICAL_SPEC.md`).

**Must be decided by Sam**: none — this item is a direct, evidenced consequence of items 1 and 2
and requires no independent decision.

---

## Priority-order dependency summary

Items 1 and 2 must ship together (isolation without login is meaningless; login without
isolation is a false sense of privacy). Item 8 is the proof that 1 (and by extension 2) actually
works, and cannot be written before 1 and 2 exist. Item 3 depends on Sam's access-method decision
but is independent code from 1/2 once decided. Item 4 is independent and can be done first or in
parallel — it touches only `dispatch()`, not note_taking's capabilities. Item 5 (HTTPS/deployment)
is a hard prerequisite for items 2 and 3 to be *safe* in the real, deployed pilot, even though the
application-level code for 1–4 can be built and tested locally beforehand. Items 6 and 7 are
operational and can be established in parallel with 1–5, but must be exercised (not just
documented) before real tester data exists.

## Open decisions requiring Sam, consolidated

1. Tester access method: self-registration behind a private URL vs. admin-provisioned accounts
   (item 3).
2. Is local-credentials-only (no password reset, no email verification) acceptable for launch
   (item 2)?
3. Session timeout: accept the 60-minute default or change it (item 2)?
4. Where server-side diagnostic logs are retained once deployed (item 4).
5. AWS deployment target, region, account, instance sizing, domain/hostname, and TLS certificate
   source (item 5) — none of this is evidenced anywhere in the repository.
6. Where backups are stored, retention window, and backup frequency (item 6).
7. Which AWS monitoring/alerting service to use and who receives alerts (item 7).

No implementation should begin on items 3, 5, 6, or 7 until the corresponding decision above is
made; items 1, 2, 4, and 8 have no blocking decision and can proceed once authorized.
