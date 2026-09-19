SUPERSEDED — NOT CURRENTLY USED AS GOVERNING AUTHORITY
Superseded by: `GOD_MODE/ACTIVE/God_Mode_Specification.md`
Reason: Historical evidence report for a completed build round. Its operative rules and current test evidence are now stated directly in God_Mode_Specification.md and GOD_MODE/ACTIVE/active_apps/APP_LIBRARY_MANIFEST.md. Nothing in this document was found to conflict with the current implementation; preserved as the historical record of how the current state was reached.
Original path: `COMPATIBILITY_AUDIT.md` (repo root)
Archived: 2026-09-13

---

# Compatibility audit — 43 built apps, real ecosystem test

**Scope discipline, stated up front:** nothing in `OUTPUT_LIBRARY/` was touched, rebuilt, or modified to
produce this report. Every finding below was produced by reading the real, already-built code (`OUTPUT_LIBRARY/`
plus the full shelf contracts still on disk under `verification/library_build/*/shelf/`) and by running real,
disposable, out-of-tree experiments against copies of that code — never against the library itself.

## Method

1. **Mapped** every app's backend (Flask host + capability modules), interface (frontend markup/JS), and
   dependencies (data files, sibling-capability references) from the real shelf contracts (`shelf/capabilities/CAP-*.json`)
   and the real route/host source files — 43 apps, **187 capabilities** total (144 compute + 43 host/UI-loaders).
2. **Catalogued** every capability's real contract (required input, output fields, side effects, category) and its
   real code shape — not inferred from naming, read from the actual `handle()` source.
3. **Tested**, live, whether capabilities can actually communicate:
   - Copied one app's capability file, byte-for-byte unmodified, into a different app's `modules/` folder and called
     it over real HTTP.
   - Ran two apps as two real, separate processes and tried a real cross-origin `fetch()` from one app's page to
     the other's API, in a real Playwright browser.
   - Ran two apps as two real, separate processes and made a real server-to-server HTTP call from a small script,
     piping one app's real output into another's real input.
4. **Classified** every capability green/yellow/orange/red per the rubric below, then answered the ecosystem
   question from what the tests actually showed, not from what the shared build convention implies.

Rubric used:

| Class | Meaning |
|---|---|
| 🟢 GREEN | Directly reusable, unmodified, as shipped |
| 🟡 YELLOW | Same structural shape; reusable once field names/route/entity are adapted |
| 🟠 ORANGE | Reusable in principle, but tightly coupled to another capability's data inside its own app |
| 🔴 RED | Not reusable — the business rule itself is domain-specific, not just a naming difference |

## 1. What's actually in the 43 apps

| Shape class | Count | What it is |
|---|---:|---|
| CREATE | 51 | validate required field(s) → build record with an auto-incrementing id → append → save → `201` |
| LIST/READ | 50 | no input → return the whole collection under one named key |
| HOST/UI-LOADER | 43 | one per app: Flask host, `/health`, dynamic capability-module discovery + dispatch, serves the page |
| UPDATE | 27 | find record by id → mutate one or more fields → save → `200` |
| DELETE | 13 | find record by id → remove it → save → `200` |
| AGGREGATE/READ | 2 | reduce the collection to one computed number (ledger balance, expense total) |
| genuinely bespoke compute | 1 | payroll's "run payroll" (see §3) |

**Zero of the 187 capabilities require authentication.** There is no user/session/identity concept anywhere in
the library — every app is single-tenant and unauthenticated by construction.

**Zero data-filename collisions** across the 43 apps' 52 distinct data files — each app's storage is already
namespace-clean.

## 2. The real interoperability tests

### Test A — mechanical drop-in (does the code even run somewhere else?)

Took `crm`'s real, unmodified "Create Contact" capability (`CAP-0802/route.py`) and copied it — no edits —
into a disposable copy of `helpdesk_ticketing`'s build, alongside its native capabilities.

```
health: {'ok': True}
native helpdesk still works: {'tickets': [...]}
foreign CRM capability call: 201 {'email': 'x@example.com', 'id': 1, 'name': 'Foreign Test', 'stage': 'lead'}
foreign capability's own data file (crm.json) written inside helpdesk app's data dir:
[PosixPath('data/helpdesk_ticketing.json'), PosixPath('data/crm.json')]
```

