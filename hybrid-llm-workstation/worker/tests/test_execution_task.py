from workstation_core.db import get_sessionmaker
from workstation_core.models_orm import Task
from worker.runner import WorkerRunner
from tests.support.fake_agent import fake_agent_server


async def test_execution_task_parks_at_requires_approval(app_env, db, owner_user):
    task = Task(user_id=owner_user.id, type="execution", status="QUEUED",
                input={"operation": "read_file", "parameters": {"path": "~/workstation-workspace/notes.txt"}})
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    runner = WorkerRunner(app_env, get_sessionmaker())
    processed = await runner.run_once()
    assert processed is True

    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "REQUIRES_APPROVAL"


async def test_execution_task_denied_by_policy_fails_the_task(app_env, db, owner_user):
    task = Task(user_id=owner_user.id, type="execution", status="QUEUED",
                input={"operation": "read_file", "parameters": {"path": "/etc/passwd"}})
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    runner = WorkerRunner(app_env, get_sessionmaker())
    await runner.run_once()

    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "FAILED"
    assert "denied" in task.error.lower()


async def test_execution_task_trusted_completes_immediately(app_env, db, owner_user, tmp_path):
    import yaml

    policies_path = tmp_path / "policies.yaml"
    policies_path.write_text(yaml.safe_dump({
        "operations": [
            {"operation": "list_directory", "level": "TRUSTED", "risk": "LOW", "allowed_paths": ["~/workstation-workspace"]},
        ]
    }))
    app_env.config_dir = tmp_path

    task = Task(user_id=owner_user.id, type="execution", status="QUEUED",
                input={"operation": "list_directory", "parameters": {"path": "~/workstation-workspace"}})
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    with fake_agent_server() as (agent_url, received):
        app_env.execution_agent_url = agent_url
        runner = WorkerRunner(app_env, get_sessionmaker())
        await runner.run_once()

    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "COMPLETED", (task.status, task.error)
    assert len(received) == 1
