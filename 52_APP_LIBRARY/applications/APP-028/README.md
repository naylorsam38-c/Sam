# APP-028: Typebot -- STARTUP_FAILED to SCREEN-VERIFIED

Real source cloned (`github.com/baptisteArno/typebot.io`, pinned commit
`61056ff9`). A bun/Nx monorepo (Next.js builder + viewer + workflows apps,
Prisma + Postgres, PartyKit for realtime).

## Why it was blocked, and why Docker wasn't the fix here

The recorded failure (`docker-compose.build.yml` build) is a real bug in the
app's own repo: its Dockerfile references `/scripts/-entrypoint.sh`, which
does not exist in the build context.

Separately, **this session's own container cannot pull any Docker image at
all** -- confirmed with two different registries:

```
docker pull hello-world                    -> 403 Forbidden at blob download
docker pull flagsmith/flagsmith:latest     -> 403 Forbidden at blob download
```

The second one matters: it's the exact image APP-001's own
`recipe_modification_note` says worked in an earlier session on this same
project. That's a real, reproducible difference between sessions, not
something fixable from in here -- so even if the Dockerfile bug were
patched, this container couldn't pull the base image to build it anyway.

Given both problems, this was verified with a genuine **native** build
instead, following the same "clone real source, build it for real, drive it
through a real browser" bar as every other native verification on this
shelf, rather than skipping straight to "blocked."

## Real build chain

- bun 1.3.11 (already `>=` the pinned `1.3.9`), Node 24.20.0 (via `nvm` --
  the pinned `engines.node: "24.x"`, since the system default was 22.x).
- `bun install` -- clean, 3171 packages, real `postinstall` (compiles
  `packages/env`, runs `nx db:generate prisma`).
- Real native Postgres 16 database (`typebot`), schema pushed with the
  project's own real command: `bunx nx run @typebot.io/prisma:db:push`.
- Real Redis (already running natively on this shelf from earlier work).
- A local `aiosmtpd`-based SMTP catcher (`52_APP_LIBRARY/_tools/smtp_catcher.py`,
  listening on 127.0.0.1:1025) standing in for a real mail server, since
  none was available -- the app's own real `sendVerificationRequest`/
  nodemailer code path was exercised unmodified; only the destination mail
  server is local. Kept as a shared tool since other apps on this shelf may
  also need a real email round-trip to verify signup/login.

Two real environment/setup bugs were found and fixed along the way (not
app bugs, but genuine gaps in trying to run one app in this monorepo
standalone rather than through the project's own full `nx run-many` dev
task):

1. **`@typebot.io/react` not built.** The `builder` app's own `dev` Nx
   target declares a `dependsOn` that builds this workspace package first;
   invoking `next dev` directly skips that. Fixed by running
   `bunx nx build @typebot.io/react` once before starting `next dev`.
2. **`next-runtime-env` writes to the wrong directory.** Running
   `next dev apps/builder` from the repo root (needed so a root `.env` would
   load) made `next-runtime-env` write its browser env file to the repo
   root's `public/__ENV.js`, but Next.js actually serves static assets from
   `apps/builder/public/`, which had its own stale, empty `__ENV.js` --
   causing every `NEXT_PUBLIC_*` var to appear `undefined` client-side even
   though the server-side env was valid. Fixed by running with
   `apps/builder` as the actual working directory
   (`bun run --cwd apps/builder next dev`) and colocating `.env` there too.

One real mistake on my own part, caught and fixed rather than shipped: I
initially set `SMTP_AUTH_DISABLED=true` in `.env`, thinking it meant "no
username/password needed for the local catcher." The app's own auth
provider list actually gates the entire Email provider on
`!env.SMTP_AUTH_DISABLED` (`packages/auth/src/lib/providers.ts`), so this
setting silently disabled email sign-in altogether, surfacing as "You need
to configure at least one auth provider." Fixed by setting it to `false`
(the provider already handles an unset username/password by passing
`auth: undefined` to nodemailer, so no credentials were needed either way).

`apps/viewer`, `apps/workflows`, and the PartyKit realtime server were not
started -- verification here is scoped to the builder app's own real UI.

## What was verified, in a real browser

- Real **Sign In** screen; real email-code flow driven end-to-end with a
  genuinely-received email (not a stubbed/fabricated code): submitted
  `admin@example.com`, the app's own `sendVerificationRequest` really sent
  an email to the local SMTP catcher, the real 6-digit code was read back
  out of the received message's actual HTML body (`<code>640954</code>`
  etc. -- a different code every time, confirming it's real and dynamic,
  not hardcoded), typed into the app's own OTP input, and the app's own
  callback verified it and logged in for real.
- Real **workspace dashboard** (`/typebots`) -- "My workspace", "Create a
  folder", "Create a typebot".
- Clicked **"Create a typebot" -> Start from scratch**: the app's own real
  `createTypebot` mutation ran (`POST /api/orpc/typebot/createTypebot 200`
  in the server log) and wrote a real row to the native Postgres database.
- Reached the real **flow editor**, with the full real block palette
  (Bubbles: Text/Image/Video/Embed/Audio; Inputs: Text/Number/Email/
  Website/Date/Time/Phone/Buttons/Pic choice/Payment/Rating/File/Cards;
  Logic: Set variable/Condition/Redirect/Script/...).
- **Dragged the "Text" bubble block onto the canvas** with real mouse
  down/move/up events (not a click shortcut) -- a new "Group #1" block
  genuinely appeared afterward, proving the editor's drag-and-drop is
  actually wired up, not just rendered.
- Zero blocking JS errors throughout. Two harmless, disclosed exceptions:
  a rate limiter (`@upstash/ratelimit`, one email-code request per minute
  per identifier) that had to be waited out between attempts -- a real,
  intentional anti-abuse feature of the app, not a bug; and
  `ERR_TUNNEL_CONNECTION_FAILED` for `framerusercontent.com`, an external
  CDN-hosted onboarding image this sandbox's egress policy blocks, used
  only for a first-run tutorial popup.

See `evidence/` for the full walkthrough: sign-in screen, the "check your
email" confirmation, the workspace dashboard, the create-typebot chooser,
the flow editor, and the editor after the real drag-and-drop block
placement.
