from workstation_core.db import get_sessionmaker
from workstation_core.models_orm import ModelRecord, Task
from worker.runner import WorkerRunner


def _make_local_model(db, name="llama3.2:latest"):
    model = ModelRecord(name=name, environment="local", provider="ollama", engine="ollama",
                        status="available", capabilities=["chat"])
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


async def test_worker_completes_a_local_chat_task(app_env, db, owner_user, fake_ollama_server, monkeypatch):
    monkeypatch.setattr(app_env, "ollama_local_url", fake_ollama_server)
    model = _make_local_model(db)
    task = Task(user_id=owner_user.id, type="chat", model_id=model.id, environment="local",
                status="QUEUED", input={"messages": [{"role": "user", "content": "hello"}]})
    db.add(task)
    db.commit()
    db.refresh(task)

    runner = WorkerRunner(app_env, get_sessionmaker())
    processed = await runner.run_once()
    assert processed is True

    db.commit()
    db.refresh(task)
    assert task.status == "COMPLETED"
    assert task.result["message"]["content"] == "hi"
    assert task.completed_at is not None


async def test_worker_idle_when_no_tasks_queued(app_env, db, owner_user):
    runner = WorkerRunner(app_env, get_sessionmaker())
    processed = await runner.run_once()
    assert processed is False
