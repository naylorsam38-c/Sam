"""The agent's own audit trail — a separate SQLite file from the control
plane's database (they may not even be on the same machine), written with
the stdlib sqlite3 module to keep the agent's dependency footprint minimal.
Every execute request is recorded here regardless of outcome (allowed,
denied, failed), satisfying spec section 16/21's "verify audit trail" and
"commands are audited" requirements independent of whatever the control
plane's own audit log says.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS execution_audit (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    task_id TEXT,
    operation TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    working_directory TEXT,
    requested_by TEXT,
    decision TEXT NOT NULL,
    risk_level TEXT,
    reason TEXT,
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    created_at TEXT NOT NULL
);
"""


class AuditStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def record(
        self, *, request_id: str, task_id: str | None, operation: str, parameters: dict[str, Any],
        working_directory: str | None, requested_by: str, decision: str, risk_level: str | None = None,
        reason: str = "", exit_code: int | None = None, stdout: str = "", stderr: str = "",
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO execution_audit (id, request_id, task_id, operation, parameters_json, "
                "working_directory, requested_by, decision, risk_level, reason, exit_code, stdout, stderr, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    # A fresh id per row, deliberately NOT request_id: a
                    # request_id identifies one logical request, but this
                    # table logs every call, and the same request_id could
                    # legitimately be retried or resent.
                    str(uuid.uuid4()), request_id, task_id, operation, json.dumps(parameters), working_directory,
                    requested_by, decision, risk_level, reason, exit_code, stdout[:10000], stderr[:10000],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def all_records(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM execution_audit ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
