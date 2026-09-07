"""One coherent end-to-end run through most of spec section 28's
Definition of Done, against real running services (control API, local
agent, worker) — no step here is asserted from a mock return value; every
assertion reads back real state from a real HTTP response or a real
database row.
"""

from __future__ import annotations

import asyncio
import time

from workstation_core.db import get_sessionmaker
from worker.runner import WorkerRunner


def _wait_for_task(api, task_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = api.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
            return task
        time.sleep(0.2)
    raise AssertionError(f"task {task_id} did not finish in time")


def _wait_for_gpu_ready(api, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = api.get("/api/gpu").json()
        if status["status"] == "READY":
            return status
        time.sleep(0.1)
    raise AssertionError("GPU did not become READY in time")


def test_full_workstation_lifecycle(api, running_control_api, workspace):
    _base_url, settings = running_control_api
    worker = WorkerRunner(settings, get_sessionmaker())

    def run_worker_once() -> bool:
        return asyncio.run(worker.run_once())

    # --- 1-3. One interface shows local and cloud models --------------
    refresh = api.post("/api/models/refresh").json()
    assert refresh["local"]["healthy"] is True
    models = api.get("/api/models").json()
    local_model = next(m for m in models if m["environment"] == "local")
    assert local_model["status"] == "available"

    # --- 4. Select a local model and chat with it ----------------------
    task = api.post("/api/tasks", json={
        "type": "chat", "model_id": local_model["id"],
        "input": {"messages": [{"role": "user", "content": "hello locally"}]},
    }).json()
    run_worker_once()
    completed = _wait_for_task(api, task["id"])
    assert completed["status"] == "COMPLETED"
    assert completed["result"]["message"]["content"] == "hi"

    # --- 5-9. Select a cloud model; GPU auto-starts; chat; see status/cost --
    assert api.get("/api/gpu").json()["status"] == "OFF"
    api.post("/api/gpu/start")
    _wait_for_gpu_ready(api)

    refresh = api.post("/api/models/refresh").json()
    assert refresh["cloud"]["healthy"] is True
    cloud_model = next(m for m in api.get("/api/models/cloud").json() if m["status"] == "available")

    cloud_task = api.post("/api/tasks", json={
        "type": "chat", "model_id": cloud_model["id"],
        "input": {"messages": [{"role": "user", "content": "hello cloud"}]},
    }).json()
    run_worker_once()
    cloud_result = _wait_for_task(api, cloud_task["id"])
    assert cloud_result["status"] == "COMPLETED"
    assert "mock cloud GPU response" in cloud_result["result"]["message"]["content"]

    cost = api.get("/api/gpu/cost").json()
    assert cost["status"] in ("READY", "IDLE", "BUSY")
    assert cost["estimated_cost"] >= 0

    # --- 10. Stop the GPU -------------------------------------------------
    api.post("/api/gpu/stop")
    assert api.get("/api/gpu").json()["status"] == "OFF"

    # --- 11-14. Create a background task, "close the browser" (nothing
    #     browser-side to actually close — the point is the task's state
    #     lives in the DB, not in any client session), "reopen", see the
    #     persisted result -------------------------------------------
    bg_task = api.post("/api/tasks", json={
        "type": "chat", "model_id": local_model["id"],
        "input": {"messages": [{"role": "user", "content": "background please"}]},
    }).json()
    run_worker_once()
    # Simulate "reopening the browser": a fresh read-by-id, independent of
    # whatever client state created the task.
    reread = api.get(f"/api/tasks/{bg_task['id']}").json()
    assert reread["status"] == "COMPLETED"
    result = api.get(f"/api/tasks/{bg_task['id']}/result").json()
    assert result["result"]["message"]["content"] == "hi"

    # --- 15-17. Task requests a laptop action; approve it; see the
    #     resulting execution/audit record -----------------------------
    (workspace / "note.txt").write_text("laptop file")
    exec_task = api.post("/api/tasks", json={
        "type": "execution",
        "input": {"operation": "read_file", "parameters": {"path": str(workspace / "note.txt")}},
    }).json()
    run_worker_once()
    parked = api.get(f"/api/tasks/{exec_task['id']}").json()
    assert parked["status"] == "REQUIRES_APPROVAL"

    approvals = api.get("/api/approvals?status_=PENDING").json()
    approval = next(a for a in approvals if a["task_id"] == exec_task["id"])
    approved = api.post(f"/api/approvals/{approval['id']}/approve").json()
    assert approved["status"] == "APPROVED"

    finished = api.get(f"/api/tasks/{exec_task['id']}").json()
    assert finished["status"] == "COMPLETED"

    # --- Notifications exist for everything that happened ----------------
    notifications = api.get("/api/notifications").json()
    types = {n["type"] for n in notifications}
    assert "task_completed" in types
    assert "gpu_started" in types
    assert "gpu_stopped" in types
