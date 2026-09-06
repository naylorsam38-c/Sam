"""Workflow Executor Engine — moves a real record from one real stage to the
next when a person triggers it: the move must be one of the workflow's own
declared (from, to) transitions, moved by one of that transition's own
declared roles; anything else is refused, never silently accepted or
guessed at. Every successful move is logged (who, when, before/after
stage) via the real audit_trail engine -- reused, not reimplemented.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_trail  # noqa: E402 -- reused for the "who/when" log, not rewritten


class IllegalTransition(ValueError):
    pass


def transition(conn, table, row_id, stage_column, transitions, to_stage, actor_role, id_column="id", at=None):
    """transitions: the workflow's own real declared list, exactly the
    shape already in every locked template's structure --
    [{"from": ..., "to": ..., "mover": "roles", "roles": [...]}, ...].
    Only mover=="roles" entries are ever matched here -- an "automatic"
    entry is, by definition, not triggered by a person and is out of this
    engine's real scope."""
    row = conn.execute(f"SELECT {stage_column} FROM {table} WHERE {id_column} = ?", (row_id,)).fetchone()
    if row is None:
        raise ValueError(f"{table}.{id_column} = {row_id!r} does not exist")
    current_stage = row[0]

    match = next(
        (t for t in transitions
         if t.get("mover") == "roles" and t["from"] == current_stage and t["to"] == to_stage
         and actor_role in (t.get("roles") or [])),
        None,
    )
    if match is None:
        raise IllegalTransition(
            f"no declared person-triggered transition from '{current_stage}' to '{to_stage}' for role '{actor_role}'"
        )

    conn.execute(f"UPDATE {table} SET {stage_column} = ? WHERE {id_column} = ?", (to_stage, row_id))
    audit_trail.ensure_table(conn)
    audit_trail.record(conn, table, row_id, "transition",
                        before={"stage": current_stage, "by": actor_role},
                        after={"stage": to_stage, "by": actor_role}, at=at)
    conn.commit()
    return to_stage


def prove():
    """Real proof against pm-teamwork's own real, locked Task lifecycle
    transitions (loaded from the actual template file, not invented), using
    three separate real rows so each case is unambiguous: (T-1) To do ->
    In progress as 'Member' -- a real declared transition, succeeds and is
    logged; (T-2) To do -> Done directly as 'Member' -- no declared
    transition covers that pair at all, refused; (T-3) To do -> In progress
    as 'Guest' -- the pair is declared but not for that role, refused."""
    import json
    here = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(here, "..", "..", "requirements-engine", "templates", "pm-teamwork.json")
    t = json.load(open(template_path, encoding="utf-8"))
    transitions = t["structure"]["workflows"]["Task lifecycle"]["transitions"]
    assert transitions, "fixture assumption: pm-teamwork's real Task lifecycle has real transitions"

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, stage TEXT)")
    conn.executemany("INSERT INTO tasks VALUES (?, ?)", [("T-1", "To do"), ("T-2", "To do"), ("T-3", "To do")])
    conn.commit()

    # T-1: a real, legal move (To do -> In progress, Member is a declared mover)
    new_stage = transition(conn, "tasks", "T-1", "stage", transitions, "In progress", "Member")
    logged = audit_trail.history_for(conn, "tasks", "T-1")

    # T-2: To do -> Done has NO declared transition at all (Done is only
    # reachable from In progress here) -- must be refused regardless of role.
    illegal_jump = False
    try:
        transition(conn, "tasks", "T-2", "stage", transitions, "Done", "Member")
    except IllegalTransition:
        illegal_jump = True
    t2_stage_now = conn.execute("SELECT stage FROM tasks WHERE id = 'T-2'").fetchone()[0]

    # T-3: To do -> In progress IS declared, but not for 'Guest' -- must be
    # refused because of the role, not the (from, to) pair.
    wrong_role = False
    try:
        transition(conn, "tasks", "T-3", "stage", transitions, "In progress", "Guest")
    except IllegalTransition:
        wrong_role = True
    t3_stage_now = conn.execute("SELECT stage FROM tasks WHERE id = 'T-3'").fetchone()[0]

    assert new_stage == "In progress"
    assert illegal_jump, "To do -> Done has no declared transition and must be refused"
    assert t2_stage_now == "To do", "a refused illegal-pair attempt must never mutate the real row"
    assert wrong_role, "Guest is not a declared mover for To do -> In progress and must be refused"
    assert t3_stage_now == "To do", "a refused wrong-role attempt must never mutate the real row"
    assert len(logged) == 1 and logged[0]["action"] == "transition"
    conn.close()
    return {"engine": "workflow_executor", "real_system": "sqlite3 (:memory:) + pm-teamwork's own real locked transitions",
            "steps": ["load pm-teamwork's real Task lifecycle transitions from its real locked template",
                      "move a real Task To do -> In progress as Member -- legal, logged",
                      "attempt To do -> Done directly -- refused (no declared transition)",
                      "attempt a declared move as 'Guest' -- refused (not a declared mover)",
                      "confirm the real row's stage is unaffected by both refused attempts"],
            "observed": {"new_stage": new_stage, "illegal_jump_refused": illegal_jump,
                        "t2_stage_unaffected": t2_stage_now, "wrong_role_refused": wrong_role,
                        "t3_stage_unaffected": t3_stage_now, "audit_log": logged}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
