"""System-Triggered Transition Engine — moves a real record from one real
stage to the next when the SYSTEM's own declared event happens, not when a
person presses something. This is the other half of workflow_executor.py,
which by its own scope only ever matches `mover: "roles"` edges; every
`mover: "automatic"` edge in a locked template had no executor at all.

What it refuses, rather than guessing:
  * an event that is not the declared event of any edge leaving the row's
    current stage;
  * an edge whose mover is a person (that is workflow_executor's job, and
    firing it from here would let the system do what only a role may do);
  * a move out of a stage the row is not actually in.

Every successful move is logged through the real audit_trail engine
(reused at its real location, not reimplemented).
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_trail  # noqa: E402 -- reused for the who/when log


class NoSuchEvent(ValueError):
    """The system raised an event no declared automatic edge listens for."""


class IllegalTransition(ValueError):
    """The move exists in the workflow but not from where this row is."""


def edges_from(transitions, from_stage):
    """Every declared automatic edge leaving a real stage."""
    return [t for t in transitions
            if t.get("mover") == "automatic" and t.get("from") == from_stage]


def fire(conn, table, row_id, stage_column, transitions, event, id_column="id", at=None):
    """Applies the one declared automatic edge that listens for `event` from
    the row's real current stage. Returns (from_stage, to_stage)."""
    row = conn.execute(
        f'SELECT "{stage_column}" FROM "{table}" WHERE "{id_column}" = ?', (row_id,)).fetchone()
    if row is None:
        raise ValueError(f"{table}.{id_column} = {row_id!r} does not exist")
    current = row[0]

    person_edges = [t for t in transitions
                    if t.get("from") == current and t.get("mover") != "automatic"
                    and t.get("event") == event]
    if person_edges:
        raise IllegalTransition(
            f"{current} -> {person_edges[0]['to']} is moved by "
            f"{person_edges[0].get('roles')}, not by the system")

    candidates = [t for t in edges_from(transitions, current) if t.get("event") == event]
    if not candidates:
        declared = sorted({t.get("event") for t in edges_from(transitions, current)})
        raise NoSuchEvent(
            f"no automatic edge leaves {current!r} on {event!r}; "
            f"the declared events from there are {declared}")
    if len(candidates) > 1:
        raise IllegalTransition(
            f"{len(candidates)} automatic edges leave {current!r} on the same event {event!r} — "
            f"the workflow is ambiguous and this engine will not choose")

    to_stage = candidates[0]["to"]
    conn.execute(f'UPDATE "{table}" SET "{stage_column}" = ? WHERE "{id_column}" = ?', (to_stage, row_id))
    conn.commit()
    audit_trail.record(conn, table, row_id, "edit",
                       before={stage_column: current}, after={stage_column: to_stage}, at=at)
    return current, to_stage


def prove():
    """Real proof: a real sqlite jobs table carrying a real Job-lifecycle
    row through its own declared automatic edges, then three real refusals."""
    transitions = [
        {"from": "queued", "to": "running", "mover": "automatic", "event": "the agent picks the job up"},
        {"from": "running", "to": "done", "mover": "automatic", "event": "the agent finishes and writes a real result"},
        {"from": "running", "to": "failed", "mover": "automatic", "event": "the agent errors or stops before finishing"},
        {"from": "done", "to": "archived", "mover": "roles", "roles": ["Sam"], "event": "Sam archives it"},
    ]
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, ask TEXT, stage TEXT)")
    conn.execute("INSERT INTO jobs VALUES ('J-1', 'draft the reply', 'queued')")
    audit_trail.ensure_table(conn)

    moves = [fire(conn, "jobs", "J-1", "stage", transitions, "the agent picks the job up"),
             fire(conn, "jobs", "J-1", "stage", transitions,
                  "the agent finishes and writes a real result")]
    final = conn.execute("SELECT stage FROM jobs WHERE id = 'J-1'").fetchone()[0]

    refusals = {}
    try:
        fire(conn, "jobs", "J-1", "stage", transitions, "the agent picks the job up")
    except NoSuchEvent as err:
        refusals["event that does not leave this stage"] = str(err)
    try:
        fire(conn, "jobs", "J-1", "stage", transitions, "Sam archives it")
    except IllegalTransition as err:
        refusals["edge a person owns"] = str(err)
    try:
        fire(conn, "jobs", "J-9", "stage", transitions, "the agent picks the job up")
    except ValueError as err:
        refusals["row that does not exist"] = str(err)

    assert moves == [("queued", "running"), ("running", "done")]
    assert final == "done"
    assert len(refusals) == 3, refusals
    log = audit_trail.history_for(conn, "jobs", "J-1")
    assert [e["after"]["stage"] for e in log] == ["running", "done"]
    conn.close()
    return {"engine": "system_triggered_transition",
            "real_system": "sqlite3 (:memory:, a real database connection) + the real audit_trail engine",
            "steps": ["a real job row in stage 'queued'",
                      "fire its own declared event -> running",
                      "fire the next declared event -> done",
                      "refuse an event that leaves no edge from 'done'",
                      "refuse an edge whose mover is a person",
                      "refuse a row that does not exist",
                      "read the real audit log back"],
            "observed": {"moves": moves, "final_stage": final, "refusals": refusals,
                         "audit": [(e["before"]["stage"], e["after"]["stage"]) for e in log]}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
