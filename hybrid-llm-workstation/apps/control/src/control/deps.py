from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from workstation_core.config import Settings
from workstation_core.db import get_db
from workstation_core.models_orm import User
from workstation_core.security import InvalidTokenError, decode_access_token

if TYPE_CHECKING:
    from control.gpu.lifecycle import GPULifecycleManager

_bearer_scheme = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_gpu_manager(request: Request) -> "GPULifecycleManager":
    return request.app.state.gpu_manager


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {exc}") from exc

    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user no longer exists")
    return user


__all__ = ["get_db", "get_current_user", "get_settings_dep", "get_gpu_manager"]
