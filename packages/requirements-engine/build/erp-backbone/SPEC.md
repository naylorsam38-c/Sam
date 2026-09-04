# erp-backbone — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify engine bindings against the locked structure; it must never be used to build a real app.

## Screens

| id | kind | engines | note |
|---|---|---|---|
| erp-backbone/SCR-001 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-002 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-003 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-004 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-005 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-006 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-007 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-008 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-009 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-010 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-011 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-012 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-013 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-014 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-015 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-016 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/SCR-017 | report | stock_ledger |  |
| erp-backbone/SCR-018 | report | stage_history |  |
| erp-backbone/SCR-019 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |

## Actions

| id | kind | engines | note |
|---|---|---|---|
| erp-backbone/ACT-001 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-002 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-003 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-004 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-005 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-006 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-007 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-008 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-009 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-010 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-011 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-012 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-013 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-014 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-015 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-016 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-017 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-018 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-019 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-020 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-021 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-022 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-023 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-024 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| erp-backbone/ACT-025 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| erp-backbone/ACT-026 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| erp-backbone/ACT-027 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| erp-backbone/ACT-028 | cancel | **UNBOUND** | no binding rule for this action kind |
| erp-backbone/ACT-029 | approve | **UNBOUND** | no binding rule for this action kind |
| erp-backbone/ACT-030 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| erp-backbone/ACT-031 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| erp-backbone/ACT-032 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| erp-backbone/ACT-033 | cancel | **UNBOUND** | no binding rule for this action kind |

## Notifications

| name | engines | note |
|---|---|---|
| Low stock alert | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |
| Order shipped | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |

## Reports

| name | engines | note |
|---|---|---|
| Stock on hand | stock_ledger |  |
| Sales by month | stage_history |  |
| Open orders | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |

## Recurring ops

| id | engines | note |
|---|---|---|
| erp-backbone/OPS-001 | scheduled_jobs |  |
| erp-backbone/OPS-002 | scheduled_jobs |  |
| erp-backbone/OPS-003 | scheduled_jobs |  |
| erp-backbone/OPS-004 | scheduled_jobs |  |
| erp-backbone/OPS-005 | scheduled_jobs |  |
| erp-backbone/OPS-006 | scheduled_jobs |  |
| erp-backbone/OPS-007 | scheduled_jobs |  |
| erp-backbone/OPS-008 | scheduled_jobs |  |
| erp-backbone/OPS-009 | scheduled_jobs |  |
| erp-backbone/OPS-010 | scheduled_jobs |  |
| erp-backbone/OPS-011 | scheduled_jobs |  |
| erp-backbone/OPS-012 | scheduled_jobs |  |
| erp-backbone/OPS-013 | scheduled_jobs |  |
| erp-backbone/OPS-014 | scheduled_jobs |  |
| erp-backbone/OPS-015 | scheduled_jobs |  |
