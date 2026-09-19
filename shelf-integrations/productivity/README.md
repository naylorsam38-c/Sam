# Super Productivity: a real, measured skin integration

This is the first shelf app in `library.json` to move past "colours only".
Its real source was cloned and built (not just its catalog metadata), and the
skin engine was proven to drive it live, in a real browser, through the app's
own real Settings UI.

## What was actually done

1. Cloned the real source: `https://github.com/johannesjo/super-productivity`
   at commit `a1743173e923492bc15e9e1b3d96d92e8d2c8b94`.
2. `npm install` (1878 packages, real, clean install) and a real production
   web build: `npx ng build sp2 --configuration=productionWeb`. Super
   Productivity's web build is purely client-side (IndexedDB/localStorage,
   no backend, no database) -- this is why it was picked over the other 7
   shelf apps, several of which need a Postgres+Redis stack to boot at all.
3. Served the real build statically and opened it in a real Chromium via
   Playwright. Zero JS errors on load.
4. Read the app's **own real source** to find how it actually themes itself:
   `src/app/core/theme/global-theme.service.ts`'s `_setColorTheme()` calls
   `MaterialCssVarsService.setPrimaryColor(theme.primary)` whenever the active
   work-context's theme changes -- the exact same real pipeline a user
   triggers by giving a project or tag a custom colour. Its colour input is a
   real component (`InputColorPickerComponent`) with a hidden native
   `<input type="color" class="native-color-input">` wired to a real
   `(change)` handler.
5. `apply_skin.py` drives that **real UI**, not a console shortcut: it clicks
   the real "add tag" button, fills the real tag name field, sets the real
   native colour input's value and dispatches a real `change` event (exactly
   what a user's own colour pick fires), clicks the real Save button, then
   clicks into the new tag's context (the actual trigger for
   `GlobalThemeService._setColorTheme()`).
6. The colour handed to it is not arbitrary -- it's
   `design_tokens.build_tokens("bold_contrast", category_hue("productivity"))["primary"]`,
   i.e. exactly what `library.json`'s own `"productivity"` shelf entry (Super
   Productivity itself) would get from a real Front Door look pick.

## What was verified, in a real browser, on the real running app

- The real colour swatch in the real "Create Tag" dialog shows our engine's
  exact colour immediately after the native input's `change` event fires.
- After Save and switching into that tag's context, the app's own real CSS
  custom property `--palette-primary-500` (and the whole Material palette
  ladder it feeds) is recomputed by the app's own real
  `MaterialCssVarsService` to our exact colour -- not merely stored somewhere,
  but read back from `getComputedStyle(document.body)`.
- Visually (see `evidence/`), the entire chrome -- sidenav active-tag
  highlight, the "+" add-task button outline, the header icon, the page's
  soft corner wash -- recolours to match, live, with zero page reload.
- Zero JS errors throughout.

Reproduce with `test_super_productivity_live.py` (see its header for the
exact commands to stand up a live build; it skips cleanly, rather than
failing, when no live build is reachable, since standing one up is too heavy
to run on every commit).

## A real negative result, kept rather than hidden

The first thing tried was **not** driving the real Settings UI -- it was
setting `--palette-primary-500` / `--brand` directly via
`document.body.style.setProperty(...)`, the same pattern
`frontdoor-skin-adapter.js` already uses for its generic `--fd-*` variables.
**This did not work**: the sidenav, buttons, and focus ring stayed on the
app's default blue. Reading `angular-material-css-vars`' own source
(`node_modules/angular-material-css-vars/src/lib/`) confirms why: its runtime
theming computes and writes a much larger, interdependent set of
derived values (the full 50-900 + A100/A200/A400/A700 ladder, contrast
colours, etc.) through its own JS service call, not by the page simply
cascading two or three custom properties on `body`. Poking a couple of the
downstream variables by hand does not reproduce what the real call does.

This matters for anyone extending this integration: **don't** assume a
`--fd-*`-style generic variable bridge works for an app just because it has
CSS custom properties. Confirm by driving the app's real theming entry point
and reading real computed styles back, the way this integration does --
never by asserting a var was *set* without checking it was actually
*consumed*.

## What this does not cover

- Only the primary/brand colour path was wired up, via a tag's colour (the
  simplest real entry point). Super Productivity also has independent accent/
  warn colours, a dark-mode toggle, and per-project (not just per-tag) themes
  -- all real, all reachable the same way, not yet done here.
- This is UI-automation-driven, not a `render_css.py`-style CSS string
  family. That's a real, deliberate difference from the `shared_card`/
  `todomvc` families in `skins_library/render_css.py`: this app doesn't
  expose a stable, directly-overridable stylesheet contract the way those
  do, so `library.json`'s `family` field for `"productivity"` correctly
  stays `""` (colours only, in the `render_css.py` sense) -- see its
  `real_integration` field instead for what actually was proven.
