"""A task parked at REQUIRES_APPROVAL must resolve itself automatically the
moment a human approves (or denies) the underlying execution request —
spec section 28: 'allow a task to request an action on the laptop, approve
or deny that action, see the resulting execution/audit record.'
"""

from workstation_core.db import get_sessionmaker
from workstation_core.execution_service import get_approval, resolve_approval
from workstation_core.models_orm import ExecutionRequest, Task
from worker.runner import WorkerRunner
from tests.support.fake_agent import fake_agent_server


async def test_approving_the_execution_request_completes_the_parked_task(app_env, db, owner_user):
    task = Task(user_id=owner_user.id, type="execution", status="QUEUED",
                input={"operation": "read_file", "parameters": {"path": "~/workstation-workspace/notes.txt"}})
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    runner = WorkerRunner(app_env, get_sessionmaker())
    await runner.run_once()
    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "REQUIRES_APPROVAL"

    exec_req = db.query(ExecutionRequest).filter(ExecutionRequest.task_id == task_id).one()

    with fake_agent_server() as (agent_url, received):
        app_env.execution_agent_url = agent_url
        approval = get_approval(db, exec_req.approval_id)
        await resolve_approval(db, app_env, approval, approve=True, actor=owner_user.id)

    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "COMPLETED", (task.status, task.error)
    assert len(received) == 1


async def test_denying_the_execution_request_fails_the_parked_task(app_env, db, owner_user):
    task = Task(user_id=owner_user.id, type="execution", status="QUEUED",
                input={"operation": "write_file", "parameters": {"path": "~/workstation-workspace/out.txt"}})
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id

    runner = WorkerRunner(app_env, get_sessionmaker())
    await runner.run_once()
    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "REQUIRES_APPROVAL"

    exec_req = db.query(ExecutionRequest).filter(ExecutionRequest.task_id == task_id).one()
    approval = get_approval(db, exec_req.approval_id)
    await resolve_approval(db, app_env, approval, approve=False, actor=owner_user.id)

    db.commit()
    task = db.get(Task, task_id)
    assert task.status == "FAILED"
    assert "denied" in task.error.lower()
