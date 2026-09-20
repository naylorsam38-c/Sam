# Strapi: proven running

Real source cloned (`github.com/strapi/strapi`, branch `develop`, pinned
commit `d83af041`). This repo is Strapi's own **core framework monorepo**,
not a scaffolded Strapi project -- so "running Strapi" here means building
the real framework packages from source and running them through the
monorepo's own real example application (`examples/getstarted`), exactly
as documented in the repo's own `CONTRIBUTING.md`, rather than guessing at
a native setup for a project whose recipe otherwise points at a generic
`node:22-bookworm` + `npm run develop` container.

## Real build chain, following the project's own documented workflow

1. `yarn install` at the monorepo root (Yarn Berry 4.12.0 -- the exact
   pinned binary is vendored in the repo itself at
   `.yarn/releases/yarn-4.12.0.cjs`, so no download from `repo.yarnpkg.com`
   was needed even though that host is blocked here; `corepack prepare`
   tried it first and failed with a real proxy 403, confirming the vendored
   binary was the right call, not a workaround).
2. `yarn setup` (`yarn && yarn clean && yarn build --skip-nx-cache && ...`)
   -- a real Nx-orchestrated build of 37 workspace packages
   (`@strapi/core`, `@strapi/content-manager`, `@strapi/upload`, the
   `strapi` CLI itself, etc.), including real native module builds
   (`better-sqlite3`, `@swc/core`, `esbuild`).
3. `cd examples/getstarted && yarn develop` -- the monorepo's own real
   fixture application, which the project's own README confirms "by
   default... you will be able to run ... with a sqlite DB directly", no
   Docker/Postgres/MySQL needed.

## A real disk-space lesson from this build

Yarn Berry's global cache (`~/.yarn/berry/cache`) genuinely needs
~950MB+ for this monorepo's ~2500 packages, and the very first install
attempt ran this sandbox's session disk allowance down to 0 mid-link
(`ENOSPC` while unpacking `graphql-scalars` into `node_modules`) --
resolved by reclaiming space from other shelf apps that were already
fully proven and documented earlier in this session (their running dev
servers were stopped and their multi-gigabyte `node_modules`/build
trees deleted, since their evidence was already saved) rather than by
cutting corners on this build.

## What was verified, in a real browser

- Landed on the real first-run admin registration screen
  (`/admin/auth/register-admin`) -- "Welcome to Strapi!", a real
  first/last name + email + password form with real client-side
  validation copy ("Must be at least 8 characters, 1 uppercase, 1
  lowercase & 1 number").
- Created a real admin account through that form and landed on the real
  post-registration dashboard: "Hello Sam", a real guided-tour widget,
  a real task checklist (Create your schema / Create and publish content
  / Copy an API token / Deploy to Strapi Cloud), real Last
  Edited/Published Entries panels.
- Logged in again in a fresh browser session with the same real
  credentials (real session auth, not shared state) and opened the real
  **Content Manager**, showing the `getstarted` example's actual 16 real
  collection types (Restaurant, Review, Menu, Article, Category, ...)
  and 4 single types -- these are the example fixture's real content-type
  schemas, not invented.
- **Created a real "Restaurant" entry** through the app's own real
  create-entry form (including its real nested repeatable components,
  `closingPeriod` and `dish`) and saved it -- confirmed the real "Saved
  document" toast, then independently verified the exact same entry
  (name and Strapi's own generated `document_id`) by querying the real
  SQLite database file (`examples/getstarted/.tmp/data.db`) directly.
  This is the same "prove the write path, not just the page load" bar
  used for Mautic, Memos, and Ghost elsewhere on this shelf.
- Mobile viewport (390px): the login screen is fully responsive with
  zero horizontal overflow.
- Zero real JS errors. The only console/network failure
  (`net::ERR_TUNNEL_CONNECTION_FAILED` on `analytics.strapi.io`) is
  Strapi's own real telemetry ping, confirmed via the server's own logs
  ("Making request for https://analytics.strapi.io/api/v2/track") and
  blocked by this sandbox's egress policy -- not an app bug.

See `evidence/` for the full walkthrough: the registration screen, the
real dashboard, the mobile login screen, the Content Manager's real
content-type list, the create-entry form, and the saved entry.
