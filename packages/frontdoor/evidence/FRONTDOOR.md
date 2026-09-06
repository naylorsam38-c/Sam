# The front door, driven end to end

Run 2026-09-06 01:14:37 UTC. **21/22 checks passed.**

Someone who has never seen this system typed one free-text description in a real browser, was shown matched catalogue cards and any NOT_ON_THE_SHELF gaps, answered the open items themselves, was handed a real running provisional app in all three looks, and locked one. Every line below was produced by doing it, not by describing it.

- PASS console picture taken from the real erp-backbone app (5 rows seeded)
- PASS board picture taken from the real crm-pipeline app (5 rows seeded)
- PASS pocket picture taken from the real booking-frontdesk app (4 rows seeded)
- PASS no pill arrives pre-selected -- who/density/mark carry no default (0 found on)
- PASS the chat request is named as not on the shelf, with what is offered instead (1 flag(s))
- PASS their words matched the right catalogue card: ['People and how they progress']
- PASS questions_shown for this run: 4 (who/density/mark/must_not, no boss -- single template)
- PASS built a real provisional app -- 4 records, 10 screens, 21 actions -> /home/user/Sam/packages/frontdoor/built/show-me-1788657273334
- PASS the first look is served for real (HTTP 200, data-design='console')
- PASS cycling 'Show me another version' visited all three designs in order: ['console', 'board', 'pocket']
- PASS the lock screen names the locked interface ('pocket')
- PASS IFC-001.chosen is 'pocket' in the real SPEC.json on disk, not just on screen
- PASS the plain-English summary is there, and it states what the app does NOT do
- PASS no browser errors in the front door
- PASS questions_shown for EXAMPLES['connecting-people']: 4 (['who', 'density', 'mark', 'must_not'])
- PASS questions_shown for EXAMPLES['clinic']: 5 (['who', 'boss', 'density', 'mark', 'must_not'])
- FAIL median questions_shown across 2 real runs = 4.5 (pass bar: <= 3) -- NOT MET: who/density/mark/must_not carry no default, ever (F1), which puts the floor at 4 open items whenever a template is matched
- PASS a real (non-'nothing') must_not answer is written into YOUR_APP.md
- PASS a build with must_not truly absent (key missing, not just empty) refuses rather than defaulting
- PASS the locked app opens directly on its 'pocket' design, not a chooser (got 'pocket')
- PASS a row created through the handed-over app's own button is really in its data
- PASS no browser errors in the built app

## The summary they were handed

```
# People and how they progress

> Something for connecting people — I want to keep everyone's details, see who is at what stage of joining, and log every time we talk to them. I'd also like them to chat to each other.

This is what was built from your eight answers, in plain English.

## What is in it

- **Organisation**. Holds: Name, Website, Phone, Notes.
- **Contact**. Holds: Full name, Email, Phone, Organisation.
- **Deal** — moves through Lead in → Contacted → Proposal sent → Negotiation → Won → Lost. Holds: Title, Value, Owner, Contact, Organisation, Expected close date.
- **Activity**. Holds: Subject, Type, Due, Done, Owner, Deal.

## Who can do what

- **Admin** — in charge; can do everything.
- **Sales manager** — can create, delete, edit, view.
- **Sales rep** — can create, delete, edit, view.

## What it will tell you

- **Pipeline by stage** — How much potential value sits in each stage of the pipeline?
- **Win rate** — Of the deals we finish, what share do we win?

## What it does on its own, with nobody clicking

- crm-pipeline/OPS-001
- crm-pipeline/OPS-002
- crm-pipeline/OPS-003
- crm-pipeline/OPS-004
- crm-pipeline/OPS-005
- crm-pipeline/OPS-006
- crm-pipeline/OPS-007
- crm-pipeline/OPS-008
- crm-pipeline/OPS-009

## Three ways to look at it

The same app, three interfaces — open any of them:

- `app/static/ui-console.html` — sidebar and tables, for a desk
- `app/static/ui-board.html` — a column per stage, for seeing the flow
- `app/static/ui-pocket.html` — built for a phone

You picked **Pocket**. The other two are there anyway.

## What you were not asked, and what was assumed

Every one of these can be changed — they were filled in so you did not have to answer them.

- **0.01** — You decide the product; the plumbing is proposed and shown to you at the end.
- **A.02** — Taken from what you said the app should do.
- **A.03** — Taken from who you said uses it.
- **A.04** — Taken from what you said the app should do.
- **A.12** — Nothing is being imported from an old system. Say so and this changes.
- **A.13** — Dates, money and times use Australian English.
- **A.14** — Nothing about this app works differently from the normal way.
- **C.01** — No other app's look is being copied.
- **C.02** — Taken from the look you picked.
- **C.07** — The menu is the order the screens were built in.
- **Z.01** — What the app does on its own is listed in your summary.
- **Z.02** — Every button and where its result lands is listed in your summary.
- **Z.03** — Every screen and who can open it is listed in your summary.

## What this does NOT do

Said plainly, so it is not a surprise later.

- **Taking card payments.** Charging a real card needs a live payment provider, which is not part of this system. _You can record that a payment was made, and an invoice settles itself once the payments recorded against it reach the total. Someone still takes the money elsewhere._
- **Actually sending the email or text.** Nothing in this system is connected to a mail or SMS provider. _The app produces the document (an invoice, say) and records that it was produced and when. Sending it is a step a person still does._
- **People signing in with their own username and password.** The app knows the different kinds of user and enforces what each may do, but there is no sign-in screen yet — the app is told who is acting. _Everything about roles and permissions is real and enforced. Put the app somewhere only your people can reach until sign-in exists._
- **People messaging each other inside the app.** There is no messaging engine on the shelf. _People can leave comments on a specific item, and everyone who can see that item sees the comments. That covers 'discuss this job' but not 'chat with Sarah'._
- **The app deciding who or what to match together.** There is no matching or recommendation engine on the shelf. _You can hold everyone's details, filter and group them, and move each person through stages by hand. A person does the matching; the a
```

## Pictures

- `evidence/01-what-are-you-building.png`
- `evidence/02-here-is-what-i-think-you-mean.png`
- `evidence/03-answered.png`
- `evidence/04-built-provisional.png`
- `evidence/05-cycled-looks.png`
- `evidence/06-locked.png`
- `evidence/08-the-app-they-got.png`