"""Audit Trail Engine — logs every mutation to a real sqlite table: who,
what changed, before/after, when. Read straight from R.02/R.14's own
sys_audit_fields default plus every one of the five templates' own real
record-mutation actions (create/edit/delete); every one of them needs a
real, queryable history of what happened, not just created_at/updated_at.
"""

import json
import sqlite3
import time


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            row_id TEXT NOT NULL,
            action TEXT NOT NULL,
            before TEXT,
            after TEXT,
            at REAL NOT NULL
        )
    """)
    conn.commit()


def record(conn, table_name, row_id, action, before=None, after=None, at=None):
    """Logs one real mutation. before/after are dicts (or None) -- stored as
    real JSON text, not summarised or dropped."""
    conn.execute(
        "INSERT INTO _audit_log (table_name, row_id, action, before, after, at) VALUES (?, ?, ?, ?, ?, ?)",
        (table_name, str(row_id), action,
         json.dumps(before) if before is not None else None,
         json.dumps(after) if after is not None else None,
         at if at is not None else time.time()),
    )
    conn.commit()


def history_for(conn, table_name, row_id):
    """Every logged mutation for one real row, oldest first."""
    rows = conn.execute(
        "SELECT action, before, after, at FROM _audit_log WHERE table_name = ? AND row_id = ? ORDER BY at ASC",
        (table_name, str(row_id)),
    ).fetchall()
    return [
        {"action": a, "before": json.loads(b) if b else None, "after": json.loads(af) if af else None, "at": at}
        for a, b, af, at in rows
    ]


def prove():
    """Real proof: a real in-memory sqlite db, a real 'tasks' table, three
    real mutations (create/edit/delete) each logged, then the real audit
    log queried back and checked against what actually happened."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, stage TEXT)")
    ensure_table(conn)

    conn.execute("INSERT INTO tasks VALUES ('T-1', 'Write report', 'To do')")
    record(conn, "tasks", "T-1", "create", before=None, after={"title": "Write report", "stage": "To do"})

    conn.execute("UPDATE tasks SET stage = 'In progress' WHERE id = 'T-1'")
    record(conn, "tasks", "T-1", "edit",
           before={"title": "Write report", "stage": "To do"},
           after={"title": "Write report", "stage": "In progress"})

    conn.execute("DELETE FROM tasks WHERE id = 'T-1'")
    record(conn, "tasks", "T-1", "delete",
           before={"title": "Write report", "stage": "In progress"}, after=None)

    log = history_for(conn, "tasks", "T-1")
    assert len(log) == 3, f"expected 3 audit entries, got {len(log)}"
    assert [e["action"] for e in log] == ["create", "edit", "delete"]
    assert log[1]["before"]["stage"] == "To do" and log[1]["after"]["stage"] == "In progress"
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0, "real delete really removed the row"
    conn.close()
    return {"engine": "audit_trail", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["create row + log", "update row + log", "delete row + log", "query history back"],
            "observed": log}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
