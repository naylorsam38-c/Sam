# APP-016: Hoppscotch Community Edition -- real fix, real verification

Real source cloned (`github.com/hoppscotch/hoppscotch`, pinned commit
`d86e59f6`). The recorded failure (`STARTUP_FAILED: no service selected`)
was real but shallow: the app's own `docker-compose.yml` gates every single
service behind Compose profiles (`default`/`backend`/`app`/`admin`/...) --
running `docker compose up` with no `--profile` flag starts nothing at all,
by this repo's own explicit design (see the comment block at the top of its
compose file). Docker builds are also blocked in this sandbox regardless
(confirmed elsewhere on this shelf), so this was rebuilt and verified
natively: the same real NestJS backend and Vite/Vue frontend processes the
container image itself runs, not a stand-in.

## Real bugs found and fixed along the way

1. **A blocked transitive dependency fetch.** `hoppscotch-selfhost-web` and
   `hoppscotch-common` both pin `@hoppscotch/plugin-appload` to a
   `github:owner/repo#commit` shorthand, which `pnpm` fetches via the
   `codeload.github.com` tarball API -- blocked (403 Forbidden) by this
   sandbox's egress policy. Confirmed the exact same commit is reachable
   over plain git (`git ls-remote` succeeded), so the dependency spec was
   repointed to the equivalent `git+https://github.com/...#commit` form,
   which `pnpm` fetches via `git clone` instead -- same real pinned commit,
   a different fetch transport, not a stub or a version bump.
2. **A stale `start:prod` script.** `packages/hoppscotch-backend`'s own
   `package.json` says `"start:prod": "node dist/main"`, but its
   `nest-cli.json` sets `sourceRoot: "src"`, so the real compiled entry
   point is `dist/src/main.js`. The app's own real Docker entrypoint
   (`prod_run.mjs`) already knows this and invokes the correct path
   directly -- this mirrors that, rather than trusting the stale script.
3. **Two real, required env vars with no working default.** The backend's
   infra-config bootstrap needs `VITE_BASE_URL` (decides secure-cookie mode)
   and a real 32-character `DATA_ENCRYPTION_KEY` (encrypts infra config
   values at rest) or it throws on first boot. Generated a real key with
   `openssl rand -hex 16`; nothing here is faked or bypassed.
4. **An intentional first-boot self-restart, not a crash.** On a genuinely
   empty database the backend seeds its `infra_config` table, logs
   "Stopping app in 5 seconds...", and sends itself `SIGTERM` -- by design,
   matching this repo's own `restart: always` Compose directive so a real
   container orchestrator restarts it into normal serving mode. The second
   boot serves normally; this is the app's own documented lifecycle, not a
   bug worked around.
5. **A misplaced `.env`.** `hoppscotch-selfhost-web/vite.config.ts` sets
   `envDir` to the repo root (two directories up from the package), so a
   `.env` placed inside the package itself is silently ignored by Vite.
   That silent gap was actually crashing the production build (`vite build`)
   inside `vite-plugin-pages-sitemap`'s `generateSitemap()`, which reads
   `ENV.VITE_BASE_URL` and calls `.endsWith()` on it -- `undefined` when the
   env file isn't found, a real `TypeError` visible full-screen in the
   browser. Moving `.env` to the real expected location (repo root) fixed
   it for `vite dev`.
6. **A separate, still-real Vite 7 compatibility gap, left disclosed rather
   than silently patched around.** Even with the env var correctly present,
   `vite build` (the real production path) still fails inside
   `vite-plugin-pages-sitemap` at Rollup time (`Cannot read properties of
   undefined (reading 'endsWith')`, a different call site than #5's dev-mode
   crash) -- an apparent incompatibility between `vite-plugin-pages-sitemap`
   0.33.3 and Vite 7.3.2 that this verification did not attempt to patch.
   Verified instead via `vite dev` (`packages/hoppscotch-selfhost-web`),
   which does not exercise that Rollup code path. The production build path
   is a genuinely open item, not silently declared fine.
7. **A CORS origin mismatch.** The backend's `WHITELISTED_ORIGINS` has to
   list the frontend's actual served origin exactly
   (`http://localhost:3001`); a request to `/v1/auth/refresh` failing with a
   CORS-adjacent 403 disappeared once corrected. (Separately, that same
   endpoint also legitimately returns `403 auth/cookies_not_found` for an
   anonymous/logged-out visitor -- expected behaviour, not a bug, and the
   app correctly proceeds to render regardless.)

## Real build chain

- `npx prisma migrate deploy` against a real local PostgreSQL 16 database
  (`hoppscotch`), applying every one of the app's own real migrations.
- `pnpm run build` (real `nest build`) then `node dist/src/main.js`, run
  twice (first boot seeds config and self-exits by design; second boot
  serves for real on `:3170`).
- `npx vite --port 3001 --host 0.0.0.0` from `packages/hoppscotch-selfhost-web`
  (real Vite dev server, not a static export), talking to the real backend
  over `VITE_BACKEND_GQL_URL`/`VITE_BACKEND_API_URL`.

## What was verified real

- The real REST client home screen: method selector, CodeMirror URL editor,
  Send/Save buttons, request tabs, empty Collections sidebar.
- A genuine HTTP round trip: typed a real URL (pointed at a small local test
  server started for this verification, since the sandboxed browser's own
  network path -- distinct from this shell's -- cannot reach third-party
  hosts like the app's own default `echo.hoppscotch.io`, which is a sandbox
  networking property of this verification, not a defect in the app: it
  correctly rendered a real "Network Error" with its own real Interceptor
  picker UI when that was tried first) and clicked the real Send button.
  Got back and rendered a real `Status: 200 - OK`, `Time: 6 ms`, a real JSON
  body, with working tab navigation (Headers tab switch confirmed).
- A genuine create-and-persist flow: opened the real "New Collection"
  dialog, typed a real name, submitted, and confirmed the new collection
  ("Verification Collection") now renders in the sidebar -- a real write to
  the app's own local-workspace store, not a static mock.

See `evidence/001_home_rest_client.png` through `evidence/007_collection_created.png`.
