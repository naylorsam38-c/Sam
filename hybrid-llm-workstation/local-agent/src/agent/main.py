"""Local execution agent — the security boundary between any LLM-driven
task and the laptop it runs on (spec sections 2.7 and 16-17).

Run with:
    uvicorn agent.main:app --host 0.0.0.0 --port 8787
or `make agent-dev`.

Every /execute call is independently authenticated (HMAC signature) and
independently policy-checked here, regardless of what the control plane
believes it already approved — see agent/policy/engine.py's module
docstring and docs/SECURITY.md for the full reasoning.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from agent.audit.store import AuditStore
from agent.auth.signature import verify
from agent.config import AgentSettings, get_agent_settings
from agent.executor.operations import OPERATIONS, OperationDeniedError, OperationError
from agent.policy.engine import PolicyEngine


class ExecuteRequest(BaseModel):
    request_id: str
    task_id: str | None = None
    operation: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    working_directory: str | None = None
    requested_by: str
    timestamp: int
    signature: str
    approval_token: str | None = None


class ExecuteResponse(BaseModel):
    request_id: str
    status: str  # COMPLETED | FAILED | DENIED
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    result: dict[str, Any] | None = None
    timestamp: int


def create_app(settings: AgentSettings | None = None) -> FastAPI:
    settings = settings or get_agent_settings()
    app = FastAPI(title="Personal LLM Workstation — Local Execution Agent", version="1.0.0")
    app.state.settings = settings
    app.state.audit = AuditStore(settings.audit_db_path)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "component": "local-execution-agent"}

    @app.post("/execute", response_model=ExecuteResponse)
    async def execute(req: ExecuteRequest, request: Request) -> ExecuteResponse:
        return _handle_execute(req, request.app.state.settings, request.app.state.audit)

    return app


def _handle_execute(req: ExecuteRequest, settings: AgentSettings, audit: AuditStore) -> ExecuteResponse:
    ok, reason = verify(
        req.request_id, req.operation, req.timestamp, req.signature,
        settings.execution_agent_token, settings.max_request_age_seconds,
    )
    if not ok:
        audit.record(request_id=req.request_id, task_id=req.task_id, operation=req.operation,
                     parameters=req.parameters, working_directory=req.working_directory,
                     requested_by=req.requested_by, decision="DENIED", reason=f"authentication failed: {reason}")
        return ExecuteResponse(request_id=req.request_id, status="DENIED", stderr=reason, timestamp=int(time.time()))

    params = dict(req.parameters)
    if req.working_directory and "working_directory" not in params:
        params["working_directory"] = req.working_directory

    engine = PolicyEngine.load(settings.policies_path)
    level, risk, class_reason = engine.classify(req.operation, params)

    if level == "RESTRICTED":
        audit.record(request_id=req.request_id, task_id=req.task_id, operation=req.operation, parameters=params,
                     working_directory=req.working_directory, requested_by=req.requested_by,
                     decision="DENIED", risk_level=risk, reason=class_reason)
        return ExecuteResponse(request_id=req.request_id, status="DENIED", stderr=class_reason,
                               timestamp=int(time.time()))

    if level == "APPROVAL" and not req.approval_token:
        reason = "operation requires approval and no approval_token was provided"
        audit.record(request_id=req.request_id, task_id=req.task_id, operation=req.operation, parameters=params,
                     working_directory=req.working_directory, requested_by=req.requested_by,
                     decision="DENIED", risk_level=risk, reason=reason)
        return ExecuteResponse(request_id=req.request_id, status="DENIED", stderr=reason, timestamp=int(time.time()))

    handler = OPERATIONS.get(req.operation)
    rule = engine.rule_for(req.operation)
    if handler is None or rule is None:
        reason = f"operation '{req.operation}' is not implemented by this agent"
        audit.record(request_id=req.request_id, task_id=req.task_id, operation=req.operation, parameters=params,
                     working_directory=req.working_directory, requested_by=req.requested_by,
                     decision="FAILED", risk_level=risk, reason=reason)
        return ExecuteResponse(request_id=req.request_id, status="FAILED", stderr=reason, timestamp=int(time.time()))

    try:
        outcome = handler(
            parameters=params, rule=rule,
            timeout=settings.command_timeout_seconds, max_bytes=settings.max_read_file_bytes,
        )
    except OperationDeniedError as exc:
        audit.record(request_id=req.request_id, task_id=req.task_id, operation=req.operation, parameters=params,
                     working_directory=req.working_directory, requested_by=req.requested_by,
                     decision="DENIED", risk_level=risk, reason=str(exc))
        return ExecuteResponse(request_id=req.request_id, status="DENIED", stderr=str(exc), timestamp=int(time.time()))
    except OperationError as exc:
        audit.record(request_id=req.request_id, task_id=req.task_id, operation=req.operation, parameters=params,
                     working_directory=req.working_directory, requested_by=req.requested_by,
                     decision="FAILED", risk_level=risk, reason=str(exc))
        return ExecuteResponse(request_id=req.request_id, status="FAILED", stderr=str(exc), timestamp=int(time.time()))

    audit.record(request_id=req.request_id, task_id=req.task_id, operation=req.operation, parameters=params,
                 working_directory=req.working_directory, requested_by=req.requested_by,
                 decision="COMPLETED", risk_level=risk, exit_code=outcome.exit_code,
                 stdout=outcome.stdout, stderr=outcome.stderr)
    return ExecuteResponse(
        request_id=req.request_id, status="COMPLETED", stdout=outcome.stdout, stderr=outcome.stderr,
        exit_code=outcome.exit_code, result=outcome.result, timestamp=int(time.time()),
    )


app = create_app()
