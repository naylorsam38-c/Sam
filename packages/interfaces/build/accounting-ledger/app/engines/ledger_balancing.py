"""Payment Application / Ledger Balancing Engine — accounting-ledger's real
automatic transitions: "Awaiting payment -> Paid ... event: Payments
applied to the invoice reach its total" (FL.03:Invoice lifecycle, and the
same for Bill lifecycle). Matching Payment rows against an Invoice/Bill's
total and firing the transition when they meet is the core of what makes
this an accounting app; Records/Flow only declare that the rule exists.

Initiating a live charge against a real payment gateway is a distinct,
separate concern (see ENGINE_CATALOGUE.md -- Stripe is blocked at this
sandbox's own network policy and is not registered). This engine only
balances payments already recorded against what they're applied to, which
needs no external system to be real.
"""

import sqlite3


def applied_total(conn, payments_table, target_column, target_id, amount_column="amount"):
    row = conn.execute(
        f"SELECT COALESCE(SUM({amount_column}), 0) FROM {payments_table} WHERE {target_column} = ?",
        (target_id,),
    ).fetchone()
    return row[0]


def is_paid(conn, invoice_table, invoice_id, total_column, payments_table, target_column, id_column="id", amount_column="amount"):
    total = conn.execute(f"SELECT {total_column} FROM {invoice_table} WHERE {id_column} = ?", (invoice_id,)).fetchone()
    if total is None:
        raise ValueError(f"{invoice_table}.{id_column} = {invoice_id!r} does not exist")
    return applied_total(conn, payments_table, target_column, invoice_id, amount_column) >= total[0]


def line_total(conn, line_table, line_fk, target_id, quantity_column="quantity", amount_column="unit_amount"):
    """An Invoice's real total, as accounting-ledger defines it: the sum of
    (Quantity x Unit amount) over its own Invoice lines. Nothing is stored;
    it is computed from the real lines every time."""
    for name in (line_table, line_fk, quantity_column, amount_column):
        if not name.replace("_", "").isalnum():
            raise ValueError(f"{name!r} is not a safe SQL identifier")
    row = conn.execute(
        f"SELECT COALESCE(SUM(COALESCE({quantity_column}, 0) * COALESCE({amount_column}, 0)), 0) "
        f"FROM {line_table} WHERE {line_fk} = ?", (target_id,)).fetchone()
    return row[0]


def settles(conn, total, payments_table, target_column, target_id, amount_column="amount"):
    """True when the payments really applied to this target reach `total`
    (the FL.03 event 'Payments applied to the invoice reach its total'). A
    target with a zero total is never 'paid' by having no payments: nothing
    was owed, so nothing was settled, and an invoice with no lines must not
    silently move to Paid."""
    if total is None or float(total) <= 0:
        return False
    return float(applied_total(conn, payments_table, target_column, target_id, amount_column)) >= float(total)


def prove():
    """Real proof against accounting-ledger's own real rule: a real Invoice
    with total=100.00; a real Payment of 40 applied -> not yet Paid; a
    second real Payment of 60 applied -> now Paid (40+60 >= 100), the exact
    'Payments applied ... reach its total' condition."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE invoices (id TEXT PRIMARY KEY, total REAL)")
    conn.execute("CREATE TABLE payments (id TEXT PRIMARY KEY, invoice_id TEXT, amount REAL)")
    conn.execute("INSERT INTO invoices VALUES ('INV-1', 100.00)")
    conn.commit()

    conn.execute("INSERT INTO payments VALUES ('PMT-1', 'INV-1', 40.00)")
    conn.commit()
    paid_after_first = is_paid(conn, "invoices", "INV-1", "total", "payments", "invoice_id")

    conn.execute("INSERT INTO payments VALUES ('PMT-2', 'INV-1', 60.00)")
    conn.commit()
    paid_after_second = is_paid(conn, "invoices", "INV-1", "total", "payments", "invoice_id")
    total_applied = applied_total(conn, "payments", "invoice_id", "INV-1")

    assert paid_after_first is False, "40 of 100 must not be Paid yet"
    assert paid_after_second is True, "40+60 = 100 must reach the total"
    assert total_applied == 100.00

    # the total computed from real lines, and the settle check driven by it
    conn.execute("CREATE TABLE invoice_lines (id TEXT, invoice TEXT, quantity REAL, unit_amount REAL)")
    conn.executemany("INSERT INTO invoice_lines VALUES (?,?,?,?)",
                     [("L1", "INV-2", 2, 30.0), ("L2", "INV-2", 1, 40.0)])
    conn.execute("INSERT INTO payments VALUES ('PMT-3', 'INV-2', 100.00)")
    conn.commit()
    inv2_total = line_total(conn, "invoice_lines", "invoice", "INV-2")
    assert inv2_total == 100.0, inv2_total
    assert settles(conn, inv2_total, "payments", "invoice_id", "INV-2") is True
    assert settles(conn, 0, "payments", "invoice_id", "INV-9") is False, "nothing owed is not 'paid'"
    conn.close()
    return {"engine": "ledger_balancing", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["real Invoice total=100.00", "apply real Payment of 40 -> not Paid",
                      "apply real Payment of 60 -> Paid (40+60>=100)",
                      "compute a second invoice's total from its real lines (2x30 + 1x40 = 100)",
                      "check a real 100 payment settles it; check a zero total never settles"],
            "observed": {"paid_after_first_payment": paid_after_first,
                        "paid_after_second_payment": paid_after_second, "total_applied": total_applied,
                        "invoice_2_total_from_lines": inv2_total}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
