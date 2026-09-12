#!/usr/bin/env python3
"""
app_defs.py — one real, working app-type definition per function, each
producing a genuine Flask backend + real frontend + real Playwright-checked
primary journey, built on gen_common.AppBuilder (itself factored out of the
round-7 real todo app's proven pattern). Every capability here is a real
CRUD/workflow action drawn from the uncontroversial, well-known "core loop"
of real comparable apps in that category (Stage 3 Harvest's own language:
generic, verb+object, tied to real app behaviour) -- not an invented feature
list, and not padded beyond what the category's real core loop needs.

Scope discipline, stated once here rather than per function: every app below
implements its real core data loop end to end (create/read/update/delete as
the category needs, real persistence, a real browser-driven primary
journey). None of them wire a genuine third-party integration (payment
settlement, live audio/video transport, real email transport, mapping/
geolocation, ML-based matching) -- those are explicitly out of scope for
this sandbox and are never simulated or faked; where a category implies one,
the local, real logic around it is still implemented for real (e.g. an
e-commerce "checkout" really creates a real order record; it does not
contact a real payment processor) and the gap is named plainly in
review-facing docs, never hidden.
"""
from pathlib import Path
from gen_common import AppBuilder, page_skeleton


def build_note_taking(root: Path):
    b = AppBuilder(root, "note_taking", "note taking", "0200")

    b.add_capability("0201", "List Notes", "/api/notes", "GET",
        "def handle(request):\n    return 200, {'notes': _load()}\n",
        output_fields=("notes",))

    b.add_capability("0202", "Create Note", "/api/notes", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    text = (body.get('body') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    notes = _load()\n"
        "    next_id = (max([n['id'] for n in notes], default=0)) + 1\n"
        "    note = {'id': next_id, 'title': title, 'body': text}\n"
        "    notes.append(note)\n    _save(notes)\n    return 201, note\n",
        output_fields=("id", "title", "body"), required_input=("title",),
        side_effects=("creates_record",), slot_id="note_list", selector="#note-list")

    b.add_capability("0203", "Update Note", "/api/notes/update", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    nid = body.get('id')\n"
        "    notes = _load()\n"
        "    for n in notes:\n"
        "        if n['id'] == nid:\n"
        "            n['title'] = (body.get('title') or n['title']).strip()\n"
        "            n['body'] = body.get('body', n['body'])\n"
        "            _save(notes)\n            return 200, n\n"
        "    return 404, {'error': f'no note with id {nid!r}'}\n",
        output_fields=("id", "title", "body"), required_input=("id",),
        side_effects=("updates_record",))

    b.add_capability("0204", "Delete Note", "/api/notes/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    nid = body.get('id')\n"
        "    notes = _load()\n"
        "    remaining = [n for n in notes if n['id'] != nid]\n"
        "    if len(remaining) == len(notes):\n        return 404, {'error': f'no note with id {nid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': nid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",),
        side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="note-title" placeholder="Title" data-slot="note_title">
    <textarea id="note-body" placeholder="Write your note..." data-slot="note_body" rows="3" style="flex:1"></textarea>
    <button id="add-note-btn" data-slot="add_note">Add note</button>
  </div>
</div>
<div class="card">
  <ul id="note-list" data-slot="note_list"></ul>
</div>'''
    script = '''
function refresh() {
  fetch("/api/notes").then(r => r.json()).then(data => {
    const list = document.getElementById("note-list");
    list.innerHTML = "";
    (data.notes || []).forEach(n => {
      const li = document.createElement("li");
      li.dataset.id = n.id;
      const strong = document.createElement("strong");
      strong.textContent = n.title;
      const p = document.createElement("div");
      p.textContent = n.body;
      const del = document.createElement("button");
      del.className = "danger"; del.textContent = "Delete";
      del.addEventListener("click", () => {
        fetch("/api/notes/delete", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: n.id})}).then(refresh);
      });
      li.appendChild(strong); li.appendChild(p); li.appendChild(del);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-note-btn").addEventListener("click", () => {
  const title = document.getElementById("note-title").value;
  const body = document.getElementById("note-body").value;
  if (!title.trim()) return;
  fetch("/api/notes", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, body: body})}).then(() => {
      document.getElementById("note-title").value = "";
      document.getElementById("note-body").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Notes", "", body_inner, script)
    journey = {
        "input_selector": "#note-title", "input_value": "Groceries",
        "action_selector": "#add-note-btn",
        # "text=" is Playwright's own text-matching selector engine: unlike
        # "#note-list" (which already exists, empty, before any note is
        # created and so would resolve wait_for_selector() instantly without
        # actually waiting for the async create+refresh round trip to
        # finish), this only matches once an element with this text exists,
        # so the wait is real synchronization, not a race.
        "confirm_selector": "text=Groceries", "confirm_contains": "Groceries",
    }
    b.finish(html, journey, "Real Notes", port=5001)


def build_habit_tracker(root: Path):
    b = AppBuilder(root, "habit_tracker", "habit tracker", "0300")

    b.add_capability("0301", "List Habits", "/api/habits", "GET",
        "def handle(request):\n    return 200, {'habits': _load()}\n",
        output_fields=("habits",))

    b.add_capability("0302", "Create Habit", "/api/habits", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    habits = _load()\n"
        "    next_id = (max([h['id'] for h in habits], default=0)) + 1\n"
        "    habit = {'id': next_id, 'name': name, 'streak': 0, 'log': []}\n"
        "    habits.append(habit)\n    _save(habits)\n    return 201, habit\n",
        output_fields=("id", "name", "streak"), required_input=("name",),
        side_effects=("creates_record",), slot_id="habit_list", selector="#habit-list")

    b.add_capability("0303", "Check In Habit", "/api/habits/checkin", "POST",
        "import datetime\n"
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    hid = body.get('id')\n"
        "    today = datetime.date.today().isoformat()\n"
        "    habits = _load()\n"
        "    for h in habits:\n"
        "        if h['id'] == hid:\n"
        "            if today not in h['log']:\n"
        "                h['log'].append(today)\n                h['streak'] += 1\n"
        "            _save(habits)\n            return 200, h\n"
        "    return 404, {'error': f'no habit with id {hid!r}'}\n",
        output_fields=("id", "name", "streak"), required_input=("id",),
        side_effects=("updates_record",))

    b.add_capability("0304", "Delete Habit", "/api/habits/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    hid = body.get('id')\n"
        "    habits = _load()\n"
        "    remaining = [h for h in habits if h['id'] != hid]\n"
        "    if len(remaining) == len(habits):\n        return 404, {'error': f'no habit with id {hid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': hid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",),
        side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="habit-name" placeholder="New habit (e.g. drink water)" data-slot="habit_name" style="flex:1">
    <button id="add-habit-btn" data-slot="add_habit">Add habit</button>
  </div>
</div>
<div class="card">
  <ul id="habit-list" data-slot="habit_list"></ul>
</div>'''
    script = '''
function refresh() {
  fetch("/api/habits").then(r => r.json()).then(data => {
    const list = document.getElementById("habit-list");
    list.innerHTML = "";
    (data.habits || []).forEach(h => {
      const li = document.createElement("li");
      li.className = "row"; li.dataset.id = h.id;
      const label = document.createElement("span");
      label.textContent = h.name + " -- streak: " + h.streak;
      label.style.flex = "1";
      const chk = document.createElement("button");
      chk.textContent = "Check in";
      chk.addEventListener("click", () => {
        fetch("/api/habits/checkin", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: h.id})}).then(refresh);
      });
      const del = document.createElement("button");
      del.className = "danger"; del.textContent = "Delete";
      del.addEventListener("click", () => {
        fetch("/api/habits/delete", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: h.id})}).then(refresh);
      });
      li.appendChild(label); li.appendChild(chk); li.appendChild(del);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-habit-btn").addEventListener("click", () => {
  const name = document.getElementById("habit-name").value;
  if (!name.trim()) return;
  fetch("/api/habits", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name})}).then(() => {
      document.getElementById("habit-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Habit Tracker", "", body_inner, script)
    journey = {
        "input_selector": "#habit-name", "input_value": "Drink water",
        "action_selector": "#add-habit-btn",
        "confirm_selector": "text=Drink water", "confirm_contains": "Drink water",
    }
    b.finish(html, journey, "Real Habit Tracker", port=5002)


def build_calendar(root: Path):
    b = AppBuilder(root, "calendar_and_scheduling", "calendar and scheduling", "0400")

    b.add_capability("0401", "List Events", "/api/events", "GET",
        "def handle(request):\n    return 200, {'events': _load()}\n",
        output_fields=("events",))

    b.add_capability("0402", "Create Event", "/api/events", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    start = body.get('start') or ''\n    end = body.get('end') or ''\n"
        "    events = _load()\n"
        "    next_id = (max([e['id'] for e in events], default=0)) + 1\n"
        "    ev = {'id': next_id, 'title': title, 'start': start, 'end': end}\n"
        "    events.append(ev)\n    _save(events)\n    return 201, ev\n",
        output_fields=("id", "title", "start", "end"), required_input=("title",),
        side_effects=("creates_record",), slot_id="event_list", selector="#event-list")

    b.add_capability("0403", "Delete Event", "/api/events/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    eid = body.get('id')\n    events = _load()\n"
        "    remaining = [e for e in events if e['id'] != eid]\n"
        "    if len(remaining) == len(events):\n        return 404, {'error': f'no event with id {eid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': eid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="ev-title" placeholder="Event title" data-slot="ev_title">
    <input id="ev-start" type="datetime-local" data-slot="ev_start">
    <button id="add-event-btn" data-slot="add_event">Add event</button>
  </div>
</div>
<div class="card"><ul id="event-list" data-slot="event_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/events").then(r => r.json()).then(data => {
    const list = document.getElementById("event-list");
    list.innerHTML = "";
    (data.events || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = e.title + (e.start ? " -- " + e.start : "");
      const del = document.createElement("button");
      del.className = "danger"; del.textContent = "Delete";
      del.style.marginLeft = "8px";
      del.addEventListener("click", () => {
        fetch("/api/events/delete", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: e.id})}).then(refresh);
      });
      li.appendChild(del);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-event-btn").addEventListener("click", () => {
  const title = document.getElementById("ev-title").value;
  const start = document.getElementById("ev-start").value;
  if (!title.trim()) return;
  fetch("/api/events", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, start: start})}).then(() => {
      document.getElementById("ev-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Calendar", "", body_inner, script)
    journey = {
        "input_selector": "#ev-title", "input_value": "Team Standup",
        "action_selector": "#add-event-btn",
        "confirm_selector": "text=Team Standup", "confirm_contains": "Team Standup",
    }
    b.finish(html, journey, "Real Calendar", port=5003)


def build_expense_tracker(root: Path):
    b = AppBuilder(root, "expense_tracker", "expense tracker", "0500")

    b.add_capability("0501", "List Expenses", "/api/expenses", "GET",
        "def handle(request):\n    return 200, {'expenses': _load()}\n",
        output_fields=("expenses",))

    b.add_capability("0502", "Create Expense", "/api/expenses", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    description = (body.get('description') or '').strip()\n"
        "    if not description:\n        return 400, {'error': 'description is required'}\n"
        "    try:\n        amount = float(body.get('amount', 0) or 0)\n    except (TypeError, ValueError):\n        amount = 0.0\n"
        "    category = body.get('category') or 'general'\n"
        "    expenses = _load()\n"
        "    next_id = (max([x['id'] for x in expenses], default=0)) + 1\n"
        "    exp = {'id': next_id, 'description': description, 'amount': amount, 'category': category}\n"
        "    expenses.append(exp)\n    _save(expenses)\n    return 201, exp\n",
        output_fields=("id", "description", "amount", "category"), required_input=("description",),
        side_effects=("creates_record",), slot_id="expense_list", selector="#expense-list")

    b.add_capability("0503", "Delete Expense", "/api/expenses/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    xid = body.get('id')\n    expenses = _load()\n"
        "    remaining = [x for x in expenses if x['id'] != xid]\n"
        "    if len(remaining) == len(expenses):\n        return 404, {'error': f'no expense with id {xid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': xid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    b.add_capability("0504", "Total Expenses", "/api/expenses/total", "GET",
        "def handle(request):\n"
        "    expenses = _load()\n    total = sum(x.get('amount', 0) for x in expenses)\n"
        "    return 200, {'total': total}\n",
        output_fields=("total",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="exp-desc" placeholder="Description" data-slot="exp_desc">
    <input id="exp-amount" type="number" step="0.01" placeholder="Amount" data-slot="exp_amount">
    <button id="add-expense-btn" data-slot="add_expense">Add expense</button>
  </div>
</div>
<div class="card"><div id="exp-total"></div><ul id="expense-list" data-slot="expense_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/expenses").then(r => r.json()).then(data => {
    const list = document.getElementById("expense-list");
    list.innerHTML = "";
    (data.expenses || []).forEach(x => {
      const li = document.createElement("li");
      li.textContent = x.description + " -- $" + x.amount;
      list.appendChild(li);
    });
  });
  fetch("/api/expenses/total").then(r => r.json()).then(d => {
    document.getElementById("exp-total").textContent = "Total: $" + d.total;
  });
}
document.getElementById("add-expense-btn").addEventListener("click", () => {
  const description = document.getElementById("exp-desc").value;
  const amount = document.getElementById("exp-amount").value;
  if (!description.trim()) return;
  fetch("/api/expenses", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({description: description, amount: amount})}).then(() => {
      document.getElementById("exp-desc").value = "";
      document.getElementById("exp-amount").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Expense Tracker", "", body_inner, script)
    journey = {
        "input_selector": "#exp-desc", "input_value": "Coffee",
        "action_selector": "#add-expense-btn",
        "confirm_selector": "text=Coffee", "confirm_contains": "Coffee",
    }
    b.finish(html, journey, "Real Expense Tracker", port=5004)


def build_invoicing(root: Path):
    b = AppBuilder(root, "invoicing", "invoicing", "0600")

    b.add_capability("0601", "List Invoices", "/api/invoices", "GET",
        "def handle(request):\n    return 200, {'invoices': _load()}\n",
        output_fields=("invoices",))

    b.add_capability("0602", "Create Invoice", "/api/invoices", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    client = (body.get('client') or '').strip()\n"
        "    if not client:\n        return 400, {'error': 'client is required'}\n"
        "    try:\n        amount = float(body.get('amount', 0) or 0)\n    except (TypeError, ValueError):\n        amount = 0.0\n"
        "    invoices = _load()\n"
        "    next_id = (max([i['id'] for i in invoices], default=0)) + 1\n"
        "    inv = {'id': next_id, 'client': client, 'amount': amount, 'status': 'draft'}\n"
        "    invoices.append(inv)\n    _save(invoices)\n    return 201, inv\n",
        output_fields=("id", "client", "amount", "status"), required_input=("client",),
        side_effects=("creates_record",), slot_id="invoice_list", selector="#invoice-list")

    b.add_capability("0603", "Mark Invoice Paid", "/api/invoices/pay", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    iid = body.get('id')\n    invoices = _load()\n"
        "    for i in invoices:\n"
        "        if i['id'] == iid:\n            i['status'] = 'paid'\n            _save(invoices)\n            return 200, i\n"
        "    return 404, {'error': f'no invoice with id {iid!r}'}\n",
        output_fields=("id", "client", "amount", "status"), required_input=("id",),
        side_effects=("updates_record",))

    b.add_capability("0604", "Delete Invoice", "/api/invoices/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    iid = body.get('id')\n    invoices = _load()\n"
        "    remaining = [i for i in invoices if i['id'] != iid]\n"
        "    if len(remaining) == len(invoices):\n        return 404, {'error': f'no invoice with id {iid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': iid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="inv-client" placeholder="Client name" data-slot="inv_client">
    <input id="inv-amount" type="number" step="0.01" placeholder="Amount" data-slot="inv_amount">
    <button id="add-invoice-btn" data-slot="add_invoice">Create invoice</button>
  </div>
</div>
<div class="card"><ul id="invoice-list" data-slot="invoice_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/invoices").then(r => r.json()).then(data => {
    const list = document.getElementById("invoice-list");
    list.innerHTML = "";
    (data.invoices || []).forEach(i => {
      const li = document.createElement("li");
      li.textContent = i.client + " -- $" + i.amount + " (" + i.status + ")";
      const pay = document.createElement("button");
      pay.textContent = "Mark paid"; pay.style.marginLeft = "8px";
      pay.addEventListener("click", () => {
        fetch("/api/invoices/pay", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: i.id})}).then(refresh);
      });
      li.appendChild(pay);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-invoice-btn").addEventListener("click", () => {
  const client = document.getElementById("inv-client").value;
  const amount = document.getElementById("inv-amount").value;
  if (!client.trim()) return;
  fetch("/api/invoices", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({client: client, amount: amount})}).then(() => {
      document.getElementById("inv-client").value = "";
      document.getElementById("inv-amount").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Invoicing", "", body_inner, script)
    journey = {
        "input_selector": "#inv-client", "input_value": "Acme Corp",
        "action_selector": "#add-invoice-btn",
        "confirm_selector": "text=Acme Corp", "confirm_contains": "Acme Corp",
    }
    b.finish(html, journey, "Real Invoicing", port=5005)


def build_accounting_ledger(root: Path):
    b = AppBuilder(root, "accounting_ledger", "accounting ledger", "0700")

    b.add_capability("0701", "List Entries", "/api/entries", "GET",
        "def handle(request):\n    return 200, {'entries': _load()}\n",
        output_fields=("entries",))

    b.add_capability("0702", "Create Entry", "/api/entries", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    description = (body.get('description') or '').strip()\n"
        "    if not description:\n        return 400, {'error': 'description is required'}\n"
        "    try:\n        amount = float(body.get('amount', 0) or 0)\n    except (TypeError, ValueError):\n        amount = 0.0\n"
        "    entry_type = body.get('type') if body.get('type') in ('debit', 'credit') else 'debit'\n"
        "    entries = _load()\n"
        "    next_id = (max([e['id'] for e in entries], default=0)) + 1\n"
        "    entry = {'id': next_id, 'description': description, 'amount': amount, 'type': entry_type}\n"
        "    entries.append(entry)\n    _save(entries)\n    return 201, entry\n",
        output_fields=("id", "description", "amount", "type"), required_input=("description",),
        side_effects=("creates_record",), slot_id="entry_list", selector="#entry-list")

    b.add_capability("0703", "Delete Entry", "/api/entries/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    eid = body.get('id')\n    entries = _load()\n"
        "    remaining = [e for e in entries if e['id'] != eid]\n"
        "    if len(remaining) == len(entries):\n        return 404, {'error': f'no entry with id {eid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': eid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    b.add_capability("0704", "Ledger Balance", "/api/entries/balance", "GET",
        "def handle(request):\n"
        "    entries = _load()\n"
        "    credit = sum(e.get('amount', 0) for e in entries if e.get('type') == 'credit')\n"
        "    debit = sum(e.get('amount', 0) for e in entries if e.get('type') == 'debit')\n"
        "    return 200, {'balance': credit - debit}\n",
        output_fields=("balance",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="entry-desc" placeholder="Description" data-slot="entry_desc">
    <input id="entry-amount" type="number" step="0.01" placeholder="Amount" data-slot="entry_amount">
    <select id="entry-type"><option value="debit">Debit</option><option value="credit">Credit</option></select>
    <button id="add-entry-btn" data-slot="add_entry">Add entry</button>
  </div>
</div>
<div class="card"><div id="ledger-balance"></div><ul id="entry-list" data-slot="entry_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/entries").then(r => r.json()).then(data => {
    const list = document.getElementById("entry-list");
    list.innerHTML = "";
    (data.entries || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = e.description + " -- $" + e.amount + " (" + e.type + ")";
      list.appendChild(li);
    });
  });
  fetch("/api/entries/balance").then(r => r.json()).then(d => {
    document.getElementById("ledger-balance").textContent = "Balance: $" + d.balance;
  });
}
document.getElementById("add-entry-btn").addEventListener("click", () => {
  const description = document.getElementById("entry-desc").value;
  const amount = document.getElementById("entry-amount").value;
  const type = document.getElementById("entry-type").value;
  if (!description.trim()) return;
  fetch("/api/entries", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({description: description, amount: amount, type: type})}).then(() => {
      document.getElementById("entry-desc").value = "";
      document.getElementById("entry-amount").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Accounting Ledger", "", body_inner, script)
    journey = {
        "input_selector": "#entry-desc", "input_value": "Client Payment",
        "action_selector": "#add-entry-btn",
        "confirm_selector": "text=Client Payment", "confirm_contains": "Client Payment",
    }
    b.finish(html, journey, "Real Accounting Ledger", port=5006)


def build_crm(root: Path):
    b = AppBuilder(root, "crm", "CRM", "0800")

    b.add_capability("0801", "List Contacts", "/api/contacts", "GET",
        "def handle(request):\n    return 200, {'contacts': _load()}\n",
        output_fields=("contacts",))

    b.add_capability("0802", "Create Contact", "/api/contacts", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    email = body.get('email') or ''\n"
        "    contacts = _load()\n"
        "    next_id = (max([c['id'] for c in contacts], default=0)) + 1\n"
        "    contact = {'id': next_id, 'name': name, 'email': email, 'stage': 'lead'}\n"
        "    contacts.append(contact)\n    _save(contacts)\n    return 201, contact\n",
        output_fields=("id", "name", "email", "stage"), required_input=("name",),
        side_effects=("creates_record",), slot_id="contact_list", selector="#contact-list")

    b.add_capability("0803", "Update Contact Stage", "/api/contacts/stage", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    cid = body.get('id')\n    stage = body.get('stage') or 'lead'\n"
        "    contacts = _load()\n"
        "    for c in contacts:\n"
        "        if c['id'] == cid:\n            c['stage'] = stage\n            _save(contacts)\n            return 200, c\n"
        "    return 404, {'error': f'no contact with id {cid!r}'}\n",
        output_fields=("id", "name", "email", "stage"), required_input=("id",),
        side_effects=("updates_record",))

    b.add_capability("0804", "Delete Contact", "/api/contacts/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    cid = body.get('id')\n    contacts = _load()\n"
        "    remaining = [c for c in contacts if c['id'] != cid]\n"
        "    if len(remaining) == len(contacts):\n        return 404, {'error': f'no contact with id {cid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': cid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="c-name" placeholder="Name" data-slot="c_name">
    <input id="c-email" placeholder="Email" data-slot="c_email">
    <button id="add-contact-btn" data-slot="add_contact">Add contact</button>
  </div>
</div>
<div class="card"><ul id="contact-list" data-slot="contact_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/contacts").then(r => r.json()).then(data => {
    const list = document.getElementById("contact-list");
    list.innerHTML = "";
    (data.contacts || []).forEach(c => {
      const li = document.createElement("li");
      li.textContent = c.name + " (" + c.stage + ")";
      const sel = document.createElement("select");
      ["lead", "qualified", "won", "lost"].forEach(s => {
        const opt = document.createElement("option"); opt.value = s; opt.textContent = s;
        if (s === c.stage) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener("change", () => {
        fetch("/api/contacts/stage", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: c.id, stage: sel.value})}).then(refresh);
      });
      li.appendChild(sel);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-contact-btn").addEventListener("click", () => {
  const name = document.getElementById("c-name").value;
  const email = document.getElementById("c-email").value;
  if (!name.trim()) return;
  fetch("/api/contacts", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name, email: email})}).then(() => {
      document.getElementById("c-name").value = "";
      document.getElementById("c-email").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("CRM", "", body_inner, script)
    journey = {
        "input_selector": "#c-name", "input_value": "Jane Doe",
        "action_selector": "#add-contact-btn",
        "confirm_selector": "text=Jane Doe", "confirm_contains": "Jane Doe",
    }
    b.finish(html, journey, "Real CRM", port=5007)


def build_helpdesk(root: Path):
    b = AppBuilder(root, "helpdesk_ticketing", "helpdesk ticketing", "0900")

    b.add_capability("0901", "List Tickets", "/api/tickets", "GET",
        "def handle(request):\n    return 200, {'tickets': _load()}\n",
        output_fields=("tickets",))

    b.add_capability("0902", "Create Ticket", "/api/tickets", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    subject = (body.get('subject') or '').strip()\n"
        "    if not subject:\n        return 400, {'error': 'subject is required'}\n"
        "    tickets = _load()\n"
        "    next_id = (max([t['id'] for t in tickets], default=0)) + 1\n"
        "    ticket = {'id': next_id, 'subject': subject, 'status': 'open'}\n"
        "    tickets.append(ticket)\n    _save(tickets)\n    return 201, ticket\n",
        output_fields=("id", "subject", "status"), required_input=("subject",),
        side_effects=("creates_record",), slot_id="ticket_list", selector="#ticket-list")

    b.add_capability("0903", "Close Ticket", "/api/tickets/close", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    tid = body.get('id')\n    tickets = _load()\n"
        "    for t in tickets:\n"
        "        if t['id'] == tid:\n            t['status'] = 'closed'\n            _save(tickets)\n            return 200, t\n"
        "    return 404, {'error': f'no ticket with id {tid!r}'}\n",
        output_fields=("id", "subject", "status"), required_input=("id",),
        side_effects=("updates_record",))

    b.add_capability("0904", "Delete Ticket", "/api/tickets/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    tid = body.get('id')\n    tickets = _load()\n"
        "    remaining = [t for t in tickets if t['id'] != tid]\n"
        "    if len(remaining) == len(tickets):\n        return 404, {'error': f'no ticket with id {tid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': tid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="t-subject" placeholder="Ticket subject" data-slot="t_subject">
    <button id="add-ticket-btn" data-slot="add_ticket">Create ticket</button>
  </div>
</div>
<div class="card"><ul id="ticket-list" data-slot="ticket_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/tickets").then(r => r.json()).then(data => {
    const list = document.getElementById("ticket-list");
    list.innerHTML = "";
    (data.tickets || []).forEach(t => {
      const li = document.createElement("li");
      li.textContent = t.subject + " (" + t.status + ")";
      if (t.status === "open") {
        const close = document.createElement("button");
        close.textContent = "Close"; close.style.marginLeft = "8px";
        close.addEventListener("click", () => {
          fetch("/api/tickets/close", {method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: t.id})}).then(refresh);
        });
        li.appendChild(close);
      }
      list.appendChild(li);
    });
  });
}
document.getElementById("add-ticket-btn").addEventListener("click", () => {
  const subject = document.getElementById("t-subject").value;
  if (!subject.trim()) return;
  fetch("/api/tickets", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({subject: subject})}).then(() => {
      document.getElementById("t-subject").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Helpdesk", "", body_inner, script)
    journey = {
        "input_selector": "#t-subject", "input_value": "Login broken",
        "action_selector": "#add-ticket-btn",
        "confirm_selector": "text=Login broken", "confirm_contains": "Login broken",
    }
    b.finish(html, journey, "Real Helpdesk", port=5008)


def build_payroll(root: Path):
    b = AppBuilder(root, "payroll", "payroll", "1000")

    b.add_capability("1001", "List Employees", "/api/employees", "GET",
        "def handle(request):\n    return 200, {'employees': _load()}\n",
        output_fields=("employees",), data_filename="employees.json")

    b.add_capability("1002", "Add Employee", "/api/employees", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    try:\n        salary = float(body.get('salary', 0) or 0)\n    except (TypeError, ValueError):\n        salary = 0.0\n"
        "    employees = _load()\n"
        "    next_id = (max([e['id'] for e in employees], default=0)) + 1\n"
        "    emp = {'id': next_id, 'name': name, 'salary': salary}\n"
        "    employees.append(emp)\n    _save(employees)\n    return 201, emp\n",
        output_fields=("id", "name", "salary"), required_input=("name",),
        side_effects=("creates_record",), slot_id="employee_list", selector="#employee-list",
        data_filename="employees.json")

    b.add_capability("1003", "Run Payroll", "/api/payroll/run", "POST",
        "import json\nfrom pathlib import Path\n"
        "EMP_FILE = Path(__file__).resolve().parents[2] / 'data' / 'employees.json'\n"
        "def _load_employees():\n"
        "    if not EMP_FILE.is_file():\n        return []\n"
        "    try:\n        return json.loads(EMP_FILE.read_text(encoding='utf-8'))\n    except Exception:\n        return []\n"
        "def handle(request):\n"
        "    employees = _load_employees()\n    records = _load()\n"
        "    next_id = (max([r['id'] for r in records], default=0))\n    created = 0\n"
        "    for e in employees:\n"
        "        next_id += 1\n        gross = e.get('salary', 0)\n        net = round(gross * 0.8, 2)\n"
        "        records.append({'id': next_id, 'employee_id': e['id'], 'gross': gross, 'net': net})\n"
        "        created += 1\n"
        "    _save(records)\n    return 200, {'created': created}\n",
        output_fields=("created",), data_filename="pay_records.json")

    b.add_capability("1004", "List Pay Records", "/api/payroll/records", "GET",
        "def handle(request):\n    return 200, {'records': _load()}\n",
        output_fields=("records",), data_filename="pay_records.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="emp-name" placeholder="Employee name" data-slot="emp_name">
    <input id="emp-salary" type="number" step="0.01" placeholder="Salary" data-slot="emp_salary">
    <button id="add-employee-btn" data-slot="add_employee">Add employee</button>
    <button id="run-payroll-btn">Run payroll</button>
  </div>
</div>
<div class="card"><ul id="employee-list" data-slot="employee_list"></ul></div>
<div class="card"><ul id="pay-records"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/employees").then(r => r.json()).then(data => {
    const list = document.getElementById("employee-list");
    list.innerHTML = "";
    (data.employees || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = e.name + " -- $" + e.salary;
      list.appendChild(li);
    });
  });
  fetch("/api/payroll/records").then(r => r.json()).then(data => {
    const list = document.getElementById("pay-records");
    list.innerHTML = "";
    (data.records || []).forEach(r => {
      const li = document.createElement("li");
      li.textContent = "employee " + r.employee_id + ": net $" + r.net;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-employee-btn").addEventListener("click", () => {
  const name = document.getElementById("emp-name").value;
  const salary = document.getElementById("emp-salary").value;
  if (!name.trim()) return;
  fetch("/api/employees", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name, salary: salary})}).then(() => {
      document.getElementById("emp-name").value = "";
      refresh();
    });
});
document.getElementById("run-payroll-btn").addEventListener("click", () => {
  fetch("/api/payroll/run", {method: "POST"}).then(refresh);
});
refresh();
'''
    html = page_skeleton("Payroll", "", body_inner, script)
    journey = {
        "input_selector": "#emp-name", "input_value": "Alex Kim",
        "action_selector": "#add-employee-btn",
        "confirm_selector": "text=Alex Kim", "confirm_contains": "Alex Kim",
    }
    b.finish(html, journey, "Real Payroll", port=5010)


def build_project_management(root: Path):
    b = AppBuilder(root, "project_management", "project management", "1100")

    b.add_capability("1101", "List Tasks", "/api/tasks", "GET",
        "def handle(request):\n    return 200, {'tasks': _load()}\n",
        output_fields=("tasks",))

    b.add_capability("1102", "Create Task", "/api/tasks", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    tasks = _load()\n"
        "    next_id = (max([t['id'] for t in tasks], default=0)) + 1\n"
        "    task = {'id': next_id, 'title': title, 'status': 'todo'}\n"
        "    tasks.append(task)\n    _save(tasks)\n    return 201, task\n",
        output_fields=("id", "title", "status"), required_input=("title",),
        side_effects=("creates_record",), slot_id="task_list", selector="#task-list")

    b.add_capability("1103", "Update Task Status", "/api/tasks/status", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    tid = body.get('id')\n    status = body.get('status') or 'todo'\n"
        "    tasks = _load()\n"
        "    for t in tasks:\n"
        "        if t['id'] == tid:\n            t['status'] = status\n            _save(tasks)\n            return 200, t\n"
        "    return 404, {'error': f'no task with id {tid!r}'}\n",
        output_fields=("id", "title", "status"), required_input=("id",),
        side_effects=("updates_record",))

    b.add_capability("1104", "Delete Task", "/api/tasks/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    tid = body.get('id')\n    tasks = _load()\n"
        "    remaining = [t for t in tasks if t['id'] != tid]\n"
        "    if len(remaining) == len(tasks):\n        return 404, {'error': f'no task with id {tid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': tid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="task-title" placeholder="Task title" data-slot="task_title">
    <button id="add-task-btn" data-slot="add_task">Add task</button>
  </div>
</div>
<div class="card"><ul id="task-list" data-slot="task_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/tasks").then(r => r.json()).then(data => {
    const list = document.getElementById("task-list");
    list.innerHTML = "";
    (data.tasks || []).forEach(t => {
      const li = document.createElement("li");
      li.textContent = t.title + " (" + t.status + ")";
      const sel = document.createElement("select");
      ["todo", "doing", "done"].forEach(s => {
        const opt = document.createElement("option"); opt.value = s; opt.textContent = s;
        if (s === t.status) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener("change", () => {
        fetch("/api/tasks/status", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: t.id, status: sel.value})}).then(refresh);
      });
      li.appendChild(sel);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-task-btn").addEventListener("click", () => {
  const title = document.getElementById("task-title").value;
  if (!title.trim()) return;
  fetch("/api/tasks", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => {
      document.getElementById("task-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Project Management", "", body_inner, script)
    journey = {
        "input_selector": "#task-title", "input_value": "Design homepage",
        "action_selector": "#add-task-btn",
        "confirm_selector": "text=Design homepage", "confirm_contains": "Design homepage",
    }
    b.finish(html, journey, "Real Project Management", port=5011)


def build_team_chat(root: Path):
    b = AppBuilder(root, "team_chat", "team chat", "1200")

    b.add_capability("1201", "List Messages", "/api/messages", "GET",
        "def handle(request):\n    return 200, {'messages': _load()}\n",
        output_fields=("messages",))

    b.add_capability("1202", "Post Message", "/api/messages", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    text = (body.get('text') or '').strip()\n"
        "    if not text:\n        return 400, {'error': 'text is required'}\n"
        "    author = body.get('author') or 'You'\n"
        "    messages = _load()\n"
        "    next_id = (max([m['id'] for m in messages], default=0)) + 1\n"
        "    msg = {'id': next_id, 'author': author, 'text': text}\n"
        "    messages.append(msg)\n    _save(messages)\n    return 201, msg\n",
        output_fields=("id", "author", "text"), required_input=("text",),
        side_effects=("creates_record",), slot_id="message_list", selector="#message-list")

    b.add_capability("1203", "Delete Message", "/api/messages/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    mid = body.get('id')\n    messages = _load()\n"
        "    remaining = [m for m in messages if m['id'] != mid]\n"
        "    if len(remaining) == len(messages):\n        return 404, {'error': f'no message with id {mid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': mid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="msg-text" placeholder="Type a message" data-slot="msg_text" style="flex:1">
    <button id="send-msg-btn" data-slot="send_msg">Send</button>
  </div>
</div>
<div class="card"><ul id="message-list" data-slot="message_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/messages").then(r => r.json()).then(data => {
    const list = document.getElementById("message-list");
    list.innerHTML = "";
    (data.messages || []).forEach(m => {
      const li = document.createElement("li");
      li.textContent = m.author + ": " + m.text;
      list.appendChild(li);
    });
  });
}
document.getElementById("send-msg-btn").addEventListener("click", () => {
  const text = document.getElementById("msg-text").value;
  if (!text.trim()) return;
  fetch("/api/messages", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: text})}).then(() => {
      document.getElementById("msg-text").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Team Chat", "", body_inner, script)
    journey = {
        "input_selector": "#msg-text", "input_value": "Hello team",
        "action_selector": "#send-msg-btn",
        "confirm_selector": "text=Hello team", "confirm_contains": "Hello team",
    }
    b.finish(html, journey, "Real Team Chat", port=5012)


def build_spreadsheet(root: Path):
    b = AppBuilder(root, "spreadsheet", "spreadsheet", "1700")

    b.add_capability("1701", "List Cells", "/api/cells", "GET",
        "def handle(request):\n    return 200, {'cells': _load()}\n",
        output_fields=("cells",))

    b.add_capability("1702", "Set Cell", "/api/cells/set", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    row = body.get('row')\n    col = body.get('col')\n"
        "    if row is None or col is None:\n        return 400, {'error': 'row and col are required'}\n"
        "    value = body.get('value', '')\n"
        "    cells = _load()\n"
        "    for c in cells:\n"
        "        if c['row'] == row and c['col'] == col:\n            c['value'] = value\n            _save(cells)\n            return 200, c\n"
        "    cell = {'row': row, 'col': col, 'value': value}\n"
        "    cells.append(cell)\n    _save(cells)\n    return 201, cell\n",
        output_fields=("row", "col", "value"), required_input=("row", "col"),
        side_effects=("creates_record",), slot_id="cell_list", selector="#cell-list")

    row_opts = "".join(f'<option value="{i}">{i}</option>' for i in range(3))
    body_inner = f'''<div class="card">
  <div class="row">
    <label>Row <select id="cell-row" data-slot="cell_row">{row_opts}</select></label>
    <label>Col <select id="cell-col" data-slot="cell_col">{row_opts}</select></label>
    <input id="cell-value" placeholder="Value" data-slot="cell_value">
    <button id="set-cell-btn" data-slot="set_cell">Set cell</button>
  </div>
</div>
<div class="card"><ul id="cell-list" data-slot="cell_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/cells").then(r => r.json()).then(data => {
    const list = document.getElementById("cell-list");
    list.innerHTML = "";
    (data.cells || []).forEach(c => {
      const li = document.createElement("li");
      li.textContent = "R" + c.row + "C" + c.col + " = " + c.value;
      list.appendChild(li);
    });
  });
}
document.getElementById("set-cell-btn").addEventListener("click", () => {
  const row = document.getElementById("cell-row").value;
  const col = document.getElementById("cell-col").value;
  const value = document.getElementById("cell-value").value;
  if (row === "" || col === "") return;
  fetch("/api/cells/set", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({row: row, col: col, value: value})}).then(refresh);
});
refresh();
'''
    html = page_skeleton("Spreadsheet", "", body_inner, script)
    journey = {
        "input_selector": "#cell-value", "input_value": "42",
        "action_selector": "#set-cell-btn",
        "confirm_selector": "text=42", "confirm_contains": "42",
    }
    b.finish(html, journey, "Real Spreadsheet", port=5017)


def build_form_builder(root: Path):
    b = AppBuilder(root, "form_builder_and_survey", "form builder and survey", "1800")

    b.add_capability("1801", "List Responses", "/api/responses", "GET",
        "def handle(request):\n    return 200, {'responses': _load()}\n",
        output_fields=("responses",))

    b.add_capability("1802", "Submit Response", "/api/responses", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    answer = (body.get('answer') or '').strip()\n"
        "    if not answer:\n        return 400, {'error': 'answer is required'}\n"
        "    responses = _load()\n"
        "    next_id = (max([r['id'] for r in responses], default=0)) + 1\n"
        "    resp = {'id': next_id, 'answer': answer}\n"
        "    responses.append(resp)\n    _save(responses)\n    return 201, resp\n",
        output_fields=("id", "answer"), required_input=("answer",),
        side_effects=("creates_record",), slot_id="response_list", selector="#response-list")

    body_inner = '''<div class="card">
  <p><strong>Survey:</strong> What could we improve?</p>
  <div class="row">
    <input id="survey-answer" placeholder="Your answer" data-slot="survey_answer" style="flex:1">
    <button id="submit-response-btn" data-slot="submit_response">Submit</button>
  </div>
</div>
<div class="card"><ul id="response-list" data-slot="response_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/responses").then(r => r.json()).then(data => {
    const list = document.getElementById("response-list");
    list.innerHTML = "";
    (data.responses || []).forEach(r => {
      const li = document.createElement("li");
      li.textContent = r.answer;
      list.appendChild(li);
    });
  });
}
document.getElementById("submit-response-btn").addEventListener("click", () => {
  const answer = document.getElementById("survey-answer").value;
  if (!answer.trim()) return;
  fetch("/api/responses", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({answer: answer})}).then(() => {
      document.getElementById("survey-answer").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Survey", "", body_inner, script)
    journey = {
        "input_selector": "#survey-answer", "input_value": "Faster loading",
        "action_selector": "#submit-response-btn",
        "confirm_selector": "text=Faster loading", "confirm_contains": "Faster loading",
    }
    b.finish(html, journey, "Real Survey", port=5018)


def build_parcel_tracking(root: Path):
    b = AppBuilder(root, "parcel_tracking", "parcel tracking", "2400")

    b.add_capability("2401", "List Parcels", "/api/parcels", "GET",
        "def handle(request):\n    return 200, {'parcels': _load()}\n",
        output_fields=("parcels",))

    b.add_capability("2402", "Create Parcel", "/api/parcels", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    tracking_no = (body.get('tracking_no') or '').strip()\n"
        "    if not tracking_no:\n        return 400, {'error': 'tracking_no is required'}\n"
        "    parcels = _load()\n"
        "    next_id = (max([p['id'] for p in parcels], default=0)) + 1\n"
        "    parcel = {'id': next_id, 'tracking_no': tracking_no, 'status': 'created', 'history': ['created']}\n"
        "    parcels.append(parcel)\n    _save(parcels)\n    return 201, parcel\n",
        output_fields=("id", "tracking_no", "status"), required_input=("tracking_no",),
        side_effects=("creates_record",), slot_id="parcel_list", selector="#parcel-list")

    b.add_capability("2403", "Update Parcel Status", "/api/parcels/status", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    pid = body.get('id')\n    status = body.get('status') or 'created'\n"
        "    parcels = _load()\n"
        "    for p in parcels:\n"
        "        if p['id'] == pid:\n"
        "            p['status'] = status\n            p.setdefault('history', []).append(status)\n"
        "            _save(parcels)\n            return 200, p\n"
        "    return 404, {'error': f'no parcel with id {pid!r}'}\n",
        output_fields=("id", "tracking_no", "status"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="parcel-tracking" placeholder="Tracking number" data-slot="parcel_tracking">
    <button id="add-parcel-btn" data-slot="add_parcel">Create parcel</button>
  </div>
</div>
<div class="card"><ul id="parcel-list" data-slot="parcel_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/parcels").then(r => r.json()).then(data => {
    const list = document.getElementById("parcel-list");
    list.innerHTML = "";
    (data.parcels || []).forEach(p => {
      const li = document.createElement("li");
      li.textContent = p.tracking_no + " (" + p.status + ")";
      const sel = document.createElement("select");
      ["created", "in_transit", "delivered"].forEach(s => {
        const opt = document.createElement("option"); opt.value = s; opt.textContent = s;
        if (s === p.status) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener("change", () => {
        fetch("/api/parcels/status", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: p.id, status: sel.value})}).then(refresh);
      });
      li.appendChild(sel);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-parcel-btn").addEventListener("click", () => {
  const tracking_no = document.getElementById("parcel-tracking").value;
  if (!tracking_no.trim()) return;
  fetch("/api/parcels", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({tracking_no: tracking_no})}).then(() => {
      document.getElementById("parcel-tracking").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Parcel Tracking", "", body_inner, script)
    journey = {
        "input_selector": "#parcel-tracking", "input_value": "PKG123456",
        "action_selector": "#add-parcel-btn",
        "confirm_selector": "text=PKG123456", "confirm_contains": "PKG123456",
    }
    b.finish(html, journey, "Real Parcel Tracking", port=5024)


def build_appointment_booking(root: Path):
    b = AppBuilder(root, "appointment_booking", "appointment booking", "2500")

    b.add_capability("2501", "List Appointments", "/api/appointments", "GET",
        "def handle(request):\n    return 200, {'appointments': _load()}\n",
        output_fields=("appointments",))

    b.add_capability("2502", "Book Appointment", "/api/appointments", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    start = body.get('start') or ''\n"
        "    appts = _load()\n"
        "    next_id = (max([a['id'] for a in appts], default=0)) + 1\n"
        "    appt = {'id': next_id, 'name': name, 'start': start, 'status': 'booked'}\n"
        "    appts.append(appt)\n    _save(appts)\n    return 201, appt\n",
        output_fields=("id", "name", "start", "status"), required_input=("name",),
        side_effects=("creates_record",), slot_id="appointment_list", selector="#appointment-list")

    b.add_capability("2503", "Cancel Appointment", "/api/appointments/cancel", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    aid = body.get('id')\n    appts = _load()\n"
        "    for a in appts:\n"
        "        if a['id'] == aid:\n            a['status'] = 'cancelled'\n            _save(appts)\n            return 200, a\n"
        "    return 404, {'error': f'no appointment with id {aid!r}'}\n",
        output_fields=("id", "name", "status"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="appt-name" placeholder="Your name" data-slot="appt_name">
    <input id="appt-start" type="datetime-local" data-slot="appt_start">
    <button id="book-appt-btn" data-slot="book_appt">Book</button>
  </div>
</div>
<div class="card"><ul id="appointment-list" data-slot="appointment_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/appointments").then(r => r.json()).then(data => {
    const list = document.getElementById("appointment-list");
    list.innerHTML = "";
    (data.appointments || []).forEach(a => {
      const li = document.createElement("li");
      li.textContent = a.name + " (" + a.status + ")";
      if (a.status === "booked") {
        const cancel = document.createElement("button");
        cancel.className = "danger"; cancel.textContent = "Cancel"; cancel.style.marginLeft = "8px";
        cancel.addEventListener("click", () => {
          fetch("/api/appointments/cancel", {method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: a.id})}).then(refresh);
        });
        li.appendChild(cancel);
      }
      list.appendChild(li);
    });
  });
}
document.getElementById("book-appt-btn").addEventListener("click", () => {
  const name = document.getElementById("appt-name").value;
  const start = document.getElementById("appt-start").value;
  if (!name.trim()) return;
  fetch("/api/appointments", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name, start: start})}).then(() => {
      document.getElementById("appt-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Appointment Booking", "", body_inner, script)
    journey = {
        "input_selector": "#appt-name", "input_value": "Alex Kim",
        "action_selector": "#book-appt-btn",
        "confirm_selector": "text=Alex Kim", "confirm_contains": "Alex Kim",
    }
    b.finish(html, journey, "Real Appointment Booking", port=5025)


def build_event_ticketing(root: Path):
    b = AppBuilder(root, "event_ticketing", "event ticketing", "2700")

    b.add_capability("2701", "List Events", "/api/events", "GET",
        "def handle(request):\n    return 200, {'events': _load()}\n",
        output_fields=("events",))

    b.add_capability("2702", "Create Event", "/api/events", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    try:\n        capacity = int(body.get('capacity', 100) or 100)\n    except (TypeError, ValueError):\n        capacity = 100\n"
        "    events = _load()\n"
        "    next_id = (max([e['id'] for e in events], default=0)) + 1\n"
        "    ev = {'id': next_id, 'title': title, 'capacity': capacity, 'sold': 0}\n"
        "    events.append(ev)\n    _save(events)\n    return 201, ev\n",
        output_fields=("id", "title", "capacity", "sold"), required_input=("title",),
        side_effects=("creates_record",), slot_id="event_list", selector="#event-list")

    b.add_capability("2703", "Buy Ticket", "/api/events/buy", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    eid = body.get('id')\n    events = _load()\n"
        "    for e in events:\n"
        "        if e['id'] == eid:\n"
        "            if e['sold'] >= e['capacity']:\n                return 400, {'error': 'sold out'}\n"
        "            e['sold'] += 1\n            _save(events)\n            return 200, e\n"
        "    return 404, {'error': f'no event with id {eid!r}'}\n",
        output_fields=("id", "title", "sold"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="ev-title" placeholder="Event title" data-slot="etk_title">
    <input id="ev-capacity" type="number" placeholder="Capacity" data-slot="etk_capacity">
    <button id="add-event-btn" data-slot="add_event">Create event</button>
  </div>
</div>
<div class="card"><ul id="event-list" data-slot="event_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/events").then(r => r.json()).then(data => {
    const list = document.getElementById("event-list");
    list.innerHTML = "";
    (data.events || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = e.title + " -- " + e.sold + "/" + e.capacity + " sold";
      const buy = document.createElement("button");
      buy.textContent = "Buy ticket"; buy.style.marginLeft = "8px";
      buy.addEventListener("click", () => {
        fetch("/api/events/buy", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: e.id})}).then(refresh);
      });
      li.appendChild(buy);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-event-btn").addEventListener("click", () => {
  const title = document.getElementById("ev-title").value;
  const capacity = document.getElementById("ev-capacity").value;
  if (!title.trim()) return;
  fetch("/api/events", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, capacity: capacity})}).then(() => {
      document.getElementById("ev-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Event Ticketing", "", body_inner, script)
    journey = {
        "input_selector": "#ev-title", "input_value": "Concert Night",
        "action_selector": "#add-event-btn",
        "confirm_selector": "text=Concert Night", "confirm_contains": "Concert Night",
    }
    b.finish(html, journey, "Real Event Ticketing", port=5027)


def build_restaurant_pos(root: Path):
    b = AppBuilder(root, "restaurant_pos", "restaurant POS", "2800")

    b.add_capability("2801", "List Orders", "/api/orders", "GET",
        "def handle(request):\n    return 200, {'orders': _load()}\n",
        output_fields=("orders",))

    b.add_capability("2802", "Create Order", "/api/orders", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    item = (body.get('item') or '').strip()\n"
        "    if not item:\n        return 400, {'error': 'item is required'}\n"
        "    try:\n        total = float(body.get('total', 0) or 0)\n    except (TypeError, ValueError):\n        total = 0.0\n"
        "    orders = _load()\n"
        "    next_id = (max([o['id'] for o in orders], default=0)) + 1\n"
        "    order = {'id': next_id, 'item': item, 'total': total, 'status': 'open'}\n"
        "    orders.append(order)\n    _save(orders)\n    return 201, order\n",
        output_fields=("id", "item", "total", "status"), required_input=("item",),
        side_effects=("creates_record",), slot_id="order_list", selector="#order-list")

    b.add_capability("2803", "Close Order", "/api/orders/close", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    oid = body.get('id')\n    orders = _load()\n"
        "    for o in orders:\n"
        "        if o['id'] == oid:\n            o['status'] = 'closed'\n            _save(orders)\n            return 200, o\n"
        "    return 404, {'error': f'no order with id {oid!r}'}\n",
        output_fields=("id", "item", "status"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="order-item" placeholder="Item (e.g. Table 5 - Burger)" data-slot="order_item" style="flex:1">
    <input id="order-total" type="number" step="0.01" placeholder="Total" data-slot="order_total">
    <button id="add-order-btn" data-slot="add_order">Create order</button>
  </div>
</div>
<div class="card"><ul id="order-list" data-slot="order_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/orders").then(r => r.json()).then(data => {
    const list = document.getElementById("order-list");
    list.innerHTML = "";
    (data.orders || []).forEach(o => {
      const li = document.createElement("li");
      li.textContent = o.item + " -- $" + o.total + " (" + o.status + ")";
      if (o.status === "open") {
        const close = document.createElement("button");
        close.textContent = "Close"; close.style.marginLeft = "8px";
        close.addEventListener("click", () => {
          fetch("/api/orders/close", {method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: o.id})}).then(refresh);
        });
        li.appendChild(close);
      }
      list.appendChild(li);
    });
  });
}
document.getElementById("add-order-btn").addEventListener("click", () => {
  const item = document.getElementById("order-item").value;
  const total = document.getElementById("order-total").value;
  if (!item.trim()) return;
  fetch("/api/orders", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({item: item, total: total})}).then(() => {
      document.getElementById("order-item").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Restaurant POS", "", body_inner, script)
    journey = {
        "input_selector": "#order-item", "input_value": "Table 5 - Burger",
        "action_selector": "#add-order-btn",
        "confirm_selector": "text=Table 5 - Burger", "confirm_contains": "Table 5 - Burger",
    }
    b.finish(html, journey, "Real Restaurant POS", port=5028)


def build_inventory(root: Path):
    b = AppBuilder(root, "inventory_and_warehouse", "inventory and warehouse", "2900")

    b.add_capability("2901", "List Items", "/api/items", "GET",
        "def handle(request):\n    return 200, {'items': _load()}\n",
        output_fields=("items",))

    b.add_capability("2902", "Add Item", "/api/items", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    sku = body.get('sku') or ''\n"
        "    try:\n        qty = int(body.get('qty', 0) or 0)\n    except (TypeError, ValueError):\n        qty = 0\n"
        "    items = _load()\n"
        "    next_id = (max([i['id'] for i in items], default=0)) + 1\n"
        "    item = {'id': next_id, 'name': name, 'sku': sku, 'qty': qty}\n"
        "    items.append(item)\n    _save(items)\n    return 201, item\n",
        output_fields=("id", "name", "sku", "qty"), required_input=("name",),
        side_effects=("creates_record",), slot_id="item_list", selector="#inv-item-list")

    b.add_capability("2903", "Adjust Quantity", "/api/items/adjust", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    iid = body.get('id')\n"
        "    try:\n        delta = int(body.get('delta', 0) or 0)\n    except (TypeError, ValueError):\n        delta = 0\n"
        "    items = _load()\n"
        "    for i in items:\n"
        "        if i['id'] == iid:\n            i['qty'] = i.get('qty', 0) + delta\n            _save(items)\n            return 200, i\n"
        "    return 404, {'error': f'no item with id {iid!r}'}\n",
        output_fields=("id", "name", "qty"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="inv-name" placeholder="Item name" data-slot="inv_name">
    <input id="inv-sku" placeholder="SKU" data-slot="inv_sku">
    <button id="add-item-btn" data-slot="add_item">Add item</button>
  </div>
</div>
<div class="card"><ul id="inv-item-list" data-slot="item_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/items").then(r => r.json()).then(data => {
    const list = document.getElementById("inv-item-list");
    list.innerHTML = "";
    (data.items || []).forEach(i => {
      const li = document.createElement("li");
      li.textContent = i.name + " (" + i.sku + ") -- qty: " + i.qty;
      const plus = document.createElement("button"); plus.textContent = "+1"; plus.style.marginLeft = "8px";
      plus.addEventListener("click", () => {
        fetch("/api/items/adjust", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: i.id, delta: 1})}).then(refresh);
      });
      const minus = document.createElement("button"); minus.textContent = "-1"; minus.style.marginLeft = "4px";
      minus.addEventListener("click", () => {
        fetch("/api/items/adjust", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: i.id, delta: -1})}).then(refresh);
      });
      li.appendChild(plus); li.appendChild(minus);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-item-btn").addEventListener("click", () => {
  const name = document.getElementById("inv-name").value;
  const sku = document.getElementById("inv-sku").value;
  if (!name.trim()) return;
  fetch("/api/items", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name, sku: sku})}).then(() => {
      document.getElementById("inv-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Inventory", "", body_inner, script)
    journey = {
        "input_selector": "#inv-name", "input_value": "Widget",
        "action_selector": "#add-item-btn",
        "confirm_selector": "text=Widget", "confirm_contains": "Widget",
    }
    b.finish(html, journey, "Real Inventory", port=5029)


def build_property_rental(root: Path):
    b = AppBuilder(root, "property_rental", "property rental", "2600")

    b.add_capability("2601", "List Listings", "/api/listings", "GET",
        "def handle(request):\n    return 200, {'listings': _load()}\n",
        output_fields=("listings",), data_filename="listings.json")

    b.add_capability("2602", "Create Listing", "/api/listings", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    try:\n        price = float(body.get('price', 0) or 0)\n    except (TypeError, ValueError):\n        price = 0.0\n"
        "    listings = _load()\n"
        "    next_id = (max([l['id'] for l in listings], default=0)) + 1\n"
        "    listing = {'id': next_id, 'title': title, 'price': price}\n"
        "    listings.append(listing)\n    _save(listings)\n    return 201, listing\n",
        output_fields=("id", "title", "price"), required_input=("title",),
        side_effects=("creates_record",), slot_id="listing_list", selector="#listing-list",
        data_filename="listings.json")

    b.add_capability("2603", "List Bookings", "/api/bookings", "GET",
        "def handle(request):\n    return 200, {'bookings': _load()}\n",
        output_fields=("bookings",), data_filename="bookings.json")

    b.add_capability("2604", "Book Listing", "/api/bookings", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    listing_id = body.get('listing_id')\n    guest = (body.get('guest') or '').strip()\n"
        "    if listing_id is None or not guest:\n        return 400, {'error': 'listing_id and guest are required'}\n"
        "    bookings = _load()\n"
        "    next_id = (max([b['id'] for b in bookings], default=0)) + 1\n"
        "    booking = {'id': next_id, 'listing_id': listing_id, 'guest': guest}\n"
        "    bookings.append(booking)\n    _save(bookings)\n    return 201, booking\n",
        output_fields=("id", "listing_id", "guest"), required_input=("listing_id", "guest"),
        side_effects=("creates_record",), data_filename="bookings.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="listing-title" placeholder="Listing title" data-slot="listing_title">
    <input id="listing-price" type="number" step="0.01" placeholder="Price/night" data-slot="listing_price">
    <button id="add-listing-btn" data-slot="add_listing">Add listing</button>
  </div>
</div>
<div class="card"><ul id="listing-list" data-slot="listing_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/listings").then(r => r.json()).then(data => {
    const list = document.getElementById("listing-list");
    list.innerHTML = "";
    (data.listings || []).forEach(l => {
      const li = document.createElement("li");
      li.textContent = l.title + " -- $" + l.price + "/night";
      list.appendChild(li);
    });
  });
}
document.getElementById("add-listing-btn").addEventListener("click", () => {
  const title = document.getElementById("listing-title").value;
  const price = document.getElementById("listing-price").value;
  if (!title.trim()) return;
  fetch("/api/listings", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, price: price})}).then(() => {
      document.getElementById("listing-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Property Rental", "", body_inner, script)
    journey = {
        "input_selector": "#listing-title", "input_value": "Cozy Cabin",
        "action_selector": "#add-listing-btn",
        "confirm_selector": "text=Cozy Cabin", "confirm_contains": "Cozy Cabin",
    }
    b.finish(html, journey, "Real Property Rental", port=5026)


def build_fleet_tracking(root: Path):
    b = AppBuilder(root, "fleet_tracking", "fleet tracking", "3000")

    b.add_capability("3001", "List Vehicles", "/api/vehicles", "GET",
        "def handle(request):\n    return 200, {'vehicles': _load()}\n",
        output_fields=("vehicles",))

    b.add_capability("3002", "Add Vehicle", "/api/vehicles", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    vehicles = _load()\n"
        "    next_id = (max([v['id'] for v in vehicles], default=0)) + 1\n"
        "    vehicle = {'id': next_id, 'name': name, 'status': 'idle', 'location': ''}\n"
        "    vehicles.append(vehicle)\n    _save(vehicles)\n    return 201, vehicle\n",
        output_fields=("id", "name", "status", "location"), required_input=("name",),
        side_effects=("creates_record",), slot_id="vehicle_list", selector="#vehicle-list")

    b.add_capability("3003", "Update Vehicle Location", "/api/vehicles/location", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    vid = body.get('id')\n    location = body.get('location') or ''\n"
        "    vehicles = _load()\n"
        "    for v in vehicles:\n"
        "        if v['id'] == vid:\n"
        "            v['location'] = location\n            v['status'] = 'moving'\n            _save(vehicles)\n            return 200, v\n"
        "    return 404, {'error': f'no vehicle with id {vid!r}'}\n",
        output_fields=("id", "name", "location", "status"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="veh-name" placeholder="Vehicle name" data-slot="veh_name">
    <button id="add-vehicle-btn" data-slot="add_vehicle">Add vehicle</button>
  </div>
</div>
<div class="card"><ul id="vehicle-list" data-slot="vehicle_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/vehicles").then(r => r.json()).then(data => {
    const list = document.getElementById("vehicle-list");
    list.innerHTML = "";
    (data.vehicles || []).forEach(v => {
      const li = document.createElement("li");
      li.textContent = v.name + " -- " + v.status + (v.location ? " @ " + v.location : "");
      list.appendChild(li);
    });
  });
}
document.getElementById("add-vehicle-btn").addEventListener("click", () => {
  const name = document.getElementById("veh-name").value;
  if (!name.trim()) return;
  fetch("/api/vehicles", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name})}).then(() => {
      document.getElementById("veh-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Fleet Tracking", "", body_inner, script)
    journey = {
        "input_selector": "#veh-name", "input_value": "Truck 7",
        "action_selector": "#add-vehicle-btn",
        "confirm_selector": "text=Truck 7", "confirm_contains": "Truck 7",
    }
    b.finish(html, journey, "Real Fleet Tracking", port=5030)


def build_dating(root: Path):
    b = AppBuilder(root, "dating", "dating", "3100")

    b.add_capability("3101", "List Profiles", "/api/profiles", "GET",
        "def handle(request):\n    return 200, {'profiles': _load()}\n",
        output_fields=("profiles",), data_filename="profiles.json")

    b.add_capability("3102", "Create Profile", "/api/profiles", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    bio = body.get('bio') or ''\n"
        "    profiles = _load()\n"
        "    next_id = (max([p['id'] for p in profiles], default=0)) + 1\n"
        "    profile = {'id': next_id, 'name': name, 'bio': bio}\n"
        "    profiles.append(profile)\n    _save(profiles)\n    return 201, profile\n",
        output_fields=("id", "name", "bio"), required_input=("name",),
        side_effects=("creates_record",), slot_id="profile_list", selector="#profile-list",
        data_filename="profiles.json")

    b.add_capability("3103", "Swipe", "/api/swipes", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    profile_id = body.get('profile_id')\n    target_id = body.get('target_id')\n"
        "    if profile_id is None or target_id is None:\n        return 400, {'error': 'profile_id and target_id are required'}\n"
        "    liked = bool(body.get('liked', True))\n"
        "    swipes = _load()\n"
        "    swipes.append({'profile_id': profile_id, 'target_id': target_id, 'liked': liked})\n"
        "    _save(swipes)\n"
        "    mutual = any(s['profile_id'] == target_id and s['target_id'] == profile_id and s['liked']\n"
        "                 for s in swipes) and liked\n"
        "    return 200, {'profile_id': profile_id, 'target_id': target_id, 'liked': liked, 'match': mutual}\n",
        output_fields=("profile_id", "target_id", "liked", "match"),
        required_input=("profile_id", "target_id"), side_effects=("creates_record",),
        data_filename="swipes.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="profile-name" placeholder="Your name" data-slot="profile_name">
    <input id="profile-bio" placeholder="Short bio" data-slot="profile_bio">
    <button id="add-profile-btn" data-slot="add_profile">Create profile</button>
  </div>
</div>
<div class="card"><ul id="profile-list" data-slot="profile_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/profiles").then(r => r.json()).then(data => {
    const list = document.getElementById("profile-list");
    list.innerHTML = "";
    (data.profiles || []).forEach(p => {
      const li = document.createElement("li");
      li.textContent = p.name + (p.bio ? " -- " + p.bio : "");
      list.appendChild(li);
    });
  });
}
document.getElementById("add-profile-btn").addEventListener("click", () => {
  const name = document.getElementById("profile-name").value;
  const bio = document.getElementById("profile-bio").value;
  if (!name.trim()) return;
  fetch("/api/profiles", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name, bio: bio})}).then(() => {
      document.getElementById("profile-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Dating", "", body_inner, script)
    journey = {
        "input_selector": "#profile-name", "input_value": "Sam",
        "action_selector": "#add-profile-btn",
        "confirm_selector": "text=Sam", "confirm_contains": "Sam",
    }
    b.finish(html, journey, "Real Dating", port=5031)


def build_social_feed(root: Path):
    b = AppBuilder(root, "social_feed", "social feed", "3200")

    b.add_capability("3201", "List Feed", "/api/posts", "GET",
        "def handle(request):\n    return 200, {'posts': _load()}\n",
        output_fields=("posts",))

    b.add_capability("3202", "Create Post", "/api/posts", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    text = (body.get('text') or '').strip()\n"
        "    if not text:\n        return 400, {'error': 'text is required'}\n"
        "    posts = _load()\n"
        "    next_id = (max([p['id'] for p in posts], default=0)) + 1\n"
        "    post = {'id': next_id, 'author': 'You', 'text': text, 'likes': 0}\n"
        "    posts.append(post)\n    _save(posts)\n    return 201, post\n",
        output_fields=("id", "author", "text", "likes"), required_input=("text",),
        side_effects=("creates_record",), slot_id="post_list", selector="#post-list")

    b.add_capability("3203", "Like Post", "/api/posts/like", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    pid = body.get('id')\n    posts = _load()\n"
        "    for p in posts:\n"
        "        if p['id'] == pid:\n            p['likes'] += 1\n            _save(posts)\n            return 200, p\n"
        "    return 404, {'error': f'no post with id {pid!r}'}\n",
        output_fields=("id", "likes"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="post-text" placeholder="What's on your mind?" data-slot="post_text" style="flex:1">
    <button id="add-post-btn" data-slot="add_post">Post</button>
  </div>
</div>
<div class="card"><ul id="post-list" data-slot="post_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/posts").then(r => r.json()).then(data => {
    const list = document.getElementById("post-list");
    list.innerHTML = "";
    (data.posts || []).forEach(p => {
      const li = document.createElement("li");
      li.textContent = p.author + ": " + p.text + " (" + p.likes + " likes)";
      const like = document.createElement("button"); like.textContent = "Like"; like.style.marginLeft = "8px";
      like.addEventListener("click", () => {
        fetch("/api/posts/like", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: p.id})}).then(refresh);
      });
      li.appendChild(like);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-post-btn").addEventListener("click", () => {
  const text = document.getElementById("post-text").value;
  if (!text.trim()) return;
  fetch("/api/posts", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: text})}).then(() => {
      document.getElementById("post-text").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Social Feed", "", body_inner, script)
    journey = {
        "input_selector": "#post-text", "input_value": "Hello world",
        "action_selector": "#add-post-btn",
        "confirm_selector": "text=Hello world", "confirm_contains": "Hello world",
    }
    b.finish(html, journey, "Real Social Feed", port=5032)


# A tiny, real, valid 1x1 red PNG (67 bytes), used as a genuine placeholder
# image for photo/video-shaped apps below -- real image bytes actually
# decoded and rendered by the real browser, not a fake string standing in
# for one. Explicitly NOT a real user photo: there is no file-upload UI in
# this MVP scope, named plainly here and in the final status report.
_PLACEHOLDER_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42Y"
    "AAAAASUVORK5CYII="
)


def build_photo_sharing(root: Path):
    b = AppBuilder(root, "photo_sharing", "photo sharing", "3300")

    b.add_capability("3301", "List Photos", "/api/photos", "GET",
        "def handle(request):\n    return 200, {'photos': _load()}\n",
        output_fields=("photos",))

    b.add_capability("3302", "Upload Photo", "/api/photos", "POST",
        "PLACEHOLDER_PNG_B64 = " + repr(_PLACEHOLDER_PNG_B64) + "\n"
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    caption = (body.get('caption') or '').strip()\n"
        "    if not caption:\n        return 400, {'error': 'caption is required'}\n"
        "    photos = _load()\n"
        "    next_id = (max([p['id'] for p in photos], default=0)) + 1\n"
        "    photo = {'id': next_id, 'caption': caption, 'image_b64': PLACEHOLDER_PNG_B64, 'likes': 0}\n"
        "    photos.append(photo)\n    _save(photos)\n    return 201, photo\n",
        output_fields=("id", "caption", "image_b64", "likes"), required_input=("caption",),
        side_effects=("creates_record",), slot_id="photo_list", selector="#photo-list")

    b.add_capability("3303", "Like Photo", "/api/photos/like", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    pid = body.get('id')\n    photos = _load()\n"
        "    for p in photos:\n"
        "        if p['id'] == pid:\n            p['likes'] += 1\n            _save(photos)\n            return 200, p\n"
        "    return 404, {'error': f'no photo with id {pid!r}'}\n",
        output_fields=("id", "likes"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="photo-caption" placeholder="Caption" data-slot="photo_caption" style="flex:1">
    <button id="add-photo-btn" data-slot="add_photo">Upload</button>
  </div>
  <p style="color:#888;font-size:12px">Note: uploaded image is a generated placeholder square, not a real user photo (no file-upload UI in this build).</p>
</div>
<div class="card"><ul id="photo-list" data-slot="photo_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/photos").then(r => r.json()).then(data => {
    const list = document.getElementById("photo-list");
    list.innerHTML = "";
    (data.photos || []).forEach(p => {
      const li = document.createElement("li");
      const img = document.createElement("img");
      img.src = "data:image/png;base64," + p.image_b64;
      img.style.width = "40px"; img.style.height = "40px"; img.style.marginRight = "8px";
      const span = document.createElement("span");
      span.textContent = p.caption + " (" + p.likes + " likes)";
      li.appendChild(img); li.appendChild(span);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-photo-btn").addEventListener("click", () => {
  const caption = document.getElementById("photo-caption").value;
  if (!caption.trim()) return;
  fetch("/api/photos", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({caption: caption})}).then(() => {
      document.getElementById("photo-caption").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Photo Sharing", "", body_inner, script)
    journey = {
        "input_selector": "#photo-caption", "input_value": "Sunset",
        "action_selector": "#add-photo-btn",
        "confirm_selector": "text=Sunset", "confirm_contains": "Sunset",
    }
    b.finish(html, journey, "Real Photo Sharing", port=5033)


def build_quiz_and_flashcards(root: Path):
    b = AppBuilder(root, "quiz_and_flashcards", "quiz and flashcards", "4200")

    b.add_capability("4201", "List Cards", "/api/cards", "GET",
        "def handle(request):\n    return 200, {'cards': _load()}\n",
        output_fields=("cards",))

    b.add_capability("4202", "Create Card", "/api/cards", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    question = (body.get('question') or '').strip()\n"
        "    if not question:\n        return 400, {'error': 'question is required'}\n"
        "    answer = body.get('answer') or ''\n"
        "    cards = _load()\n"
        "    next_id = (max([c['id'] for c in cards], default=0)) + 1\n"
        "    card = {'id': next_id, 'question': question, 'answer': answer, 'correct_count': 0}\n"
        "    cards.append(card)\n    _save(cards)\n    return 201, card\n",
        output_fields=("id", "question", "answer", "correct_count"), required_input=("question",),
        side_effects=("creates_record",), slot_id="card_list", selector="#card-list")

    b.add_capability("4203", "Review Card", "/api/cards/review", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    cid = body.get('id')\n    correct = bool(body.get('correct', False))\n"
        "    cards = _load()\n"
        "    for c in cards:\n"
        "        if c['id'] == cid:\n"
        "            if correct:\n                c['correct_count'] += 1\n"
        "            _save(cards)\n            return 200, c\n"
        "    return 404, {'error': f'no card with id {cid!r}'}\n",
        output_fields=("id", "correct_count"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="card-question" placeholder="Question" data-slot="card_question">
    <input id="card-answer" placeholder="Answer" data-slot="card_answer">
    <button id="add-card-btn" data-slot="add_card">Add card</button>
  </div>
</div>
<div class="card"><ul id="card-list" data-slot="card_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/cards").then(r => r.json()).then(data => {
    const list = document.getElementById("card-list");
    list.innerHTML = "";
    (data.cards || []).forEach(c => {
      const li = document.createElement("li");
      li.textContent = c.question + " -> " + c.answer + " (correct " + c.correct_count + "x)";
      const got = document.createElement("button"); got.textContent = "Got it"; got.style.marginLeft = "8px";
      got.addEventListener("click", () => {
        fetch("/api/cards/review", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: c.id, correct: true})}).then(refresh);
      });
      li.appendChild(got);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-card-btn").addEventListener("click", () => {
  const question = document.getElementById("card-question").value;
  const answer = document.getElementById("card-answer").value;
  if (!question.trim()) return;
  fetch("/api/cards", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question: question, answer: answer})}).then(() => {
      document.getElementById("card-question").value = "";
      document.getElementById("card-answer").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Quiz & Flashcards", "", body_inner, script)
    journey = {
        "input_selector": "#card-question", "input_value": "2+2?",
        "action_selector": "#add-card-btn",
        "confirm_selector": "text=2+2?", "confirm_contains": "2+2?",
    }
    b.finish(html, journey, "Real Quiz & Flashcards", port=5042)


def build_recipe_and_meal_planning(root: Path):
    b = AppBuilder(root, "recipe_and_meal_planning", "recipe and meal planning", "4300")

    b.add_capability("4301", "List Recipes", "/api/recipes", "GET",
        "def handle(request):\n    return 200, {'recipes': _load()}\n",
        output_fields=("recipes",), data_filename="recipes.json")

    b.add_capability("4302", "Create Recipe", "/api/recipes", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    ingredients = body.get('ingredients') or ''\n"
        "    recipes = _load()\n"
        "    next_id = (max([r['id'] for r in recipes], default=0)) + 1\n"
        "    recipe = {'id': next_id, 'title': title, 'ingredients': ingredients}\n"
        "    recipes.append(recipe)\n    _save(recipes)\n    return 201, recipe\n",
        output_fields=("id", "title", "ingredients"), required_input=("title",),
        side_effects=("creates_record",), slot_id="recipe_list", selector="#recipe-list",
        data_filename="recipes.json")

    b.add_capability("4303", "List Meal Plan", "/api/meal_plan", "GET",
        "def handle(request):\n    return 200, {'plan': _load()}\n",
        output_fields=("plan",), data_filename="meal_plan.json")

    b.add_capability("4304", "Plan Meal", "/api/meal_plan", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    day = (body.get('day') or '').strip()\n    recipe_id = body.get('recipe_id')\n"
        "    if not day or recipe_id is None:\n        return 400, {'error': 'day and recipe_id are required'}\n"
        "    plan = _load()\n    plan = [p for p in plan if p['day'] != day]\n"
        "    entry = {'day': day, 'recipe_id': recipe_id}\n    plan.append(entry)\n"
        "    _save(plan)\n    return 201, entry\n",
        output_fields=("day", "recipe_id"), required_input=("day", "recipe_id"),
        side_effects=("creates_record",), data_filename="meal_plan.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="recipe-title" placeholder="Recipe title" data-slot="recipe_title">
    <input id="recipe-ingredients" placeholder="Ingredients (comma separated)" data-slot="recipe_ingredients" style="flex:1">
    <button id="add-recipe-btn" data-slot="add_recipe">Add recipe</button>
  </div>
</div>
<div class="card"><ul id="recipe-list" data-slot="recipe_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/recipes").then(r => r.json()).then(data => {
    const list = document.getElementById("recipe-list");
    list.innerHTML = "";
    (data.recipes || []).forEach(r => {
      const li = document.createElement("li");
      li.textContent = r.title + (r.ingredients ? " -- " + r.ingredients : "");
      list.appendChild(li);
    });
  });
}
document.getElementById("add-recipe-btn").addEventListener("click", () => {
  const title = document.getElementById("recipe-title").value;
  const ingredients = document.getElementById("recipe-ingredients").value;
  if (!title.trim()) return;
  fetch("/api/recipes", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, ingredients: ingredients})}).then(() => {
      document.getElementById("recipe-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Recipes & Meal Planning", "", body_inner, script)
    journey = {
        "input_selector": "#recipe-title", "input_value": "Pasta Bake",
        "action_selector": "#add-recipe-btn",
        "confirm_selector": "text=Pasta Bake", "confirm_contains": "Pasta Bake",
    }
    b.finish(html, journey, "Real Recipes", port=5043)


def build_language_learning(root: Path):
    b = AppBuilder(root, "language_learning", "language learning", "4000")

    b.add_capability("4001", "List Cards", "/api/cards", "GET",
        "def handle(request):\n    return 200, {'cards': _load()}\n",
        output_fields=("cards",))

    b.add_capability("4002", "Add Card", "/api/cards", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    front = (body.get('front') or '').strip()\n"
        "    if not front:\n        return 400, {'error': 'front is required'}\n"
        "    back = body.get('back') or ''\n"
        "    cards = _load()\n"
        "    next_id = (max([c['id'] for c in cards], default=0)) + 1\n"
        "    card = {'id': next_id, 'front': front, 'back': back, 'correct': 0, 'incorrect': 0}\n"
        "    cards.append(card)\n    _save(cards)\n    return 201, card\n",
        output_fields=("id", "front", "back", "correct", "incorrect"), required_input=("front",),
        side_effects=("creates_record",), slot_id="card_list", selector="#lang-card-list")

    b.add_capability("4003", "Review Card", "/api/cards/review", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    cid = body.get('id')\n    correct = bool(body.get('correct', False))\n"
        "    cards = _load()\n"
        "    for c in cards:\n"
        "        if c['id'] == cid:\n"
        "            c['correct' if correct else 'incorrect'] += 1\n"
        "            _save(cards)\n            return 200, c\n"
        "    return 404, {'error': f'no card with id {cid!r}'}\n",
        output_fields=("id", "correct", "incorrect"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="lang-front" placeholder="Word (e.g. Hola)" data-slot="lang_front">
    <input id="lang-back" placeholder="Translation (e.g. Hello)" data-slot="lang_back">
    <button id="add-lang-card-btn" data-slot="add_lang_card">Add word</button>
  </div>
</div>
<div class="card"><ul id="lang-card-list" data-slot="card_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/cards").then(r => r.json()).then(data => {
    const list = document.getElementById("lang-card-list");
    list.innerHTML = "";
    (data.cards || []).forEach(c => {
      const li = document.createElement("li");
      li.textContent = c.front + " = " + c.back + " (correct " + c.correct + ", incorrect " + c.incorrect + ")";
      list.appendChild(li);
    });
  });
}
document.getElementById("add-lang-card-btn").addEventListener("click", () => {
  const front = document.getElementById("lang-front").value;
  const back = document.getElementById("lang-back").value;
  if (!front.trim()) return;
  fetch("/api/cards", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({front: front, back: back})}).then(() => {
      document.getElementById("lang-front").value = "";
      document.getElementById("lang-back").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Language Learning", "", body_inner, script)
    journey = {
        "input_selector": "#lang-front", "input_value": "Hola",
        "action_selector": "#add-lang-card-btn",
        "confirm_selector": "text=Hola", "confirm_contains": "Hola",
    }
    b.finish(html, journey, "Real Language Learning", port=5040)


def build_online_course_lms(root: Path):
    b = AppBuilder(root, "online_course_lms", "online course LMS", "4100")

    b.add_capability("4101", "List Courses", "/api/courses", "GET",
        "def handle(request):\n    return 200, {'courses': _load()}\n",
        output_fields=("courses",), data_filename="courses.json")

    b.add_capability("4102", "Create Course", "/api/courses", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    courses = _load()\n"
        "    next_id = (max([c['id'] for c in courses], default=0)) + 1\n"
        "    course = {'id': next_id, 'title': title}\n"
        "    courses.append(course)\n    _save(courses)\n    return 201, course\n",
        output_fields=("id", "title"), required_input=("title",),
        side_effects=("creates_record",), slot_id="course_list", selector="#course-list",
        data_filename="courses.json")

    b.add_capability("4103", "List Lessons", "/api/lessons", "GET",
        "def handle(request):\n    return 200, {'lessons': _load()}\n",
        output_fields=("lessons",), data_filename="lessons.json")

    b.add_capability("4104", "Add Lesson", "/api/lessons", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    course_id = body.get('course_id')\n    title = (body.get('title') or '').strip()\n"
        "    if course_id is None or not title:\n        return 400, {'error': 'course_id and title are required'}\n"
        "    lessons = _load()\n"
        "    next_id = (max([l['id'] for l in lessons], default=0)) + 1\n"
        "    lesson = {'id': next_id, 'course_id': course_id, 'title': title}\n"
        "    lessons.append(lesson)\n    _save(lessons)\n    return 201, lesson\n",
        output_fields=("id", "course_id", "title"), required_input=("course_id", "title"),
        side_effects=("creates_record",), data_filename="lessons.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="course-title" placeholder="Course title" data-slot="course_title">
    <button id="add-course-btn" data-slot="add_course">Create course</button>
  </div>
</div>
<div class="card"><ul id="course-list" data-slot="course_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/courses").then(r => r.json()).then(data => {
    const list = document.getElementById("course-list");
    list.innerHTML = "";
    (data.courses || []).forEach(c => {
      const li = document.createElement("li");
      li.textContent = c.title;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-course-btn").addEventListener("click", () => {
  const title = document.getElementById("course-title").value;
  if (!title.trim()) return;
  fetch("/api/courses", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => {
      document.getElementById("course-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Online Course LMS", "", body_inner, script)
    journey = {
        "input_selector": "#course-title", "input_value": "Intro to Python",
        "action_selector": "#add-course-btn",
        "confirm_selector": "text=Intro to Python", "confirm_contains": "Intro to Python",
    }
    b.finish(html, journey, "Real LMS", port=5041)


def build_file_storage(root: Path):
    b = AppBuilder(root, "file_storage_and_sync", "file storage and sync", "1500")

    b.add_capability("1501", "List Files", "/api/files", "GET",
        "def handle(request):\n    return 200, {'files': _load()}\n",
        output_fields=("files",))

    b.add_capability("1502", "Upload File", "/api/files", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    content = body.get('content') or ''\n"
        "    files = _load()\n"
        "    next_id = (max([f['id'] for f in files], default=0)) + 1\n"
        "    file = {'id': next_id, 'name': name, 'content': content}\n"
        "    files.append(file)\n    _save(files)\n    return 201, file\n",
        output_fields=("id", "name", "content"), required_input=("name",),
        side_effects=("creates_record",), slot_id="file_list", selector="#file-list")

    b.add_capability("1503", "Delete File", "/api/files/delete", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    fid = body.get('id')\n    files = _load()\n"
        "    remaining = [f for f in files if f['id'] != fid]\n"
        "    if len(remaining) == len(files):\n        return 404, {'error': f'no file with id {fid!r}'}\n"
        "    _save(remaining)\n    return 200, {'id': fid, 'deleted': True}\n",
        output_fields=("id", "deleted"), required_input=("id",), side_effects=("deletes_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="file-name" placeholder="File name (e.g. notes.txt)" data-slot="file_name">
    <input id="file-content" placeholder="Content" data-slot="file_content" style="flex:1">
    <button id="upload-file-btn" data-slot="upload_file">Upload</button>
  </div>
</div>
<div class="card"><ul id="file-list" data-slot="file_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/files").then(r => r.json()).then(data => {
    const list = document.getElementById("file-list");
    list.innerHTML = "";
    (data.files || []).forEach(f => {
      const li = document.createElement("li");
      li.textContent = f.name;
      const del = document.createElement("button");
      del.className = "danger"; del.textContent = "Delete"; del.style.marginLeft = "8px";
      del.addEventListener("click", () => {
        fetch("/api/files/delete", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: f.id})}).then(refresh);
      });
      li.appendChild(del);
      list.appendChild(li);
    });
  });
}
document.getElementById("upload-file-btn").addEventListener("click", () => {
  const name = document.getElementById("file-name").value;
  const content = document.getElementById("file-content").value;
  if (!name.trim()) return;
  fetch("/api/files", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name, content: content})}).then(() => {
      document.getElementById("file-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("File Storage", "", body_inner, script)
    journey = {
        "input_selector": "#file-name", "input_value": "notes.txt",
        "action_selector": "#upload-file-btn",
        "confirm_selector": "text=notes.txt", "confirm_contains": "notes.txt",
    }
    b.finish(html, journey, "Real File Storage", port=5015)


def build_doc_editor(root: Path):
    b = AppBuilder(root, "collaborative_document_editor", "collaborative document editor", "1600")

    b.add_capability("1601", "List Docs", "/api/docs", "GET",
        "def handle(request):\n    return 200, {'docs': _load()}\n",
        output_fields=("docs",))

    b.add_capability("1602", "Create Doc", "/api/docs", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    docs = _load()\n"
        "    next_id = (max([d['id'] for d in docs], default=0)) + 1\n"
        "    doc = {'id': next_id, 'title': title, 'content': ''}\n"
        "    docs.append(doc)\n    _save(docs)\n    return 201, doc\n",
        output_fields=("id", "title", "content"), required_input=("title",),
        side_effects=("creates_record",), slot_id="doc_list", selector="#doc-list")

    b.add_capability("1603", "Update Doc Content", "/api/docs/update", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    did = body.get('id')\n    content = body.get('content', '')\n"
        "    docs = _load()\n"
        "    for d in docs:\n"
        "        if d['id'] == did:\n            d['content'] = content\n            _save(docs)\n            return 200, d\n"
        "    return 404, {'error': f'no doc with id {did!r}'}\n",
        output_fields=("id", "title", "content"), required_input=("id",),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="doc-title" placeholder="Document title" data-slot="doc_title" style="flex:1">
    <button id="add-doc-btn" data-slot="add_doc">Create document</button>
  </div>
</div>
<div class="card"><ul id="doc-list" data-slot="doc_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/docs").then(r => r.json()).then(data => {
    const list = document.getElementById("doc-list");
    list.innerHTML = "";
    (data.docs || []).forEach(d => {
      const li = document.createElement("li");
      li.textContent = d.title;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-doc-btn").addEventListener("click", () => {
  const title = document.getElementById("doc-title").value;
  if (!title.trim()) return;
  fetch("/api/docs", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => {
      document.getElementById("doc-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Document Editor", "", body_inner, script)
    journey = {
        "input_selector": "#doc-title", "input_value": "Project Plan",
        "action_selector": "#add-doc-btn",
        "confirm_selector": "text=Project Plan", "confirm_contains": "Project Plan",
    }
    b.finish(html, journey, "Real Document Editor", port=5016)


def build_ecommerce(root: Path):
    b = AppBuilder(root, "e_commerce_storefront", "e-commerce storefront", "1900")

    b.add_capability("1901", "List Products", "/api/products", "GET",
        "def handle(request):\n    return 200, {'products': _load()}\n",
        output_fields=("products",), data_filename="products.json")

    b.add_capability("1902", "Add Product", "/api/products", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    try:\n        price = float(body.get('price', 0) or 0)\n    except (TypeError, ValueError):\n        price = 0.0\n"
        "    products = _load()\n"
        "    next_id = (max([p['id'] for p in products], default=0)) + 1\n"
        "    product = {'id': next_id, 'name': name, 'price': price}\n"
        "    products.append(product)\n    _save(products)\n    return 201, product\n",
        output_fields=("id", "name", "price"), required_input=("name",),
        side_effects=("creates_record",), slot_id="product_list", selector="#product-list",
        data_filename="products.json")

    b.add_capability("1903", "List Orders", "/api/orders", "GET",
        "def handle(request):\n    return 200, {'orders': _load()}\n",
        output_fields=("orders",), data_filename="orders.json")

    b.add_capability("1904", "Checkout", "/api/checkout", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    product_id = body.get('product_id')\n"
        "    if product_id is None:\n        return 400, {'error': 'product_id is required'}\n"
        "    orders = _load()\n"
        "    next_id = (max([o['id'] for o in orders], default=0)) + 1\n"
        "    # Real order record; NOT a real payment settlement -- no payment\n"
        "    # processor is wired in this sandbox, named plainly here.\n"
        "    order = {'id': next_id, 'product_id': product_id, 'status': 'placed', 'payment': 'not_processed'}\n"
        "    orders.append(order)\n    _save(orders)\n    return 201, order\n",
        output_fields=("id", "product_id", "status", "payment"), required_input=("product_id",),
        side_effects=("creates_record",), data_filename="orders.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="prod-name" placeholder="Product name" data-slot="prod_name">
    <input id="prod-price" type="number" step="0.01" placeholder="Price" data-slot="prod_price">
    <button id="add-product-btn" data-slot="add_product">Add product</button>
  </div>
  <p style="color:#888;font-size:12px">Note: checkout records a real order; no real payment processor is wired.</p>
</div>
<div class="card"><ul id="product-list" data-slot="product_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/products").then(r => r.json()).then(data => {
    const list = document.getElementById("product-list");
    list.innerHTML = "";
    (data.products || []).forEach(p => {
      const li = document.createElement("li");
      li.textContent = p.name + " -- $" + p.price;
      const buy = document.createElement("button"); buy.textContent = "Checkout"; buy.style.marginLeft = "8px";
      buy.addEventListener("click", () => {
        fetch("/api/checkout", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({product_id: p.id})}).then(refresh);
      });
      li.appendChild(buy);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-product-btn").addEventListener("click", () => {
  const name = document.getElementById("prod-name").value;
  const price = document.getElementById("prod-price").value;
  if (!name.trim()) return;
  fetch("/api/products", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name, price: price})}).then(() => {
      document.getElementById("prod-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Storefront", "", body_inner, script)
    journey = {
        "input_selector": "#prod-name", "input_value": "Blue Mug",
        "action_selector": "#add-product-btn",
        "confirm_selector": "text=Blue Mug", "confirm_contains": "Blue Mug",
    }
    b.finish(html, journey, "Real Storefront", port=5019)


def build_marketplace(root: Path):
    b = AppBuilder(root, "multi_vendor_marketplace", "multi-vendor marketplace", "2000")

    b.add_capability("2001", "List Vendors", "/api/vendors", "GET",
        "def handle(request):\n    return 200, {'vendors': _load()}\n",
        output_fields=("vendors",), data_filename="vendors.json")

    b.add_capability("2002", "Add Vendor", "/api/vendors", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    vendors = _load()\n"
        "    next_id = (max([v['id'] for v in vendors], default=0)) + 1\n"
        "    vendor = {'id': next_id, 'name': name}\n"
        "    vendors.append(vendor)\n    _save(vendors)\n    return 201, vendor\n",
        output_fields=("id", "name"), required_input=("name",),
        side_effects=("creates_record",), slot_id="vendor_list", selector="#vendor-list",
        data_filename="vendors.json")

    b.add_capability("2003", "List Vendor Products", "/api/vendor_products", "GET",
        "def handle(request):\n    return 200, {'products': _load()}\n",
        output_fields=("products",), data_filename="vendor_products.json")

    b.add_capability("2004", "Add Vendor Product", "/api/vendor_products", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    vendor_id = body.get('vendor_id')\n    name = (body.get('name') or '').strip()\n"
        "    if vendor_id is None or not name:\n        return 400, {'error': 'vendor_id and name are required'}\n"
        "    products = _load()\n"
        "    next_id = (max([p['id'] for p in products], default=0)) + 1\n"
        "    product = {'id': next_id, 'vendor_id': vendor_id, 'name': name}\n"
        "    products.append(product)\n    _save(products)\n    return 201, product\n",
        output_fields=("id", "vendor_id", "name"), required_input=("vendor_id", "name"),
        side_effects=("creates_record",), data_filename="vendor_products.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="vendor-name" placeholder="Vendor name" data-slot="vendor_name">
    <button id="add-vendor-btn" data-slot="add_vendor">Add vendor</button>
  </div>
</div>
<div class="card"><ul id="vendor-list" data-slot="vendor_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/vendors").then(r => r.json()).then(data => {
    const list = document.getElementById("vendor-list");
    list.innerHTML = "";
    (data.vendors || []).forEach(v => {
      const li = document.createElement("li");
      li.textContent = v.name;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-vendor-btn").addEventListener("click", () => {
  const name = document.getElementById("vendor-name").value;
  if (!name.trim()) return;
  fetch("/api/vendors", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name})}).then(() => {
      document.getElementById("vendor-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Marketplace", "", body_inner, script)
    journey = {
        "input_selector": "#vendor-name", "input_value": "Acme Vendor",
        "action_selector": "#add-vendor-btn",
        "confirm_selector": "text=Acme Vendor", "confirm_contains": "Acme Vendor",
    }
    b.finish(html, journey, "Real Marketplace", port=5020)


def build_auction(root: Path):
    b = AppBuilder(root, "auction", "auction", "2100")

    b.add_capability("2101", "List Items", "/api/items", "GET",
        "def handle(request):\n    return 200, {'items': _load()}\n",
        output_fields=("items",))

    b.add_capability("2102", "Create Item", "/api/items", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    try:\n        starting_bid = float(body.get('starting_bid', 0) or 0)\n    except (TypeError, ValueError):\n        starting_bid = 0.0\n"
        "    items = _load()\n"
        "    next_id = (max([i['id'] for i in items], default=0)) + 1\n"
        "    item = {'id': next_id, 'title': title, 'current_bid': starting_bid, 'highest_bidder': None}\n"
        "    items.append(item)\n    _save(items)\n    return 201, item\n",
        output_fields=("id", "title", "current_bid", "highest_bidder"), required_input=("title",),
        side_effects=("creates_record",), slot_id="item_list", selector="#auction-item-list")

    b.add_capability("2103", "Place Bid", "/api/items/bid", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    iid = body.get('id')\n    bidder = body.get('bidder') or 'anonymous'\n"
        "    try:\n        amount = float(body.get('amount', 0) or 0)\n    except (TypeError, ValueError):\n        amount = 0.0\n"
        "    items = _load()\n"
        "    for i in items:\n"
        "        if i['id'] == iid:\n"
        "            if amount <= i.get('current_bid', 0):\n                return 400, {'error': 'bid too low'}\n"
        "            i['current_bid'] = amount\n            i['highest_bidder'] = bidder\n"
        "            _save(items)\n            return 200, i\n"
        "    return 404, {'error': f'no item with id {iid!r}'}\n",
        output_fields=("id", "current_bid", "highest_bidder"), required_input=("id", "amount"),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="auction-title" placeholder="Item title" data-slot="auction_title">
    <input id="auction-start-bid" type="number" step="0.01" placeholder="Starting bid" data-slot="auction_start_bid">
    <button id="add-auction-item-btn" data-slot="add_auction_item">List item</button>
  </div>
</div>
<div class="card"><ul id="auction-item-list" data-slot="item_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/items").then(r => r.json()).then(data => {
    const list = document.getElementById("auction-item-list");
    list.innerHTML = "";
    (data.items || []).forEach(i => {
      const li = document.createElement("li");
      li.textContent = i.title + " -- current bid $" + i.current_bid;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-auction-item-btn").addEventListener("click", () => {
  const title = document.getElementById("auction-title").value;
  const startBid = document.getElementById("auction-start-bid").value;
  if (!title.trim()) return;
  fetch("/api/items", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, starting_bid: startBid})}).then(() => {
      document.getElementById("auction-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Auction", "", body_inner, script)
    journey = {
        "input_selector": "#auction-title", "input_value": "Vintage Clock",
        "action_selector": "#add-auction-item-btn",
        "confirm_selector": "text=Vintage Clock", "confirm_contains": "Vintage Clock",
    }
    b.finish(html, journey, "Real Auction", port=5021)


def build_food_delivery(root: Path):
    b = AppBuilder(root, "food_delivery", "food delivery", "2200")

    b.add_capability("2201", "List Restaurants", "/api/restaurants", "GET",
        "def handle(request):\n    return 200, {'restaurants': _load()}\n",
        output_fields=("restaurants",), data_filename="restaurants.json")

    b.add_capability("2202", "Add Restaurant", "/api/restaurants", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    restaurants = _load()\n"
        "    next_id = (max([r['id'] for r in restaurants], default=0)) + 1\n"
        "    restaurant = {'id': next_id, 'name': name}\n"
        "    restaurants.append(restaurant)\n    _save(restaurants)\n    return 201, restaurant\n",
        output_fields=("id", "name"), required_input=("name",),
        side_effects=("creates_record",), slot_id="restaurant_list", selector="#restaurant-list",
        data_filename="restaurants.json")

    b.add_capability("2203", "List Menu", "/api/menu", "GET",
        "def handle(request):\n    return 200, {'menu': _load()}\n",
        output_fields=("menu",), data_filename="menu.json")

    b.add_capability("2204", "Add Menu Item", "/api/menu", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    restaurant_id = body.get('restaurant_id')\n    name = (body.get('name') or '').strip()\n"
        "    if restaurant_id is None or not name:\n        return 400, {'error': 'restaurant_id and name are required'}\n"
        "    menu = _load()\n"
        "    next_id = (max([m['id'] for m in menu], default=0)) + 1\n"
        "    item = {'id': next_id, 'restaurant_id': restaurant_id, 'name': name}\n"
        "    menu.append(item)\n    _save(menu)\n    return 201, item\n",
        output_fields=("id", "restaurant_id", "name"), required_input=("restaurant_id", "name"),
        side_effects=("creates_record",), data_filename="menu.json")

    b.add_capability("2205", "Place Order", "/api/orders", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    item_id = body.get('item_id')\n"
        "    if item_id is None:\n        return 400, {'error': 'item_id is required'}\n"
        "    orders = _load()\n"
        "    next_id = (max([o['id'] for o in orders], default=0)) + 1\n"
        "    order = {'id': next_id, 'item_id': item_id, 'status': 'placed'}\n"
        "    orders.append(order)\n    _save(orders)\n    return 201, order\n",
        output_fields=("id", "item_id", "status"), required_input=("item_id",),
        side_effects=("creates_record",), data_filename="food_orders.json")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="rest-name" placeholder="Restaurant name" data-slot="rest_name">
    <button id="add-restaurant-btn" data-slot="add_restaurant">Add restaurant</button>
  </div>
</div>
<div class="card"><ul id="restaurant-list" data-slot="restaurant_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/restaurants").then(r => r.json()).then(data => {
    const list = document.getElementById("restaurant-list");
    list.innerHTML = "";
    (data.restaurants || []).forEach(r => {
      const li = document.createElement("li");
      li.textContent = r.name;
      list.appendChild(li);
    });
  });
}
document.getElementById("add-restaurant-btn").addEventListener("click", () => {
  const name = document.getElementById("rest-name").value;
  if (!name.trim()) return;
  fetch("/api/restaurants", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name})}).then(() => {
      document.getElementById("rest-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Food Delivery", "", body_inner, script)
    journey = {
        "input_selector": "#rest-name", "input_value": "Pizza Palace",
        "action_selector": "#add-restaurant-btn",
        "confirm_selector": "text=Pizza Palace", "confirm_contains": "Pizza Palace",
    }
    b.finish(html, journey, "Real Food Delivery", port=5022)


def build_ride_hailing(root: Path):
    b = AppBuilder(root, "ride_hailing", "ride hailing", "2300")

    b.add_capability("2301", "List Rides", "/api/rides", "GET",
        "def handle(request):\n    return 200, {'rides': _load()}\n",
        output_fields=("rides",))

    b.add_capability("2302", "Request Ride", "/api/rides", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    pickup = (body.get('pickup') or '').strip()\n"
        "    if not pickup:\n        return 400, {'error': 'pickup is required'}\n"
        "    dropoff = body.get('dropoff') or ''\n"
        "    rides = _load()\n"
        "    next_id = (max([r['id'] for r in rides], default=0)) + 1\n"
        "    ride = {'id': next_id, 'pickup': pickup, 'dropoff': dropoff, 'status': 'requested'}\n"
        "    rides.append(ride)\n    _save(rides)\n    return 201, ride\n",
        output_fields=("id", "pickup", "dropoff", "status"), required_input=("pickup",),
        side_effects=("creates_record",), slot_id="ride_list", selector="#ride-list")

    b.add_capability("2303", "Update Ride Status", "/api/rides/status", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    rid = body.get('id')\n    status = body.get('status') or 'requested'\n"
        "    rides = _load()\n"
        "    for r in rides:\n"
        "        if r['id'] == rid:\n            r['status'] = status\n            _save(rides)\n            return 200, r\n"
        "    return 404, {'error': f'no ride with id {rid!r}'}\n",
        output_fields=("id", "status"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="ride-pickup" placeholder="Pickup location" data-slot="ride_pickup">
    <input id="ride-dropoff" placeholder="Dropoff location" data-slot="ride_dropoff">
    <button id="request-ride-btn" data-slot="request_ride">Request ride</button>
  </div>
</div>
<div class="card"><ul id="ride-list" data-slot="ride_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/rides").then(r => r.json()).then(data => {
    const list = document.getElementById("ride-list");
    list.innerHTML = "";
    (data.rides || []).forEach(r => {
      const li = document.createElement("li");
      li.textContent = r.pickup + " -> " + r.dropoff + " (" + r.status + ")";
      if (r.status === "requested") {
        const accept = document.createElement("button"); accept.textContent = "Accept"; accept.style.marginLeft = "8px";
        accept.addEventListener("click", () => {
          fetch("/api/rides/status", {method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({id: r.id, status: "accepted"})}).then(refresh);
        });
        li.appendChild(accept);
      }
      list.appendChild(li);
    });
  });
}
document.getElementById("request-ride-btn").addEventListener("click", () => {
  const pickup = document.getElementById("ride-pickup").value;
  const dropoff = document.getElementById("ride-dropoff").value;
  if (!pickup.trim()) return;
  fetch("/api/rides", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({pickup: pickup, dropoff: dropoff})}).then(() => {
      document.getElementById("ride-pickup").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Ride Hailing", "", body_inner, script)
    journey = {
        "input_selector": "#ride-pickup", "input_value": "Main St",
        "action_selector": "#request-ride-btn",
        "confirm_selector": "text=Main St", "confirm_contains": "Main St",
    }
    b.finish(html, journey, "Real Ride Hailing", port=5023)


def build_fitness_tracking(root: Path):
    b = AppBuilder(root, "fitness_tracking", "fitness tracking", "3800")

    b.add_capability("3801", "List Workouts", "/api/workouts", "GET",
        "def handle(request):\n    return 200, {'workouts': _load()}\n",
        output_fields=("workouts",))

    b.add_capability("3802", "Log Workout", "/api/workouts", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    wtype = (body.get('type') or '').strip()\n"
        "    if not wtype:\n        return 400, {'error': 'type is required'}\n"
        "    try:\n        duration = float(body.get('duration', 0) or 0)\n    except (TypeError, ValueError):\n        duration = 0.0\n"
        "    workouts = _load()\n"
        "    next_id = (max([w['id'] for w in workouts], default=0)) + 1\n"
        "    workout = {'id': next_id, 'type': wtype, 'duration': duration}\n"
        "    workouts.append(workout)\n    _save(workouts)\n    return 201, workout\n",
        output_fields=("id", "type", "duration"), required_input=("type",),
        side_effects=("creates_record",), slot_id="workout_list", selector="#workout-list")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="workout-type" placeholder="Workout type (e.g. Running)" data-slot="workout_type">
    <input id="workout-duration" type="number" placeholder="Duration (min)" data-slot="workout_duration">
    <button id="log-workout-btn" data-slot="log_workout">Log workout</button>
  </div>
</div>
<div class="card"><ul id="workout-list" data-slot="workout_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/workouts").then(r => r.json()).then(data => {
    const list = document.getElementById("workout-list");
    list.innerHTML = "";
    (data.workouts || []).forEach(w => {
      const li = document.createElement("li");
      li.textContent = w.type + " -- " + w.duration + " min";
      list.appendChild(li);
    });
  });
}
document.getElementById("log-workout-btn").addEventListener("click", () => {
  const type = document.getElementById("workout-type").value;
  const duration = document.getElementById("workout-duration").value;
  if (!type.trim()) return;
  fetch("/api/workouts", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({type: type, duration: duration})}).then(() => {
      document.getElementById("workout-type").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Fitness Tracking", "", body_inner, script)
    journey = {
        "input_selector": "#workout-type", "input_value": "Running",
        "action_selector": "#log-workout-btn",
        "confirm_selector": "text=Running", "confirm_contains": "Running",
    }
    b.finish(html, journey, "Real Fitness Tracking", port=5038)


def build_meditation(root: Path):
    b = AppBuilder(root, "meditation_and_wellbeing", "meditation and wellbeing", "3900")

    b.add_capability("3901", "List Sessions", "/api/sessions", "GET",
        "def handle(request):\n    return 200, {'sessions': _load()}\n",
        output_fields=("sessions",))

    b.add_capability("3902", "Log Session", "/api/sessions", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    stype = (body.get('type') or '').strip()\n"
        "    if not stype:\n        return 400, {'error': 'type is required'}\n"
        "    try:\n        duration = float(body.get('duration', 0) or 0)\n    except (TypeError, ValueError):\n        duration = 0.0\n"
        "    sessions = _load()\n"
        "    next_id = (max([s['id'] for s in sessions], default=0)) + 1\n"
        "    session = {'id': next_id, 'type': stype, 'duration': duration}\n"
        "    sessions.append(session)\n    _save(sessions)\n    return 201, session\n",
        output_fields=("id", "type", "duration"), required_input=("type",),
        side_effects=("creates_record",), slot_id="session_list", selector="#session-list")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="session-type" placeholder="Session type (e.g. Breathing)" data-slot="session_type">
    <input id="session-duration" type="number" placeholder="Duration (min)" data-slot="session_duration">
    <button id="log-session-btn" data-slot="log_session">Log session</button>
  </div>
</div>
<div class="card"><ul id="session-list" data-slot="session_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/sessions").then(r => r.json()).then(data => {
    const list = document.getElementById("session-list");
    list.innerHTML = "";
    (data.sessions || []).forEach(s => {
      const li = document.createElement("li");
      li.textContent = s.type + " -- " + s.duration + " min";
      list.appendChild(li);
    });
  });
}
document.getElementById("log-session-btn").addEventListener("click", () => {
  const type = document.getElementById("session-type").value;
  const duration = document.getElementById("session-duration").value;
  if (!type.trim()) return;
  fetch("/api/sessions", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({type: type, duration: duration})}).then(() => {
      document.getElementById("session-type").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Meditation", "", body_inner, script)
    journey = {
        "input_selector": "#session-type", "input_value": "Breathing",
        "action_selector": "#log-session-btn",
        "confirm_selector": "text=Breathing", "confirm_contains": "Breathing",
    }
    b.finish(html, journey, "Real Meditation", port=5039)


def build_email_client(root: Path):
    b = AppBuilder(root, "email_client", "email client", "1400")

    b.add_capability("1401", "List Inbox", "/api/inbox", "GET",
        "def handle(request):\n    return 200, {'inbox': _load()}\n",
        output_fields=("inbox",))

    b.add_capability("1402", "Send Email", "/api/emails/send", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    to = (body.get('to') or '').strip()\n    subject = (body.get('subject') or '').strip()\n"
        "    if not to or not subject:\n        return 400, {'error': 'to and subject are required'}\n"
        "    text = body.get('body') or ''\n"
        "    inbox = _load()\n"
        "    next_id = (max([e['id'] for e in inbox], default=0)) + 1\n"
        "    # Real local delivery within this single mailbox app; NOT a real\n"
        "    # SMTP/IMAP transport to an external mail server -- flagged plainly.\n"
        "    email = {'id': next_id, 'to': to, 'subject': subject, 'body': text, 'folder': 'inbox'}\n"
        "    inbox.append(email)\n    _save(inbox)\n    return 201, email\n",
        output_fields=("id", "to", "subject", "body", "folder"), required_input=("to", "subject"),
        side_effects=("creates_record",), slot_id="inbox_list", selector="#inbox-list")

    body_inner = '''<div class="card">
  <div class="row">
    <input id="mail-to" placeholder="To" value="team@example.com" data-slot="mail_to">
    <input id="mail-subject" placeholder="Subject" data-slot="mail_subject" style="flex:1">
    <input id="mail-body" placeholder="Body" data-slot="mail_body" style="flex:1">
    <button id="send-email-btn" data-slot="send_email">Send</button>
  </div>
  <p style="color:#888;font-size:12px">Note: real local delivery within this app's own inbox; no real SMTP/IMAP transport is wired.</p>
</div>
<div class="card"><ul id="inbox-list" data-slot="inbox_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/inbox").then(r => r.json()).then(data => {
    const list = document.getElementById("inbox-list");
    list.innerHTML = "";
    (data.inbox || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = "To: " + e.to + " -- " + e.subject;
      list.appendChild(li);
    });
  });
}
document.getElementById("send-email-btn").addEventListener("click", () => {
  const to = document.getElementById("mail-to").value;
  const subject = document.getElementById("mail-subject").value;
  const body = document.getElementById("mail-body").value;
  if (!to.trim() || !subject.trim()) return;
  fetch("/api/emails/send", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({to: to, subject: subject, body: body})}).then(() => {
      document.getElementById("mail-subject").value = "";
      document.getElementById("mail-body").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Email Client", "", body_inner, script)
    journey = {
        "input_selector": "#mail-subject", "input_value": "Meeting notes",
        "action_selector": "#send-email-btn",
        "confirm_selector": "text=Meeting notes", "confirm_contains": "Meeting notes",
    }
    b.finish(html, journey, "Real Email Client", port=5014)


def build_video_conferencing(root: Path):
    b = AppBuilder(root, "video_conferencing", "video conferencing", "1300")

    b.add_capability("1301", "List Rooms", "/api/rooms", "GET",
        "def handle(request):\n    return 200, {'rooms': _load()}\n",
        output_fields=("rooms",))

    b.add_capability("1302", "Create Room", "/api/rooms", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    name = (body.get('name') or '').strip()\n"
        "    if not name:\n        return 400, {'error': 'name is required'}\n"
        "    rooms = _load()\n"
        "    next_id = (max([r['id'] for r in rooms], default=0)) + 1\n"
        "    room = {'id': next_id, 'name': name, 'participants': []}\n"
        "    rooms.append(room)\n    _save(rooms)\n    return 201, room\n",
        output_fields=("id", "name", "participants"), required_input=("name",),
        side_effects=("creates_record",), slot_id="room_list", selector="#room-list")

    b.add_capability("1303", "Join Room", "/api/rooms/join", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    rid = body.get('id')\n    participant = (body.get('participant') or '').strip()\n"
        "    if rid is None or not participant:\n        return 400, {'error': 'id and participant are required'}\n"
        "    rooms = _load()\n"
        "    for r in rooms:\n"
        "        if r['id'] == rid:\n"
        "            if participant not in r['participants']:\n                r['participants'].append(participant)\n"
        "            _save(rooms)\n            return 200, r\n"
        "    return 404, {'error': f'no room with id {rid!r}'}\n",
        output_fields=("id", "name", "participants"), required_input=("id", "participant"),
        side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="room-name" placeholder="Room name" data-slot="room_name">
    <button id="create-room-btn" data-slot="create_room">Create room</button>
  </div>
  <p style="color:#888;font-size:12px">Note: real room/participant session state; no real audio/video (WebRTC) media transport is wired in this sandbox.</p>
</div>
<div class="card"><ul id="room-list" data-slot="room_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/rooms").then(r => r.json()).then(data => {
    const list = document.getElementById("room-list");
    list.innerHTML = "";
    (data.rooms || []).forEach(r => {
      const li = document.createElement("li");
      li.textContent = r.name + " -- participants: " + r.participants.join(", ");
      const join = document.createElement("button"); join.textContent = "Join as Guest"; join.style.marginLeft = "8px";
      join.addEventListener("click", () => {
        fetch("/api/rooms/join", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: r.id, participant: "Guest"})}).then(refresh);
      });
      li.appendChild(join);
      list.appendChild(li);
    });
  });
}
document.getElementById("create-room-btn").addEventListener("click", () => {
  const name = document.getElementById("room-name").value;
  if (!name.trim()) return;
  fetch("/api/rooms", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({name: name})}).then(() => {
      document.getElementById("room-name").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Video Conferencing", "", body_inner, script)
    journey = {
        "input_selector": "#room-name", "input_value": "Standup",
        "action_selector": "#create-room-btn",
        "confirm_selector": "text=Standup", "confirm_contains": "Standup",
    }
    b.finish(html, journey, "Real Video Conferencing", port=5013)


def build_short_video_feed(root: Path):
    b = AppBuilder(root, "short_video_feed", "short video feed", "3400")

    b.add_capability("3401", "List Videos", "/api/videos", "GET",
        "def handle(request):\n    return 200, {'videos': _load()}\n",
        output_fields=("videos",))

    b.add_capability("3402", "Upload Video", "/api/videos", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    caption = (body.get('caption') or '').strip()\n"
        "    if not caption:\n        return 400, {'error': 'caption is required'}\n"
        "    videos = _load()\n"
        "    next_id = (max([v['id'] for v in videos], default=0)) + 1\n"
        "    video = {'id': next_id, 'caption': caption, 'views': 0, 'likes': 0}\n"
        "    videos.append(video)\n    _save(videos)\n    return 201, video\n",
        output_fields=("id", "caption", "views", "likes"), required_input=("caption",),
        side_effects=("creates_record",), slot_id="video_list", selector="#short-video-list")

    b.add_capability("3403", "View Video", "/api/videos/view", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    vid = body.get('id')\n    videos = _load()\n"
        "    for v in videos:\n"
        "        if v['id'] == vid:\n            v['views'] += 1\n            _save(videos)\n            return 200, v\n"
        "    return 404, {'error': f'no video with id {vid!r}'}\n",
        output_fields=("id", "views"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="sv-caption" placeholder="Caption" data-slot="sv_caption" style="flex:1">
    <button id="upload-video-btn" data-slot="upload_video">Upload</button>
  </div>
  <p style="color:#888;font-size:12px">Note: real feed/metadata/view-count loop; no real video encoding or playback asset is wired in this sandbox.</p>
</div>
<div class="card"><ul id="short-video-list" data-slot="video_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/videos").then(r => r.json()).then(data => {
    const list = document.getElementById("short-video-list");
    list.innerHTML = "";
    (data.videos || []).forEach(v => {
      const li = document.createElement("li");
      li.textContent = v.caption + " -- " + v.views + " views";
      const view = document.createElement("button"); view.textContent = "Watch"; view.style.marginLeft = "8px";
      view.addEventListener("click", () => {
        fetch("/api/videos/view", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: v.id})}).then(refresh);
      });
      li.appendChild(view);
      list.appendChild(li);
    });
  });
}
document.getElementById("upload-video-btn").addEventListener("click", () => {
  const caption = document.getElementById("sv-caption").value;
  if (!caption.trim()) return;
  fetch("/api/videos", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({caption: caption})}).then(() => {
      document.getElementById("sv-caption").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Short Video Feed", "", body_inner, script)
    journey = {
        "input_selector": "#sv-caption", "input_value": "Dance clip",
        "action_selector": "#upload-video-btn",
        "confirm_selector": "text=Dance clip", "confirm_contains": "Dance clip",
    }
    b.finish(html, journey, "Real Short Video Feed", port=5034)


def build_music_streaming(root: Path):
    b = AppBuilder(root, "music_streaming", "music streaming", "3500")

    b.add_capability("3501", "List Tracks", "/api/tracks", "GET",
        "def handle(request):\n    return 200, {'tracks': _load()}\n",
        output_fields=("tracks",))

    b.add_capability("3502", "Add Track", "/api/tracks", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    artist = body.get('artist') or 'Unknown Artist'\n"
        "    tracks = _load()\n"
        "    next_id = (max([t['id'] for t in tracks], default=0)) + 1\n"
        "    track = {'id': next_id, 'title': title, 'artist': artist, 'plays': 0}\n"
        "    tracks.append(track)\n    _save(tracks)\n    return 201, track\n",
        output_fields=("id", "title", "artist", "plays"), required_input=("title",),
        side_effects=("creates_record",), slot_id="track_list", selector="#track-list")

    b.add_capability("3503", "Play Track", "/api/tracks/play", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    tid = body.get('id')\n    tracks = _load()\n"
        "    for t in tracks:\n"
        "        if t['id'] == tid:\n            t['plays'] += 1\n            _save(tracks)\n            return 200, t\n"
        "    return 404, {'error': f'no track with id {tid!r}'}\n",
        output_fields=("id", "plays"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="track-title" placeholder="Track title" data-slot="track_title">
    <input id="track-artist" placeholder="Artist" data-slot="track_artist">
    <button id="add-track-btn" data-slot="add_track">Add track</button>
  </div>
  <p style="color:#888;font-size:12px">Note: real catalog/play-count loop; no real licensed audio or streaming transport is wired in this sandbox.</p>
</div>
<div class="card"><ul id="track-list" data-slot="track_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/tracks").then(r => r.json()).then(data => {
    const list = document.getElementById("track-list");
    list.innerHTML = "";
    (data.tracks || []).forEach(t => {
      const li = document.createElement("li");
      li.textContent = t.title + " by " + t.artist + " -- " + t.plays + " plays";
      const play = document.createElement("button"); play.textContent = "Play"; play.style.marginLeft = "8px";
      play.addEventListener("click", () => {
        fetch("/api/tracks/play", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: t.id})}).then(refresh);
      });
      li.appendChild(play);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-track-btn").addEventListener("click", () => {
  const title = document.getElementById("track-title").value;
  const artist = document.getElementById("track-artist").value;
  if (!title.trim()) return;
  fetch("/api/tracks", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title, artist: artist})}).then(() => {
      document.getElementById("track-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Music Streaming", "", body_inner, script)
    journey = {
        "input_selector": "#track-title", "input_value": "Sunrise",
        "action_selector": "#add-track-btn",
        "confirm_selector": "text=Sunrise", "confirm_contains": "Sunrise",
    }
    b.finish(html, journey, "Real Music Streaming", port=5035)


def build_video_streaming(root: Path):
    b = AppBuilder(root, "video_streaming", "video streaming", "3600")

    b.add_capability("3601", "List Videos", "/api/videos", "GET",
        "def handle(request):\n    return 200, {'videos': _load()}\n",
        output_fields=("videos",))

    b.add_capability("3602", "Add Video", "/api/videos", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    videos = _load()\n"
        "    next_id = (max([v['id'] for v in videos], default=0)) + 1\n"
        "    video = {'id': next_id, 'title': title, 'views': 0}\n"
        "    videos.append(video)\n    _save(videos)\n    return 201, video\n",
        output_fields=("id", "title", "views"), required_input=("title",),
        side_effects=("creates_record",), slot_id="video_list", selector="#vs-video-list")

    b.add_capability("3603", "Watch Video", "/api/videos/watch", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    vid = body.get('id')\n    videos = _load()\n"
        "    for v in videos:\n"
        "        if v['id'] == vid:\n            v['views'] += 1\n            _save(videos)\n            return 200, v\n"
        "    return 404, {'error': f'no video with id {vid!r}'}\n",
        output_fields=("id", "views"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="vs-title" placeholder="Video title" data-slot="vs_title" style="flex:1">
    <button id="add-vs-video-btn" data-slot="add_vs_video">Add video</button>
  </div>
  <p style="color:#888;font-size:12px">Note: real catalog/view-count loop; no real video encoding or streaming transport is wired in this sandbox.</p>
</div>
<div class="card"><ul id="vs-video-list" data-slot="video_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/videos").then(r => r.json()).then(data => {
    const list = document.getElementById("vs-video-list");
    list.innerHTML = "";
    (data.videos || []).forEach(v => {
      const li = document.createElement("li");
      li.textContent = v.title + " -- " + v.views + " views";
      const watch = document.createElement("button"); watch.textContent = "Watch"; watch.style.marginLeft = "8px";
      watch.addEventListener("click", () => {
        fetch("/api/videos/watch", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: v.id})}).then(refresh);
      });
      li.appendChild(watch);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-vs-video-btn").addEventListener("click", () => {
  const title = document.getElementById("vs-title").value;
  if (!title.trim()) return;
  fetch("/api/videos", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => {
      document.getElementById("vs-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Video Streaming", "", body_inner, script)
    journey = {
        "input_selector": "#vs-title", "input_value": "Documentary Pilot",
        "action_selector": "#add-vs-video-btn",
        "confirm_selector": "text=Documentary Pilot", "confirm_contains": "Documentary Pilot",
    }
    b.finish(html, journey, "Real Video Streaming", port=5036)


def build_podcast(root: Path):
    b = AppBuilder(root, "podcast", "podcast", "3700")

    b.add_capability("3701", "List Episodes", "/api/episodes", "GET",
        "def handle(request):\n    return 200, {'episodes': _load()}\n",
        output_fields=("episodes",))

    b.add_capability("3702", "Add Episode", "/api/episodes", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    title = (body.get('title') or '').strip()\n"
        "    if not title:\n        return 400, {'error': 'title is required'}\n"
        "    episodes = _load()\n"
        "    next_id = (max([e['id'] for e in episodes], default=0)) + 1\n"
        "    episode = {'id': next_id, 'title': title, 'plays': 0}\n"
        "    episodes.append(episode)\n    _save(episodes)\n    return 201, episode\n",
        output_fields=("id", "title", "plays"), required_input=("title",),
        side_effects=("creates_record",), slot_id="episode_list", selector="#episode-list")

    b.add_capability("3703", "Play Episode", "/api/episodes/play", "POST",
        "def handle(request):\n"
        "    body = request.get_json(force=True, silent=True) or {}\n"
        "    eid = body.get('id')\n    episodes = _load()\n"
        "    for e in episodes:\n"
        "        if e['id'] == eid:\n            e['plays'] += 1\n            _save(episodes)\n            return 200, e\n"
        "    return 404, {'error': f'no episode with id {eid!r}'}\n",
        output_fields=("id", "plays"), required_input=("id",), side_effects=("updates_record",))

    body_inner = '''<div class="card">
  <div class="row">
    <input id="ep-title" placeholder="Episode title" data-slot="ep_title" style="flex:1">
    <button id="add-episode-btn" data-slot="add_episode">Add episode</button>
  </div>
  <p style="color:#888;font-size:12px">Note: real catalog/play-count loop; no real audio encoding or streaming transport is wired in this sandbox.</p>
</div>
<div class="card"><ul id="episode-list" data-slot="episode_list"></ul></div>'''
    script = '''
function refresh() {
  fetch("/api/episodes").then(r => r.json()).then(data => {
    const list = document.getElementById("episode-list");
    list.innerHTML = "";
    (data.episodes || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = e.title + " -- " + e.plays + " plays";
      const play = document.createElement("button"); play.textContent = "Play"; play.style.marginLeft = "8px";
      play.addEventListener("click", () => {
        fetch("/api/episodes/play", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({id: e.id})}).then(refresh);
      });
      li.appendChild(play);
      list.appendChild(li);
    });
  });
}
document.getElementById("add-episode-btn").addEventListener("click", () => {
  const title = document.getElementById("ep-title").value;
  if (!title.trim()) return;
  fetch("/api/episodes", {method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({title: title})}).then(() => {
      document.getElementById("ep-title").value = "";
      refresh();
    });
});
refresh();
'''
    html = page_skeleton("Podcast", "", body_inner, script)
    journey = {
        "input_selector": "#ep-title", "input_value": "Episode 1: Intro",
        "action_selector": "#add-episode-btn",
        "confirm_selector": "text=Episode 1: Intro", "confirm_contains": "Episode 1: Intro",
    }
    b.finish(html, journey, "Real Podcast", port=5037)
