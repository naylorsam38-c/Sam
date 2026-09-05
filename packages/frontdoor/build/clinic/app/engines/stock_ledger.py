"""Stock/Inventory Ledger Engine — erp-backbone's real on_complete text:
"On Received, each line's Quantity is added to its Product's Stock on
hand." / "On Shipped, ... subtracted..." (FL.08), feeding the real alert
condition: "a Product's Stock on hand falls to or below its Reorder point"
(N.01:Low stock alert). Mutating one record's field as a side effect of a
different record's workflow stage, then evaluating a live two-field
comparison, is arithmetic no part of Records/Flow/Notify performs alone.
"""

import sqlite3


def adjust_stock(conn, table, product_id, delta, stock_column="stock_on_hand", id_column="id"):
    """Real, atomic UPDATE -- never a read-then-write race, matching what a
    real concurrent order-fulfilment system needs."""
    conn.execute(f"UPDATE {table} SET {stock_column} = {stock_column} + ? WHERE {id_column} = ?",
                 (delta, product_id))
    conn.commit()
    return conn.execute(f"SELECT {stock_column} FROM {table} WHERE {id_column} = ?", (product_id,)).fetchone()[0]


def needs_reorder(conn, table, product_id, stock_column="stock_on_hand", reorder_column="reorder_point", id_column="id"):
    row = conn.execute(f"SELECT {stock_column}, {reorder_column} FROM {table} WHERE {id_column} = ?",
                       (product_id,)).fetchone()
    if row is None:
        raise ValueError(f"{table}.{id_column} = {product_id!r} does not exist")
    stock, reorder_point = row
    return stock <= reorder_point


def apply_order_line(conn, product_table, product_id, quantity, direction, stock_column="stock_on_hand", id_column="id"):
    """direction: 'receive' (Purchase order -> Received, adds stock) or
    'ship' (Sales order -> Shipped, subtracts stock) -- exactly
    erp-backbone's own two real on_complete rules. Returns (new_stock,
    reorder_needed)."""
    delta = quantity if direction == "receive" else -quantity
    new_stock = adjust_stock(conn, product_table, product_id, delta, stock_column, id_column)
    return new_stock, needs_reorder(conn, product_table, product_id, stock_column, "reorder_point", id_column)


def apply_order_lines(conn, line_table, line_fk, order_id, product_table, product_fk, quantity_column,
                      direction, stock_column="stock_on_hand", id_column="id"):
    """Every line of one real order applied to its own Product, in one pass --
    exactly erp-backbone's FL.08 ("On Received, EACH line's Quantity is added
    ..." / "On Shipped, ... subtracted ..."). Returns one entry per line:
    {product_id, quantity, new_stock, reorder_needed}. A line whose Product
    link is empty is reported, not silently skipped."""
    for name in (line_table, line_fk, product_fk, quantity_column):
        if not name.replace("_", "").isalnum():
            raise ValueError(f"{name!r} is not a safe SQL identifier")
    lines = conn.execute(
        f"SELECT {product_fk}, {quantity_column} FROM {line_table} WHERE {line_fk} = ?", (order_id,)).fetchall()
    out = []
    for product_id, quantity in lines:
        if not product_id:
            out.append({"product_id": None, "quantity": quantity, "new_stock": None, "reorder_needed": None,
                        "error": "line has no Product"})
            continue
        new_stock, reorder = apply_order_line(conn, product_table, product_id, int(quantity or 0), direction,
                                              stock_column, id_column)
        out.append({"product_id": product_id, "quantity": int(quantity or 0), "new_stock": new_stock,
                    "reorder_needed": reorder})
    return out


def count_at_or_below_reorder(conn, table, stock_column="stock_on_hand", reorder_column="reorder_point"):
    """erp-backbone's "count of Products at or below Reorder point": a real
    two-column comparison, which the generic reporting engine's single-field
    filters cannot express. Products with no reorder point set do not count."""
    return conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {reorder_column} IS NOT NULL AND {stock_column} IS NOT NULL "
        f"AND {stock_column} <= {reorder_column}").fetchone()[0]


def prove():
    """Real proof against erp-backbone's own real rules: a real Product
    starts at stock=10, reorder_point=5. A real Sales order line for
    quantity=6 reaching Shipped subtracts 6 -> stock=4 -> reorder needed. A
    real Purchase order line for quantity=20 reaching Received adds 20 ->
    stock=24 -> no longer needed."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE products (id TEXT PRIMARY KEY, stock_on_hand INTEGER, reorder_point INTEGER)")
    conn.execute("INSERT INTO products VALUES ('P-1', 10, 5)")
    conn.commit()

    stock_after_ship, needs_1 = apply_order_line(conn, "products", "P-1", 6, "ship")
    assert stock_after_ship == 4 and needs_1 is True

    stock_after_receive, needs_2 = apply_order_line(conn, "products", "P-1", 20, "receive")
    assert stock_after_receive == 24 and needs_2 is False

    # a whole real order: two lines against two products, applied in one pass
    conn.execute("INSERT INTO products VALUES ('P-2', 3, 5)")
    conn.execute("CREATE TABLE sales_order_lines (id TEXT, sales_order TEXT, product TEXT, quantity INTEGER)")
    conn.executemany("INSERT INTO sales_order_lines VALUES (?,?,?,?)",
                     [("L1", "SO-1", "P-1", 4), ("L2", "SO-1", "P-2", 1)])
    conn.commit()
    applied = apply_order_lines(conn, "sales_order_lines", "sales_order", "SO-1", "products", "product",
                                "quantity", "ship")
    assert [(a["product_id"], a["new_stock"], a["reorder_needed"]) for a in applied] == \
        [("P-1", 20, False), ("P-2", 2, True)], applied
    low = count_at_or_below_reorder(conn, "products")
    assert low == 1, low
    conn.close()
    return {"engine": "stock_ledger", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["real Product starts stock=10 reorder_point=5",
                      "real Sales order line qty=6 reaches Shipped -> subtract 6",
                      "real Purchase order line qty=20 reaches Received -> add 20",
                      "a whole real Sales order (2 lines, 2 products) reaches Shipped in one pass",
                      "count the real products now at or below their reorder point"],
            "observed": {"stock_after_ship": stock_after_ship, "reorder_needed_after_ship": needs_1,
                        "stock_after_receive": stock_after_receive, "reorder_needed_after_receive": needs_2,
                        "order_applied": applied, "products_at_or_below_reorder": low}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
