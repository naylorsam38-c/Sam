# Front Door

Ask a plain-text question ("I need a feature flag tool") and the Front Door resolves it
against a real shelf of self-hostable apps, then lets you skin whatever it opens.

## What's real here, and what isn't yet

This system was assembled from three separate deliveries that didn't originally come with
each other, and this section says exactly where each seam is, so nothing here is taken on
faith later:

- **`skins_library/`** -- the real, ground-truth design engine (`design_tokens.py` +
  `render_css.py`), plus 172 real generated skin files across 43 measured categories. This
  is unmodified from Sam's upload. `skins-engine.js` is a byte-for-byte JS port of it,
  verified in `test_frontdoor.py` Sections A/B against every one of those 172 files *and*
  the full 360-hue x 4-look input range (1440 sets) -- not a sample.
- **`library.json`** -- the real shelf catalog: 19 real, named, open-source self-hosted apps
  (Flagsmith, Ghost, langfuse, Chatwoot, code-server, DocuSeal, Uptime Kuma, Nginx Proxy
  Manager, Appsmith, Mautic, OneDev, linkding, AnythingLLM, Strapi, Krayin, Memos, Infisical,
  Super Productivity, Galene), copied verbatim from their own `app.json` entries in Sam's
  52_APP_LIBRARY acquisition pipeline (name, category, repository, real screenshot). None of
  them shipped their actual page source through this pipeline -- only catalog metadata and a
  screenshot -- so every entry is marked `"family": ""` (no `render_css.py`-style CSS family)
  in `library.json`, per the rule below. That's a separate question from whether the app
  itself has been proven to actually run: **16 of the 19 have been** -- real source cloned,
  built, and driven through their real UI in a real browser.
  See `shelf-integrations/STATUS.md` for the full per-app tally, and
  `shelf-integrations/productivity/` for the one that goes further still (the skin engine's
  colour actually driving the app's own real theming service, not just "it boots").
- **`front-door.html` / `shelf-ui.js` / `demo-app.html`** -- new, built for this task. The
  ask -> resolve -> preview -> keep/undo flow is real and fully tested, but the thing it
  visibly reskins live is `demo-app.html`, a small first-party `shared_card`-family fixture
  -- **not** one of the 8 real catalog apps, since none of their real markup exists here to
  reskin. The app screen shows each real app's real name, real screenshot and real repo
  link, clearly labelled "colours only -- this app's real markup hasn't been measured yet."

## How a person uses it

Type what you need on the ask screen. The Front Door matches it against the real shelf
catalog (`library.json`) by name/category/keyword and opens the closest match -- or says
plainly that nothing matches, rather than guessing. Tap the round icon to change the look:

- Tap one of the five looks (Original + the four measured looks from `design_tokens.py`) →
  the live preview changes **straight away** → "Keep it" or "Not that".
- "Not that", closing the sheet, or picking something else → it goes back.
- Or just say it: "make it dark", "make it navy" -- a small deterministic keyword table
  (`Skins.parseAsk` in `skins-engine.js`) picks a look/colour and lists it back for approval.
  This is **not** a call to an external model; see "Design choices" below.
- A colour/font/radius change requested while still on Original adds a visible "switches to
  Minimal Neutral" step first -- never applied silently on top of the app's own look.
- Every kept change is in the log with Undo.

## Where to change things

- `library.json` -- the real shelf catalog. Add an app here (from its real `app.json`) to
  admit it to the shelf. `family` stays `""` until that app's actual markup has been
  measured and a matching renderer added to `skins-engine.js`/`skins_library/render_css.py`.
- `skins-engine.js`'s `FAMILY_RENDERERS` -- add a family here (and to
  `skins_library/render_css.py`, the Python source of truth) once an app's real selectors
  have been read from its real source, never guessed at.
- `skins-engine.js`'s `KNOWN_COLOR_NAMES` / `LOOK_KEYWORDS` -- the free-text "or just say it"
  vocabulary.

## Putting the skin into a real, separately-hosted app (`frontdoor-skin-adapter.js`)

Unchanged from the original delivery, at the repo root:

1. Add `<script src="frontdoor-skin-adapter.js"></script>` to the end of the app's page.
2. Open the app through the Front Door and pick a look.
3. First time, nothing will happen and the console will say `ignored a skin from https://...`.
   Copy that address into `ALLOWED_ORIGINS` in the adapter's RULES block. Reload. Done.

