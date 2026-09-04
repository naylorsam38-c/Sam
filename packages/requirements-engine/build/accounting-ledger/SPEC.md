# accounting-ledger — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 17 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify engine bindings against the locked structure; it must never be used to build a real app.

## Screens

| id | kind | engines | note |
|---|---|---|---|
| accounting-ledger/SCR-001 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-002 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-003 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-004 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-005 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-006 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-007 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-008 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-009 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-010 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/SCR-011 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| accounting-ledger/SCR-012 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |

## Actions

| id | kind | engines | note |
|---|---|---|---|
| accounting-ledger/ACT-001 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-002 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-003 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-004 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-005 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-006 | custom | document_generation, email_parsing | document rendering and message composition are real and proven; actually dispatching over SMTP was never built or proven, so this action is only partially covered |
| accounting-ledger/ACT-007 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-008 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-009 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-010 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-011 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-012 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-013 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| accounting-ledger/ACT-014 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| accounting-ledger/ACT-015 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| accounting-ledger/ACT-016 | transition | ledger_balancing |  |
| accounting-ledger/ACT-017 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| accounting-ledger/ACT-018 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| accounting-ledger/ACT-019 | approve | **UNBOUND** | no binding rule for this action kind |
| accounting-ledger/ACT-020 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| accounting-ledger/ACT-021 | transition | ledger_balancing |  |
| accounting-ledger/ACT-022 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| accounting-ledger/ACT-023 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |

## Notifications

| name | engines | note |
|---|---|---|
| Invoice sent | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |
| Payment reminder | scheduled_jobs | covers the real timing half (wait until due, then fire); actual message delivery over email/sms/push has no engine -- see catalogue |
| Payment received | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |

## Reports

| name | engines | note |
|---|---|---|
| Profit and loss | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| Aged receivables | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |

## Recurring ops

| id | engines | note |
|---|---|---|
| accounting-ledger/OPS-001 | scheduled_jobs |  |
| accounting-ledger/OPS-002 | scheduled_jobs |  |
| accounting-ledger/OPS-003 | scheduled_jobs |  |
| accounting-ledger/OPS-004 | scheduled_jobs |  |
| accounting-ledger/OPS-005 | scheduled_jobs |  |
| accounting-ledger/OPS-006 | scheduled_jobs |  |
| accounting-ledger/OPS-007 | scheduled_jobs |  |
| accounting-ledger/OPS-008 | scheduled_jobs |  |
| accounting-ledger/OPS-009 | scheduled_jobs |  |
| accounting-ledger/OPS-010 | scheduled_jobs |  |
| accounting-ledger/OPS-011 | scheduled_jobs |  |
| accounting-ledger/OPS-012 | scheduled_jobs |  |
