# command-desk — bound spec (verification artifact, not customer-complete)

`customer_complete: false` -- 0 real customer questions are still open (). This spec exists only to verify part bindings against the locked structure; it must never be used to build a real app.


## Screens

| id | kind | parts | note |
|---|---|---|---|
| command-desk/SCR-001 | list | crud_list_detail |  |
| command-desk/SCR-002 | detail | crud_list_detail |  |
| command-desk/SCR-003 | list | crud_list_detail |  |
| command-desk/SCR-004 | detail | crud_list_detail |  |
| command-desk/SCR-005 | list | crud_list_detail |  |
| command-desk/SCR-006 | detail | crud_list_detail |  |
| command-desk/SCR-007 | list | crud_list_detail |  |
| command-desk/SCR-008 | detail | crud_list_detail |  |
| command-desk/SCR-009 | list | crud_list_detail |  |
| command-desk/SCR-010 | detail | crud_list_detail |  |
| command-desk/SCR-011 | list | crud_list_detail |  |
| command-desk/SCR-012 | detail | crud_list_detail |  |
| command-desk/SCR-013 | list | crud_list_detail |  |
| command-desk/SCR-014 | detail | crud_list_detail |  |
| command-desk/SCR-015 | form | form_render_submit |  |
| command-desk/SCR-016 | form | form_render_submit |  |
| command-desk/SCR-017 | form | form_render_submit |  |
| command-desk/SCR-018 | report | reporting_engine |  |
| command-desk/SCR-019 | report | reporting_engine |  |
| command-desk/SCR-020 | integration_status | oauth_connect |  |
| command-desk/SCR-021 | integration_status | oauth_connect |  |
| command-desk/SCR-022 | integration_status | api_key_connect |  |
| command-desk/SCR-023 | integration_status | api_key_connect |  |

## Actions

| id | kind | parts | note |
|---|---|---|---|
| command-desk/ACT-001 | create | crud_list_detail |  |
| command-desk/ACT-002 | edit | crud_list_detail |  |
| command-desk/ACT-003 | delete | crud_list_detail |  |
| command-desk/ACT-004 | custom | custom_action_execution |  |
| command-desk/ACT-005 | create | crud_list_detail |  |
| command-desk/ACT-006 | edit | crud_list_detail |  |
| command-desk/ACT-007 | delete | crud_list_detail |  |
| command-desk/ACT-008 | create | crud_list_detail |  |
| command-desk/ACT-009 | edit | crud_list_detail |  |
| command-desk/ACT-010 | delete | crud_list_detail |  |
| command-desk/ACT-011 | custom | custom_action_execution |  |
| command-desk/ACT-012 | create | crud_list_detail |  |
| command-desk/ACT-013 | edit | crud_list_detail |  |
| command-desk/ACT-014 | delete | crud_list_detail |  |
| command-desk/ACT-015 | create | crud_list_detail |  |
| command-desk/ACT-016 | edit | crud_list_detail |  |
| command-desk/ACT-017 | delete | crud_list_detail |  |
| command-desk/ACT-018 | create | crud_list_detail |  |
| command-desk/ACT-019 | edit | crud_list_detail |  |
| command-desk/ACT-020 | delete | crud_list_detail |  |
| command-desk/ACT-021 | create | crud_list_detail |  |
| command-desk/ACT-022 | edit | crud_list_detail |  |
| command-desk/ACT-023 | delete | crud_list_detail |  |
| command-desk/ACT-024 | custom | preserved_original_document_store | the part serves the stored original by its recorded path and re-checks its hash; the screen that opens it is a plain detail screen |
| command-desk/ACT-025 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-026 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-027 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-028 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-029 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-030 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-031 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-032 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-033 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-034 | approve | stage_approval_gate |  |
| command-desk/ACT-035 | transition | workflow_executor |  |
| command-desk/ACT-036 | transition | workflow_executor |  |
| command-desk/ACT-037 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-038 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-039 | transition | system_triggered_transition | the move itself is real and refuses anything not declared; whatever the declared event implies beyond moving the record needs its own part, and gets one where it exists |
| command-desk/ACT-040 | transition | workflow_executor |  |
| command-desk/ACT-041 | transition | workflow_executor |  |
| command-desk/ACT-042 | transition | document_field_detection, value_provenance | detection and provenance are real; a field whose value is MISSING stops here rather than moving on, which is the part's own behaviour |
| command-desk/ACT-043 | transition | trust_gate_approval |  |
| command-desk/ACT-044 | transition | preserved_original_document_store |  |
| command-desk/ACT-045 | submit | form_render_submit |  |
| command-desk/ACT-046 | submit | form_render_submit |  |
| command-desk/ACT-047 | submit | form_render_submit |  |

## Notifications

| id | kind | parts | note |
|---|---|---|---|
| Agent stopped | notification | notification_delivery |  |
| Job failed | notification | notification_delivery |  |
| Job done | notification | notification_delivery |  |
| Approval needed | notification | notification_delivery |  |

## Reports

| id | kind | parts | note |
|---|---|---|---|
| Activity per agent | report | reporting_engine |  |
| Cost | report | reporting_engine |  |

## Recurring ops

| id | kind | parts | note |
|---|---|---|---|
| command-desk/OPS-001 | ops | scheduled_jobs |  |
| command-desk/OPS-002 | ops | scheduled_jobs |  |
| command-desk/OPS-003 | ops | scheduled_jobs |  |
| command-desk/OPS-004 | ops | scheduled_jobs |  |
| command-desk/OPS-005 | ops | scheduled_jobs |  |
| command-desk/OPS-006 | ops | scheduled_jobs |  |
| command-desk/OPS-007 | ops | scheduled_jobs |  |
| command-desk/OPS-008 | ops | scheduled_jobs |  |
| command-desk/OPS-009 | ops | scheduled_jobs |  |
| command-desk/OPS-010 | ops | scheduled_jobs |  |
| command-desk/OPS-011 | ops | scheduled_jobs |  |
| command-desk/OPS-012 | ops | scheduled_jobs |  |
| command-desk/OPS-013 | ops | scheduled_jobs |  |
| command-desk/OPS-014 | ops | scheduled_jobs |  |
| command-desk/OPS-015 | ops | scheduled_jobs |  |
| command-desk/OPS-016 | ops | scheduled_jobs |  |
| command-desk/OPS-017 | ops | scheduled_jobs |  |
| command-desk/OPS-018 | ops | scheduled_jobs |  |
| command-desk/OPS-019 | ops | scheduled_jobs |  |
| command-desk/OPS-020 | ops | scheduled_jobs |  |
| command-desk/OPS-021 | ops | scheduled_jobs |  |
| command-desk/OPS-022 | ops | scheduled_jobs |  |
| command-desk/OPS-023 | ops | scheduled_jobs |  |
