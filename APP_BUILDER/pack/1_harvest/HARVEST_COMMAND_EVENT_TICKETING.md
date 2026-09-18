# HARVEST COMMAND — ONE APP, ONE RUN: EVENT TICKETING

Governing authority: **GOD MODE**. Everything below is subordinate to
`God_Mode_Specification.md` and the two ACTIVE drop-ins in the pack
(`GOD_MODE_RULE_HARVEST_ADMISSION.md`, `GOD_MODE_RULE_NUMBERING.md`).
Where this command and god mode conflict, god mode wins and you say so in your
report.

Attached: `template-harvest-pack-v5-GODMODE.zip`.
Unzip it. Read `README_START_HERE.md` first, then follow its read order.

**This replaces the dating harvest.** Dating was dispatched twice and rejected
twice at admission, on evidence: permissive-licensed Flask dating apps with
published REST API docs do not appear to exist — real dating apps go
strong-copyleft because of the personal data, and the permissive Flask ones are
unlicensed toy clones. Both rejections were correct and are accepted. Do not
re-run dating. `HARVEST_COMMAND_DATING.md` stays in the pack as the record of
that outcome, not as a live instruction.

---

## THE TASK

Harvest **event ticketing** end to end, in one run, and bring back a working
app.

You do the whole thing on your end — find it, clone it, run it, record it, gate
it, number it, write the registry. Nothing gets handed back for someone else to
process. Do not stop to check in.

**Two things must come back and they are not optional:**

1. **The app, running.** Real terminal output of the server up, a real request
   made against it, the real response. Not a description of it running.
2. **The registry, written.** `number_registry.json` and the app tree, with
   numbers allocated, produced by the pack's own scripts.

If you cannot deliver 1, the task failed and you say which step stopped you.

---

## WHY THIS CATEGORY

Event ticketing was picked because permissive-licensed Flask applications with
real published API documentation plausibly exist here, which is exactly what
dating lacked. Admission is still yours to prove, not mine to assert.

**One candidate to check first: Indico** (`indico/indico`). Believed to be
Flask, MIT-licensed, with published HTTP API documentation, and a real
production event-management product rather than a clone. **I have not verified
any of that** — verify the licence from the repo's own `LICENSE` file and the
framework from its own dependency files, exactly as you did with Duolicious,
where a web summary claimed Flask and the actual `requirements.txt` said
FastAPI. If Indico fails a rule, say which and move on. It is a starting point,
not an instruction to accept it.

---

## THE TARGET LIST — FIXED, NOT YOURS TO CHOOSE

From `catalog.json`, the `event-ticketing` row:

```
register account        log in                  log out
search records          filter list             view record detail
book slot               take payment            issue refund
apply discount code     scan barcode            send email notification
send push notification  manage inventory        generate report
split payout
```

16 capabilities. You do not add to it, drop from it, or reinterpret it.
Catalog line: *lets a user buy entry to a dated event and prove it at the door.*
Extensions on this row: Concurrency, Device Access, Multi-Tenant Ownership.
Catalog exemplars: **none recorded** — naming the exemplar is step 1.

---

## STEPS

### 1. Name the market leader
Which commercial ticketing product you are treating as the exemplar, and why,
with evidence URLs. The catalog records no exemplar for this row, so this is a
real choice and it needs justifying against the 16 capabilities above.

### 2. Read its capabilities off the product
Marketing pages are acceptable **here and only here**, to understand what the
app does. Nothing from a marketing page ever enters the record. Labels, fields
and behaviour come from code.

### 3. Find the open-source equivalent
The closest real, runnable open-source event ticketing or event management
application.

### 4. Apply the four admission rules
Per `GOD_MODE_RULE_HARVEST_ADMISSION.md`:
1. Permissive licence — MIT / BSD / Apache-2.0. Not GPL, not AGPL, not
   source-available.
2. **Flask.** Django, FastAPI, Node, PHP, Java, Go are rejections.
3. Publishes REST API documentation.
4. Structural match to the exemplar.

Confirm every branch with `git ls-remote` before fetching.
`raw.githubusercontent.com` returns HTTP 200 for a branch that does not exist
and silently serves the default — a raw URL is not proof a file is there.

Log every repo you rejected and the rule it failed. The rejections are part of
the deliverable.

### 5. Clone it and get it running — THIS IS THE DELIVERABLE
Clone the accepted repo. Install it. Start it. Hit it.

Show: the install completing, the server process starting, a real HTTP request,
the real response body. Reading the source is not evidence that it runs. If it
will not start, fix it and show the fix, or report exactly what blocked it.

