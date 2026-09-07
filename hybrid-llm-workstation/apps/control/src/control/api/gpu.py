from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from workstation_core.models_orm import User
from workstation_core.schemas import GPUCostOut, GPUStatusOut

from control.deps import get_current_user, get_db, get_gpu_manager
from control.gpu.lifecycle import GPULifecycleError, GPULifecycleManager

router = APIRouter(prefix="/api/gpu", tags=["gpu"])


def _to_status_out(session, settings) -> GPUStatusOut:
    meta = session.session_metadata or {}
    return GPUStatusOut(
        status=session.status,
        provider=session.provider,
        instance_id=session.instance_id,
        endpoint=meta.get("endpoint"),
        started_at=session.started_at,
        last_activity_at=session.last_activity_at,
        idle_timeout_minutes=settings.gpu_idle_timeout_minutes,
        max_session_minutes=settings.gpu_max_session_minutes,
        max_hourly_cost=settings.gpu_max_hourly_cost,
        estimated_cost=session.estimated_cost or 0.0,
        actual_cost=session.actual_cost,
        auto_stop=settings.gpu_auto_stop,
        error=meta.get("last_error"),
    )


@router.get("", response_model=GPUStatusOut)
async def get_gpu_status(
    db: Session = Depends(get_db), manager: GPULifecycleManager = Depends(get_gpu_manager),
    _user: User = Depends(get_current_user),
) -> GPUStatusOut:
    session = await manager.get_status(db)
    return _to_status_out(session, manager.settings)


@router.post("/start", response_model=GPUStatusOut)
async def start_gpu(
    db: Session = Depends(get_db), manager: GPULifecycleManager = Depends(get_gpu_manager),
    user: User = Depends(get_current_user),
) -> GPUStatusOut:
    try:
        session = await manager.start(db, actor=user.id)
    except GPULifecycleError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _to_status_out(session, manager.settings)


@router.post("/stop", response_model=GPUStatusOut)
async def stop_gpu(
    force: bool = False, db: Session = Depends(get_db), manager: GPULifecycleManager = Depends(get_gpu_manager),
    user: User = Depends(get_current_user),
) -> GPUStatusOut:
    try:
        session = await manager.stop(db, actor=user.id, force=force)
    except GPULifecycleError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _to_status_out(session, manager.settings)


@router.post("/restart", response_model=GPUStatusOut)
async def restart_gpu(
    db: Session = Depends(get_db), manager: GPULifecycleManager = Depends(get_gpu_manager),
    user: User = Depends(get_current_user),
) -> GPUStatusOut:
    try:
        await manager.stop(db, actor=user.id, force=False)
        session = await manager.start(db, actor=user.id)
    except GPULifecycleError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return _to_status_out(session, manager.settings)


@router.get("/cost", response_model=GPUCostOut)
async def gpu_cost(
    db: Session = Depends(get_db), manager: GPULifecycleManager = Depends(get_gpu_manager),
    _user: User = Depends(get_current_user),
) -> GPUCostOut:
    return GPUCostOut(**await manager.get_cost(db))
