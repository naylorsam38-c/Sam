"""The five families, live: each reference instance is assembled and built by
packages/interfaces/build_families.py, started as a real process on a real
port, and driven over HTTP -- every generation rule the Builder gained for
them (clone, set_fields_from_input, generate_document, transition effects on
stock, a Payment settling its Invoice/Bill, stage-history and stock-ledger
reports) is exercised against the real generated app, not the generator."""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
IFACE = ROOT / "packages" / "interfaces"
sys.path.insert(0, str(IFACE))
import build_families as bf  # noqa: E402

BUILD = IFACE / "build"


@pytest.fixture(scope="module", autouse=True)
def built():
    for family in bf.FAMILIES:
        bf.build_family(family)


def start(family, port):
    app = BUILD / family / "app"
    db = app / "app.db"
    if db.exists():
        db.unlink()
    env = dict(os.environ, PORT=str(port))
    proc = subprocess.Popen(["python3", "app.py"], cwd=str(app), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            return proc
        except Exception:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("server did not come up: " + (proc.stdout.read() if proc.stdout else ""))


def call(port, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def check(name, cond, info=""):
    assert cond, f"{name}: {info}"


def test_pm_teamwork_clone_moves_and_reports():
    p = start("pm-teamwork", 8801)
    try:
        s, pr = call(8801, "POST", "/api/projects", {"Name": "Alpha", "Owner": "sam"})
        s, t = call(8801, "POST", "/api/tasks", {"Title": "Write it", "Project": pr["id"], "Assignee": "sam", "Due date": "2020-01-01"})
        check("task created", s == 201, (s, t))
        s, r = call(8801, "POST", f"/api/actions/tasks/{t['id']}/Duplicate", {"role": "Member"})
        check("Duplicate clones", s == 200 and r.get("cloned_to"), (s, r))
        s, rows = call(8801, "GET", "/api/tasks"); titles = sorted(x["title"] for x in rows)
        check("clone titled (copy) in To do", titles == ["Write it", "Write it (copy)"] and all(x["stage"]=="To do" for x in rows), rows)
        s, r = call(8801, "POST", f"/api/actions/tasks/{t['id']}/Duplicate", {"role": "Guest"})
        check("Duplicate refused for Guest", s == 403, (s, r))
        s, r = call(8801, "POST", f"/api/moves/tasks/{t['id']}", {"to": "In progress", "role": "Member"})
        check("move To do -> In progress", s == 200 and r["to"] == "In progress", (s, r))
        s, r = call(8801, "POST", f"/api/moves/tasks/{t['id']}", {"to": "Done", "role": "Guest"})
        check("illegal mover refused", s == 409, (s, r))
        s, r = call(8801, "GET", "/api/reports/open_tasks_by_person")
        check("open tasks by person", s == 200 and r["count of Tasks not in stage Done, grouped by Assignee"] == {"sam": 2}, (s, r))
        s, r = call(8801, "GET", "/api/reports/overdue_tasks")
        check("overdue tasks = 2", s == 200 and r["count of overdue Tasks"] == 2, (s, r))
    finally: p.terminate()


def test_crm_pipeline_reassign_from_input_and_win_rate():
    p = start("crm-pipeline", 8802)
    try:
        s, d1 = call(8802, "POST", "/api/deals", {"Title": "Big", "Value": 1000, "Owner": "ann"})
        s, d2 = call(8802, "POST", "/api/deals", {"Title": "Small", "Value": 10, "Owner": "ann"})
        s, r = call(8802, "POST", f"/api/actions/deals/{d1['id']}/Reassign", {"role": "Sales manager", "inputs": {"owner": "bob"}})
        check("Reassign sets owner from input", s == 200 and r["after"] == {"owner": "bob"}, (s, r))
        s, r = call(8802, "POST", f"/api/actions/deals/{d1['id']}/Reassign", {"role": "Sales manager"})
        check("Reassign without input refused 400", s == 400, (s, r))
        for to in ["Contacted", "Proposal sent", "Negotiation", "Won"]:
            s, r = call(8802, "POST", f"/api/moves/deals/{d1['id']}", {"to": to, "role": "Sales rep"})
        check("deal 1 Won", s == 200 and r["to"] == "Won", (s, r))
        s, r = call(8802, "POST", f"/api/moves/deals/{d2['id']}", {"to": "Lost", "role": "Sales rep"})
        check("deal 2 Lost", s == 200, (s, r))
        s, r = call(8802, "GET", "/api/reports/win_rate")
        check("win rate 50%", s == 200 and r["win rate"]["percentage"] == 50.0, (s, r))
        s, r = call(8802, "GET", "/api/reports/pipeline_by_stage")
        check("pipeline by stage excludes Won/Lost from value", s == 200 and r["sum of open Deal Value grouped by stage"] == {} and r["count of Deals grouped by stage"] == {"Won": 1, "Lost": 1}, (s, r))
    finally: p.terminate()


def test_booking_form_confirm_and_no_show_rate():
    p = start("booking-frontdesk", 8803)
    try:
        s, sv = call(8803, "POST", "/api/services", {"Name": "Cut", "Duration minutes": 30, "Price": 40})
        s, cu = call(8803, "POST", "/api/customers", {"Full name": "Jo"})
        s, r = call(8803, "POST", "/api/forms/public_booking_form", {"service": sv["id"], "customer": cu["id"], "staff_member": "kim", "start": "2026-09-06T10:00"})
        check("public form books", s == 201 and r.get("id"), (s, r))
        ap = r["id"]
        s, r = call(8803, "POST", f"/api/moves/appointments/{ap}", {"to": "Confirmed", "role": "Staff"})
        check("staff confirms", s == 200, (s, r))
        s, r = call(8803, "POST", f"/api/moves/appointments/{ap}", {"to": "No-show", "role": "Staff"})
        check("no-show", s == 200, (s, r))
        s, r = call(8803, "GET", "/api/reports/no_show_rate")
        check("no-show rate 100%", s == 200 and r["no-show rate"]["percentage"] == 100.0, (s, r))
        s, r = call(8803, "GET", "/api/reports/upcoming_appointments")
        check("upcoming = 0 (it ended)", s == 200 and r["count of Appointments in stage Booked or Confirmed"] == 0, (s, r))
    finally: p.terminate()


def test_erp_approval_stock_effects_and_reports():
    p = start("erp-backbone", 8804)
    try:
        s, prod = call(8804, "POST", "/api/products", {"Name": "Widget", "SKU": "W1", "Stock on hand": 10, "Reorder point": 5, "Sale price": 3})
        s, sup = call(8804, "POST", "/api/suppliers", {"Name": "Acme"})
        s, po = call(8804, "POST", "/api/purchase_orders", {"Supplier": sup["id"], "Order date": "2026-09-01"})
        s, r = call(8804, "POST", "/api/purchase_order_lines", {"Purchase order": po["id"], "Product": prod["id"], "Quantity": 20, "Unit cost": 1})
        s, r = call(8804, "POST", f"/api/moves/purchase_orders/{po['id']}", {"to": "Confirmed", "role": "Purchasing"})
        check("PO leaving Draft needs approval", s == 409 and r.get("waiting_for_approval"), (s, r))
        s, r = call(8804, "POST", f"/api/approvals/purchase_orders/{po['id']}", {"decision": "APPROVED", "by": "Operations"})
        check("Operations approves", s == 200, (s, r))
        s, r = call(8804, "POST", f"/api/moves/purchase_orders/{po['id']}", {"to": "Confirmed", "role": "Purchasing"})
        check("PO confirmed", s == 200, (s, r))
        s, r = call(8804, "POST", f"/api/moves/purchase_orders/{po['id']}", {"to": "Received", "role": "Warehouse"})
        check("PO received applies stock", s == 200 and r["effects"] and r["effects"][0]["lines"][0]["new_stock"] == 30, (s, r))
        s, cust = call(8804, "POST", "/api/customer_accounts", {"Name": "Bob"})
        s, so = call(8804, "POST", "/api/sales_orders", {"Customer account": cust["id"], "Order date": "2026-09-02"})
        s, r = call(8804, "POST", "/api/sales_order_lines", {"Sales order": so["id"], "Product": prod["id"], "Quantity": 27, "Unit price": 3})
        s, r = call(8804, "POST", f"/api/moves/sales_orders/{so['id']}", {"to": "Confirmed", "role": "Sales"})
        s, r = call(8804, "GET", "/api/reports/open_orders")
        check("open orders: 1 sales confirmed", s == 200 and r["count of Sales orders in Confirmed"] == 1, (s, r))
        s, r = call(8804, "POST", f"/api/moves/sales_orders/{so['id']}", {"to": "Shipped", "role": "Warehouse"})
        check("SO shipped subtracts stock -> 3, reorder", s == 200 and r["effects"][0]["lines"][0]["new_stock"] == 3 and r["effects"][0]["lines"][0]["reorder_needed"] is True, (s, r))
        s, r = call(8804, "GET", "/api/reports/stock_on_hand")
        check("stock on hand report", s == 200 and r["sum of Product Stock on hand"] == 3 and r["count of Products at or below Reorder point"] == 1, (s, r))
        s, r = call(8804, "GET", "/api/reports/sales_by_month")
        check("sales by month has this month = 81", s == 200 and list(r["sales value"].values())[-1] == 81.0 and len(r["sales value"]) == 12, (s, r))
    finally: p.terminate()


def test_accounting_gate_send_and_payments_settle():
    p = start("accounting-ledger", 8805)
    try:
        s, c = call(8805, "POST", "/api/contacts", {"Name": "Zed", "Type": "customer"})
        s, inv = call(8805, "POST", "/api/invoices", {"Contact": c["id"], "Issue date": "2026-09-01", "Due date": "2026-09-30", "Reference": "INV-0001"})
        s, r = call(8805, "POST", "/api/invoice_lines", {"Invoice": inv["id"], "Description": "Work", "Quantity": 2, "Unit amount": 50})
        s, r = call(8805, "POST", f"/api/moves/invoices/{inv['id']}", {"to": "Awaiting approval", "role": "Accountant"})
        check("to Awaiting approval", s == 200, (s, r))
        s, r = call(8805, "POST", f"/api/moves/invoices/{inv['id']}", {"to": "Awaiting payment", "role": "Admin"})
        check("leaving Awaiting approval gated", s == 409, (s, r))
        s, r = call(8805, "POST", f"/api/approvals/invoices/{inv['id']}", {"decision": "APPROVED", "by": "Admin"})
        s, r = call(8805, "POST", f"/api/moves/invoices/{inv['id']}", {"to": "Awaiting payment", "role": "Admin"})
        check("approved -> Awaiting payment", s == 200, (s, r))
        s, r = call(8805, "POST", f"/api/actions/invoices/{inv['id']}/Send", {"role": "Accountant"})
        check("Send generates document + stamps", s == 200 and r["total"] == 100.0 and r["stamped"] and "not dispatched" in r["email"], (s, r))
        with urllib.request.urlopen(f"http://127.0.0.1:8805{r['document_pdf']}") as resp: pdf = resp.read()
        check("pdf served", pdf.startswith(b"%PDF"), pdf[:10])
        s, row = call(8805, "GET", f"/api/invoices/{inv['id']}")
        check("sent_at stamped on row", s == 200 and row["sent_at"], row)
        s, r = call(8805, "POST", "/api/payments", {"Invoice": inv["id"], "Amount": 40, "Date": "2026-09-05", "Method": "bank"})
        check("part payment does not settle", s == 201 and r["effects"][0]["settled"] is False and r["effects"][0]["applied"] == 40, (s, r))
        s, r = call(8805, "POST", "/api/payments", {"Invoice": inv["id"], "Amount": 60, "Date": "2026-09-05", "Method": "bank"})
        check("full payment settles -> Paid", s == 201 and r["effects"][0]["settled"] and r["effects"][0]["moved"] == {"from": "Awaiting payment", "to": "Paid"}, (s, r))
        s, row = call(8805, "GET", f"/api/invoices/{inv['id']}")
        check("invoice now Paid", row["stage"] == "Paid", row)
        s, b = call(8805, "POST", "/api/bills", {"Contact": c["id"], "Issue date": "2026-09-01", "Due date": "2026-09-30", "Amount": 25})
        s, r = call(8805, "POST", f"/api/moves/bills/{b['id']}", {"to": "Awaiting payment", "role": "Accountant"})
        s, r = call(8805, "POST", "/api/payments", {"Bill": b["id"], "Amount": 25, "Date": "2026-09-05", "Method": "cash"})
        check("bill settles -> Paid", s == 201 and r["effects"][0]["moved"] == {"from": "Awaiting payment", "to": "Paid"}, (s, r))
    finally: p.terminate()