### 6. Record it from real code
Copy `FORM_TEMPLATE_GODMODE_v2.json` to `forms/event-ticketing.form.json` and
fill it.

Every value traceable to a file, a symbol and a line range. Control labels
lifted from templates or route handlers, never from a marketing page. Anything
not findable in the code goes in `unresolved`, named. A named blank is correct.
A guess is a defect.

Leave `cap_block` and every `cap_id` **blank** — they are allocated in step 8,
not written by you.

### 7. Gate it
```
# no gate script -- admission fires inside harvest_parts.py before anything is fetched
```
Exit 0 or it is not done. Fix the record, never the validator.

### 8. Number it and write the registry
Only after the gate exits 0:
```
python3 assign_numbers.py
```
This allocates the app number and the capability numbers into
`number_registry.json` and writes `trees/event-ticketing.tree.json` and
`trees/event-ticketing.tree.txt`. Gate first, numberer second — always that
order.

Run it twice. The second run must reassign nothing. If it allocates new numbers
on a re-run, that is a defect and you report it.

This is the **first** app through the registry, so it is also the first real
test of the numberer. Anything it does that the rule does not describe, report.

---

## GOD MODE CONSTRAINTS THAT WILL BITE ON THIS APP

- **§4 Host Dispatch** — GET and POST only, keyed `(method, path)`. If the
  source uses PUT/PATCH/DELETE, it maps onto GET/POST or it does not go in.
  Ticketing APIs lean on DELETE for cancellation and PATCH for reschedules —
  expect to map these.
- **§2 Capability Record Contract** — `data_access`, `context_fields`,
  `contract_version` nest **inside `data_shape`**. Undeclared entities and raw
  path bypasses hard-fail. `contract_version` is `"2.0"`.
- **§5 Isolation** — data filenames are `event_ticketing__<raw>`. Declare
  `data_access`. `auth_sessions.json` and `blobs.json` are reserved to the
  shared library.
- **§3 CAP-0000** — shared library public API only, no private helpers.
  `take payment`, `issue refund` and `split payout` will want money handling
  that CAP-0000 does not expose — whatever the source does, it goes through the
  declared public API or it goes in `unresolved`.
- **§8 Slot proving** — auth capability names exactly `Register`, `Login`,
  `Bootstrap Admin`.
- **§7 Journey target** — plain, **unauthenticated**, text-based, not an upload.
  This category has a genuine public surface: a public event listing or event
  detail page. `register account` and `log in` are **not** valid targets.
  `scan barcode` is not either.
- **§6 Identity** — **you declare it and justify it against §6's five types,
  from the code.** This row carries Multi-Tenant Ownership, so organiser and
  attendee are likely distinct — but which of the five that maps to is a real
  decision and I am not guessing it for you. Name the type, name the code that
  shows it, and if two types genuinely both apply, put it in `unresolved`
  rather than picking one quietly.
- **§9 Arrangement** — `position` in `left`, `center`, `right` only.
- **§10 Numbering** — superseded by `GOD_MODE_RULE_NUMBERING.md`. Capabilities
  are referenced by number, never copied. CAP-0000 stays reserved.
- **Non-button capability on this row: `scan barcode`.** That one, and only
  that one, appears in `catalog.json.capability_classes.non_button.all`.
  `catalog.json` is the authority — the harvester reads that list at
  runtime, not this command. If this command ever disagrees with the catalog,
  the catalog wins and you report the disagreement.

---

## HARD RULES

- Nothing invented. Not a capability, not a label, not a field, not a line
  number.
- **No mocks, no simulations, no fake providers, no synthetic test data.** It
  runs against the real cloned repo or it is not evidence.
- Do not edit `harvest_parts.py` or `assign_numbers.py` to make anything
  pass.
- Do not touch `CANONICAL_SPEC.md` or anything under `GOD_MODE/ACTIVE/`.
- Do not commit or push.
- Nothing in `ARCHIVE/` governs anything. Do not follow it.

---

## BRING BACK

1. **The app running** — verbatim terminal output: install, server start, a
   real request, the real response.
2. How to start it again — the exact commands.
3. The exemplar chosen, with evidence.
4. Every repo rejected and the rule it failed.
5. `forms/event-ticketing.form.json`, filled, provenance on every value.
6. **Verbatim** gate output including the exit code.
7. `number_registry.json`, `trees/event-ticketing.tree.json`,
   `trees/event-ticketing.tree.txt`, and the numbers allocated.
8. Proof the second numberer run reassigned nothing.
9. Everything in `unresolved`, named.
10. Anything where god mode and this command disagreed.
