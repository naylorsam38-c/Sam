"""End-to-end cloud-task test: a real control API (uvicorn, in a background
thread) backed by the mock GPU provider, plus a worker that asks it to
start the GPU, waits for READY, then runs inference against the mock
provider's real HTTP endpoint. Nothing here is mocked at the HTTP layer —
every hop is a real socket.
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn

from workstation_core.db import get_sessionmaker
from workstation_core.models_orm import GPUSession, ModelRecord, Task
from worker.runner import WorkerRunner


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def running_control_api(app_env):
    from control.main import create_app

    port = _free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning", lifespan="on")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            httpx.get(f"{base_url}/health", timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:
        raise RuntimeError("control API did not start in time")

    yield base_url

    server.should_exit = True
    thread.join(timeout=10)


def _make_cloud_model(db, name="large-qwen"):
    model = ModelRecord(name=name, environment="cloud", provider="mock", engine="ollama",
                        status="available", capabilities=["chat"])
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


async def test_cloud_task_starts_gpu_and_completes(app_env, db, owner_user, running_control_api):
    app_env.control_api_url = running_control_api
    model = _make_cloud_model(db)
    task = Task(user_id=owner_user.id, type="chat", model_id=model.id, environment="cloud",
                status="QUEUED", input={"messages": [{"role": "user", "content": "hello from the worker"}]})
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    runner = WorkerRunner(app_env, get_sessionmaker())
    processed = await runner.run_once()
    assert processed is True

    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "COMPLETED", (task.status, task.error)
    assert "mock cloud GPU response" in task.result["message"]["content"]

    gpu_session = db.query(GPUSession).order_by(GPUSession.created_at.desc()).first()
    assert gpu_session.status == "READY"  # released back to READY after inference, GPU left running


async def test_cloud_task_works_from_a_cold_start(app_env, db, owner_user, running_control_api):
    """The cloud model was discovered on some earlier session and is now
    marked unavailable because the GPU has been off since — this is the
    normal state between sessions, and picking that model to start a new
    task is exactly what should boot the GPU back up (spec: 'select a
    cloud model' -> 'GPU automatically starts'), not be rejected outright."""
    app_env.control_api_url = running_control_api
    model = _make_cloud_model(db)
    model.status = "unavailable"
    db.commit()

    task = Task(user_id=owner_user.id, type="chat", model_id=model.id, environment="cloud",
                status="QUEUED", input={"messages": [{"role": "user", "content": "cold start"}]})
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    runner = WorkerRunner(app_env, get_sessionmaker())
    await runner.run_once()

    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "COMPLETED", (task.status, task.error)
