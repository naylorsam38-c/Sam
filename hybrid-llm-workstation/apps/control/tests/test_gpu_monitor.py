"""Direct unit tests of GPULifecycleManager's idle-timeout / cost-limit /
max-session monitor logic (spec sections 8 and 20), bypassing HTTP so we can
manipulate timestamps precisely.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from control.gpu.lifecycle import GPULifecycleManager
from workstation_core.db import get_sessionmaker
from workstation_core.enums import GPUStatus
from workstation_core.models_orm import User


@pytest.fixture()
def manager(app_env, db):
    db.add(User(username="sam", password_hash="x"))
    db.commit()
    return GPULifecycleManager(app_env, get_sessionmaker())


async def _start_and_wait_ready(manager, db):
    import asyncio

    await manager.start(db, actor="test")
    for _ in range(200):
        # The boot task commits its progress on a *different* Session; this
        # session must end its own read transaction between polls or SQLite
        # keeps serving it a snapshot from before those commits.
        db.commit()
        session = await manager.get_status(db)
        if session.status == GPUStatus.READY.value:
            return session
        await asyncio.sleep(0.01)
    raise AssertionError("GPU never became ready")


@pytest.mark.asyncio
async def test_idle_timeout_auto_stops(manager, db, app_env):
    app_env.gpu_idle_timeout_minutes = 5
    app_env.gpu_auto_stop = True
    await _start_and_wait_ready(manager, db)

    session = await manager.get_status(db)
    session.last_activity_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()

    await manager._monitor_tick()

    session = await manager.get_status(db)
    assert session.status == GPUStatus.OFF.value


@pytest.mark.asyncio
async def test_idle_without_autostop_only_marks_idle(manager, db, app_env):
    app_env.gpu_idle_timeout_minutes = 5
    app_env.gpu_auto_stop = False
    await _start_and_wait_ready(manager, db)

    session = await manager.get_status(db)
    session.last_activity_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()

    await manager._monitor_tick()

    session = await manager.get_status(db)
    assert session.status == GPUStatus.IDLE.value  # visible, but not stopped


@pytest.mark.asyncio
async def test_busy_gpu_is_never_touched_by_monitor(manager, db, app_env):
    app_env.gpu_idle_timeout_minutes = 5
    app_env.gpu_auto_stop = True
    await _start_and_wait_ready(manager, db)
    manager.mark_activity(db, busy=True)
    db.commit()

    session = await manager.get_status(db)
    session.last_activity_at = datetime.now(timezone.utc) - timedelta(hours=5)
    db.commit()

    await manager._monitor_tick()

    session = await manager.get_status(db)
    assert session.status == GPUStatus.BUSY.value  # never terminated mid-inference


@pytest.mark.asyncio
async def test_max_session_duration_forces_stop(manager, db, app_env):
    app_env.gpu_max_session_minutes = 1
    await _start_and_wait_ready(manager, db)

    session = await manager.get_status(db)
    session.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()

    await manager._monitor_tick()

    session = await manager.get_status(db)
    assert session.status == GPUStatus.OFF.value


@pytest.mark.asyncio
async def test_cost_limit_forces_stop(manager, db, app_env):
    # Must stay >= the mock provider's simulated hourly rate
    # (settings.gpu_estimated_hourly_cost, default 0.50) or the post-boot
    # rate check in _boot_and_finalize would stop it before this test gets
    # a chance to exercise the ongoing session-budget check below.
    app_env.gpu_max_hourly_cost = 1.0
    app_env.gpu_max_session_minutes = 240  # budget = 1.0 * 4h = $4.00
    await _start_and_wait_ready(manager, db)

    # Session wall-clock start stays recent (so max-session-duration doesn't
    # also fire); only the provider's internal cost clock is pushed back, to
    # isolate the accrued-cost check from the elapsed-duration check.
    provider = manager._get_provider()
    provider._started_at = (datetime.now(timezone.utc) - timedelta(hours=10)).timestamp()  # cost = 0.5 * 10 = $5.00 > $4.00 budget

    await manager._monitor_tick()

    session = await manager.get_status(db)
    assert session.status == GPUStatus.OFF.value
