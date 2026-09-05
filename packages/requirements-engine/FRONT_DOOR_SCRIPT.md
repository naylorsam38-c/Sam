# The front-door interview script

**Superseded draft, kept below for history:** the original version of this
document (committed as `c2e7e10`) was my own wording, extrapolated from a
different session's simpler `front_door.py`/`interfaces.py` mechanism. A
third session then built a more complete, working front door
(`packages/frontdoor/` — `intake.py`, `catalogue.py`, `serve.py`) that
does real cross-template mixing (pick more than one kind of app and it
merges them into one spec) and is fully tested. This revision replaces my
earlier wording with that real system's actual questions, verified by
running the code directly rather than reading its docs.

## Verification, not trust

Before writing this, I extracted the delivered zip and ran it for real in
this sandbox: `python3 intake.py --questions` printed the exact wording
below; the full suite (`pytest`, both `tests/` and the three package
suites) came back **227 passed, 1 skipped** — the exact count claimed,
reproduced independently, after fixing a local sandbox issue (this
environment's installed Chromium revision didn't match the pinned
Playwright version — an environment quirk, not a code defect). All six
families' checkers are genuinely CLEAN (0 FAIL each), and the shelf's own
`parts_shelf.json` shows 14 of 33 parts at `PRODUCT_QUALIFIED` — matching
the claimed jump from 4.

## The eight real questions

1. **[free text]** *"What do you want the app to do?"* — "Say it however
   you like. A sentence is plenty." Captured as context; **does not**
   currently pre-select anything in Q2 (verified by reading `intake.py` —
   no such routing exists yet). That gap is real, not hidden.

2. **[tap, multi-select]** *"Which of these does your app need?"* — "Pick
   as many as fit. Each one is a whole working piece."
   - Work and tasks — jobs to do, who's doing them, whether they're done (`pm-teamwork`)
   - People and how they progress — a directory of people/companies moving through stages (`crm-pipeline`)
   - Appointments and bookings — what you offer, who booked it, when (`booking-frontdesk`)
   - Stock and orders — what you hold, buy, sell (`erp-backbone`)
   - Invoices and payments — owed, owing, settled (`accounting-ledger`)

   This is the real "mix and match, use them all together" capability —
   picking two or more genuinely merges those templates into one spec
   (confirmed: the `clinic` example build merges `booking-frontdesk` +
   `accounting-ledger` into one running app).

3. **[tap, single-select]** *"Who uses it?"* — Just me / A few of us doing
   different jobs / My team plus the public (the last exposes a public
   page with no account).

4. **[tap, single-select, real screenshots]** *"Which of these looks
   right?"* — Console (desk, rows) / Board (stages, drag) / Pocket (phone,
   big buttons). Same app underneath; all three are viewable afterward.

5. **[tap, single-select]** *"How much on screen at once?"* — Roomy /
   Balanced / Packed.

6. **[tap, single-select]** *"Your mark"* — six real icon options (compass,
   cube, grid, orbit, spark, wave), each with a one-line rationale, plus
   "decide later."

7. **[free text, required]** *"What is it called?"* — "It goes on every
   screen." (Verified this reaches the real build: the `connecting-people`
   example — the same illustrative case used earlier in this
   conversation — produced a real running app actually titled
   **"Connector"**, not a generic placeholder.)

8. **[tap, single-select, conditional]** *"Who is in charge?"* — appears
   only when two picked pieces each came with their own boss role, so the
   merged app has exactly one.

That's 2 typed/free-text questions and 6 tap/visual ones — matching "it
doesn't have to be many... multiple choice with the visual interfaces,
plus whatever word question you need" about as closely as a real,
tested system gets.

## What makes it refuse rather than guess

`catalogue.py` loads each of the five "piece" cards above only if every
record, workflow, report, form and notification it names is something
the real templates actually declare — a card can't promise what the
Builder can't build. It also explicitly declines nine things (chat,
matching, card payments, sign-in, video, maps, App Store, sending email,
going live) with a stated reason and what's offered instead, shown at
the point of choosing rather than failing silently later.

## Known, named gaps (not hidden)

- Q1's free text doesn't yet drive a Q2 suggestion — the person still
  taps the pieces themselves.
- No sign-in exists yet in the generated apps — a real, flagged, pending
  product decision (staff-only vs. customers too; email+password vs.
  invite vs. Google), not an oversight.
