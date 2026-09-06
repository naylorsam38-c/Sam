# Connector

> Something for connecting people — I want to keep everyone's details, see who is at what stage of joining, and log every time we talk to them.

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

You picked **Board**. The other two are there anyway.

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
- **The app deciding who or what to match together.** There is no matching or recommendation engine on the shelf. _You can hold everyone's details, filter and group them, and move each person through stages by hand. A person does the matching; the app records it._
- **Video or voice calls.** Not on the shelf, and not something this system builds. _You can book a time and hold the details of the meeting. The call happens in whatever you already use._
- **Maps, distance or 'people near me'.** There is no mapping or location engine on the shelf. _You can hold an address as text and filter on it. No map, no distance._
- **An app people install from the App Store or Play Store.** What gets built is a web app, opened in a browser. _One of the three looks is built for phones — it fills the screen, has big buttons and a bottom tab bar. People open it in their phone browser and can pin it to their home screen._
- **Putting it on the internet at your own web address.** The system builds and proves the app; it does not host it or buy you a domain. _You get the whole app and instructions to run it. Putting it somewhere permanent is a separate job for you or a developer._

## Is it actually working?

Every button in all three interfaces is pressed in a real browser and the result is checked against the app's own data — not against what the screen claims. Run it yourself:

```bash
cd app && python3 app.py        # then open http://127.0.0.1:8900/
```
