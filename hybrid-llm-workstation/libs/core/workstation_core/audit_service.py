"""Audit logging (spec section 13/15). Every service in the control plane
that performs a security-relevant or state-changing action should call
`record` in the same transaction as the change, so an audit trail can never
exist without the change it describes (or vice versa)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from workstation_core.models_orm import AuditEvent


def record(
    db: Session,
    *,
    actor: str,
    event_type: str,
    resource_type: str,
    resource_id: str | None,
    action: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        event_metadata=metadata or {},
    )
    db.add(event)
    db.flush()
    return event
