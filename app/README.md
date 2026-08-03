# Sam — standalone chat / case / tasks

Self-contained. No database, no build step, no npm dependencies. Runs on
`127.0.0.1:8787` and is completely separate from airexploit.com and
/commanddesk — it shares no code, no config and no web server with them.

Requests that need more than an answer go through the complex-request
lifecycle defined in the Command Desk Master Specification v1.3: goal
formation, your approval, planning, your approval, then execution. The state
machine, the checks and the verdicts are code. No model decides a state, an
approval or an ownership transfer.

## Running it on Windows

```powershell
# once, to store the secrets for your user account
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY","sk-ant-...","User")
[Environment]::SetEnvironmentVariable("APP_PASSWORD","pick-a-password","User")

# then, in a NEW PowerShell window
cd path\to\app
.\start.ps1
```

Open <http://127.0.0.1:8787> and enter the password.

## Running it on Linux or macOS

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export APP_PASSWORD=pick-a-password
node server.js
```

## What it does

- **Chat** — a conversation with `claude-sonnet-5`, keeping the last 20 turns as context.
- **Case** — the complex-request lifecycle. Forge proposes a goal and Mind
  attacks it, up to the round limit. Hub checks the package against your
  original request and rejects anything invented. You approve, and only then
  is the goal locked and planning opened. The plan is checked the same way and
  needs your approval before execution begins.
- **Tasks** — add, tick and delete. Stored in `data/tasks.json`.

## The lifecycle

| State | Who owns it | Timeout |
| --- | --- | --- |
| `goal_forming` | Forge and Mind | — |
| `goal_review` | you | — |
| `goal_approved` | Hub | — |
| `plan_forming` | Forge and Mind | — |
| `plan_review` | you | — |
| `plan_approved` | Hub | — |
| `executing` | the named worker | — |
| `handoff_validating` | Hub | 30 s |
| `handoff_awaiting_acceptance` | the receiving worker | 30 s |
| `handoff_returned` | the originating worker | 120 s |
| `handoff_escalated` | Hub | — |

Transitions not listed in the specification's state table do not exist: an
attempt to make one is refused and the refusal is written to the audit log.
A handoff state that reaches its timeout resolves to `handoff_escalated`,
ownership returns to Hub, and the timeout is the logged reason. It is never
retried and never resolves to accepted.

What is enforced in code, with the requirement each check comes from:

| Rule | What the code does |
| --- | --- |
| `INV-011` | `POST /api/plan` is refused — planning cannot start off a bare request |
| `INV-012` | every audit row carries the goal and plan it descends from; a package from another goal is escalated |
| `INV-013` | every state names exactly one owner |
| `GF-001` | the reason the request entered the lifecycle is recorded |
| `GF-002` | a goal package carrying implementation instructions is rejected |
| `GF-005` | the pair stops at the round limit rather than looping |
| `GF-006` | all ten goal-package fields must be present and non-empty |
| `GF-007` | any number, amount, date, address or reference not in your request is rejected as invented |
| `GF-008` | the goal is locked only by your approval, and only once |
| `PLN-001` | planning is refused before the goal is approved |
| `PLN-002` | a plan offering a menu of options is rejected |
| `PLN-003` | all eleven plan fields must be present |
| `PLN-004` | every phase and task must reference the locked goal or an approved success criterion |
| `PLN-005` | a plan that alters the locked goal stops the work and reopens goal formation |
| `PLN-006` | execution opens only on your approval |
| `HOF-002` | all thirteen handoff fields must be present |
| `HOF-009` | a package with no evidence never reaches the receiver |
| `HOF-010` | correctable defects return; anything that would change the goal or plan escalates |
| `HOF-011` | a timeout escalates, is logged as the reason, and is never retried |
| `HOF-012` | a worker that declares its own outcome is ignored and the attempt is logged |
| `HOF-014` | a refusal naming no specific insufficiency is returned to the receiver as a Category B defect |
| fix loop | two attempts, then escalation |

### Routes

| Route | What it does |
| --- | --- |
| `POST /api/case` | opens a case and runs goal formation |
| `GET /api/case` | lists open cases |
| `GET /api/case/:id` | the case, its state and the last twenty audit rows |
| `GET /api/case/:id/audit` | the full audit trail |
| `POST /api/case/:id/goal/approve` | locks the goal |
| `POST /api/case/:id/goal/reject` | returns it to goal formation |
| `POST /api/case/:id/plan` | opens planning |
| `POST /api/case/:id/plan/approve` | opens execution |
| `POST /api/case/:id/plan/reject` | returns it to planning |
| `POST /api/case/:id/handoff` | submits a handoff package to Hub |
| `POST /api/case/:id/handoff/receive` | the receiving worker's report |
| `POST /api/case/:id/handoff/resubmit` | a correction from the originating worker |

## Tests

```bash
npm test         # both suites
node test-lifecycle.js   # the engine, 84 checks
node test.js             # end to end, 81 checks
```

165 checks. `test-lifecycle.js` exercises the state machine directly with time
injected, so the timeout rules are tested rather than waited for. `test.js`
spawns a real server and a local stand-in for the Anthropic API and drives the
whole path. No dependencies and no API key needed. Both run in CI on every
push.

## Security

- A password is required. Login sets an HMAC-signed, `HttpOnly`, `SameSite=Lax` cookie.
- Every `/api/*` route rejects unauthenticated requests with 401 **before** any Anthropic call, so no unauthenticated request can spend against the key.
- Failed logins are counted per client address and locked out (default: 8 failures, 15 minutes). Without this the password could be brute-forced at full speed.
- Passwords under 8 characters are refused at startup rather than warned about.
- `APP_PASSWORD_HASH` accepts a SHA-256 hash so the plaintext password need never sit in the environment or a launcher script:
  ```powershell
  # generate the hash, then set APP_PASSWORD_HASH instead of APP_PASSWORD
  node -e "console.log(require('crypto').createHash('sha256').update('your-password').digest('hex'))"
  ```
- State-changing requests carrying a foreign `Origin` are refused with 403, behind the cookie check rather than in place of it.
- Responses carry a strict CSP, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` and `nosniff`. `frame-ancestors 'none'` is what stops the app being framed and clicked through.
- Static file serving is confined to `public/`; traversal attempts cannot reach the source.
- Per-session daily call cap (`DAILY_CALL_CAP`, default 200) and `max_tokens` ceilings on both models.
- Binds `127.0.0.1` by default, so it is not reachable from other machines.
- The API key and password are read from the environment. Neither is in source, and neither is logged.

## Before exposing it beyond this machine

1. Set `COOKIE_SECURE=1` so the session cookie is only sent over HTTPS.
2. Set `SESSION_SECRET` to a fixed random value, otherwise every restart logs everyone out.
3. Use a real password, not a short one — this is the only thing standing between the internet and your API key.

## Adding it to an iPhone home screen

Requires HTTPS; iOS will not install a home-screen app from plain HTTP. The
manifest, `apple-mobile-web-app-capable` meta tag and 180×180 touch icon are
already in place, so once it is served over HTTPS, Safari → Share → Add to
Home Screen gives a full-screen app with no address bar.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | — | Required for chat and the planner |
| `APP_PASSWORD` | — | The login password; minimum 8 characters |
| `APP_PASSWORD_HASH` | — | SHA-256 hex of the password, used instead of `APP_PASSWORD` |
| `LOGIN_MAX_FAILURES` | `8` | Failed logins before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `15` | How long a lockout lasts |
| `SESSION_SECRET` | random per boot | Set it to keep sessions across restarts |
| `HOST` / `PORT` | `127.0.0.1` / `8787` | Bind address |
| `MODEL_CHAT` | `claude-sonnet-5` | Chat model |
| `GOAL_ROUND_LIMIT` | `3` | Forge/Mind rounds before the pair stops (GF-005) |
| `MAX_TOKENS_CHAT` | `1024` | Per-reply ceiling |
| `MAX_TOKENS_PLAN` | `2048` | Per-round ceiling for goal formation and planning |
| `DAILY_CALL_CAP` | `200` | Calls per session per day |
| `COOKIE_SECURE` | off | Set to `1` when served over HTTPS |
| `ANTHROPIC_BASE_URL` | — | Testing only; points the client at a local stub |

## Where the model roster is fixed

Forge and Mind both run `claude-sonnet-5`, set in `workers.js`. Document 02 of
the specification fixes the roster, so the ids are not read from the
environment: a model swap is a specification change, not a runtime setting.

## What this app does not do

The specification describes a system larger than this app. Not implemented
here, and not pretended otherwise:

- The permission layer and the exactly-once send guard. Nothing in this app
  performs an outward action, so there is nothing yet for a gate to hold.
- The wider worker roster — builder, tester, research, clerk, checker, angel,
  observer, watcher. The handoff machinery is real and tested, but the workers
  it routes between are supplied by the caller rather than run here.
- The `build_test` isolation group.
- `executing` is the one state whose permitted exits the specification does
  not state. It is implemented as `handoff_validating` or `failed`, marked
  `inferred: true` in `lifecycle.js`, and raised as a specification gap rather
  than presented as specified.
