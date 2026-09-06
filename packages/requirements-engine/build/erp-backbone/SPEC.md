# erp-backbone — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify part bindings against the locked structure; it must never be used to build a real app.


## Screens

| id | kind | parts | note |
|---|---|---|---|
| erp-backbone/SCR-001 | list | crud_list_detail |  |
| erp-backbone/SCR-002 | detail | crud_list_detail |  |
| erp-backbone/SCR-003 | list | crud_list_detail |  |
| erp-backbone/SCR-004 | detail | crud_list_detail |  |
| erp-backbone/SCR-005 | list | crud_list_detail |  |
| erp-backbone/SCR-006 | detail | crud_list_detail |  |
| erp-backbone/SCR-007 | list | crud_list_detail |  |
| erp-backbone/SCR-008 | detail | crud_list_detail |  |
| erp-backbone/SCR-009 | list | crud_list_detail |  |
| erp-backbone/SCR-010 | detail | crud_list_detail |  |
| erp-backbone/SCR-011 | list | crud_list_detail |  |
| erp-backbone/SCR-012 | detail | crud_list_detail |  |
| erp-backbone/SCR-013 | list | crud_list_detail |  |
| erp-backbone/SCR-014 | detail | crud_list_detail |  |
| erp-backbone/SCR-015 | list | crud_list_detail |  |
| erp-backbone/SCR-016 | detail | crud_list_detail |  |
| erp-backbone/SCR-017 | report | stock_ledger |  |
| erp-backbone/SCR-018 | report | stage_history |  |
| erp-backbone/SCR-019 | report | reporting_engine |  |

## Actions

| id | kind | parts | note |
|---|---|---|---|
| erp-backbone/ACT-001 | create | crud_list_detail |  |
| erp-backbone/ACT-002 | edit | crud_list_detail |  |
| erp-backbone/ACT-003 | delete | crud_list_detail |  |
| erp-backbone/ACT-004 | create | crud_list_detail |  |
| erp-backbone/ACT-005 | edit | crud_list_detail |  |
| erp-backbone/ACT-006 | delete | crud_list_detail |  |
| erp-backbone/ACT-007 | create | crud_list_detail |  |
| erp-backbone/ACT-008 | edit | crud_list_detail |  |
| erp-backbone/ACT-009 | delete | crud_list_detail |  |
| erp-backbone/ACT-010 | create | crud_list_detail |  |
| erp-backbone/ACT-011 | edit | crud_list_detail |  |
| erp-backbone/ACT-012 | delete | crud_list_detail |  |
| erp-backbone/ACT-013 | create | crud_list_detail |  |
| erp-backbone/ACT-014 | edit | crud_list_detail |  |
| erp-backbone/ACT-015 | delete | crud_list_detail |  |
| erp-backbone/ACT-016 | create | crud_list_detail |  |
| erp-backbone/ACT-017 | edit | crud_list_detail |  |
| erp-backbone/ACT-018 | delete | crud_list_detail |  |
| erp-backbone/ACT-019 | create | crud_list_detail |  |
| erp-backbone/ACT-020 | edit | crud_list_detail |  |
| erp-backbone/ACT-021 | delete | crud_list_detail |  |
| erp-backbone/ACT-022 | create | crud_list_detail |  |
| erp-backbone/ACT-023 | edit | crud_list_detail |  |
| erp-backbone/ACT-024 | delete | crud_list_detail |  |
| erp-backbone/ACT-025 | transition | workflow_executor |  |
| erp-backbone/ACT-026 | transition | workflow_executor |  |
| erp-backbone/ACT-027 | transition | workflow_executor |  |
| erp-backbone/ACT-028 | approve | stage_approval_gate |  |
| erp-backbone/ACT-029 | transition | workflow_executor |  |
| erp-backbone/ACT-030 | transition | workflow_executor |  |
| erp-backbone/ACT-031 | transition | workflow_executor |  |

## Notifications

| id | kind | parts | note |
|---|---|---|---|
| Low stock alert | notification | notification_delivery |  |
| Order shipped | notification | notification_delivery |  |

## Reports

| id | kind | parts | note |
|---|---|---|---|
| Stock on hand | report | stock_ledger |  |
| Sales by month | report | stage_history |  |
| Open orders | report | reporting_engine |  |

## Recurring ops

| id | kind | parts | note |
|---|---|---|---|
| erp-backbone/OPS-001 | ops | scheduled_jobs |  |
| erp-backbone/OPS-002 | ops | scheduled_jobs |  |
| erp-backbone/OPS-003 | ops | scheduled_jobs |  |
| erp-backbone/OPS-004 | ops | scheduled_jobs |  |
| erp-backbone/OPS-005 | ops | scheduled_jobs |  |
| erp-backbone/OPS-006 | ops | scheduled_jobs |  |
| erp-backbone/OPS-007 | ops | scheduled_jobs |  |
| erp-backbone/OPS-008 | ops | scheduled_jobs |  |
| erp-backbone/OPS-009 | ops | scheduled_jobs |  |
| erp-backbone/OPS-010 | ops | scheduled_jobs |  |
| erp-backbone/OPS-011 | ops | scheduled_jobs |  |
| erp-backbone/OPS-012 | ops | scheduled_jobs |  |
| erp-backbone/OPS-013 | ops | scheduled_jobs |  |
| erp-backbone/OPS-014 | ops | scheduled_jobs |  |
| erp-backbone/OPS-015 | ops | scheduled_jobs |  |

## Interface

| id | kind | parts | note |
|---|---|---|---|
| erp-backbone/IFC-001 | interface | **UNBOUND** | no interface chosen yet -- the front door has not run for this instance |
