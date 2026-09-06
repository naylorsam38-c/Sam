# Teamwork (pm-teamwork)

`SPEC-PM-TEAMWORK-REF` — assembled from `pm-teamwork` against graph 3.0. Every field below is numbered by the question, default, or derivation that owns it — nothing here was guessed.

## actions

| # | Field | Value | Source |
|---|---|---|---|
| Z.02 | `actions.inventory` | confirmed | question |
| D12 | `actions.inventory.items` | see build_model.D12 | derivation |

## api

| # | Field | Value | Source |
|---|---|---|---|
| sys_api_convention | `api.*` | One fixed REST convention for every endpoint, verb and envelope. | system_default |

## auth

| # | Field | Value | Source |
|---|---|---|---|
| sys_first_admin | `auth.bootstrap_admin` | The first super-role account is seeded from the deploy inputs, not created throu… | system_default |
| AU.05 | `auth.default_role` | null | question |
| AU.12 | `auth.deletion_allowed` | {"allowed": "yes", "by": "both", "data": "anonymised"} | question |
| AU.12 | `auth.deletion_by` | {"allowed": "yes", "by": "both", "data": "anonymised"} | question |
| AU.12 | `auth.deletion_data_policy` | {"allowed": "yes", "by": "both", "data": "anonymised"} | question |
| AU.03 | `auth.email_verification` | yes | question |
| sys_account_identity | `auth.identity_field` | The email address is the account identity; changing it requires re-verification. | system_default |
| AU.06 | `auth.invite_authority` | {"inviters": ["Admin", "Member"], "default_role": "Member"} | question |
| AU.06 | `auth.invite_default_role` | {"inviters": ["Admin", "Member"], "default_role": "Member"} | question |
| sys_invite_expiry | `auth.invite_expiry` | Invitations expire after 7 days and can be re-sent. | system_default |
| AU.08 | `auth.lockout_attempts` | {"attempts": 5, "duration": "15 minutes"} | question |
| AU.08 | `auth.lockout_duration` | {"attempts": 5, "duration": "15 minutes"} | question |
| AU.04 | `auth.methods` | ["password", "google"] | question |
| AU.07 | `auth.mfa_method` | {"scope": "nobody", "method": "n/a"} | question |
| sys_mfa_recovery | `auth.mfa_recovery` | One-time recovery codes issued at MFA enrolment. | system_default |
| AU.07 | `auth.mfa_scope` | {"scope": "nobody", "method": "n/a"} | question |
| AU.09 | `auth.multi_device` | yes | question |
| sys_profile_self_edit | `auth.profile_self_service` | Every user can edit their own name, email, password and notification preferences… | system_default |
| AU.02 | `auth.registration_fields` | [{"name": "Full name", "type": "short_text", "required": "yes", "unique": "no"},… | question |
| AU.01 | `auth.registration_modes` | ["invited"] | question |
| A.07 | `auth.required` | yes | question |
| AU.13 | `auth.reset_others_by` | ["super"] | question |
| sys_password_reset | `auth.self_reset_flow` | Self-service reset by emailed link, valid 1 hour. | system_default |
| AU.10 | `auth.session_length` | 30 days | question |
| sys_suspended_experience | `auth.suspended_screen` | A suspended user sees a fixed 'account suspended — contact <support contact>' sc… | system_default |
| AU.11 | `auth.suspension_allowed` | {"allowed": "yes", "by": ["super"], "auto_triggers": []} | question |
| AU.11 | `auth.suspension_auto_triggers` | {"allowed": "yes", "by": ["super"], "auto_triggers": []} | question |
| AU.11 | `auth.suspension_by` | {"allowed": "yes", "by": ["super"], "auto_triggers": []} | question |

## billing

| # | Field | Value | Source |
|---|---|---|---|
| B.10 | `billing.cancellation` | null | question |
| B.02 | `billing.charged_party` | null | question |
| B.04 | `billing.currency` | null | question |
| sys_billing_details | `billing.details_collection` | Card, billing address and tax IDs are collected by the gateway's hosted form; in… | system_default |
| sys_billing_details | `billing.invoices` | Card, billing address and tax IDs are collected by the gateway's hosted form; in… | system_default |
| B.01 | `billing.model` | null | question |
| B.08 | `billing.on_failure` | null | question |
| sys_limit_reached | `billing.on_limit_reached` | Hitting a plan limit shows an upgrade prompt, then blocks the action. | system_default |
| B.07 | `billing.payment_methods` | null | question |
| B.09 | `billing.plan_change` | null | question |
| D10 | `billing.plan_linkage` | see build_model.D10 | derivation |
| B.03 | `billing.plans` | null | question |
| sys_proration | `billing.proration_rule` | Mid-cycle plan changes are prorated by the gateway. | system_default |
| B.11 | `billing.refunds` | null | question |
| A.09 | `billing.required` | no | question |
| sys_tax_calculation | `billing.tax_calculation` | Tax computed by the payment gateway from the billing address. | system_default |
| B.05 | `billing.trial` | null | question |
| B.06 | `billing.usage_charge_timing` | null | question |
| B.06 | `billing.usage_unit` | null | question |
| sys_idempotency_webhook | `billing.webhook_handling` | Payment webhooks signature-verified and processed exactly once. | system_default |

## client

| # | Field | Value | Source |
|---|---|---|---|
| C.06 | `client.landing_screen_per_role` | {"Admin": "Projects list", "Member": "My tasks", "Guest": "Projects list"} | question |
| C.05 | `client.mobile_behaviour` | {"mode": "simplified"} | question |
| C.07 | `client.navigation` | confirmed | question |
| D13 | `client.navigation.derived` | see build_model.D13 | derivation |
| A.06 | `client.platforms` | ["web"] | question |
| A.10 | `client.public_surfaces` | [] | question |

## data

| # | Field | Value | Source |
|---|---|---|---|
| A.12 | `data.import_required` | {"required": "no"} | question |
| A.12 | `data.import_sources` | {"required": "no"} | question |

## deploy

| # | Field | Value | Source |
|---|---|---|---|
| DI.10 | `deploy.app_store_accounts` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.01 | `deploy.domain` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.02 | `deploy.email_sender` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.04 | `deploy.first_admin_email` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.06 | `deploy.gateway_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.09 | `deploy.integration_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.11 | `deploy.legal_documents` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.08 | `deploy.oauth_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.05 | `deploy.region` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.07 | `deploy.sms_credentials` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |
| DI.03 | `deploy.support_contact` | [PENDING — collected at deploy time, not at requirements time] | deploy_input |

## deviation

| # | Field | Value | Source |
|---|---|---|---|
| A.14 | `deviation.flags` | [] | question |

## engine

| # | Field | Value | Source |
|---|---|---|---|
| 0.01 | `engine.involvement` | guided | question |

## file

| # | Field | Value | Source |
|---|---|---|---|
| sys_file_type_inference | `file.*.allowed_mimes` | Allowed formats come from a fixed allow-list per file category. | system_default |
| sys_image_handling | `file.*.image_handling` | Images get thumbnails; downloads are served by signed URL. | system_default |
| sys_file_security_scanning | `file.*.malware_scanning` | Async malware scan before a file is marked active. | system_default |
| D06 | `file.*.retention` | see build_model.D06 | derivation |
| sys_file_storage | `file.*.storage_backend` | Private object storage for uploads. | system_default |
| FI.02:Attachment | `file.Attachment.cardinality` | many | question |
| FI.07:Attachment | `file.Attachment.cascade_delete` | yes | question |
| FI.04:Attachment | `file.Attachment.category` | document | question |
| FI.05:Attachment | `file.Attachment.max_size_mb` | 50 | question |
| FI.01:Attachment | `file.Attachment.parent_record` | {"purpose": "a file added to a task for context", "parent": "Task"} | question |
| FI.01:Attachment | `file.Attachment.purpose` | {"purpose": "a file added to a task for context", "parent": "Task"} | question |
| FI.03:Attachment | `file.Attachment.uploaders` | {"uploaders": ["Member"], "viewers": ["Member", "Guest"]} | question |
| FI.06:Attachment | `file.Attachment.versioning` | keep_history | question |
| FI.03:Attachment | `file.Attachment.viewers` | {"uploaders": ["Member"], "viewers": ["Member", "Guest"]} | question |

## form

| # | Field | Value | Source |
|---|---|---|---|
| D02 | `form.*.fields` | see build_model.D02 | derivation |
| sys_form_failure | `form.*.layout` | A failed submit shows inline errors and keeps what was typed; forms are single-p… | system_default |
| sys_form_failure | `form.*.on_failure` | A failed submit shows inline errors and keeps what was typed; forms are single-p… | system_default |
| sys_form_failure | `form.*.spam_protection` | A failed submit shows inline errors and keeps what was typed; forms are single-p… | system_default |

## integration

| # | Field | Value | Source |
|---|---|---|---|
| sys_retry_policy | `integration.*.retry_policy` | Failed external calls retry 3× with exponential backoff + jitter. | system_default |
| A.11 | `integration.public_api_required` | no | question |

## inventory

| # | Field | Value | Source |
|---|---|---|---|
| A.15 | `inventory.file_types` | ["Attachment"] | question |
| A.15 | `inventory.forms` | [] | question |
| A.15 | `inventory.integrations` | [] | question |
| A.15 | `inventory.notifications` | ["Task assigned", "Task due reminder", "New comment"] | question |
| A.15 | `inventory.records` | ["Project", "Task", "Comment"] | question |
| A.15 | `inventory.reports` | ["Open tasks by person", "Overdue tasks"] | question |
| A.15 | `inventory.roles` | ["Admin", "Member", "Guest"] | question |
| A.15 | `inventory.screens` | [] | question |
| A.15 | `inventory.workflows` | ["Task lifecycle"] | question |

## legal

| # | Field | Value | Source |
|---|---|---|---|
| AU.14 | `legal.terms_required` | {"required": "yes", "status": "need_drafting"} | question |
| AU.14 | `legal.terms_status` | {"required": "yes", "status": "need_drafting"} | question |

## locale

| # | Field | Value | Source |
|---|---|---|---|
| sys_locale_formatting | `locale.formatting` | Dates, numbers and currency display in the format of A.13's region; stored in UT… | system_default |
| A.13 | `locale.languages` | {"region": "Australia", "languages": ["English"]} | question |
| A.13 | `locale.primary_region` | {"region": "Australia", "languages": ["English"]} | question |
| sys_locale_formatting | `locale.timezone_handling` | Dates, numbers and currency display in the format of A.13's region; stored in UT… | system_default |

## notification

| # | Field | Value | Source |
|---|---|---|---|
| sys_notification_copywriting | `notification.*.copy_final` | Message wording drafted at build time and approved by the owner before launch; n… | system_default |
| sys_notification_retry | `notification.*.retry_policy` | 3 delivery retries then dead-letter. | system_default |
| D05 | `notification.*.timing` | see build_model.D05 | derivation |
| N.03:New comment | `notification.New comment.channels` | ["in_app"] | question |
| N.04:New comment | `notification.New comment.intent` | Someone said something on your task — read and reply if needed. | question |
| N.05:New comment | `notification.New comment.opt_out` | yes | question |
| N.02:New comment | `notification.New comment.recipients` | [{"kind": "field", "record": "Task", "field": "Assignee"}, {"kind": "owner"}] | question |
| N.01:New comment | `notification.New comment.trigger` | {"kind": "event", "event": "a comment is created on a task"} | question |
| N.03:Task assigned | `notification.Task assigned.channels` | ["email", "in_app"] | question |
| N.04:Task assigned | `notification.Task assigned.intent` | You've been given this task — open it and see what's needed. | question |
| N.05:Task assigned | `notification.Task assigned.opt_out` | yes | question |
| N.02:Task assigned | `notification.Task assigned.recipients` | [{"kind": "field", "record": "Task", "field": "Assignee"}] | question |
| N.01:Task assigned | `notification.Task assigned.trigger` | {"kind": "event", "event": "a task's Assignee field is set or changed"} | question |
| N.03:Task due reminder | `notification.Task due reminder.channels` | ["email", "in_app"] | question |
| N.04:Task due reminder | `notification.Task due reminder.intent` | This task is due tomorrow — finish it or move the date. | question |
| N.05:Task due reminder | `notification.Task due reminder.opt_out` | yes | question |
| N.02:Task due reminder | `notification.Task due reminder.recipients` | [{"kind": "field", "record": "Task", "field": "Assignee"}] | question |
| N.01:Task due reminder | `notification.Task due reminder.trigger` | {"kind": "relative_to_date", "record": "Task", "date_field": "Due date", "offset… | question |

## notify

| # | Field | Value | Source |
|---|---|---|---|
| sys_inapp_inbox | `notify.inbox` | If any notification uses in-app, the app has one notification inbox with read/un… | system_default |

## ops

| # | Field | Value | Source |
|---|---|---|---|
| Z.01 | `ops.recurring_operations` | confirmed | question |
| D11 | `ops.recurring_operations.items` | see build_model.D11 | derivation |

## product

| # | Field | Value | Source |
|---|---|---|---|
| A.03 | `product.audience` | A small team and the outside collaborators it invites into specific projects. | question |
| A.01 | `product.description` | A shared task board: projects hold tasks, tasks are assigned to people, moved th… | question |
| A.02 | `product.goals` | Plan work as projects and tasks, see who is carrying what, and chase what is ove… | question |
| A.05 | `product.name` | Teamwork | question |
| A.04 | `product.success_definition` | Nothing slips: every open task has an owner and a date, and the overdue report i… | question |

## qa

| # | Field | Value | Source |
|---|---|---|---|
| D15 | `qa.generated_tests` | see build_model.D15 | derivation |
| sys_qa_pass_conditions | `qa.pass_condition.*` | Every node's pass/fail check is generated from that node's own answers. | system_default |

## record

| # | Field | Value | Source |
|---|---|---|---|
| sys_audit_fields | `record.*.audit_fields` | created_at/updated_at/created_by/updated_by on every table. | system_default |
| sys_concurrent_edit | `record.*.concurrency` | Last save wins; a user saving over a newer version is warned and shown the newer… | system_default |
| sys_list_behaviour | `record.*.exportable` | Every record list is searchable and filterable on its visible fields, sorted new… | system_default |
| D01 | `record.*.field.*.storage_type` | see build_model.D01 | derivation |
| D14 | `record.*.field.*.storage_type_for_options` | see build_model.D14 | derivation |
| sys_field_type_defaults | `record.*.field.*.validation` | Each field type carries one standard validation rule and error message. | system_default |
| sys_database_identifiers | `record.*.id_strategy` | UUIDv4 primary keys on every table. | system_default |
| sys_list_behaviour | `record.*.list_behaviour` | Every record list is searchable and filterable on its visible fields, sorted new… | system_default |
| R.06:Comment | `record.Comment.access.create` | ["Member", "Guest"] | question |
| R.08:Comment | `record.Comment.access.delete` | [{"role": "Member", "scope": "own"}, {"role": "Admin", "scope": "all"}] | question |
| R.07:Comment | `record.Comment.access.edit` | [{"role": "Member", "scope": "own"}] | question |
| R.05:Comment | `record.Comment.access.view` | [{"role": "Member", "scope": "all"}, {"role": "Guest", "scope": "linked", "via":… | question |
| R.13:Comment | `record.Comment.archivable` | no | question |
| R.15:Comment | `record.Comment.custom_actions` | [] | question |
| R.02:Comment | `record.Comment.fields` | [{"name": "Body", "type": "long_text", "required": "yes", "unique": "no"}, {"nam… | question |
| R.10:Comment | `record.Comment.has_lifecycle` | {"has": "no"} | question |
| R.04:Comment | `record.Comment.human_id` | {"needed": "no"} | question |
| R.12:Comment | `record.Comment.on_delete` | delete_too | question |
| R.09:Comment | `record.Comment.ownership_rule` | {"basis": "creator"} | question |
| R.01:Comment | `record.Comment.purpose` | A message left on a task by a person. | question |
| R.11:Comment | `record.Comment.relations` | [{"target": "Task", "cardinality": "one_to_many", "required": "yes"}] | question |
| R.14:Comment | `record.Comment.retention` | forever | question |
| R.03:Comment | `record.Comment.title_field` | Body | question |
| R.06:Project | `record.Project.access.create` | ["Member"] | question |
| R.08:Project | `record.Project.access.delete` | [{"role": "Member", "scope": "own"}, {"role": "Admin", "scope": "all"}] | question |
| R.07:Project | `record.Project.access.edit` | [{"role": "Member", "scope": "all"}] | question |
| R.05:Project | `record.Project.access.view` | [{"role": "Member", "scope": "all"}, {"role": "Guest", "scope": "linked", "via":… | question |
| R.13:Project | `record.Project.archivable` | yes | question |
| R.15:Project | `record.Project.custom_actions` | [] | question |
| R.02:Project | `record.Project.fields` | [{"name": "Name", "type": "short_text", "required": "yes", "unique": "no"}, {"na… | question |
| R.10:Project | `record.Project.has_lifecycle` | {"has": "no"} | question |
| R.04:Project | `record.Project.human_id` | {"needed": "no"} | question |
| R.12:Project | `record.Project.on_delete` | null | question |
| R.09:Project | `record.Project.ownership_rule` | {"basis": "field", "field": "Owner"} | question |
| R.01:Project | `record.Project.purpose` | A container of related work with an owner and a set of tasks. | question |
| R.11:Project | `record.Project.relations` | [] | question |
| R.14:Project | `record.Project.retention` | forever | question |
| R.03:Project | `record.Project.title_field` | Name | question |
| R.06:Task | `record.Task.access.create` | ["Member"] | question |
| R.08:Task | `record.Task.access.delete` | [{"role": "Member", "scope": "own"}, {"role": "Admin", "scope": "all"}] | question |
| R.07:Task | `record.Task.access.edit` | [{"role": "Member", "scope": "all"}] | question |
| R.05:Task | `record.Task.access.view` | [{"role": "Member", "scope": "all"}, {"role": "Guest", "scope": "linked", "via":… | question |
| R.13:Task | `record.Task.archivable` | yes | question |
| R.15:Task | `record.Task.custom_actions` | [{"name": "Duplicate", "who": ["Member"], "effect": "creates a copy of the task … | question |
| R.02:Task | `record.Task.fields` | [{"name": "Title", "type": "short_text", "required": "yes", "unique": "no"}, {"n… | question |
| R.10:Task | `record.Task.has_lifecycle` | {"has": "yes", "stages": ["To do", "In progress", "Done"]} | question |
| R.04:Task | `record.Task.human_id` | {"needed": "no"} | question |
| R.12:Task | `record.Task.on_delete` | delete_too | question |
| R.09:Task | `record.Task.ownership_rule` | {"basis": "creator"} | question |
| R.01:Task | `record.Task.purpose` | A single unit of work inside a project, assigned to one person. | question |
| R.11:Task | `record.Task.relations` | [{"target": "Project", "cardinality": "one_to_many", "required": "yes"}] | question |
| R.14:Task | `record.Task.retention` | forever | question |
| R.03:Task | `record.Task.title_field` | Title | question |

## report

| # | Field | Value | Source |
|---|---|---|---|
| sys_report_caching | `report.*.cache_policy` | Reports regenerate on demand, cached 5 min. | system_default |
| D07 | `report.*.data_source` | see build_model.D07 | derivation |
| D07 | `report.*.metric.*.derived_definition` | see build_model.D07 | derivation |
| RP.06:Open tasks by person | `report.Open tasks by person.default_range` | {"filters": ["Project", "Assignee", "Priority"], "default_range": "all time"} | question |
| RP.07:Open tasks by person | `report.Open tasks by person.export` | {"allowed": "yes", "by": ["Member"]} | question |
| RP.06:Open tasks by person | `report.Open tasks by person.filters` | {"filters": ["Project", "Assignee", "Priority"], "default_range": "all time"} | question |
| RP.03:Open tasks by person | `report.Open tasks by person.form` | {"delivery": "screen", "shape": "both"} | question |
| RP.04:Open tasks by person | `report.Open tasks by person.metrics` | ["count of Tasks not in stage Done, grouped by Assignee"] | question |
| RP.01:Open tasks by person | `report.Open tasks by person.question` | Who is carrying how much open work right now? | question |
| RP.08:Open tasks by person | `report.Open tasks by person.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Open tasks by person | `report.Open tasks by person.viewers` | ["Member"] | question |
| RP.06:Overdue tasks | `report.Overdue tasks.default_range` | {"filters": ["Project", "Assignee"], "default_range": "all time"} | question |
| RP.07:Overdue tasks | `report.Overdue tasks.export` | {"allowed": "yes", "by": ["Member"]} | question |
| RP.06:Overdue tasks | `report.Overdue tasks.filters` | {"filters": ["Project", "Assignee"], "default_range": "all time"} | question |
| RP.03:Overdue tasks | `report.Overdue tasks.form` | {"delivery": "screen", "shape": "table"} | question |
| RP.05:Overdue tasks:count of overdue Tasks | `report.Overdue tasks.metric.count of overdue Tasks.definition` | a Task counts as overdue when Due date is before today AND its stage is not Done… | question |
| RP.04:Overdue tasks | `report.Overdue tasks.metrics` | ["count of overdue Tasks"] | question |
| RP.01:Overdue tasks | `report.Overdue tasks.question` | What has slipped past its due date and needs chasing? | question |
| RP.08:Overdue tasks | `report.Overdue tasks.scheduled_delivery` | {"enabled": "no"} | question |
| RP.02:Overdue tasks | `report.Overdue tasks.viewers` | ["Member"] | question |

## role

| # | Field | Value | Source |
|---|---|---|---|
| D04 | `role.*.forbidden_actions` | see build_model.D04 | derivation |
| D04 | `role.*.is_admin` | see build_model.D04 | derivation |
| D04 | `role.*.permitted_actions` | see build_model.D04 | derivation |
| D03 | `role.*.visible_screens` | see build_model.D03 | derivation |
| P.04:Admin | `role.Admin.assignable_by` | null | question |
| P.03:Admin | `role.Admin.billing_access` | null | question |
| P.01:Admin | `role.Admin.description` | null | question |
| P.02:Admin | `role.Admin.sees_private_data` | null | question |
| P.04:Guest | `role.Guest.assignable_by` | ["Admin", "Member"] | question |
| P.03:Guest | `role.Guest.billing_access` | null | question |
| P.01:Guest | `role.Guest.description` | An outside collaborator invited into specific projects only. | question |
| P.02:Guest | `role.Guest.sees_private_data` | no | question |
| P.04:Member | `role.Member.assignable_by` | ["Admin"] | question |
| P.03:Member | `role.Member.billing_access` | null | question |
| P.01:Member | `role.Member.description` | A person on the team who plans and does the work. | question |
| P.02:Member | `role.Member.sees_private_data` | no | question |

## roles

| # | Field | Value | Source |
|---|---|---|---|
| P.00 | `roles.multi_role_per_person` | no | question |
| A.16 | `roles.super_role` | Admin | question |

## screen

| # | Field | Value | Source |
|---|---|---|---|
| D03 | `screen.*.access` | see build_model.D03 | derivation |
| D03 | `screen.*.contents` | see build_model.D03 | derivation |
| sys_screen_interaction_pattern | `screen.*.interaction_states` | Standard loading / empty / error / success / back / leave-and-return behaviour o… | system_default |

## screens

| # | Field | Value | Source |
|---|---|---|---|
| Z.03 | `screens.inventory` | confirmed | question |
| D13 | `screens.inventory.items` | see build_model.D13 | derivation |

## tenancy

| # | Field | Value | Source |
|---|---|---|---|
| T.07 | `tenancy.branding` | null | question |
| T.02 | `tenancy.creation` | null | question |
| T.06 | `tenancy.isolation` | null | question |
| sys_client_isolation | `tenancy.isolation_mechanism` | Row-level security enforces organisation isolation in the database. | system_default |
| A.08 | `tenancy.mode` | single | question |
| T.01 | `tenancy.multi_membership` | null | question |
| T.05 | `tenancy.operator_role` | null | question |
| T.03 | `tenancy.org_admin_role` | null | question |
| sys_org_switcher | `tenancy.org_settings` | A person in several organisations switches with a standard switcher; each organi… | system_default |
| D09 | `tenancy.role_visibility` | see build_model.D09 | derivation |
| T.04 | `tenancy.roles_scope` | null | question |
| T.08 | `tenancy.suspend_delete` | null | question |
| sys_org_switcher | `tenancy.switcher` | A person in several organisations switches with a standard switcher; each organi… | system_default |

## visual

| # | Field | Value | Source |
|---|---|---|---|
| sys_theme | `visual.accessibility` | Light theme only; WCAG 2.1 AA contrast and keyboard access. | system_default |
| C.04 | `visual.brand_assets` | {"mode": "design_for_me"} | question |
| C.03 | `visual.density` | balanced | question |
| C.01 | `visual.references` | none | question |
| sys_theme | `visual.theme` | Light theme only; WCAG 2.1 AA contrast and keyboard access. | system_default |
| C.02 | `visual.tone` | ["clear", "fast", "calm"] | question |

## workflow

| # | Field | Value | Source |
|---|---|---|---|
| D08 | `workflow.*.transition_graph` | see build_model.D08 | derivation |
| FL.05:Task lifecycle | `workflow.Task lifecycle.approvals` | [] | question |
| FL.07:Task lifecycle | `workflow.Task lifecycle.cancel` | {"allowed": "no"} | question |
| FL.08:Task lifecycle | `workflow.Task lifecycle.on_complete` | Nothing further; it stays visible in its finished stage. | question |
| FL.06:Task lifecycle | `workflow.Task lifecycle.on_reject` | null | question |
| FL.04:Task lifecycle | `workflow.Task lifecycle.preconditions` | [] | question |
| FL.09:Task lifecycle | `workflow.Task lifecycle.readonly_from` | never | question |
| FL.11:Task lifecycle | `workflow.Task lifecycle.stage_notifications` | [] | question |
| FL.02:Task lifecycle | `workflow.Task lifecycle.stages` | {"stages": ["To do", "In progress", "Done"], "initial": "To do", "terminal": ["D… | question |
| FL.10:Task lifecycle | `workflow.Task lifecycle.timeouts` | [] | question |
| FL.03:Task lifecycle | `workflow.Task lifecycle.transitions` | [{"from": "To do", "to": "In progress", "mover": "roles", "roles": ["Member"]}, … | question |
| FL.01:Task lifecycle | `workflow.Task lifecycle.trigger` | {"kind": "person", "who": ["Member"], "action": "creating a task (starts in 'To … | question |

## Build model summary

- Records: Project, Task, Comment
- Roles: Admin, Member, Guest (super: Admin)
- Workflows: Task lifecycle
- Screens: 8 (`SPEC-PM-TEAMWORK-REF` navigation order)
- Actions: 14
- Generated QA tests: 42
