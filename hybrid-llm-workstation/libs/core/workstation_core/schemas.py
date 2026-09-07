"""Pydantic request/response schemas for the control API (spec section 14)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth --------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Models --------------------------------------------------------------

class ModelOut(ORMSchema):
    id: str
    name: str
    environment: str
    provider: str
    engine: str
    capabilities: list[str]
    context_length: int | None
    status: str
    cost_class: str
    model_metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


# --- GPU --------------------------------------------------------------

class GPUStatusOut(BaseModel):
    status: str
    provider: str
    instance_id: str | None = None
    endpoint: str | None = None
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    idle_timeout_minutes: int
    max_session_minutes: int
    max_hourly_cost: float
    estimated_cost: float = 0.0
    actual_cost: float | None = None
    auto_stop: bool
    error: str | None = None


class GPUCostOut(BaseModel):
    status: str
    session_minutes: float
    estimated_cost: float
    max_hourly_cost: float
    over_limit: bool


# --- Tasks --------------------------------------------------------------

class TaskCreateRequest(BaseModel):
    type: str
    model_id: str | None = None
    environment: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)


class TaskOut(ORMSchema):
    id: str
    user_id: str
    type: str
    status: str
    model_id: str | None
    environment: str | None
    worker_id: str | None
    progress: float
    input: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None
    retry_count: int
    created_at: datetime
    started_at: datetime | None
    updated_at: datetime
    completed_at: datetime | None


# --- Notifications --------------------------------------------------------------

class NotificationOut(ORMSchema):
    id: str
    user_id: str
    type: str
    title: str
    body: str
    status: str
    created_at: datetime
    read_at: datetime | None


# --- Approvals --------------------------------------------------------------

class ApprovalOut(ORMSchema):
    id: str
    task_id: str | None
    action: str
    risk_level: str
    status: str
    requested_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None


# --- Execution agent proxy --------------------------------------------------------------

class ExecutionRequestCreate(BaseModel):
    task_id: str | None = None
    operation: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    working_directory: str | None = None


class ExecutionRequestOut(ORMSchema):
    id: str
    task_id: str | None
    command: str
    working_directory: str | None
    arguments: dict[str, Any]
    status: str
    approval_id: str | None
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None


class HealthOut(BaseModel):
    component: str
    healthy: bool
    detail: str = ""
    checked_at: datetime
