# accounting-ledger — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify part bindings against the locked structure; it must never be used to build a real app.


## Screens

| id | kind | parts | note |
|---|---|---|---|
| accounting-ledger/SCR-001 | list | crud_list_detail |  |
| accounting-ledger/SCR-002 | detail | crud_list_detail |  |
| accounting-ledger/SCR-003 | list | crud_list_detail |  |
| accounting-ledger/SCR-004 | detail | crud_list_detail |  |
| accounting-ledger/SCR-005 | list | crud_list_detail |  |
| accounting-ledger/SCR-006 | detail | crud_list_detail |  |
| accounting-ledger/SCR-007 | list | crud_list_detail |  |
| accounting-ledger/SCR-008 | detail | crud_list_detail |  |
| accounting-ledger/SCR-009 | list | crud_list_detail |  |
| accounting-ledger/SCR-010 | detail | crud_list_detail |  |
| accounting-ledger/SCR-011 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |
| accounting-ledger/SCR-012 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |

## Actions

| id | kind | parts | note |
|---|---|---|---|
| accounting-ledger/ACT-001 | create | crud_list_detail |  |
| accounting-ledger/ACT-002 | edit | crud_list_detail |  |
| accounting-ledger/ACT-003 | delete | crud_list_detail |  |
| accounting-ledger/ACT-004 | create | crud_list_detail |  |
| accounting-ledger/ACT-005 | edit | crud_list_detail |  |
| accounting-ledger/ACT-006 | custom | document_generation, email_parsing | document rendering and message composition are real and proven; actually dispatching over SMTP was never built or proven, so this action is only partially covered |
| accounting-ledger/ACT-007 | create | crud_list_detail |  |
| accounting-ledger/ACT-008 | edit | crud_list_detail |  |
| accounting-ledger/ACT-009 | delete | crud_list_detail |  |
| accounting-ledger/ACT-010 | create | crud_list_detail |  |
| accounting-ledger/ACT-011 | edit | crud_list_detail |  |
| accounting-ledger/ACT-012 | create | crud_list_detail |  |
| accounting-ledger/ACT-013 | edit | crud_list_detail |  |
| accounting-ledger/ACT-014 | transition | workflow_executor |  |
| accounting-ledger/ACT-015 | transition | workflow_executor |  |
| accounting-ledger/ACT-016 | transition | ledger_balancing |  |
| accounting-ledger/ACT-017 | transition | workflow_executor |  |
| accounting-ledger/ACT-018 | transition | workflow_executor |  |
| accounting-ledger/ACT-019 | approve | **UNBOUND** | no binding rule for this action kind |
| accounting-ledger/ACT-020 | transition | workflow_executor |  |
| accounting-ledger/ACT-021 | transition | ledger_balancing |  |
| accounting-ledger/ACT-022 | transition | workflow_executor |  |
| accounting-ledger/ACT-023 | transition | workflow_executor |  |

## Notifications

| id | kind | parts | note |
|---|---|---|---|
| Invoice sent | notification | notification_delivery |  |
| Payment reminder | notification | scheduled_jobs, notification_delivery |  |
| Payment received | notification | notification_delivery |  |

## Reports

| id | kind | parts | note |
|---|---|---|---|
| Profit and loss | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |
| Aged receivables | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting part was built |

## Recurring ops

| id | kind | parts | note |
|---|---|---|---|
| accounting-ledger/OPS-001 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-002 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-003 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-004 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-005 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-006 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-007 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-008 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-009 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-010 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-011 | ops | scheduled_jobs |  |
| accounting-ledger/OPS-012 | ops | scheduled_jobs |  |
