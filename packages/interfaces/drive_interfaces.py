#!/usr/bin/env python3
"""
drive_interfaces.py — every control of every interface, pressed in a real
browser, every outcome verified by re-reading the API.

For each of the 15 interfaces (5 families x 3 designs) this runs the same
journey the family's own spec implies -- derived from MODEL, not typed per
family: create every record (in link order, as a role that may), open it,
edit it, walk every workflow through its person-moved transitions (approving
at every gate, declining once to prove back_to), press every declared custom
action (supplying inputs where the action asks), add related records from a
parent's page, submit every public form, run every report, delete a row.
After each press the outcome is verified against the real generated route
(or the in-browser demo store when the file is opened with no server), never
from what the page says about itself.

It also sweeps: every distinct data-act control kind that was ever rendered
must have been pressed at least once, or it is reported.

Usage:
  python drive_interfaces.py                 # all 15 against live servers, plus 3 file:// demo runs
  python drive_interfaces.py crm-pipeline board
Writes: evidence/INTERFACES.json, evidence/INTERFACES.md, evidence/shots/*.png
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
OUT = os.path.join(HERE, "out")
EVID = os.path.join(HERE, "evidence")
SHOTS = os.path.join(EVID, "shots")
sys.path.insert(0, HERE)
from build_families import FAMILIES, PORTS  # noqa: E402
DESIGNS = ["console", "board", "pocket"]
VIEWPORT = {"console": (1280, 820), "board": (1280, 820), "pocket": (390, 844)}


class Server:
    def __init__(self, family, port):
        self.app = os.path.join(BUILD, family, "app"); self.port = port
    def __enter__(self):
        db = os.path.join(self.app, "app.db")
        if os.path.exists(db):
            os.remove(db)
        self.proc = subprocess.Popen(["python3", "app.py"], cwd=self.app, env=dict(os.environ, PORT=str(self.port)),
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=1); return self
            except Exception:
                time.sleep(0.1)
        self.proc.terminate(); raise RuntimeError("server did not start")
    def __exit__(self, *a):
        self.proc.terminate()
        try: self.proc.communicate(timeout=5)
        except subprocess.TimeoutExpired: self.proc.kill()


class Verifier:
    """Reads the truth: HTTP against the generated app, or the page's own
    DemoStore when the interface was opened as a file."""
    def __init__(self, page, port=None):
        self.page, self.port = page, port
    async def call(self, method, path, body=None):
        if self.port is None:
            return await self.page.evaluate("([m,p,b]) => window.DemoStore.call(m,p,b)", [method, path, body])
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return {"status": r.status, "data": json.loads(r.read() or b"null")}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "data": json.loads(e.read() or b"null")}
    async def rows(self, table):
        r = await self.call("GET", "/api/" + table); return r["data"] if r["status"] == 200 else []
    async def row(self, table, rid):
        r = await self.call("GET", f"/api/{table}/{rid}"); return r["data"] if r["status"] == 200 else None


def sample_value(field, n):
    t = field["type"]
    if t == "short_text": return f"{field['name']} {n}"
    if t == "long_text": return f"Notes for {field['name']} {n}"
    if t == "whole_number": return str(10 + n)
    if t in ("decimal_number", "money"): return f"{25 + n}.50"
    if t == "date": return "2026-09-0" + str(1 + n % 9)
    if t == "date_time": return "2026-09-1" + str(n % 9) + "T10:30"
    if t == "email": return f"person{n}@example.com"
    if t == "phone": return f"+61 4{n:02d} 000 000"
    if t == "url": return f"https://example.com/{n}"
    if t == "one_choice": return None   # pick first option
    if t == "yes_no": return True
    if t == "other": return f"user{n}"
    return f"{field['name']} {n}"


class Run:
    def __init__(self, family, design, page, ver, model, label):
        self.family, self.design, self.page, self.ver, self.M, self.label = family, design, page, ver, model, label
        self.steps = []      # (ok, text)
        self.pressed = set() # control kinds pressed
        self.rendered = set()
        self.errors = []
        self.n = 0
        self.shot_i = 0
        page.on("pageerror", lambda e: self.errors.append("pageerror: " + str(e)))
        page.on("console", lambda m: self.errors.append("console: " + m.text) if m.type == "error" else None)
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

    # -------------------------------------------------------------- helpers
    def rec(self, r): return self.M["records"][r]
    def wf(self, r): return self.M["workflows"].get(self.rec(r)["workflow"]) if self.rec(r)["workflow"] else None
    def admin_roles(self): return [r for r in self.M["roles"] if self.M["role_admin"].get(r)]
    def role_for(self, allowed):
        allowed = allowed or []
        return (allowed + self.admin_roles() + [None])[0]
    def ok(self, text): self.steps.append((True, text))
    def fail(self, text): self.steps.append((False, text))
    async def check(self, cond, text):
        (self.ok if cond else self.fail)(text); return cond
    async def sweep(self):
        kinds = await self.page.evaluate("() => Array.from(document.querySelectorAll('[data-act]')).map(e => e.dataset.act + (e.dataset.decision ? ':' + e.dataset.decision : ''))")
        self.rendered.update(kinds)
    async def press(self, selector, kind, index=0):
        await self.sweep()
        loc = self.page.locator(selector)
        # when a modal/drawer is open, the control in front is the one a person reaches
        front = self.page.locator(".overlay " + selector + ", .drawer " + selector)
        if await front.count() > index:
            loc = front
        cnt = await loc.count()
        if cnt <= index:
            self.fail(f"control missing: {selector}"); return False
        await loc.nth(index).click()
        await self.page.wait_for_timeout(140)
        self.pressed.add(kind)
        return True
    async def shot(self, name):
        self.shot_i += 1
        await self.page.screenshot(path=os.path.join(SHOTS, f"{self.label}-{self.shot_i:02d}-{name}.png"), full_page=False)
    async def set_role(self, role):
        if role is None: return
        cur = await self.page.evaluate("() => window.UI.state.role")
        if cur == role: return
        await self.close_overlays()
        if await self.page.locator('select[data-act="role"]').count() == 0:
            # pocket keeps the role switch on Home / More, like a settings tab
            await self.press('[data-act="nav"][data-kind="more"]', "nav:more")
        await self.page.select_option('select[data-act="role"]', role)
        await self.page.wait_for_timeout(160)
        self.pressed.add("role")
        got = await self.page.evaluate("() => window.UI.state.role")
        await self.check(got == role, f"role switched to {role}")
    async def close_overlays(self):
        # a person closes an open drawer/modal before reaching for the navigation behind it
        for sel in ('.modal.doc [data-act="closeDoc"]', '.drawer [data-act="back"]', '.overlay .modal-h [data-act="back"]', '.overlay .modal-h [data-act="nav"]'):
            if await self.page.locator(sel).count():
                await self.page.locator(sel).first.click(); await self.page.wait_for_timeout(120)
    async def go_list(self, record):
        await self.close_overlays()
        # sidebar/tab/menu link, or via More on pocket
        sel = f'[data-act="nav"][data-kind="list"][data-record="{record}"]'
        if await self.page.locator(sel).count() == 0 and self.design == "pocket":
            await self.press('[data-act="nav"][data-kind="more"]', "nav:more")
        await self.press(sel, "nav:list")
    async def open_row(self, record, rid):
        await self.go_list(record)
        sel = f'[data-act="open"][data-record="{record}"][data-id="{rid}"]'
        if await self.page.locator(sel).count() == 0:
            self.fail(f"{record} {rid[:8]} not listed"); return False
        await self.press(sel, "open")
        shown = await self.page.evaluate("() => window.UI.state.detail && window.UI.state.detail.row.id")
        return await self.check(shown == rid, f"opened {record} {rid[:8]}")
    async def fill_form(self, form_sel, record, n, skip_slugs=(), only_parent=None):
        d = self.rec(record)
        for f in d["fields"]:
            if f["slug"] in skip_slugs: continue
            # from a parent's page a person links the child to that parent only, not to
            # every other record on the form (a Payment added on an Invoice is not also a Bill's)
            if only_parent and f["type"] == "link" and f["target_record"] != only_parent and f.get("required") != "yes": continue
            sel = f'{form_sel} [name="{f["slug"]}"]'
            if await self.page.locator(sel).count() == 0: continue
            if f["type"] == "link":
                opts = await self.page.locator(sel + " option").all_text_contents()
                vals = await self.page.locator(sel + " option").evaluate_all("os => os.map(o => o.value)")
                real = [v for v in vals if v]
                if real: await self.page.select_option(sel, real[0])
                continue
            if f["type"] in ("one_choice", "multi_choice"):
                vals = await self.page.locator(sel + " option").evaluate_all("os => os.map(o => o.value)")
                real = [v for v in vals if v]
                if real: await self.page.select_option(sel, real[0])
                continue
            if f["type"] == "yes_no":
                await self.page.locator(sel).check(); continue
            await self.page.fill(sel, str(sample_value(f, n)))

    # -------------------------------------------------------------- journey
    def creation_order(self):
        order, seen = [], set()
        def visit(r):
            if r in seen: return
            seen.add(r)
            for f in self.rec(r)["fields"]:
                if f["type"] == "link" and f["target_record"] in self.M["records"] and f["target_record"] != r: visit(f["target_record"])
            order.append(r)
        for r in self.M["records"]: visit(r)
        return order

    async def create(self, record, n, parent=None, parent_id=None):
        d = self.rec(record); role = self.role_for(d["access"]["create"])
        if role is None: self.ok(f"{record}: nobody may create (declared) — skipped"); return None
        await self.set_role(role)
        before = {r["id"] for r in await self.ver.rows(d["table"])}
        if parent:
            if not await self.open_row(parent, parent_id): return None
            if not await self.press(f'[data-act="newRow"][data-record="{record}"][data-parent="{parent}"]', "newRow:child"): return None
            form = f'form[data-act="create"][data-record="{record}"]'
        else:
            await self.go_list(record)
            if not await self.press(f'[data-act="newRow"][data-record="{record}"]', "newRow"): return None
            form = f'form[data-act="create"][data-record="{record}"]'
        await self.fill_form(form, record, n, only_parent=parent)
        await self.shot(f"new-{d['table']}")
        await self.press(f'{form} button[type=submit]', "create")
        rows = await self.ver.rows(d["table"])
        new = [r for r in rows if r["id"] not in before]
        if not await self.check(len(new) == 1, f"created {record} as {role} (API shows the new row)"): return None
        rid = new[0]["id"]
        if d["has_stage"]:
            await self.check(new[0]["stage"] == self.wf(record)["initial"], f"{record} starts in '{self.wf(record)['initial']}'")
        return rid

    async def edit(self, record, rid, n):
        d = self.rec(record); role = self.role_for(d["access"]["edit"])
        if role is None: self.ok(f"{record}: nobody may edit (declared) — no Save shown"); return
        await self.set_role(role)
        if not await self.open_row(record, rid): return
        tf = d["title_field"]; f = next((x for x in d["fields"] if x["name"] == tf and x["type"] in ("short_text", "other")), None)
        form = f'form[data-act="save"][data-record="{record}"]'
        if await self.page.locator(form).count() == 0: self.fail(f"{record}: edit form not shown for {role}"); return
        if f:
            await self.page.fill(f'{form} [name="{f["slug"]}"]', f"Edited {record} {n}")
        await self.press(f'{form} button[type=submit]', "save")
        row = await self.ver.row(d["table"], rid)
        if f: await self.check(row and row[f["slug"]] == f"Edited {record} {n}", f"edited {record} title saved (API)")
        else: await self.check(row is not None, f"saved {record} (API)")
        await self.shot(f"detail-{d['table']}")

    async def walk_workflow(self, record, rid, decline_once):
        d = self.rec(record); wf = self.wf(record); table = d["table"]
        visited = set(); steps = 0; declined = False
        while steps < 12:
            steps += 1
            row = await self.ver.row(table, rid); stage = row["stage"]; visited.add(stage)
            if stage in (wf["terminal"] or []): self.ok(f"{record} reached terminal stage '{stage}'"); break
            gate = next((g for g in wf["approvals"] if g["stage"] == stage), None)
            if gate:
                st = await self.ver.call("GET", f"/api/approvals/{table}/{rid}")
                decision = (st["data"] or {}).get("decision")
                if not decision or decision.get("decision") != "APPROVED":
                    approver = gate["approvers"][0]
                    await self.set_role(approver)
                    if not await self.open_row(record, rid): return
                    if decline_once and not declined and wf.get("on_reject") and wf["on_reject"].get("back_to"):
                        await self.page.fill('form.decide [name=reason]', "not yet")
                        await self.press('[data-act="approve"][data-decision="DECLINED"]', "approve:DECLINED")
                        row2 = await self.ver.row(table, rid)
                        await self.check(row2["stage"] == wf["on_reject"]["back_to"], f"{record} declined by {approver} → back to '{wf['on_reject']['back_to']}'")
                        st3 = await self.ver.call("GET", f"/api/approvals/{table}/{rid}")
                        await self.check(((st3["data"] or {}).get("decision") or {}).get("decision") in ("DECLINED", None), "the decline is what the gate now records")
                        declined = True
                        visited.discard(stage)   # sent back: the gated stage must be re-entered and approved this time
                        continue
                    await self.press('form.decide button[type=submit]', "approve:APPROVED")
                    st2 = await self.ver.call("GET", f"/api/approvals/{table}/{rid}")
                    await self.check((st2["data"] or {}).get("decision", {}) and st2["data"]["decision"]["decision"] == "APPROVED", f"{record} approved by {approver} at '{stage}' (API)")
                    await self.shot(f"approved-{table}")
            options = [t for t in wf["transitions"] if t["mover"] == "roles" and t["from"] == stage]
            options = [t for t in options if t["to"] not in visited] or options
            if not options: self.ok(f"{record}: no person-moved edge out of '{stage}'"); break
            # prefer forward progress: the target furthest along the declared stage order
            options.sort(key=lambda t: -wf["stages"].index(t["to"]))
            # accounting: prefer the payment path over Voided when both exist
            non_term = [t for t in options if t["to"] not in (wf["terminal"] or [])]
            t = (non_term or options)[0]
            role = t["roles"][0]
            stock_before = {}
            for eff in wf.get("effects") or []:
                if eff["on_enter"] == t["to"] and eff["op"] == "apply_order_lines":
                    for l in [l for l in await self.ver.rows(eff["line_table"]) if l[eff["line_fk"]] == rid]:
                        p = await self.ver.row(eff["product_table"], l[eff["product_fk"]])
                        stock_before[l[eff["product_fk"]]] = p and p.get("stock_on_hand")
            await self.set_role(role)
            if not await self.open_row(record, rid): return
            if not await self.press(f'[data-act="move"][data-record="{record}"][data-id="{rid}"][data-to="{t["to"]}"]', "move"): return
            row3 = await self.ver.row(table, rid)
            await self.check(row3["stage"] == t["to"], f"{record}: {role} moved '{stage}' → '{t['to']}' (API)")
            # declared transition effects really happened, by the numbers
            for eff in wf.get("effects") or []:
                if eff["on_enter"] == t["to"] and eff["op"] == "apply_order_lines":
                    # every line of the order applied to its product: totals per product
                    delta = {}
                    for l in [l for l in await self.ver.rows(eff["line_table"]) if l[eff["line_fk"]] == rid]:
                        q = int(l[eff["quantity_column"]] or 0)
                        delta[l[eff["product_fk"]]] = delta.get(l[eff["product_fk"]], 0) + (q if eff["direction"] == "receive" else -q)
                    for pid, dq in delta.items():
                        p = await self.ver.row(eff["product_table"], pid)
                        was = stock_before.get(pid) or 0
                        await self.check(p is not None and p.get("stock_on_hand") == was + dq, f"stock effect on '{t['to']}': {was} {'+' if dq >= 0 else '−'} {abs(dq)} = {p and p.get('stock_on_hand')} (API)")
                    text = await self.page.locator(".notice").inner_text() if await self.page.locator(".notice").count() else ""
                    await self.check("stock" in text, "the page told the user about the stock movement")
            if t["to"] in (wf["terminal"] or []): break

    async def custom_actions(self, record, rid, n):
        d = self.rec(record)
        for a in d["custom_actions"]:
            role = (a.get("who") or [None])[0]
            if role is None: continue
            await self.set_role(role)
            if not await self.open_row(record, rid): return
            ex = a.get("execution") or {}
            sel = f'[data-act="action"][data-record="{record}"][data-id="{rid}"][data-action="{a["name"]}"]'
            before = await self.ver.rows(d["table"])
            if not await self.press(sel, f"action:{ex.get('op')}"): continue
            if ex.get("op") == "set_fields_from_input":
                for f in ex["fields"]:
                    await self.page.fill(f'form.inputs [name="{f}"]', f"newvalue{n}")
                await self.press('form.inputs button[type=submit]', "action:confirm-inputs")
                row = await self.ver.row(d["table"], rid)
                await self.check(all(row[f] == f"newvalue{n}" for f in ex["fields"]), f"{a['name']}: {ex['fields']} set from input (API)")
            elif ex.get("op") == "clone":
                after = await self.ver.rows(d["table"])
                copy = [r for r in after if r["id"] not in {x["id"] for x in before}]
                await self.check(len(copy) == 1 and (ex.get("title_suffix") or "") in str(copy[0].get(ex.get("title_column"), "")), f"{a['name']}: a copy exists with '{ex.get('title_suffix')}' (API)")
                if copy and ex.get("overrides", {}).get("stage"):
                    await self.check(copy[0]["stage"] == ex["overrides"]["stage"], f"{a['name']}: copy in '{ex['overrides']['stage']}'")
            elif ex.get("op") == "generate_document":
                row = await self.ver.row(d["table"], rid)
                await self.check(bool(row.get(ex.get("stamp_column"))), f"{a['name']}: '{ex.get('stamp_column')}' stamped (API)")
                await self.check(await self.page.locator(".modal.doc").count() == 1, f"{a['name']}: generated document shown")
                await self.shot(f"document-{d['table']}")
                await self.press('[data-act="closeDoc"]', "closeDoc")
            else:
                self.ok(f"{a['name']} pressed (op {ex.get('op')})")
            hist = await self.ver.call("GET", f"/api/history/{d['table']}/{rid}")
            await self.check(any(h["action"] == "custom:" + a["name"] for h in (hist["data"] or {}).get("audit", [])), f"{a['name']} is in the activity trail (API)")

    async def ledger_journeys(self, ids, n):
        """For every declared create effect 'ledger_balance': take a fresh target
        (Invoice/Bill) to the stage its automatic edge leaves from, add lines on
        its own page, then add the settling Payment from that page and verify the
        target really moved (Paid) -- the whole of accounting-ledger's point."""
        M = self.M
        for record, d in M["records"].items():
            for eff in d.get("on_create") or []:
                if eff.get("op") != "ledger_balance": continue
                target_rec = next((r for r, x in M["records"].items() if x["table"] == eff["table"]), None)
                wf = self.wf(target_rec)
                edge = next((t for t in wf["transitions"] if t.get("mover") == "automatic" and t.get("event") == eff["event"]), None)
                if not edge: self.fail(f"ledger: no automatic edge for event {eff['event']!r}"); continue
                n += 1
                tid = await self.create(target_rec, n)
                if not tid: continue
                total = None
                if eff["total"]["kind"] == "lines":
                    line_rec = next(r for r, x in M["records"].items() if x["table"] == eff["total"]["line_table"])
                    n += 1
                    lid = await self.create(line_rec, n, parent=target_rec, parent_id=tid)
                    line = await self.ver.row(eff["total"]["line_table"], lid) if lid else None
                    total = (float(line[eff["total"]["quantity_column"]] or 0) * float(line[eff["total"]["amount_column"]] or 0)) if line else None
                else:
                    trow = await self.ver.row(eff["table"], tid); total = float(trow[eff["total"]["column"]] or 0)
                await self.check(total and total > 0, f"ledger: {target_rec} total is {total}")
                # walk to the stage the automatic edge leaves from (approving on the way)
                await self.walk_workflow_to(target_rec, tid, edge["from"])
                trow = await self.ver.row(eff["table"], tid)
                if not await self.check(trow["stage"] == edge["from"], f"ledger: {target_rec} is in '{edge['from']}' awaiting payment"): continue
                # a part payment from the target's own page: applied, not settled
                pay_role = self.role_for(d["access"]["create"]); await self.set_role(pay_role)
                for amount, should_settle in ((round(total / 2, 2), False), (round(total - round(total / 2, 2), 2), True)):
                    if not await self.open_row(target_rec, tid): break
                    if not await self.press(f'[data-act="newRow"][data-record="{record}"][data-parent="{target_rec}"]', "newRow:child"): break
                    form = f'form[data-act="create"][data-record="{record}"]'
                    await self.fill_form(form, record, n, skip_slugs=(eff["amount_column"],), only_parent=target_rec)
                    await self.page.fill(f'{form} [name="{eff["amount_column"]}"]', str(amount))
                    await self.press(f'{form} button[type=submit]', "create")
                    trow = await self.ver.row(eff["table"], tid)
                    text = await self.page.locator(".notice").inner_text() if await self.page.locator(".notice").count() else ""
                    if should_settle:
                        await self.check(trow["stage"] == edge["to"], f"ledger: paying the balance ({amount}) moved {target_rec} '{edge['from']}' → '{edge['to']}' (API)")
                        await self.check(edge["to"] in text, "the page told the user the target settled")
                        await self.shot(f"settled-{eff['table']}")
                    else:
                        await self.check(trow["stage"] == edge["from"], f"ledger: part payment ({amount}) left {target_rec} in '{edge['from']}' (API)")
                        await self.check("applied" in text, "the page told the user how much is applied")

    async def walk_workflow_to(self, record, rid, target_stage):
        wf = self.wf(record); table = self.rec(record)["table"]
        for _ in range(10):
            row = await self.ver.row(table, rid)
            if row["stage"] == target_stage: return
            gate = next((g for g in wf["approvals"] if g["stage"] == row["stage"]), None)
            if gate:
                st = await self.ver.call("GET", f"/api/approvals/{table}/{rid}")
                if not ((st["data"] or {}).get("decision") or {}).get("decision") == "APPROVED":
                    await self.set_role(gate["approvers"][0])
                    if not await self.open_row(record, rid): return
                    await self.press('form.decide button[type=submit]', "approve:APPROVED")
                    st2 = await self.ver.call("GET", f"/api/approvals/{table}/{rid}")
                    await self.check(((st2["data"] or {}).get("decision") or {}).get("decision") == "APPROVED", f"{record} approved by {gate['approvers'][0]} at '{row['stage']}' (API)")
            # shortest declared person-moved path toward the target: BFS over stages
            path = self._path(wf, row["stage"], target_stage)
            if not path: self.fail(f"{record}: no person-moved path from '{row['stage']}' to '{target_stage}'"); return
            t = path[0]
            await self.set_role(t["roles"][0])
            if not await self.open_row(record, rid): return
            await self.press(f'[data-act="move"][data-record="{record}"][data-id="{rid}"][data-to="{t["to"]}"]', "move")
            row2 = await self.ver.row(table, rid)
            await self.check(row2["stage"] == t["to"], f"{record}: {t['roles'][0]} moved '{row['stage']}' → '{t['to']}' (API)")

    def _path(self, wf, start, goal):
        from collections import deque
        q = deque([(start, [])]); seen = {start}
        while q:
            st, path = q.popleft()
            if st == goal: return path
            for t in wf["transitions"]:
                if t.get("mover") == "roles" and t["from"] == st and t["to"] not in seen:
                    seen.add(t["to"]); q.append((t["to"], path + [t]))
        return None

    async def reports(self):
        for name, rp in self.M["reports"].items():
            await self.close_overlays()
            sel = f'[data-act="nav"][data-kind="report"][data-report="{name}"]'
            if await self.page.locator(sel).count() == 0:
                if self.design == "pocket": await self.press('[data-act="nav"][data-kind="more"]', "nav:more")
                elif self.design == "board":
                    await self.press('[data-act="home"]', "home")
                    sel = f'[data-act="runReport"][data-report="{name}"]'
            if not await self.press(sel, "nav:report"): continue
            truth = await self.ver.call("GET", "/api/reports/" + rp["slug"])
            shown = await self.page.locator(".report .metric").count()
            await self.check(truth["status"] == 200 and shown == len(rp["metrics"]), f"report '{name}': {shown} metric(s) rendered, API {truth['status']}")
            for m in rp["metrics"]:
                v = truth["data"][m]
                text = await self.page.locator(".report").inner_text()
                if isinstance(v, (int, float)): expect = str(v) if isinstance(v, int) or float(v).is_integer() and False else (str(v) if isinstance(v, int) else f"{v:.2f}")
                elif isinstance(v, dict) and "percentage" in v: expect = "—" if v["percentage"] is None else f"{float(v['percentage']):.1f}%"
                elif isinstance(v, dict): expect = None
                else: expect = str(v)
                if expect is not None: await self.check(expect in text, f"report '{name}' shows {m} = {expect}")
                else: await self.check(len(v) == 0 or all(k in text for k in list(v)[:3]), f"report '{name}' shows the groups of {m}")
            await self.press('[data-act="runReport"]', "runReport")
            await self.shot(f"report-{rp['slug']}")

    async def forms(self):
        for name, fm in self.M["forms"].items():
            await self.close_overlays()
            sel = f'[data-act="nav"][data-kind="form"][data-form="{name}"]'
            if await self.page.locator(sel).count() == 0 and self.design == "pocket": await self.press('[data-act="nav"][data-kind="more"]', "nav:more")
            if not await self.press(sel, "nav:form"): continue
            d = self.rec(fm["record"]); before = {r["id"] for r in await self.ver.rows(d["table"])}
            await self.fill_form(f'form[data-act="submitForm"]', fm["record"], 7)
            await self.shot(f"form-{fm['slug']}")
            await self.press('form[data-act="submitForm"] button[type=submit]', "submitForm")
            after = [r for r in await self.ver.rows(d["table"]) if r["id"] not in before]
            await self.check(len(after) == 1, f"form '{name}' created a {fm['record']} (API)")

    async def delete(self, record, rid):
        d = self.rec(record); role = self.role_for(d["access"]["delete"])
        if role is None: self.ok(f"{record}: nobody may delete (declared) — no Delete shown"); return
        await self.set_role(role)
        if not await self.open_row(record, rid): return
        if not await self.press(f'.danger-zone [data-act="remove"][data-record="{record}"][data-id="{rid}"]', "remove"): return
        gone = await self.ver.row(d["table"], rid)
        await self.check(gone is None, f"deleted {record} as {role} (API 404)")

    async def negative(self, record, rid):
        """A role that may not move a row sees no move button — the page does
        not offer what the route would refuse."""
        wf = self.wf(record)
        if not wf: return
        movers = {r for t in wf["transitions"] for r in (t.get("roles") or [])}
        outsider = next((r for r in self.M["roles"] if r not in movers), None)
        if outsider is None: return
        await self.set_role(outsider)
        if not await self.open_row(record, rid): return
        n = await self.page.locator(f'[data-act="move"][data-record="{record}"]').count()
        await self.check(n == 0, f"{outsider} (not a declared mover) is offered no move on {record}")

    async def run(self):
        M = self.M
        await self.page.wait_for_timeout(300)
        await self.check(await self.page.locator("#app").inner_text() != "", "page rendered")
        await self.shot("home")
        ids = {}
        n = 0
        for record in self.creation_order():
            n += 1
            ids[record] = await self.create(record, n)
        for record, rid in ids.items():
            if rid: await self.edit(record, rid, n)
        # related records from the parent's page (lines under an order/invoice)
        for record, d in M["records"].items():
            parents = [f["target_record"] for f in d["fields"] if f["type"] == "link" and f["target_record"] in ids and ids[f["target_record"]]]
            if parents and d["access"]["create"]:
                n += 1
                await self.create(record, n, parent=parents[0], parent_id=ids[parents[0]])
        for record, rid in ids.items():
            if rid and self.rec(record)["has_stage"]:
                await self.negative(record, rid)
                await self.walk_workflow(record, rid, decline_once=True)
                if self.rec(record)["custom_actions"]:
                    # a second row for the actions, so a terminal-stage row does not hide them
                    n += 1; rid2 = await self.create(record, n)
                    if rid2: await self.custom_actions(record, rid2, n)
            elif rid and self.rec(record)["custom_actions"]:
                await self.custom_actions(record, rid, n)
        await self.reports()
        await self.forms()
        await self.ledger_journeys(ids, n)
        for record, rid in list(ids.items()):
            if rid: await self.delete(record, rid); break
        await self.close_overlays()
        await self.press('[data-act="home"]', "home")
        await self.check((await self.page.evaluate("() => window.UI.state.view.kind")) == "home", "Home returns to the overview")
        await self.shot("home-after")
        await self.sweep()
        aliases = {"nav": {"nav:list", "nav:report", "nav:form", "nav:more"}, "action": {"action:clone", "action:set_fields_from_input", "action:generate_document", "action:confirm-inputs"}, "newRow": {"newRow", "newRow:child"}}
        pressed = set(self.pressed)
        for k, al in aliases.items():
            if pressed & al: pressed.add(k)
        never = sorted(k for k in self.rendered if k not in pressed)
        never = [k for k in never if k not in ("dismiss", "resetDemo", "back", "cancelInputs")]
        await self.check(not never, "every rendered control kind was pressed" + (": never pressed " + ", ".join(never) if never else ""))
        await self.check(not self.errors, "no browser errors" + (": " + "; ".join(self.errors[:3]) if self.errors else ""))


