# APP-030: websoft9 -- INSTALL_FAILED to SCREEN-VERIFIED (partial, disclosed)

Real source cloned (`github.com/Websoft9/websoft9`, pinned commit
`112d07a4`). A self-hosted PaaS that lets a person browse and one-click
deploy 300+ open-source apps from a web console, with domain/SSL
management, backups, and a built-in Git/CI story.

## The automated pipeline's finding was stale, and Docker wasn't the fix anyway

The recorded reason was "no Dockerfile or compose file - no documented way
to run it". Not accurate for this repo: it has a real
`docker/Dockerfile` and `docker/docker-compose.dev.yml`. It doesn't matter
either way -- this session's own container cannot pull any Docker image at
all (confirmed against Docker Hub and ghcr.io, both 403 Forbidden at the
CDN blob-download stage, same constraint documented elsewhere on this
shelf).

## Why this one is only *partially* native-verified, disclosed plainly

Websoft9's real architecture is a single Docker image that bundles **four**
separate services glued together by supervisord: its own console (React/
Vite) + apphub (Python/FastAPI) backend, plus binaries extracted at build
time from `gitea/gitea`, `portainer/portainer-ce`, and
`jc21/nginx-proxy-manager` images. Its headline feature -- the App Store,
one-click deploying any of 300+ apps -- works by having apphub talk to
`/var/run/docker.sock` to manage *other* Docker containers on the host.

That means Docker isn't just this app's *own* packaging (as it was for
Typebot/gaseous-server) -- it's the actual mechanism the app's core feature
uses at runtime. With no Docker in this sandbox at all, that feature is a
real, disclosed hard gap, not something a native build works around.
Reconstructing Gitea + Portainer + Nginx Proxy Manager from source natively
just to bundle them the same way the Docker image does would be a huge
undertaking for functionality (repo hosting, container management, reverse
proxying) already proven independently elsewhere -- so this verification
scopes itself to what's real and load-bearing here: **websoft9's own
console and apphub**, run exactly as supervisord runs them inside the real
image, minus the three vendored services.

## Real build chain

- **Console**: real `npm install` (React 19 + MUI + Vite 8) in `console/`,
  run via its own real `npx vite` dev server (not a static build -- this
  is the same dev workflow the project's own `docker-compose.dev.yml`
  comment block documents, just without the container).
- **apphub**: real `pip install -r apphub/requirements.txt` (FastAPI,
  `docker`/`aiodocker` client libraries, PyMySQL, psycopg2, etc.) into a
  clean venv -- installs cleanly even though the actual Docker/DB
  connections those libraries would make aren't exercised.
- Two apphub processes started exactly as `docker/supervisord.conf` runs
  them: `python3 -m uvicorn src.main:app --port 8080` and
  `python3 -m uvicorn src.media:app --port 8081` (moved to 9092 here --
  8080/8081 were already in use by other shelf apps in this same sandbox
  session).
- One missing directory found and created by hand: `apphub/src/media.py`
  hardcodes `/websoft9/media` (normally created by the Docker image's own
  `mkdir` layer); `mkdir -p /websoft9/media /websoft9/library/apps` fixed
  it, no code change needed.
- One config change, disclosed: `console/vite.config.ts`'s dev proxy
  normally routes `/api/` and `/media/` through the full nginx gateway
  (which then reaches whichever service); pointed those two prefixes
  directly at the two apphub ports instead of also standing up nginx,
  gitea, portainer, and npm just to proxy through them. The other proxied
  paths (`/w9git/`, `/w9proxy/`, `/w9deployment/`, `/w9gateway/`) are
  untouched and simply unreachable, matching the disclosed scope above.

## What was verified, in a real browser

- Real **first-run administrator setup** form; created a real account
  (`admin` / `admin@example.com`).
- Real **sign-in** with that account, reaching a real **dashboard**.
- The dashboard reads genuine **live host stats** (CPU load, memory,
  disk, hostname, kernel, uptime -- all real values from the actual
  sandbox host) and **honestly reports its own degraded state**
  ("Healthy services 1/5", "Core services need review - 0 degraded, 4
  unavailable") rather than crashing or silently hiding the gap left by
  not running Gitea/Portainer/NPM -- a genuinely well-behaved app under a
  deliberately partial deployment.
- Real **Users** page listing the exact admin account created earlier,
  round-tripped through the app's own real backing store -- the same
  "prove the write path" bar used for Krayin/Mautic/Ghost/gaseous-server
  elsewhere on this shelf. Found and disclosed a real i18n bug here: the
  Email column header shows the literal untranslated key
  `usersPage.fields.email` instead of "Email".
- Real **App Store** page navigation, correctly and honestly reporting
  "App Store data is temporarily unavailable" (a 404 from the
  never-run build-time catalog sync step) rather than crashing.
- Harmless React-dev-mode console noise only otherwise (MUI `Tooltip`
  `title`-prop deprecation warnings) -- cosmetic, not functional.

See `evidence/` for the full walkthrough: the setup form (empty and
filled), the post-signup sign-in screen, the real dashboard with live
stats, the Users page showing the real account, and the App Store's
honest unavailable-state screen.
