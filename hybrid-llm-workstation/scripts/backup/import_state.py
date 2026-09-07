#!/usr/bin/env python3
"""Restore persistent state from a file produced by export_state.py.

Usage:
    PYTHONPATH=libs/core:. python3 scripts/backup/import_state.py backups/workstation-export-....json

Intended for restoring into a freshly-migrated, empty database (a disaster
recovery / GPU-replacement scenario, spec section 18). Existing rows with a
matching primary key are left untouched and reported as skipped rather than
silently overwritten.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from workstation_core.db import init_db, session_scope
from workstation_core.models_orm import (
    Approval,
    AuditEvent,
    Conversation,
    ExecutionRequest,
    GPUSession,
    Message,
    ModelRecord,
    Notification,
    Task,
    User,
    Worker,
)

TABLES_BY_NAME = {
    m.__tablename__: m
    for m in [User, ModelRecord, Conversation, Message, GPUSession, Worker, Task, Approval, ExecutionRequest,
              Notification, AuditEvent]
}

# Same dependency order as export_state.py — required so a row's foreign
# keys already exist when it's inserted.
TABLE_ORDER = ["users", "models", "conversations", "messages", "gpu_sessions", "workers", "tasks", "approvals",
               "execution_requests", "notifications", "audit_events"]

_DATETIME_COLUMNS = {"created_at", "updated_at", "started_at", "completed_at", "stopped_at", "last_activity_at",
                     "requested_at", "resolved_at", "read_at", "last_heartbeat"}


def _deserialise(key: str, value: Any) -> Any:
    if key in _DATETIME_COLUMNS and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: import_state.py <export.json>", file=sys.stderr)
        return 1

    data = json.loads(Path(sys.argv[1]).read_text())
    init_db()

    inserted = 0
    skipped = 0
    with session_scope() as db:
        for table_name in TABLE_ORDER:
            model = TABLES_BY_NAME[table_name]
            rows = data.get("tables", {}).get(table_name, [])
            for raw in rows:
                pk = raw["id"]
                if db.get(model, pk) is not None:
                    skipped += 1
                    continue
                kwargs = {k: _deserialise(k, v) for k, v in raw.items()}
                db.add(model(**kwargs))
                inserted += 1
            db.commit()

    print(f"Imported {inserted} row(s), skipped {skipped} already-present row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
