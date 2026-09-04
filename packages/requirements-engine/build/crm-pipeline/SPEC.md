# crm-pipeline — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify part bindings against the locked structure; it must never be used to build a real app.


## Screens

| id | kind | parts | note |
|---|---|---|---|
| crm-pipeline/SCR-001 | list | crud_list_detail |  |
| crm-pipeline/SCR-002 | detail | crud_list_detail |  |
| crm-pipeline/SCR-003 | list | crud_list_detail |  |
| crm-pipeline/SCR-004 | detail | crud_list_detail |  |
| crm-pipeline/SCR-005 | list | crud_list_detail |  |
| crm-pipeline/SCR-006 | detail | crud_list_detail |  |
| crm-pipeline/SCR-007 | list | crud_list_detail |  |
| crm-pipeline/SCR-008 | detail | crud_list_detail |  |
| crm-pipeline/SCR-009 | report | reporting_engine |  |
| crm-pipeline/SCR-010 | report | stage_history |  |

## Actions

| id | kind | parts | note |
|---|---|---|---|
| crm-pipeline/ACT-001 | create | crud_list_detail |  |
| crm-pipeline/ACT-002 | edit | crud_list_detail |  |
| crm-pipeline/ACT-003 | delete | crud_list_detail |  |
| crm-pipeline/ACT-004 | create | crud_list_detail |  |
| crm-pipeline/ACT-005 | edit | crud_list_detail |  |
| crm-pipeline/ACT-006 | delete | crud_list_detail |  |
| crm-pipeline/ACT-007 | create | crud_list_detail |  |
| crm-pipeline/ACT-008 | edit | crud_list_detail |  |
| crm-pipeline/ACT-009 | delete | crud_list_detail |  |
| crm-pipeline/ACT-010 | custom | **UNBOUND** | a plain restricted field edit -- no specialist part needed, but the Builder has no generic custom-action execution rule at all |
| crm-pipeline/ACT-011 | create | crud_list_detail |  |
| crm-pipeline/ACT-012 | edit | crud_list_detail |  |
| crm-pipeline/ACT-013 | delete | crud_list_detail |  |
| crm-pipeline/ACT-014 | transition | workflow_executor |  |
| crm-pipeline/ACT-015 | transition | workflow_executor |  |
| crm-pipeline/ACT-016 | transition | workflow_executor |  |
| crm-pipeline/ACT-017 | transition | workflow_executor |  |
| crm-pipeline/ACT-018 | transition | workflow_executor |  |
| crm-pipeline/ACT-019 | transition | workflow_executor |  |
| crm-pipeline/ACT-020 | transition | workflow_executor |  |
| crm-pipeline/ACT-021 | transition | workflow_executor |  |

## Notifications

| id | kind | parts | note |
|---|---|---|---|
| Activity due | notification | scheduled_jobs, notification_delivery |  |
| Deal won | notification | notification_delivery |  |

## Reports

| id | kind | parts | note |
|---|---|---|---|
| Pipeline by stage | report | reporting_engine |  |
| Win rate | report | stage_history |  |

## Recurring ops

| id | kind | parts | note |
|---|---|---|---|
| crm-pipeline/OPS-001 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-002 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-003 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-004 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-005 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-006 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-007 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-008 | ops | scheduled_jobs |  |
| crm-pipeline/OPS-009 | ops | scheduled_jobs |  |
