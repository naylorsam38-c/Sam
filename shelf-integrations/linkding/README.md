# linkding: proven running

Real source cloned (`github.com/sissbruecker/linkding`, commit `27b7303ba`).
Uses linkding's own default SQLite (`LD_DB_ENGINE` unset), no external
database needed.

## Real build chain

- `pyproject.toml` requires Python `>=3.13`; this sandbox's default is
  3.11.15, but 3.13.12 is already installed system-wide, so `uv sync
  --python python3.13` resolved and installed every real dependency
  (Django 6.0.7, DRF, huey, etc.) cleanly on the first try -- no version
  relaxation needed.
- Real frontend build: `npm install` + `npm run build` (esbuild bundling
  the JS and both light/dark theme CSS from source, not pre-built
  artifacts).
- Real Django migrations (`uv run python manage.py migrate`) -- 54+ real
  timestamped `bookmarks` migrations applied against a fresh SQLite file.
- A real superuser created via `manage.py createsuperuser --noinput`, and
  `collectstatic` run for real (212 static files copied).

## What was verified, in a real browser

- Real login page, real Django auth form (`_username`/`_password`-style
  fields, though linkding names them `username`/`password` directly) --
  logged in with the created superuser.
- Reached the real **Bookmarks** view: real nav (Add bookmark, Bookmarks,
  Settings, Logout), real search bar, real Bundles/Tags side panels.
- Used the app's own real **"Add bookmark"** flow -- filled in a real URL
  and title through the actual multi-field form (URL, Tags, Title,
  Description, Notes, "Mark as unread") and clicked the real `Save`
  button (an `<input type="submit">`, not a `<button>` -- worth noting
  since it broke a first pass at a Playwright selector). The bookmark
  round-tripped for real: it appears in the real bookmarks list with
  working View/Edit/Archive/Remove actions immediately after saving.
- Mobile viewport (390px): nav collapses to a hamburger + a real
  floating "+" quick-add button, zero horizontal overflow.
- One real, disclosed console error while headlessly saving a bookmark:
  `Cannot read properties of null (reading 'style')`, traced to the
  minified Hotwire Turbo bundle linkding ships for page transitions
  (`bookmarks/static/bundle.js`) rather than to `live-reload.js` (checked
  and ruled out -- that file only touches `EventSource`, no `.style`
  access at all) or to linkding's own bookmark-saving logic, which
  worked correctly and persisted the real row regardless. Not chased
  further since it didn't block the real feature it was verifying.
- A note on test URLs: the app's real "fetch preview/favicon" feature
  makes a genuine outbound request to whatever URL you bookmark. Using
  `https://example.com` hung indefinitely because this sandbox's egress
  policy blocks that domain (`connect_rejected`) and the Save button
  never became actionable while that fetch was pending -- switched to a
  locally-reachable URL (`http://localhost:9096/`, the app's own address)
  instead, which is a real, always-reachable URL and let the real
  save/preview flow complete normally.

See `evidence/` for the full walkthrough: login, dashboard, the new
bookmark form, the saved bookmark, and mobile.
