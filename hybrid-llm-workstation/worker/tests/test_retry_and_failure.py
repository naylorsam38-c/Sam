from workstation_core.db import get_sessionmaker
from workstation_core.models_orm import ModelRecord, Notification, Task
from worker.runner import WorkerRunner


def _make_local_model(db, name="llama3.2:latest"):
    model = ModelRecord(name=name, environment="local", provider="ollama", engine="ollama",
                        status="available", capabilities=["chat"])
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


async def test_unreachable_ollama_retries_then_fails(app_env, db, owner_user, monkeypatch):
    monkeypatch.setattr(app_env, "ollama_local_url", "http://127.0.0.1:1")  # nothing listens here
    monkeypatch.setattr(app_env, "task_max_retries", 2)
    model = _make_local_model(db)
    task = Task(user_id=owner_user.id, type="chat", model_id=model.id, environment="local",
                status="QUEUED", input={"messages": [{"role": "user", "content": "hello"}]})
    db.add(task)
    db.commit()
    db.refresh(task)

    runner = WorkerRunner(app_env, get_sessionmaker())

    # Attempt 1: fails, retries (retry_count 0 -> 1), requeued
    await runner.run_once()
    db.commit()
    db.refresh(task)
    assert task.status == "QUEUED"
    assert task.retry_count == 1

    # Attempt 2: fails, retries (1 -> 2)
    await runner.run_once()
    db.commit()
    db.refresh(task)
    assert task.status == "QUEUED"
    assert task.retry_count == 2

    # Attempt 3: retries exhausted (2 >= max_retries=2) -> FAILED
    await runner.run_once()
    db.commit()
    db.refresh(task)
    assert task.status == "FAILED"
    assert task.error is not None

    notifications = db.query(Notification).filter(Notification.user_id == owner_user.id).all()
    assert any(n.type == "task_failed" for n in notifications)


async def test_model_unavailable_after_queueing_fails_without_retry(app_env, db, owner_user):
    model = _make_local_model(db)
    task = Task(user_id=owner_user.id, type="chat", model_id=model.id, environment="local",
                status="QUEUED", input={"messages": []})
    db.add(task)
    db.commit()
    db.refresh(task)

    # Simulate the model going unavailable (e.g. Ollama no longer reports
    # it) between task creation and the worker claiming it.
    model.status = "unavailable"
    db.commit()

    runner = WorkerRunner(app_env, get_sessionmaker())
    await runner.run_once()

    db.commit()
    db.refresh(task)
    assert task.status == "FAILED"
    assert task.retry_count == 0
