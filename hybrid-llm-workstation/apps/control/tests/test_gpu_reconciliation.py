"""Tests for GPULifecycleManager.reconcile_on_startup — what happens when
the control API process restarts while the GPU session row says it was
non-OFF (spec section 28 item 19: 'restart the system without losing
persistent state', and the rule that an unknown state must never be
silently assumed safe).
"""

from __future__ import annotations

import pytest

from control.gpu.lifecycle import GPULifecycleManager
from gpu.provider_interface.base import GPUProviderError, ProviderStatus
from workstation_core.db import get_sessionmaker
from workstation_core.enums import GPUStatus
from workstation_core.models_orm import GPUSession, User


@pytest.fixture()
def manager(app_env, db):
    db.add(User(username="sam", password_hash="x"))
    db.commit()
    return GPULifecycleManager(app_env, get_sessionmaker())


async def test_no_prior_session_row_is_a_silent_noop(manager, db):
    # Nothing to reconcile — a completely fresh database.
    await manager.reconcile_on_startup()
    session = await manager.get_status(db)
    assert session.status == GPUStatus.OFF.value


async def test_ready_session_with_no_instance_id_becomes_off(manager, db):
    session = GPUSession(provider="mock", status=GPUStatus.READY.value, instance_id=None)
    db.add(session)
    db.commit()

    await manager.reconcile_on_startup()

    db.commit()
    session = await manager.get_status(db)
    assert session.status == GPUStatus.OFF.value


async def test_unverifiable_instance_becomes_error_not_off(manager, db, monkeypatch):
    """The critical safety property: if we can't independently confirm the
    provider's real state, we must never silently claim OFF — that could
    hide a real, still-billing instance."""
    session = GPUSession(provider="mock", status=GPUStatus.READY.value, instance_id="some-instance")
    db.add(session)
    db.commit()

    provider = manager._get_provider()

    async def _boom():
        raise GPUProviderError("simulated: could not reach provider API")

    monkeypatch.setattr(provider, "status", _boom)

    await manager.reconcile_on_startup()

    db.commit()
    session = await manager.get_status(db)
    assert session.status == GPUStatus.ERROR.value
    assert "could not reconcile" in session.session_metadata["last_error"]


async def test_verified_still_running_instance_is_marked_ready(manager, db, monkeypatch):
    session = GPUSession(provider="mock", status=GPUStatus.READY.value, instance_id="some-instance")
    db.add(session)
    db.commit()

    provider = manager._get_provider()

    async def _still_ready():
        return ProviderStatus(running=True, ready=True, instance_id="some-instance", endpoint="http://x:1")

    monkeypatch.setattr(provider, "status", _still_ready)

    await manager.reconcile_on_startup()

    db.commit()
    session = await manager.get_status(db)
    assert session.status == GPUStatus.READY.value


async def test_reconciliation_never_touches_an_already_off_session(manager, db):
    session = GPUSession(provider="mock", status=GPUStatus.OFF.value)
    db.add(session)
    db.commit()

    await manager.reconcile_on_startup()

    db.commit()
    # Still exactly one OFF session — reconciliation returned early, no
    # new row or spurious transition.
    assert db.query(GPUSession).count() == 1
    assert db.query(GPUSession).first().status == GPUStatus.OFF.value
