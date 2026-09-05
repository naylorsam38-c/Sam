"""Custom Action Execution Engine — runs a record's own declared extra
button (Pause, Retry, …) as a real, named operation on a real row.

Until now the Builder had no execution rule for a custom action at all, so
every `action/custom` item in every locked template was UNBOUND. This is
the generic rule. It is deliberately narrow: an action can only do one of
the operations below, declared in the action itself, and the engine refuses
anything it was not handed —

  set_fields     write declared column values onto the row
  clear_fields   blank declared columns on the row
  reset_to_stage put the row back to a named stage and clear declared columns
  set_fields_from_input
                 write declared columns with values the person supplied when
                 pressing the button (crm-pipeline's Reassign: the new Owner
                 is chosen at press time, not fixed in the declaration); a
                 declared column the press did not supply is refused

Refused, rather than guessed at: an actor whose role is not one of the
action's own declared `who`; an operation this engine has no code for; a
column that does not exist on the real table; a row that does not exist.
Every run is logged through the real audit_trail engine.

What it deliberately does NOT do: move a record along its lifecycle. That
is workflow_executor (person-moved) or system_triggered_transition
(system-moved). `reset_to_stage` is not a lifecycle move — it is an
explicit, declared button that puts a row back, and it is logged as the
custom action it is.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_trail  # noqa: E402 -- reused, not rewritten

OPERATIONS = ("set_fields", "clear_fields", "reset_to_stage", "set_fields_from_input")


class NotAllowed(PermissionError):
    """The actor's role is not one the action itself names."""


class UnknownOperation(ValueError):
    """An effect this engine has no real code for. Never approximated."""


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _check_columns(conn, table, names):
    unknown = sorted(set(names) - _columns(conn, table))
    if unknown:
        raise ValueError(f"{table} has no column(s) {unknown}")


def run(conn, action, table, row_id, actor_role, id_column="id", at=None, inputs=None):
    """action: the record's own declared entry, exactly the shape already in
    every locked template's R.15 —
    {"name", "who": [roles], "effect": {"op": ..., ...}, "result_location"}.
    Returns the real before/after of every column it touched."""
    who = action.get("who") or []
    if actor_role not in who:
        raise NotAllowed(f"{actor_role!r} may not press {action.get('name')!r}; declared: {who}")

    effect = action.get("effect")
    if not isinstance(effect, dict) or effect.get("op") not in OPERATIONS:
        raise UnknownOperation(
            f"{action.get('name')!r} declares {effect!r}; this engine performs {list(OPERATIONS)} "
            f"and will not approximate anything else")

    op = effect["op"]
    if op == "set_fields":
        changes = dict(effect["fields"])
    elif op == "set_fields_from_input":
        inputs = inputs or {}
        missing = [name for name in effect["fields"] if name not in inputs or inputs[name] in (None, "")]
        if missing:
            raise ValueError(f"{action.get('name')!r} needs a value for {missing} and none was supplied")
        changes = {name: inputs[name] for name in effect["fields"]}
    elif op == "clear_fields":
        changes = {name: None for name in effect["fields"]}
    else:  # reset_to_stage
        changes = {effect["stage_column"]: effect["stage"]}
        changes.update({name: None for name in effect.get("clear", [])})

    if not changes:
        # Found by the seam journeys on Command Desk ACT-024 ("Open source
        # document" declared as clear_fields with no fields): an empty change
        # set used to reach sqlite as `UPDATE ... SET  WHERE ...` and die with a
        # syntax error. An action that changes nothing is not something this
        # engine performs; whatever the button is really for needs its own part.
        raise UnknownOperation(
            f"{action.get('name')!r} declares {op} with no fields — it would change nothing; "
            f"this engine will not pretend to perform it")

    _check_columns(conn, table, changes)
    row = conn.execute(
        f'SELECT * FROM "{table}" WHERE "{id_column}" = ?', (row_id,)).fetchone()
    if row is None:
        raise ValueError(f"{table}.{id_column} = {row_id!r} does not exist")
    names = [d[0] for d in conn.execute(f'SELECT * FROM "{table}" LIMIT 0').description]
    before = {name: value for name, value in zip(names, row) if name in changes}

    assignments = ", ".join(f'"{name}" = ?' for name in changes)
    conn.execute(f'UPDATE "{table}" SET {assignments} WHERE "{id_column}" = ?',
                 list(changes.values()) + [row_id])
    conn.commit()
    audit_trail.record(conn, table, row_id, f"custom:{action['name']}",
                       before=before, after=changes, at=at)
    return {"action": action["name"], "by": actor_role, "before": before, "after": changes}


