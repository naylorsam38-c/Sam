"""Execution-request + approval orchestration (spec sections 16/17).

Flow:
  submit_request()  -> classify risk -> either DENIED (out of policy bounds),
                        auto-approved (TRUSTED) and executed immediately, or
                        AWAITING_APPROVAL (a human must act).
  approve()/deny()  -> resolves the Approval; approve() triggers execution.

The local agent re-checks policy independently on every call regardless of
what happened here — this service's classification only controls the
control-plane UX (does the user see a prompt), never bypasses the agent's
own enforcement (spec: "the agent must enforce policy locally even if the
cloud service requests otherwise").
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from workstation_core.agent_client import AgentClient, AgentUnavailableError
from workstation_core.audit_service import record as audit_record
from workstation_core.config import Settings
from workstation_core.enums import (
    TASK_TERMINAL_STATES,
    ApprovalStatus,
    ExecutionStatus,
    NotificationType,
    PolicyLevel,
    TaskStatus,
)
from workstation_core.models_orm import Approval, ExecutionRequest, Task, User
from workstation_core.notification_service import notify
from workstation_core.policy_engine import PolicyEngine
from workstation_core.task_service import InvalidTaskTransitionError
from workstation_core.task_service import transition as task_transition


class ExecutionRequestNotFoundError(Exception):
    pass


class ApprovalNotFoundError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owner_user_id(db: Session) -> str:
    user = db.query(User).order_by(User.created_at.asc()).first()
    return user.id if user else "unknown"


def _sync_task(db: Session, exec_req: ExecutionRequest, *, actor: str = "system:execution-service") -> None:
    """Keep the Task that spawned this ExecutionRequest (if any) in step
    with it — a task waits at REQUIRES_APPROVAL exactly as long as its
    execution request does, and resolves the moment the request does,
    without needing a separate human 'resume' call. ExecutionRequest.status
    stays the source of truth regardless; this is a best-effort mirror, so
    an illegal transition (task already moved on some other way) is
    swallowed rather than raised."""
    if exec_req.task_id is None:
        return
    task = db.get(Task, exec_req.task_id)
    if task is None or TaskStatus(task.status) in TASK_TERMINAL_STATES:
        return

    target: TaskStatus | None = None
    fields: dict = {}
    if exec_req.status == ExecutionStatus.AWAITING_APPROVAL.value:
        target = TaskStatus.REQUIRES_APPROVAL
    elif exec_req.status == ExecutionStatus.DENIED.value:
        target = TaskStatus.FAILED
        fields = {"error": f"execution denied by policy: {exec_req.command}"}
    elif exec_req.status == ExecutionStatus.COMPLETED.value:
        target = TaskStatus.COMPLETED
        fields = {"result": {"execution_request_id": exec_req.id, "result": exec_req.result}, "progress": 1.0}
    elif exec_req.status == ExecutionStatus.FAILED.value:
        target = TaskStatus.FAILED
        fields = {"error": str((exec_req.result or {}).get("error", "execution failed"))}

    if target is None or TaskStatus(task.status) == target:
        return
    try:
        task_transition(db, task, target, actor=actor, **fields)
    except InvalidTaskTransitionError:
        pass


async def submit_request(
    db: Session, settings: Settings, *, task_id: str | None, operation: str,
    parameters: dict[str, Any], working_directory: str | None, actor: str,
) -> ExecutionRequest:
    engine = PolicyEngine.load(settings.policies_config_path)
    level, risk = engine.classify(operation, parameters)

    exec_req = ExecutionRequest(
        task_id=task_id, command=operation, working_directory=working_directory,
        arguments=parameters, status=ExecutionStatus.PENDING.value,
    )
    db.add(exec_req)
    db.flush()
    audit_record(db, actor=actor, event_type="execution.requested", resource_type="execution_request",
                 resource_id=exec_req.id, action="submit", metadata={"operation": operation, "level": level.value})

    if level == PolicyLevel.RESTRICTED:
        exec_req.status = ExecutionStatus.DENIED.value
        db.flush()
        audit_record(db, actor="system:policy", event_type="execution.denied", resource_type="execution_request",
                     resource_id=exec_req.id, action="deny", metadata={"reason": "outside policy bounds"})
        _sync_task(db, exec_req)
        db.commit()
        db.refresh(exec_req)
        return exec_req

    approval = Approval(
        task_id=task_id, action=f"{operation}({parameters})", risk_level=risk.value,
        status=ApprovalStatus.APPROVED.value if level == PolicyLevel.TRUSTED else ApprovalStatus.PENDING.value,
    )
    if level == PolicyLevel.TRUSTED:
        approval.resolved_at = _now()
        approval.resolved_by = "system:trusted-policy"
    db.add(approval)
    db.flush()
    exec_req.approval_id = approval.id
    exec_req.status = (
        ExecutionStatus.PENDING.value if level == PolicyLevel.TRUSTED else ExecutionStatus.AWAITING_APPROVAL.value
    )
    db.flush()

    if level == PolicyLevel.APPROVAL:
        notify(db, user_id=_owner_user_id(db), type_=NotificationType.TASK_REQUIRES_APPROVAL,
               title="Laptop action needs approval", body=f"{operation} — risk {risk.value}")
        _sync_task(db, exec_req)
    db.commit()
    db.refresh(exec_req)

    if level == PolicyLevel.TRUSTED:
        return await execute_now(db, settings, exec_req)
    return exec_req


async def execute_now(db: Session, settings: Settings, exec_req: ExecutionRequest) -> ExecutionRequest:
    client = AgentClient(settings.execution_agent_url, settings.execution_agent_token)
    exec_req.status = ExecutionStatus.RUNNING.value
    db.commit()
    try:
        result = await client.execute(
            operation=exec_req.command, parameters=exec_req.arguments,
            working_directory=exec_req.working_directory, task_id=exec_req.task_id,
            requested_by="control-plane", approval_token=exec_req.approval_id,
        )
    except AgentUnavailableError as exc:
        exec_req.status = ExecutionStatus.FAILED.value
        exec_req.result = {"error": str(exc)}
        exec_req.completed_at = _now()
        audit_record(db, actor="system:agent-client", event_type="execution.failed", resource_type="execution_request",
                     resource_id=exec_req.id, action="execute", metadata={"error": str(exc)})
        _sync_task(db, exec_req)
        db.commit()
        db.refresh(exec_req)
        return exec_req

    agent_status = result.get("status")
    if agent_status == "COMPLETED":
        exec_req.status = ExecutionStatus.COMPLETED.value
    elif agent_status == "DENIED":
        # The agent independently refused it (its own policy check, or the
        # signature didn't verify) even though this control plane thought
        # it was approved — exactly the defense-in-depth case spec section
        # 17 requires; surface it distinctly rather than as a generic FAILED.
        exec_req.status = ExecutionStatus.DENIED.value
    else:
        exec_req.status = ExecutionStatus.FAILED.value
    exec_req.result = result
    exec_req.completed_at = _now()
    audit_record(db, actor="system:agent-client", event_type="execution.completed", resource_type="execution_request",
                 resource_id=exec_req.id, action="execute", metadata={"exit_code": result.get("exit_code")})
    _sync_task(db, exec_req)
    db.commit()
    db.refresh(exec_req)
    return exec_req


def get_request(db: Session, request_id: str) -> ExecutionRequest:
    req = db.get(ExecutionRequest, request_id)
    if req is None:
        raise ExecutionRequestNotFoundError(request_id)
    return req


def list_approvals(db: Session, *, status: str | None = None) -> list[Approval]:
    query = db.query(Approval)
    if status:
        query = query.filter(Approval.status == status)
    return query.order_by(Approval.requested_at.desc()).all()


def get_approval(db: Session, approval_id: str) -> Approval:
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise ApprovalNotFoundError(approval_id)
    return approval


async def resolve_approval(
    db: Session, settings: Settings, approval: Approval, *, approve: bool, actor: str,
) -> Approval:
    if approval.status != ApprovalStatus.PENDING.value:
        return approval  # already resolved; idempotent no-op

    approval.status = ApprovalStatus.APPROVED.value if approve else ApprovalStatus.DENIED.value
    approval.resolved_at = _now()
    approval.resolved_by = actor
    db.flush()
    audit_record(db, actor=actor, event_type=f"approval.{approval.status.lower()}", resource_type="approval",
                 resource_id=approval.id, action="resolve")
    db.commit()
    db.refresh(approval)

    exec_req = db.query(ExecutionRequest).filter(ExecutionRequest.approval_id == approval.id).one_or_none()
    if exec_req is not None:
        if approve:
            await execute_now(db, settings, exec_req)
        else:
            exec_req.status = ExecutionStatus.DENIED.value
            exec_req.completed_at = _now()
            _sync_task(db, exec_req)
            db.commit()
    return approval
