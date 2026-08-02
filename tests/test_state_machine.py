"""Tests for aura.state.StateMachine."""
from __future__ import annotations

import pytest

from aura.protocol import State
from aura.state import IllegalTransition, StateMachine


def test_starts_idle():
    sm = StateMachine()
    assert sm.state is State.IDLE


def test_legal_path_to_speaking():
    sm = StateMachine()
    assert sm.to(State.THINKING) is State.THINKING
    assert sm.to(State.STARTING_SPEECH) is State.STARTING_SPEECH
    assert sm.to(State.SPEAKING) is State.SPEAKING
    assert sm.state is State.SPEAKING


def test_can_reflects_allowed():
    sm = StateMachine()
    assert sm.can(State.LISTENING) is True
    assert sm.can(State.USER_SPEAKING) is False


def test_illegal_transition_raises():
    sm = StateMachine()
    # IDLE -> USER_SPEAKING is not allowed
    with pytest.raises(IllegalTransition):
        sm.to(State.USER_SPEAKING)
    # state unchanged after a failed transition
    assert sm.state is State.IDLE


def test_no_op_same_state_non_speaking():
    sm = StateMachine()
    sm.to(State.LISTENING)
    fired = []
    sm._on_change = lambda p, c: fired.append((p, c))
    # LISTENING -> LISTENING is a no-op and must not fire on_change
    assert sm.to(State.LISTENING) is State.LISTENING
    assert fired == []


def test_speaking_to_speaking_allowed_and_fires():
    fired = []
    sm = StateMachine(on_change=lambda p, c: fired.append((p, c)))
    sm.to(State.THINKING)
    sm.to(State.STARTING_SPEECH)
    sm.to(State.SPEAKING)
    fired.clear()
    # SPEAKING -> SPEAKING is explicitly allowed (unlike other self-transitions)
    assert sm.to(State.SPEAKING) is State.SPEAKING
    assert fired == [(State.SPEAKING, State.SPEAKING)]


def test_on_change_receives_prev_and_cur():
    fired = []
    sm = StateMachine(on_change=lambda p, c: fired.append((p, c)))
    sm.to(State.LISTENING)
    sm.to(State.USER_SPEAKING)
    assert fired == [
        (State.IDLE, State.LISTENING),
        (State.LISTENING, State.USER_SPEAKING),
    ]


@pytest.mark.parametrize("path", [
    [],                                   # from IDLE
    [State.LISTENING],                    # from LISTENING
    [State.THINKING, State.STARTING_SPEECH, State.SPEAKING],  # from SPEAKING
    [State.THINKING, State.INTERRUPTED],  # from INTERRUPTED
])
def test_force_error_from_any_state(path):
    fired = []
    sm = StateMachine(on_change=lambda p, c: fired.append((p, c)))
    for st in path:
        sm.to(st)
    fired.clear()
    prev = sm.state
    assert sm.force_error() is State.ERROR
    assert sm.state is State.ERROR
    # on_change fires with (prev, ERROR) unless we were already in ERROR
    assert fired == [(prev, State.ERROR)]


def test_force_error_from_error_does_not_refire():
    fired = []
    sm = StateMachine(on_change=lambda p, c: fired.append((p, c)))
    sm.force_error()
    fired.clear()
    sm.force_error()
    assert fired == []
    assert sm.state is State.ERROR


def test_error_can_recover():
    sm = StateMachine()
    sm.force_error()
    assert sm.to(State.RECOVERING) is State.RECOVERING
    assert sm.to(State.LISTENING) is State.LISTENING
