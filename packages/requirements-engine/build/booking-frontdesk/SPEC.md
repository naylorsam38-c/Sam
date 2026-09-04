# booking-frontdesk — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 18 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify engine bindings against the locked structure; it must never be used to build a real app.

## Screens

| id | kind | engines | note |
|---|---|---|---|
| booking-frontdesk/SCR-001 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/SCR-002 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/SCR-003 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/SCR-004 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/SCR-005 | list | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/SCR-006 | detail | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/SCR-007 | form | **UNBOUND** | no binding rule for this screen kind |
| booking-frontdesk/SCR-008 | report | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| booking-frontdesk/SCR-009 | report | stage_history |  |

## Actions

| id | kind | engines | note |
|---|---|---|---|
| booking-frontdesk/ACT-001 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-002 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-003 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-004 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-005 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-006 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-007 | create | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-008 | edit | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-009 | delete | (existing Builder rule -- CRUD/OAuth, no engine needed) |  |
| booking-frontdesk/ACT-010 | transition | **UNBOUND** | half of this transition is 'the deposit payment succeeds' -- needs live payment processing, not registered; the other half needs no engine at all, but the template models both as one automatic-triggered edge |
| booking-frontdesk/ACT-011 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| booking-frontdesk/ACT-012 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| booking-frontdesk/ACT-013 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| booking-frontdesk/ACT-014 | transition | **UNBOUND** | person-triggered -- no specialist engine needed, but the Builder has no generic workflow executor |
| booking-frontdesk/ACT-015 | cancel | **UNBOUND** | no binding rule for this action kind |
| booking-frontdesk/ACT-016 | submit | **UNBOUND** | no binding rule for this action kind |

## Notifications

| name | engines | note |
|---|---|---|
| Booking confirmation | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |
| Appointment reminder | scheduled_jobs | covers the real timing half (wait until due, then fire); actual message delivery over email/sms/push has no engine -- see catalogue |
| Cancellation notice | **UNBOUND** | event-triggered -- fires synchronously, no timing engine needed; actual message delivery has no engine |

## Reports

| name | engines | note |
|---|---|---|
| Upcoming appointments | **UNBOUND** | plain aggregation over existing fields -- no generic reporting engine was built |
| No-show rate | stage_history |  |

## Recurring ops

| id | engines | note |
|---|---|---|
| booking-frontdesk/OPS-001 | scheduled_jobs |  |
| booking-frontdesk/OPS-002 | scheduled_jobs |  |
| booking-frontdesk/OPS-003 | scheduled_jobs |  |
| booking-frontdesk/OPS-004 | scheduled_jobs |  |
| booking-frontdesk/OPS-005 | scheduled_jobs |  |
| booking-frontdesk/OPS-006 | scheduled_jobs |  |
| booking-frontdesk/OPS-007 | scheduled_jobs |  |
| booking-frontdesk/OPS-008 | scheduled_jobs |  |
| booking-frontdesk/OPS-009 | scheduled_jobs |  |
| booking-frontdesk/OPS-010 | scheduled_jobs |  |
| booking-frontdesk/OPS-011 | scheduled_jobs |  |
