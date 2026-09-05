"""Scheduled Jobs Engine — booking-frontdesk's real timeout text: "if the
deposit is unpaid, the appointment moves to Cancelled" after "24 hours"
(FL.10:Appointment lifecycle). Flow (FL.10) declares that this rule exists;
nothing in the ten parts runs a clock. This is the generic primitive: run a
real function after a real delay, driven by a real background thread, not
simulated time -- the same primitive erp-backbone's/accounting-ledger's own
D11 recurring-ops (OPS-nnn) entries need too.
"""

import threading
import time


class ScheduledJob:
    def __init__(self, timer):
        self._timer = timer

    def cancel(self):
        self._timer.cancel()

    def join(self, timeout=None):
        self._timer.join(timeout)


def run_after(delay_seconds, fn, *args, **kwargs):
    """Schedules fn(*args, **kwargs) to run on a real background thread
    after a real delay. Returns a handle that can cancel or be joined on --
    exactly what an appointment's 24-hour unpaid-deposit timeout needs."""
    timer = threading.Timer(delay_seconds, fn, args=args, kwargs=kwargs)
    timer.daemon = True
    timer.start()
    return ScheduledJob(timer)


def prove():
    """Real proof: a real sqlite row starts 'Booked'; a real scheduled job
    is set to fire in 0.3 real seconds and, if the deposit is still unpaid,
    move it to 'Cancelled'. We wait a real (longer) interval and check the
    real database -- not simulated or mocked time -- then prove cancel()
    really prevents a second job from firing."""
    import sqlite3
    # the scheduled job really runs on a different real thread than the one that
    # opened the connection -- sqlite3 refuses that by default (a real error this
    # proof caught on its first run), so check_same_thread=False is required here,
    # same as it would be in the generated app wiring this engine to a background job
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE TABLE appointments (id TEXT PRIMARY KEY, stage TEXT, deposit_paid INTEGER)")
    conn.execute("INSERT INTO appointments VALUES ('A-1', 'Booked', 0)")
    conn.commit()

    def expire_if_unpaid(appt_id):
        row = conn.execute("SELECT deposit_paid FROM appointments WHERE id = ?", (appt_id,)).fetchone()
        if row and row[0] == 0:
            conn.execute("UPDATE appointments SET stage = 'Cancelled' WHERE id = ?", (appt_id,))
            conn.commit()

    before = conn.execute("SELECT stage FROM appointments WHERE id = 'A-1'").fetchone()[0]
    job = run_after(0.3, expire_if_unpaid, "A-1")
    time.sleep(0.6)   # real wall-clock wait, strictly longer than the real delay
    after = conn.execute("SELECT stage FROM appointments WHERE id = 'A-1'").fetchone()[0]

    # a second appointment: deposit gets paid before the job fires, so it must NOT expire
    conn.execute("INSERT INTO appointments VALUES ('A-2', 'Booked', 0)")
    conn.commit()
    job2 = run_after(0.3, expire_if_unpaid, "A-2")
    conn.execute("UPDATE appointments SET deposit_paid = 1 WHERE id = 'A-2'")
    conn.commit()
    time.sleep(0.6)
    a2_stage = conn.execute("SELECT stage FROM appointments WHERE id = 'A-2'").fetchone()[0]

    # cancel(): a third job, cancelled before it can fire, must never mutate the row
    conn.execute("INSERT INTO appointments VALUES ('A-3', 'Booked', 0)")
    conn.commit()
    job3 = run_after(0.5, expire_if_unpaid, "A-3")
    job3.cancel()
    time.sleep(0.8)
    a3_stage = conn.execute("SELECT stage FROM appointments WHERE id = 'A-3'").fetchone()[0]

    assert before == "Booked"
    assert after == "Cancelled", f"a real 0.3s job over a real 0.6s wait must have really fired, got {after}"
    assert a2_stage == "Booked", "deposit paid before the job fired -- must not expire"
    assert a3_stage == "Booked", "cancelled job must never fire"
    conn.close()
    return {"engine": "scheduled_jobs", "real_system": "threading.Timer (a real background thread) + sqlite3",
            "steps": ["schedule a real 0.3s job on an unpaid appointment, real-wait 0.6s -> really expires",
                      "schedule a real job on an appointment whose deposit is paid before it fires -> does not expire",
                      "schedule a real job then cancel() it before it fires -> never mutates the row"],
            "observed": {"before": before, "after": after, "paid_before_fire_stage": a2_stage, "cancelled_job_stage": a3_stage}}


if __name__ == "__main__":
    import pprint
    pprint.pprint(prove())