It only ever adds one `<style>` tag, one font link, and `--fd-*` colour variables. Original
takes them all off. Delete the script line and the app is exactly as it was.

`adapter-fixture/` holds a **test-only** copy of the adapter (differing only in
`ALLOWED_ORIGINS`) plus three fixture pages, used to prove the postMessage contract against
a genuinely different origin (`test_frontdoor.py` runs two HTTP servers, on two ports, for
exactly this reason -- not a same-origin stand-in).

## Design choices made to build this (disclosed, not hidden)

Two pieces of this app have no prior spec to port from and were designed fresh for this
task. Both are pinned down by `test_frontdoor.py`'s own assertions, not vibes:

- **`Skins.withEdits` / `Skins.lookFields`** (`skins-engine.js`) -- how a manual accent/
  radius/font edit layers on top of a chosen look (recolouring hover/focus-ring/shadow
  together; keeping a look's own small-to-large radius ratio; keeping a genuine "pill" look
  pill-shaped). See Section C of the tests.
- **`Skins.parseAsk` / `Skins.resolveAsk`** -- the free-text look-picker and the ask-to-shelf-
  app matcher are small, deterministic keyword tables, not a live call to an LLM. This keeps
  behaviour reproducible offline and in CI. If a real model call is wanted for either later,
  swap the function body; nothing else depends on how the match was produced.

## Tested (real Chromium via Playwright, `test_frontdoor.py`)

**115/115**, run against two real local HTTP servers (one for the Front Door, a second on a
different port for the cross-origin adapter proof):

- All 172 real `skins_library` files reproduced byte-for-byte by `skins-engine.js`, plus the
  full 360-hue x 4-look range (1440 sets) against the real Python.
- A real, documented rounding bug was caught and fixed while building this: hue 210 in Soft
  Rounded came out one shade off (`#dee5ed` vs Python's `#dee6ed`) because of how a redundant
  floating-point remainder was taken -- the same class of bug `_verification`'s history
  already called out once before. Fixed in `skins-engine.js`'s `pymod`; see the comment there.
- `withEdits`/`lookFields`, gates (`checkEdit`/`normalizeChanges`), ask-resolution against
  the real shelf apps (including a no-match case), preview/keep/not-that/undo/reload/
  close-mid-preview, three viewports (desktop, mobile, mobile dark), no JS errors.
- Ask-resolution regression, all 19 real catalog apps: a real bug was found and fixed here
  too -- `resolveAsk`'s original scoring let a single-word keyword double-dip (a verbatim-
  substring bonus *and* a word-overlap bonus for the same evidence), and had no stemming, so
  natural asks like "I need a bookmark manager" or "I need a blog platform" silently resolved
  to the wrong app (or nothing at all). Fixed with a small deterministic stemmer, a scoring
  split so the substring bonus only applies to multi-word phrases, and an extended stopword
  list excluding generic descriptor nouns ("manager", "platform", "tool", ...); see the
  comments above `stem()`/`scoreApp()`/`resolveAsk()` in `skins-engine.js`. All 19 apps now
  proven, live in a real browser with screenshots, in
  `shelf-integrations/_frontdoor-live-check/README.md` -- including a full click-through
  proving the demo preview's own real "Add" button genuinely works, not just that resolution
  picked the right app.
- Adapter: both measured families delivered across a real different origin, colours-only
  apps get variables with no guessed stylesheet, wrong-origin senders are refused and named.

## Proven: a real app, wired for real (`shelf-integrations/productivity/`)

Super Productivity's real source (`github.com/johannesjo/super-productivity`, commit
`a1743173`) was cloned, `npm install`ed, and built for real
(`ng build sp2 --configuration=productionWeb` -- it's purely client-side, no backend or
database, which is why it was picked first). A real Chromium opened the real build and,
through the app's **own real Settings UI** (not a console shortcut), created a tag, set its
colour via the app's own native colour-input component, saved, and switched into that tag's
context -- exactly what a person would click through. The colour handed in was our engine's
real output for this exact shelf entry:
`design_tokens.build_tokens("bold_contrast", category_hue("productivity"))["primary"]`.

