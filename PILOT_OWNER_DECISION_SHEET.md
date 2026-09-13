# Pilot Owner Decision Sheet — Seven Open Items

**Status:** Decision sheet only. No code, test, generated app, or specification was modified.
Nothing below has been implemented. No password, API key, AWS access key, token, or other secret
is requested or recorded anywhere in this document.

**Basis:** Builds directly on the accepted `PRIVATE_PILOT_SAFETY_MILESTONE.md` (ff9796f) and the
prior accepted planning documents. Every "current repository evidence" line below is a fact
already established in those documents or freshly re-cited from the same code locations — nothing
here was re-derived differently.

**Provisional assumptions** (labeled recommendations only — not decisions Sam has made):
private pilot · invited testers · no email verification · no public registration · HTTPS required
· separate tester identities preferred over a shared login · no external API keys until a real
dependency is identified.

---

## 1. Tester access method

- **Current repository evidence**: No account-provisioning capability exists. The only
  implemented registration path is open, unauthenticated self-registration
  (`add_auth_capabilities()`, `gen_common.py:1237`) — anyone reaching the register endpoint can
  create an account. This is not yet even wired into note_taking. No admin-provisioning
  capability exists anywhere (`identity_and_access_demo`'s "Register Admin" is explicitly
  documented as "a demo convenience, not a production pattern," not a real provisioning
  mechanism).
