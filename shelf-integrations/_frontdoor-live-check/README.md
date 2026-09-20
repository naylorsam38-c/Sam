# Front Door itself, proven live: ask -> resolve -> click -> move the buttons

Every other `shelf-integrations/<app>/` folder on this shelf proves a real app
runs on its own, separately-hosted instance. This folder proves something
different and narrower, in direct response to being asked for it: that the
**Front Door product itself** (`front-door.html`, typed into like a person
would) correctly resolves a plain-language question to the right shelf app,
and that a person can then actually click through its own interface -- not
just the target app's separate instance.

## What was found

Going through this exercise for the first time surfaced a real bug:
`skins-engine.js`'s `resolveAsk`/`scoreApp` had never actually been driven
with natural phrasing for the 11 apps added to the catalog this session, only
with test phrasing chosen to match keywords. Two structural problems in the
scoring, run for real:

- A single-word keyword got both a "verbatim substring in the ask" bonus
  *and* a "word overlap" bonus for the exact same evidence, letting generic
  one-word keywords (`llm`, `manager`) systematically outscore more specific
  multi-word phrases (`llm tracing`, `bookmark manager`) that rarely appear
  verbatim in how someone actually phrases a request.
- No stemming, so a plural/singular or verb-form mismatch (ask "bookmark",
  keyword "bookmarks") silently zeroed out an otherwise-correct match.
- Ghost's own `keywords` list in `library.json` was missing the single most
  natural word for it: "blog".

Concretely, before the fix:

| Ask | Resolved to (wrong) | Should resolve to |
|---|---|---|
| "I need a bookmark manager" | Infisical | linkding |
| "I need a blog platform" | nothing matched | Ghost |
| "I need to get documents signed electronically" | AnythingLLM | DocuSeal |
| "I need to trace my LLM calls" | AnythingLLM | langfuse |

## What was fixed, and how it's proven

`skins-engine.js`'s `scoreApp`/`resolveAsk`/`tokenize` were rewritten: a
small deterministic stemmer, a scoring split so a verbatim-substring bonus
only applies to multi-word phrases (not single generic words), and an
extended stopword list excluding generic descriptor nouns ("manager",
"platform", "tool", "app", "system", "service", "software", "solution") that
show up incidentally across many unrelated categories. `library.json`'s
Ghost entry got "blog" added to its keywords. See the comments directly
above `stem()`/`scoreApp()`/`resolveAsk()` in `skins-engine.js` for the full
account.

This is now proven two ways:

1. **Durable, in the real test suite.** `test_frontdoor.py`'s new Section E2
   drives all 19 real catalog apps through the actual `#ask-input` /
   `#ask-form` UI with a natural, non-keyword-copying ask for each, and
   checks the resolved `app.slug` -- 115/115 total, up from 96. Verified
   this is a real regression test, not a tautology, by temporarily reverting
   `skins-engine.js` to its pre-fix state and re-running: 3 of the 4 broken
   cases above fail immediately (the 4th, Ghost, needs the `library.json`
   keyword fix too, which was left in place for that check).
2. **Live, in a real browser, with screenshots** (this folder):
   - `ask-01` through `ask-06`: six real asks (Krayin, Strapi, AnythingLLM,
     linkding, Ghost, Mautic) typed into the Front Door's own ask screen,
     screenshotted after resolution. `ask-04-linkding.png` and
     `ask-05-ghost.png` are the two that were broken before the fix (they
     used to show Infisical and a "nothing matches" screen, respectively) --
     now showing the correct app's real name/blurb/repo link.
   - `click-01` through `click-04`: a full click-through of the Front Door's
     own interface for the linkding case, proving the buttons actually move,
     not just that resolution picked the right app:
     - `click-01-fab-open.png` -- resolved to linkding, tapped the round
       skin-picker button (`#fab`), the real look-picker sheet opens.
     - `click-02-look-picked.png` -- picked "Bold Contrast"; the live
       preview (the first-party `demo-app.html` "Job tracker" fixture --
       see `SKINS.md` for why it's this fixture and not linkding's own
       markup) recolours immediately, with the real confirm/"Keep it"/
       "Not that" step.
     - `click-03-kept.png` -- clicked "Keep it"; the sheet shows the real
       "Undo: Switches the look to Bold Contrast" log entry.
     - `click-04-demo-button-clicked.png` -- filled the demo's own real
       "New job" input and clicked its own real "Add" button (the demo
       page's own JS handler, not a shortcut): the job list genuinely grew
       from 2 items to 3, with the exact typed text appended
       ("Test bookmark demo interaction"), confirmed both by a direct
       DOM-count/text assertion and, after closing the sheet and scrolling
       the demo's own list into view, visually in this screenshot.
   - Zero JS console errors throughout. One real (harmless) 404 was found
     during this work -- the browser's automatic `GET /favicon.ico`, which
     neither `front-door.html` nor Python's `http.server` handled. Fixed
     with an inline data-URI `<link rel="icon">` in `front-door.html`;
     reproduced as present before the fix and absent after.

## Every app, every screen (not just ask-resolution)

Being asked directly whether *every* app had actually been checked loading in
properly, through every screen, with buttons and photos verified -- not just
resolved correctly -- surfaced a real gap: until this point, only
ask-resolution had been checked for all 19 apps, and only one app (linkding)
had been driven through a full interactive click-through by hand. The other
18 apps' own screens (their real screenshot actually rendering, the
skin-picker sheet, live preview, keep/undo, the demo's own real Add/Clear
buttons) had never individually been exercised.

`test_frontdoor.py`'s new Section E3 closes that gap for good: every one of
the 19 real catalog apps is now driven through every screen the Front Door
shows for it --

1. the app screen (real name, real screenshot -- checked via
   `naturalWidth > 0` in a real browser, not just "the file exists on disk",
   real repo link, the honest "colours only" family note),
2. the skin-picker sheet (`#fab`, five look tiles, original marked pressed),
3. live preview (picking a look visibly changes the demo's rendered colour),
4. keep it (saved to `localStorage`, logged),
5. the demo fixture's own real "Add" and "Clear" buttons (its own JS
   handlers, not a shortcut -- job count and text verified, not assumed),
6. undo (reverts to original) and close.

266 new checks (19 apps x 14 each), all passing -- **381/381 total**, up
from 115. Verified this is a real check, not a tautology, by temporarily
pointing one app's `screenshot` field at a nonexistent file: both the
image-load check and the "no errors" check failed immediately and correctly
for that one app, with the other 18 unaffected; reverted after confirming.

`walkthrough-01-ab-testing-experimentation-*.png` (Flagsmith, first in the
catalog), `walkthrough-02-note-taking-*.png` (Memos, an app in the middle of
the catalog), and `walkthrough-03-crm-*.png` (Krayin, last in the catalog)
are a representative sample of this, screenshotted live: the app screen with
its own real name/screenshot/repo link, then after picking a look and
clicking the demo's own real "Add" button, showing a genuinely different
job text appended for each app's session ("Walkthrough job for Memos", etc).

## What this does and doesn't prove

This proves the Front Door's own ask/resolve/preview/keep flow is real and
interactive for these apps -- the actual bar asked for ("running these
through the questions clicking through it making sure you can move the
buttons"). It does not change what `SKINS.md` already discloses: none of the
19 shelf apps' real markup has been measured into a CSS family, so the live
preview shown is always the first-party `demo-app.html` fixture recoloured,
never the shelf app's own real page embedded inline. That's a separate,
already-documented gap, not something this evidence folder claims to close.