**Result: it just worked.** The dynamic module loader (identical in all 43 hosts, confirmed by diff) picks up
*any* capability dropped into `modules/`, because every capability is self-contained — its own `DATA_FILE`, its
own `ROUTE`, zero imports of sibling modules. This is real, positive, and not obvious in advance.

### Test B — browser-to-browser (can a combined *frontend* call two apps' APIs?)

Ran `crm` and `helpdesk_ticketing` as two real, separate Flask processes on two real ports. Loaded `crm`'s real
page in a real Playwright/Chromium session, then tried a real in-page `fetch()` to `helpdesk_ticketing`'s API:

```
Cross-origin fetch from CRM's page to helpdesk's API: {"ok": false, "error": "TypeError: Failed to fetch"}
Console errors: ["Access to fetch at 'http://127.0.0.1:7900/api/tickets' from origin 'http://127.0.0.1:7800'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource."]
```

**Result: blocked.** None of the 43 apps send CORS headers, so as deployed today, two of these apps sitting
side-by-side cannot talk to each other from the browser. A combined single-page frontend spanning two of these
backends fails today, out of the box.

### Test C — server-to-server (can a backend orchestrator combine them?)

Same two processes, but the call made from a plain Python script instead of a browser (CORS is a *browser*
policy; it does not apply here):

```
1. Created CRM contact directly: {'email': 's@example.com', 'id': 3, 'name': 'Server Test', 'stage': 'lead'}
2. Server-to-server call, CRM output fed into helpdesk's create_ticket:
   {'id': 3, 'status': 'open', 'subject': 'Follow up with Server Test'}
```

**Result: works today, zero code changes.** A server-side orchestrator that treats each app as an independent
HTTP microservice can already compose them — this is a real, immediately-usable integration path, distinct from
(and better-proven than) the browser path.

## 3. Classification

### 🟢 GREEN — directly reusable today, unmodified

- **The storage engine.** `_load()`/`_save()` (JSON read/write with the same defensive `try/except`) is
  byte-identical in every one of the 144 compute capabilities, differing only in the `DATA_FILE` line. Confirmed
  by diff across three unrelated pairs (todo/crm, music/podcast, photo/social).
- **The host runtime.** Flask app + `/health` + dynamic capability-module discovery/dispatch is byte-identical
  across all 43 hosts (diffed `crm`'s and `auction`'s `app.py`: the only differences are the embedded page HTML
  and the literal `"CAP-XXXX"` self-exclusion string). Test A proves this is genuinely, not just theoretically,
  portable.
- **The interface CSS/layout shell.** 42 of the 43 apps' pages share a byte-identical `<style>` block (`.card`,
  button variants, list layout) — only `todo_list` (built before the shared generator existed) differs.

### 🟡 YELLOW — reusable with an adapter (140 of 187 capabilities)

Every CREATE (51), DELETE (13), and the great majority of UPDATE (27) and LIST/READ (50) capabilities, plus both
AGGREGATE/READ capabilities. Proven, not assumed: diffing matched pairs (todo vs. crm's delete-by-id;
fitness_tracking vs. meditation's create; music_streaming vs. podcast's play-count update; photo_sharing vs.
social_feed's like-count update) shows **zero algorithmic difference** — only variable names, the route string,
and the data filename change. An adapter here means "substitute the entity name, field names, route, and data
file," not "rewrite the logic."

Real cross-app shape matches already exist in the wild, with **12 different apps** sharing the exact same
delete-by-id contract (`{id} → {id, deleted}`), and smaller exact matches for list-shape (auction/inventory,
calendar/event_ticketing, e-commerce/marketplace, e-commerce/restaurant_pos, language_learning/quiz, and
short_video_feed/video_streaming, which share **both** their list and their view-count-update shape).

A smaller sub-family (video_conferencing's join-room, habit_tracker's check-in, quiz's review, spreadsheet's
set-cell) adds one conditional/idempotent rule on top of the same skeleton — still YELLOW, just a slightly
richer adapter ("append if not present," "increment if a condition holds").

### 🟠 ORANGE — reusable, but tightly coupled (1 of 187)

**`payroll`'s "Run Payroll" (`CAP-1003`).** Its `handle()` hardcodes a path to a *sibling* capability's data
file (`employees.json`, written by `CAP-1002`) rather than calling that capability's API. Move this file into
another app unmodified and it silently reads whatever (if anything) happens to live at that filename there —
no error, no declared dependency, just quietly wrong or empty output. This is the one proven case of intra-app
coupling in the whole library.

That also surfaces a system-level gap: every capability's shelf contract has a `dependencies` field, and it is
**empty in all 187 records** — this coupling is real but invisible to any tooling; it was only found by reading
source.

### 🔴 RED — not reusable (3 of 187, plus two structural absences)

- **`auction`'s "Place Bid"** (`CAP-2103`) — rejects a bid unless it exceeds the current one. A real business
  rule, not a naming difference.
- **`dating`'s "Swipe"** (`CAP-3103`) — searches the whole swipe history for a reciprocal like to declare a
  match. No other capability in the 187 does a cross-record reciprocity search.
- **`event_ticketing`'s "Buy Ticket"** (`CAP-2703`) — enforces a capacity ceiling. A real domain guarantee
  (no overselling), unique to this capability.
- **Every app's domain-specific UI markup and JS** (everything inside `page_skeleton()`'s `body_inner`/`script`
  arguments) — bespoke per app; only the outer shell is shared (see GREEN above).
