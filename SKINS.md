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
- **`library.json`** -- the real shelf catalog: 8 real, named, open-source self-hosted apps
  (Flagsmith, Chatwoot, code-server, DocuSeal, Uptime Kuma, Nginx Proxy Manager, Infisical,
  Super Productivity), copied verbatim from their own `app.json` entries in Sam's
  52_APP_LIBRARY acquisition pipeline (name, category, repository, real screenshot). What
  was **not** provided for any of them is their actual page source -- only this metadata and
  a screenshot. So every one of these 8 apps is honestly marked `"family": ""` (colours only)
  in `library.json`, per the rule below. Nothing here pretends one of them has been measured
  when it hasn't.
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

**96/96**, run against two real local HTTP servers (one for the Front Door, a second on a
different port for the cross-origin adapter proof):

- All 172 real `skins_library` files reproduced byte-for-byte by `skins-engine.js`, plus the
  full 360-hue x 4-look range (1440 sets) against the real Python.
- A real, documented rounding bug was caught and fixed while building this: hue 210 in Soft
  Rounded came out one shade off (`#dee5ed` vs Python's `#dee6ed`) because of how a redundant
  floating-point remainder was taken -- the same class of bug `_verification`'s history
  already called out once before. Fixed in `skins-engine.js`'s `pymod`; see the comment there.
- `withEdits`/`lookFields`, gates (`checkEdit`/`normalizeChanges`), ask-resolution against
  all 8 real shelf apps (including a no-match case), preview/keep/not-that/undo/reload/
  close-mid-preview, three viewports (desktop, mobile, mobile dark), no JS errors.
- Adapter: both measured families delivered across a real different origin, colours-only
  apps get variables with no guessed stylesheet, wrong-origin senders are refused and named.

## Not yet proven

- **None of the 8 real shelf apps' actual page markup has been measured.** They ship
  colours-only. Doing this for real (per `skins_library/REPORT.md`'s own methodology: read
  the real source, find the real selectors, add a renderer, verify live) is the next step,
  app by app, starting with whichever is easiest to reach without a full docker stack.
- `reference/` holds the original demo materials (`SKINS.md.orig`, `test_skins.py.orig`) this
  system was built from, for provenance -- they describe a smaller, fictional 43/52-category
  demo catalog, not this repo's real one.
