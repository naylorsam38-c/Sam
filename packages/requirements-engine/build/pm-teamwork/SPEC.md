# pm-teamwork — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify engine bindings against the locked structure; it must never be used to build a real app.

## Screens

| id | kind | engines | note |
|---|---|---|---|
| pm-teamwork/SCR-001 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/SCR-002 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/SCR-003 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/SCR-004 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/SCR-005 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/SCR-006 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/SCR-007 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| pm-teamwork/SCR-008 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |

## Actions

| id | kind | engines | note |
|---|---|---|---|
| pm-teamwork/ACT-001 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-002 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-003 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-004 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-005 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-006 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-007 | custom | record_cloning |  |
| pm-teamwork/ACT-008 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-009 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-010 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| pm-teamwork/ACT-011 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| pm-teamwork/ACT-012 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| pm-teamwork/ACT-013 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| pm-teamwork/ACT-014 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |

## Notifications

| name | engines | note |
|---|---|---|
| Task assigned | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |
| Task due reminder | scheduled_jobs | covers the real timing half (wait until due, then fire); actual message delivery over email/sms/push has no engine -- see catalogue |
| New comment | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |

## Reports

| name | engines | note |
|---|---|---|
| Open tasks by person | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| Overdue tasks | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |

## Recurring ops

| id | engines | note |
|---|---|---|
| pm-teamwork/OPS-001 | scheduled_jobs |  |
| pm-teamwork/OPS-002 | scheduled_jobs |  |
| pm-teamwork/OPS-003 | scheduled_jobs |  |
| pm-teamwork/OPS-004 | scheduled_jobs |  |
| pm-teamwork/OPS-005 | scheduled_jobs |  |
| pm-teamwork/OPS-006 | scheduled_jobs |  |
| pm-teamwork/OPS-007 | scheduled_jobs |  |
| pm-teamwork/OPS-008 | scheduled_jobs |  |
| pm-teamwork/OPS-009 | scheduled_jobs |  |
