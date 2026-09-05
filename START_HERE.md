# Start here

Three ways in, shortest first.

## 1. See the finished apps (30 seconds, no install)

Open any of these files in a browser — they run standalone on an in-browser
demo store and say so in a banner:

    packages/interfaces/out/<family>/{console,board,pocket}.html

Five families × three looks = the 15 interfaces:
pm-teamwork (Teamwork) · crm-pipeline (Pipeline) · booking-frontdesk (Front Desk) ·
erp-backbone (Backbone) · accounting-ledger (Ledger).

## 2. Run one for real (1 minute)

```bash
cd packages/interfaces/build/crm-pipeline/app && PORT=8802 python3 app.py
# http://127.0.0.1:8802/              pick a look
# http://127.0.0.1:8802/ui-board.html
```

Stdlib Python only — no install, no dependencies.

## 3. Make a new app from eight questions (2 minutes)

```bash
cd packages/frontdoor && python3 serve.py
# http://127.0.0.1:8700
```

Type what you want, tap through pictures, press Build it. It builds a real app
and hands you the link. Worked examples without the browser:

```bash
python3 intake.py --questions                    # the eight questions
python3 intake.py --example connecting-people    # one family
python3 intake.py --example clinic               # two families merged
```

## Read this next

- **`STATUS_AND_DIRECTION.md`** — what exists, what is NOT done and why each is
  stuck, the order to do it in, and the five decisions that need you.
- `FINDINGS_2026-09-05_INTERFACES.md` — what changed and what running it found.
- `packages/frontdoor/README.md` — the eight questions and how they stay honest.
- `packages/interfaces/README.md` — the three designs and how they are proven.

## The evidence

- `packages/interfaces/evidence/INTERFACES.md` — 1244 browser checks, every step
- `packages/interfaces/evidence/shots/` — 343 screenshots
- `packages/interfaces/evidence/seams/` — qualification receipts per family
- `packages/frontdoor/evidence/FRONTDOOR.md` — 14/14, screenshots of every question

## Prove it yourself

```bash
pip install pytest playwright && python -m playwright install chromium
pytest                                          # 227 tests, ~6 min
cd packages/interfaces && python drive_interfaces.py    # every control of all 15
cd ../frontdoor && python prove_frontdoor.py            # the eight questions, end to end
```

## The chain

`requirements-engine` (graph, 6 templates, lock, bind) → `assembly-engine`
(numbered spec) → `builder` (real app + the parts shelf) → `playwright-tester`
(live tester + seam journeys) → `loop` (fix-and-retest, Definition of Done).
`frontdoor` is the way in; `interfaces` is what comes out. `governance/` is the
constitution. `command-desk` is the sixth template — included because the
chain's own tests run on it, and **unchanged**.
