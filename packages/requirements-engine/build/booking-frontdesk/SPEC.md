# booking-frontdesk — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 18 real customer questions are still open (0.01, A.01, A.02, A.03, A.04, A.05...). This spec exists only to verify part bindings against the locked structure; it must never be used to build a real app.


## Screens

| id | kind | parts | note |
|---|---|---|---|
| booking-frontdesk/SCR-001 | list | crud_list_detail |  |
| booking-frontdesk/SCR-002 | detail | crud_list_detail |  |
| booking-frontdesk/SCR-003 | list | crud_list_detail |  |
| booking-frontdesk/SCR-004 | detail | crud_list_detail |  |
| booking-frontdesk/SCR-005 | list | crud_list_detail |  |
| booking-frontdesk/SCR-006 | detail | crud_list_detail |  |
| booking-frontdesk/SCR-007 | form | form_render_submit |  |
| booking-frontdesk/SCR-008 | report | reporting_engine |  |
| booking-frontdesk/SCR-009 | report | stage_history |  |

## Actions

| id | kind | parts | note |
|---|---|---|---|
| booking-frontdesk/ACT-001 | create | crud_list_detail |  |
| booking-frontdesk/ACT-002 | edit | crud_list_detail |  |
| booking-frontdesk/ACT-003 | delete | crud_list_detail |  |
| booking-frontdesk/ACT-004 | create | crud_list_detail |  |
| booking-frontdesk/ACT-005 | edit | crud_list_detail |  |
| booking-frontdesk/ACT-006 | delete | crud_list_detail |  |
| booking-frontdesk/ACT-007 | create | crud_list_detail |  |
| booking-frontdesk/ACT-008 | edit | crud_list_detail |  |
| booking-frontdesk/ACT-009 | delete | crud_list_detail |  |
| booking-frontdesk/ACT-010 | transition | workflow_executor |  |
| booking-frontdesk/ACT-011 | transition | workflow_executor |  |
| booking-frontdesk/ACT-012 | transition | workflow_executor |  |
| booking-frontdesk/ACT-013 | transition | workflow_executor |  |
| booking-frontdesk/ACT-014 | transition | workflow_executor |  |
| booking-frontdesk/ACT-015 | submit | form_render_submit |  |

## Notifications

| id | kind | parts | note |
|---|---|---|---|
| Booking confirmation | notification | notification_delivery |  |
| Appointment reminder | notification | scheduled_jobs, notification_delivery |  |
| Cancellation notice | notification | notification_delivery |  |

## Reports

| id | kind | parts | note |
|---|---|---|---|
| Upcoming appointments | report | reporting_engine |  |
| No-show rate | report | stage_history |  |

## Recurring ops

| id | kind | parts | note |
|---|---|---|---|
| booking-frontdesk/OPS-001 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-002 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-003 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-004 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-005 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-006 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-007 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-008 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-009 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-010 | ops | scheduled_jobs |  |
| booking-frontdesk/OPS-011 | ops | scheduled_jobs |  |
