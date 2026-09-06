"""Record Cloning Engine — pm-teamwork's `Duplicate` custom action: "creates
a copy of the task in stage 'To do' with '(copy)' appended to the title"
(R.15:Task). Copying a row, resetting one column to a fixed value, and
mutating another is not a CRUD verb Records (R) declares.
"""

import sqlite3
import uuid


def clone(conn, table, row_id, id_column="id", overrides=None, title_column=None, title_suffix=None):
    """Reads a real row from a real table, inserts a real new row with the
    same data except `overrides` (column -> fixed value) and, if given, the
    title column suffixed. Returns the new row's real id."""
    cur = conn.execute(f"SELECT * FROM {table} WHERE {id_column} = ?", (row_id,))
    col_names = [d[0] for d in cur.description]
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"{table}.{id_column} = {row_id!r} does not exist")
    data = dict(zip(col_names, row))

    new_id = str(uuid.uuid4())
    data[id_column] = new_id
    for col, val in (overrides or {}).items():
        data[col] = val
    if title_column and title_suffix:
        data[title_column] = f"{data[title_column]}{title_suffix}"

    cols = list(data)
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                 [data[c] for c in cols])
    conn.commit()
    return new_id


def prove():
    """Real proof against pm-teamwork's own real Duplicate rule: a real Task
    row in stage 'In progress' is cloned; the clone is a distinct real row,
    reset to 'To do', with '(copy)' appended to its title -- the original
    untouched."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, stage TEXT)")
    conn.execute("INSERT INTO tasks VALUES ('T-1', 'Write report', 'In progress')")
    conn.commit()

    new_id = clone(conn, "tasks", "T-1", overrides={"stage": "To do"},
                    title_column="title", title_suffix=" (copy)")

    original = conn.execute("SELECT title, stage FROM tasks WHERE id = 'T-1'").fetchone()
    clone_row = conn.execute("SELECT title, stage FROM tasks WHERE id = ?", (new_id,)).fetchone()
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    assert original == ("Write report", "In progress"), "original must be untouched"
    assert clone_row == ("Write report (copy)", "To do")
    assert new_id != "T-1" and total == 2
    conn.close()
    return {"engine": "record_cloning", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["insert a real Task row", "clone it with overrides+suffix",
                      "query back both real rows"],
            "observed": {"original": original, "clone": clone_row, "new_id_distinct": new_id != "T-1"}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
