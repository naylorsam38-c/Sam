"""Background worker loop (spec sections 2.5 and 11).

Each `run_once()` call claims at most one task and drives it end to end:
select model -> select environment -> start GPU if required -> execute ->
store progress/result -> release resources -> notify. Workers are plain
polling processes with no shared in-memory state, so any number of them can
run concurrently against the same database (spec: "multiple workers may run
concurrently subject to configured limits").
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from worker.control_client import ControlApiClient, ControlApiUnavailableError
from worker.errors import RetryableTaskError, TaskExecutionError
from workstation_core import task_service
from workstation_core.cloud_client import CloudInferenceClient, CloudInferenceUnavailableError
from workstation_core.config import Settings
from workstation_core.enums import Environment, GPUStatus, NotificationType, TaskStatus, TaskType
from workstation_core.execution_service import submit_request as submit_execution_request
from workstation_core.gpu_activity import mark_gpu_activity
from workstation_core.models_orm import GPUSession, ModelRecord, Task, User, Worker
from workstation_core.notification_service import notify
from workstation_core.ollama_client import OllamaClient, OllamaUnavailableError
from workstation_core.routing_service import RoutingError, resolve

logger = logging.getLogger("worker")

ELIGIBLE_TASK_TYPES = [TaskType.CHAT.value, TaskType.GENERATE.value, TaskType.EXECUTION.value]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkerRunner:
    def __init__(self, settings: Settings, session_factory, worker_id: str | None = None):
        self.settings = settings
        self._session_factory = session_factory
        self.worker_id = worker_id or str(uuid.uuid4())

    # --- lifecycle ------------------------------------------------------

    def _heartbeat(self, db: Session, *, current_task_id: str | None) -> None:
        worker_row = db.get(Worker, self.worker_id)
        if worker_row is None:
            worker_row = Worker(id=self.worker_id, status="idle")
            db.add(worker_row)
        worker_row.status = "busy" if current_task_id else "idle"
        worker_row.current_task_id = current_task_id
        worker_row.last_heartbeat = _now()
        db.commit()

    async def run_forever(self) -> None:
        logger.info("worker %s starting", self.worker_id)
        while True:
            try:
                processed = await self.run_once()
            except Exception:  # noqa: BLE001 - a single bad iteration must not kill the loop
                logger.exception("worker iteration failed")
                processed = False
            if not processed:
                with self._session_factory() as db:
                    self._heartbeat(db, current_task_id=None)
                await asyncio.sleep(self.settings.worker_poll_interval_seconds)

    async def run_once(self) -> bool:
        """Claim and fully process at most one task. Returns True if a task
        was claimed (regardless of whether it succeeded or failed)."""
        with self._session_factory() as db:
            self._heartbeat(db, current_task_id=None)
            task = task_service.claim_next_task(db, worker_id=self.worker_id, eligible_types=ELIGIBLE_TASK_TYPES)
            if task is None:
                return False
            task_id = task.id  # capture before the next commit expires `task`'s attributes
            self._heartbeat(db, current_task_id=task_id)

        await self._process_task(task_id)
        return True

    # --- task processing --------------------------------------------------

    async def _process_task(self, task_id: str) -> None:
        with self._session_factory() as db:
            task = db.get(Task, task_id)
            try:
                task = task_service.transition(db, task, TaskStatus.RUNNING, actor=f"worker:{self.worker_id}")
                db.commit()

                if task.type == TaskType.EXECUTION.value:
                    # Fully handled (including its own terminal/parked state
                    # transitions) by execution_service._sync_task — an
                    # execution task has no model/environment to resolve.
                    await self._run_execution_task(db, task)
                    return

                model = self._resolve_model(db, task)
                task.environment = model.environment
                result = await self._run_inference_task(db, task, model)

                task = task_service.transition(
                    db, task, TaskStatus.COMPLETED, actor=f"worker:{self.worker_id}", result=result, progress=1.0,
                )
                notify(db, user_id=task.user_id, type_=NotificationType.TASK_COMPLETED,
                       title="Task completed", body=f"{task.type} task finished")
                db.commit()

            except RetryableTaskError as exc:
                self._handle_failure(db, task, exc, retryable=True)
            except (TaskExecutionError, RoutingError) as exc:
                self._handle_failure(db, task, exc, retryable=False)
            except Exception as exc:  # noqa: BLE001 - unexpected errors still terminate the task cleanly
                logger.exception("unexpected error processing task %s", task_id)
                self._handle_failure(db, task, exc, retryable=False)

    def _handle_failure(self, db: Session, task: Task, exc: Exception, *, retryable: bool) -> None:
        if retryable and task.retry_count < self.settings.task_max_retries:
            task.retry_count += 1
            task_service.transition(db, task, TaskStatus.RETRYING, actor=f"worker:{self.worker_id}", error=str(exc))
            db.commit()
            task_service.transition(db, task, TaskStatus.QUEUED, actor=f"worker:{self.worker_id}",
                                    worker_id=None, started_at=None)
            db.commit()
            return

        task_service.transition(db, task, TaskStatus.FAILED, actor=f"worker:{self.worker_id}", error=str(exc))
        notify(db, user_id=task.user_id, type_=NotificationType.TASK_FAILED,
               title="Task failed", body=str(exc))
        db.commit()

    def _resolve_model(self, db: Session, task: Task) -> ModelRecord:
        if task.model_id:
            model = db.get(ModelRecord, task.model_id)
            if model is None:
                raise TaskExecutionError(f"model '{task.model_id}' no longer exists")
            # A cloud model marked unavailable just means the GPU isn't up
            # right now — _ensure_gpu_ready() is exactly what fixes that.
            # A local model marked unavailable means Ollama doesn't have it,
            # which nothing here can fix.
            if model.environment == Environment.LOCAL.value and model.status != "available":
                raise TaskExecutionError(
                    f"local model '{model.name}' is no longer available (status={model.status}); "
                    "refresh the registry or check Ollama"
                )
            return model
        return resolve(db, model_id=None, environment=task.environment, input_=task.input)

    # --- inference execution --------------------------------------------

    async def _run_inference_task(self, db: Session, task: Task, model: ModelRecord) -> dict:
        messages = task.input.get("messages", [])

        if model.environment == Environment.LOCAL.value:
            client = OllamaClient(self.settings.ollama_local_url)
            try:
                response = await client.chat(model.name, messages)
            except OllamaUnavailableError as exc:
                raise RetryableTaskError(f"local Ollama unavailable: {exc}") from exc
            return {"message": response.get("message"), "raw": response}

        endpoint = await self._ensure_gpu_ready(db)
        mark_gpu_activity(db, busy=True)
        db.commit()
        try:
            cloud = CloudInferenceClient(endpoint, self.settings.cloud_llm_api_key, self.settings.cloud_llm_engine)
            response = await cloud.chat(model.name, messages)
        except CloudInferenceUnavailableError as exc:
            raise RetryableTaskError(f"cloud inference failed: {exc}") from exc
        finally:
            mark_gpu_activity(db, busy=False)
            db.commit()
        return {"message": response.get("message") or response.get("choices"), "raw": response}

    async def _ensure_gpu_ready(self, db: Session) -> str:
        db.commit()  # start a fresh read transaction to see other processes' commits
        session = db.query(GPUSession).order_by(GPUSession.created_at.desc()).first()
        endpoint = (session.session_metadata or {}).get("endpoint") if session else None
        if session and session.status in (GPUStatus.READY.value, GPUStatus.BUSY.value, GPUStatus.IDLE.value) and endpoint:
            return endpoint

        if not self.settings.gpu_auto_start:
            raise TaskExecutionError("cloud GPU is off and GPU_AUTO_START is disabled; start it manually")

        owner = db.query(User).order_by(User.created_at.asc()).first()
        if owner is None:
            raise TaskExecutionError("no user account exists to authenticate the GPU start request")
        control_client = ControlApiClient(self.settings.control_api_url, owner.id, owner.username)
        try:
            await control_client.request_gpu_start()
        except ControlApiUnavailableError as exc:
            raise RetryableTaskError(f"could not request GPU start from control API: {exc}") from exc

        deadline = time.monotonic() + min(self.settings.gpu_max_session_minutes * 60, 600)
        while time.monotonic() < deadline:
            db.commit()
            session = db.query(GPUSession).order_by(GPUSession.created_at.desc()).first()
            if session and session.status == GPUStatus.READY.value:
                endpoint = (session.session_metadata or {}).get("endpoint")
                if endpoint:
                    return endpoint
            if session and session.status == GPUStatus.ERROR.value:
                raise RetryableTaskError(
                    f"GPU entered ERROR state while starting: {(session.session_metadata or {}).get('last_error')}"
                )
            await asyncio.sleep(1.0)
        raise RetryableTaskError("GPU did not become ready within the boot timeout")

    # --- execution-agent task type ---------------------------------------

    async def _run_execution_task(self, db: Session, task: Task) -> None:
        """A task of type "execution" asks the local agent to do something
        on the laptop, through the same approval-gated path a human uses
        via the API (spec section 16/17) — a task can never skip approval
        just because it originated from an LLM-driven background job.

        submit_execution_request already leaves the Task in the right state
        (REQUIRES_APPROVAL / FAILED / COMPLETED via
        workstation_core.execution_service._sync_task) — nothing further to
        do here regardless of the outcome."""
        await submit_execution_request(
            db, self.settings, task_id=task.id, operation=task.input.get("operation", ""),
            parameters=task.input.get("parameters", {}), working_directory=task.input.get("working_directory"),
            actor=f"worker:{self.worker_id}",
        )
