#!/usr/bin/env python3
"""Export all persistent state to a single timestamped JSON file (spec
section 18: "implement backup/export capability for persistent state").

Usage:
    PYTHONPATH=libs/core:. python3 scripts/backup/export_state.py [output_path]

The output contains password hashes and full conversation/task content —
treat it as sensitive as the database itself and store it accordingly
(this script does not encrypt it).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import inspect as sa_inspect

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

# Dependency order: a table only appears after every table it has a
# foreign key into.
TABLES = [User, ModelRecord, Conversation, Message, GPUSession, Worker, Task, Approval, ExecutionRequest,
          Notification, AuditEvent]


def _serialise(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def row_to_dict(row: Any) -> dict[str, Any]:
    mapper = sa_inspect(row).mapper
    return {col.key: _serialise(getattr(row, col.key)) for col in mapper.columns}


def main() -> int:
    init_db()
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        f"backups/workstation-export-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export: dict[str, Any] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }

    with session_scope() as db:
        for model in TABLES:
            rows = db.query(model).all()
            export["tables"][model.__tablename__] = [row_to_dict(r) for r in rows]

    output_path.write_text(json.dumps(export, indent=2))
    counts = {name: len(rows) for name, rows in export["tables"].items()}
    print(f"Exported to {output_path}")
    for name, count in counts.items():
        print(f"  {name}: {count} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
