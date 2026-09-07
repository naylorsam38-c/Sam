from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from workstation_core.audit_service import record as audit_record
from workstation_core.models_orm import User
from workstation_core.schemas import LoginRequest, TokenResponse
from workstation_core.security import create_access_token, verify_password

from control.deps import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        audit_record(db, actor=payload.username, event_type="auth.login_failed", resource_type="user",
                     resource_id=None, action="login")
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid username or password")

    audit_record(db, actor=user.id, event_type="auth.login_succeeded", resource_type="user",
                 resource_id=user.id, action="login")
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.username))
