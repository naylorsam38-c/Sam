# pm-teamwork — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify part bindings against the locked structure; it must never be used to build a real app.


## Screens

| id | kind | parts | note |
|---|---|---|---|
| pm-teamwork/SCR-001 | list | crud_list_detail |  |
| pm-teamwork/SCR-002 | detail | crud_list_detail |  |
| pm-teamwork/SCR-003 | list | crud_list_detail |  |
| pm-teamwork/SCR-004 | detail | crud_list_detail |  |
| pm-teamwork/SCR-005 | list | crud_list_detail |  |
| pm-teamwork/SCR-006 | detail | crud_list_detail |  |
| pm-teamwork/SCR-007 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |
| pm-teamwork/SCR-008 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |

## Actions

| id | kind | parts | note |
|---|---|---|---|
| pm-teamwork/ACT-001 | create | crud_list_detail |  |
| pm-teamwork/ACT-002 | edit | crud_list_detail |  |
| pm-teamwork/ACT-003 | delete | crud_list_detail |  |
| pm-teamwork/ACT-004 | create | crud_list_detail |  |
| pm-teamwork/ACT-005 | edit | crud_list_detail |  |
| pm-teamwork/ACT-006 | delete | crud_list_detail |  |
| pm-teamwork/ACT-007 | custom | record_cloning |  |
| pm-teamwork/ACT-008 | create | crud_list_detail |  |
| pm-teamwork/ACT-009 | edit | crud_list_detail |  |
| pm-teamwork/ACT-010 | delete | crud_list_detail |  |
| pm-teamwork/ACT-011 | transition | **UNBOUND** | person-triggered -- no specialist part needed, but the Builder has no generic workflow executor |
| pm-teamwork/ACT-012 | transition | **UNBOUND** | person-triggered -- no specialist part needed, but the Builder has no generic workflow executor |
| pm-teamwork/ACT-013 | transition | **UNBOUND** | person-triggered -- no specialist part needed, but the Builder has no generic workflow executor |
| pm-teamwork/ACT-014 | transition | **UNBOUND** | person-triggered -- no specialist part needed, but the Builder has no generic workflow executor |

## Notifications

| id | kind | parts | note |
|---|---|---|---|
| Task assigned | notification | **UNBOUND** | event-triggered -- fires synchronously, no timing part needed; actual message delivery has no part |
| Task due reminder | notification | scheduled_jobs | covers the real timing half (wait until due, then fire); actual message delivery over email/sms/push has no part on the shelf |
| New comment | notification | **UNBOUND** | event-triggered -- fires synchronously, no timing part needed; actual message delivery has no part |

## Reports

| id | kind | parts | note |
|---|---|---|---|
| Open tasks by person | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |
| Overdue tasks | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |

## Recurring ops

| id | kind | parts | note |
|---|---|---|---|
| pm-teamwork/OPS-001 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-002 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-003 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-004 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-005 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-006 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-007 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-008 | ops | scheduled_jobs |  |
| pm-teamwork/OPS-009 | ops | scheduled_jobs |  |
