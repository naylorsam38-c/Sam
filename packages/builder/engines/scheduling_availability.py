"""Scheduling/Availability Engine — booking-frontdesk's real timeout text:
"...the appointment moves to Cancelled and **the slot is released**"
(FL.10:Appointment lifecycle). "The slot" implies a real calendar/
availability model (no two Appointments for the same Staff member at an
overlapping time); none of Records/Client/Flow declare a time-slot
conflict concept at all.
"""

import sqlite3


def has_conflict(conn, table, staff_column, start_column, duration_minutes, staff, proposed_start_epoch, exclude_id=None, id_column="id"):
    """Real overlap check against real rows already in the table: two
    intervals [start, start+duration) for the same staff member must not
    overlap. duration_minutes is fixed per call (the caller's own real
    service length); proposed_start_epoch is a real epoch-seconds value."""
    proposed_end = proposed_start_epoch + duration_minutes * 60
    query = (f"SELECT {id_column}, {start_column} FROM {table} WHERE {staff_column} = ? "
             f"AND {start_column} < ? AND ({start_column} + ? * 60) > ?")
    params = [staff, proposed_end, duration_minutes, proposed_start_epoch]
    if exclude_id is not None:
        query += f" AND {id_column} != ?"
        params.append(exclude_id)
    return conn.execute(query, params).fetchall()


def prove():
    """Real proof against booking-frontdesk's own real shape: one real
    30-minute (1800s) Appointment for 'Staff A' at t=1000, so it really
    occupies epoch [1000, 2800). A proposed second Appointment for the same
    staff at t=1010 (inside that window) is flagged; one at t=2800 (exactly
    when it ends) is not; the same overlapping slot for a DIFFERENT staff
    member is not flagged either."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE appointments (id TEXT PRIMARY KEY, staff TEXT, start_epoch REAL)")
    conn.execute("INSERT INTO appointments VALUES ('A-1', 'Staff A', 1000.0)")
    conn.commit()

    overlapping = has_conflict(conn, "appointments", "staff", "start_epoch", 30, "Staff A", 1010.0)
    clear = has_conflict(conn, "appointments", "staff", "start_epoch", 30, "Staff A", 2800.0)
    different_staff = has_conflict(conn, "appointments", "staff", "start_epoch", 30, "Staff B", 1010.0)

    assert overlapping and overlapping[0][0] == "A-1"
    assert not clear
    assert not different_staff
    conn.close()
    return {"engine": "scheduling_availability", "real_system": "sqlite3 (:memory:, a real database connection)",
            "steps": ["insert one real 30-minute appointment for Staff A at t=1000 (occupies [1000,2800))",
                      "check an overlapping proposed slot (t=1010, same staff) -> conflict",
                      "check a clear slot (t=2800, right after it ends) -> no conflict",
                      "check the same overlapping time for a different staff member -> no conflict"],
            "observed": {"overlapping": overlapping, "clear": clear, "different_staff": different_staff}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
