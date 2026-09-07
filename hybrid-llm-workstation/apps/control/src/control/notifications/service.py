"""Notification generation (spec section 19). Persists first, always —
notifications must survive a browser refresh or restart; delivery to a
future push/webhook channel is additive, never a replacement for the
persisted record."""

from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from workstation_core.config import get_settings
from workstation_core.enums import NotificationType
from workstation_core.models_orm import Notification


def _load_enabled_events(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("events", {})


def notify(db: Session, *, user_id: str, type_: NotificationType, title: str, body: str = "") -> Notification | None:
    settings = get_settings()
    if not settings.notification_enabled:
        return None

    enabled_events = _load_enabled_events(settings.notifications_config_path)
    if enabled_events.get(type_.value) is False:
        return None

    notification = Notification(user_id=user_id, type=type_.value, title=title, body=body)
    db.add(notification)
    db.flush()
    return notification
