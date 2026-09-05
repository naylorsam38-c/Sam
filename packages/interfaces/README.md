# Interfaces — 3 designs × 5 families = 15 working apps

Every interface here is a real client of the family's generated app. Every
control calls the real generated route and shows only what the current role
may really do — the same rules the routes enforce. Nothing is mocked when a
server is there; when the HTML is opened straight from disk, an in-browser
demo store follows the same declared rules and a banner says so.

| Family | App name | Console | Board | Pocket |
|---|---|---|---|---|
| pm-teamwork | Teamwork | `out/pm-teamwork/console.html` | `board.html` | `pocket.html` |
| crm-pipeline | Pipeline | `out/crm-pipeline/console.html` | `board.html` | `pocket.html` |
| booking-frontdesk | Front Desk | `out/booking-frontdesk/console.html` | `board.html` | `pocket.html` |
| erp-backbone | Backbone | `out/erp-backbone/console.html` | `board.html` | `pocket.html` |
| accounting-ledger | Ledger | `out/accounting-ledger/console.html` | `board.html` | `pocket.html` |

## The three designs

They are three different products on the same routes, not three colour schemes.

**Console** — left sidebar of records, reports and forms; data tables; a
right-hand slide-over for the record: fields, lifecycle rail, moves, approval,
declared actions, related records with inline add, activity trail. Desk work.

**Board** — top tabs; a kanban column per stage for any record with a
lifecycle (move chips on every card), card grids for the rest; a centred modal
for the record; the reports as tiles on the Overview. For seeing the flow.

**Pocket** — phone-first: bottom tab bar, full-width cards with 44px+ tap
targets, full-screen record pages with a back button, a floating New button,
toast notices, stat tiles on Home, the role switch under Home / More.

## What every interface does

- **Role switch** — pick any declared role; the page re-reads what that role may see.
- **Create / edit / delete** — where the record's own access grants allow it.
- **Lifecycle** — the stage rail, and a button for every person-moved
  transition the current role may take (exactly `workflow_executor`'s rule:
  Admin is not a mover unless the transition names Admin).
- **Approvals** — at a gated stage: "waiting for X", and Approve / Decline for
  a declared approver; a decline sends the row to the declared `back_to`.
- **Declared custom actions** — Duplicate (clone), Reassign (asks for the new
  owner on press), Send (renders the document, stamps `Sent at`, shows the
  document and the PDF link, and says honestly that no email was dispatched).
- **Related records** — lines under an order or invoice, payments under an
  invoice, added from the parent's own page.
- **Effects, told to the user** — a Received/Shipped order reports the stock
  movement; a Payment reports what it applied and whether the target settled.
- **Public forms** — booking's public booking form, submitted and validated.
- **Reports** — every declared metric: numbers, grouped bars, rates with the
  n-of-m behind them, sales by month.
- **Activity trail** — moves, approvals and pressed actions, from the app's own audit trail.

## Run it against the real app

```bash
cd packages/interfaces
python build_families.py            # assemble + build the five reference instances
python make_interfaces.py           # write the 15 interfaces into each app's static/ and into out/
cd build/crm-pipeline/app && PORT=8802 python3 app.py
# open http://127.0.0.1:8802/            -> chooser
#      http://127.0.0.1:8802/ui-board.html
```

Or open any `out/<family>/<design>.html` directly: it runs on its demo store.

## How it is proven

`drive_interfaces.py` presses every control of every interface in real
Chromium and verifies every outcome by re-reading the API (or the demo store
when opened as a file). Its journey is derived from the family's MODEL, not
written per family: create every record in link order as a role that may,
edit, walk every workflow (approve at every gate, decline once), press every
declared action, add related records, submit forms, run reports, delete;
then sweep that every control kind ever rendered was pressed.

```bash
python drive_interfaces.py                       # all 15 + 3 opened as files
python drive_interfaces.py erp-backbone board    # one
```

Evidence: `evidence/INTERFACES.md` (every step), `evidence/INTERFACES.json`,
`evidence/shots/` (a screenshot at every state). Last run: **1244 checks, 0
failed, 0 browser errors** across 18 interface runs.

`run_seams.py` runs the shelf's own seam journeys against every built family
and writes the qualification receipts (`evidence/seams/<family>/`).

## Files

- `build_families.py` — the five reference instances (the customer questions
  every template leaves open, answered for a plain reference customer, all
  labelled) → `build/<family>/{INSTANCE,SPEC}.json` and `build/<family>/app/`
- `make_interfaces.py` — MODEL from SPEC.json; assembles the 15 pages from `src/`
- `src/runtime.js` — state, the `data-act` dispatcher, transport with demo fallback
- `src/demo_store.js` — the same routes in the browser, for file:// use
- `src/parts.js` — shared fragments (forms, lifecycle, actions, related, trail, reports)
- `src/console.js|css`, `src/board.js|css`, `src/pocket.js|css` — the designs
- `drive_interfaces.py`, `run_seams.py` — the proofs
