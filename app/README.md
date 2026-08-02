# Sam — standalone chat / planner / tasks

Self-contained. No database, no build step, no npm dependencies. Runs on
`127.0.0.1:8787` and is completely separate from airexploit.com and
/commanddesk — it shares no code, no config and no web server with them.

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
- **Plan** — sends a goal to `claude-opus-5` and renders the result as overview, key parts, build order, risks and next action.
- **Tasks** — add, tick and delete. Stored in `data/tasks.json`.

## Tests

```bash
node test.js     # or: npm test
```

38 checks covering authentication, the login lockout, the model routing, the
task round-trip, cross-origin refusal, response headers and path traversal. No
dependencies and no API key needed — the Anthropic call is exercised against a
local stand-in. The same suite runs in CI on every push.

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
| `MODEL_PLAN` | `claude-opus-5` | Planner model |
| `MAX_TOKENS_CHAT` | `1024` | Per-reply ceiling |
| `MAX_TOKENS_PLAN` | `2048` | Per-plan ceiling |
| `DAILY_CALL_CAP` | `200` | Calls per session per day |
| `COOKIE_SECURE` | off | Set to `1` when served over HTTPS |
| `ANTHROPIC_BASE_URL` | — | Testing only; points the client at a local stub |