- **Recommended pilot default**: Admin-provisioned accounts (Sam creates each tester's account).
  Matches the "no public registration" and "separate tester identities" assumptions above; a
  small, well-scoped new capability (`required_role="admin"`-gated "Create User"), following the
  same pattern already proven for "Delete Any Task."
- **Available choices**: (a) admin-provisioned accounts; (b) self-registration behind an unlisted,
  private URL (weaker — URL secrecy is not real access control, and conflicts with the "no public
  registration" assumption).
- **Security/operational consequence**: (a) requires building and testing one new capability
  before launch; (b) needs no new code but means anyone who obtains the URL can register.
- **Blocks implementation**: **Yes** — `PRIVATE_PILOT_SAFETY_MILESTONE.md` item 3 cannot be built
  until this is chosen.

---

## 2. Password-reset policy

- **Current repository evidence**: No "forgot password" flow, and no email-transport integration
  of any kind, exists anywhere in the codebase.
- **Recommended pilot default**: No self-service reset for the pilot; Sam resets a tester's
  account manually on request.
- **Available choices**: (a) no self-service reset (manual only); (b) build self-service reset,
  which requires choosing and integrating a real email provider — a new external dependency this
  project has consistently deferred, and one that conflicts with the "no external API keys until a
  real dependency is identified" assumption above unless Sam decides otherwise.
- **Security/operational consequence**: (a) zero new work, small support burden on Sam for a small
  invited group; (b) real new work, plus a new provider/credential decision this sheet is
  explicitly not requesting values for.
- **Blocks implementation**: **No**, if (a) is accepted.

---

## 3. Session timeout

- **Current repository evidence**: `create_session(user_id, extra=None, ttl_minutes=60, ...)`
  (`gen_common.py:333`) — 60 minutes is the engine's existing, already-tested default.
- **Recommended pilot default**: Keep 60 minutes.
- **Available choices**: 60-minute default, or a different value (a one-parameter change, not new
  design).
- **Security/operational consequence**: Shorter increases tester friction (more re-logins);
  longer increases the window an unattended, logged-in browser stays valid.
- **Blocks implementation**: **No** — has a safe, already-tested default.

---

## 4. Log retention location and duration

- **Current repository evidence**: No logging module exists anywhere in the codebase (`grep -n
  "import logging"` → zero matches). `PRIVATE_PILOT_SAFETY_MILESTONE.md` item 4 recommends adding
  server-side diagnostic logging in `dispatch()` (`gen_common.py:711-737`) to replace the current
  behavior of returning raw exception text to the client — but that change needs somewhere to
  write to.
- **Recommended pilot default**: CloudWatch Logs (AWS-native), retained for the duration of the
  pilot plus a short review buffer (e.g., 30 days) — a recommendation only, since no AWS logging
  configuration exists in this repository today.
- **Available choices**: CloudWatch Logs; a local log file on the instance; another AWS logging
  service. Retention window is a separate, independent choice.
- **Security/operational consequence**: Without a destination, item 4's fix has nowhere to send
  diagnostic detail, leaving Sam blind to errors after they occur; the retention window trades
  off review capability against storage cost.
- **Blocks implementation**: **Yes** — item 4's implementation should not be finalized without
  knowing where the log output is meant to go.

---

## 5. AWS deployment target and current URL

- **Current repository evidence**: Zero AWS evidence anywhere in the repository (confirmed by
  repeated search across `.py`/`.md` files). Every generated app binds to
  `app.run(host="127.0.0.1", port=args.port)` — loopback only. **No pilot URL currently exists.**
- **Recommended pilot default**: None — this item has no safe technical default; it is entirely
  Sam's to specify.
- **Available choices**: EC2, ECS, Elastic Beanstalk, or another AWS compute target; a real domain
  name vs. a bare cloud-provided hostname.
- **Security/operational consequence**: This choice determines the concrete shape of
  `PRIVATE_PILOT_SAFETY_MILESTONE.md` item 5 (HTTPS/reverse-proxy/process-supervision setup) —
  nothing in that item can be finalized without it.
- **Blocks implementation**: **Yes** — hard blocker for item 5, and indirectly for safely
  deploying items 2 and 3 (login/access) at all, since credentials must not travel over plaintext
  HTTP.

---

## 6. Backup storage and retention

- **Current repository evidence**: No backup mechanism exists anywhere in the codebase. Data is
  plain JSON under `DATA_DIR` (`gen_common.py:156`), with no scheduled copy of any kind.
- **Recommended pilot default**: A periodic copy of the `data/` directory to S3, retained for the
  pilot duration plus a short buffer (e.g., 30 days) — a recommendation only, since no AWS backup
  configuration exists in this repository today.
- **Available choices**: S3 file-level copy; EBS snapshot (if EC2 is the compute target, per
  item 5); another AWS mechanism. Retention window is a separate, independent choice.
- **Security/operational consequence**: Without a backup, data loss (corruption, accidental
  deletion, instance failure) is unrecoverable. A backup copy must carry the same access
  restrictions as the live data (it holds the same tester notes and, once login ships, password
  hashes and session tokens).
- **Blocks implementation**: **No** for starting item-1–4 development, but should be resolved
  before real tester data accumulates, per `PRIVATE_PILOT_SAFETY_MILESTONE.md`'s own
  dependency summary.

---

## 7. Monitoring service

- **Current repository evidence**: Only `/health` (`gen_common.py:638-639`) exists, already
  returning `{"ok": true}`. No metrics, alerting, or monitoring integration of any kind exists
  beyond that single endpoint.
- **Recommended pilot default**: AWS-native CloudWatch alarms on the deployment target's own
  health check (once item 5 is chosen) and on elevated error rates — consistent with the "no
  external API keys until a real dependency is identified" assumption, since a third-party
  monitoring service would introduce exactly such a dependency.
- **Available choices**: CloudWatch (AWS-native, no new external credential); a third-party
  monitoring service (introduces a new API-key dependency, which the provisional assumptions
  above recommend against for now).
- **Security/operational consequence**: Without monitoring, an outage or elevated error rate goes
  unnoticed until a tester reports it.
- **Blocks implementation**: **No** for starting item-1–4 development, but should be resolved
  before go-live, in parallel with item 6.

---

## Summary — what blocks implementation right now

| # | Decision | Blocks implementation? |
|---|---|---|
| 1 | Tester access method | Yes |
| 2 | Password-reset policy | No |
| 3 | Session timeout | No |
| 4 | Log retention location and duration | Yes |
| 5 | AWS deployment target and current URL | Yes |
| 6 | Backup storage and retention | No (resolve before go-live) |
| 7 | Monitoring service | No (resolve before go-live) |

Items 1, 4, and 5 are the three genuine blockers. Items 2 and 3 already have safe, accepted-by-
default answers unless Sam overrides them. Items 6 and 7 can be decided in parallel with early
implementation but must be resolved before real tester data exists on the deployed pilot.
