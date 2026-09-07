"""Shared helper for marking GPU busy/idle from whichever process is
currently doing inference (control API or worker) — both act on the same
`gpu_sessions` row, so this lives in workstation_core rather than being
duplicated. Only status/timestamp bookkeeping; actually starting or
stopping the provider stays exclusively in
apps/control/src/control/gpu/lifecycle.GPULifecycleManager.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from workstation_core.enums import GPU_TRANSITIONS, GPUStatus
from workstation_core.models_orm import GPUSession


def mark_gpu_activity(db: Session, *, busy: bool) -> GPUSession | None:
    session = db.query(GPUSession).order_by(GPUSession.created_at.desc()).first()
    if session is None:
        return None
    current = GPUStatus(session.status)
    if current not in (GPUStatus.READY, GPUStatus.BUSY, GPUStatus.IDLE):
        return session
    session.last_activity_at = datetime.now(timezone.utc)
    target = GPUStatus.BUSY if busy else GPUStatus.READY
    if target != current and target in GPU_TRANSITIONS.get(current, set()):
        session.status = target.value
    db.flush()
    return session
