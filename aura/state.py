"""
Deterministic session state machine.

Only legal transitions are allowed; illegal ones raise. The machine is pure and
synchronous so it is trivially unit-testable. `on_change` hooks let the session
emit a STATE event to the client whenever it moves.
"""
from __future__ import annotations

from typing import Callable

from .protocol import State

# Allowed transitions. Any state may drop to ERROR; ERROR/INTERRUPTED can RECOVER.
_ALLOWED: dict[State, set[State]] = {
    State.IDLE:            {State.LISTENING, State.THINKING, State.STARTING_SPEECH, State.ERROR},
    State.LISTENING:       {State.USER_SPEAKING, State.THINKING, State.IDLE, State.ERROR},
    State.USER_SPEAKING:   {State.THINKING, State.LISTENING, State.ERROR},
    State.THINKING:        {State.STARTING_SPEECH, State.LISTENING, State.INTERRUPTED, State.ERROR},
    State.STARTING_SPEECH: {State.SPEAKING, State.INTERRUPTED, State.ERROR},
    State.SPEAKING:        {State.SPEAKING, State.INTERRUPTED, State.LISTENING, State.IDLE, State.ERROR},
    State.INTERRUPTED:     {State.RECOVERING, State.LISTENING, State.ERROR},
    State.RECOVERING:      {State.LISTENING, State.IDLE, State.ERROR},
    State.ERROR:           {State.RECOVERING, State.IDLE},
}


class IllegalTransition(Exception):
    pass


class StateMachine:
    def __init__(self, on_change: Callable[[State, State], None] | None = None):
        self._state = State.IDLE
        self._on_change = on_change

    @property
    def state(self) -> State:
        return self._state

    def can(self, to: State) -> bool:
        return to in _ALLOWED.get(self._state, set())

    def to(self, to: State) -> State:
        if to == self._state and to != State.SPEAKING:
            return self._state
        if not self.can(to):
            raise IllegalTransition(f"{self._state.value} -> {to.value}")
        prev, self._state = self._state, to
        if self._on_change:
            self._on_change(prev, to)
        return self._state

    def force_error(self) -> State:
        prev, self._state = self._state, State.ERROR
        if self._on_change and prev != State.ERROR:
            self._on_change(prev, State.ERROR)
        return self._state
