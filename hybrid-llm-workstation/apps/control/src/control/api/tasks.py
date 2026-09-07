from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from workstation_core import task_service
from workstation_core.config import Settings
from workstation_core.enums import TaskStatus, TaskType
from workstation_core.models_orm import User
from workstation_core.schemas import TaskCreateRequest, TaskOut

from control.deps import get_current_user, get_db, get_settings_dep
from workstation_core.routing_service import RoutingError, resolve

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def list_tasks(status_: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return task_service.list_tasks(db, user_id=user.id, status=status_)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreateRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep),
    user: User = Depends(get_current_user),
):
    model_id = payload.model_id
    environment = payload.environment

    # Execution tasks (laptop actions via the local agent) have no model or
    # environment to route — routing only applies to inference tasks.
    if payload.type != TaskType.EXECUTION.value:
        # Resolve now for immediate, explicit routing errors; background
        # tasks (routing_mode == "automatic" with no model yet available)
        # are allowed through and re-resolved by the worker at claim time.
        if model_id or environment or payload.input.get("routing_mode") != "automatic":
            try:
                model = resolve(db, model_id=model_id, environment=environment, input_=payload.input)
                model_id, environment = model.id, model.environment
            except RoutingError as exc:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    task = task_service.create_task(
        db, user_id=user.id, type_=payload.type, model_id=model_id, environment=environment, input_=payload.input,
    )
    return task


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _get_owned_task(db, task_id, user)
    return task


@router.post("/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _get_owned_task(db, task_id, user)
    return task_service.cancel_task(db, task, actor=user.id)


@router.post("/{task_id}/pause", response_model=TaskOut)
def pause_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _get_owned_task(db, task_id, user)
    try:
        return task_service.pause_task(db, task, actor=user.id)
    except task_service.InvalidTaskTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{task_id}/resume", response_model=TaskOut)
def resume_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _get_owned_task(db, task_id, user)
    try:
        return task_service.resume_task(db, task, actor=user.id)
    except task_service.InvalidTaskTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/{task_id}/result")
def get_task_result(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _get_owned_task(db, task_id, user)
    if TaskStatus(task.status) not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        raise HTTPException(status.HTTP_409_CONFLICT, f"task is not finished (status={task.status})")
    return {"status": task.status, "result": task.result, "error": task.error}


def _get_owned_task(db: Session, task_id: str, user: User):
    try:
        task = task_service.get_task(db, task_id)
    except task_service.TaskNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found") from exc
    if task.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "task not found")
    return task
