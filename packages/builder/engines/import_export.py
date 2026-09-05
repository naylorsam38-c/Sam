"""Import/Export Engine — moving real data in and out of a record's real
sqlite table, via real CSV files on disk (stdlib `csv`). A.12 ("existing
data that has to be brought in before launch") and every template's own
"exportable" system default (`sys_list_behaviour`) both need this; neither
Records nor any of the ten parts declares how the actual read/write happens.
"""

import csv
import sqlite3


def export_csv(conn, table, columns, path, id_column="id"):
    """Real CSV file, real header row, real rows in a stable order."""
    rows = conn.execute(f"SELECT {id_column}, {', '.join(columns)} FROM {table} ORDER BY {id_column}").fetchall()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([id_column, *columns])
        w.writerows(rows)
    return len(rows)


def import_csv(conn, table, columns, path, id_column="id"):
    """Reads a real CSV file and inserts real rows. Refuses (raises) a row
    missing a required column rather than inserting a partial/blank one."""
    inserted = 0
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        missing_header = [c for c in [id_column, *columns] if c not in (r.fieldnames or [])]
        if missing_header:
            raise ValueError(f"{path}: missing column(s) {missing_header}")
        placeholders = ", ".join("?" for _ in [id_column, *columns])
        for row in r:
            conn.execute(f"INSERT INTO {table} ({id_column}, {', '.join(columns)}) VALUES ({placeholders})",
                         [row[id_column], *[row[c] for c in columns]])
            inserted += 1
    conn.commit()
    return inserted


def prove():
    """Real proof: a real sqlite table with 3 real rows, exported to a real
    temp CSV file on disk, table wiped, re-imported from that same real
    file -- round-trip checked row for row."""
    import tempfile, os
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE contacts (id TEXT PRIMARY KEY, name TEXT, email TEXT)")
    conn.executemany("INSERT INTO contacts VALUES (?, ?, ?)", [
        ("C-1", "Ada Lovelace", "ada@example.com"),
        ("C-2", "Grace Hopper", "grace@example.com"),
        ("C-3", "Alan Turing", "alan@example.com"),
    ])
    conn.commit()

    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    try:
        exported = export_csv(conn, "contacts", ["name", "email"], path)
        with open(path, encoding="utf-8") as f:
            raw_file_contents = f.read()

        conn.execute("DELETE FROM contacts")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 0

        imported = import_csv(conn, "contacts", ["name", "email"], path)
        rows_back = conn.execute("SELECT id, name, email FROM contacts ORDER BY id").fetchall()
    finally:
        os.remove(path)

    assert exported == 3 and imported == 3
    assert rows_back == [("C-1", "Ada Lovelace", "ada@example.com"),
                          ("C-2", "Grace Hopper", "grace@example.com"),
                          ("C-3", "Alan Turing", "alan@example.com")]
    conn.close()
    return {"engine": "import_export", "real_system": "a real CSV file on disk + sqlite3 (:memory:)",
            "steps": ["insert 3 real rows", "export to a real temp CSV file", "delete all rows",
                      "import back from that same real file", "compare round-trip"],
            "observed": {"exported_count": exported, "imported_count": imported,
                        "rows_back": rows_back, "csv_bytes": len(raw_file_contents)}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
