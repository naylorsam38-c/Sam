"""GPU lifecycle manager — owns the single live GPUProvider connection for
this control-API process and drives the state machine in
workstation_core.enums (spec section 8).

Ownership model: only this manager (running inside the control API process)
ever calls provider.start()/stop()/destroy(). The worker process, which may
run separately, never imports a provider directly — it asks for a GPU via
POST /api/gpu/start and polls GET /api/gpu, and marks BUSY/READY itself by
writing to the shared `gpu_sessions` row (spec: workers are independent
processes coordinating through persisted state, not sharing objects).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from control.audit.service import record as audit_record
from control.notifications.service import notify
from gpu.provider_interface.base import GPUProvider, GPUProviderError
from gpu.registry import get_provider
from workstation_core.config import Settings
from workstation_core.enums import GPU_PROTECTED_STATES, GPU_TRANSITIONS, GPUStatus, NotificationType
from workstation_core.models_orm import GPUSession

logger = logging.getLogger("control.gpu")

SYSTEM_ACTOR = "system:gpu-lifecycle"


class GPULifecycleError(Exception):
    pass


class GPULifecycleManager:
    def __init__(self, settings: Settings, session_factory):
        self.settings = settings
        self._session_factory = session_factory
        self._provider: GPUProvider | None = None
        self._lock = asyncio.Lock()
        self._monitor_task: asyncio.Task | None = None

    # --- provider handle -------------------------------------------------

    def _get_provider(self) -> GPUProvider:
        if self._provider is None:
            self._provider = get_provider(
                self.settings.gpu_provider,
                api_key=self.settings.gpu_provider_api_key,
                template_id=self.settings.gpu_template_id,
                volume_id=self.settings.gpu_volume_id,
                hourly_rate=self.settings.gpu_estimated_hourly_cost,
            )
        return self._provider

    # --- session row helpers ----------------------------------------------

    def _current_session(self, db: Session) -> GPUSession:
        session = (
            db.query(GPUSession)
            .order_by(GPUSession.created_at.desc())
            .first()
        )
        if session is None:
            session = GPUSession(provider=self.settings.gpu_provider, status=GPUStatus.OFF.value)
            db.add(session)
            db.flush()
        return session

    def _transition(self, session: GPUSession, new_status: GPUStatus, db: Session, error: str | None = None) -> None:
        current = GPUStatus(session.status)
        allowed = GPU_TRANSITIONS.get(current, set())
        if new_status != current and new_status not in allowed:
            raise GPULifecycleError(f"illegal GPU transition {current} -> {new_status}")
        session.status = new_status.value
        if new_status == GPUStatus.ERROR and error:
            meta = dict(session.session_metadata or {})
            meta["last_error"] = error
            session.session_metadata = meta
        db.flush()

    # --- reconciliation at process startup -------------------------------

    async def reconcile_on_startup(self) -> None:
        """Recover from a control-API restart. Real providers that expose a
        stable instance id (e.g. RunPod) are re-queried for ground truth;
        anything we cannot verify is marked ERROR rather than assumed OFF,
        because assuming OFF could hide an actually-running, cost-accruing
        instance (spec rule: 'if something is unknown, do not guess')."""
        with self._session_factory() as db:
            session = self._current_session(db)
            if session.status == GPUStatus.OFF.value:
                return

            if not session.instance_id:
                self._transition(session, GPUStatus.OFF, db)
                db.commit()
                return

            try:
                provider = self._get_provider()
                if hasattr(provider, "_pod_id"):
                    provider._pod_id = session.instance_id  # type: ignore[attr-defined]
                status = await provider.status()
            except Exception as exc:  # noqa: BLE001 - any provider failure here must not crash startup
                logger.warning("GPU reconciliation could not verify provider state: %s", exc)
                self._transition(session, GPUStatus.ERROR, db, error=f"could not reconcile after restart: {exc}")
                audit_record(db, actor=SYSTEM_ACTOR, event_type="gpu.reconcile_failed", resource_type="gpu_session",
                             resource_id=session.id, action="reconcile", metadata={"error": str(exc)})
                db.commit()
                return

            new_status = GPUStatus.READY if status.ready else (GPUStatus.STARTING if status.running else GPUStatus.OFF)
            session.status = new_status.value  # direct set: recovering from an unknown prior state
            db.flush()
            db.commit()

    # --- public operations ---------------------------------------------

    async def get_status(self, db: Session) -> GPUSession:
        return self._current_session(db)

    async def start(self, db: Session, actor: str) -> GPUSession:
        async with self._lock:
            session = self._current_session(db)
            current = GPUStatus(session.status)

            if current in (GPUStatus.READY, GPUStatus.BUSY, GPUStatus.IDLE):
                return session  # already up — idempotent
            if current in (GPUStatus.PROVISIONING, GPUStatus.STARTING, GPUStatus.BOOTING):
                return session  # a start is already in flight

            if not self.settings.gpu_auto_start and actor == "system":
                raise GPULifecycleError("GPU_AUTO_START is disabled; a user must start the GPU explicitly")

            provider = self._get_provider()
            try:
                if current == GPUStatus.OFF:
                    self._transition(session, GPUStatus.PROVISIONING, db)
                    db.commit()
                    await provider.provision()
                    self._transition(session, GPUStatus.STARTING, db)
                else:
                    # Retrying from ERROR: provisioning (e.g. the volume)
                    # already happened, go straight to (re)starting.
                    self._transition(session, GPUStatus.STARTING, db)
                instance_id = await provider.start()
                session.instance_id = instance_id
                session.started_at = datetime.now(timezone.utc)
                session.last_activity_at = session.started_at
                db.commit()
            except GPUProviderError as exc:
                self._transition(session, GPUStatus.ERROR, db, error=str(exc))
                notify(db, user_id=_owner_user_id(db), type_=NotificationType.GPU_ERROR,
                       title="GPU failed to start", body=str(exc))
                audit_record(db, actor=actor, event_type="gpu.start_failed", resource_type="gpu_session",
                             resource_id=session.id, action="start", metadata={"error": str(exc)})
                db.commit()
                raise GPULifecycleError(str(exc)) from exc

            self._transition(session, GPUStatus.BOOTING, db)
            db.commit()
            audit_record(db, actor=actor, event_type="gpu.start_requested", resource_type="gpu_session",
                         resource_id=session.id, action="start")
            db.commit()

            self._monitor_task = self._monitor_task or asyncio.create_task(self._background_monitor_loop())
            asyncio.create_task(self._boot_and_finalize(session.id))
            return session

    async def _boot_and_finalize(self, session_id: str) -> None:
        provider = self._get_provider()
        deadline = asyncio.get_event_loop().time() + min(self.settings.gpu_max_session_minutes * 60, 600)
        healthy = False
        detail = "boot timed out"
        while asyncio.get_event_loop().time() < deadline:
            try:
                status = await provider.status()
                if status.ready:
                    ok, detail = await provider.health()
                    if ok:
                        healthy = True
                        break
            except GPUProviderError as exc:
                detail = str(exc)
            await asyncio.sleep(1.0)

        with self._session_factory() as db:
            session = db.get(GPUSession, session_id)
            if session is None:
                return
            if healthy:
                status = await provider.status()
                endpoint = status.endpoint or provider.get_endpoint()
                meta = dict(session.session_metadata or {})
                meta["endpoint"] = endpoint
                session.session_metadata = meta
                self._transition(session, GPUStatus.READY, db)
                notify(db, user_id=_owner_user_id(db), type_=NotificationType.GPU_STARTED,
                       title="Cloud GPU ready", body=f"Endpoint: {endpoint}")
                audit_record(db, actor=SYSTEM_ACTOR, event_type="gpu.ready", resource_type="gpu_session",
                             resource_id=session.id, action="ready", metadata={"endpoint": endpoint})

                cost = await provider.get_cost()
                if cost.hourly_rate and cost.hourly_rate > self.settings.gpu_max_hourly_cost:
                    detail = (
                        f"provider hourly rate ${cost.hourly_rate:.2f} exceeds "
                        f"GPU_MAX_HOURLY_COST ${self.settings.gpu_max_hourly_cost:.2f}"
                    )
                    await self._safe_stop(db, session, reason=detail, notify_type=NotificationType.COST_LIMIT_REACHED)
            else:
                self._transition(session, GPUStatus.ERROR, db, error=detail)
                notify(db, user_id=_owner_user_id(db), type_=NotificationType.GPU_ERROR,
                       title="GPU failed to become healthy", body=detail)
                audit_record(db, actor=SYSTEM_ACTOR, event_type="gpu.boot_failed", resource_type="gpu_session",
                             resource_id=session.id, action="boot", metadata={"detail": detail})
            db.commit()

    async def stop(self, db: Session, actor: str, force: bool = False) -> GPUSession:
        async with self._lock:
            session = self._current_session(db)
            current = GPUStatus(session.status)
            if current == GPUStatus.OFF:
                return session
            if current in GPU_PROTECTED_STATES and not force:
                raise GPULifecycleError(
                    f"refusing to stop GPU while status is {current} (active work in progress); "
                    "pass force=true only if you accept terminating active inference"
                )
            await self._safe_stop(db, session, reason="requested" if not force else "forced", actor=actor)
            db.commit()
            return session

    async def _safe_stop(
        self, db: Session, session: GPUSession, *, reason: str,
        actor: str = SYSTEM_ACTOR, notify_type: NotificationType = NotificationType.GPU_STOPPED,
    ) -> None:
        provider = self._get_provider()
        self._transition(session, GPUStatus.STOPPING, db)
        db.flush()
        try:
            cost = await provider.get_cost()
            session.estimated_cost = cost.estimated_cost
        except GPUProviderError:
            pass
        await provider.stop()
        self._transition(session, GPUStatus.OFF, db)
        session.stopped_at = datetime.now(timezone.utc)
        db.flush()
        notify(db, user_id=_owner_user_id(db), type_=notify_type, title="Cloud GPU stopped", body=reason)
        audit_record(db, actor=actor, event_type="gpu.stopped", resource_type="gpu_session",
                     resource_id=session.id, action="stop", metadata={"reason": reason})

    async def get_cost(self, db: Session) -> dict:
        session = self._current_session(db)
        if session.status == GPUStatus.OFF.value:
            return {
                "status": session.status, "session_minutes": 0.0,
                "estimated_cost": session.estimated_cost or 0.0,
                "max_hourly_cost": self.settings.gpu_max_hourly_cost, "over_limit": False,
            }
        provider = self._get_provider()
        cost = await provider.get_cost()
        budget = self.settings.gpu_max_hourly_cost * (self.settings.gpu_max_session_minutes / 60.0)
        return {
            "status": session.status,
            "session_minutes": cost.session_seconds / 60.0,
            "estimated_cost": cost.estimated_cost,
            "max_hourly_cost": self.settings.gpu_max_hourly_cost,
            "over_limit": cost.estimated_cost > budget,
        }

    def mark_activity(self, db: Session, *, busy: bool) -> None:
        """Called by the worker (same DB, different process) when it starts
        or finishes using the GPU for inference."""
        session = self._current_session(db)
        current = GPUStatus(session.status)
        if current not in (GPUStatus.READY, GPUStatus.BUSY, GPUStatus.IDLE):
            return
        session.last_activity_at = datetime.now(timezone.utc)
        target = GPUStatus.BUSY if busy else GPUStatus.READY
        if target != current:
            self._transition(session, target, db)
        db.flush()

    # --- background monitor: idle timeout, max session, cost cap --------

    async def _background_monitor_loop(self) -> None:
        while True:
            await asyncio.sleep(self.settings.gpu_monitor_interval_seconds)
            try:
                await self._monitor_tick()
            except Exception:  # noqa: BLE001
                logger.exception("GPU monitor tick failed")

    async def _monitor_tick(self) -> None:
        with self._session_factory() as db:
            session = self._current_session(db)
            status = GPUStatus(session.status)
            if status == GPUStatus.OFF:
                return

            now = datetime.now(timezone.utc)

            if session.started_at and session.started_at.tzinfo is None:
                session.started_at = session.started_at.replace(tzinfo=timezone.utc)
            if session.last_activity_at and session.last_activity_at.tzinfo is None:
                session.last_activity_at = session.last_activity_at.replace(tzinfo=timezone.utc)

            over_session_limit = (
                session.started_at is not None
                and now - session.started_at > timedelta(minutes=self.settings.gpu_max_session_minutes)
            )

            cost_info = None
            over_cost_limit = False
            if status in (GPUStatus.READY, GPUStatus.BUSY, GPUStatus.IDLE):
                try:
                    cost_info = await self.get_cost(db)
                    over_cost_limit = cost_info["over_limit"]
                except GPUProviderError:
                    pass

            if status in GPU_PROTECTED_STATES:
                return  # never touch an in-flight boot or active inference

            if over_cost_limit:
                await self._safe_stop(db, session, reason="GPU_MAX_HOURLY_COST budget exceeded",
                                       notify_type=NotificationType.COST_LIMIT_REACHED)
                db.commit()
                return

            if over_session_limit:
                await self._safe_stop(db, session, reason="GPU_MAX_SESSION_MINUTES exceeded")
                db.commit()
                return

            idle_for = now - session.last_activity_at if session.last_activity_at else None
            if status == GPUStatus.READY and idle_for and idle_for > timedelta(minutes=self.settings.gpu_idle_timeout_minutes):
                self._transition(session, GPUStatus.IDLE, db)
                db.commit()
                status = GPUStatus.IDLE

            if status == GPUStatus.IDLE and self.settings.gpu_auto_stop:
                await self._safe_stop(db, session, reason="idle timeout reached")
                db.commit()


def _owner_user_id(db: Session) -> str:
    """Single-user system: notifications always go to the one user account."""
    from workstation_core.models_orm import User

    user = db.query(User).order_by(User.created_at.asc()).first()
    return user.id if user else "unknown"
