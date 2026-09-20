# APP-020: MindsDB (mindshub/"cowork") -- real fixes made, then genuinely blocked

Real source cloned (`github.com/mindsdb/mindshub`, pinned commit
`780bbcbb`). Despite the catalog name "MindsDB", this repo is MindsDB Inc's
newer "Cowork"/Anton product: a FastAPI backend (`cowork-server`) plus an
Electron/web frontend (`cowork`), oriented around an AI coding/ops agent.

## The recorded failure was real but shallow -- and revealed a deeper one

The recorded Docker build error (`target web: ... "/frontend/package.json":
not found`) was accurate: `frontend/`, `backend/core_api`,
`backend/core_agent`, and `backend/data-vault` are all git submodules
(`ignore = all` in `.gitmodules`) that were never checked out during
acquisition, so the build context genuinely had no frontend source at all.

Fixed with a real `git submodule update --init --recursive`, which pulls in
four separate, all-public repos: `mindsdb/cowork` (frontend),
`mindsdb/cowork-server` (`backend/core_api`), `mindsdb/anton`
(`backend/core_agent`), and `mindsdb/data-vault` (unused by this
`docker-compose.yml`, not built).

That fix surfaced a second, deeper build bug -- one that would break the
project's own official Docker build too, not just this native attempt:
`backend/core_api/pyproject.toml` pins its `hermes-agent` dependency
(`[tool.uv.sources]`) straight to
`git+https://github.com/NousResearch/hermes-agent.git`. That package's own
`setup.py` deliberately raises rather than build a wheel/sdist:

> `RuntimeError: Building wheels or sdists for hermes-agent is not
> supported. Hermes is distributed via the shell installer, Docker image,
> or Nix ... If you are developing, use an editable install instead.`

Fixed by cloning `hermes-agent` locally and repointing that one
`[tool.uv.sources]` line at the local editable path instead of the git URL
(an environment-local `pyproject.toml` edit -- `source/` is gitignored
project-wide here, so nothing needed reverting). With both fixes,
`uv pip install ./backend/core_agent ./backend/core_api` succeeds cleanly.

A third, smaller drift found and worked around rather than "fixed" (it's
this repo's own checked-in config, at this exact pinned commit, that's
stale): `docker/nginx.conf` proxies `/v1/` to the API, but the actual built
frontend calls `/api/v1/...` and the live `core_api`'s own OpenAPI schema
confirms every real route lives under `/api/v1/`. The native nginx config
used here proxies the correct, currently-real prefix.

## Real build chain

- Native Python 3.12 venv (matching `backend/core_api`'s own
  `requires-python = ">=3.12,<3.14"`), `uv pip install` for both backend
  submodules plus the local `hermes-agent` editable checkout.
- `cowork-server` booted directly: `DATABASE_URI=sqlite:///.../cowork.db
  COWORK_SERVER_HOST=0.0.0.0 COWORK_SERVER_PORT=26866 cowork-server`.
- `npm ci --ignore-scripts && npm run build:web` in `frontend/` (a real,
  documented web-target Vite build, distinct from the Electron desktop
  build) -- built cleanly, no errors.
- Served via a native nginx vhost on :8130 (root pointed at the real build
  output, `/api/` proxied to the real `cowork-server` process on :26866).

## What was verified real, and what wasn't

**Real and verified:**
- `cowork-server`'s own real health endpoint:
  `GET /api/v1/health/` → `{"status":"ok","anton_available":true,
  "mode":"anton","server_version":"0.1.5","anton_version":"2.26.6.15.1",
  "config_ready":false,"config_error":"Configure anthropic_api_key for
  Anthropic.", ...}` -- correctly, honestly reporting that it isn't fully
  configured without a real Anthropic API key (which this verification
  doesn't have), not crashing or faking readiness.
- `GET /api/v1/settings/install-status` →
  `{"antonInstalled":true,"serverDepsReady":true}` -- real, accurate
  install-state reporting.
- The real frontend build serving correctly and immediately, correctly,
  redirecting to its configured login flow (see below) -- proving the SPA
  itself, its routing, and its real auth-guard logic all work.

**Genuinely blocked, not attempted further:** the web frontend's login is
hard-wired (`frontend/src/renderer/lib/keycloak.ts`) to MindsDB's own
hosted Keycloak identity provider -- `https://auth.dev.mindshub.ai/auth`,
realm `mindsdb`, client `anton-desktop` -- with no self-hosted realm export
or no-auth/local mode documented anywhere in this repo (checked `docs/`,
`CLAUDE.md`, `dev.env.example`). `auth.dev.mindshub.ai` is itself blocked
by this sandbox's egress policy (confirmed: 403 Forbidden). Even if it
weren't, proceeding would mean authenticating against the vendor's real,
live production identity service under an assumed identity -- not
something this verification does. Despite the word "self-hosted" in this
product's own description, its web login is not actually self-hostable as
shipped at this commit, without insider knowledge of MindsDB's own realm
configuration this repo doesn't include.

See `evidence/001_home.png` for the actual browser state reached: the real
OAuth authorization URL it redirects to (visible in full, showing the
real client_id/realm/redirect_uri), blocked at the network level.
