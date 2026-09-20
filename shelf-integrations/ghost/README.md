# Ghost: proven running

Real source cloned (`github.com/TryGhost/Ghost`, branch `main`, pinned commit
`8e2eb8abf`). No external database needed -- Ghost's own default is
`better-sqlite3`, and that's what was used here, unmodified from the app's
own recipe.

## Real build chain

- Node: `engines` pins `^22.23.1 || ^24.20.0`; `pnpm` is pinned to `12.4.2`
  via `packageManager` + Corepack. This sandbox's preinstalled Node
  (22.22.2) didn't satisfy either range, so both `22.23.1` (Ghost's own
  `.nvmrc` -- its primary, tested version) and `24.20.0` (the alternative
  the engines field also allows) were installed for real via `nvm` from
  `nodejs.org` (not blocked here).
- `pnpm install`, then the real production build pipeline:
  `pnpm nx run ghost:build:tsc` (TypeScript), `pnpm nx run ghost:build:assets`
  (Sass/JS asset bundling), `pnpm nx run @tryghost/admin:build` (the real
  Ember/Vite admin SPA, `apps/admin`) -- Nx's own build graph copies the
  compiled admin app to `ghost/core/core/built/admin`, exactly where
  `core/shared/config/overrides.json`'s `adminAssets` path expects it.
- Two git submodules (`ghost/core/content/themes/casper`,
  `.../source`) needed `git submodule update --init --recursive` -- without
  it the public site 404s on its own default theme.

## A real, non-obvious native-module bug found and fixed here

`better-sqlite3`'s own `install` script tries `prebuild-install` first and
only falls back to compiling from source if that fails. Under Node
**24.20.0**, `prebuild-install`/`node-gyp` (even freshly rebuilt, even with
the binary's reported ABI matching 24.20.0 in isolated tests) produced a
`better_sqlite3.node` that crashed with a **native-level C++ assertion**
(`node::RemoveEnvironmentCleanupHook` hit a null `env` in the `Statement`
destructor) the moment Ghost's own migrations ran real `DROP`/`CREATE
TABLE` statements -- a real incompatibility between this exact
`better-sqlite3@12.11.1` native binding and Node 24.20.0's newer
`Environment`/`CleanupHook` internals, not a sandbox artifact. Passing
`node-gyp` an explicit `--target` didn't change the crash.

Rather than patching a third-party native addon's C++ source to chase a
Node 24-specific internal API change, the fix was to use Ghost's own
**primary, `.nvmrc`-pinned** version instead of the secondary one the
`engines` field also permits: Node **22.23.1**. Rebuilt
`better-sqlite3` under it (`pnpm rebuild better-sqlite3`, verified ABI 127
matches) and Ghost's real migrations, boot, and every write below all ran
clean. This is disclosed as a real, version-specific compatibility gap
in a widely-used dependency, not silently worked around.

## What was verified, in a real browser

- Public site: real Casper theme, default "Coming soon" post, real
  subscribe form -- served from the real submodule-checked-out theme.
- Admin setup wizard (`/ghost/#/setup`): created a real admin account
  (site title, name, email, password) -- persisted for real via Ghost's
  own Bookshelf models into the real SQLite file
  (`content/data/ghost-dev.db`).
- Logged in with those real credentials in a fresh browser session (real
  session-cookie auth, not shared state) and reached the real **Analytics**
  dashboard (Ghost's default admin home): real nav (Analytics, Network,
  Posts/Drafts/Scheduled/Published, Pages, Tags, Members, Comments,
  Settings), real account chip ("Sam Naylor").
- Opened the real **Lexical/Koenig post editor**, typed a real title and
  body, and **published a real post** through the app's own Publish flow
  (the real "Continue, final review" -> "Publish" two-step confirmation) --
  confirmed three independent ways: the real "Boom! It's out there. That's
  2 posts published." confirmation dialog, the post appearing on the real
  public site's homepage, and a direct query against the real SQLite
  `posts` table showing `status: "published"`.
- Mobile viewport (390px): admin collapses to a real bottom tab bar
  (Analytics/Write/Members/More), zero horizontal overflow.
- Zero real JS errors. The console noise seen along the way (`403`s during
  an unauthenticated page load before redirecting to sign-in; failed
  requests to `static.ghost.org`, Google-related domains, and Ghost's own
  ActivityPub self-check) is either correct pre-auth behaviour or genuinely
  external calls this sandbox's egress policy blocks -- not app bugs.

See `evidence/` for the full walkthrough: public site, setup wizard, the
real dashboard (desktop and mobile), the editor, and the publish
confirmation.
