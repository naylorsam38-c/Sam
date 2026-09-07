"""Task CRUD + state machine (spec section 12). Every transition is
validated against TASK_TRANSITIONS and persisted with an updated_at bump
(handled by the ORM's onupdate=) plus an audit event, so a task's full
history is always reconstructable from the database alone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from workstation_core.audit_service import record as audit_record
from workstation_core.enums import TASK_TERMINAL_STATES, TASK_TRANSITIONS, TaskStatus
from workstation_core.models_orm import Task


class InvalidTaskTransitionError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_task(
    db: Session, *, user_id: str, type_: str, model_id: str | None, environment: str | None,
    input_: dict[str, Any],
) -> Task:
    task = Task(user_id=user_id, type=type_, model_id=model_id, environment=environment,
                status=TaskStatus.QUEUED.value, input=input_)
    db.add(task)
    db.flush()
    audit_record(db, actor=user_id, event_type="task.created", resource_type="task", resource_id=task.id,
                 action="create", metadata={"type": type_, "environment": environment})
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: str) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise TaskNotFoundError(task_id)
    return task


def list_tasks(db: Session, *, user_id: str | None = None, status: str | None = None) -> list[Task]:
    query = db.query(Task)
    if user_id:
        query = query.filter(Task.user_id == user_id)
    if status:
        query = query.filter(Task.status == status)
    return query.order_by(Task.created_at.desc()).all()


def transition(db: Session, task: Task, new_status: TaskStatus, *, actor: str, **fields: Any) -> Task:
    current = TaskStatus(task.status)
    if new_status != current and new_status not in TASK_TRANSITIONS.get(current, set()):
        raise InvalidTaskTransitionError(f"illegal task transition {current} -> {new_status}")

    task.status = new_status.value
    for key, value in fields.items():
        setattr(task, key, value)

    if new_status == TaskStatus.STARTING and task.started_at is None:
        task.started_at = _now()
    if new_status in TASK_TERMINAL_STATES:
        task.completed_at = _now()

    db.flush()
    audit_record(db, actor=actor, event_type=f"task.{new_status.value.lower()}", resource_type="task",
                 resource_id=task.id, action="transition", metadata={"from": current.value, "to": new_status.value})
    return task


def cancel_task(db: Session, task: Task, *, actor: str) -> Task:
    if TaskStatus(task.status) in TASK_TERMINAL_STATES:
        return task
    task = transition(db, task, TaskStatus.CANCELLED, actor=actor)
    db.commit()
    db.refresh(task)
    return task


def pause_task(db: Session, task: Task, *, actor: str) -> Task:
    task = transition(db, task, TaskStatus.PAUSED, actor=actor)
    db.commit()
    db.refresh(task)
    return task


def resume_task(db: Session, task: Task, *, actor: str) -> Task:
    task = transition(db, task, TaskStatus.QUEUED, actor=actor)
    db.commit()
    db.refresh(task)
    return task


def claim_next_task(db: Session, *, worker_id: str, eligible_types: list[str] | None = None) -> Task | None:
    """Atomically claim the oldest QUEUED task. Uses a conditional UPDATE so
    two worker processes racing on the same row never both succeed (spec:
    'multiple workers may run concurrently')."""
    query = db.query(Task).filter(Task.status == TaskStatus.QUEUED.value)
    if eligible_types:
        query = query.filter(Task.type.in_(eligible_types))
    candidate = query.order_by(Task.created_at.asc()).first()
    if candidate is None:
        return None

    rowcount = (
        db.query(Task)
        .filter(Task.id == candidate.id, Task.status == TaskStatus.QUEUED.value)
        .update({"status": TaskStatus.STARTING.value, "worker_id": worker_id, "started_at": _now()},
                synchronize_session=False)
    )
    db.commit()
    if rowcount == 0:
        return None  # another worker won the race
    db.refresh(candidate)
    audit_record(db, actor=f"worker:{worker_id}", event_type="task.claimed", resource_type="task",
                 resource_id=candidate.id, action="claim")
    db.commit()
    return candidate
