# The front-door interview script

The actual customer-facing wording for the flow you described: describe it
in your own words, get shown real interfaces, confirm the look, answer as
few more questions as possible, hand off to the Builder. This is grounded
in the real, already-built mechanism (`front_door.py`, `interfaces.py`,
the `C.00` interview question, and each template's real `ask_customer`
list) — not invented wording for a system that doesn't exist. Where the
wording below asks for something the code doesn't do yet, that's called
out explicitly rather than glossed over.

## Why so few questions

Each of the 5 templates leaves 17 real open questions in its
`ask_customer` list (confirmed by reading `pm-teamwork.json` directly).
`front_door.py` answers 11 of those 17 itself from a labelled `AUTOMATED`
table (shown to the customer with its reason, never hidden), and folds
4 more (`C.01`-`C.04`: layout, palette, density, tone) into a single tap.
That leaves exactly **3 things a person answers**: which kind of app,
what it should look like, and its name. Everything else is default,
visible, and correctable before build — never silently guessed.

---

## Q1 — Open, one line (free text)

> **"Tell us in your own words what you need this app to do for you."**

Purpose: warms the person up and gives them a place to say anything —
"I run a small physio clinic and I'm sick of double-booking myself" —
without needing to know any of this system's vocabulary. This text isn't
consumed by a rule today; it's there so Q2's category choice feels like a
continuation of what they just said, not a cold restart. **Gap, stated
plainly**: matching this free text to the right category in Q2
automatically (rather than the person picking) isn't built — there's no
classifier here yet. Until there is, Q2 is answered by the person, with
this text as context for whoever/whatever picks the pre-highlighted
suggestion.

## Q2 — Which kind of app (visual, single-select tiles)

> **"Which of these is closest to what you're building?"**

One tile per real category, a one-line description in plain language —
not the internal template names:

| Tile | Plain-language line | Real template |
|---|---|---|
| 🗂️ Team & Project Work | Tasks, boards, deadlines, who's doing what | `pm-teamwork` |
| 🤝 Sales & Customer Pipeline | Deals, contacts, follow-ups, win or lose | `crm-pipeline` |
| 📅 Bookings & Front Desk | Appointments, services, reminders, no-shows | `booking-frontdesk` |
| 📦 Operations & Inventory | Orders, stock, purchasing, fulfilment | `erp-backbone` |
| 💰 Invoicing & Accounts | Invoices, bills, payments, reports | `accounting-ledger` |

## Q3 — What it should look like (visual, single-select tiles — real screenshots)

> **"Here's what a [category] app can look like. Tap the one you like."**

Three real tiles, each a real screenshot of a real, already-built app in
that category (not a mockup) — `interfaces.py`'s three layout options:

- **Workbench** — sidebar navigation, dense, built for someone who lives
  in this screen all day
- **Cards** — a top-nav gallery, browsing-first
- **Focus** — single column, breadcrumbs, one thing at a time

Under the three tiles, the confirm loop you asked for, worded exactly as
a yes/no-plus-escape-hatch:

> **"Is this what you wanted it to look like?"**
> **[ Yes, use this ]**   **[ Show me a different category ]**   **[ Let me describe a change ]**

If "Let me describe a change":

> **"What would you move, add, or remove?"** (free text)

**Gap, stated plainly**: today this box is where the person's words would
go, but nothing yet reads it back into a changed layout — the 15 real
interfaces are fixed presets. Wiring this box to actually adjust the
chosen preset (move a nav item, hide a field) is new work, not yet built.

## Q4 — The one thing that must be typed (free text, required)

> **"What do you want to call your app?"**

This is `A.05` — it appears on every screen and every email, so it's the
one question no default can stand in for.

## Then — the automate-the-rest read-back

Before handoff, the person sees exactly what got filled in for them and
why (this is real: `front_door.py` writes it to `front_door.automated`,
not hidden):

> **"We've filled in the rest with sensible defaults for a [category] app.
> You don't need to change any of these — but here's what we chose, and
> why:"**

| What | Default | Why |
|---|---|---|
| What "done" looks like | Every record, action, report and notification works end to end | Same Definition of Done the build-and-test loop already checks |
| Who uses it | The people who do this work every day | The template's own roles |
| Region / language | Australia, English | Change it if that's wrong |
| Data import | None yet | Never assumed — tell us your source and we'll wire it up |
| Menu order | The template's own natural order | Reorder later if you want |

Each row has a **[change this]** link — not a wall of settings, just an
escape hatch on the specific defaults someone might actually want to
touch.

## Then — handoff

> **"That's everything. Building your app now — we'll test every button
> ourselves before handing it to you."**

This is where the real pipeline takes over: `front_door.fill()` produces
a customer-complete instance, `assemble.py` turns it into a numbered
spec, `builder.py` builds the real app, and the Playwright-driven
fix-and-retest loop runs before anything is called done.

---

## What's real vs. what's new wording

**Real, already built and tested**: the 3-question reduction itself
(category, look, name), the 15 real screenshotted interfaces behind Q3,
the automated-defaults table and its reasons, the refusal if anything is
still open after these three answers.

**New in this document**: the plain-language category names/descriptions
in Q2 (the code calls them `pm-teamwork` etc.), the Q1 free-text warm-up
and the Q3 confirm-loop wording (`Is this what you wanted it to look
like?` / `Let me describe a change`) — these are the actual words to put
in front of a customer; they are not yet wired to code.

**Explicitly not built yet, named rather than hidden**: Q1's free text
does not yet route to a Q2 suggestion; Q3's "describe a change" box does
not yet edit the chosen layout. Both are real, scoped gaps — the next
concrete build items if this script is adopted, not stubbed today.
