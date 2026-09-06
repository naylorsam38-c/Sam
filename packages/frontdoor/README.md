# Front door — eight questions to a working app

Someone who has never built an app says what they want, taps through a handful
of pictures, and is handed a real running application with three interfaces and
the evidence that every button in it works.

```bash
cd packages/frontdoor
python serve.py            # http://127.0.0.1:8700
```

## The eight

One is typing. One is naming it. The other six are taps.

| | Question | What it decides |
|---|---|---|
| 1 | **What do you want the app to do?** | Their own words. Pre-ticks the cards, and catches anything this system cannot build. |
| 2 | **Which of these does your app need?** | Which whole, working pieces go in. |
| 3 | **Who uses it?** | Whether roles are kept, and whether outsiders get a public page. |
| 4 | **Which of these looks right?** | The interface — chosen from photographs of real running apps. |
| 5 | **How much on screen at once?** | Roomy / balanced / packed. |
| 6 | **Your mark** | One of six starter marks, or decide later. |
| 7 | **What is it called?** | The name on every screen. |
| 8 | **Who is in charge?** | Only when two pieces each arrived with someone in charge. |

Question 8 is not padding. When two families merge, the one whose boss is
demoted genuinely needs authority answers it never needed alone — the assembly
engine refuses the build rather than inventing them. Rather than guess, the
front door asks the one question that settles it, then copies that role's new
authority from an ordinary role of its own template and tells the person it did.

The interview underneath has 122 questions, and every template leaves 17 open
for the customer. The other 9–16 are filled in from the templates, and **every
single fill is listed back to the person with the reason it was safe** in their
summary. An unasked question is visible, never hidden.

## Saying no properly

The person will ask for things this cannot build — chat, matching, card
payments, sign-in, video, maps, an App Store app, going live. `catalogue.py`
holds that list, and for each one: what it is, why not, and **what is offered
instead**. It is shown at the moment they choose, not buried at the end:

> **People messaging each other inside the app — not something this can build.**
> There is no messaging engine on the shelf.
> *People can leave comments on a specific item, and everyone who can see that
> item sees the comments. That covers 'discuss this job' but not 'chat with Sarah'.*

That is the rule the whole chain runs on — refuse, never guess — applied to the
conversation itself. **A model helping someone through these questions may only
ever offer a card from `CAPABILITIES`.** It cannot invent one, because the
catalogue refuses to load if a card names a record, workflow, report, form or
notification that the real templates do not declare. The catalogue cannot drift
into promising something the builder could not make.

## What it does after the last tap

No further questions:

1. picks the templates behind the chosen cards
2. combines them with the assembly engine's own `combine` (which refuses a
   clash rather than merging two different things silently), reconciling only
   records that genuinely mean the same thing under different names
3. fills the remaining answers, recording each one's reason
4. runs the real `check_template.py` — if the answers do not make a buildable
   app, it stops and says so in the chain's own words, with nothing half-built
5. assembles the numbered spec, builds the real application
6. generates all three interfaces
7. writes `YOUR_APP.md` — what it holds, who can do what, what it will tell
   them, what it does on its own, every question answered on their behalf, and
   **what this app does not do**
8. starts the app and hands over the link

## Proof

```bash
python prove_frontdoor.py      # ~2 min, real Chromium
```

One run, three jobs: takes the three look photographs from real running apps
with real rows in them; drives a person through all eight questions and the
build; then **opens the app that was handed over and uses it** — creating a row
through its own button and reading it back from its own data. If the front door
ever hands someone an app whose buttons do not work, this fails.

Last run: **14/14**, evidence and screenshots in `evidence/`.

Fast checks that guard the rules (no browser): `pytest tests/test_frontdoor.py`
— 10 tests, including that a card promising a record no template declares is
refused, and that two families with two bosses refuse until the person answers.

## Files

- `catalogue.py` — what can be built, in plain English, proven against the real
  templates on load. Plus what cannot be, with what to say instead.
- `intake.py` — the eight questions, and answers → instance → spec → app →
  interfaces → summary. `--questions`, `--example connecting-people`, `--example clinic`.
- `serve.py` — the front door running: serves the page, really builds, starts
  their app, hands over the link.
- `web/index.html` — the page. One question at a time, big targets, works on a phone.
- `web/shots/` — the three photographs, retaken by `prove_frontdoor.py`.
- `prove_frontdoor.py` — the browser proof.

## Worked examples

```bash
python intake.py --example connecting-people   # "connecting people" -> one family
python intake.py --example clinic              # bookings + invoices -> two families merged
```

`connecting-people` is the honest version of a vague ask: the person wanted
chat, was told plainly it is not available and what is, and got a real directory
with stages, activity logging and reports. `clinic` is two families merged,
including the "who is in charge?" question that makes the merge possible.