- **Notifications and calendars, as reusable capability types, don't exist at all.** Not one of the 187
  capabilities sends a notification of any kind (no push, no webhook, no in-app feed, no email trigger) — not
  even in the apps whose real-world equivalents obviously need one (`team_chat`, `helpdesk_ticketing`,
  `social_feed`). "Calendar" fares little better: `calendar_and_scheduling` and `appointment_booking` each
  independently store a raw date/time string with no shared date-handling, timezone, or recurrence logic —
  there is no shared calendar engine to reuse, just two unrelated ad hoc implementations.

## 4. Ecosystem-level findings (not per-capability)

1. **No shared ID namespace.** Every app allocates its own integer sequence from 1. CRM's `id=3` and a helpdesk
   ticket's `id=3` share nothing; there is no foreign-key concept between apps.
2. **No declared inter-capability dependencies** anywhere (confirmed above) — coupling like payroll's is
   discoverable only by reading source, not by querying the registry.
3. **CORS blocks browser-side combination today** (Test B, proven live).
4. **Server-side orchestration works today, unmodified** (Test C, proven live) — this is the real, available
   integration path.
5. **Capability code is mechanically portable** between any two apps (Test A, proven live) because every
   capability is self-contained by construction.
6. **No authentication or identity anywhere** — nothing to unify a signed-in user across apps even if the other
   gaps were closed.

## 5. Verdict

**They are 43 separate working apps that share a common architectural idiom — not yet a compatible ecosystem.**

The shared idiom is real and genuinely useful: identical storage engine, identical host/loader runtime
(mechanically proven portable), a shared UI shell, and the same few CRUD shapes reappearing everywhere (140 of
187 capabilities are one adapter away from being drop-in reusable, and the delete-by-id shape already is,
verbatim, across 12 apps).

But "ecosystem" implies capabilities can be *composed*, and today that's true in exactly one direction: **server-side, capability-by-capability, one adapter at a time** — proven live in Test C. It is not true **for a combined frontend** (Test B: CORS blocks it outright) or **for anything that needs to know who's using it, cross-reference another app's record, or notify anyone** (§4.1, §4.6, and the calendar/notification gaps in §3).

**What this means for asking the builder to combine capabilities into a new app:**

- Feasible now, with real (not hypothetical) confidence: pull 2–4 of the proven-YELLOW CRUD capabilities across
  different apps into one new app's shelf, server-side, the same way Test A and Test C did it live. This is a
  request the builder can execute today.
- Not feasible without real architectural work first: anything that needs (a) a shared user/auth model, (b) a
  cross-app reference/ID scheme, (c) a combined browser frontend spanning more than one app's origin (needs
  either CORS headers on every app or a reverse-proxy/gateway), or (d) a calendar or notification capability —
  none of those exist yet anywhere in the 43 apps, so "combine the calendar and notification capabilities" isn't
  a composition task, it's a build-two-new-capabilities-from-scratch task.