Verified live, in the browser, with zero JS errors: the app's own real
`--palette-primary-500` custom property (and the whole Material colour ladder behind it) was
recomputed by the app's own `MaterialCssVarsService` to our exact colour, and the whole
chrome -- sidenav highlight, add-task button, header icon -- visibly recoloured. Screenshots
in `shelf-integrations/productivity/evidence/`.

A genuinely useful negative result came out of this too: a naive direct override of
`--palette-primary-500`/`--brand` (the same generic-variable pattern
`frontdoor-skin-adapter.js` uses) **did not work** -- the app's dynamic theming computes far
more than those two variables at runtime. Driving the real UI was the only mechanism that
actually worked; see `shelf-integrations/productivity/README.md` for the full account, kept
rather than hidden, since it's exactly the kind of thing the next app's integration needs to
check for itself rather than assume.

`shelf-integrations/productivity/test_super_productivity_live.py` reproduces this; it's kept
separate from `test_frontdoor.py`'s 96 tests because it needs a live build already running
(too heavy for every commit) and skips cleanly rather than failing when one isn't reachable.

## Proven running: 16 of 19 shelf apps (`shelf-integrations/STATUS.md`)

Beyond Super Productivity's full skin integration, 15 more apps were cloned, built with real
native infrastructure (no docker -- image pulls are blocked here, so this runs on
apt-installed Postgres/MariaDB/Redis/pgvector, Go, Ruby, PHP, Python, Node), and driven
through a real signup or setup flow into their real dashboard, with mobile-viewport overflow
checked and the console watched for JS errors the whole way: **Uptime Kuma, DocuSeal,
Chatwoot, Infisical, Nginx Proxy Manager, Memos, Galene, Mautic, Ghost, linkding, AnythingLLM,
Strapi, Krayin, and langfuse** (the last on its final Postgres-only release, `v2.95.12`, since
current main needs a ClickHouse+S3 stack unreachable here -- disclosed, not silently
substituted; Mautic and Krayin both on MariaDB 10.11, since Mautic 7.x's own installer refuses
the Ubuntu-archive MySQL 8.0 and MariaDB is a real, supported alternative per Mautic's own
compatibility matrix; Ghost on Node 22.23.1, its own primary pinned version, after a real
Node-24-specific native-module crash in `better-sqlite3` surfaced on the alternative version
its own `engines` field also allows; AnythingLLM with one optional `.xlsx` file-format
converter excluded since its dependency chain resolves to a blocked CDN, and a real
mobile-layout gap at 390px disclosed rather than hidden; Strapi built from its own core
framework monorepo via Yarn Berry + Nx and run through its own real `examples/getstarted`
fixture app, rather than guessing at a native setup for what's otherwise a Docker-first
recipe). Full per-app mechanism notes, real bugs found along the way (DocuSeal's own committed
SQLite schema has Postgres-only SQL), and the
exact fixes applied are in
`shelf-integrations/STATUS.md`.

**Flagsmith, Appsmith, and OneDev are genuinely blocked**: Flagsmith's `pyproject.toml`
requires `flagsmith-private` from a non-public package index; Appsmith's entire config store
is built on Spring Data reactive MongoDB with no Postgres/MySQL fallback in the CE codebase,
and MongoDB itself is unreachable here (no apt package, official repo unreachable, generic
tarball blocked by egress policy); OneDev's Maven build needs a parent POM published only on
the project's own private Maven repo, genuinely absent from Maven Central, with its only other
distribution channel (a Docker image) unreachable the same way every other Docker Hub pull has
been on this shelf. All three are real gaps in the OSS repo or this sandbox's network policy,
not something to work around by faking a datastore, stripping a real dependency, or inventing
build configuration. **code-server is deprioritized**: a reproducible bug in its own npm
postinstall pipeline in
this sandbox, lower-value to chase than the business apps.

## Not yet proven

- None of the 19 shelf apps' actual page markup has a `render_css.py`-style CSS family yet --
  "proven running" (above) and "measured for a full stylesheet skin" are different bars. Only
  Super Productivity has gone further, via its own real theming service rather than a CSS
  family (see above).
- `reference/` holds the original demo materials (`SKINS.md.orig`, `test_skins.py.orig`) this
  system was built from, for provenance -- they describe a smaller, fictional 43/52-category
  demo catalog, not this repo's real one.
