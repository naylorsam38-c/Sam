# Library rules — as decided 2026-09-19

Everything below was decided by Sam in the session that dropped the Django-only rule. Where a rule is
implemented, the setting that enforces it is named.

## Architecture

1. **The stack rule is dropped.** Any working app in any language can go on the shelf, provided it is licensed
   for use and serves its own screens.
2. **Capabilities are their own services, written in Node**, with their own storage, exposed over the network.
3. **The translator is the connector.** It speaks the host app's language on one side and Sam's canonical
   names on the other, and carries answers back. It carries events and answers; it does not carry tables.
4. **Nothing shares a database.**
5. Harvesting other people's capability *components* is parked — second shelf, its own licence and admission
   problems. App shelf first.
6. Cost accepted: each capability is a deployed service; network calls instead of function calls.

## What counts as an app

7. **A live app has screens.** JSON-only is a component, not an app. (`MIN_SCREEN_FILES`, `LOGIN_MARKERS`)
8. It must run from its own recipe in its own repo — compose file or Dockerfile. (`RUN_RECIPE_NAMES`)
9. Licence is read from the repo's own LICENSE file, never from a directory listing alone.
   (`ALLOWED_LICENCES`, `NO_LICENCE_FILE_IS_REFUSAL`; OSL, PolyForm, CC-BY-NC, BUSL, Elastic, SSPL, EUPL are
   named and refused)

## The category gate (added after the Kestra / Cal.diy / HyperSwitch failure)

10. **An app must say what it is.** Its own description or README head must contain one of the category's
    `declares` phrases. Stray words in code do not count. (`CATEGORY_GATE_ON`, `DECLARATION_*`)
11. **A product name only declares in "alternative to" context.** "Sends alerts to WhatsApp" is an
    integration; "open-source alternative to Eventbrite" is a declaration. (`PRODUCT_NAMES`,
    `PRODUCT_NAME_CONTEXT_WORDS`)
12. **Anchors.** The first three capabilities of each row are things the app cannot be without; every word of
    each anchor must appear in the structural code. (`ANCHOR_COUNT`, `ANCHOR_REQUIRE_ALL_WORDS`)
13. Anchor checking is still word-based and can refuse a right-kind app on vocabulary (it struck NewsBlur,
    Miniflux and CommaFeed on "Source aggregation"). The walker, not the anchor, is the real capability check.

## Admission

14. **The machine decides, not Sam.** Sam does not review screenshots; screenshots are evidence for disputed
    cases. Sam sees one table.
15. **Admission needs both**: a passed walkthrough AND a high robustness rank. Robustness (tests, CI, releases,
    commit cadence, stars) separates a maintained project from a weekend build. (`ROBUSTNESS_WEIGHTS`)
16. **Robustness alone earns nothing.** The app has to do the capabilities in the row. Anything short is not
    a finished library entry.
17. **Blank beats wrong.** A category with nothing that does the job says NONE ADMITTED. Dating, short-form
    video and Zoom-class conferencing are expected to be blank.

## The walker's output is a gap list

18. The walker stands the app up from its own recipe, in a real container, and drives a real browser. No
    mocks, no simulations, no synthetic data.
19. Per capability it records REACHED (a screen for it was reached), SEEN (words only), ABSENT. Boot and
    get-in are recorded with the reason on failure.
20. **The output is a gap list, not pass/fail.** An app that does twelve of fifteen stays as the base; the
    three gaps are what the Node capability services fill through the translator.
21. Only one round. The walker tries the next-ranked app itself if the top one will not boot
    (`CANDIDATES_PER_CATEGORY`). Sam is not sent back through the list.

## Pipeline as agreed

search per category → licence gate → screens gate → runs gate → category gate → robustness score →
capability match → rank → walker stands up top candidates and walks the row → one table, NONE ADMITTED where
nothing passes.

## Not yet done (carried forward)

- Capability lists have no source links; each needs a `source_url` from the exemplar's own site and a
  `core` flag before the walker can issue feature verdicts against the exemplar. Never from memory.
- Which 70 is the library: Sam's pasted benchmark table (used here) vs CATEGORY_REGISTRY.json (differs).
- The old Django rulebook (DJANGO_UNCHAINED.md) no longer describes the system and needs rewriting.
- Capability service architecture (interface, storage, deployment, translator mapping, per-app enable flag).
- Walker proof level: boot + get-in + reachable screens today; end-to-end feature proof is the next level.