def prove():
    """Real proof: Command Desk's own two custom actions — Pause on a real
    Agent row and Retry on a real Job row — then three real refusals."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE agents (id TEXT PRIMARY KEY, name TEXT, on_ INTEGER, stage TEXT)")
    conn.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, ask TEXT, result TEXT, "
                 "finished_at TEXT, stage TEXT)")
    conn.execute("INSERT INTO agents VALUES ('A-1', 'research', 1, 'running')")
    conn.execute("INSERT INTO jobs VALUES ('J-1', 'draft the reply', 'no answer found', "
                 "'2026-09-04T10:00', 'failed')")
    audit_trail.ensure_table(conn)

    pause = {"name": "Pause", "who": ["Sam"], "result_location": "the agent's own screen",
             "effect": {"op": "set_fields", "fields": {"on_": 0, "stage": "stopped-and-reported"}}}
    retry = {"name": "Retry", "who": ["Sam"], "result_location": "the job's own screen",
             "effect": {"op": "reset_to_stage", "stage_column": "stage", "stage": "queued",
                        "clear": ["result", "finished_at"]}}

    paused = run(conn, pause, "agents", "A-1", "Sam")
    retried = run(conn, retry, "jobs", "J-1", "Sam")
    agent_now = conn.execute("SELECT on_, stage FROM agents WHERE id = 'A-1'").fetchone()
    job_now = conn.execute("SELECT stage, result, finished_at FROM jobs WHERE id = 'J-1'").fetchone()

    # crm-pipeline's Reassign: the value comes from the press, not the declaration
    conn.execute("CREATE TABLE deals (id TEXT PRIMARY KEY, owner TEXT)")
    conn.execute("INSERT INTO deals VALUES ('D-1', 'alice')")
    reassign = {"name": "Reassign", "who": ["Sales manager"], "result_location": "the deal page",
                "effect": {"op": "set_fields_from_input", "fields": ["owner"]}}
    reassigned = run(conn, reassign, "deals", "D-1", "Sales manager", inputs={"owner": "bob"})
    deal_now = conn.execute("SELECT owner FROM deals WHERE id = 'D-1'").fetchone()
    assert deal_now == ("bob",), deal_now

    refusals = {}
    try:
        run(conn, reassign, "deals", "D-1", "Sales manager", inputs={})
    except ValueError as err:
        refusals["an input the press did not supply"] = str(err)
    try:
        run(conn, pause, "agents", "A-1", "Nova")
    except NotAllowed as err:
        refusals["a role the action does not name"] = str(err)
    try:
        run(conn, {"name": "Teleport", "who": ["Sam"], "effect": {"op": "teleport"}},
            "agents", "A-1", "Sam")
    except UnknownOperation as err:
        refusals["an operation with no code"] = str(err)
    try:
        run(conn, {"name": "Pause", "who": ["Sam"],
                   "effect": {"op": "set_fields", "fields": {"nonexistent": 1}}},
            "agents", "A-1", "Sam")
    except ValueError as err:
        refusals["a column that does not exist"] = str(err)

    assert agent_now == (0, "stopped-and-reported")
    assert job_now == ("queued", None, None), job_now
    assert len(refusals) == 4, refusals
    log = audit_trail.history_for(conn, "jobs", "J-1")
    assert log and log[-1]["action"] == "custom:Retry"
    conn.close()
    return {"engine": "custom_action_execution",
            "real_system": "sqlite3 (:memory:, a real database connection) + the real audit_trail engine",
            "steps": ["press the real declared Pause on a real running agent row",
                      "press the real declared Retry on a real failed job row",
                      "refuse an actor the action does not name",
                      "refuse an operation this engine has no code for",
                      "refuse a column the real table does not have",
                      "read the real audit log back"],
            "observed": {"pause": paused, "retry": retried, "reassign": reassigned,
                         "agent_row_now": agent_now, "job_row_now": job_now,
                         "refusals": refusals}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
