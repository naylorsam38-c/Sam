from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from control.deps import get_current_user, get_db, get_settings_dep
from control.models.registry import refresh_registry
from workstation_core.config import Settings
from workstation_core.models_orm import ModelRecord, User
from workstation_core.schemas import ModelOut

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[ModelOut])
def list_models(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[ModelRecord]:
    return db.query(ModelRecord).order_by(ModelRecord.environment, ModelRecord.name).all()


@router.get("/local", response_model=list[ModelOut])
def list_local_models(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[ModelRecord]:
    return db.query(ModelRecord).filter(ModelRecord.environment == "local").order_by(ModelRecord.name).all()


@router.get("/cloud", response_model=list[ModelOut])
def list_cloud_models(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[ModelRecord]:
    return db.query(ModelRecord).filter(ModelRecord.environment == "cloud").order_by(ModelRecord.name).all()


@router.get("/{model_id}", response_model=ModelOut)
def get_model(model_id: str, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> ModelRecord:
    model = db.get(ModelRecord, model_id)
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "model not found")
    return model


@router.post("/refresh")
async def refresh_models(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings_dep),
    _user: User = Depends(get_current_user),
) -> dict:
    report = await refresh_registry(db, settings)
    db.commit()
    return report
