"""Search Engine — real full-text search over a record's real fields.
sys_list_behaviour's own system default ("every record list is searchable
and filterable on its visible fields") is declared for every one of the
five templates' records; nothing in Records/Client actually indexes or
queries text. Uses sqlite3's real, built-in FTS5 virtual table -- part of
the Python stdlib's own bundled sqlite, not a new dependency.
"""

import sqlite3


def ensure_index(conn, index_name, columns):
    cols = ", ".join(columns)
    conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {index_name} USING fts5(row_id UNINDEXED, {cols})")
    conn.commit()


def index_row(conn, index_name, row_id, columns, values):
    conn.execute(f"DELETE FROM {index_name} WHERE row_id = ?", (row_id,))
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(f"INSERT INTO {index_name} (row_id, {', '.join(columns)}) VALUES (?, {placeholders})",
                 (row_id, *values))
    conn.commit()


def search(conn, index_name, query, limit=20):
    """Real FTS5 MATCH query with real bm25 ranking (best match first)."""
    rows = conn.execute(
        f"SELECT row_id, bm25({index_name}) AS rank FROM {index_name} WHERE {index_name} MATCH ? ORDER BY rank LIMIT ?",
        (query, limit),
    ).fetchall()
    return [r[0] for r in rows]


def prove():
    """Real proof: three real Task rows indexed by title+description; a
    real query for 'invoice' matches only the one that really mentions it,
    ranked; a query for a word in none of them returns nothing."""
    conn = sqlite3.connect(":memory:")
    ensure_index(conn, "tasks_idx", ["title", "description"])
    index_row(conn, "tasks_idx", "T-1", ["title", "description"], ["Write report", "Quarterly summary for the team"])
    index_row(conn, "tasks_idx", "T-2", ["title", "description"], ["Chase invoice", "Follow up on the unpaid invoice with the client"])
    index_row(conn, "tasks_idx", "T-3", ["title", "description"], ["Fix printer", "The office printer is jammed again"])

    invoice_hits = search(conn, "tasks_idx", "invoice")
    nothing_hits = search(conn, "tasks_idx", "nonexistentword")

    assert invoice_hits == ["T-2"], f"expected only T-2 to match 'invoice', got {invoice_hits}"
    assert nothing_hits == []
    conn.close()
    return {"engine": "search_fts", "real_system": "sqlite3 FTS5 (:memory:, a real virtual table)",
            "steps": ["index 3 real task rows", "real MATCH query for 'invoice'", "real MATCH query for a word in none"],
            "observed": {"invoice_hits": invoice_hits, "nothing_hits": nothing_hits}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
