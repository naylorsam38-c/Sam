"""Unit tests for the GPU and Task state machines (spec sections 8, 12)."""

from workstation_core.enums import (
    GPU_PROTECTED_STATES,
    GPU_TRANSITIONS,
    TASK_TERMINAL_STATES,
    TASK_TRANSITIONS,
    GPUStatus,
    TaskStatus,
)


def test_every_gpu_status_has_a_transition_entry():
    for status in GPUStatus:
        assert status in GPU_TRANSITIONS, f"{status} has no defined transitions"


def test_off_is_reachable_only_from_stopping_or_error():
    # STOPPING -> OFF is the normal path. ERROR -> OFF exists too, for
    # startup reconciliation confirming a previously-errored GPU really is
    # off now (see GPULifecycleManager.reconcile_on_startup) — every other
    # state must go through STOPPING first, never straight to OFF.
    reachable_from = {src for src, dests in GPU_TRANSITIONS.items() if GPUStatus.OFF in dests}
    assert reachable_from == {GPUStatus.STOPPING, GPUStatus.ERROR}


def test_protected_states_cannot_go_directly_to_off():
    for state in GPU_PROTECTED_STATES:
        assert GPUStatus.OFF not in GPU_TRANSITIONS[state], (
            f"{state} must go through STOPPING, never straight to OFF"
        )


def test_busy_can_only_reach_stopping_via_explicit_force():
    # BUSY -> STOPPING exists (for force-stop) but BUSY -> OFF does not —
    # nothing may skip the STOPPING step even when forced.
    assert GPUStatus.STOPPING in GPU_TRANSITIONS[GPUStatus.BUSY]
    assert GPUStatus.OFF not in GPU_TRANSITIONS[GPUStatus.BUSY]


def test_error_can_recover_to_starting_without_reprovisioning():
    assert GPUStatus.STARTING in GPU_TRANSITIONS[GPUStatus.ERROR]


def test_task_terminal_states_have_no_outgoing_transitions():
    for state in TASK_TERMINAL_STATES:
        assert TASK_TRANSITIONS[state] == set()


def test_every_task_status_has_a_transition_entry():
    for status in TaskStatus:
        assert status in TASK_TRANSITIONS


def test_failed_is_only_reached_after_retries_not_directly_from_queued():
    # A fresh task cannot jump straight to FAILED without at least
    # attempting to start (spec: retries happen before FAILED is terminal).
    assert TaskStatus.FAILED not in TASK_TRANSITIONS[TaskStatus.QUEUED]


def test_retrying_always_leads_back_to_queued_never_to_running_directly():
    assert TaskStatus.QUEUED in TASK_TRANSITIONS[TaskStatus.RETRYING]
    assert TaskStatus.RUNNING not in TASK_TRANSITIONS[TaskStatus.RETRYING]
