"""The real database behind a Hands session.

One sqlite file per data root. Every table here holds real state the
engine reads back and acts on — there is no in-memory shadow copy, so a
restart mid-session resumes from exactly what the database says.
"""

import sqlite3
from pathlib import Path

from . import config, shelf

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    workflow_id     TEXT NOT NULL,
    customer        TEXT NOT NULL,
    state           TEXT NOT NULL,
    outcome         TEXT,
    failure_reason  TEXT,
    price_cents     INTEGER,
    price_scope     TEXT,
    price_locked_at REAL,
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    role        TEXT NOT NULL,           -- 'original' | 'completed'
    filename    TEXT NOT NULL,
    path        TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    byte_length INTEGER NOT NULL,
    attestation TEXT,
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS fields (
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    name        TEXT NOT NULL,
    label       TEXT NOT NULL,
    rect        TEXT NOT NULL,           -- JSON [x0,y0,x1,y1] from the real document
    value       TEXT NOT NULL DEFAULT '',
    provenance  TEXT NOT NULL,
    source      TEXT,
    waived      INTEGER NOT NULL DEFAULT 0,
    updated_at  REAL NOT NULL,
    PRIMARY KEY (session_id, name)
);

CREATE TABLE IF NOT EXISTS approvals (
    id           TEXT PRIMARY KEY,
    session_id   TEXT NOT NULL REFERENCES sessions(id),
    action       TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    decision     TEXT NOT NULL,          -- 'APPROVED' | 'DECLINED'
    decided_by   TEXT NOT NULL,
    decided_at   REAL NOT NULL,
    consumed_at  REAL
);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    at         REAL NOT NULL,
    kind       TEXT NOT NULL,
    detail     TEXT NOT NULL
);
"""


def data_root(root=None):
    path = Path(root or config.DATA_ROOT)
    path.mkdir(parents=True, exist_ok=True)
    return path


def connect(root=None):
    """Opens the real database, creating the schema if this is a fresh
    data root. Also creates the shelf audit_trail part's own table, since
    Hands records its mutations through that part rather than a second
    audit implementation of its own."""
    path = data_root(root) / "hands.db"
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # concurrent readers while one writer commits
    conn.execute("PRAGMA busy_timeout=15000")
    conn.executescript(SCHEMA)
    shelf.audit_trail.ensure_table(conn)
    conn.commit()
    return conn
