# Live Playwright Tester — component 4 of the chain

Reads the Assembly Engine's `SPEC.json` (`build_model`) and runs real
Playwright against the real, already-running application the Builder
produced — the same pinned Chromium install `packages/crawler.py` uses, and
the exact same destructive-word skip list (`crawler.DESTRUCTIVE_WORDS`,
imported, not copied).

## What this adds beyond the crawler

`crawler.py` discovers what a page has and records whether a click changed
navigation at all. That is a smoke test, and its own README says so: *"A
click succeeding at the browser level does not prove the product action is
correct."* This component closes that gap for the numbered spec's own
declared actions — a click on the control belonging to `ACT-nnn` is proven
against the real response the real generated route actually returned, not
against wherever the browser eventually lands.

## Two modes, matching how the real spec is shaped

Command Desk's own already-approved spec states AC-01/AC-02 against a
running backend and AC-03 against a stopped one — two different real
conditions, not one simulated in place of the other:

- **`normal`** — the app is really running. Walks every screen in
  `screens_inventory`, checks the empty state where there is genuinely no
  data, and for every `connect`-kind action clicks the real control and
  proves the redirect's real `Location` header (see below for why the
  header, not the final landed page).
- **`backend-down`** — the backend is really not answering (the caller's
  job to arrange, not this tool's). Loads the declared screen and checks
  the real `on_unavailable` message actually renders.

## Why the redirect's Location header, not the browser's final URL

This session's own sandbox denies a headless browser's outbound connection
to `accounts.google.com` by organisation policy (confirmed via the proxy's
own status endpoint: a real 403 to the CONNECT — not a bug, and per this
environment's own rules, not something to retry past). A plain Python HTTP
client (`urllib`) reaches the same endpoint from the same sandbox without
issue — see `tests/test_builder.py`'s two `@NEEDS_GOOGLE` tests, which
complete the real round trip including a real rejection from Google's real
token endpoint. Only the *browser's own* onward connection is blocked.

So the OAuth click here is verified against the 302 response's `Location`
header — produced entirely by the real generated server answering the real
click, observed via `page.expect_response()` before the browser ever tries
to go further. That proves the same real behaviour (a real click reaches
the real route and gets back the real, correct provider URL) without
depending on whether a given sandbox is allowed to complete the trip. It is
not a weaker check than watching the final page load; it is a more precise
one, and it happens to also be robust to this constraint.

## Tested against real running servers

`tests/test_playwright_tester.py`:

- Builds and starts Command Desk's real OAuth feature, clicks the real
  "Connect Google" button in a real browser, and checks the real 302
  Location header — plus that the empty/`MISSING` state renders on a
  genuinely fresh database.
- Proves `backend-down` mode against a *real* failure: the server process
  stays up (so the page really loads, matching what the real spec's own
  wording implies) and the database is overwritten with non-database bytes
  *after* startup, so the running server's next query genuinely fails and
  the real frontend catch path genuinely renders the message. Also proves
  the refusal path: a build with the wrong `on_unavailable` message really
  renders, and the tester really reports it as failed, not a pass.
- Loads every pm-teamwork records screen (real data, same fixture pattern
  as `tests/test_assembly_engine.py` and `tests/test_builder.py`) in a real
  browser and checks for zero console/page errors.

Building this suite found and fixed three more real bugs, on top of the
three found while building the Builder itself:

1. The generated "Connect" button navigated via `window.location.href`,
   which only ever issues a **GET** — but the start route is POST-only
   (the real spec's own AC-01 requires POST). The click 404'd in a real
   browser even though nothing looked wrong in the Builder's own tests,
   which never actually clicked anything. Fixed by generating a real
   `<form method="POST">` instead.
2. `Handler` had no top-level exception handling: a real failure inside a
   route (found via the database-corruption test above) crashed the
   request thread with an unhandled traceback instead of a clean 500,
   which the client saw as a connection reset rather than a real error
   response. Fixed with a `_guarded()` wrapper around every `do_*` method.
3. Every generated page produced a console error on load from the
   browser's automatic `/favicon.ico` request. Fixed with a real 204 route
   for it, rather than filtering the noise out of what tests check for.

None of these three would have been caught by starting the server and
curling it — they only show up when something actually clicks the actual
button, or actually breaks the actual database while requests are in
flight, in an actual browser. That is the reason this component exists.
