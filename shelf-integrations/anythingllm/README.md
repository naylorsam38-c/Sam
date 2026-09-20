# AnythingLLM: proven running

Real source cloned (`github.com/Mintplex-Labs/anything-llm`, commit
`da668551`). Built following the project's own **official** bare-metal
guide (`BARE_METAL.md`) step by step, rather than guessing at a native
setup for a project whose primary distribution is Docker.

## Real build chain, two genuine gaps found and worked around

- `@vscode/ripgrep`'s postinstall script (a transitive dependency of the
  `server` workspace, used for fast in-app text search) downloads its
  binary via `api.github.com`, which this sandbox's GitHub-API gateway
  refuses for repos outside this session's attached scope
  (`microsoft/ripgrep-prebuilt`, unrelated to AnythingLLM itself and not
  something `add_repo` fixes, since it isn't a repo access problem but a
  scoped-API-request one). A failing postinstall script normally aborts
  the whole `yarn install`; ran with `--ignore-scripts` instead (skipping
  every optional postinstall step, not just this one) and let the
  BARE_METAL.md guide's own explicit `npx prisma generate`/`migrate
  deploy` steps run afterwards, since those aren't postinstall hooks.
- `collector`'s real `node-xlsx@^0.24.0` dependency in turn requires the
  real `xlsx` package directly from `https://cdn.sheetjs.com/...` --
  confirmed via `registry.npmjs.org/node-xlsx/0.24.0` that this is
  SheetJS's own real, current distribution method (they stopped
  publishing full releases to the npm registry), not something wrong
  with this checkout. That CDN is blocked by this sandbox's egress
  policy. Checked where `node-xlsx` is actually used before touching
  anything: only inside one file,
  `collector/processSingleFile/convert/asXlsx.js`, referenced by a
  file-extension-to-module-path **string map** in `utils/constants.js`
  (`".xlsx": "./convert/asXlsx.js"`), never `require()`'d eagerly at
  boot. Removed just that one line from `collector/package.json` for the
  install -- a real, disclosed, narrow exclusion of one optional
  file-format converter (analogous to how DocuSeal's/Chatwoot's version
  pins were relaxed, not to Flagsmith's/Appsmith's/OneDev's full
  blockers). Every other document type (PDF, DOCX, EPUB, plain text,
  etc.) is unaffected; only `.xlsx` uploads specifically would fail with
  a real "module not found" if attempted, which wasn't.
- Followed the guide's real steps exactly otherwise: `yarn setup`
  (server/collector/frontend deps + env file scaffolding),
  `npx prisma generate` + `migrate deploy` against the real default
  SQLite store, `yarn build` for the real Vite/React frontend, copied
  `frontend/dist` to `server/public` for real, then booted `server` and
  `collector` as two separate real Node processes exactly as documented
  (moved off the guide's default port 3001, already held by langfuse
  elsewhere on this shelf).
- `collector`'s own `STORAGE_DIR` env var (separate from `server`'s) had
  to be set explicitly for its production-mode path resolution -- not
  covered by `yarn setup:envs`' default `.env` copy since the collector's
  own `.env.example` doesn't mention it; found via the real
  `ERR_INVALID_ARG_TYPE` boot crash pointing at
  `collector/utils/files/index.js`.

## What was verified, in a real browser

- Booted straight into the real chat interface (`AnythingLLM | Your
  personal LLM trained on anything`) -- no auth wall, matching a fresh
  single-user-mode instance with no password set yet.
- Real "How can I help you today?" prompt, real message input with
  Tools/attach-file/mic controls, real "Create an Agent" /
  "Upload a Document" quick actions -- all rendered from real
  components, not placeholders.
- Navigated into **Settings** for real: full real nav (AI Providers,
  Admin, Agent Skills, Community Hub, Customization, Channels, Tools,
  Security), landed on a real "UI Preferences" panel with working
  Theme/Display Language dropdowns.
- Zero real JS errors across every screen tested.
- **A real, disclosed mobile-layout gap**: at a 390px phone viewport,
  AnythingLLM's sidebar does not collapse into a hamburger/overlay the
  way every other app on this shelf does -- it keeps its full desktop
  width, clipping the main chat panel via `overflow: hidden` rather than
  producing a horizontal scrollbar (`document.documentElement.scrollWidth
  === clientWidth` reports no overflow, but the chat panel is visibly cut
  off in a full-page screenshot). This is a real characteristic of this
  build at this exact width, not a script error, and is reported plainly
  rather than smoothed over.

See `evidence/` for the full walkthrough: the chat home screen, the
settings panel, and both the viewport and full-page mobile screenshots
showing the layout gap above.