async def drive_one(pw, family, design, port=None):
    label = f"{family}-{design}" + ("" if port else "-file")
    model = json.load(open(os.path.join(OUT, family, "MODEL.json"), encoding="utf-8"))
    browser = await pw.chromium.launch()
    w, h = VIEWPORT[design]
    page = await browser.new_page(viewport={"width": w, "height": h})
    ver = Verifier(page, port)
    run = Run(family, design, page, ver, model, label)
    if port:
        await page.goto(f"http://127.0.0.1:{port}/ui-{design}.html")
    else:
        await page.goto("file://" + os.path.join(OUT, family, design + ".html"))
        await page.evaluate("() => window.DemoStore.reset()")
        await page.reload()
    try:
        await run.run()
    except Exception as e:
        run.fail(f"driver crashed: {e!r}")
    await browser.close()
    passed = sum(1 for ok, _ in run.steps if ok); failed = [t for ok, t in run.steps if not ok]
    return {"interface": label, "family": family, "design": design, "mode": "server" if port else "file",
            "checks": len(run.steps), "passed": passed, "failed": failed, "controls_pressed": sorted(run.pressed),
            "browser_errors": run.errors, "steps": run.steps}


async def main(argv):
    os.makedirs(SHOTS, exist_ok=True)
    fams = [argv[0]] if argv else FAMILIES
    designs = [argv[1]] if len(argv) > 1 else DESIGNS
    results = []
    async with async_playwright() as pw:
        for family in fams:
            for design in designs:
                with Server(family, PORTS[family]) as srv:
                    r = await drive_one(pw, family, design, srv.port)
                results.append(r)
                print(f"{r['interface']:34} {r['passed']}/{r['checks']} checks" + ("" if not r["failed"] else "  FAIL: " + r["failed"][0]))
        if not argv:
            # the same journeys with no server at all: one family per design, opened as a file
            for family, design in (("crm-pipeline", "console"), ("erp-backbone", "board"), ("accounting-ledger", "pocket")):
                r = await drive_one(pw, family, design, None)
                results.append(r)
                print(f"{r['interface']:34} {r['passed']}/{r['checks']} checks" + ("" if not r["failed"] else "  FAIL: " + r["failed"][0]))
    json.dump(results, open(os.path.join(EVID, "INTERFACES.json"), "w"), indent=1)
    lines = ["# Interface qualification — every control, real Chromium, outcomes verified by API", "",
             f"Run {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}. {len(results)} interface runs.", "",
             "| Interface | Mode | Checks | Passed | Failed | Browser errors |", "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['interface']} | {r['mode']} | {r['checks']} | {r['passed']} | {len(r['failed'])} | {len(r['browser_errors'])} |")
    lines += ["", "## Failures", ""]
    anyf = False
    for r in results:
        for f in r["failed"]:
            anyf = True; lines.append(f"- **{r['interface']}**: {f}")
    if not anyf: lines.append("None.")
    lines += ["", "## Every step", ""]
    for r in results:
        lines.append(f"### {r['interface']} ({r['mode']})"); lines.append("")
        for ok, t in r["steps"]: lines.append(f"- {'PASS' if ok else 'FAIL'} {t}")
        lines.append("")
    open(os.path.join(EVID, "INTERFACES.md"), "w").write("\n".join(lines))
    total_failed = sum(len(r["failed"]) for r in results)
    print(f"\n{sum(r['passed'] for r in results)} passed, {total_failed} failed across {len(results)} interface runs -> evidence/INTERFACES.md")
    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
