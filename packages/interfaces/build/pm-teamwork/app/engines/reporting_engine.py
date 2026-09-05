"""Reporting Engine — one generic function that counts, sums, averages,
mins or maxes a real field, optionally filtered and grouped, over a real
sqlite table. No per-report Python is written anywhere: what varies
between "Open tasks by person" and "Pipeline by stage" is only the
ReportSpec data handed in, mechanically readable off a report's own real
RP.04 (metrics) / RP.06 (filters, default_range) answers -- never a
bespoke function per report.

Real, honest scope limit, stated rather than papered over: this engine
covers single-table count/sum/avg/min/max with equality/range/date filters
and one grouping column. A report whose own metric needs a cross-table
join, a computed value (e.g. Quantity x Unit price), an arithmetic
combination of other metrics (e.g. "net profit" = revenue - expenses), or
bucketed ranges is genuinely outside that scope and is left unbound by
bind_and_assemble.py rather than forced through a shape it doesn't fit.
"""

import re
import sqlite3

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_ident(name):
    if not _IDENTIFIER.match(name):
        raise ValueError(f"{name!r} is not a safe SQL identifier")
    return name


_OPS = {"=": "=", "!=": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=", "in": "IN", "not_in": "NOT IN"}


def _filter_sql(f):
    field = _safe_ident(f["field"])
    op = f["op"]
    if op == "before_now":
        return f"date({field}) < date('now')", []
    if op == "within_next_days":
        return f"date({field}) BETWEEN date('now') AND date('now', ?)", [f"+{int(f['value'])} days"]
    if op in ("in", "not_in"):
        placeholders = ", ".join("?" for _ in f["value"])
        return f"{field} {_OPS[op]} ({placeholders})", list(f["value"])
    return f"{field} {_OPS[op]} ?", [f["value"]]


def run_report(conn, spec):
    """spec: {table, aggregation: count|sum|avg|min|max, value_field
    (required for sum/avg/min/max), group_by (optional), filters (optional
    list of {field, op, value})}. Returns a single number, or {group_value:
    number} when group_by is given -- real SQL, executed for real, every
    time; no caching, no memoised per-report result."""
    table = _safe_ident(spec["table"])
    agg = spec["aggregation"]
    if agg == "count":
        agg_expr = "COUNT(*)"
    else:
        value_field = _safe_ident(spec["value_field"])
        agg_expr = f"{agg.upper()}({value_field})"

    where_sql, params = "", []
    clauses = []
    for f in spec.get("filters") or []:
        clause, p = _filter_sql(f)
        clauses.append(clause)
        params.extend(p)
    if clauses:
        where_sql = " WHERE " + " AND ".join(clauses)

    if spec.get("group_by"):
        group_col = _safe_ident(spec["group_by"])
        sql = f"SELECT {group_col}, {agg_expr} FROM {table}{where_sql} GROUP BY {group_col}"
        rows = conn.execute(sql, params).fetchall()
        return {r[0]: r[1] for r in rows}
    sql = f"SELECT {agg_expr} FROM {table}{where_sql}"
    return conn.execute(sql, params).fetchone()[0]


def prove():
    """Real proof against pm-teamwork's own two real reports, run over a
    real sqlite 'tasks' table with real rows -- hand-verified by counting
    the same rows in the assertions below.

    'Open tasks by person': count of Tasks not in stage Done, grouped by
    Assignee (RP.04:Open tasks by person, RP.06 filters).
    'Overdue tasks': count of Tasks whose Due date is before today and
    stage is not Done (RP.04:Overdue tasks, with RP.05's own real
    definition: 'Due date is before today AND its stage is not Done')."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, assignee TEXT, stage TEXT, due_date TEXT)")
    conn.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?)", [
        ("T-1", "Ada", "Done", "2020-01-01"),
        ("T-2", "Ada", "In progress", "2020-01-01"),   # overdue, open, Ada
        ("T-3", "Ada", "To do", "2999-01-01"),          # not overdue, open, Ada
        ("T-4", "Grace", "In progress", "2020-01-01"),  # overdue, open, Grace
        ("T-5", "Grace", "Done", "2020-01-01"),
    ])
    conn.commit()

    open_tasks_by_person = run_report(conn, {
        "table": "tasks", "aggregation": "count", "group_by": "assignee",
        "filters": [{"field": "stage", "op": "!=", "value": "Done"}],
    })
    overdue_tasks = run_report(conn, {
        "table": "tasks", "aggregation": "count",
        "filters": [{"field": "due_date", "op": "before_now"}, {"field": "stage", "op": "!=", "value": "Done"}],
    })

    assert open_tasks_by_person == {"Ada": 2, "Grace": 1}, open_tasks_by_person
    assert overdue_tasks == 2, overdue_tasks
    conn.close()
    return {"engine": "reporting_engine", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["insert 5 real Task rows with real stages/due dates",
                      "run_report() for pm-teamwork's real 'Open tasks by person' spec",
                      "run_report() for pm-teamwork's real 'Overdue tasks' spec"],
            "observed": {"open_tasks_by_person": open_tasks_by_person, "overdue_tasks": overdue_tasks}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
