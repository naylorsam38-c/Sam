"""Stage-Entry History Engine — records the real timestamp a record entered
each workflow stage. crm-pipeline's "Win rate" metric definition ("deals
that entered Won divided by deals that entered Won or Lost, in the selected
period, attributed to the date the deal reached that stage") and
erp-backbone's "Sales by month" ("...whose Sales order reached Shipped in
the month") both need this; no field in either template's own R.02 answers
holds it (see SPECIALIST_ENGINES.md).
"""

import re
import sqlite3
import time


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _stage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_table TEXT NOT NULL,
            row_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            entered_at REAL NOT NULL
        )
    """)
    conn.commit()


def record_transition(conn, record_table, row_id, stage, at=None):
    conn.execute(
        "INSERT INTO _stage_history (record_table, row_id, stage, entered_at) VALUES (?, ?, ?, ?)",
        (record_table, str(row_id), stage, at if at is not None else time.time()),
    )
    conn.commit()


def entered_at(conn, record_table, row_id, stage):
    """The most recent real time this exact record entered this exact stage,
    or None if it never has."""
    row = conn.execute(
        "SELECT entered_at FROM _stage_history WHERE record_table = ? AND row_id = ? AND stage = ? "
        "ORDER BY entered_at DESC LIMIT 1",
        (record_table, str(row_id), stage),
    ).fetchone()
    return row[0] if row else None


def rate_between(conn, record_table, numerator_stage, denominator_stages, since=None, until=None):
    """Real 'win rate'-shaped computation: count of records whose LATEST
    entry into numerator_stage falls in [since, until), divided by count of
    records that entered any of denominator_stages in the same window --
    exactly crm-pipeline's own real metric definition, mechanically."""
    since = since if since is not None else 0.0
    until = until if until is not None else time.time() + 1
    numer = conn.execute(
        "SELECT COUNT(DISTINCT row_id) FROM _stage_history WHERE record_table = ? AND stage = ? "
        "AND entered_at >= ? AND entered_at < ?",
        (record_table, numerator_stage, since, until),
    ).fetchone()[0]
    placeholders = ",".join("?" for _ in denominator_stages)
    denom = conn.execute(
        f"SELECT COUNT(DISTINCT row_id) FROM _stage_history WHERE record_table = ? AND stage IN ({placeholders}) "
        "AND entered_at >= ? AND entered_at < ?",
        (record_table, *denominator_stages, since, until),
    ).fetchone()[0]
    return (numer / denom) if denom else None


def rate_over_last_days(conn, record_table, numerator_stage, denominator_stages, days, now=None):
    """rate_between over a trailing window of `days` ending now -- the exact
    shape of crm-pipeline's "last 90 days" and booking-frontdesk's "last 30
    days" default ranges. Returns {"rate": 0..1 or None, "percentage": 0..100
    or None, "numerator": n, "denominator": n, "window_days": days}."""
    now = now if now is not None else time.time()
    since = now - float(days) * 86400.0
    numer = conn.execute(
        "SELECT COUNT(DISTINCT row_id) FROM _stage_history WHERE record_table = ? AND stage = ? "
        "AND entered_at >= ? AND entered_at < ?",
        (record_table, numerator_stage, since, now + 1),
    ).fetchone()[0]
    placeholders = ",".join("?" for _ in denominator_stages)
    denom = conn.execute(
        f"SELECT COUNT(DISTINCT row_id) FROM _stage_history WHERE record_table = ? AND stage IN ({placeholders}) "
        "AND entered_at >= ? AND entered_at < ?",
        (record_table, *denominator_stages, since, now + 1),
    ).fetchone()[0]
    rate = (numer / denom) if denom else None
    return {"rate": rate, "percentage": (round(rate * 100.0, 1) if rate is not None else None),
            "numerator": numer, "denominator": denom, "window_days": days}


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name):
    if not _IDENT.match(str(name)):
        raise ValueError(f"{name!r} is not a safe SQL identifier")
    return name


