from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from workstation_core.models_orm import Notification, User
from workstation_core.schemas import NotificationOut

from control.deps import get_current_user, get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.status == "unread")
    return query.order_by(Notification.created_at.desc()).all()


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    notification = db.get(Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "notification not found")
    notification.status = "read"
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification
