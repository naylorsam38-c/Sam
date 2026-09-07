from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from workstation_core.config import Settings
from workstation_core.models_orm import User
from workstation_core.schemas import ExecutionRequestCreate, ExecutionRequestOut

from control.deps import get_current_user, get_db, get_settings_dep
from workstation_core import execution_service

router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.post("/requests", response_model=ExecutionRequestOut, status_code=status.HTTP_201_CREATED)
async def create_execution_request(
    payload: ExecutionRequestCreate, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep),
    user: User = Depends(get_current_user),
):
    return await execution_service.submit_request(
        db, settings, task_id=payload.task_id, operation=payload.operation, parameters=payload.parameters,
        working_directory=payload.working_directory, actor=user.id,
    )


@router.get("/requests/{request_id}", response_model=ExecutionRequestOut)
def get_execution_request(request_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    try:
        return execution_service.get_request(db, request_id)
    except execution_service.ExecutionRequestNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "execution request not found") from exc


@router.post("/requests/{request_id}/approve", response_model=ExecutionRequestOut)
async def approve_execution_request(
    request_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep),
    user: User = Depends(get_current_user),
):
    req = _get_request_or_404(db, request_id)
    if req.approval_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "this execution request has no pending approval")
    approval = execution_service.get_approval(db, req.approval_id)
    await execution_service.resolve_approval(db, settings, approval, approve=True, actor=user.id)
    db.refresh(req)
    return req


@router.post("/requests/{request_id}/deny", response_model=ExecutionRequestOut)
async def deny_execution_request(
    request_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep),
    user: User = Depends(get_current_user),
):
    req = _get_request_or_404(db, request_id)
    if req.approval_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "this execution request has no pending approval")
    approval = execution_service.get_approval(db, req.approval_id)
    await execution_service.resolve_approval(db, settings, approval, approve=False, actor=user.id)
    db.refresh(req)
    return req


def _get_request_or_404(db: Session, request_id: str):
    try:
        return execution_service.get_request(db, request_id)
    except execution_service.ExecutionRequestNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "execution request not found") from exc
