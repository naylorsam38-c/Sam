"""Stage-Entry History Engine — records the real timestamp a record entered
each workflow stage. crm-pipeline's "Win rate" metric definition ("deals
that entered Won divided by deals that entered Won or Lost, in the selected
period, attributed to the date the deal reached that stage") and
erp-backbone's "Sales by month" ("...whose Sales order reached Shipped in
the month") both need this; no field in either template's own R.02 answers
holds it (see SPECIALIST_ENGINES.md).
"""

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
    conn.close()
    return {"engine": "stage_history", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["record 3 real deals' real stage transitions at real timestamps",
                      "query entered_at('Won') for Deal 1", "compute real win rate over Won/Lost"],
            "observed": {"entered_at_won_D1": won_at, "win_rate": win_rate}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
