# crm-pipeline — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify engine bindings against the locked structure; it must never be used to build a real app.

## Screens

| id | kind | engines | note |
|---|---|---|---|
| crm-pipeline/SCR-001 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-002 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-003 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-004 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-005 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-006 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-007 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-008 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/SCR-009 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| crm-pipeline/SCR-010 | report | stage_history |  |

## Actions

| id | kind | engines | note |
|---|---|---|---|
| crm-pipeline/ACT-001 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-002 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-003 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-004 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-005 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-006 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-007 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-008 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-009 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-010 | custom | **UNBOUND** | a plain restricted field edit -- no specialist engine needed, but the Builder has no generic custom-action execution rule at all |
| crm-pipeline/ACT-011 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-012 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-013 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| crm-pipeline/ACT-014 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| crm-pipeline/ACT-015 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| crm-pipeline/ACT-016 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| crm-pipeline/ACT-017 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| crm-pipeline/ACT-018 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| crm-pipeline/ACT-019 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| crm-pipeline/ACT-020 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| crm-pipeline/ACT-021 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |

## Notifications

| name | engines | note |
|---|---|---|
| Activity due | scheduled_jobs | covers the real timing half (wait until due, then fire); actual message delivery over email/sms/push has no engine -- see catalogue |
| Deal won | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |

## Reports

| name | engines | note |
|---|---|---|
| Pipeline by stage | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| Win rate | stage_history |  |

## Recurring ops

| id | engines | note |
|---|---|---|
| crm-pipeline/OPS-001 | scheduled_jobs |  |
| crm-pipeline/OPS-002 | scheduled_jobs |  |
| crm-pipeline/OPS-003 | scheduled_jobs |  |
| crm-pipeline/OPS-004 | scheduled_jobs |  |
| crm-pipeline/OPS-005 | scheduled_jobs |  |
| crm-pipeline/OPS-006 | scheduled_jobs |  |
| crm-pipeline/OPS-007 | scheduled_jobs |  |
| crm-pipeline/OPS-008 | scheduled_jobs |  |
| crm-pipeline/OPS-009 | scheduled_jobs |  |