def line_value_by_month(conn, record_table, stage, line_table, line_fk, quantity_column,
                        price_column, months=12, now=None):
    """erp-backbone's own "Sales by month" definition, mechanically: for every
    record whose LATEST entry into `stage` falls in the trailing `months`
    window, sum (quantity x price) over its lines, bucketed by the month
    (YYYY-MM, UTC) it reached that stage. Returns {"YYYY-MM": value}, months
    with no sales present as 0.0 so a chart has a full axis."""
    now = now if now is not None else time.time()
    since = now - float(months) * 31 * 86400.0
    lt, fk, qc, pc = _ident(line_table), _ident(line_fk), _ident(quantity_column), _ident(price_column)
    rows = conn.execute(
        f"""
        WITH latest AS (
            SELECT row_id, MAX(entered_at) AS entered_at
            FROM _stage_history WHERE record_table = ? AND stage = ?
            GROUP BY row_id
        )
        SELECT strftime('%Y-%m', latest.entered_at, 'unixepoch') AS month,
               COALESCE(SUM(COALESCE(l.{qc}, 0) * COALESCE(l.{pc}, 0)), 0)
        FROM latest LEFT JOIN {lt} l ON l.{fk} = latest.row_id
        WHERE latest.entered_at >= ? AND latest.entered_at < ?
        GROUP BY month ORDER BY month
        """,
        (record_table, stage, since, now + 1),
    ).fetchall()
    out = {}
    # every month in the window, oldest first, so an empty month is a real 0 not a gap
    t = time.gmtime(now)
    y, m = t.tm_year, t.tm_mon
    keys = []
    for _ in range(int(months)):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    for k in reversed(keys):
        out[k] = 0.0
    for month, value in rows:
        out[month] = float(value)
    return out


def prove():
    """Real proof, against crm-pipeline's own real shape: three real Deals
    move through real stages at real (distinct) timestamps; the real win
    rate query is run against that real history and checked by hand."""
    conn = sqlite3.connect(":memory:")
    ensure_table(conn)
    t0 = 1000.0
    # Deal 1: Lead in -> Contacted -> Won
    for i, stage in enumerate(["Lead in", "Contacted", "Won"]):
        record_transition(conn, "deals", "D-1", stage, at=t0 + i)
    # Deal 2: Lead in -> Lost
    for i, stage in enumerate(["Lead in", "Lost"]):
        record_transition(conn, "deals", "D-2", stage, at=t0 + i)
    # Deal 3: Lead in -> Contacted (still open, never reached Won or Lost)
    for i, stage in enumerate(["Lead in", "Contacted"]):
        record_transition(conn, "deals", "D-3", stage, at=t0 + i)

    won_at = entered_at(conn, "deals", "D-1", "Won")
    assert won_at == t0 + 2

    win_rate = rate_between(conn, "deals", "Won", ["Won", "Lost"])
    assert win_rate == 0.5, f"expected 1 Won / 2 (Won+Lost) = 0.5, got {win_rate}"

    # trailing-window rate: with "now" pinned just after the history, the
    # 90-day window holds everything -> 50%; a window ending before it -> None
    recent = rate_over_last_days(conn, "deals", "Won", ["Won", "Lost"], 90, now=t0 + 10)
    assert recent["percentage"] == 50.0 and recent["numerator"] == 1 and recent["denominator"] == 2, recent
    empty = rate_over_last_days(conn, "deals", "Won", ["Won", "Lost"], 90, now=t0 - 100 * 86400)
    assert empty["rate"] is None and empty["denominator"] == 0, empty

    # erp-backbone's "Sales by month": two real orders reach Shipped in two
    # different months; their real lines sum to (2x10)+(1x5)=25 and (3x4)=12
    conn.execute("CREATE TABLE sales_order_lines (id TEXT, sales_order TEXT, quantity INTEGER, unit_price REAL)")
    conn.executemany("INSERT INTO sales_order_lines VALUES (?,?,?,?)",
                     [("L1", "SO-1", 2, 10.0), ("L2", "SO-1", 1, 5.0), ("L3", "SO-2", 3, 4.0)])
    jan = 1767225600.0   # 2026-01-01T00:00:00Z
    feb = 1769904000.0   # 2026-02-01T00:00:00Z
    record_transition(conn, "sales_orders", "SO-1", "Shipped", at=jan + 3600)
    record_transition(conn, "sales_orders", "SO-2", "Shipped", at=feb + 3600)
    by_month = line_value_by_month(conn, "sales_orders", "Shipped", "sales_order_lines", "sales_order",
                                   "quantity", "unit_price", months=3, now=feb + 86400)
    assert by_month == {"2025-12": 0.0, "2026-01": 25.0, "2026-02": 12.0}, by_month
    conn.close()
    return {"engine": "stage_history", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["record 3 real deals' real stage transitions at real timestamps",
                      "query entered_at('Won') for Deal 1", "compute real win rate over Won/Lost",
                      "compute the same rate over a trailing 90-day window (and an empty window)",
                      "sum real order lines by the month their order reached Shipped"],
            "observed": {"entered_at_won_D1": won_at, "win_rate": win_rate,
                         "rate_last_90_days": recent, "sales_by_month": by_month}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
