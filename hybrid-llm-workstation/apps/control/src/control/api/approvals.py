from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from control.deps import get_current_user, get_db, get_settings_dep
from control.execution import service as execution_service
from workstation_core.config import Settings
from workstation_core.models_orm import User
from workstation_core.schemas import ApprovalOut

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_approvals(status_: str | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return execution_service.list_approvals(db, status=status_)


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
async def approve(
    approval_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep),
    user: User = Depends(get_current_user),
):
    try:
        approval = execution_service.get_approval(db, approval_id)
    except execution_service.ApprovalNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
    return await execution_service.resolve_approval(db, settings, approval, approve=True, actor=user.id)


@router.post("/{approval_id}/deny", response_model=ApprovalOut)
async def deny(
    approval_id: str, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep),
    user: User = Depends(get_current_user),
):
    try:
        approval = execution_service.get_approval(db, approval_id)
    except execution_service.ApprovalNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "approval not found") from exc
    return await execution_service.resolve_approval(db, settings, approval, approve=False, actor=user.id)
