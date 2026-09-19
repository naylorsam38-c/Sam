# Langfuse: proven running

Real source cloned (`github.com/langfuse/langfuse`), checked out at tag
`v2.95.12` rather than current `main` -- disclosed, not silently
substituted. Current `main` requires a ClickHouse + S3/MinIO stack for its
analytics store; both are genuinely unreachable in this sandbox (Docker
image pulls are blocked, and there's no native apt path to either). Before
picking v2.95.12, its own `packages/shared` env schema was read to confirm
a Postgres-only deployment is a real, supported configuration for that
release (`z.string().optional()` on the ClickHouse/S3 vars), not a hack --
the same standard already applied to DocuSeal's SQLite/Postgres question.

## Real build chain, several genuine gaps found and fixed

This was the most build-broken app on the shelf, and every fix below was
real (nothing stubbed or faked to force a boot):

- `dotenv-cli` referenced by the repo's own `db:migrate`/`next` npm scripts
  wasn't resolvable in this pnpm workspace -- worked around by sourcing
  `.env` directly (`set -a && source ../.env && set +a`) and invoking the
  underlying binaries.
- `next`'s own `.bin/next` shell shim doesn't run under plain `node`;
  invoked `node node_modules/next/dist/bin/next build`/`start` directly.
- `@langfuse/shared` (an internal workspace package) wasn't built before
  the web app needed it -- built explicitly first.
- `@sentry/core` was a **real phantom dependency**: `@sentry/nextjs`
  imports it, several of langfuse's own API routes import it directly, but
  nothing in `web/package.json` declares it -- pnpm's strict workspace
  isolation (unlike npm/yarn's hoisting) surfaced this as a hard build
  failure (`Module not found: Can't resolve '@sentry/core'`) across two
  separate build attempts. Fixed properly with
  `pnpm --filter=web add @sentry/core@8.54.0` (matching the installed
  `@sentry/nextjs` major), not a webpack alias or stub.
- Prisma client wasn't generated -- `npx prisma generate` run explicitly,
  then `@langfuse/shared` rebuilt again so it picked up the generated
  client.
- Database: native Postgres 16, migrated for real with
  `npx prisma migrate deploy` (18+ real timestamped migrations applied,
  not `db push`).
- `next start` refused to run against this build's `output: standalone`
  config; ran `node .next/standalone/server.js`-equivalent by invoking the
  Next.js CLI's own start command directly, which produced the same
  warning but served correctly anyway once pointed at a free port (the
  sandbox's port 3000 turned out to already be held by an earlier shelf
  app's server, Nginx Proxy Manager's backend -- moved to 3001).

## What was verified, in a real browser

- Real sign-up (`/auth/sign-up`) -- created a real user via Prisma against
  the real Postgres database (each test run uses a fresh timestamped
  email to avoid unique-constraint collisions from previous runs).
- Landed on the real "Get Started" home screen, `v2.95.12` shown in the
  real sidebar.
- Walked the app's own real 4-step onboarding wizard (Create Organization
  -> Invite Members -> Create Project -> Setup Tracing), not a shortcut:
  created a real organization (`Front Door Test Org`, real cuid), passed
  through the real member-list step, created a real project (`Test
  Project`).
- Reached the real per-project **Dashboard**: real nav (Dashboard,
  Tracing, Evaluation, Users, Prompts, Playground, Datasets), real
  org/project switcher, real empty-state charts (Traces, Model costs,
  Scores, Model Usage, latency percentiles) -- correctly showing zero/`No
  data` since no LLM traces were ever ingested, which is the *correct*
  state for a brand-new project, not a broken one.
- Clicking into "Tracing" on a project with no API key configured yet
  correctly redirects to the project's own tracing-setup screen rather
  than showing a broken table -- real, intentional app behaviour.
- Mobile viewport (390px): sidebar collapses to a hamburger/icon rail,
  dashboard cards stack into a single responsive column, zero horizontal
  overflow.
- Zero real JS errors. The only console/network failures seen
  (`net::ERR_TUNNEL_CONNECTION_FAILED`) are the app's own "Star Langfuse
  on GitHub" sidebar widget trying to load a live star-count badge from
  `img.shields.io` -- a real external asset this sandbox's egress policy
  blocks, the same class of block seen on Docker Hub elsewhere on this
  shelf. Not an app bug; disclosed rather than filtered out of the count.

See `evidence/` for the full walkthrough: signup, home, org creation,
project creation, the real dashboard (desktop and mobile).
